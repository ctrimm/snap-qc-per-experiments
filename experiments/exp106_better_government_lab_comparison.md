# Experiment 106 — comparing with Better Government Lab's snap_qc

**Date:** 2026-10-26 (pre-registered before any part B code ran) · **Code:** `exp106_better_government_lab_comparison.py` · **Their repo:** [github.com/giannella/snap_qc](https://github.com/giannella/snap_qc) at `eedb3f5` (v2.7.0, 2026-10-06), Apache 2.0 · **Results:** `exp106_results.json`

> **Note (October 30):** where this write-up compares our results with Better Government Lab's lists, it is our model's per-case predictions against their published rule lists, not model against model. Their rule lists are built for agencies that can't run a model: readable if-then rules in a workbook a state can use as is. A model scoring higher on dollar recall than those lists is expected and isn't a judgment on that approach. Better Government Lab reports that its own boosted-tree models give numbers matching ours. See the README section "Building on Better Government Lab's work" for what we adopted from them.

### Why

Better Government Lab's snap_qc is an independent project on the same problem with the same public data. It mines interpretable if-then rules from the SNAP QC public-use files and delivers a ranked rule list per state, for a review budget of 5% or 10% of the caseload. Where two independent teams agree, the finding is more trustworthy; where they disagree, one of us has something to learn. This experiment compares the two on findings (part A) and head to head on one test (part B).

### What they do, in brief (from their README, GUIDANCE.md, PIPELINE.md and features.R)

| | Better Government Lab's snap_qc | This repo |
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

### Amendment 2 (2026-10-26, before it ran): leak-free re-run

**Why.** Part B showed our rankers' inputs combine the agency's issued benefit (`RAWBEN`) with the QC reviewer's recorded facts (`RAWGROSS`, `RAWNET`, `RAWERND`, `SHELDED`, household size, and the ratios built on them), which for error cases are the corrected values. Better Government Lab's snap_qc avoids this: its benefit feature is recomputed from the reported facts (`raw_benefit_amount = rawben_recreated`), never the issued amount.

**Leak-free feature set (L1):** our 22 features minus the two that carry the issued benefit: `issued_benefit` (RAWBEN) and `benefit_share_of_max` (RAWBEN / BENMAX). The remaining inputs are all reviewer-recorded facts plus BENMAX, so they agree with one another and cannot reveal an error by disagreeing.

**Limitation that remains:** for error cases these facts are still the corrected ones, while a deployed tool sees the agency's uncorrected facts. With public data this can't be removed, and it affects Better Government Lab's lists equally. L1 removes the direct leak; it does not make the held-out numbers a deployment forecast.

**Runs** (same splits, seeds, engine and adopted variants as before; the variants were chosen on leaky features, a stated bias):
- **D0:** exp83's design (exp68 holdouts): top-10% and top-20% lift on all error dollars and on over-threshold dollars, per jurisdiction.
- **D1:** part B's one-year-ahead test with L1, paired against Better Government Lab's v2.5.0 lists.
- **C:** part C's fairness ratios, on both the leaky (B0) and the L1 refit:
  - review ratio of elderly and disabled households, any-error and over-threshold definitions;
  - with and without the floor;
  - against random review.
- **Cost share:** exp93's central scenario recomputed with the L1 floor-on top-10% lift (and the top-20% basis).

**Expectation, stated in advance:**
- **D1:** L1 precision at the 5% budget should fall to roughly the range of Better Government Lab's (0.25–0.40).
- **D0:** the top-20% lift should fall well below 3.97×.

Whatever it shows replaces the ranker figures in the papers, which carry an under-review notice until then.

### Results

<!-- AUTO-RESULTS:START -->
Scored 2026-10-26 by `exp106_better_government_lab_comparison.py` (part B, 2 min 57 s) and `exp106_leakfree.py` (amendments 1–2, 3 min 13 s), 8 workers.

**Gates:** the leaky refit reproduced exp83's top-20% lift, exp83's floor lift and exp93's top-10% floor lift in 53 of 53 jurisdictions each. The leak-free numbers therefore differ from the published ones by the two removed inputs only.

**Same test frame:** our FY2024 frame matched Better Government Lab's (median 847 cases per state, 12.4% over-threshold base rate, 49 states).

### Part B: the published (leaky) model on their test

| Median of 49 states, FY2024 | Ours, published features | Theirs (v2.5.0 lists) |
|---|---|---|
| Precision, 5% budget | **1.000** | 0.318 |
| Precision, 10% budget | 0.800 | 0.298 |
| Dollar recall, 5% / 10% | 0.593 / 0.805 | 0.141 / 0.265 |

**Not credible, and the evidence shows why: our features leak.**
- **The fields hold the reviewer's values.** The QC technical documentation says the raw file "is generated from the monthly reviews"; "reported" fields are the reviewer's.
- **They equal the reviewer's calculations on error cases.** On 5,809 FY2024 over-threshold error cases: RAWGROSS = FSGRINC 98.9%, RAWERND = FSERNDED 98.1%, SHELDED = FSSLTDED 91.9%, RAWNET = FSNETINC 86.0%, CERTHHSZ = FSUSIZE 100%.
- **The formula reproduces the reviewer's benefit.** The benefit formula on RAWNET reproduces the reviewer's benefit (FSBEN) in 79.8%, and the issued benefit (RAWBEN) in 0.8%.
- **The mechanism:** our features put the issued benefit beside the reviewer's corrected facts. Better Government Lab's do not; their benefit feature is recomputed from the reported facts.

### Amendment 2: leak-free (L1, without `issued_benefit` and `benefit_share_of_max`)

| Median of 53 jurisdictions (exp83 design) | Published (leaky) | Leak-free (L1) |
|---|---|---|
| Top-20% lift, all error dollars | 3.97× | **2.70×** (range 1.98–3.67; 52 of 53 at 2.0× or more) |
| Top-10% lift | 6.38× | **3.31×** |
| Top-20% lift, over-threshold dollars only | 4.68× | 2.95× |
| Top-20% lift with the fairness floor | 3.93× | 2.42× |
| Top-10% lift with the floor | 6.17× | 2.93× |
| Share of top-20% reviews finding any error / an over-threshold error | 0.80 / 0.57 | 0.66 / 0.31 |

**FY2028 cost share avoided, exp93's scenarios with the L1 floor-on lifts:**

| Scenario | Avoided a year |
|---|---|
| Low | $0.21B |
| **Central** | **$3.42B** (published $6.05B) |
| High | $6.63B |
| Central, top-20% basis | $2.79B (published $4.06B) |

**D1, their one-year-ahead test with L1, paired against their lists (49 states):**

| | Ours (L1) | Theirs | Paired median difference | States where ours is higher / lower |
|---|---|---|---|---|
| Precision, 5% budget | 0.404 | 0.318 | +0.065 | 33 / 16 |
| Precision, 10% budget | 0.319 | 0.298 | +0.041 | 33 / 14 |
| Dollar recall, 5% | 0.260 | 0.141 | +0.109 | 39 / 10 |
| Dollar recall, 10% | 0.410 | 0.265 | +0.132 | 39 / 10 |

**Hypotheses:**
- **H1 (ours higher dollar recall):** supported at both budgets.
- **H2 (theirs higher precision):** not supported; ours is also higher on precision.
- **H3 (over-threshold lift within 10% of any-error lift):** not supported. Over-threshold lift is higher, by 18% (leaky) and 9% (L1) at the median.
- **Caveats:**
  - Their lists are interpretable rules shipped as a workbook, and ours a score.
  - Both use reviewer-recorded facts for error cases, so neither number is a deployment forecast.

### Part C: elderly and disabled households (top 20%, median of jurisdictions)

| | Leaky, any error | Leaky, over-threshold | **L1, any error** | **L1, over-threshold** |
|---|---|---|---|---|
| Elderly, ranking by dollars | 0.61 | 0.95 | **0.33** | **0.50** |
| Elderly, below 0.8 | 49 of 53 | 12 of 52 | 53 of 53 | 47 of 52 |
| Elderly, below random review | 52 | 51 | 53 | 52 |
| Elderly, random review gives | 0.90 | 1.35 | 0.90 | 1.35 |
| Elderly, with the floor | 1.00 | 1.51 | 1.00 | 1.51 |
| Disabled, ranking by dollars | 0.78 | 1.01 | 0.63 | 0.82 |
| Disabled, below random review | 34 of 51 | 34 | 48 | 48 |

**What part C shows:**
- **The leak hid the problem.** Without the leak, dollar ranking under-reviews elderly households more, not less: below random review in 52–53 jurisdictions under either error definition.
- **The definition doesn't rescue it.** Under the official over-threshold definition elderly households have fewer errors (random review gives them 1.35), and dollar ranking still gives them 0.50.
- **The floor still works.** It lifts them above proportional on both definitions.

### Verdict

**Our published ranker figures were inflated by a feature leak.**
- **The cause:** our models paired the agency's issued benefit with the QC reviewer's corrected facts.
- **Without the leak:** the ranker still finds about 2.7× the error dollars of random review in the top fifth of the queue (3.3× in the top tenth), and a central $3.42B a year of FY2028 cost share avoided, against $6.05B published.
- **On the same leak-free footing it beats Better Government Lab's lists** on dollar recall (+0.11 to +0.13) and precision (+0.04 to +0.07), paired over 49 states.
- **The fairness finding holds and is stronger:** dollar ranking under-reviews older households under both error definitions, and the floor fixes it.

**What follows:**
1. **Papers and dashboard:** every paper and the dashboard need their ranker figures replaced. They carry an under-review notice until then.
2. **Packaged models:** the models in `deliverables/state_rankers/` use the leaky features and must be refit on L1.
3. **Remaining limitation:** reviewer-recorded facts for error cases remain in both projects; only a state's own pre-review data can remove it.
4. **Adopt from Better Government Lab:** their 2026-dollar conversion, which they found helps lists applied three years after their training data.
<!-- AUTO-RESULTS:END -->

### Correction (2026-10-26, after results; found in the triple-check)

Two statements above about Better Government Lab's method are wrong, as their munging script shows (`1_data_munging_and_raw_variable_reconstruction_for_using_public_qc_data.R`, steps 5–7, `correct_variables <- TRUE`):
- **Their inputs are rebuilt, not recomputed.** Amendment 2's "its benefit feature is recomputed from the reported facts" and Part B's "their benefit feature is recomputed from the reported facts" are wrong. Better Government Lab starts from the reviewer's final values (`FS*`), uses the error codes (`ELEMENT1`/`NATURE1`) to decide which field was in error, and shifts that field a dollar at a time until the benefit formula gives `RAWBEN`. Their mined features (`rawearn`, `rawgross`, `rawrent`, …) and `raw_benefit_amount = rawben_recreated` are therefore approximate **pre-review** values.
- **The limitation is not shared.** Verdict item 3 ("reviewer-recorded facts for error cases remain in both projects") is wrong. It remains in ours.
- **Consequence:** D1 compares our model on reviewer-corrected inputs with their lists on rebuilt pre-review inputs. That is not like-for-like and may favour ours. The fair test is our model on their rebuilt inputs. It needs their R pipeline; R is not installed here.
- **The near-maximum artifact** they report (CHANGELOG v2.6) is a defect in that rebuild: cases where it could not reach the issued benefit. It is not a trace of our leak.

