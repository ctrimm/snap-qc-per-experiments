# Experiment 57 — quotable expected dollars for the triage rankers

**Date:** 2026-10-07 · **Code:** `experiments/exp57_calibrated_dollars.py` · **Results:** `experiments/exp57_results.json`

### Hypothesis

exp56's rankers order cases well, but the score they produce, P(error) × E[dollars | error], is also what a state would quote ("the top 20% of the queue holds about $X of errors"). PA5 noted that number runs up to ~40% low: P(error) is uncalibrated, and the dollar part predicts log1p(dollars), whose back-transform is a geometric mean. Correcting both, using out-of-fold (OOF) predictions inside the training rows, should bring expected dollars within ~10–15% of actual without changing the ranking. Moves the POC's production readiness (quotable numbers for a state CIO).

### Method

For each POC state (PA, NY, TX, SD, UT, ID), exp56's final configuration with `issued_benefit` (`exp56_results_<ST>_with_issued.json`; PA from `exp56b_results_with_issued.json`). On the non-holdout rows, 5-fold OOF raw P(error), log-dollar residuals and raw expected-dollar scores. Three estimates on each state's existing holdout (a measurement check, not a selection step):

1. **raw** — P(error) × expm1(log-dollar prediction).
2. **smearing + isotonic P** — isotonic-calibrated P(error) × (exp(prediction) × Duan smearing factor − 1).
3. **isotonic on the dollar score** — isotonic regression of actual dollars on the raw OOF expected-dollar score, applied to the holdout score.

All three are monotone in the raw score, so the ranking (and dollars recovered) is unchanged. Metric: expected ÷ actual dollars in the top 10%, top 20% and all holdout cases; expected calibration error (ECE, by decile) for P(error).

### Results

Expected ÷ actual (top 10% / top 20% / all cases):

| state | smearing factor | raw | smearing + isotonic P | **isotonic on dollar score** |
|---|---|---|---|---|
| PA | 1.78 | 0.73 / 0.71 / 0.64 | 1.22 / 1.21 / 1.13 | **0.99 / 0.99 / 0.97** |
| NY | 1.85 | 0.74 / 0.66 / 0.61 | 1.33 / 1.19 / 1.13 | **0.99 / 0.90 / 0.96** |
| TX | 2.00 | 0.71 / 0.54 / 0.51 | 1.27 / 0.98 / 1.05 | 1.23 / 0.92 / 0.97 |
| SD | 2.05 | 1.05 / 0.93 / 0.58 | 1.62 / 1.59 / 1.34 | **0.91 / 0.95 / 0.89** |
| UT | 1.86 | 0.74 / 0.76 / 0.59 | 1.31 / 1.36 / 1.13 | 1.23 / 1.28 / 1.07 |
| ID | 1.70 | 0.64 / 0.64 / 0.58 | 1.06 / 1.07 / 0.99 | 1.25 / 1.18 / 1.02 |

Mean absolute error of the top-20% ratio: raw 0.30, smearing + isotonic P 0.22, isotonic on dollar score 0.11. P(error) ECE raw → isotonic: PA 0.058 → 0.037, NY 0.054 → 0.025, TX 0.072 → 0.045, SD 0.150 → 0.051, UT 0.035 → 0.035, ID 0.036 → 0.050.

### Verdict

Held. Raw expected dollars run 36–49% low across all six states, confirming PA5. Smearing over-corrects (heavy-tailed dollar errors inflate the mean of exp(residuals), and top-scored cases regress toward the mean), overstating the top 20% by ~20%. Calibrating the final dollar score directly with isotonic regression on OOF predictions lands totals within ±11% in every state and the top 20% within ~10% in four of six; UT and ID still overstate the top slices by ~20% (small holdouts: 120–200 cases in each top 20%). Use the directly calibrated score for any quoted expected-dollar figure; rankings are unaffected.

### Next steps

1. Package each state's ranker with its dollar calibrator as the POC deliverable (one fit per state, refit annually per PA6/NY6 temporal results).
2. Report expected dollars with a ±15–20% band for a single state's top-of-queue estimate.
3. Over-issuance-weighted variant (PA5/NY5 next step) if a state's goal is program savings rather than total error dollars.
