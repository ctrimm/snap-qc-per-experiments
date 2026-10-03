# NY1: NY-conditioned SNAP QC synthetic generator

**Date:** 2026-09-29
**Status:** Complete — gates the New York chain (NY2 transfer trains on this generator).
**Deliverables (new files only; no existing file modified):**
- `src/synth/ny_state.py` — NY-conditioned generator module
- `experiments/ny1_ny_generator.py` — fit + validate harness
- `experiments/ny1_ny_generator.md` — this chronicle

## Hypothesis

Per exp33, state heterogeneity in SNAP QC errors lives in error *size*, not
just error *rate* — and New York is the sharpest illustration yet: NY errs
*less* often than national (case-weighted 36.6% vs 38.8%) but its substantive
(non-timing) errors are roughly twice as large at the median ($121 vs $56),
while its timing-97 errors run slightly *smaller* ($13 vs $15). A
NY-conditioned generator can therefore be built as **parametric offsets
applied inside the national generator's injection stage** (not post-generation
resampling), mirroring PA1's architecture: true generative NY mode, no
duplicated cases, mechanics-consistent facts→benefit math, arbitrary n/seed
for NY2. The national (default) path must stay byte-identical.

## Method

**Fit** (`python3 experiments/ny1_ny_generator.py fit`): pooled FY2020–2024 QC
public-use microdata (STATE='36', n=3,257 rows: FY2020 399 / FY2021 221 /
FY2022 896 / FY2023 856 / FY2024 885; FYWGT-weighted; microdata-implied
rates, NOT FNS-published). National reference is the same pooled microdata
basis (non-NY rows). Microdata is read-only at `snap-qc-data/` beside the
repo checkout, never copied into the repo.

NY-vs-national empirical facts (pooled, FYWGT-weighted):
- Finding c/o/u: NY 0.6345/0.2101/0.1553 vs nat 0.6122/0.2398/0.1480.
  Case-error rate 0.3655 vs 0.3878 (−0.0223); dollar rate 0.0854 vs 0.0859
  (−0.0005). NY errs less often, with a lower over share (57.5% vs 61.8%).
- P(err|earner) 0.5858 vs 0.5653 (ratio 1.0362); P(err|no_earner) 0.3075 vs
  0.3225 (ratio 0.9535). Opposite pattern to PA (PA: earner down, no-earner
  up) — NY's gap concentrates on earner strata.
- Element buckets (NY/nat): medical **1.7477**, hhcomp **1.5846**, sua 1.2056,
  unearned 1.0875, earned 1.0080, shelter **0.8105**; depcare/arithmetic → 1.0
  (sparsity guard, NY unweighted n<25: 10 and 12).
- 97-share per bucket (NY/nat): earned 1.16, unearned **2.02**, shelter
  **1.78**, sua **2.32**, medical **2.07**, depcare 1.42, hhcomp **2.62**,
  arithmetic 7.21 (tiny-n: 9 unweighted 97s — kept by the ≥5 guard).
  NY runs far more timing variances than national on every bucket.
- Direction among non-97 natures: shelter under-skewed (over 0.57x, under
  **1.59x**); sua over-skewed (over **1.55x**, under 0.49x); earned more
  over-directional (1.21x/0.92x); medical over 1.09x/under 0.79x.
- 97 resolution P(over|97): earned 1.15, sua 1.06, unearned 0.97, shelter
  0.90, medical 0.70, hhcomp 1.24, depcare 1.20, arithmetic 0.28.
- Cause: NY blanks cause on **21.9%** of timing-97 variances (vs nat 69.7%
  pooled / 32% in the generator's FY2024-calibrated wrapper) — NY records
  97 causes far more often than national. NY **never uses cause 26**
  (no-fault) on non-97 variances (0.000, all buckets — same as PA); medical
  non-97 causes are all agency-caused. NY's recorded 97 causes are
  1/12-heavy (agency), not 99-heavy like PA's.
- Dollar: p50 29 vs 28; p90 **201 vs 183**; mean **72 vs 65**; le56 0.692 vs
  0.703; medO 35/34; medU 21/21. Relative scale factors s_over=1.0294,
  s_under=1.0000 (median ratios; deliberately relative — the generator's
  national level bias stays owned by exp31).
- near-full|over: NY 0.0657 vs nat 0.0568 → p_unit unchanged.

**Conditioning** (`src/synth/ny_state.py`): `apply_ny_offsets(dist)` returns a
NY-conditioned deep copy of the adopted dist (input never mutated), applying
in order: finding-rate coin ratios × global calibration scalar; element-bucket
ratios; 97-share ratios; direction-balance ratios; 97-resolution coin ratios;
non-97 cause ratios. NY-only wrappers (installed during `generate_ny` only,
try/finally teardown): `_draw_nature` resamples 97-causes from NY's empirical
97-cause mix; `_recorded_cause` blanks 97 causes at NY's 0.2189 (consumes the
rng draw to keep the stream aligned); `_corrupt_income`/`_corrupt_deduction`
scale agency-side amount deltas by s_over/s_under per realized direction.
Importing the module installs nothing.

Unlike PA1's it1 (which fit cause ratios pooled and blew up on the blanking
interaction), NY1 started with the margin architecture throughout: cause
ratios fit on non-97 only, 97 causes resampled from NY's empirical mix —
NY's 21.9% blank rate sits between national's 32% (wrapper) and 69.7%
(pooled), so the distortion PA hit would have been milder, but the cleaner
design was used from the start.

## Results

`python3 experiments/ny1_ny_generator.py validate --qc ../snap-qc-data/raw --n 20000 --seed 7`
(NY synth vs real NY; national sanity: nat synth 0.601/0.245/0.154):

| metric | it1 | it2 (final) |
|---|---|---|
| finding L1 | 0.0422 | **0.0202** |
| element L1 | 0.0798 | **0.0439** |
| cause L1 | 0.0852 | **0.0735** |
| dollar p50 (synth/real) | 17/29 | 18/29 |
| dollar p90 (synth/real) | 189/201 | 172/201 |
| dollar mean (synth/real) | 58/72 | 57/72 |
| share ≤$56 (synth/real) | 0.731/0.692 | 0.736/0.692 |
| case-rate (synth/real) | 0.3834/0.3655 | **0.3651**/0.3655 |
| p(over\|err) (synth/real) | 0.603/0.575 | 0.602/0.575 |

(L1 = sum of absolute mix-share differences across the categories — 0 is a
perfect match. F1/AUC/GBM = gradient-boosted trees, not used in NY1.)

Iteration history:
- **it1** (pure empirical ratios, coin scalar 1.0): finding L1 0.0422 —
  already under the 0.06 gate. Cause L1 0.085 (no blanking blowup, unlike
  PA's it1 0.273 — the non-97-only cause fit + 97 resample design worked
  first try). Two gaps: the p(over|err) offset recovered only −0.0117 of
  −0.0433, and element L1 0.080 with medical/hhcomp under-recording.
- **it2** (one-step realized-output calibrations, mirroring PA1's it3):
  bucket ratios × real_NY_share/synth_share (medical 1.75→2.04, unearned
  1.09→1.18, sua 1.21→1.05, hhcomp 1.58→1.33); 97-resolution coins ×
  real/synth P(over|97,b) (sua 1.06→1.22, hhcomp 1.24→0.81); direction
  margins × real/synth on the non-97 slice — the it1 margins had overshot
  directionality on earned/unearned and undershot on shelter/medical/hhcomp,
  because materialization asymmetry eats part of the drawn margin. Per-bucket
  P(over|b) now lands within ~0.02 of real on every major bucket (shelter
  0.416 vs 0.416 exact). Coin scalar line search over {0.90, 0.93, 0.96,
  1.0}: 0.96 wins (finding L1 0.0202, case_err 0.3651 vs 0.3655 — the it1
  1.0 overshot at 0.3889 once the recalibrations raised materialization;
  unlike PA's 1.08, which fought a materialization ceiling, NY needed a
  small downward correction).

**Structural limitations (documented, not fixable within NY1's scope):**
1. Dollar p50 18 vs 29. Root cause is a NY shape fact the relative-offset
   architecture cannot express: NY's 97-driven errors are slightly *smaller*
   than national's (p50 $13 vs $15) while its non-97 errors are ~2x *bigger*
   (p50 $121 vs $56; per-bucket: unearned 3.7x, shelter 2.5x, sua 1.9x,
   earned 1.7x). A single direction-conditional scale (s_over=1.0294,
   s_under=1.0) cannot separate the two modes. The national level bias
   (synth nat p50 21 vs real 28) is exp31's territory; the remainder is the
   shape gap. If NY2's transfer needs dollar-amount fidelity, the lever is a
   97-vs-non97 (or per-bucket) dollar scale — a defined extension, not a
   calibration fix.
2. p(over|err) 0.602 vs 0.575 (+0.027): per-bucket direction landed, but the
   case-level offset recovered only −0.012 of −0.043. The margin instrument
   under-corrects (the "other"-nature mass dilutes the drawn margin). A
   damped second step was judged not worth the overfitting risk at finding
   L1 0.020.
3. Dollar-rate offset −0.0076 vs −0.0005 (synth dollars too small overall) —
   same root cause as (1).
4. The baked bucket/coin/direction ratios include the it2 realized-output
   calibration; pure empirical values are in the `fit` output and the code
   comments.

**National byte-identical:** verified — a 5k-case national run
(`python3 -m src.synth.generate`, exact CLI path incl. `enable_adopted` and
`persistent_buckets=True`) produces byte-identical output with and without
`ny_state` imported (md5-identical across three runs). Note for future
verifiers: `errors.inject` defaults `persistent_buckets=False`, so a
hand-rolled replication must pass the CLI's flags explicitly — the byte
check must replicate the exact CLI path.

## Verdict

NY1 gates the NY chain: the NY-conditioned generator reproduces NY's finding
mix (L1 0.020), element mix (0.044), cause mix (0.074), case-error rate
(0.3651 vs 0.3655), and per-bucket direction (shelter 0.416 exact), with the
national path byte-identical. The two honest residuals are the dollar level
(p50 18 vs 29 — the NY shape fact above, plus exp31's national bias) and a
+0.027 p(over|err) gap. The conditional structure (which variances, which
directions, which causes, and the 97-heavy timing profile) is faithful, which
is what NY2's transfer experiment needs.

## Next steps

- **NY2** consumes `generate_ny` (API below) for the transfer experiment:
  train on NY synth, test on real NY microdata. Suggested NY2 checks: GBM
  transfer (finding/element/nature/cause + dollar amount); seed-robustness
  (n=20k seeds 8, 9); an NY-vs-PA cross-state transfer comparison (PA2's
  protocol) to test whether state-conditioned training beats pooled.
- If dollar-amount transfer underperforms, the defined lever is a
  97-vs-non97 (or per-bucket) dollar scale in the corruptor wrapper —
  NY's substantive errors are 1.1–3.7x national per bucket, which no
  direction-conditional scale can express.
- If p(over|err) fidelity becomes binding, a damped second-step direction
  calibration is staged (residual factors are ~0.92–1.10 per bucket).

## NY2 API (copy-paste)

Python:
```python
from src.synth.ny_state import generate_ny
generate_ny(n=20000, seed=7, dist="experiments/dist.json", out="data/ny_synth.jsonl")
# returns the output path; each case dict matches the national schema plus "state": "NY"
```

Shell:
```bash
python3 -m src.synth.ny_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out data/ny_synth.jsonl
```

Reproduce the fit (provenance of every baked constant):
```bash
python3 experiments/ny1_ny_generator.py fit
```

Re-run validation:
```bash
python3 experiments/ny1_ny_generator.py validate --qc ../snap-qc-data/raw --n 20000 --seed 7
```
