# Experiment 108 — rechecking four results that may share the exp106 leak

**Date:** 2026-10-26 (pre-registered before running) · **Code:** `exp108_leak_recheck.py`; re-runs of `exp74_odds_calibration.py` and `exp67_feedback_loop_sim.py` · **Results:** `exp108_results.json`, `exp74_leakfree_results.json`, `exp67_leakfree_results.json`

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

### Results

<!-- AUTO-RESULTS:START -->
(pending)
<!-- AUTO-RESULTS:END -->
