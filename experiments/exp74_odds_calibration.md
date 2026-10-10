# Experiment 74 — are the flag cards' "about N in 10" odds honest?

**Date:** 2026-10-10 · **Code:** `experiments/exp74_odds_calibration.py` (pre-registered in its docstring) · **Results:** `experiments/exp74_results.json`

### Question

Flag cards show the top three parts of the case to check as "about N in 10". A first look at exp65's cards found "9 in 10" right only 57% (NY) to 71% (PA) of the time. Are the odds overconfident, and does a simple, order-preserving recalibration fix them?

### Method

PA, NY, ID. The exp61 where-to-look model; temperature scaling fit on 5-fold out-of-fold probabilities from the training error cases (one temperature per state, by log loss), which leaves the ranking of parts unchanged. Test: flagged holdout errors (as exp61/62). Metric: expected calibration error (ECE) over every listed part, plus a reliability table by "N in 10". Adopted if ECE falls in all three states.

### Results

| State | Temperature | ECE raw → calibrated | "9 in 10" raw: n, actually right | after |
|---|---|---|---|---|
| PA | 2.90 | 0.124 → **0.048** | 80, 71% | 9, 89% |
| NY | 2.90 | 0.172 → **0.050** | 82, 57% | 8, 75% |
| ID | 2.80 | 0.217 → **0.074** | 54, 50% | 4, 50% |

After calibration the odds track reality across the scale (PA: "5 in 10" right 61%, "8 in 10" 86%; NY: "7 in 10" 82%, "8 in 10" 78%). The raw model said "9 in 10" for about two-thirds of its first picks; calibrated, it says that only when it's earned.

### Verdict

Held; adopted. The raw odds were overconfident (ECE 0.12–0.22). Temperature scaling (T ≈ 2.9) cuts calibration error by 60–70% in all three states without changing which parts are listed or their order, so coverage (exp65: 86–88% top-3) is unchanged.

### Next steps

1. Apply the temperature in the flag-card builder before any reviewer sees cards.
2. Reword the card line to "in about N of 10 similar cases with an error": the odds are conditional on there being an error.
