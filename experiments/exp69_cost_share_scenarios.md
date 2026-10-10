# Experiment 69 — what ranker-guided reviews could mean for FY2028 cost share

**Date:** 2026-10-10 · **Code:** `experiments/exp69_cost_share_scenarios.py` · **Inputs:** `exp69_published_per.json` (official FY2024/25 rates), `exp68_results.json` · **Results:** `experiments/exp69_results.json`

### Question

H.R. 1 (2025) makes states pay part of SNAP benefit costs from FY2028 if their payment error rate is 6% or more: 5% of benefits at 6–8%, 10% at 8–10%, 15% at 10% or more (FY2028 uses FY2025 or FY2026's rate; later years the rate from three years earlier; states with rate × 1.5 ≥ 20% can delay). How much could ranker-guided reviews of active cases lower a state's rate, and its cost share? This is a scenario model, not a forecast; its assumptions were committed (`d0c0a22`) before the all-state lifts existed.

### Method

- **Baseline:** USDA's official FY2025 payment error rates (FNA PDF dated June 24, 2026; national 10.62%). Annual benefits from FY2024 QC microdata (Σ FYWGT × RAWBEN × 12 = $91.0B nationally, close to FY2024's actual).
- **Mechanism:** errors stay in the caseload for m months until recertification. Reviews correct a share c = R × L × f of the caseload's error dollars each month (R = share of cases reviewed a month, L = the state's exp68 lift, f = share of found errors fixed). In steady state error dollars, and the rate, fall by 1 / (1 + c × m). Random reviews of the same volume use L = 1.
- **Scenarios:** low R 1%, top-20% lift, f 0.6, m 4; central R 2%, top-10% lift, f 0.8, m 6; high R 3%, top-10% lift, f 0.9, m 8. Staff: 30 minutes a review, 140 productive hours an FTE-month.

### Results

Today (FY2025 rates): 43 jurisdictions at or above 6%, paying **$10.56B a year** at FY2028 rules.

| All jurisdictions | Avoided with ranker reviews | Avoided with random reviews | Jurisdictions dropping a bracket (random) | Under 6% after (now 10) | Reviews a month / FTEs |
|---|---|---|---|---|---|
| Low | $0.32B | $0.16B | 5 (2) | 11 | 216k / 771 |
| **Central** | **$5.28B** | $1.03B | 38 (8) | 19 | 432k / 1,542 |
| High | $9.41B | $2.39B | 42 (25) | 41 | 648k / 2,314 |

Examples, central scenario: Pennsylvania 9.21% → 6.06% (share 10% → 5%, about $209M a year avoided; random reviews 8.40%, no bracket change); New York 13.18% → 8.79% (15% → 10%, about $360M); California 10.93% → 7.28% (15% → 5%); Alaska 23.15% → 20.70% (no change; its ranker is weak).

### Verdict

Informative. At the same review effort, ranker-guided reviews avoid about **five times** the cost share of random reviews in the central scenario ($5.28B vs $1.03B a year nationally), because the ranker sends reviewers to the costly errors. The range is wide (low $0.32B to high $9.41B) and driven mostly by review volume and how long errors persist, which a pilot would measure. Not modelled: whether corrections land before the federal sample month, procedural errors outside the public file (published rates run 2–3 points above microdata-implied rates, exp40), behaviour change, the delay option, and the cost of the reviews themselves beyond the FTE count.

### Next steps

1. A pilot should measure m (how long a found error would otherwise persist) and f (the fix rate): they move the answer more than the ranker does.
2. Present state results as ranges, never the central figure alone.
