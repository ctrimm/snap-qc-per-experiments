# Experiment 23 — Merge exp18's dollar mechanisms and recalibrate injection
**Date:** 2026-09-29 · **Code:** `experiments/exp23_merge_recalibrate.py` · **Module:** `src/synth/dollar_mech.py`

### Hypothesis
Experiment 18 verified three mechanisms behind the synthetic generator's dollar-error mismatch (too few small errors, a missing p90 over/under inversion, wrong per-nature under medians). This experiment merges the working mechanisms — (1) a 97-conditional small-error mode, (2) whole-unit ineligibility cases, and (4, new) rescaling coarse under magnitudes to real per-nature medians — and recalibrates the injection weights under the new mechanisms. The bet: the merged mechanisms plus recalibration restore the **finding mix** (correct / overissuance / underissuance) toward the real 60.3 / 23.9 / 15.8 while keeping the fixed dollar-error marginal. This targets the **calibration gate** (north star gate 1): synthetic marginals must stay near the real QC distributions or anything trained on the generator inherits the drift.

### Method
- New additive module `src/synth/dollar_mech.py` formalizes the mechanisms behind `enable()` / `disable()` (idempotent, default off, no import side effects; `src/synth/errors.py` untouched). Mechanism 4 is a post-hoc rescale of the coarse corruption delta on under-leaning natures only.
- New script `experiments/exp23_merge_recalibrate.py` with a `--dollar-mechanisms` CLI flag (default off = stock baseline). Runs baseline and treatment on paired seeds (1000/1001/1002, 20k cases each).
- Recalibration is an in-memory port of `experiments/measure_effectiveness.py` + `experiments/calibrate_injection.py` (committed `eff.json` / `inject.json` are NOT rewritten). Phase 1 fits a unit-aware injection coin: `coin = (empirical − p_unit) / ((1 − p_unit) × m)`, where `p_unit` is the whole-unit case rate and `m` is the measured materialization rate. Phase 2 refits the per-bucket 97-resolution coins. A 30k-case pre-pass fits the mechanism-4 rescale factors.
- One subtlety found in testing: effectiveness must be measured *after* enabling mechanism 4, because the rescale changes materialization rates; measuring before distorts the bucket mix.
- Validation is against real FY2024 QC public-use microdata (held-out; aggregates only, never written to the repo).
- Key terms: **L1 distance** is the sum of absolute differences between two distributions (0 = identical). **Materialization** = a drawn error actually changes the computed benefit (some drawn errors are absorbed by benefit floors/caps and leave no trace). **Importance weights** (`dir_weight`) = correction factors that make rarely-materializing error directions get drawn more often, so the recorded mix lands on the empirical one.

### Results
Fitted mechanism-4 rescale factors: nature 44 → 0.82, nature 57 → 0.25 (hit the floor), nature 52 → 0.541.

**Dollar-error marginal (errors only) — the win:**

| stat | real FY2024 | baseline | treatment |
|---|---|---|---|
| p10 / p25 / p50 | 4 / 11 / 31 | 22 / 43 / 78 | 2 / 5 / 19 |
| p90 / p99 | 201 / 528 | 202 / 311 | 181 / 530 |
| mean | 71 | 91 | 63 |
| share ≤ $56 | 0.70 | 0.36 | 0.67 |

**Over/under asymmetry (median / mean / p90 / p99, sign correct?):**

| | real | baseline | treatment |
|---|---|---|---|
| median over / under | 39 / 23 | — | 27 / 8 |
| p90 over / under | 244 / 128 | inverted (exp18) | 190 / 156 — **inversion fixed** |

Per-nature under medians land: nature 44: 45 vs 41 real; nature 57: 12 vs 14; nature 52: 61 vs 59.

**Finding mix (correct / over / under) — the miss:**

| | correct | over | under | L1 vs real |
|---|---|---|---|---|
| real | 0.603 | 0.239 | 0.158 | — |
| baseline | 0.610 | 0.245 | 0.144 | 0.028 |
| treatment | 0.599 | 0.266 | 0.136 | 0.053 |

Element-label L1 regressed: 0.068 → 0.149 (household-composition share 0.064 vs 0.027 real; shelter 0.273 vs 0.325).

**Ablation (mechanisms on, no recalibration):** 0.666 / 0.234 / 0.100, L1 = 0.126. Recalibration is doing heavy lifting — without it the small-error mode's attrition collapses the error rate.

### Verdict
Hypothesis **partially held**. The merged mechanisms + recalibration fix the dollar-error marginal (share ≤ $56: 0.36 → 0.67 vs 0.70 real; p99 530 vs 528; the p90 over/under inversion is resolved; per-nature under medians land). But the finding mix is **not** recovered — it regresses (L1 0.028 → 0.053), driven by a persistent underissuance shortfall (0.136 vs 0.158 real) and excess overissuances (0.266 vs 0.239).

Diagnosis, each piece verified by a targeted measurement:
1. **The recalibration works for the total error rate** (correct 0.599 vs 0.603 real; without it, 0.672). The residual problem is the *direction split*, not the volume.
2. **The unit mechanism adds +1.24pp of pure over mechanically** (747/60,000 cases), and the phase-1 injection coin is direction-blind, so nothing offsets it.
3. **Double-counting.** Real near-full-benefit overs are 4.9% of real overs (529/10,734) and are coded as *earned income* (element 311, natures 35/38/39/37) — not as household-composition/nature-99, which is how mechanism 2 records them. The empirical variance mix therefore already contains the real whole-unit mass, and mechanism 2 adds it a second time. This miscoding also drives the element-L1 regression.
4. **Small-mode under attrition.** The 97-conditional small-error mode produces tiny unders that die at the $23 minimum-benefit floor (overall under median collapses to $8 vs $23 real). The variance-level importance weights compensate in *draw* counts but the finding-level under stays short — and the baseline already had a mild under shortfall (−1.4pp), so the mechanisms deepen a pre-existing bias rather than creating it.
5. **Ruled out:** stale nature-57 weights (disabling changes L1 0.054 → 0.055) and the (household × bucket) mismatch in the effectiveness measurement (fixing it changes eff values substantially but moves finding L1 only 0.053 → 0.052).

Net: the dollar distribution is now the closest it has ever been, but the finding-mix gate needs the direction split fixed, not just the volume.

### Next steps
1. **(Recommended next run)** Recode mechanism 2 as earned-income zeroing → (element 311, nature 35), matching how the real file codes whole-unit overs, *and* subtract the whole-unit mass from the empirical direction targets so it is not double-counted. Expected to repair both the over excess and the element-L1 regression.
2. Make the phase-1 coin direction-aware (separate over/under injection targets) so the mechanical unit over-contribution can be offset instead of baked in.
3. Revisit the small-error mode's magnitude for 97-unders (real median $14 vs small-mode $1–9) to repair the collapsed under median without re-breaking the ≤$56 share.
4. Minor: fix the effectiveness measurement to draw buckets from the applicable mix (matches the injector); verified low-impact but removes a known bias.
