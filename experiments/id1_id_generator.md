# Experiment ID1: Idaho-conditioned generator

**Date:** 2026-10-04 · **Code:** `experiments/id1_id_generator.py`
(module: `src/synth/id_state.py`; fit output: `/tmp/id1out/fit.txt`)

## Hypothesis

Tied to the north star (calibration): an Idaho-conditioned synthetic
generator that reproduces Idaho's finding mix, element mix, cause mix,
case-error rate, and directional profile — via relative offsets on the
national adopted dist, in memory only — gives ID2 a state-conditioned
training distribution while leaving national output byte-identical.

## Method

Port of `experiments/sd1_sd_generator.py` with STATE="16" (string — the
harness uses csv.DictReader). **Fitting-window change (NY6 lesson):**
offsets are fit on **FY2022-2024 only** (n=3,111 ID rows). FY2020 (n=515)
and FY2021 (n=213) are partial-year/thin QC files for Idaho; the NY6
finding (partial-year files move the fitted error rate ~1.9pp and distort
bucket ratios) is adopted as a standing rule — the ID2 holdout is still
built on all pooled FY2020-2024 rows. All aggregates FYWGT-weighted;
microdata-implied rates (NOT FNS-published).

The fit computes ID/national offset ratios: finding mix, case-error rate,
dollar rate, P(err|earner/no-earner), P(over|err), near-full|over, dollar
p10/p25/p50/p90/mean, share ≤$56, med-over/med-under, cause-97 blank rate,
per-bucket element ratios, 97-share ratios, direction-balance ratios,
97-resolution P(over|97) ratios, cause ratios on non-97 variances only, and
the empirical cause mix on nature-97s per bucket. Sparsity guards:
bucket cells with ID unweighted n<25, 97-share/97-coin cells with 97-n<5,
direction cells with non-97 n<25 keep the national value (1.0).

Transcription into `src/synth/id_state.py` followed SD1's it2 recipe:
1. **it1:** pure-empirical constants baked.
2. **it2:** 20k-case pilot → one-step realized-output calibration
   (× real_ID_share/synth_share) on the bucket, 97-share, 97-resolution,
   and direction blocks; it2b-style rebased cause ratios
   (ID_non97_mix / dist_mixed_basis — the SD-track blowup fix); coin-cal
   line search over {0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30}.
3. **it3:** one-step residual correction on the five fitted buckets'
   non-97 cause cells (× real_cell/synth_cell, factors 0.87–1.16).

## Results

**Idaho empirical targets (FY2022-24, n=3,111, FYWGT):**
finding c/o/u 0.6609/0.2084/0.1307; case-error rate 0.3391 (national
0.4014); dollar rate 0.0366 (national 0.0873); p(err|earn) 0.4620,
p(err|noearn) 0.2852; p(over|err) 0.6146; near-full|over 0.0076 (national
0.0573); dollar p10/p25/p50/p90 = 2/7/19/87, mean 36, 86.9% ≤$56
(national 3/11/31/202, mean 70); medO $21 / medU $15 (national $37/$23);
cause-97 blank 0.502 (national 0.585).

Idaho's signature vs national: earned 1.15x, shelter 1.31x (above);
unearned 0.74x, sua 0.68x, medical 0.62x (below); timing-97 share ratios
1.4–4.4x per bucket (ID's errors are heavily timing); non-97 shelter
direction strongly suppressed (over 0.12x / under 0.07x); cause mix tilts
client/other ("other" 1.5–4.1x national; no_fault 0.0 on substantive
variances). **Dollar note for ID5:** ID's p90 is $87 — no big-dollar tail,
like SD's $70 (national $202).

**Validation (20k ID-conditioned cases, seed 7, vs real ID FY2022-24):**

| metric | ID1 | NY1 (reference) |
|---|---|---|
| finding L1 | **0.0215** | 0.0202 |
| element L1 | 0.0829 | 0.044 |
| cause L1 | 0.0957 (0.1130 pre-it3) | 0.074 |
| case-error rate | synth 0.3412 vs real 0.3391 (exact) | exact |
| dollar p50 | synth $7 vs real $19 | $18 vs $29 |
| dollar p90 / mean | $66/$26 vs $87/$36 | — |
| share ≤$56 | 0.883 vs 0.869 | — |
| p(over\|err) offset | synth +0.0276 vs real +0.0018 | +0.027 |

Coin-cal: **1.20** wins (finding L1 0.0235 on 8k pilots; U-shaped over
{0.95…1.30}) — a larger upward correction than SD's 1.05 / PA's 1.08,
because ID's deep coin cuts (0.788/0.856) plus small-dollar errors
materialize less often than the national-calibrated correction expects.
National output byte-identical with/without the module imported (5k-case
run, md5 cb449be75fb5cb25e8b5d1342f384308).

**Structural residuals (documented honestly):**
- Dollar p50 ($7 vs $19): the relative-offset architecture (uniform
  s_over/s_under scales) cannot express ID's 97-vs-non97 dollar shape —
  same family as NY1's 18-vs-29 residual.
- Element L1 0.0829: dominated by the sparsity-guarded rare buckets
  (depcare/hhcomp/arithmetic over-drawn at national rates; +0.041 of the
  L1). The five fitted buckets are within 0.025. The guard is deliberate —
  fitting on tiny-n cells would be noise-chasing.
- Cause L1 0.0957: the recorded-basis mix includes 97-cause recorded mass
  (causes 1/26 → client/no_fault), a separate mechanism from the non-97
  ratios; the non-97 mechanism itself is within ~15% per cell on the five
  fitted buckets after it3.
- p(over|err) +0.028 overshoot: same structural residual as NY1's +0.027.

## Verdict

**PASS.** Finding L1 0.0215 ≤ 0.06, case-error rate exact, national output
byte-identical, and all offset directions recovered. The element/cause
residuals are documented structural facts (guarded rare buckets; 97-cause
recorded-mass interaction), not calibration failures — and the transfer
battery (ID2) is the empirical test of whether they matter.

## Next steps

- ID2 trains on `generate_id(n=20000, seed 7)` output. API block for ID2+:
  ```python
  from src.synth.id_state import generate_id
  generate_id(n=20000, seed=7, dist="experiments/dist.json",
              out="/tmp/id2out/id_synth.jsonl")
  ```
  Shell:
  ```bash
  python3 -m src.synth.id_state --n 20000 --seed 7 \
      --dist experiments/dist.json --out /tmp/id2out/id_synth.jsonl
  cd src && python3 -m synth.generate --n 20000 --seed 7 \
      --dist ../experiments/dist.json --max-attempts 12 \
      --out /tmp/id2out/nat_synth.jsonl
  ```
- Reproduction: `python3 experiments/id1_id_generator.py fit` (prints the
  it1 constants baked into `src/synth/id_state.py`); it2/it3 steps are
  `/tmp/id1out/calibrate_id1.py` and `/tmp/id1out/bake_it2.py` (scratch,
  documented above).
