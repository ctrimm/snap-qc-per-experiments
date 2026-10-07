# Experiment 26 — Combine exp23's dollar mechanisms with exp24's defaults
**Date:** 2026-09-29 · **Code:** `experiments/exp26_combine_dollar.py` · **Module edits:** `src/synth/dollar_mech.py` (additive only; `src/synth/errors.py` untouched)

### Hypothesis
North-star gate: **calibration** — the synthetic finding mix and dollar-error marginal must stay near the real QC distributions, or anything trained on the generator inherits the drift. Exp23 merged the dollar mechanisms (97-conditional small-error mode, whole-unit ineligibility, coarse-under rescale) and recalibrated, which fixed the dollar marginal but regressed the finding mix (L1 0.028 → 0.053) — and it ran on pre-exp24 defaults. Exp24 then changed the draw (`ZERO_BASE_WEIGHT={}` + per-(bucket,stratum) materialization matrix, finding L1 0.025). This combination is untested. The bet: implementing exp23's precise three-part fix — (a) recode the whole-unit mechanism as earned-income zeroing → (311, 35) with the unit mass subtracted from the empirical targets, (b) a direction-aware phase-1 injection coin (separate over/under targets) to offset the mechanical unit over-contribution, (c) larger small-error magnitudes for unders — and re-deriving effectiveness plus recalibration *under the exp24 defaults* recovers the finding mix (L1 ≤ 0.030) while keeping dollar marginals at least as good as exp23's treatment.

Plain-language glossary (see terms.md): **L1 distance** = total probability mass you'd have to move to make two distributions match (0 = identical). **Materialization** = a drawn corruption actually moves the computed benefit (some are absorbed by floors/caps and vanish). **Injection coin** = per-case probability of attempting any error variance. **Residual pool** = cases not taken by the whole-unit draw. **Importance weights** (`dir_weight`) = draw-time corrections so the *recorded* mix lands on the empirical mix despite some directions materializing more often than others.

### Method
**Module edits** (`src/synth/dollar_mech.py`, additive; `enable()`/`disable()` idempotent pattern kept):
- (a) Whole-unit recode: the mechanism now records **(element 311, nature 35, bucket "earned")** instead of (150, 99, "hhcomp") — the real file codes near-full-benefit overs as earned-income variances (311 / natures 35/38/39/37), not hhcomp/99, which is what drove exp23's element-L1 regression (0.068 → 0.149). New `apply_unit_bucket_correction(dist, p_unit, variances_per_case)`: scales the earned draw weight by (1 − unit_share/earned_share) in every bucket mix — the double-counting guard, since the real whole-unit mass already lives in the empirical earned mix (fitted factor: **0.8744**, from V = 0.394 recorded variances/case in the pre-pass).
- (b) New `apply_direction_balance(dist, boost_over, boost_under)`: folds over/under draw multipliers into `dir_weight` (the timing-97 "other" class is untouched — 97 direction is owned by the phase-2 resolution coin). The phase-1 calibration then targets **separate residual rates** — over = (0.239 − p_unit)/(1 − p_unit) = 0.2295, under = 0.158/(1 − p_unit) = 0.1602 — so mechanism 2's mechanical over contribution is subtracted before fitting, not baked in.
- (c) Small-error mode is now direction-aware: under-direction perturbations draw U($20, $80) on the amount (both paths) instead of $2–30. The pass-through correction that motivated this: I first assumed deductions pass through ~1:1 and sized a smaller deduction range, then measured the benefit formula directly — the benefit is `max_allotment − 0.3 × net_income` on *both* paths (income: 0.8 × 0.3 = 0.24 after the earnings disregard; deductions: 0.3 when they bite, 0 at the shelter cap). So $20–80 → ~$5–24 benefit deltas, centering near the real 97-under median ($15). Overs keep $2–30 (deliberately: raising them would break the p10 bar).

**Script** (`experiments/exp26_combine_dollar.py`): stock-baseline arm first, then treatment, on paired seeds (7, 8, 9), 20k cases each. Recalibration under exp24 defaults, all in-memory (committed `eff.json`/`inject.json`/`dist.json` untouched): 30k-case pre-pass → fit mechanism-4 scales → `enable(under_scale=...)` → re-measure effectiveness **after** mechanism 4 is on (exp23's subtlety), with exp23's minor next-step-4 fix (bucket drawn from the applicable mix, not uniformly) → earned-bucket correction → phase-2 97-coin refit → direction-balance fit (2 multiplicative updates, [0.5, 2.0] trust region) → direction-aware phase-1 coins. Real QC microdata read for aggregate comparison only.

Tree-state note: a parallel worker's exp29 household-sampler change (stratum-conditioned base positivity for unearned/shelter/sua in `src/synth/household.py`) landed in the working tree *before* the full runs below. Both arms are paired on the identical sampler, so the treatment-vs-baseline comparison is valid — but the "stock baseline" is stock-injector + exp24 draw defaults + exp29 sampler, and comparisons to exp23/exp24 historical numbers carry that confound. I did not touch exp29's files.

### Results
Fitted values: mechanism-4 scales 44 → 0.651, 57 → 0.311, 52 → 0.587; direction boosts → (over 0.686, under 0.959); phase-1 coins earner 0.9308 / no-earner 0.8772; 97-resolution coins refit per bucket (e.g. earned 0.614, shelter 0.394).

**Dollar-error marginal (absolute $, error cases) — jointly with the finding mix:**

| stat | real FY2024 | baseline | treatment |
|---|---|---|---|
| p10 / p25 / p50 | 4 / 11 / 31 | 22 / 42 / 75 | 4 / 8 / 21 |
| p90 / p99 | 201 / 528 | 202 / 316 | 186 / 510 |
| mean | 71 | 95 | 64 |
| share ≤ $56 | 0.70 | 0.36 | 0.69 |

**Over/under asymmetry (median / mean / p90 / p99, sign correct?):**

| | real | baseline | treatment |
|---|---|---|---|
| median over / under | 38 / 23 | 72 / 83 (inverted) | 28 / 19 |
| mean over / under | 86 / 49 | 93 / 101 (inverted) | 73 / 48 |
| p90 over / under | 244 / 128 | 197 / 206 (inverted) | 198 / 159 — inversion fixed |
| p99 over / under | 603 / 361 | 330 / 277 | 661 / 244 |

**Finding mix (correct / over / under):**

| | correct | over | under | L1 vs real |
|---|---|---|---|---|
| real | 0.603 | 0.239 | 0.158 | — |
| baseline (exp24 defaults) | 0.597 | 0.261 | 0.142 | 0.045 |
| treatment | 0.601 | 0.247 | 0.152 | **0.016** (per-seed 0.011–0.023) |

**Element mix — no regression from the recode:** element L1 0.105 (baseline) → **0.060** (treatment); exp23's miscoding had driven 0.068 → 0.149. Recorded earned lands 0.248 vs 0.253 empirical — the unit-bucket correction works (without it, earned would carry ~+2.8pp of double-counted unit mass). Whole-unit cases: 721/60,000 = 0.0120 (target p_unit = 0.0125).

**Per-nature under medians (single-variance cases):** 44: 41 vs 41 real; 57: 18 vs 14; 52: 75 vs 59 (overshoots); **97-under: 15 vs 14 real** (was $8 in exp23 — the small-under fix verified); 97-over: 5 vs 18 real (kept small by design).

**Recalibration diagnostics:** the direction-balance fit moved residual under 0.157 → 0.169 (target 0.1602 ✓) but residual over only 0.279 → 0.264 (target 0.2295) — the over instrument is inelastic: ~1/3 of residual overs carry a 97 variance (phase-2 coin, untouched by boosts) and over-direction corruptions materialize better. The coined eval nevertheless landed at residual over 0.238 / under 0.154, close to targets. Open question (recorded, not blocking): the forced-injection boost-fit measurement reads ~2.6pp more over than the coined eval on the same fitted dist — the leading hypothesis is stratum-dependent direction mixes (forced: over|earner 0.423 / over|no-earner 0.205) interacting with the per-stratum coins, but this is unverified; a per-stratum direction fit or more boost iterations is the follow-up.

Footnote: the script prints "full-unit share of overs: 0.000" — that is the strict FSBEN==0 definition, which finds nothing in the file. The mechanism targets exp18's 4.9% of overs with AMTERR ≥ 0.9 × RAWBEN (p_unit = 0.0125 ≈ 5.2% of overs). The two definitions differ; the print is not evidence against the mechanism.

### Verdict
Hypothesis **holds**. Finding L1 = 0.016 ≤ 0.030 (per-seed 0.011–0.023 — also better than the exp24 stock baseline's 0.045 and exp23's treatment 0.053), and dollar marginals are at least as good as exp23's treatment on every bar: share ≤$56 = 0.69 ≥ 0.60 (exp23: 0.67), p90 inversion fixed (198/159 vs exp23's 190/156), p10 = 4 ≤ 8 (exp23: 2; real: 4). Strictly better than exp23's treatment on p10/p25/p50/p90, the ≤$56 share, and the under median ($19 vs $8, real $23). Neither half failed. The three-part fix composes cleanly under the exp24 defaults: the (311, 35) recode + unit-mass subtraction repaired both the over excess and the element-L1 regression, the direction-aware phase-1 landed the finding mix, and the pass-through-corrected small-unders repaired the collapsed under median without breaking the ≤$56 share.

### Next steps
1. (Staged, coordinator's call) Adopt the exp26 mechanism set + recalibrated dist as the generator's dollar baseline (currently flag-gated in `dollar_mech`; `generate.py` has no `--dollar-mechanisms` flag — wiring one in is the adoption step).
   - **Done →** [exp31](exp31_adopt_dollar.md): Adopted: `--dollar-mechanisms` on by default, recalibration baked in.
2. Resolve the forced-vs-coined direction-measurement gap: run more boost iterations and/or fit the direction balance per stratum (earner cases are far more over-prone: 0.423 vs 0.205 residual).
3. Re-run the transfer battery (exp19/exp24 arms) on the treatment dist — the label priors shifted (many more small errors, recoded unit cases as earned/35); check element accuracy/macroF1 before any LM pretraining consumes this mix.
   - **Done →** [exp31](exp31_adopt_dollar.md): Transfer battery re-run on the adopted mix: macroF1 cost −0.003 (acceptable).
4. 52-under median overshoots (75 vs 59 real): revisit the 52 scale (0.587) or the non-97 small-mode residual on 52s.
5. Optional, now that p10 has headroom (4 vs the 8 bar): a small bump to the 97-over small-mode range to lift medO (28 vs 38 real) — trades p10 for the over median, so gate it on the same four bars.
