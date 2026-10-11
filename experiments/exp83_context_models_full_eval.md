# Experiment 83 — full held-out evaluation of the context-aware pooled models

**Date:** 2026-10-10 · **Code:** `experiments/exp83_context_models_full_eval.py` (pre-registered in its docstring) · **Results:** `experiments/exp83_results.json`

### Why

exp80/82 adopted context-aware pooled models in all 53 jurisdictions on two readouts (top-20% holdout lift and time split). The deliverable also reports top-10% lift, the dollar-forecast check and household-type fairness, which had been measured on the old own-case models only. This measures them for the adopted models (each refit on its training rows plus all other jurisdictions', with a dollar calibrator from out-of-fold scores), on each exp68 holdout. A measurement, not a selection step; it reproduces every adopted top-20% lift exactly.

### Results (53-jurisdiction medians)

| | Own-case models (exp68/72) | **Context-aware pooled (now deployed)** |
|---|---|---|
| Top-20% lift | 3.25× | **3.97×** (lowest Alaska 2.96×) |
| Top-10% lift | — | **6.38×** |
| Dollar forecast ÷ actual, top 20% | 1.03 (49 of 53 within ±20%) | **1.00 (52 of 53)**; Alaska 1.39 is the exception |
| Lift with the fairness floor | 3.18× | **3.93×** |
| Elderly review ÷ risk, no floor → floor | 0.57 → 1.00 | 0.61 → 1.00 |

- Elderly households are still under-reviewed for their risk without the floor in 49 of 53 jurisdictions, and disabled households in 30 of 51; with the floor, no jurisdiction has elderly households below 0.8.
- The floor's cost is now small almost everywhere (median −0.04×); the largest costs are Hawaii (−0.56×), Wyoming (−0.51×) and the Virgin Islands (−0.28×).

### Verdict

The context-aware pooled models are better on every measure the deliverable reports: more lift at both cut-offs, better-calibrated dollar forecasts, and a fairness floor that now costs about 1% of lift instead of 2–3%. They replace the own-case models in the package, the dashboard, the standalone map and the report. The exp69/78 cost-share scenarios used the own-case lifts and are therefore conservative.
