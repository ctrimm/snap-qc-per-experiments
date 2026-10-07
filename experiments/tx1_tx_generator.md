# TX1: TX-conditioned SNAP QC synthetic generator

**Date:** 2026-10-03
**Status:** Complete — gates the Texas chain (TX2 transfer trains on this generator).
**Deliverables (new files only; no existing file modified):**
- `src/synth/tx_state.py` — TX-conditioned generator module
- `experiments/tx1_tx_generator.py` — fit + validate harness
- `experiments/tx1_tx_generator.md` — this chronicle

## Hypothesis

Per exp33, state heterogeneity in SNAP QC errors lives in error *size*, not
just error *rate* — and Texas is a distinctive third point after PA and NY:
TX errs *more* often than national (case-weighted 43.4% vs 38.3%) but tilts
hard toward *under*issuances (51.4% over vs 62.4% national), with a lighter
error tail (p90 $149 vs $188). Its error mix is depcare-heavy (1.59x),
sua-heavy (1.22x), and medical-light (0.62x) — the inverse of NY's
medical-heavy profile — and it runs *fewer* timing-97 variances than
national (0.48-1.04x per bucket) while coding "Other" nature 99 at 4.28x
national. A TX-conditioned generator can therefore be built as **parametric
offsets applied inside the national generator's injection stage** (not
post-generation resampling), mirroring PA1/NY1's architecture: true
generative TX mode, no duplicated cases, mechanics-consistent facts→benefit
math, arbitrary n/seed for TX2. The national (default) path must stay
byte-identical.

## Method

**Fit** (`python3 experiments/tx1_tx_generator.py fit`): pooled FY2020–2024 QC
public-use microdata (STATE='48', n=3,457 rows: FY2020 612 / FY2021 182 /
FY2022 866 / FY2023 842 / FY2024 955; FYWGT-weighted; microdata-implied
rates, NOT FNS-published). National reference is the same pooled microdata
basis (non-TX rows). Microdata is read-only at `snap-qc-data/` beside the
repo checkout, never copied into the repo. Partial-year files FY2020–21 are included in
the *fit* (pooled targets need the n) but excluded from refits per the NY6
lesson — documented per-stage.

TX-vs-national empirical facts (pooled, FYWGT-weighted):
- Finding c/o/u: TX 0.5656/0.2234/0.2109 vs nat 0.6175/0.2387/0.1438.
  Case-error rate 0.4344 vs 0.3825 (+0.0519); dollar rate 0.0740 vs 0.0869
  (−0.0128). TX errs more often, with a far lower over share (51.4% vs
  62.4% — the underissuance tilt).
- P(err|earner) 0.6279 vs 0.5605 (ratio 1.1204); P(err|no_earner) 0.3363 vs
  0.3202 (ratio 1.0501). TX's gap concentrates on earner strata, like NY's.
- Element buckets (TX/nat): depcare **1.5871**, sua **1.2221**, earned
  1.1486, arithmetic 1.1180, hhcomp 0.9863, unearned 0.9757, shelter 0.8788,
  medical **0.6170**. (No sparsity-guard hits — all buckets have TX
  unweighted n ≥ 25.)
- 97-share per bucket (TX/nat): earned 1.04, unearned 0.80, shelter 0.56,
  sua 0.48, medical 0.82, depcare 0.70, hhcomp/arithmetic → 1.0 (tiny-n
  guard). TX runs *fewer* timing variances than national on most buckets —
  the opposite of NY's 1.2-2.6x timing-heavy profile.
- Direction among non-97 natures: under-skewed across buckets (over
  0.29-0.73x, under up to **1.91x** on medical). The under tilt is
  TX's signature directional fact.
- 97 resolution P(over|97): earned 0.94, unearned 0.70, shelter 0.92, sua
  0.97, medical 0.92, depcare 1.14, hhcomp/arithmetic → 1.0 (tiny-n).
- Cause: TX blanks cause on **79.95%** of timing-97 variances (vs nat 64.4%
  pooled) — and every recorded 97 cause is raw code 26 (no-fault),
  verified 180/180 directly against the microdata. TX essentially never
  uses cause 26 on non-97 variances (0.0 on 7 of 8 buckets); non-97 causes
  skew agency-side (agency 1.24x national overall).
- Dollar: p50 27 vs 28; p90 **149 vs 188**; mean **58 vs 66**; le56 0.743
  vs 0.699; medO 30/34; medU 25/20. Relative scale factors s_over=0.8824,
  s_under=1.2500 (median ratios; deliberately relative — the generator's
  national level bias stays owned by exp31).
- near-full|over: TX 0.0225 vs nat 0.0599 → p_unit unchanged (documented
  structural residual: TX's whole-unit tail is smaller, but re-deriving
  the unit-bucket correction is out of TX1 scope).

**Conditioning** (`src/synth/tx_state.py`): `apply_tx_offsets(dist)` returns
a TX-conditioned deep copy of the adopted dist (input never mutated),
applying in order: finding-rate coin ratios × global calibration scalar;
element-bucket ratios; 97-share ratios; direction-balance ratios;
97-resolution coin ratios; non-97 cause ratios. TX-only wrappers (installed
during `generate_tx` only, try/finally teardown): `_draw_nature` resamples
97-causes from TX's empirical 97-cause mix (all code 26); `_recorded_cause`
blanks 97 causes at TX's 0.7995 (consumes the rng draw to keep the stream
aligned); `_corrupt_income`/`_corrupt_deduction` scale agency-side amount
deltas by s_over/s_under per realized direction. Importing the module
installs nothing.

The margin architecture from NY1 is used from the start: cause ratios fit
on non-97 only, 97 causes resampled from TX's empirical mix — required
here because TX's 79.95% 97-blanking (vs 64.4% national) would otherwise
distort the pooled cause fit exactly the way PA1's it1 blew up.

## Results

`python3 experiments/tx1_tx_generator.py validate --qc ../snap-qc-data/raw --n 20000 --seed 7`
(TX synth vs real TX; national sanity: nat synth 0.601/0.245/0.154):

| metric | it1 | it2 | it2b (final) |
|---|---|---|---|
| finding L1 | 0.0169 | 0.0164 | **0.0279** |
| element L1 | 0.0821 | 0.0276 | **0.0344** |
| cause L1 | 0.0758 | 0.0976 | **0.0286** |
| dollar p50 (synth/real) | 25/27 | 25/27 | **29/27** |
| dollar p90 (synth/real) | 168/149 | 168/149 | **175/149** |
| dollar mean (synth/real) | 60/58 | 60/58 | **65/58** |
| share ≤$56 (synth/real) | 0.698/0.743 | 0.700/0.743 | **0.669/0.743** |
| case-rate (synth/real) | 0.4165/0.4344 | 0.4378/0.4344 | **0.4345/0.4344** |
| p(over\|err) (synth/real) | 0.5417/0.5144 | 0.5291/0.5144 | **0.5464/0.5144** |

(L1 = sum of absolute mix-share differences across the categories — 0 is a
perfect match. F1/AUC/GBM = gradient-boosted trees, not used in TX1.)

Iteration history:
- **it1** (pure empirical ratios, coin scalar 1.0): finding L1 0.0169 —
  already under the 0.06 gate. Element L1 0.0821 (sua overshooting),
  cause L1 0.0758.
- **it2** (one-step realized-output calibration on buckets only,
  mirroring PA1's it3/NY1's it2): bucket ratios × real_TX_share/synth_share
  (sua 1.22→0.91 is the material move — it1 overshot sua's realized share
  once the 97-share cut bit). Element L1 0.0821→0.0276, finding L1
  0.0169→0.0164. The 97-resolution-coin and direction-margin one-steps were
  tried and **reverted**: both overshot (finding L1 0.0169→0.0685 undamped,
  →0.0394 sqrt-damped) — TX's 97-resolution and direction instruments have
  gain > 1 on TX's mix, the opposite of NY's gain < 1 ("materialization
  asymmetry eats part of the drawn margin"). it1's pure-empirical direction
  already lands p(over|err) within 0.015, so the revert costs nothing.
- **it2b** (one-step on the 97-share ratios): the it2 pilot's realized
  97-share was 0.41 vs 0.29 real — 97s materialize at a higher rate than the
  drawn mix implies, which left too many recorded 97s → no_fault (cause 26)
  overshoot driving cause L1 0.0976. Correcting per-bucket (shelter
  0.56→0.29, sua 0.48→0.28, depcare 0.70→0.44, hhcomp 1.0→0.10,
  arithmetic 1.0→0.0) brought cause L1 0.0976→**0.0286** and element L1 to
  **0.0344**, at the cost of finding L1 0.0164→0.0309. Coin-cal line search
  over {0.97, 0.98, 0.99, 1.0}: **0.98 wins** (case_err 0.4345 vs 0.4344
  real — essentially exact; finding L1 0.0279).

**Structural limitations (documented, not fixable within TX1's scope):**
1. Dollar p90 175 vs 149 / mean 65 vs 58: the uniform direction-conditional
   scale (s_over=0.8824, s_under=1.25) cannot fully match TX's lighter tail
   — same architectural limit NY1 documented (NY's was the reverse: a
   heavier tail the scale couldn't reach).
2. p(over|err) 0.5464 vs 0.5144 (+0.032): the direction instrument was
   deliberately left at its it1 values after the one-step overshot; a
   damped second step is staged but judged not worth the overfitting risk
   at finding L1 0.028.
3. near-full|over 0.0225 vs 0.0599 national: p_unit stays at the national
   default — TX's whole-unit tail is smaller than the generator produces.
   Re-deriving the unit-bucket correction is a defined extension.
4. The baked bucket/97-share/coin ratios include the it2/it2b
   realized-output calibrations; pure empirical values are in the `fit`
   output and the code comments.

**National byte-identical:** verified — a 5k-case national run
(`python3 -m src.synth.generate`, exact CLI path with the adopted flags)
produces byte-identical output with and without `synth.tx_state` imported
in the same process (md5-identical across runs, including the import
variant — the earlier NY1 chronicle's warning about replicating the exact
CLI path was followed).

## Verdict

TX1 gates the TX chain: the TX-conditioned generator reproduces TX's finding
mix (L1 0.028), element mix (0.034), cause mix (0.029), case-error rate
(0.4345 vs 0.4344 — exact), and the underissuance tilt, with the national
path byte-identical. Final calibration is *tighter than NY1's* on element
(0.034 vs 0.044) and cause (0.029 vs 0.074), comparable on finding (0.028
vs 0.020). The honest residuals are the dollar tail (p90 175 vs 149) and a
+0.032 p(over|err) gap. The distinctive TX structure the transfer
experiment needs — depcare/sua-heavy, medical-light, under-tilted,
nature-99-coded errors — is faithfully in the generator.

## Next steps

- **TX2** consumes `generate_tx` (API below) for the transfer experiment:
  train on TX synth, test on real TX microdata. Suggested TX2 checks: GBM
  transfer (finding/element + dollar amount); seed-robustness (n=20k seeds
  8, 9); the TX-vs-national decision battery per the NY2 protocol.
  - **Done →** [TX2](tx2_tx_transfer.md): TX2: MIXED — finding: TX-synth AUC 0.688 vs national 0.670 (wins, 2/6 seeds — weaker than NY's 6/6). Element: 0.407 vs 0.441 national — TX *loses* on fine-grained element pred…
- If p(over|err) fidelity becomes binding, the staged lever is a damped
  (sqrt) second-step direction calibration — residual factors are modest
  but the instrument's gain > 1 must be respected.
- If the whole-unit tail matters for dollar transfer, the defined lever is
  re-deriving the unit-bucket correction at TX's 0.0225 near-full rate.

## TX2 API (copy-paste)

Python:
```python
from src.synth.tx_state import generate_tx
generate_tx(n=20000, seed=7, dist="experiments/dist.json", out="data/tx_synth.jsonl")
# returns the output path; each case dict matches the national schema plus "state": "TX"
```

Shell:
```bash
python3 -m src.synth.tx_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out data/tx_synth.jsonl
```

Reproduce the fit (provenance of every baked constant):
```bash
python3 experiments/tx1_tx_generator.py fit
```

Re-run validation:
```bash
python3 experiments/tx1_tx_generator.py validate --qc ../snap-qc-data/raw --n 20000 --seed 7
```
