# Experiment 55 — reportable-variance distribution for the generator (IN PROGRESS)

**Date:** 2026-10-07 · **Code:** `experiments/exp55_build_dist_reportable.py`, `experiments/exp55_measure.py`, `experiments/exp52_rlvr_dataset.py --dist --fy-coding` · **Artifact:** `experiments/dist_reportable.json`

### Hypothesis

exp54 matched synthetic labels to the eval by reweighting, which fixed the label mix but did not change what the generator produces. The root cause is that `dist.json` counts every recorded variance in the FY2024 file, including zero-dollar ones, while the generator only records variances that change the benefit and the eval labels the largest *reportable* (AMOUNT > 0) variance. Building the generator's variance distribution from reportable variances only should make synthetic labels eval-consistent by construction, without reweighting, and should not cost real-case skill. Moves gate 1 (calibration fidelity) and gate 3 (LM eval).

### Method

**Measurement (FY2024 public-use file, supported buckets).** Of 22,836 recorded variances on error cases, 11,899 (52%) have AMOUNT = 0; 59% of those are nature 97 (timing). Reportable variances (AMOUNT > 0): nature 97 = 19%. Variances on correct cases are negligible (4).

**Build** (`exp55_build_dist_reportable.py`). `dist_reportable.json` is a copy of `dist.json` whose variance-level tables are recomputed from AMOUNT > 0 variances on error cases: `bucket_probs` (+ earner / no-earner / the four exp11 earner×senior strata), `nature_given_bucket` (+ earner splits), `cause_given_bucket`, `p_over_97_given_bucket` (single-reportable-variance cases). Case-level rates are copied unchanged. `dist.json`, `eff.json` and `inject.json` are untouched; default generator output is unchanged.

**Calibration check** (`exp55_measure.py`, n = 30,000, seed 7, persistent pool) against real FY2024, with the primary variance defined the eval's way.

**Training test.** 4,000 / 200 finding-balanced, view-calibrated training cases from `dist_reportable.json` with FY-aware coding only (cause 26 re-drawn and natures 56/57 coded 53 for the eval's 5/6 pre-2024 share; no reweighting). Answer-only SFT, lr 1e-5, rank 16, batch 4, 500 steps; dev scores at steps 300/400/500.

### Results

Calibration vs real FY2024:

| | real | `dist.json` | `dist_reportable.json` |
|---|---|---|---|
| nature 97 share (largest reportable variance) | 0.20 | 0.41 | **0.21** |
| nature mix L1 | — | 0.47 | **0.21** |
| bucket mix L1 | — | 0.10 | **0.08** |
| finding mix L1 (bar ≤ 0.03) | — | 0.010 | 0.077 (over 0.278 vs 0.239) |
| dollar errors ≤ $56 | 0.70 | 0.70 | 0.59 |
| median dollar error | $31 | $21 | $37 |
| error cases with 2+ reportable variances | 0.07 | 0.11 | 0.10 |

**Re-fit calibration.** `inject.json` re-fits have no effect under the default dollar mechanisms: `dollar_mech.adopted_dist` overrides them with exp31's baked-in constants. So the exp31 capture was re-run against the new distribution (`exp31_adopt_dollar.py capture --dist experiments/dist_reportable.json --out experiments/exp55_capture_reportable.json`, ~20 s) and the generator gained `--calibration FILE` (via `dollar_mech.constants_from_capture`) to use it. Default output is byte-identical (3,000 cases, `cmp`). Direction boosts moved over 0.664 → 0.537, under 0.989 → 1.081; phase-1 coins earner 0.913 → 0.884, no-earner 0.857 → 0.770.

| vs real FY2024 | real | `dist.json` | reportable, old constants | **reportable, re-fit** |
|---|---|---|---|---|
| correct / over / under | .603 / .239 / .158 | .602 / .244 / .154 | .587 / .278 / .136 | **.617 / .243 / .140** |
| finding mix L1 (bar ≤ 0.03) | — | 0.010 | 0.077 | **0.037** |
| nature 97 share | 0.20 | 0.41 | 0.21 | 0.21 |
| bucket mix L1 | — | 0.10 | 0.08 | 0.07 |
| dollar errors ≤ $56 | 0.70 | 0.70 | 0.59 | 0.60 |

The remaining dollar gap points at a missing case type: ~45% of real FY2024 error cases carry no reportable variance at all (8,053, exp30), small-dollar errors with only zero-amount variances recorded. The reportable draw never produces them.

Within-direction nature mix (what the balanced training set sees), L1 vs real: over 0.53 → 0.34, under 0.56 → 0.48; nature 97 within over 0.35 → 0.16 (real 0.16), within under 0.51 → 0.30 (real 0.26).

Training labels by construction (no reweighting): T4 97 27%, 53 18%; T5 agency 48%, client 32%, other 18%, no-fault 2% (real FY21–23: 47 / 38 / 16 / 0%).

SFT dev results: pending (run started 2026-10-07 14:02).

### Verdict

Pending the SFT result. So far: the reportable distribution fixes the label mix by construction. With its own re-fit exp31 constants (`--calibration`), the finding mix is near the bar (L1 0.037 vs ≤ 0.03); dollar sizes still skew large until the no-reportable-variance case type is modeled.

### Next steps

1. Score the SFT run (dev, checkpoints 300–500) against the original recipe (seed 52 / 53 peaks 0.271 / 0.167).
2. Model the missing case type: error cases whose only recorded variances have no dollar effect (~45% of real FY2024 error cases; small dollar errors, no T3–T5 label). Should close the ≤ $56 gap and pull the finding mix under the bar. (`calibrate_injection.py` / `measure_effectiveness.py` gained `--bundle`, but the exp31 capture path above is the one that matters under dollar mechanisms.)
3. Dropped from the backlog: "raise the multi-variance rate" (exp27). Only 7% of real error cases carry 2+ *reportable* variances; exp27's ~33% counted zero-dollar variances. Synthetic is already at 10%.
4. Remaining generator item: the six T3 buckets it never produces (childsupport, assets, reporting, standard, income_total, other).
