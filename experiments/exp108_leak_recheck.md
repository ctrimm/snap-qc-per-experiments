# Experiment 108 — rechecking four results that may share the exp106 leak

**Date:** 2026-10-26 (pre-registered before running) · **Code:** `exp108_leak_recheck.py`; re-runs of `exp74_odds_calibration.py` and `exp67_feedback_loop_sim.py` · **Results:** `exp108_results.json` (legacy gate), `exp108_leakfree_results.json`, `exp74_results.json`/`exp67_results.json` (legacy gates, unchanged), `exp74_leakfree_results.json`, `exp67_leakfree_results.json`

### Why

exp106 found that our ranker inputs paired the issued benefit (`RAWBEN`) with QC reviewers' corrected facts; exp107 rebuilt the rankers without it. Four published results used models with the same inputs and were marked "not rechecked" in the papers:
1. **Flag-card "check first" coverage** (exp65: the real error's location among the top 3 listed parts for 88% of flagged errors in PA and 86% in NY). The where-to-look model predicts the error's part of the case from the same inputs. A mismatch between the issued benefit and the reviewer's income or deductions could point straight at the part, so this is the likeliest to be inflated.
2. **The flag cards' odds calibration** (exp74: raw "N in 10" odds overconfident, ECE 0.12–0.22, cut to 0.05–0.07 by temperature scaling, T ≈ 2.9).
3. **The feedback-loop simulation** (exp67: a ranker retrained only on its own flagged reviews reaches 2.60× in 2024 against 3.05× with all labels, about 15% less effective).
4. **The early household-type tests** (exp47/49):
   - on the Pennsylvania and New York synthetic-trained rankers, elderly households were reviewed at 0.22/0.34 of their error rate;
   - reviewed elderly and disabled cases had an error 66% and 70% of the time (PA);
   - the floor raised review precision from 49% to 58% with no measurable loss in dollars per hour.

### Design

Every item runs twice, with the same data, splits and seeds:
- **Legacy** (`SNAPQC_FEATURES=legacy`): must reproduce the published figure. This is the gate.
- **Leak-free** (the default).

**Items 1–3:**
- **Item 1:** coverage is recomputed with exp62/exp65's card logic (`--top-k 3`). The where-to-look classifier is trained on non-holdout error cases with known location, and scored on the top 20% of the state's ranked holdout. Coverage = the share of flagged errors whose real location (T3) is among the top 1/2/3 listed parts. PA and NY are the gate states; ID, UT and SD are reported too.
- **Item 2:** `exp74_odds_calibration.py` is rerun as is (its output now goes through `results_path`).
- **Item 3:** `exp67_feedback_loop_sim.py` is rerun as is (likewise).

**Item 4:** the early synthetic-trained rankers aren't what a state would deploy. So instead of re-running them, the same household measurements are taken on the leak-free deployed models for PA and NY (exp107 design, exp68 holdouts, top 20%):
- for each household type: error rate, review rate, both ratios (exp47's review rate ÷ error rate, and exp72's share ratio), and precision among reviewed cases;
- with the floor: lift, precision and ratios.

The published synthetic-ranker figures stay as history, labelled.

### What changes depending on the result

The papers quote all four. Each figure is replaced by its leak-free value, or confirmed, and the "not rechecked" labels are removed. No hypothesis on direction, except the expectation stated in exp106 that item 1 is the most exposed.

### Amendment 1 (2026-10-26, before it ran): does pooling still beat state-only without the leak?

**Why.** The comparison paper says both projects find national data is the backbone, and ours rests on the claim that pooled models beat state-only ones (exp75, exp80, exp82). That was measured only on the leaky features.

**Design.** `exp108_pooling.py`. For each of 53 jurisdictions, on the exp68 holdout and the leak-free features (exp83 design), compare:
- **pooled:** the deployed pooled model, its top-20% lift taken from `exp83_leakfree_results.json`;
- **state-only:** the same learner (`fit_w`, `E56.DEFAULT`, the same features) trained on the state's own non-holdout cases only.

**Readout:** the median top-20% lift of each, and the number of states where pooled is higher. The claim holds if pooled is higher in the median state and in most states.

### Results

<!-- AUTO-RESULTS:START -->
**Gates passed.** Under `SNAPQC_FEATURES=legacy` every item reproduces its published figure:
- coverage PA 88.2%, NY 85.8% (published 88%/86%);
- ECE PA 0.124 → 0.048, NY 0.172 → 0.050, ID 0.217 → 0.074;
- feedback loop 2.60× vs 3.05×.

The leak-free household figures for PA and NY match the corrected briefs (lift 2.70×/3.05×; elderly share ratio 0.42/0.54; with the floor 2.69×/2.55× and 0.90/1.20).

**Item 1: flag-card coverage. Holds, with a caveat.**

| Top-20% flagged errors with a known location | Legacy top-3 | Leak-free top-1 | top-2 | **top-3** | Always list the 3 most common parts |
|---|---|---|---|---|---|
| PA (n 127 → 108) | 88.2% | 63.9% | 75.0% | **83.3%** | 79.6% |
| NY (127 → 108) | 85.8% | 51.9% | 73.1% | **88.9%** | 78.7% |
| ID (82 → 66) | 86.6% | 50.0% | 72.7% | **87.9%** | 81.8% |
| UT (46 → 39) | 76.1% | 56.4% | 69.2% | **82.1%** | 82.1% |
| SD (27 → 29) | 85.2% | 44.8% | 62.1% | **82.8%** | 79.3% |

- **Coverage barely moved:** PA fell 5 points and NY rose 3. The leak was not what made the cards cover the error.
- **New, and more important:** a fixed list of each state's three most common error locations covers 79–82% on its own, so the model adds only 1–10 points over it at top 3 (none in Utah). Most of the card's top-3 coverage is base rate. The model's own value shows mostly in the order (top-1 45–64%).
- **The comparison was not pre-registered; it is reported as found.**

**Item 2: odds calibration. Holds.**

| | Raw ECE (legacy → leak-free) | Calibrated ECE (legacy → leak-free) | T (leak-free) |
|---|---|---|---|
| PA | 0.124 → 0.124 | 0.048 → 0.059 | 2.90 |
| NY | 0.172 → 0.209 | 0.050 → 0.054 | 2.95 |
| ID | 0.217 → 0.222 | 0.074 → 0.081 | 2.85 |

- **Same conclusion:** the raw "N in 10" odds are overconfident, and temperature scaling (T ≈ 2.9) cuts the error by about two-thirds in all three states (adopt: true).
- **Corrected range:** 0.12–0.22 → 0.05–0.08.

**Item 3: feedback-loop simulation. Does not hold.**

| Mean of 6 states, lift in 2024 | eps = 0 (flagged only) | eps = 0.1 | eps = 0.2 | All labels |
|---|---|---|---|---|
| Legacy (published) | 2.60× | 2.73× | 2.68× | 3.05× |
| **Leak-free** | **2.40×** | 2.31× | 2.22× | **2.29×** |

- **By state, leak-free (flagged only vs all labels):** PA 2.83 vs 2.56; NY 3.10 vs 3.13; TX 1.84 vs 1.76; SD 2.47 vs 2.09; UT 2.02 vs 2.30; ID 2.13 vs 1.92.
- **Share of error dollars found, mean of the four years:** 43.4% vs 42.8%.
- **The published 15% loss was the leak.** The extra past cases in the "all labels" arm mostly carried more examples of the issued-benefit mismatch to learn from. Without the leak, a ranker retrained only on its own flagged reviews does no worse over four years than one retrained on every case: it is better in 4 states and worse in 2, by amounts within the simulation's noise.
- **The random slice doesn't measurably help either.**
- **What still stands:** the claim "retraining only on flags degrades the model" is withdrawn. Including the federal QC sample in retraining remains sensible, because it is free and unbiased, and a random slice is still how a pilot checks the forecast. But neither is supported by this simulation as protection against a measured loss.

**Item 4: household detail on the deployed leak-free models.**

| Top 20%, dollar ranking | PA | NY | Early synthetic tests (exp47–49) |
|---|---|---|---|
| Elderly review rate ÷ error rate | 0.20 | 0.29 | 0.22 / 0.34 |
| Elderly share ratio (exp72) | 0.42 | 0.54 | — |
| Elderly reviewed cases with an error | 62% | 71% | 66% / 44% |
| Disabled reviewed cases with an error | 69% | 76% | 70% / 65% |
| All reviewed cases with an error (random: 43% / 37%) | 68% | 74% | 49% (PA) |
| With the floor: reviewed with an error | 71% | 76% | 58% (PA) |
| With the floor: lift | 2.69× (vs 2.70×) | 2.55× (vs 3.05×) | "no measurable loss" |

- **The early finding holds on today's models:** dollar ranking reviews older households at a fifth (PA) to under a third (NY) of their error rate, and most of their reviewed cases have an error. It is not a detection failure.
- **The floor's effect on precision is smaller than in the early tests:** +2 to +3 points rather than +9, because today's queue has fewer error-free cases to swap out.
- **The floor's cost:** none in PA, 16% of lift in NY (as already published from exp107).

### Verdict

| Item | Published | Leak-free | Status |
|---|---|---|---|
| Card top-3 coverage | 88% PA, 86% NY | 83% PA, 89% NY | Holds; but a fixed list of the 3 most common locations gets 79–80% |
| Odds calibration | ECE 0.12–0.22 → 0.05–0.07 | 0.12–0.22 → 0.05–0.08 | Holds |
| Retraining on flags only | about 15% worse in 4 years | no measurable loss (2.40× vs 2.29×) | **Withdrawn** |
| Older households (early tests) | 0.22/0.34 of error rate; 66%/44% of reviewed have errors | 0.20/0.29; 62%/71% | Holds; NY precision corrected; floor precision gain +2–3 points, not +9 |

**Papers updated (Oct 26):** project summary, triage whitepaper, replication guide, the PA/NY/ID briefs, both older-adults papers, and the comparison paper. The "not rechecked" labels are removed.
<!-- AUTO-RESULTS:END -->
