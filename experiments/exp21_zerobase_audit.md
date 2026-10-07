# Experiment 21 — zero-base weight double-counting audit
**Date:** 2026-09-29 · **Code:** `experiments/exp21_zerobase_audit.py`

## Hypothesis
North-star gate: calibration. Exp20 showed the scalar per-bucket
effectiveness was masking a draw-side distortion: `_applicable_buckets`
multiplies the empirical stratum mix by `ZERO_BASE_WEIGHT` (earned ×0.018,
unearned ×0.091, shelter ×0.227 on zero bases), but the empirical stratum
mixes *already reflect* real zero-base households — the same double-counting
exp11 diagnosed and fixed for medical (medical 0.11x → 0.67x). Removing
earned/unearned/shelter from `ZERO_BASE_WEIGHT` should fix the draw-side
distortion (earned/unearned/shelter → 1.0x, sua deflates → 1.0x), and
re-applying the exp20 per-(bucket, stratum) materialization matrix on the
corrected draw should then move hhcomp/arithmetic → 1.0x and finding L1
below the 0.036 baseline.

Glossary for this chronicle: *draw* = picking a variance's bucket from the
weighted mix; *materialization* = a drawn corruption moves the computed
benefit and is recorded (terms.md); *keep rate* = P(materialize | drawn);
*per-case ratio* = the chronicle convention since exp7 (synthetic
count/cases over real count/cases; 1.0x = matches real); *finding L1* = how
far the synthetic finding mix (correct/over/under) is from the real mix —
lower is better (terms.md); *double-counting* = applying a correction for
something the empirical data already accounts for, suppressing it twice.

## Method
All in-process; only this script and chronicle are written, no repo files
touched, nothing committed. `generate.py` is unmodified; the
`ZERO_BASE_WEIGHT` swaps happen through a context manager (the generator
default is untouched — same explicit-flag spirit as
`--no-persistent-buckets`). Real QC microdata is read for aggregate
comparison only.

1. **AUDIT:** quantified the double-count two ways. Analytically: sampled
   100k synth households (seed 5) for per-stratum base positivity, giving
   the implied average draw multiplier M[b][s] = P(base>0) +
   P(base=0)·w_b (1.0 = no distortion). By simulation: measured the actual
   drawn bucket mix per stratum under the current weights (40k cases,
   seed 13, monkeypatched `_inject_persistent` attributing draws to
   stratum, as in exp20) and divided by the empirical stratum mix.
   Also read real per-stratum base positivity (FSEARN/FSUNEARN/FSSLTEXP/
   UTIL) and the real arithmetic per-case rate by stratum, aggregates only.
2. **BEFORE:** 20k cases, seed 7, current generator (replicates exp20).
3. **DAMPED:** `ZERO_BASE_WEIGHT` entries square-rooted (partial-removal
   probe — exp13-style damping of the suppression toward 1.0), 20k seed 7,
   paired rng stream.
4. **REMOVED:** `ZERO_BASE_WEIGHT = {}` (the exp11 medical precedent), 20k
   seed 7, paired.
5. **REMOVED+EXP20MAT:** corrected draw + exp20's original measured matrix
   (transcribed from the exp20 chronicle), 20k seed 7 — tests whether the
   matrix transfers across the draw fix.
6. **REMOVED+NEWMAT:** keep rates re-measured under the corrected draw
   (60k, seed 11), then the damped (0.8) matrix applied with exp20's
   guardrails (mechanics-gap fallback, 2.5x trust-region cap), 20k seed 7.
7. Compared per-case element ratios, share ratios, and finding L1 at each
   step.

## Results

**The audit: the double-count is real, and bigger than the task framed it.**
Simulated drawn/empirical share ratios under the current weights (1.0 =
draw matches the empirical mix):

| stratum | earned | unearned | shelter | sua | medical | depcare | hhcomp | arith |
|---|---|---|---|---|---|---|---|---|
| no_earner_nonsenior | 0.03 | 0.46 | 1.33 | 2.21 | 1.39 | 0.67 | 1.10 | 0.72 |
| earner_nonsenior | 0.95 | 0.29 | 1.38 | 2.20 | 1.96 | 0.64 | 1.14 | 0.70 |
| no_earner_senior | 0.03 | 0.65 | 1.05 | 1.81 | 1.10 | 0.47 | 0.90 | 0.50 |
| earner_senior | 0.87 | 0.62 | 1.47 | 1.87 | 1.34 | 1.15 | 0.78 | 0.33 |

Implied average draw multipliers M (1.0 = undistorted): earned 0.018 on
no-earner strata (1.0 on earner strata — the base defines the stratum);
unearned 0.33–0.86; shelter 0.71–0.78. The analytic cross-check
(mix × M / eff_b) agrees directionally; where it differs (depcare,
medical on earner_nonsenior) the cause is depcare's kid-household gating,
which the analytic ignores — the simulation is authoritative.

Two refinements to the exp20 diagnosis: (a) shelter draws are *not*
suppressed — they sit at/above empirical (1.05–1.47x) because the 1/eff_b
scalar (3.08x) overcompensates M≈0.72; shelter's 0.74x recorded shortfall
is a keep-rate problem (0.21–0.68 by stratum), not a draw problem.
(b) sua draws are inflated ~2x and medical ~1.1–2.0x — the suppression of
earned/unearned renormalizes the whole mix upward for never-scaled
buckets. Arithmetic is *under*-drawn (0.33–0.72x); its 1.51x recorded
overage comes from always materializing (m=1.0) while competitors' draws
fail to materialize — a materialization-side win in a distorted draw.

Real per-stratum base positivity vs the synth household sampler
(aggregates only): unearned matches well except seniors (real 0.95/0.81 vs
synth 0.84/0.67); shelter is low in synth for earner/senior strata (real
0.88/0.91/0.95 vs synth 0.63/0.64/0.72); sua is flat 0.72 in synth vs
0.46–0.88 in real. These are household-sampler gaps, separate from the
draw-weight issue — the draw target is the marginal empirical mix either
way — but they are real calibration-relevant gaps for a follow-up.

**Step-by-step effects** (per-case ratios; 1.0x = matches real):

| bucket | BEFORE | DAMPED | REMOVED | REMOVED+EXP20MAT | REMOVED+NEWMAT |
|---|---|---|---|---|---|
| earned | 0.84x | 0.78x | 0.79x | 0.79x | 0.80x |
| unearned | 0.77x | 0.82x | 0.93x | 0.81x | 0.94x |
| shelter | 0.74x | 0.84x | 0.88x | 0.84x | 0.83x |
| sua | 1.04x | 0.96x | 0.91x | 1.06x | 0.90x |
| medical | 0.69x | 0.61x | 0.50x | 0.52x | 0.53x |
| depcare | 0.50x | 0.43x | 0.35x | 0.44x | 0.41x |
| hhcomp | 1.59x | 1.37x | 1.11x | 1.01x | 1.08x |
| arithmetic | 1.51x | 1.34x | 1.10x | 0.92x | 0.95x |
| finding L1 | 0.036 | 0.027 | 0.024 | 0.032 | 0.025 |
| nature-57 share | 0.98x | 1.18x | 1.20x | 1.21x | 1.16x |

Finding mixes (real: 0.603/0.239/0.158): BEFORE 0.615/0.245/0.140,
DAMPED 0.612/0.244/0.145, REMOVED 0.600/0.251/0.149,
REMOVED+EXP20MAT 0.619/0.238/0.143, REMOVED+NEWMAT 0.608/0.247/0.146.

**The partial-removal probe is monotonic** (L1 0.036 → 0.027 → 0.024):
the improvement scales with how much suppression is removed, which pins
the causal attribution on the weights rather than on rng noise.

**The stale matrix does not transfer.** REMOVED+EXP20MAT re-inflates sua
to 1.06x and finding L1 back to 0.032: the old matrix was measured under
the distorted draw and its sua upweighting re-creates the inflation the
draw fix removed. Re-measuring under the corrected draw fixes it
(REMOVED+NEWMAT: L1 0.025, sua 0.90x, arithmetic 0.95x, hhcomp 1.08x).
This refines exp20's invariance finding: keep rates are invariant to draw
*weight* changes that preserve within-cell household composition, but
removing the weights changes the zero-base/positive-base composition
inside cells — unearned/no_earner_nonsenior's keep rate moved 0.81 →
0.65, and the previously unmeasurable earned/no_earner_senior cell went
0.02 (clipped, 0/1 draws) → 0.723 with real sample size. Everything else
moved ≤0.05.

**Honest debits.** Earned did *not* move toward 1.0x (0.84x → 0.80x):
its draws are dominated by earner strata where M was already 1.0, and the
restored competitors dilute its share slightly — earned's ~0.8x has a
separate, non-draw-side constraint. Medical (0.69x → 0.53x) and depcare
(0.50x → 0.35x) relatively deflate: they were never scaled, so restoring
competitors' draw mass deflates their shares — a shares-game cost of the
fix. Nature-57's share inflates (0.98x → 1.16x) as shelter/earned draws
recover under the exp13 57-weights. Net finding L1 still improves
(0.036 → 0.025).

**Arithmetic fallback diagnosis.** Real data gives no basis for gating
arithmetic: its per-case rate is essentially flat across strata
(0.0081/0.0095/0.0095/0.0101). The `if not cands` fallback in
`_applicable_buckets` never fires under current weights (all weights >
0) — "always-applicable" means arithmetic is never down-scaled, so it
absorbs relative share when competitors are suppressed, and its m=1.0
lets it win the recorded mix. Fixing the draw rebalances the mix and
arithmetic falls to 0.95–1.10x with no gating. No gating is needed or
justified.

## Verdict
**Largely held.** The double-counting diagnosis is confirmed and
quantified: earned draws collapsed to 3% of empirical in no-earner
strata, unearned to 29–65%, sua inflated ~2x. Removing the three entries
(the exp11 precedent) fixes the draw side — unearned 0.77x → 0.94x,
shelter 0.74x → 0.83x, sua 1.04x → 0.90x — and the re-measured matrix on
the corrected draw lands hhcomp at 1.08x, arithmetic at 0.95x, finding L1
at 0.025, below the 0.036 target. The draw fix alone does most of the
work (L1 0.024); the re-measured matrix adds balance on the two problem
buckets. Exceptions, all reported above: earned is insensitive to this fix
(~0.8x throughout — separate constraint); medical/depcare relatively
deflate and nature-57 inflates as shares-game costs; the exp20-original
matrix must *not* be reused — it has to be re-measured on the corrected
draw.

## Next steps
1. **(recommended)** Adopt the draw fix in `errors.py` — delete the
   earned/unearned/shelter entries from `ZERO_BASE_WEIGHT`, extending the
   exp11/exp12 comment — plus the re-measured per-(bucket, stratum) matrix
   from this experiment, then re-run the golden calibration eval and the
   transfer evals to confirm nothing regressed. (Changing the generator
   default alters other experiments' baselines, so this needs an explicit
   go-ahead; the old behavior remains reproducible via the script's
   patch pattern.)
   - **Done →** [exp24](exp24_adopt_rebaseline.md): Draw fix adopted as default and re-baselined (finding L1 0.036 → 0.025).
2. Earned ~0.8x stickiness: separate audit — the constraint is not
   draw-side zero-base; likely keep-rate or nature-mix.
   - **Partly done →** [exp27](exp27_earned_audit.md): Earned audit found the constraint is the first-variance bucket mix; fix staged pending direction recalibration (exp45).
3. Medical/depcare relative deflation and nature-57 inflation: revisit
   whether the empirical mixes or the exp13 57-weights need
   re-measurement under the corrected draw.
   - **Done →** [exp28](exp28_shares_game.md): Nature-57 weights re-measured (1.16x → 1.03x), depcare kid-gate fixed (0.44x → 0.89x).
4. Household sampler base-positivity gaps (shelter/sua for senior
   strata, sua for no_earner_nonsenior) as a sampler follow-up; they do
   not change the draw-fix conclusion but matter for calibration.
   - **Done →** [exp29](exp29_sampler_positivity.md): Sampler base-positivity fixed: worst per-stratum gap 0.009.
