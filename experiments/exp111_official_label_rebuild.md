# Experiment 111 — rebuilding the deployed rankers on the official error definition

**Date:** 2026-10-26 (pre-registered before running) · **Decision:** adopt exp110's OVER arm as the default (its pre-registered rule was met; approved by the project lead the same day) · **Code:** `SNAPQC_LABEL` in `exp58_agency_rankers.py`; reruns of exp83, exp93, exp79, exp107_timesplit, exp107_package · **Results:** `*_official_results.json`

### What changes

- **The new default label:** rankers now learn and are scored on the official payment-error definition (`SNAPQC_LABEL=official`, the default): |RAWBEN − FSBEN| above the fiscal year's federal tolerance ($38 FY2020, $39 FY2021, $48 FY2022, $54 FY2023, $56 FY2024).
- **The dollars:** that difference.
- **The status:** "2" overpaid, "3" underpaid.
- **Inputs:** unchanged and leak-free. RAWBEN and FSBEN enter the label only, never the inputs.
- **The old label:** `SNAPQC_LABEL=any` (any reviewer-found error, AMTERR dollars) reproduces exp107.

### Why

The official error rate, which sets the H.R. 1 cost share, counts only these errors. exp110 found that training on them:
- raises the median top-20% lift on over-threshold dollars (2.47× → 2.61×), and with the floor 2.10× → 2.45×;
- costs 1.7% of the lift on all error dollars;
- reviews older and disabled households closer to their share.

### Runs (same data, holdouts, seeds and settings as exp107)

| Script | Gate or role |
|---|---|
| `exp83_context_models_full_eval.py` | **Gate:** top-20% lift must equal exp110's OVER `lift_over` in 53 of 53 (same label, rows, order and seeds) |
| `exp93_cost_share_current_models.py` | Cost share; scenario lifts are now lifts on over-threshold dollars. **Check:** central ≈ $3.15B (exp110's estimate from a slightly different summation) |
| `exp79_underpayment_ranker.py` | Underpayment ranker; underpayment = over-threshold and RAWBEN < FSBEN |
| `exp107_timesplit.py` | Later-years test |
| `exp107_package.py` | All 53 packaged models; the model card records `error_label: official` |

### Then

**Papers, briefs, the replication guide and the dashboard** get the new figures, under a dated correction note:
- **The new headline:** lift on the dollars that count toward the official error rate.
- **The cost share:** restated; the central estimate becomes about $3.15B (exp110).
- **Checks:** `state_numbers.py check` must pass on the new sources.

### Results

<!-- AUTO-RESULTS:START -->
**Gate passed:** exp83 under the new default reproduces exp110's OVER arm top-20% lift on over-threshold dollars in 53 of 53. exp93's central cost share is $3.15B, as exp110 estimated.

**Packaged:** 53 of 53 model cards record `feature_set: leakfree`, `error_label: official`, built 2026-10-26.

All lifts below are on the dollars that count toward the official payment error rate (over the tolerance).

| Median of 53 jurisdictions | exp107 (any-error label; any-error dollars) | **exp111 (official)** |
|---|---|---|
| Top 20% vs random | 2.70× (1.98–3.67) | **2.61×** (Idaho 1.49× – Alaska 3.37×) |
| Jurisdictions at 2.0× or better | 52 of 53 | 50 of 53 |
| Top 10% vs random | 3.31× | **3.37×** |
| Found per review hour, top 20% (random) | $45–251 | **$142** median ($52); range $44–550 |
| Dollar forecast within 20% of actual | 43 of 53 | 43 of 53 (median expected/actual 0.99) |
| Later years (train 2020–22, test 2023–24) | 2.61× | **2.51×** (Kansas lowest 1.72×) |
| With the fairness floor, top 20% | 2.42× | **2.45×** (median cost 7% of the lift; most Maine 35%; no cost in 8) |
| Older households' review ratio, dollar-only | 0.33 (53 of 53 below 0.8) | **0.44** (50 of 52 below 0.8) |
| With the floor | 1.00; none below 0.8 | **1.02; 8 of 52 below 0.8** (lowest 0.66) |
| Disabled households, dollar-only | 0.63 | 0.79 (26 of 51 below 0.8) |
| Underpayment ranker vs main ranker, underpayment dollars | 1.80× vs 1.54× (better in 36) | **1.91× vs 1.41× (better in 41)** |

**Comparability:** the exp107 column measured any-error dollars, while the official rate counts only over-threshold dollars. On those dollars exp107's model scored 2.47× (exp110), so the like-for-like change is 2.47× → 2.61×.

**FY2028 cost share avoided a year (exp93 scenarios, top-10% floor-on lift on over-threshold dollars):**

| Scenario | Floor on | Dollar-only | Random review |
|---|---|---|---|
| Low | $0.21B | $0.21B | $0.16B |
| **Central** | **$3.15B** (31 states drop a bracket) | $3.90B | $1.03B |
| High | $7.05B | $7.73B | $2.39B |
| Central, top-20% basis | $2.72B | | |

**What changed besides the numbers:**
- **The floor is costlier than its 7% median cost suggests.** It now costs $0.75B of the central estimate ($3.90B → $3.15B), against $0.13B before. With fewer errors per household type to set its shares, it also no longer lifts every jurisdiction above 0.8 (8 below).
- **Small states lose most:** Idaho falls 2.02× → 1.49×, South Dakota 2.82× → 2.25×, Utah 2.17× → 2.01×. Over-threshold errors are rarer, so their own-state signal is thinner.
- **New York and Pennsylvania:** New York gains (3.05× → 3.22×); Pennsylvania is about flat (2.70× → 2.62×).

### Verdict

Adopted as the default. Every paper, brief, the guide and the dashboard are restated on these figures (Oct 26). The cost share's central estimate is $3.15B (low $0.21B, high $7.05B). The floor-coverage regression (8 jurisdictions below 0.8) is a caveat, and the next fairness work.
<!-- AUTO-RESULTS:END -->
