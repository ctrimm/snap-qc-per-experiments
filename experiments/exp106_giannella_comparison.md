# Experiment 106 — comparing with giannella/snap_qc

**Date:** 2026-10-26 (pre-registered before any part B code ran) · **Code:** `exp106_giannella_comparison.py` · **Their repo:** [github.com/giannella/snap_qc](https://github.com/giannella/snap_qc) at `eedb3f5` (v2.7.0, 2026-10-06), Apache 2.0 · **Results:** `exp106_results.json`

### Why

giannella/snap_qc is an independent project on the same problem with the same public data. It mines interpretable if-then rules from the SNAP QC public-use files and delivers a ranked rule list per state, for a review budget of 5% or 10% of the caseload. Where two independent teams agree, the finding is more trustworthy; where they disagree, one of us has something to learn. This experiment compares the two on findings (part A) and head to head on one test (part B).

### What they do, in brief (from their README, GUIDANCE.md, PIPELINE.md and features.R)

| | giannella/snap_qc | This repo |
|---|---|---|
| Output | A frozen, ranked list of if-then rules per state (interpretable; ships as an Excel workbook) | A scoring model per state (expected error dollars per case) |
| Engine | Rules mined from xgboost + ranger tree paths, filtered by a false-discovery-rate test and a 30-case floor | Two-part gradient-boosted model: P(error) × E[dollars \| error], isotonic-calibrated |
| Ranking | 99% Wilson lower bound of each rule's precision (count-based); dollar ranking tested as an option | Expected error dollars |
| Error definition | \|RAWBEN − FSBEN\| above the federal tolerance threshold for the fiscal year ($48 FY2022, $54 FY2023, $56 FY2024); base rate about 11% | Any error (STATUS 2 or 3), AMTERR dollars; base rate about 38% |
| Data | FY2017–19 and FY2022–24 (FY2020–21 excluded); MFIP and SSI-cap cases excluded; dollars converted to 2026 prices | FY2020–24, all cases; nominal dollars |
| Pooling | National rule pool blended with the state's own pool on one confidence scale | Every state's cases pooled, plus two inputs for the state's benefit levels |
| Headline test | Mine on FY2022–23, score each state's FY2024 at 5% and 10% budgets: median precision 0.318 / 0.298, 2.7× random error dollars at 10% nationwide | Random 25% holdout per state (top-20% lift median 3.97×), plus train 2020–22 / test 2023–24 (median 3.80×) |

### Part A: findings, compared

Each of their GUIDANCE.md claims that touches something we also tested, set against our result: agree, disagree, or not comparable. Written up from the documents; no new computation.

### Part B: one test, one footing (pre-registered)

Their 2024 benchmark (`methods/v250_benchmark_2024/v250_benchmark_2024.csv`, 49 states, the lists they ship) gives per state, at budgets of 5% and 10%: precision (share of flagged cases with an over-threshold error), dollar recall (share of over-threshold error dollars caught), and lift (precision ÷ base rate).

**Our arm (B1, primary):** our deployed recipe unchanged, trained their way.
- Train on FY2022–23 cases of all 53 jurisdictions pooled, with each state's adopted variant (exp80/exp82: B_ctx, or C_ctx with own cases ×10).
- Score each state's FY2024 cases and flag the top 5% and 10% by expected dollars.

**Test frame:** each state's FY2024 cases with their exclusions applied where the public file allows: MFIP (`MN_FIP` ≠ 0) and SSI-cap (`SSI_CAP` ≠ 0) cases dropped, and cases dropped where \|RAWBEN − FSBEN\| differs from AMTERR by more than $5. Their frame drops a few more rows in munging; we report our test-frame size beside theirs.

**Metrics, their definitions:**
- **Error:** \|RAWBEN − FSBEN\| > $56 (the FY2024 threshold).
- **Precision:** share of flagged cases with an error.
- **Dollar recall:** share of error dollars (\|RAWBEN − FSBEN\| of error cases) caught.
- **Lift:** precision ÷ base rate.

**Secondary arm (B2, exploratory):** the same recipe but trained on their target (over-threshold errors, over-threshold dollars). It tests whether training on the official definition matters.

**Also reported:**
- our deployed models' existing holdout lift (exp83) recomputed on over-threshold dollars only (B0). This asks whether our headline lift depends on sub-threshold errors, which never count toward the payment error rate.

**Hypotheses, with the comparison paired by state (median of per-state differences, sign test):**
- **H1:** ours has higher dollar recall at both budgets. We rank by dollars; they rank by precision.
- **H2:** theirs has higher precision at both budgets, for the same reason reversed.
- **H3 (B0):** our top-20% lift on over-threshold dollars is within 10% of the any-error lift (median across 53).

No winner is declared. The two tools optimize different goals, and the point is to measure the trade-off on one test.

**Caveats fixed in advance:**
- **Frames differ.** Their frame and ours differ in small exclusions, so base rates are compared per state.
- **Dollars.** Their lists are scored in 2026 dollars and ours in nominal; recall shares are unaffected.
- **Interpretability.** Their lists are interpretable rules, ours a score; parity on numbers does not mean parity on deployability.

### Amendment 1 (2026-10-26, before part C ran): elderly and disabled households under the official error definition

Part A turned up a definitional split, measured on the QC files with their exclusions:
- **Any error:** elderly-or-disabled households have more errors than others (FY2022–24: 45.4% against 33.0%).
- **Over the tolerance threshold:** they have fewer (12.6% against 17.2%), and hold 33.7% of over-threshold error dollars while making up 49.0% of the caseload.

Our fairness findings (exp47–49, exp72, exp83) measure each household type's risk with any error. That raises the question whether dollar ranking still under-reviews elderly households when risk is measured with the errors that count toward the payment error rate.

**Part C:** for each jurisdiction, the deployed model as refit in B0 (exp83 recipe, exp68 holdout, top 20%), compute:
- each household type's review ratio (share of reviews ÷ share of error cases) with error = over-threshold, beside the any-error ratio (which must reproduce exp83's);
- the same with the fairness floor (exp72 rule, budget split by training share of error cases, any-error definition as shipped).

**Readouts:**
- the median elderly and disabled ratios under each definition;
- the number of jurisdictions below 0.8;
- the number below what random review would give.

There is no hypothesis on direction; this is a measurement.

### Results

<!-- AUTO-RESULTS:START -->
(pending)
<!-- AUTO-RESULTS:END -->
