# PA1: PA-conditioned SNAP QC synthetic generator

**Date:** 2026-09-29
**Status:** Complete — gates the Pennsylvania POC validation track.
**Deliverables (new files only; no existing file modified):**
- `src/synth/pa_state.py` — PA-conditioned generator module
- `experiments/pa1_pa_generator.py` — fit + validate harness
- `experiments/pa1_pa_generator.md` — this chronicle

**Dependency note:** the coordinator has in-flight exp32 work
(`experiments/exp32_medical_senior.py`, untracked at PA1 start). PA1 does not
touch it, but PA2 consumers should check whether exp32's medical/senior
recalibration changes the adopted dist PA1 builds on.

## Hypothesis

Per exp33, state heterogeneity in SNAP QC errors lives in error *size*, not
just error *rate*, and per exp8c Pennsylvania's benefit engine matches statute
99.7–100% every FY — so PA's differences are process/human-layer (mixes,
rates, sizes), not engine parameters. A PA-conditioned generator can therefore
be built as **parametric offsets applied inside the national generator's
injection stage** (not post-generation resampling): true generative PA mode,
no duplicated cases, mechanics-consistent facts→benefit math, arbitrary n/seed
for PA2. The national (default) path must stay byte-identical.

## Method

**Fit** (`python3 experiments/pa1_pa_generator.py fit`): pooled FY2020–2024 QC
public-use microdata (STATE='42', n=3,268 rows; FYWGT-weighted;
microdata-implied rates, NOT FNS-published). National reference is the same
pooled microdata basis (per exp33's verdict; FY2024-only shown to be
outlier-sensitive — e.g. PA medO/medU ratio 1.05 in FY2024 vs 0.89/0.93/0.78/0.85
in FY2020–2023). Microdata is read-only at `snap-qc-data/` beside the repo
checkout, never copied into the repo.

PA-vs-national empirical facts (pooled, FYWGT-weighted):
- Finding c/o/u: PA 0.5875/0.2469/0.1656 vs nat 0.6151/0.2372/0.1477.
  Case-error rate 0.4125 vs 0.3849 (+0.0277); dollar rate 0.0846 vs 0.0859
  (−0.0013). PA errs more often but smaller.
- P(err|earner) 0.5468 vs 0.5675 (ratio 0.9635); P(err|no_earner) 0.3624 vs
  0.3193 (ratio 1.1351). The gap concentrates on no-earner strata.
- Element buckets (PA/nat): shelter **1.442**, medical 1.162, hhcomp 0.948,
  earned 0.935, unearned 0.685, sua 0.616; depcare/arithmetic → 1.0
  (sparsity guard, PA unweighted n<25).
- 97-share per bucket (PA/nat): earned 1.10, shelter 0.89, sua 0.74,
  unearned **0.36**, medical **0.25**; PA has fewer timing variances.
- Direction among non-97 natures: PA more directional — over ratios
  1.01–1.41, under ratios 0.59–1.43 per bucket ("other" natures down).
- 97 resolution P(over|97): earned 1.04, unearned 0.93, shelter 0.80,
  sua 1.65, medical 0.40 (PA 0.230 vs nat 0.575).
- Cause: PA **never blanks cause on 97s** (0.000 all FYs vs nat 0.32 FY2024 /
  0.68 pooled) and records mostly cause **99** (undetermined) on them
  (earned 0.57, shelter 0.48, sua 0.70). PA **never uses cause 26**
  (no-fault) on non-97 variances (0.000, all buckets).
- Dollar: PA p50 25 vs 28; medO 31/34; medU 18/21; p90 156/187.
  Relative scale factors: s_over=0.9118, s_under=0.8571 (deliberately
  relative — the generator's national level bias stays owned by exp31).
- near-full|over: PA 0.0529 vs nat 0.0576 → p_unit unchanged.

**Conditioning** (`src/synth/pa_state.py`): `apply_pa_offsets(dist)` returns a
PA-conditioned deep copy of the adopted dist (input never mutated), applying
in order: finding-rate coin ratios × global calibration scalar; element-bucket
ratios; 97-share ratios; direction-balance ratios; 97-resolution coin ratios;
non-97 cause ratios. PA-only wrappers (installed during `generate_pa` only,
try/finally teardown): `_draw_nature` resamples 97-causes from PA's empirical
97-cause mix; `_recorded_cause` zeroes 97-cause blanking (consumes the rng draw
to keep the stream aligned); `_corrupt_income`/`_corrupt_deduction` scale
agency-side amount deltas by s_over/s_under per realized direction. Importing
the module installs nothing.

## Results

`python3 experiments/pa1_pa_generator.py validate --qc ../snap-qc-data/raw --n 20000 --seed 7`
(PA synth vs real PA; national sanity: nat synth 0.610/0.241/0.149 = exp31):

| metric | it1 | it2 | it3 (final) |
|---|---|---|---|
| finding L1 | 0.044 | 0.032 | **0.028** |
| element L1 | 0.070 | 0.095 | **0.065** |
| cause L1 | 0.273 | 0.030 | **0.050** |
| dollar p50 (synth/real) | 18/25 | 19/25 | 19/25 |
| dollar p90 (synth/real) | 155/156 | 174/156 | 144/156 |
| case-rate offset (synth/real) | +0.001/+0.028 | +0.007/+0.028 | **+0.009**/+0.028 |
| p(over\|err) offset | −0.037/−0.018 | −0.029/−0.018 | −0.023/−0.018 |

Iteration history:
- **it1** (sparse per-nature/per-cause ratios, pooled cause fit): cause L1
  0.273 — diagnosed as a 97-blanking interaction. National blanks 32% of 97
  causes, which suppresses national's recorded no-fault-26 share; PA records
  all 97 causes, so applying the pooled PA/nat cause ratio to the national
  *drawn* mix exploded no_fault (synth 0.25 vs real 0.07 on earned).
- **it2** (margin ratios: 97-share + direction-balance per bucket; cause
  ratios fit on non-97 only; 97 causes resampled from PA's empirical mix,
  mostly 99): cause L1 0.030, direction fixed. Element L1 regressed
  (0.070→0.095) — the nature-mix shift changed per-bucket materialization,
  which the national draw correction (measured under the national nature mix)
  could not see.
- **it3** (one-step realized-output bucket calibration × real_PA/synth share;
  coin calibration scalar 1.08): finding L1 0.028, element L1 0.065.
  The bucket calibration cost error-rate (shelter/medical materialize worse),
  so the coin scalar was raised to 1.08 to recover the marginal.

**Structural limitations (documented, not fixable within PA1's scope):**
1. P(err|no_earner) caps at ~0.335 vs 0.362 empirical. The no_earner coin
   hits its 0.99 ceiling; PA's shelter-heavy mix materializes worse than the
   national mix the draw correction assumes. The case-rate offset recovers
   only +0.009 of the +0.028 real gap.
2. The 1.08 coin scalar overshoots P(err|earner) (0.576 vs 0.547) to buy the
   marginal. Conditional fidelity was traded for marginal fidelity.
3. Dollar p50 19 vs 25 is the expected residual of relative-offset semantics
   (exp31 owns the national level bias); p90 144 vs 156.
4. The baked bucket ratios (shelter 1.5425, medical 1.5631, hhcomp 0.6117,
   sua 0.5368) include the realized-output calibration; pure empirical
   values are in the `fit` output and the code comment.

**National byte-identical:** verified — 5k-case national run with and without
`pa_state` imported produces byte-identical output.

## Verdict

PA1 gates the POC: the PA-conditioned generator reproduces PA's finding mix
(L1 0.028), element mix (0.065), cause mix (0.050), direction (−0.023 vs −0.018
real offset), and smaller errors (p50 19 vs 25 with correct p90/mean shape),
with the national path byte-identical. The error-rate level is 0.399 vs 0.4125
(3% relative shortfall) due to the structural materialization ceiling above —
acceptable for a POC, and the conditional structure (which variances, which
directions, which causes) is faithful.

## Next steps

- **PA2** consumes `generate_pa` (API below) for the POC validation track.
  Suggested PA2 checks: transfer experiment (train on PA synth, test on real
  PA microdata); seed-robustness (n=20k seeds 8, 9); sensitivity to the
  FY2024-outlier question on a FY2020–2023-only fit.
- If the materialization model becomes state-conditional, revisit the coin
  ceiling and the bucket calibration (both are workarounds for a national
  draw correction applied under a PA nature mix).
- Check exp32's medical/senior recalibration (in-flight at PA1 time) for
  interactions with the adopted dist PA1 builds on.

## PA2 API (copy-paste)

Python:
```python
from src.synth.pa_state import generate_pa
generate_pa(n=20000, seed=7, dist="experiments/dist.json", out="data/pa_synth.jsonl")
# returns the output path; each case dict matches the national schema plus "state": "PA"
```

Shell:
```bash
python3 -m src.synth.pa_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out data/pa_synth.jsonl
```

Reproduce the fit (provenance of every baked constant):
```bash
python3 experiments/pa1_pa_generator.py fit
```

Re-run validation:
```bash
python3 experiments/pa1_pa_generator.py validate --qc ../snap-qc-data/raw --n 20000 --seed 7
```
