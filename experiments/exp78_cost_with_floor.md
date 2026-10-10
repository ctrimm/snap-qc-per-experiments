# Experiment 78 — cost-share scenarios with the fairness floor on

**Date:** 2026-10-10 · **Code:** `experiments/exp78_cost_with_floor.py` (pre-registered in its docstring) · **Results:** `experiments/exp78_results.json`

### Question

exp69's figures assume dollar-only ranking, but the recommended default is exp72's per-household-type floor. What does the floor cost in avoided cost share? exp72 measured the floor's top-20% lift only, so both arms use the top-20% lift here (exp69's central and high scenarios used the top-10% lift, so their dollar-only figures below are lower than exp69's).

### Results

National FY2028 cost share avoided per year (jurisdictions dropping a bracket):

| Scenario | Dollar-only ranking | With fairness floor | Random reviews |
|---|---|---|---|
| Low (1% a month) | $0.32B (5) | $0.30B (4) | $0.16B (2) |
| Central (2%) | $3.85B (36) | **$3.49B (35)** | $1.03B (8) |
| High (3%) | $7.67B (41) | $7.33B (41) | $2.39B (25) |

### Verdict

Informative. The fairness floor costs about 9% of the avoided cost share in the central scenario ($3.85B → $3.49B a year) and one fewer jurisdiction drops a bracket. With the floor on, ranker-guided reviews still avoid about 3.4 times what random reviews do. On a like-for-like basis the default setting's central figure is about $3.5B a year, not exp69's $5.3B (which used the top-10% lift and no floor).

### Next steps

Quote the floor-on figure ($3.5B central, top-20% basis) as the default in the report and dashboard, with the dollar-only figure beside it.
