# Experiment 55 — reportable-variance distribution for the generator (labels fixed by construction; real-case skill at parity)

**Date:** 2026-10-07 · **Code:** `experiments/exp55_build_dist_reportable.py`, `experiments/exp55_measure.py`, `experiments/exp52_rlvr_dataset.py --dist --fy-coding` · **Artifact:** `experiments/dist_reportable.json`

### Hypothesis

exp54 matched synthetic labels to the eval by reweighting, which fixed the label mix but did not change what the generator produces. The root cause is that `dist.json` counts every recorded variance in the FY2024 file, including zero-dollar ones, while the generator only records variances that change the benefit and the eval labels the largest *reportable* (AMOUNT > 0) variance. Building the generator's variance distribution from reportable variances only should make synthetic labels eval-consistent by construction, without reweighting, and should not cost real-case skill. Moves gate 1 (calibration fidelity) and gate 3 (LM eval).

### Method

**Measurement (FY2024 public-use file, supported buckets).** Of 22,836 recorded variances on error cases, 11,899 (52%) have AMOUNT = 0; 59% of those are nature 97 (timing). Reportable variances (AMOUNT > 0): nature 97 = 19%. Variances on correct cases are negligible (4).

**Build** (`exp55_build_dist_reportable.py`). `dist_reportable.json` is a copy of `dist.json` whose variance-level tables are recomputed from AMOUNT > 0 variances on error cases: `bucket_probs` (+ earner / no-earner / the four exp11 earner×senior strata), `nature_given_bucket` (+ earner splits), `cause_given_bucket`, `p_over_97_given_bucket` (single-reportable-variance cases). Case-level rates are copied unchanged. `dist.json`, `eff.json` and `inject.json` are untouched; default generator output is unchanged.

**Calibration check** (`exp55_measure.py`, n = 30,000, seed 7, persistent pool) against real FY2024, with the primary variance defined the eval's way.

**Training test.** 4,000 / 200 finding-balanced, view-calibrated training cases from `dist_reportable.json` with FY-aware coding only (cause 26 re-drawn and natures 56/57 coded 53 for the eval's 5/6 pre-2024 share; no reweighting). Answer-only SFT, lr 1e-5, rank 16, batch 4, 500 steps; dev scores at steps 300/400/500.

### Correction (2026-10-07, later the same day)

The "zero-dollar variance" framing below is wrong. Per-variance AMOUNT = 0 is overwhelmingly a **state recording practice**: in 22 of 53 states more than half of error cases carry no per-variance amount (Texas, Georgia, Louisiana, Michigan, Ohio, Colorado, Wisconsin, Kentucky at 98–100%), while others record nearly all of them (PA, NY, Arizona, Nevada, Alaska, Delaware at 0–2%; POC states: PA 0.1%, NY 0%, ID 38%, UT 67%, SD 75%, TX 99.9%). The share is stable across FY2020–24 (45–53%). Within the 16 FY2024 states that record amounts, zero-amount variances are only 12% of the total (755 vs 5,312), and nature 97 is 31% of the amount-carrying variances.

What that means: `dist.json` pools variances from all states, while the eval's T3–T5 labels (largest AMOUNT > 0 variance) can only come from amount-recording states. `dist_reportable.json` is in effect the variance distribution of the amount-recording states. It still matches what the eval labels, so the practical result (label mix closer to the eval, LLM skill at parity) stands, but the mechanism is state composition, not "tolerance variances that are mostly timing". There is no "small timing error regime" to model in the generator; the "45% of error cases" finding below is the same recording practice.

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

**SFT dev results** (197 real items; checkpoints of a 500-step run):

| | step 300 | step 400 | step 500 |
|---|---|---|---|
| composite skill | **0.225** | 0.172 | 0.102 |
| T1 κ / accuracy | 0.523 / 79.7% | 0.409 | 0.237 |
| T2 κ | **0.323** | 0.252 | 0.181 |
| T3 κ | 0.117 | 0.105 | 0.060 |
| T4 / T5 κ | −0.003 / −0.012 | | |

vs the original recipe (all-variance `dist.json`): peaks 0.271 (seed 52, step 400) and 0.167 (seed 53, step 600). Synthetic-valid mean excess 0.150 (step 500).

**Missing-regime profile (FY2024).** 8,053 of 17,836 error cases (45%) carry no reportable variance: median AMTERR $21 (87% ≤ $56) vs $47 (55% ≤ $56) for cases with one; their variances are mostly nature 97 (6,708); over/under 4,486 / 3,567. A faithful generator is a mixture: ~45% small timing errors with no reportable variance (no T3–T5 label) and ~55% drawn from the reportable distribution. The old all-variance draw was modeling the first regime.

**Rare T3 buckets.** The six buckets the generator never produces (childsupport, assets, reporting, standard, income_total, other) are 2–3% of real reportable primaries (FY2021–24) but 30% of the eval's T3 test items (217 / 733) and 6 of its 14 macro-F1 classes, because exp30's sampler gave each bucket a quota. Adding them to the generator buys little realism and needs new household facts, benefit math and calibration per bucket.

### Verdict

Held for fidelity, parity for skill. The reportable distribution fixes the T3–T5 label mix by construction (nature 97 0.41 → 0.21 vs 0.20 real) and, with its own exp31 capture (`--calibration`), keeps the finding mix near the bar (L1 0.037). Trained on it, the LLM peaks at dev skill 0.225, inside the seed band of the original recipe (0.167–0.271): best T2 κ of any run (0.323) and best T1 accuracy (79.7%), lower T3 κ than seed 52 (0.117 vs 0.253, level with seed 53), and an earlier peak (step 300). T4/T5 stay at chance, confirming exp54. Adopted as the more faithful LLM training data; not test-gated (it doesn't clearly beat the current best, test composite 0.266, and the test set has had three looks). Dollar sizes still skew large until the no-reportable-variance regime is modeled.

### Next steps

1. ~~Score the SFT run~~ done (above). For LLM data, stop around step 300 with this distribution.
2. ~~Model the no-reportable-variance regime~~ withdrawn: it is a state recording practice (see Correction), not an error type. The state rankers use case-level AMTERR, which every state records, so they are unaffected. If per-state eval-style labels are ever needed, model it as a per-state "records variance amounts" flag.
3. Dropped from the backlog: "raise the multi-variance rate" (exp27). Only 7% of real error cases carry 2+ *reportable* variances; exp27's ~33% counted zero-dollar variances. Synthetic is already at 10%.
4. Eval decision (exp30, with the T3 bar): score T3 over the 8 modeled buckets or prevalence-weighted, rather than macro-F1 over 14 buckets where 6 are ~2–3% of reality but 30% of test items. Preferred over generator work for those buckets.
