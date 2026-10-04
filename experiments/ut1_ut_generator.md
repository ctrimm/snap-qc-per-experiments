# Experiment UT1: UT-conditioned SNAP QC synthetic generator

**Date:** 2026-10-04 · **Code:** `experiments/ut1_ut_generator.py` (fit
harness), `src/synth/ut_state.py` (the conditioned generator)

## Hypothesis

Tied to the north star (state-conditioned synthetic training data for QC
error detection): Utah's QC error profile is nationally distinctive — a
low payment-error-rate state (5.54% FNS-published FY2025), the third leg of
the low-PER panel with SD (lowest, validated) and ID (2nd-lowest, running
concurrently). If the relative-offset architecture (national dist →
adopted calibration → UT offset ratios, in-memory) can reproduce UT's
finding mix, element mix, cause mix, case-error rate, and directional
profile while leaving national output byte-identical, the module gates the
UT transfer experiment (UT2).

## Method

Microdata: SNAP QC public-use files, Utah (STATE=49, n=4,101 pooled
FY2020–2024; FY2020 729 / FY2021 245 / FY2022 1007 / FY2023 1055 /
FY2024 1065), read-only. **Fit basis is FY2022–2024 only (n=3,127)** —
partial-year FY2020–21 are excluded from fitting per the NY6 lesson (NY's
FY2021 221 rows moved the fitted error rate 1.9pp; UT's FY2021 n=245 and
FY2020 n=729 are likewise thin). The national reference uses the same
FY2022–2024 basis so the UT/national ratios sit on one temporal footing.
The shared UT holdout (`experiments/ut2_holdout_idx.json`) still spans all
five FYs — it is test data, not fit data. All aggregates FYWGT-weighted;
rates are microdata-implied, NOT FNS-published (the microdata case-error
rate is 33.23% vs FNS's 5.54% published payment rate — the same
published-vs-microdata divergence as PA/NY/TX/SD; the POC trains on the
microdata basis throughout).

The fit harness (`fit_ut_targets`) mirrors `fit_sd_targets` with
STATE="49" and `fys=[2022, 2023, 2024]`: finding mix, case-error rate,
dollar rate, P(err|earner/no-earner), P(over|err), near-full|over, dollar
quantiles, share ≤$56, per-bucket element ratios, 97-share ratios,
direction-balance ratios, 97-resolution P(over|97) ratios, cause ratios on
**non-97 variances only** (the PA1 lesson), and the empirical cause mix on
nature-97s per bucket. Sparsity guards (copied verbatim): bucket cells
with UT unweighted n<25, 97-share/97-coin cells with 97-n<5, direction
cells with non-97 n<25 keep the national value (ratio 1.0).

UT empirical targets (FY2022–2024, FYWGT-weighted): finding correct/over/
under 0.6677/0.1920/0.1403; case-error rate 0.3323 (national 0.4014);
dollar rate 0.0390 (national 0.0873); p(err|earner) 0.5751,
p(err|no-earner) 0.2376 (coin ratios 0.9816/0.7131); p(over|err) 0.5778
(national 0.6130); dollar p50 $22 (national $31), p90 $99 ($202), mean $42
($70), medO $25/$37, medU $18/$23, share≤$56 0.855; cause97 blank 0.840
(national 0.584); near-full|over 0.0033 (national 0.0574).

Iteration history:

- **it1** (pure empirical ratios, coin scalar 1.0): case rate undershot at
  0.2993 vs 0.3323 — UT's coin cuts plus small-dollar errors materialize
  less often than the national-calibrated correction expects. Cause L1
  0.0262 out of the gate (UT codes no no-fault on substantive variances —
  no_fault 0.0 on every bucket, NY-like — so SD1's it2b basis blowup cannot
  occur: 0.0 kills the term on any basis).
- **it2** (one-step realized-output calibrations, mirroring SD1's it2 /
  NY1's it2 / PA1's it3): bucket ratios × real_UT_share/synth_share
  (earned 1.2677→1.4102, sua 0.7885→0.6166, medical 1.0274→1.4559);
  97-share × real/synth P(97|b) (earned 1.5228→1.6223, shelter 0.764→0.6873);
  direction margins × real/synth on the non-97 slice (shelter over
  1.5602→1.9409, sua over 1.08→1.9073); 97-resolution coins × real/synth
  P(over|97,b) (sua 1.0972→1.2787). Coin-cal line search over
  {0.95, 1.0, 1.05, 1.1, 1.15} on the calibrated ratios: **1.10 wins**
  (finding L1 0.0497, case_err 0.3350 vs 0.3323) — like PA's 1.08 and SD's
  1.05, UT needs an *upward* correction against a materialization ceiling.
- **it3** (damped second one-step correction on direction + 97-coin
  blocks): the full one-step correction diverged (multipliers up to 2.5x —
  drawn direction margins only partially materialize through the
  generator's mechanics), so this step applied sqrt(real/synth) damped
  multipliers computed under the baked coin cal 1.10. Variance-level
  direction now tracks real within ~0.04 on every major bucket (97-coins
  within ~0.05).

Two UT-specific design decisions beyond the SD template: (1)
`UT_P_UNIT = 0.0007` (P_UNIT_DEFAULT × 0.0033/0.0574 near-full|over) —
whole-unit ineligibility is near-absent in UT, so mechanism 2 is scaled
down rather than left at the national default; (2) `UT_97_CAUSE` carries
UT's empirical per-bucket mix (mostly cause 26 no-fault, with client-coded
1s on earned/shelter; thin buckets fall back to the pooled UT mix) —
unlike SD's degenerate all-26 mix, UT records some substantive 97 causes.

(AUC = area under the ROC curve, a ranking metric: 0.5 is chance, 1.0 is
perfect. L1 = sum of absolute mix-share differences across categories — 0
is a perfect match.)

## Results

Validation: UT-conditioned synth (n=20,000, seed 7) vs real UT —

| metric | it1 | it3 (final) | SD1 final (ref) |
|---|---|---|---|
| finding L1 | 0.0659 | **0.0451** | 0.0039 |
| element L1 | 0.1080 | **0.0698** | 0.0965 |
| cause L1 | 0.0262 | **0.0354** | 0.2023 |
| dollar p50 (synth/real) | 15/22 | 16/22 | 10/17 |
| dollar p90 (synth/real) | 105/99 | 110/99 | 70/70 |
| dollar mean (synth/real) | 38/42 | 40/42 | 27/34 |
| share ≤$56 (synth/real) | 0.795/0.855 | 0.779/0.855 | 0.876/0.886 |
| case-rate (synth/real) | 0.2993/0.3323 | **0.3324**/0.3323 | 0.2465/0.2475 |
| p(over\|err) (synth/real) | 0.591/0.578 | 0.643/0.578 | 0.505/0.497 |

Offset recovery (UT minus national): case_err_rate real −0.0692 / synth
−0.0659; dollar_rate real −0.0484 / synth −0.0285; p(over|err) real −0.0352
/ synth +0.0293. The direction and scale of the case-rate and dollar-rate
offsets are recovered; the over-share offset misses sign (+6.5pp on
p(over|err)) — see structural residual 2.

**Structural residuals (documented, not fixable within UT1's scope):**

1. Element L1 0.0698 (NY 0.044, SD 0.0965): the sparsity-guarded rare
   buckets (depcare/hhcomp/arithmetic keep national draw weights) plus the
   97-vs-non97 shape the relative-offset architecture cannot fully express.
   Within the documented cross-state range.
2. Case-level p(over|err) 0.643 vs 0.578 (+6.5pp): the non-97 direction
   margins saturate — drawn over/under multipliers up to 2.2x move realized
   P(over|non97) only ~0.03–0.05, because the generator's non-97 nature mix
   carries an "other"-direction mass the margin architecture cannot
   redirect (unearned 0.570 vs 0.705 real, sua 0.393 vs 0.501 real even at
   ×1.76/×2.19). The 97-resolution coins (the dominant direction lever)
   are within 0.05 of real on every major bucket. UT4/UT5 calibrate the
   finding model on the real UT train split, which corrects the marginal;
   the conditional structure the transfer battery trains on is faithful at
   the variance level.
3. Dollar level: p50 $16 vs $22, share≤$56 0.779 vs 0.855 (p90 110/99,
   mean 40/42 close). Same family as NY1's/SD1's documented shape fact: a
   single direction-conditional scale (s_over=0.6757, s_under=0.7826)
   cannot separate the 97-vs-non97 size modes.

**National byte-identical:** verified — a 5k-case national run (`python3
-m src.synth.generate`, exact CLI path incl. `--max-attempts 12`) produces
md5-identical output (cb449be75fb5cb25e8b5d1342f384308 — the same hash
SD1 recorded) with and without `ut_state` imported.

## Verdict

**PASS with documented residuals.** UT1 gates the UT chain: the
UT-conditioned generator reproduces UT's finding mix (L1 0.0451, inside
NY1's 0.06 gate), case-error rate (exact), element mix (0.0698, between NY
and SD), cause mix (0.0354 — best of the four states), and the direction
and scale of the case-rate and dollar-rate offsets, with the national path
byte-identical. The residuals are concentrated where the architecture
cannot reach: non-97 direction-margin saturation (case-level over-share
+6.5pp) and the 97-vs-non97 dollar shape (level). The conditional structure
UT2 needs — which cases err, which direction, how big — is faithful at the
variance level. The FY2022–2024 fit basis (NY6 lesson) is documented in
the module docstring and the fit harness.

## Next steps

- **UT2** consumes `generate_ut` (API below) for the transfer experiment:
  train on UT synth, test on held-out real UT rows (all five FYs, ~1,025
  rows, ~340 error cases — a larger holdout than SD's).
- Watch the over-share residual in UT5's over/under split: the synth's
  +6.5pp over tilt is calibrated out at the margin by UT4/UT5's real-train
  calibration, but the split should be reported honestly.
- If UT2's finding transfer is weak, the staged lever is re-scoping
  (NY2's MIXED pattern), not more calibration — it3 already shows the
  saturation curve.

## UT2 API (copy-paste)

Python:
```python
from src.synth.ut_state import generate_ut
generate_ut(n=20000, seed=7, dist="experiments/dist.json", out="data/ut_synth.jsonl")
# returns the output path; each case dict matches the national schema plus "state": "UT"
```

Shell:
```bash
python3 -m src.synth.ut_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out data/ut_synth.jsonl
```

Reproduce the fit (provenance of every baked constant):
```bash
python3 experiments/ut1_ut_generator.py fit
```

Re-run validation:
```bash
python3 experiments/ut1_ut_generator.py validate --qc ~/workspace/snap-qc-data/raw --n 20000 --seed 7
```
