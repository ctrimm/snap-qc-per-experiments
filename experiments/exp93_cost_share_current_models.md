# Experiment 93 — FY2028 cost share on the deployed models, fairness floor on

**Date:** 2026-10-15 · **Code:** `experiments/exp93_cost_share_current_models.py` (pre-registered in its docstring, written before running; not committed before the run) · **Results:** `experiments/exp93_results.json`

### Question

Two cost-share figures were in circulation: $5.28B a year (exp69 central) and $3.49B (exp78). Both used the old own-case lifts (exp68), not the deployed pooled models (exp83). And most of the gap between them came from switching the lift basis, not from the floor. exp78 had to use the top-20% lift because the floor had only been measured there:

| Central scenario, old models | Avoided a year | What changed |
|---|---|---|
| exp69 | $5.28B | top-10% lift, no floor |
| exp78, dollar-only arm | $3.85B | top-20% lift instead (−$1.43B) |
| exp78, floor arm | $3.49B | fairness floor (−$0.36B) |

What does exp69's pre-registered scenario give on the deployed models with the floor on, the recommended default?

### Method

1. Re-ran exp83's fit for each jurisdiction and measured the exp72 floor at both top 10% and top 20%. Gate: top-10% lift, top-20% lift and top-20% floor lift must reproduce exp83 exactly.
2. exp69's model, inputs and scenarios unchanged (low R 1%, top-20% lift, f 0.6, m 4; central R 2%, top-10% lift, f 0.8, m 6; high R 3%, top-10% lift, f 0.9, m 8). Arms: floor on, dollar-only, random. Also the floor-on central on the top-20% basis.

The first run measured everything and passed the gate, then crashed writing the JSON (a numpy integer). The fix only touched serialization. The rerun reproduced the same measurements.

### Results

Gate: **53 of 53** jurisdictions reproduce exp83 exactly. Median lifts: top 10% 6.38× (6.17× with the floor), top 20% 3.97× (3.93× with the floor). With the floor at the top 10%, elderly review is a median 0.995 of fair share.

National FY2028 cost share avoided per year (jurisdictions dropping a bracket); $10.56B a year due now:

| Scenario | **Floor on** | Dollar-only | Random |
|---|---|---|---|
| Low | **$0.39B** (6) | $0.39B (6) | $0.16B (2) |
| Central | **$6.05B** (40) | $6.82B (40) | $1.03B (8) |
| High | **$10.06B** (42) | $9.99B (42) | $2.39B (25) |

- Central, floor on, top-20% basis (conservative reading): **$4.06B**.
- Central examples, floor on: Pennsylvania 9.21% → 5.66% (10% → none, $418M a year); New York 13.18% → 8.19% (15% → 10%, $360M); California 10.93% → 7.25% (15% → 5%, $1.19B); Texas 9.34% → 6.13% (10% → 5%, $343M); Alaska 23.15% → 17.68% (no change).
- Under 6% after (central): 27 jurisdictions with the floor, against 11 with random reviews (10 today).

### Verdict

Informative. The default figure is now **about $6.1B a year** (central, floor on, deployed models), about six times random reviews ($1.0B). Both earlier figures understated it because they used the old lifts. At the top-10% basis the floor costs $0.77B of the central figure (about 11%), more than at the top-20% basis ($0.15B), because the floor gives up more lift at the very top of the queue. The range across scenarios is $0.4–10.1B, and exp73's finding stands: review volume and error lifetime drive it.

### Next steps

1. Quote $6.1B (floor on, central) as the default, with $4.1B (top-20% basis) as the conservative reading and the low–high range beside it.
2. The dashboard now reads its cost fields from this experiment.
