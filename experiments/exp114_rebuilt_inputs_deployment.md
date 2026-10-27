# Experiment 114 — rebuilding the deployed rankers on pre-review inputs (DESIGN DRAFT)

**Date:** 2026-10-27 · **Status:** **DRAFT for discussion, not pre-registered and not run.** The open decisions below must be settled before a pre-registration is written. · **Depends on:** exp109, exp112, exp113

### Why

The deployed rankers (exp112) are trained and evaluated on the public QC file's "reported" fields, which for error cases hold the reviewer's corrected values. A state scoring its own caseload sees the agency's pre-review values instead.

Two experiments have measured the gap:
- **exp109:** on giannella/snap_qc's rebuilt pre-review values, our dollar recall falls about 17% one year ahead.
- **exp113:** across three windows (test 2024, test 2019, three years ahead), the median top-20% lift on rebuilt inputs is 2.58–2.66×, against 2.96× on reviewer values.

exp113's pre-registered rule says go. This experiment would make rebuilt inputs the basis of the packaged models and of every headline figure.

**What exp114 would change, and what it wouldn't:**
- **Would change:** the training data and the evaluation.
- **Wouldn't change:** how a state uses the tool. A state still scores its own case records with `score_cases.py`, and those records already are pre-review values. Training on rebuilt values makes the training data look like what the model will see.

### What we know going in

| | Reviewer inputs (exp112) | Rebuilt inputs (exp113, nominal) |
|---|---|---|
| Median top-20% lift | 2.96× (exp68 holdout, 53 jurisdictions) | 2.61× (test 2024), 2.58× (test 2019), 2.66× (3 years ahead); 49 states |
| Years available | FY2020–24 | FY2017–19, FY2022–24 |
| Jurisdictions | 53 | 49 (no AK, HI, GU, VI) |
| Rows | 167,002 | 231,619 (after exclusions) |
| Price basis | nominal | nominal won three years ahead (exp113) |

### Open decisions

**1. Where the rebuilt values come from.**

| Option | For | Against |
|---|---|---|
| A. giannella's published frame (`reg_model_data.rds`) | No new code. It's their maintained output, and exactly what exp113 tested | 2026 prices only, so we'd still need our own nominal build (exp109 ran their R script with one flag). It depends on their release cadence and choices (exclusions, years) |
| B. Run their R munging script ourselves (as exp109 did) | Nominal, and our own control of the flag. Reproducible from their tagged commit | An R toolchain in our pipeline (Homebrew R, 9 packages, about 25 minutes to compile Arrow) |
| C. Port the rebuild to Python | Self-contained. We could extend it to FY2020–21 and to AK/HI/GU/VI with their allotment tables | Real work (their script is about 1,100 lines with several repaired defects; findings §28, §38). It must reproduce their frame exactly before use |

*Leaning:* **B** now, pinned to a giannella commit, with **C** as a follow-up that has to reproduce B row for row.

**2. The four jurisdictions their frame leaves out** (Alaska, Hawaii, Guam, Virgin Islands; separate allotment tables).
- (a) Keep their current exp112 models, clearly labelled as trained on reviewer values.
- (b) Train them on the pooled rebuilt frame and score with their own BENMAX; evaluation would be thin.
- (c) Wait for option C.

*Leaning:* (a), with a note on every page that shows them.

**3. FY2020–21.** Their frame drops these years (pandemic emergency allotments; findings, frame provenance), and our later-years test (train 2020–22, test 2023–24) uses them.
- Replace the later-years test with exp113's three windows. W3 (train 2017–19, test 2022) is the deployment-like gap and the better test anyway.

*Leaning:* yes.

**4. Evaluation design.**
- **New per-state holdouts:** 25%, stratified, seeded, drawn from the frame's FY2022–24 rows (exp68's design).
- **Plus exp113's three windows** as the forward tests.
- **The headline becomes** the holdout top-20% lift on rebuilt inputs; the forward tests are reported beside it.

**5. Training years for the packaged models.**
- (a) All six years (2017–19 and 2022–24).
- (b) 2022–24 only, the closest to now.

*To test:* exp113 suggests the model is stable across eras. Settle it with a pre-registered comparison on W1 (train 2022–23 vs 2017–18 + 2022–23, test 2024).

**6. Label.**
- **Training:** the official label (STATUS 2/3 with |AMTERR| over the tolerance, exp112), computed on the frame's rows.
- **Scoring:** the frame's `over_threshold` / `total_error_amount` (giannella's definition) agrees by construction after their reconciliation filter. Report both.

**7. Cost share.**
- **How:** recompute exp93's scenarios on the new floor-on lifts (top 10%, over-tolerance dollars).
- **The expected direction:** lower than $4.47B, since the lifts fall about 10–13%.
- **The four excluded jurisdictions:** they keep exp112 lifts, flagged.

**8. Fairness floor.** Re-measure the elderly and disabled ratios on rebuilt inputs, as every model change has moved them. Watch the 8 jurisdictions now below 0.8.

**9. Scoring script.**
- **No input change:** `score_cases.py` keeps the same 13 fields plus BENMAX.
- **Model cards:** they record `input_basis: rebuilt_pre_review`, the giannella commit, and the price basis.

### Gates (to pre-register)

- **Frame reproduction (option B):** our nominal build must equal exp109's frame row for row (231,619 rows, identical columns used).
- **exp113 reproduction:** the W1/W2/W3 medians must reproduce exactly before anything new runs.
- **Coverage:** every packaged model card records its input basis. Four jurisdictions are labelled reviewer-input.

### What it would restate

- the headline lift (about 2.6×, from 2.96×);
- the cost share;
- the fairness ratios;
- the seven state briefs, the PA/NY brief and the replication guide (all 53 rows, four flagged);
- the triage whitepaper, project summary, both older-adults papers, the comparison paper, COST-SHARE-REPLICATE, LEARNINGS and the dashboard.

### Not in scope

- Changing the model (features, learner, weighting), and inflation adjustment (exp113 chose nominal).
- giannella's rule lists. The head-to-head is settled in exp113 and isn't rerun here.

### Decision needed from the project lead

The **source** of the rebuilt values (A, B or C) and the handling of the **four excluded jurisdictions**. The rest follows from exp113.
