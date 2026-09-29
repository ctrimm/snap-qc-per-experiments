# Experiment 25 — re-derive the classifier-training recipe on the faithful generator
**Date:** 2026-09-29 · **Code:** `experiments/exp25_training_recipe.py`

## Hypothesis
North-star gate: **transfer**. Exp24's adoption (draw fix + re-measured
materialization matrix) was a strict win on the calibration gate (finding
L1 0.036 → 0.025) but cost 0.007–0.031 of element macroF1, because the
faithful mix contains ~35% fewer distinct rare-bucket training examples
(hhcomp 420 → ~276, arithmetic 262 → ~164). The calibration win and the
macroF1 loss are the same event, and macroF1 is count-driven (exp9/exp19).
Doctrine going in: keep the GENERATOR faithful (it is the data product),
fix the TRAINING recipe.

We hypothesized that, on the faithful post-exp24 generator,
generation-time rare-bucket oversampling for the TRAINING mix only —
optionally combined with hard-household selection (a retry-style
materialization screen selecting harder households) — would recover the
lost macroF1, without reintroducing distortion into the generator or the
data product. If neither intervention recovers it, the recipe question is
settled: faithful persistent + balancing is the training recipe, and the
macroF1 gap is the honest price of a faithful generator.

Glossary for this chronicle (see terms.md): *accuracy* = fraction of
element-bucket predictions exactly right; *macroF1* = F1 averaged plainly
across buckets, so rare buckets count as much as common ones — the headline
element-transfer metric; *class_weight="balanced"* = the classifier
penalizes mistakes on rare classes more heavily, rebalancing the gradient
(it cannot create examples that were never generated); *boosted draw* =
generating extra training cases with rare-bucket draw weights multiplied
(4x here) — distinct new cases through the real injection machinery, never
row duplication; *hard-household screen* = the retry loop's
redraw-until-something-materializes logic used as a household filter
(exp22's arm-(j) pattern); *training mix* = the rows the classifier trains
on (may be deliberately distorted); *data product* = the generator's
default output (must stay faithful).

## Method
Exp19/exp22's battery on the current (post-exp24) generator — generator
files and defaults untouched (`src/synth/dollar_mech.py` not touched; the
boosted draw is an in-process dist copy, and the extras/screened rows never
enter the product pool):

- **Pools:** faithful persistent 20k + retry-loop 20k (`--no-persistent-buckets`),
  seed 7, `--max-attempts 12`, current defaults. The persistent 20k doubles
  as the data-product pool for the calibration check.
- **(a) faithful + balanced** — persistent 20k error rows (7,847),
  `class_weight="balanced"`. New baseline; replication check vs exp24's
  after-(b) seed 7 (0.481/0.281).
- **(b) faithful + boosted-draw rare extras + balanced** — (a)'s rows plus
  423 distinct extra rare-bucket error cases generated with 4x rare-bucket
  draw weights (fresh household stream, seed 999; 4,983 households drawn,
  all targets met, none short), restoring each rare bucket to its pre-exp24
  persistent 20k count: hhcomp 420, arithmetic 262, medical 310, depcare 72,
  sua 781. Training mix only.
- **(c) hard-household screen + balanced** — exp22's arm-(j) pattern on the
  current generator: retry-loop 20k error households → persistent injection
  with the shared phase-1 coin forced on → keep the 5,228 (64%) that yield
  a persistent error. Balanced.
- **(d) (c) + (b)'s extras + balanced** — 5,651 rows; tests whether
  selection and oversampling compose.

Classifier: `HistGradientBoostingClassifier(random_state=0)`, v1 features
(9 raw), element task, `class_weight="balanced"` on every arm, same real
FY2024 QC test split as exp19/exp22 (17,318 rows; never touched). Real QC
microdata used for the test split and aggregate references only.

Calibration: finding-mix L1 and all-variances per-case element ratios
(exp24's definition: every recorded variance, ELEMENT1–ELEMENT9) on the
unsampled 20k product pool.

## Results

**Replication checks pass.** (a) reproduces exp24's after-(b) seed 7
exactly (0.481/0.281); baseline rare counts match exp24 (hhcomp 281,
arithmetic 166, sua 669, medical 241, depcare 65). The product pool is
undistorted: finding L1 = 0.025 and per-case element ratios reproduce
exp24's after-persist table exactly (earned 0.80x, shelter 0.83x, unearned
0.94x, sua 0.90x, medical 0.53x, hhcomp 1.08x, arithmetic 0.95x, depcare
0.41x). The training recipe touched only training mixes.

### Transfer battery (synth→real, element, v1, balanced)

| arm | acc | macroF1 | train rows |
|---|---|---|---|
| (a) faithful + balanced | 0.481 | **0.281** | 7,847 |
| (b) + boosted rare extras | 0.453 | 0.270 (−0.010) | 8,270 |
| (c) retry-selected households | 0.446 | 0.247 (−0.034) | 5,228 |
| (d) (c) + extras | 0.435 | 0.247 (−0.034) | 5,651 |

Per-bucket F1 (rare buckets marked *):

| bucket | (a) | (b) | (c) | (d) |
|---|---|---|---|---|
| earned | 0.687 | 0.663 | 0.673 | 0.629 |
| shelter | 0.557 | 0.527 | 0.495 | 0.523 |
| unearned | 0.364 | 0.365 | 0.343 | 0.338 |
| sua * | 0.092 | 0.076 | 0.107 | 0.072 |
| medical * | 0.160 | 0.169 | 0.139 | 0.153 |
| hhcomp * | 0.094 | 0.092 | 0.063 | 0.081 |
| arithmetic * | 0.086 | 0.070 | 0.034 | 0.082 |
| depcare * | 0.205 | 0.200 | 0.119 | 0.097 |

### Reading the arms

**(b) — restoring the lost counts did not restore the lost macroF1.**
Arm (b)'s training set has *exactly* the pre-exp24 persistent per-bucket
counts (420/262/310/72/781), yet scores 0.270 vs the old regime's 0.288 —
same counts, worse macroF1, and accuracy falls 0.481 → 0.453. Two
consistent readings: (1) the macroF1 loss is not purely count — the
*provenance* of the rare examples matters (the old cases came from the
distorted draw; the extras come from a boosted empirical draw with
different household/nature composition); (2) exp19's inverted-U: the
faithful generator's macroF1 optimum sits at lower rare counts, and pushing
past it makes the model predict rare buckets too aggressively (accuracy
collapses as in exp19's arm (f)). Either way, generation-time oversampling
back to the old counts is not the recovery.

**(c) — hard-household selection hurts on the faithful generator.**
0.281 → 0.247 (−0.034), accuracy 0.481 → 0.446. Exp22's 89.3%
gap-closure does not survive the rebaseline — consistent with exp22's own
working-tree run, where (j) scored 0.272 below (b)'s 0.283. Two reasons:
the retry screen itself changed when `ZERO_BASE_WEIGHT` was emptied, so
"retry-selected households" are a different, differently-distorted
population than in exp22; and the screened set confounds selection with
count — 33% fewer rows and starved rare buckets (arithmetic 73, depcare 56,
hhcomp 155), which is where the F1 damage concentrates (arithmetic
0.086 → 0.034, depcare 0.205 → 0.119).

**(d) — the interventions do not compose.** (d) lands exactly on (c)'s
0.247: the extras recover arithmetic (0.034 → 0.082) and hhcomp
(0.063 → 0.081) but sua (0.107 → 0.072) and depcare (0.119 → 0.097) fall
further; net wash, accuracy down again (0.446 → 0.435).

## Verdict
**Hypothesis did not hold.** None of the three recipe interventions
recovers the lost macroF1 on the faithful generator: oversampling to the
old counts costs 0.010, hard-household screening costs 0.034, and the
combination costs 0.034. The new baseline — **faithful persistent +
`class_weight="balanced"` (0.481/0.281)** — remains the best
classifier-training recipe, and the recipe question is now closed: the
macroF1 gap vs the pre-exp24 regime is the honest price of a faithful
generator, and chasing it with training-mix tricks reintroduces the very
distortion the calibration gate was bought with.

Doctrine updates:
- The training recipe is simply "faithful persistent + balanced". The
  retry loop has no remaining role in the recipe (its old edge was the
  distortion, exp24; its selection variant hurts, this experiment).
- Refine "macroF1 is count-driven" (exp9/exp19): arm (b) shows
  same-counts/different-provenance gives different macroF1 — distinct
  rare-example count is necessary but not sufficient; the examples'
  composition matters. Do not cite count alone as the mechanism again.
- Exp19's inverted-U stands and now has a second data point: on the
  faithful generator, oversampling rare buckets past the (lower) optimum
  hurts both macroF1 and accuracy.

## Next steps
1. **(recommended — closes the campaign)** Accept (a) as the
   classifier-training recipe and move remaining effort to the
   LM-pretraining stage, where the faithful generator is the data product.
   No further recipe experiments are staged; this was the last experiment
   in the campaign budget.
2. If the macroF1 gap is ever revisited anyway: disentangle (c)'s
   selection-vs-count confound with a size-matched subsample of (a) before
   concluding anything about household selection per se.
3. Exp22's medical residual (selection closed ~25%, structure ~7% of the
   old retry loop's medical edge) is now moot for the recipe but remains a
   generator-fidelity question if medical transfer is ever targeted
   directly.
4. Any future oversampling work should sweep the boost/target (the
   inverted-U) rather than assuming more rare examples is better.
