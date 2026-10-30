# Experiment 113 — our ranker on rebuilt pre-review inputs, across three test windows and both price bases

**Date:** 2026-10-27 (pre-registered before running) · **Code:** `exp113_rebuilt_inputs_eras.py` · **Results:** `exp113_official_results.json`

### Why

- **Our inputs flatter us.** For error cases our inputs are the QC reviewer's corrected values. exp109 measured how much that flatters our dollar figures: about 17% in one window, train FY2022–23, test FY2024.
- **Their frame offers a fix and a wider test.** Better Government Lab's snap_qc published the modelling frame their munging script builds (`additional_data/reg_model_data.rds`, commit `46ac0d1`, the same script that produced exp109's frame). It holds approximate pre-review ("rebuilt") values for FY2017–19 and FY2022–24.
- **Their benchmarks sit beside it.** The repo carries per-state results for their delivery lists in three windows, in 2026 prices and in nominal dollars (`methods/cpi_inflate_test/out/lists_*`, two seeds).
- **Their own warning (findings §21):** dollar ranking beat precision ranking in 2024 but barely in the 2017–19 era.

So the question is whether our model, on rebuilt inputs, holds up:
- across eras;
- three years ahead (the gap a state actually faces);
- in either price basis.

The answer decides whether we rebuild our own inputs this way, and in which price basis.

### Design

**Frames:**
- **CPI:** the published `reg_model_data.rds` (2026 prices), converted to Parquet without change.
- **Nominal:** exp109's frame, built from the same munging script with `cpi_inflate_vars <- FALSE`. It matches the CPI frame row for row (231,619 rows; keyed by year and `HHLDNO`).

**Inputs:** our 20 leak-free features, built by our unchanged `context_features`. The rebuilt columns replace the reviewer fields (mapping as in exp109). SUA1 and HOMEDED are taken from the frame.

**Training label (our default, exp112):**
- **Error:** STATUS 2/3 with |AMTERR| above the year's federal tolerance (Better Government Lab `year_data.csv`: $38 FY2017, $37 FY2018–19, $48 FY2022, $54 FY2023, $56 FY2024).
- **Dollars:** |AMTERR|.
- **Weighting:** each state's adopted weight (own cases ×10 for `C_ctx`).
- **Learner:** `fit_w`, `E56.DEFAULT`, pooled over every state's training-year rows.

**Scoring (their definition, to match their lists):**
- **Error:** `over_threshold == 1`.
- **Dollars:** `total_error_amount` on those cases.
- **Test rows:** each state's test-year rows in the frame.

| Window | Train | Test | Their lists file |
|---|---|---|---|
| W1, one year ahead | FY2022–23 | FY2024 | `lists_2223_24_{cpi,nominal}.csv` |
| W2, second era | FY2017–18 | FY2019 | `lists_1718_19_{cpi,nominal}.csv` |
| W3, three years ahead | FY2017–19 | FY2022 | `lists_1719_22_{cpi,nominal}.csv` |

**Arms:** ours on the CPI frame (`B_cpi`) and on the nominal frame (`B_nom`). Each is compared with Better Government Lab's lists in the same price basis (seed 1; seed 2 reported as a noise check).

**Metrics, per state:**
- precision and dollar recall at 5% and 10% budgets, exactly as their lists are scored;
- our headline, top-20% dollar lift.

**Gate:** our test count per state must equal their lists' `n_te` in every state and window.

**Paired readouts (Better Government Lab's shipping companions):**
- the median paired difference;
- the mean;
- the harmed tail (states worse by more than 0.05) against the helped tail.

### Pre-registered decisions

1. **Price basis for our rebuilt inputs:** the arm with the higher median dollar recall at 10% in W3 (three years ahead, the deployment gap). Within 0.005 means CPI, to match Better Government Lab.
2. **Head-to-head claims:** "ours beats their lists" is claimed for a window and metric only when all three hold:
   - the median paired difference > 0;
   - the mean > 0;
   - the helped tail exceeds the harmed tail.

   Otherwise the result is reported as even or as theirs.
3. **Rebuilding our inputs (exp114, packaging):** go ahead if ours on rebuilt inputs keeps a median top-20% dollar lift of at least 2.0× in all three windows. The rebuilt figures then become the honest headline.

No hypothesis on direction.

### Results

<!-- AUTO-RESULTS:START -->
**Gate passed:** our test counts equal Better Government Lab's lists' `n_te` in every state, window and price basis (0 mismatches). Same cases, same error definition, same budgets.

**Coverage:** 49 jurisdictions. Better Government Lab's frame leaves out Alaska, Hawaii, Guam and the Virgin Islands, the jurisdictions with their own allotment tables.

**Our model on rebuilt pre-review inputs, median of 49:**

| | W1: one year ahead (test 2024) | W2: second era (test 2019) | W3: three years ahead (test 2022) |
|---|---|---|---|
| Top-20% dollar lift, nominal | **2.61×** (47 at 2.0×+) | **2.58×** (44) | **2.66×** (45) |
| Top-20% dollar lift, 2026 prices | 2.53× (45) | 2.60× (43) | 2.56× (46) |
| Lowest states, nominal | Texas 1.82×, Montana 1.91× | Vermont 1.46×, Idaho 1.55× | **Wyoming 0.66×**, New Hampshire 1.63× |

**Against Better Government Lab's lists (same price basis, seed 1; seed 2 within 0.03 of every median difference).** Dollar recall at a 10% budget:

| | W1 | W2 | W3 |
|---|---|---|---|
| Nominal: ours / theirs | 0.337 / 0.258 | 0.337 / 0.244 | **0.330 / 0.214** |
| Median diff, mean diff | +0.043, +0.054 | +0.096, +0.086 | +0.091, +0.108 |
| Higher in; helped / harmed (±0.05) | 39 of 49; 21 / 3 | 36; 30 / 4 | **47; 38 / 0** |
| 2026 prices: ours / theirs | 0.314 / 0.279 | 0.297 / 0.264 | 0.305 / 0.232 |

**Precision at 10%, nominal:**

| | W1 | W2 | W3 |
|---|---|---|---|
| Ours / theirs | 0.333 / 0.297 | 0.278 / 0.220 | 0.305 / 0.237 |
| States higher | 36 | 34 | 44 |

**At a 5% budget,** every median and mean difference is positive too, for both metrics and both price bases.

### Decisions (as pre-registered)

1. **Price basis: nominal.**
   - **The test:** at three years ahead, dollar recall at 10% is 0.330 nominal against 0.305 in 2026 prices, outside the 0.005 tie band.
   - **The contrast with Better Government Lab:** the conversion that helps their rules three years ahead (their findings §41) doesn't help ours. A plausible reason is that our ratio features (income per person, shelter to income, net to gross) already carry most of the scale-free signal.
2. **Head-to-head:** ours beats their lists in **all 24** window × price × metric comparisons, each meeting all three conditions (median > 0, mean > 0, helped > harmed).
   - **The second era holds.** Their §21 found dollar ranking barely beat precision ranking for their rules in 2019. Our model's lead in 2019 is as large as in 2024.
   - **Three years ahead, the lead is largest:** ours finds more dollars in 47 of 49 states and is worse by more than 0.05 in none.
3. **Rebuild our inputs: go (exp114).** The median top-20% lift on rebuilt inputs is at least 2.0× in all three windows (2.58–2.66× nominal).
   - **The honest headline:** this is what our model achieves on inputs closer to what a state has. It sits about 10–13% below the 2.96× on reviewer-recorded inputs (exp112), in line with exp109's estimate of the flattering.

**Caveats:**
- **Wyoming is below random three years ahead** (0.66×). Small samples make single states volatile.
- **The rebuild is approximate:** it uses the review's error codes to decide which field to shift. A state's own pre-review records remain the real test.
- **Their lists are a fixed rule list, ours a score.** Their advantage, readable rules, isn't measured here.
<!-- AUTO-RESULTS:END -->

## Note (October 30): predictions against rule lists

Every "ours beats their lists" result above compares **our model's per-case predictions** with **Better Government Lab's published rule lists**, the if-then rules a state receives. It doesn't compare model with model. Better Government Lab reports that its own boosted-tree models, replicated, give numbers matching ours. So these margins measure mostly what is given up by turning predictions into readable rules, not a better model. Better Government Lab plans a release in which one script outputs predictions rather than rules. That allows a prediction-to-prediction comparison, which would need its own pre-registration.
