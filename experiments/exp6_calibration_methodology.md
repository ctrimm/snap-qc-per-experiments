# Calibration methodology — attrition-corrected injection
**Date:** 2026-09-28 · **Code:** `experiments/build_dist.py`,
`experiments/measure_effectiveness.py`, `experiments/calibrate_injection.py`
· **Artifacts:** `experiments/dist.json`, `experiments/eff.json`,
`experiments/inject.json`

Companion to exp 6. This is the measurement and correction machinery behind
the eligibility-screen result, recorded here because the three corrections
are reusable methodology, not one experiment's tuning.

## Problem
Three separate attrition / bias mechanisms stood between the empirical
distributions measured from the real QC file and what the generator's retry
loop actually records:

1. **Injection attrition.** `inject()` flips a coin, then the retry loop
   drops the case if no corruption materializes (or the budget exhausts).
   P(materialize | inject) differs by stratum (0.952 earner, 0.786
   non-earner), so a naive coin overshoots earners and undershoots
   non-earners.
2. **Retry-filtering bias across buckets.** Some buckets' corruptions
   frequently no-op: the excess-shelter cap absorbs shelter increases,
   the $35 disregard absorbs small medical changes. A flat bucket mix
   therefore under-records exactly the buckets whose errors are
   economically muted.
3. **Retry-filtering bias across directions within a bucket.** The
   asymmetry is directional, not just bucket-level: shelter-over
   materializes at 0.178 vs shelter-under at 0.566; sua-over 0.259 vs
   sua-under 0.558; medical-over 0.352 vs medical-under 0.704; depcare-over
   0.329 vs depcare-under 0.628. Earned and unearned are symmetric
   (~0.73 both ways). A bucket-level correction alone leaves the nature
   mix distorted (this is what produced the 52-at-1.91x / 56-at-0.57x
   signature in the first exp 6 run).

## Method
- **Phase 1 — injection coins** (`calibrate_injection.py`): force-inject one
  variance per case per stratum, measure P(materialize | inject), solve
  coin = P_empirical(error) / P(materialize | inject). Coins: earner 0.622,
  non-earner 0.413. Written to `inject.json`.
- **Phase 2 — stochastic-97 resolution coins** (`calibrate_injection.py`):
  the real file shows nature 97 (timing) is direction-ambiguous — earned-97
  is 60.5% over, shelter-97 37.1% over, sua-97 51.9%, unearned-97 67.8%,
  medical-97 55.4% (single-variance cases). The generator used to treat 97
  as always-over, which pushed the earned over-share to 0.94 vs 0.68 real.
  Fix: each drawn 97 resolves into a directional corruption (income→38/44,
  deductions→56/57, hhcomp→7/6) while the recorded nature stays 97.
  Per-bucket coins solve c = t·m_u / (t·m_u + (1−t)·m_o) from forced
  97→over / 97→under materialization runs (e.g. shelter 0.543, sua 0.683,
  earned 0.608). One real bug caught here: the coins were silently not
  applied because the reader looked at the top level of inject.json while
  the writer nests under `dist["injection_rate"]` — fixed, verified
  (realized shelter-97 over = 0.346 vs target 0.371).
- **Two-level effectiveness** (`measure_effectiveness.py`): measures
  P(materialize | bucket, direction-class) with classes over={35,37,38,53,
  56,7}, under={44,52,57,6,13}, other={97,99,40,…}; computes per-(bucket,
  dir) importance weights w ∝ 1/m normalized over the empirical direction
  mix, plus an analytical bucket rate eff_b = Σ w·p·m (the harmonic-mean
  form — no second measurement pass needed). `inject()` applies the bucket
  weights at bucket-draw time and the direction weights at nature-draw time.
  The arithmetic bucket is special-cased (direct benefit noise in
  `inject()`, always materializes: eff = 1.0, no direction weighting —
  without this the measured m ≈ 0.02 would upweight it 50x).
- **Zero-base weights re-verified** (`src/synth/errors.py`): all five
  P(var | base=0)/P(var | base>0) ratios re-measured over all FY2024 cases;
  four matched, medical corrected 0.036 → 0.087.

## Results
The full stack (conditional mixes + 97 coins + two-level effectiveness +
phase-1 coins) produces exp 6's finding mix: 60.4/23.5/16.1 vs real
60.3/23.9/15.8, **L1 = 0.009** (from 0.191 at exp 5), with the nature-level
directional signature (52/56) corrected from 1.91x/0.57x to 1.24x/1.02x.

## Verdict
The methodology works and is load-bearing: removing any one correction
re-opens a visible gap (direction weighting alone fixed the 52/56
asymmetry; the 97 coins fixed the earned over-share; the phase-1 coins
fixed the earner/non-earner rate split). The importance-weighting framing
is the right mental model — the retry loop is a rejection sampler, and
these are its proposal corrections.

## Next steps
1. The two-level weights are measured on the marginal household population;
   the retry loop draws from the zero-base-scaled conditional population.
   If a bucket's conditional materialization diverges (medical did), the
   correction under/over-shoots — measure m under the actual draw
   distribution as a refinement.
2. Same importance-weighting treatment for the nature mix *within*
   (bucket, direction): currently only direction classes are corrected.
3. `dist.json` / `eff.json` / `inject.json` are committed so the repo runs
   standalone; the real QC microdata stays out of the repo (held-out
   validation only).
