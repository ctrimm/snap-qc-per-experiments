# Experiment 72 — household-type fairness of the rankers, all 53 jurisdictions

**Date:** 2026-10-10 · **Code:** `experiments/exp72_fairness_all_states.py` (pre-registered in its docstring) · **Results:** `experiments/exp72_results.json`

### Question

exp47–49 found, on the older six-state rankers, that ranking by dollars under-reviews elderly and disabled households relative to their error risk, and that per-type floors fix it at little cost. Does that hold for the current agency-side rankers in every jurisdiction?

### Method

Per jurisdiction, the exp68 configuration refit on its training rows, scoring its holdout; the top 20% are reviewed. Household types as exp47 (elderly > disabled > composition). Measure: each type's share of cases reviewed divided by its share of cases with an error, relative to the same ratio for all cases (1.0 = reviewed in proportion to risk). Remedy: exp49's per-type floor (f = 1.0: the review budget split across types by each type's share of training errors, top scores within type).

### Results

Median across jurisdictions (1.0 = proportional to risk):

| Household type | Ranked by dollars | With per-type floor |
|---|---|---|
| Elderly | **0.57** | 1.00 |
| Disabled (not elderly) | 0.81 | 1.00 |
| Single parent | 1.50 | 0.97 |
| Married with kids | 1.79 | 1.01 |
| Multi-adult with kids | 1.55 | 0.93 |
| Child-only | 1.12 | 0.99 |
| Childless adult | 1.03 | 0.99 |

- Elderly households are under-reviewed for their risk (ratio < 0.8) in **51 of 53** jurisdictions; disabled households in 22 of 51. With the floor: 0 and 2.
- Cost of the floor: median top-20% lift 3.25× → 3.18× (−0.10×). Largest costs: Wyoming 1.72× → 1.02×, Hawaii 2.68× → 2.25×, New York 3.54× → 3.13×, DC 3.80× → 3.45×. In three jurisdictions (Louisiana, Alaska, Guam) the floor slightly raised lift.
- Examples: Texas elderly 0.35 → 0.95; Pennsylvania 0.69 → 0.90 (lift 3.48× → 3.18×).

### Verdict

Held, and consistent everywhere. Ranking by dollars sends reviewers to families with earnings, whose errors are larger, and away from elderly households, whose errors are more frequent per dollar but smaller. A per-type floor makes review proportional to risk in nearly every jurisdiction for a small median cost in dollars found (about 3% of lift), though the cost is larger in a few states (New York −0.42×, Wyoming −0.70×).

### Next steps

1. Ship the floor as the default queue setting, with the dollar-only ranking available as an option and its trade-off shown per state.
2. Add both lifts (with and without the floor) to the map dashboard.
