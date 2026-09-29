# Experiment 24 — adopt the draw fix + re-measured matrix as generator defaults, re-baseline
**Date:** 2026-09-29 · **Code:** `experiments/exp24_adopt_rebaseline.py`

## Hypothesis
North-star gates: calibration **and** transfer. Exp21 showed removing
earned/unearned/shelter from `ZERO_BASE_WEIGHT` (the draw fix) plus the
re-measured per-(bucket, stratum) materialization matrix gives finding L1
0.025 (from 0.036), with hhcomp 1.08x, arithmetic 0.95x, unearned 0.94x,
sua 0.90x. Adopting both as generator defaults should establish a new,
strictly better baseline on the calibration gate (finding mix L1, element
ratios, cause mix, dollar marginals) and the transfer gate (exp19's
battery: element accuracy/macroF1, persistent + balanced arm and the
retry-loop arm). The stale exp20 matrix must not be reused — keep rates
were re-measured on the corrected draw.

Glossary for this chronicle (see terms.md): *draw* = picking a variance's
bucket from the weighted mix; *materialization* = a drawn corruption moves
the computed benefit and is recorded; *keep rate* = P(materialize | drawn);
*per-case ratio* = synthetic count/cases over real count/cases (1.0x =
matches real); *finding L1* = distance between the synthetic and real
finding mixes (correct/over/under), lower is better; *accuracy* =
fraction of element-bucket predictions exactly right; *macroF1* = F1
averaged plainly across buckets, so rare buckets count as much as common
ones — the headline element-transfer metric.

## Method
Generator edits (minimal, clearly delimited; `src/synth/dollar_mech.py`
not touched — exp23 owns it):
- `src/synth/errors.py`: (1) `ZERO_BASE_WEIGHT = {}` — the three entries
  deleted, extending the exp11/exp12 comment; (2) new
  `MATERIALIZATION_MATRIX`: the 32 keep rates re-measured under the
  corrected draw, transcribed at full measured precision; (3)
  `_inject_persistent` now applies the matrix by default with exp20's
  guardrails (0.8 damping toward the scalar, mechanics-gap fallback below
  0.10, 2.5x trust-region cap); `legacy_materialization=True` restores the
  old scalar 1/eff_b path for reproducibility of old chronicles; (4)
  `inject()` plumbs the flag through. The retry loop keeps its scalar
  correction either way — the matrix was measured in persistent flow, and
  changing retry behavior would confound the comparison arms.
- `src/synth/generate.py`: new `--legacy-materialization` flag (default
  off). No other CLI defaults changed.

All in-process; only this script and its chronicle are written, nothing
committed. Real QC microdata read for aggregate comparison only.

1. **SANITY:** re-measured keep rates under the corrected draw (60k cases,
   seed 11, exp21's exact procedure: scalar-draw measurement) and asserted
   the hard-coded matrix matches (max |diff| = 0.000000 < 1e-6; the 1e-6
   floor is 6-decimal transcription rounding).
2. **BEFORE:** 20k cases, seed 7, pre-change defaults reproduced in-process
   (old `ZERO_BASE_WEIGHT` restored + legacy scalar path), persistent and
   retry-loop arms. Paired rng streams for the after arms.
3. **AFTER:** 20k cases, seed 7, new generator defaults, persistent and
   retry-loop.
4. **CALIBRATION:** finding mix L1, per-case element ratios + share ratios,
   nature-57 share, coarse cause mix (exp15's agency/client/other/unknown
   mapping), dollar marginals (exp18's stats: p10/p25/p50/p90/p99, mean,
   share <= $56, over/under asymmetry). No dollar flag — exp23's dollar
   mechanisms are a staged follow-up.
5. **TRANSFER:** exp19's battery arms (a) persistent unbalanced,
   (b) persistent + `class_weight="balanced"`, (c) retry-loop + balanced —
   on BEFORE and AFTER. Element task, v1 features (9 raw),
   `HistGradientBoostingClassifier(random_state=0)`, same real FY2024 QC
   test split as exp4/exp9/exp19 (17,318 rows, never touched). Seed 7 in
   the script; seed 8 spot-check for the headline arms (b)/(c) to confirm
   the transfer pattern is not seed noise.

## Results

**The adopted matrix is exactly exp21's.** The in-script re-measurement
reproduces all 32 cells to <1e-6, including the composition-shifted ones
(unearned/no_earner_nonsenior 0.81 -> 0.65; earned/no_earner_senior 0.02
clipped -> 0.723 with real sample size). A side finding: measuring keep
rates under the *matrix-weighted* draw instead agrees on all well-sampled
cells (draws >= 300: within 0.03) and differs only in tiny-sample cells —
keep rates are weight-invariant in expectation, as assumed; the noisy
cells are why the trust-region cap and mechanics-gap fallback exist.
Caveat kept in the code comment: depcare's senior-strata cells rest on 3
and 4 draws.

**Reproducibility check passed:** BEFORE-persistent (old weights +
legacy scalar, in-process) reproduces exp21's BEFORE finding mix exactly
(0.615/0.245/0.140); AFTER-persistent matches exp21's REMOVED+NEWMAT
(0.608/0.247/0.146, L1 0.025). Old chronicles remain reproducible via
`--legacy-materialization` plus the `patched_zbw` pattern.

### Calibration gate — strictly better

| | BEFORE-persist | AFTER-persist | BEFORE-retry | AFTER-retry |
|---|---|---|---|---|
| finding mix (c/o/u) | 0.615/0.245/0.140 | 0.608/0.247/0.146 | 0.611/0.225/0.164 | 0.593/0.241/0.166 |
| **finding L1** | **0.036** | **0.025** | **0.029** | **0.019** |

Per-case element ratios (1.0x = matches real):

| bucket | B-persist | A-persist | B-retry | A-retry |
|---|---|---|---|---|
| earned | 0.84x | 0.80x | 0.83x | 0.81x |
| unearned | 0.77x | **0.94x** | 0.80x | 1.12x |
| shelter | 0.74x | **0.83x** | 0.73x | 0.89x |
| sua | 1.04x | **0.90x** | 1.16x | 0.93x |
| medical | 0.69x | 0.53x | 0.69x | 0.50x |
| depcare | 0.50x | 0.41x | 0.56x | 0.48x |
| hhcomp | 1.59x | **1.08x** | 3.11x | 1.97x |
| arithmetic | 1.51x | **0.95x** | 3.25x | 1.97x |
| nature-57 share | 0.98x | 1.16x | 0.96x | 1.25x |

Unearned, shelter, sua, hhcomp, arithmetic all move toward 1.0x. Known
residuals, recorded not fixed (as framed): earned insensitive (~0.8x,
separate constraint); medical 0.69x -> 0.53x and depcare 0.50x -> 0.41x
relatively deflate as shares-game costs; nature-57 inflates 0.98x ->
1.16x. Arithmetic needed no gating, as exp21 predicted: 0.95x.

Cause mix: 4-way L1 0.022 -> 0.032 on persistent (slightly worse, driven
by the blank-cause "unknown" share 0.126 -> 0.132); the 3-way
known-cause L1 is flat (0.024 -> 0.024). Retry arm improves 0.071 ->
0.023. Roughly neutral — the draw fix does not distort who-caused-what.

Dollar marginals (error cases, absolute $): essentially unchanged, as
expected with no dollar-mechanism change — mean 93 -> 97 (real 71),
share <= $56 0.39 -> 0.36 (real 0.70), over/under medians still flipped
vs real (medO < medU in synth, > in real). No regression, no improvement:
this is the baseline exp23's dollar flag will build on.

### Transfer gate — mixed: accuracy up, macroF1 down

| Config (synth→real, element, v1) | acc (seed7 / seed8) | macroF1 (seed7 / seed8) |
|---|---|---|
| (a) persistent, unbalanced — before | 0.510 / — | 0.290 / — |
| (a) persistent, unbalanced — after | 0.514 / — | 0.255 / — |
| (b) persistent + balanced — before | 0.478 / 0.470 | 0.288 / 0.299 |
| (b) persistent + balanced — after | 0.481 / 0.491 | 0.281 / 0.286 |
| (c) retry-loop + balanced — before | 0.437 / 0.456 | 0.304 / 0.303 |
| (c) retry-loop + balanced — after | 0.440 / 0.471 | 0.273 / 0.273 |

The pattern replicates on seed 8: **accuracy improves slightly on every
arm (+0.004 to +0.021); macroF1 drops on every arm (-0.007 to -0.031).**
Per-bucket F1 (seed 7, arm b): hhcomp 0.165 -> 0.094, sua 0.092 ->
0.092 (flat), medical 0.175 -> 0.160, arithmetic 0.089 -> 0.086, while
earned 0.665 -> 0.687 and depcare 0.171 -> 0.205 *improve*. The damage is
concentrated in the rare buckets.

**Mechanism (confirmed on both seeds):** the draw fix makes the *training*
mix more faithful, which means ~35% fewer distinct rare-bucket examples:
persistent hhcomp 420 -> 281/272, arithmetic 262 -> 166/162, sua 781 ->
669/622, medical 310 -> 241/242; retry hhcomp 735 -> 468/477, arithmetic
508 -> 312/284. Exp9/exp19 established that macroF1 is driven by distinct
rare-example counts — decision boundaries are learned from distinct
examples, and `class_weight="balanced"` cannot create examples that were
never generated. The calibration win and the macroF1 loss are the same
event viewed from two gates: the old generator's rare-bucket *overage*
was feeding the classifier.

Corollary: the retry loop's macroF1 edge over persistent+balanced is gone
after the fix (seed 7: 0.304 vs 0.288 before -> 0.273 vs 0.281 after;
seed 8: 0.303 vs 0.299 -> 0.273 vs 0.286). The edge was feeding on the
same distortion — the retry loop's rare-bucket counts fell hardest
(hhcomp 3.11x -> 1.97x).

## Verdict
**Partially held.** The adoption is a strict win on the calibration gate
(finding L1 0.036 -> 0.025 persistent, 0.029 -> 0.019 retry; five buckets
move toward 1.0x; cause mix neutral; dollar marginals unchanged) and the
generator edits are verified (reproducibility check, exact matrix
re-measurement, `--legacy-materialization` escape hatch). The "strictly
better on transfer" half did **not** hold: accuracy improves slightly but
macroF1 drops 0.007–0.031 across arms on both seeds, because the faithful
mix contains ~35% fewer distinct rare-bucket training examples and
macroF1 is count-driven. This is not a reason to revert — the data product
(the faithful generator) is the north star's calibration gate, and a
training recipe that depends on generator distortion was already on
borrowed time (exp19's doctrine update). It does mean the
classifier-training recipe must now be re-derived from the faithful
generator rather than inherited: rare-bucket signal has to come from the
*training* mix (e.g. generation-time oversampling of rare buckets purely
for training, exp19's arm-(g) direction), not from generator distortion.

## Next steps
1. **(recommended)** Re-derive the classifier-training recipe on the new
   faithful defaults (exp19's next step #3, now urgent): does
   generation-time oversampling of rare buckets for the *training* mix
   recover macroF1 without touching the generator? The retry loop's edge
   is gone, so the recipe question is open again.
2. **(staged)** Combine with exp23's dollar-mechanism flag once it lands:
   re-baseline dollar marginals (mean 97 vs 71, share <= $56 0.36 vs 0.70,
   flipped over/under medians) on the new defaults.
3. Earned ~0.8x stickiness: separate audit — not draw-side (exp21); likely
   keep-rate or nature-mix.
4. Medical/depcare relative deflation and nature-57 inflation: revisit
   whether the empirical mixes or the exp13 57-weights need re-measurement
   under the corrected draw.
5. Re-measure the tiny-sample matrix cells (depcare senior strata: 3–4
   draws; hhcomp/earner_senior: 22) with a larger measurement run, or pool
   them with the exp20 values.
6. Household sampler base-positivity gaps from exp21 (shelter/sua for
   senior strata, sua for no_earner_nonsenior) — sampler follow-up,
   independent of this change.
