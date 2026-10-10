# Experiment 73 — which assumption drives the cost-share range?

**Date:** 2026-10-10 · **Code:** `experiments/exp73_cost_sensitivity.py` · **Results:** `experiments/exp73_results.json`

### Question

exp69's national range was wide ($0.32B–$9.41B a year avoided). Which input drives it, and so what should a pilot measure first? One factor at a time around exp69's central scenario (2% of cases reviewed a month, top-10% lift, 80% of found errors fixed, errors last 6 months), same model and inputs.

### Results

National FY2028 cost share avoided per year:

| Factor | Range tried | Ranker-guided reviews | Random reviews | Jurisdictions under 6% |
|---|---|---|---|---|
| Cases reviewed a month | 0.5% → 5% | **$1.32B → $9.87B** | $0.16B → $2.84B | 12 → 43 |
| Months an error lasts | 2 → 12 | **$1.73B → $8.98B** | $0.16B → $2.39B | 14 → 38 |
| Share of found errors fixed | 50% → 100% | $3.52B → $6.37B | $0.21B → $1.23B | 16 → 26 |
| Ranker lift | top-20% lift / top-10% × 0.75 / top-10% | $3.85B → $5.28B | $1.03B (unchanged) | 16 → 19 |

Today: 10 jurisdictions under 6%, $10.56B a year in cost share.

### Verdict

Informative. Review volume and how long errors stay in the caseload drive the range: each moves the answer by about $7–8B across plausible values. The fix rate moves it by about $3B, and the ranker's own accuracy by about $1.4B, even with a 25% haircut on its lift. At every setting, ranker-guided reviews avoid 3–15 times what random reviews of the same volume avoid.

### Next steps

A pilot should measure first how long a found error would otherwise have lasted (time to the next recertification or change report) and the realistic review volume. Those two numbers settle most of the uncertainty; the ranker's lift is already the best-measured input.
