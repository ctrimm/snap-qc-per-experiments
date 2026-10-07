# Experiment 56 — tuned triage classifier, PA + five states (issued benefit +0.7× in PA; tuning +4–11% in 5 of 6 states)

**Date:** 2026-10-07 · **Code:** `experiments/exp56_pa_tuned_classifier.py` · **Results:** `experiments/exp56_results.json`

### Hypothesis

PA5 identified the production path for Pennsylvania: rank cases for QC review by P(error) × E[dollars | error], trained on real PA QC features, with PA-conditioned synthetic as a cold start. Its real-trained arm was untuned (scikit-learn defaults; 5.00× top-10% and 3.15× top-20% dollar lift on the 817-case holdout). Tuning the ranker for the job — dollars recovered per review hour — on budget-time features should raise recovered dollars at the top of the queue, without leaking reviewer-verified fields. This advances the PA POC's production recommendation (the classifier half of the "classifier for the score, LLM for the words" split, exp53).

### Method

- **Data:** real PA QC cases (STATE 42), FY2020–2024, 3,268 rows. The PA2/PA8 holdout (817 rows, `pa2_holdout_idx.json`) is scored once, at the end; everything else (2,451 rows) is for training and tuning.
- **Features (budget-time only):** the clean-8 set (PA7 dropped `issued_benefit` as a post-decision feature) plus derived ratios: total income, income per person, earned share, shelter ÷ income, medical and dependent-care presence. AMTERR and reviewer fields are never inputs.
- **Model:** two-part ranker, HistGradientBoosting P(error) classifier × log-dollar regressor on error cases.
- **Objective:** dollars recovered in the top 20% of the ranking (PA5's metric); review cost 30 min/case (PA5's assumption).
- **Search:** random search over learning rate, leaf count, min leaf size, L2 and iterations for both models, scored by 3-fold CV inside the training data; for the synthetic arm, also the weight on PA-synthetic rows (0, 0.05, 0.1, 0.3).
- **Estimate:** nested CV (5 outer folds, each with its own inner search) vs the untuned recipe on the same folds.
- **Arms:** untuned clean-8 (PA5 b-r minus `issued_benefit`); tuned real-only; tuned real + PA-synthetic (20k cases, `synth.pa_state.generate_pa`, seed 7).
- **Checks:** time split (tune FY2020–22, test FY2023–24 on non-holdout rows); single holdout score.

### Results

**Smoke run (n_search 3, 3k synthetic; pipeline check).** Nested-CV top-20% lift: untuned 2.48×, tuned real 2.73×, tuned real + synth 2.43×; time split 2.58× → 2.68×. Holdout: untuned clean-8 2.75× / 2.77× / 2.17× at top 10 / 20 / 30%, tuned 3.48× / 2.53× / 2.14×. Caveats: a 3-config search is not a real tuning, and this smoke scored the holdout, so the full run's holdout score is its second look. It also took 42 min from thread oversubscription (scikit-learn across 28 cores on 2k-row fits, alongside an MLX training job); the full run caps `OMP_NUM_THREADS=2`.

**Full run (n_search 30, 20k synthetic, ~20 min with `OMP_NUM_THREADS=2`):**

| top-20% dollar lift vs random | untuned clean-8 | tuned real | tuned real + synth |
|---|---|---|---|
| nested CV (2,451 cases, 5 outer folds) | 2.48× | **2.71×** | 2.70× |
| time split (tune FY20–22, test FY23–24, n = 1,216) | 2.58× | **2.85×** | — |

The inner search picked synthetic weight 0.0 in all five outer folds.

Holdout (817 cases; second look, see smoke caveat), final arm tuned real:

| | top 10% | top 20% | top 30% |
|---|---|---|---|
| untuned clean-8 | 2.75× ($129/hr) | **2.77×** ($131/hr) | 2.17× |
| tuned | **3.57×** ($168/hr) | 2.59× ($123/hr) | 2.17× |

Reference: PA5's untuned ranker *with* `issued_benefit` reached 5.00× / 3.15× at top 10 / 20%.

**Arm b: + `issued_benefit`** (`--with-issued`, results `experiments/exp56b_results_with_issued.json`; holdout third look):

| top-20% dollar lift | clean-8 untuned | clean-8 tuned | + issued, untuned | **+ issued, tuned** |
|---|---|---|---|---|
| nested CV | 2.48× | 2.71× | 3.19× | **3.34×** |
| time split (FY23–24) | 2.58× | 2.85× | 2.93× | **3.16×** |
| holdout top 10% | 2.75× | 3.57× | 4.92× ($231/hr) | **5.19× ($244/hr)** |
| holdout top 20% | 2.77× | 2.59× | 3.33× ($158/hr) | **3.33× ($158/hr)** |
| holdout top 30% | 2.17× | 2.17× | 2.57× | 2.50× |

Tuned + synth with issued: 3.32× nested CV (synthetic still adds nothing).

**All six POC states** (`--state`, `--with-issued`, n_search 30; results `experiments/exp56_results_<ST>_with_issued.json`; holdouts are each state's existing PA2/NY2/TX/SD/UT2/ID2 split; "untuned" = scikit-learn defaults, same features):

| state | training cases (errors) | nested-CV top-20% lift: untuned → tuned | time split (FY23–24) | synthetic | holdout top-20% $/hr tuned (random) |
|---|---|---|---|---|---|
| PA | 2,451 (1,046) | 3.19× → **3.34×** (+5%) | 2.93× → 3.16× | no gain (3.32×) | $158 ($47) |
| NY | 2,442 (895) | 3.12× → **3.31×** (+6%) | 3.14× → 3.20× | no gain (3.20×) | $193 ($56) |
| TX | 2,592 (1,147) | 2.24× → **2.41×** (+8%) | 2.15× → 2.34× | +0.02× (2.41 vs 2.39) | $143 ($53) |
| SD | 1,773 (455) | 2.59× → 2.55× (−2%) | 2.31× → 2.35× | — | $58 ($22) |
| UT | 3,075 (1,010) | 2.48× → **2.76×** (+11%) | 2.11× → 2.24× | **+0.14×** (2.76 vs 2.62) | $61 ($26) |
| ID | 2,879 (969) | 2.85× → **2.96×** (+4%) | 2.64× → 2.65× | no gain (2.87×) | $62 ($22) |

Holdout top-20% for each state's final arm vs untuned: NY 3.44× vs 3.32×, TX 2.68× vs 2.36×, SD 2.66× vs 2.88×, UT 2.32× vs 2.33×, ID 2.79× vs 2.72× (120–200 cases per top-20% slice; noisy).

### Verdict

Held, with the feature mattering more than the tuning. Adding `issued_benefit` — known at triage time; PA7's exclusion was about element classification — is worth ~+0.7× top-20% lift (nested CV 2.48× → 3.19×) and brings the top 10% to ~5×, matching PA5's original ranker. Tuning for dollars recovered adds a modest, consistent 5–10% on top (with issued: nested CV 3.19× → 3.34×, time split 2.93× → 3.16×). Best PA ranker: tuned + issued benefit, ~$244 per review hour at the top 10% and $158/hr at the top 20% on the holdout (30 min/case). Clean-8 alone: tuning adds 9–10% at the top 20%.

Across the six POC states the recipe mostly holds: tuning adds 4–11% in nested CV in five states and every time split is equal or better; SD, the smallest dataset (455 training errors), is the exception (−2%; the inner search overfits). Synthetic rows help clearly only in UT (+0.14×) and marginally in TX; elsewhere they add nothing, so "synthetic = cold start" holds for four of six states. Every state's ranker beats random review by 2.4–3.3× at the top 20%. The holdout shows the gain at the top 10% (+30%) but not at 20% (163 cases; within noise), so nested CV is the estimate to quote. PA-synthetic rows add nothing once real PA data is available (weight 0 in every fold), confirming PA5: synthetic is the cold start, not the production model. The largest remaining lever is a feature, not tuning: `issued_benefit`, dropped by PA7 for the element task, is known at triage time and carried PA5's ranker to 3.15× at the top 20%.

### Next steps

1. ~~Re-run with `issued_benefit`~~ done (arm b): adopt it for the triage ranker.
2. **(recommended)** Calibrate P(error) (isotonic on out-of-fold predictions) so expected-dollar estimates are quotable, plus PA5's smearing correction for the log-dollar regressor.
3. ~~Repeat for NY/TX/SD/UT/ID~~ done (above). For SD, use the untuned recipe or a narrower search; for UT, keep the synthetic rows.
