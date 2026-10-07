# Experiment 11: senior-conditioned bucket mixes

## Hypothesis
North-star gate: calibration. The medical element residual (0.11x) is a DRAW
problem: the bucket mix is conditional on earner status only, but real
P(medical variance) is 0.109 on (no-earner, senior/disabled) vs 0.048 on
(no-earner, non-senior). Conditioning the draw on senior/disabled status will
move medical toward ~1.0x without regressing the finding mix.

## Method
1. Measured the real FY2024 bucket mix in 4 strata — (earner/no-earner) ×
   (senior-or-disabled/neither) — from held-out QC microdata (senior =
   FSNELDER > 0 or any SSI receipt; never committed).
2. Stored as `bucket_probs_given_{earner,no_earner}_{senior,nonsenior}` in
   dist.json (restricted to the 8 modeled buckets, renormalized);
   `_applicable_buckets` now picks the stratum from `facts`.
3. **Key diagnosis:** the senior conditioning alone moved medical only
   0.11x → 0.24x. The bigger suppressor was `ZERO_BASE_WEIGHT["medical"]
   = 0.087` — applied ON TOP of the empirical stratum mix, double-counting
   the base-rate suppression (the empirical mix already reflects real
   zero-base households). Removed medical from `ZERO_BASE_WEIGHT`.
4. Recalibrated effectiveness + injection coins (both modes); regenerated
   20k, seed 7, persistent (default) vs retry-loop baseline.

Real 4-stratum medical shares: no_earner/senior 0.089, no_earner/nonsenior
0.055, earner/senior 0.032, earner/nonsenior 0.002.

## Results
| element | persistent before | persistent after | baseline after |
|---|---|---|---|
| medical | 0.11x | **0.67x** | 0.61x |
| hhcomp | 1.16x | 1.91x | 3.48x |
| arithmetic | 1.51x | 1.44x | 3.32x |
| finding L1 | 0.044 | 0.046 | 0.011 |

Medical improved 6x (0.11x → 0.67x). Finding L1 stable (persistent 0.046;
retry-loop baseline actually improved to 0.011).

## Verdict
**Partially held.** The senior conditioning + zero-base fix moved medical
from 0.11x to 0.67x — the draw-problem diagnosis was correct. But hhcomp
regressed (1.16x → 1.91x persistent): the no_earner/nonsenior stratum carries
hhcomp=0.056 empirically, and the persistent materialization over-converts
those draws. The stratum mixes are empirical (correct); the residual is a
materialization-rate problem, not a draw problem.

## Next steps
1. hhcomp materialization audit: why do 0.056-drawn hhcomp attempts
   materialize at 1.91x? Likely the persistent single-apply over-converts
   vs the retry loop's feasibility filter.
   - **Done →** [exp14](exp14_materialization_correction.md), [exp21](exp21_zerobase_audit.md): hhcomp over-materialization traced to the zero-base double-count; removing it took hhcomp 1.59x → 1.11x.
2. Exp12 (depcare 0.03x) and exp13 (57 residual) remain queued; exp14 (SUA)
   may interact with the shelter/sua bucket weights.
   - **Done →** [exp12](exp12_kid_depcare.md), [exp13](exp13_nature57_weights.md): Depcare 0.03x → 0.56x (exp12) and nature-57 0.50x → 1.04x (exp13).
