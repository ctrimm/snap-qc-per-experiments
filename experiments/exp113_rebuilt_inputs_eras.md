# Experiment 113 — our ranker on rebuilt pre-review inputs, across three test windows and both price bases

**Date:** 2026-10-27 (pre-registered before running) · **Code:** `exp113_rebuilt_inputs_eras.py` · **Results:** `exp113_official_results.json`

### Why

- **Our inputs flatter us.** For error cases our inputs are the QC reviewer's corrected values. exp109 measured how much that flatters our dollar figures: about 17% in one window, train FY2022–23, test FY2024.
- **Their frame offers a fix and a wider test.** giannella/snap_qc published the modelling frame their munging script builds (`additional_data/reg_model_data.rds`, commit `46ac0d1`, the same script that produced exp109's frame). It holds approximate pre-review ("rebuilt") values for FY2017–19 and FY2022–24.
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
- **Error:** STATUS 2/3 with |AMTERR| above the year's federal tolerance (giannella `year_data.csv`: $38 FY2017, $37 FY2018–19, $48 FY2022, $54 FY2023, $56 FY2024).
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

**Arms:** ours on the CPI frame (`B_cpi`) and on the nominal frame (`B_nom`). Each is compared with giannella's lists in the same price basis (seed 1; seed 2 reported as a noise check).

**Metrics, per state:**
- precision and dollar recall at 5% and 10% budgets, exactly as their lists are scored;
- our headline, top-20% dollar lift.

**Gate:** our test count per state must equal their lists' `n_te` in every state and window.

**Paired readouts (giannella's shipping companions):**
- the median paired difference;
- the mean;
- the harmed tail (states worse by more than 0.05) against the helped tail.

### Pre-registered decisions

1. **Price basis for our rebuilt inputs:** the arm with the higher median dollar recall at 10% in W3 (three years ahead, the deployment gap). Within 0.005 means CPI, to match giannella.
2. **Head-to-head claims:** "ours beats their lists" is claimed for a window and metric only when all three hold:
   - the median paired difference > 0;
   - the mean > 0;
   - the helped tail exceeds the harmed tail.

   Otherwise the result is reported as even or as theirs.
3. **Rebuilding our inputs (exp114, packaging):** go ahead if ours on rebuilt inputs keeps a median top-20% dollar lift of at least 2.0× in all three windows. The rebuilt figures then become the honest headline.

No hypothesis on direction.

### Results

<!-- AUTO-RESULTS:START -->
(pending)
<!-- AUTO-RESULTS:END -->
