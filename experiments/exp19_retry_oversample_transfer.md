# Experiment 19 — Retry-loop + generation-time oversampling on the transfer gate
**Date:** 2026-09-29 · **Code:** `experiments/exp19_retry_oversample_transfer.py`

## Hypothesis
North star gate: **transfer**. Exp 9's verdict was that the retry loop's
element-transfer edge over the persistent generator (acc 0.458 vs 0.443,
macroF1 0.274 vs 0.252) comes from producing ~2x more *distinct*
rare-bucket training cases (hhcomp 672 vs 328, arithmetic 553 vs 238):
decision boundaries are learned from distinct examples, not from
upweighted or duplicated copies — `class_weight="balanced"` rebalances
the *gradient* (mistakes on rare classes are penalized more) but cannot
create examples that were never generated.

We hypothesized the edge is really about distinct-example count: if the
persistent generator explicitly oversamples rare buckets at *generation*
time — generating more distinct cases, never duplicating rows — to match
the retry loop's per-class counts, the transfer gap should close. If it
doesn't, the retry loop's distortion carries something beyond count.

(Metric definitions in `terms.md`: accuracy = fraction of cases where the
predicted element bucket is exactly right; macroF1 = per-bucket F1
averaged plainly, so rare buckets count as much as common ones — the
headline metric for element classification transfer.)

## Method
Exp 9's battery, re-run on the current generator: element task only, v1
features (9 raw; exp4 v3 confirmed v1 beats v2 for element),
`HistGradientBoostingClassifier(random_state=0)`, 20k synth baselines
(seed 7, same command flags as exp9: `--max-attempts 12`), the same real
FY2024 QC test split (17,318 test rows after exp9's bucket filter; the
test set is never touched). Retry-loop arms pass `--no-persistent-buckets`
explicitly (the generate.py default is persistent; no regression of that
fix).

Generation-time oversampling: one 100k-case pool per generator (seed 7, so
the first 20k rows are exactly the exp9 baselines), then extend the rare
buckets (hhcomp, depcare, sua, arithmetic, medical) with distinct extra
cases from the pool remainder until each reaches a target = the retry
loop's distinct 20k count for that bucket (`max()` with the persistent
count, so no bucket is ever downsampled). Base and extra rows are disjoint
slices of one seeded pool, so no case is ever duplicated.

Arms:
- **(a)** persistent, unbalanced — v3 reference
- **(b)** persistent + `class_weight="balanced"` — exp9 reference
- **(c)** retry-loop + `class_weight="balanced"` — exp9 headline (the bar)
- **(d)** persistent + row-duplication oversample-to-uniform — exp9 reference
- **(e)** persistent + generation-time oversample to retry counts + balanced
- **(f)** retry-loop + generation-time oversample to 2x retry counts + balanced
- **(g)** persistent + generation-time oversample to 2x retry counts + balanced

Calibration reading: finding-mix L1 (correct/over/under) for the four
generator pools vs the real finding mix; element-mix and direction-mix L1
for the oversampled training subsets vs the real mixes.

**Caveat — exp9's reference numbers are stale.** The generator changed
between exp9 and exp19 (exp10–15: senior-conditioned bucket mixes,
kid-gated depcare, nature-57 weights, statutory refresh, blank-cause
rule). The 20k replication check confirmed the drift: persistent 20k rare
counts moved hhcomp 328→420, arithmetic 238→262, medical 47→**310**,
depcare 4→**72**; retry-loop hhcomp 672→735, arithmetic 553→508, medical
57→264, depcare 2→82. The calibration work since exp9 largely fixed
rare-bucket starvation in the persistent generator itself. Arms (a)–(d)
therefore re-baseline exp9's configs on the current generator; the
internal comparisons (same generator, same code, same test rows) are what
carry the verdict.

## Results

| Config (synth→real, element, v1) | acc | macroF1 | train rows |
|---|---|---|---|
| (a) persistent, unbalanced | 0.510 | 0.290 | 7,703 |
| (b) persistent + balanced | 0.478 | 0.288 | 7,703 |
| (c) retry-loop + balanced | 0.437 | **0.304** | 7,772 |
| (d) persistent + row-duplication to uniform | 0.473 | 0.296 | 17,944 |
| (e) persistent + gen-oversample 1x + balanced | 0.467 | 0.287 | 8,274 |
| (f) retry-loop + gen-oversample 2x + balanced | 0.401 | 0.286 | 10,277 |
| (g) persistent + gen-oversample 2x + balanced | 0.451 | 0.290 | 10,690 |

Oversample targets actually used (retry-loop distinct 20k counts):
hhcomp 735, arithmetic 508, medical 310, depcare 82, sua 781
(persistent's own 20k already met/exceeded medical 310 and sua 781, so
(e) added only 315 distinct hhcomp + 246 arithmetic + 10 depcare cases).

Per-bucket F1s (rare buckets; full grid in the script output):

| bucket | (b) persist+bal | (c) retry+bal | (e) persist 1x | (f) retry 2x | (g) persist 2x | (d) dup |
|---|---|---|---|---|---|---|
| hhcomp | 0.165 | 0.185 | 0.159 | 0.194 | 0.186 | 0.172 |
| arithmetic | 0.089 | 0.130 | 0.102 | 0.137 | 0.107 | 0.123 |
| medical | 0.175 | 0.279 | 0.181 | 0.264 | 0.202 | 0.180 |
| sua | 0.092 | 0.163 | 0.079 | 0.148 | 0.087 | 0.073 |
| depcare | 0.171 | 0.168 | 0.195 | 0.119 | 0.189 | 0.236 |
| shelter | 0.573 | 0.471 | 0.567 | 0.462 | 0.556 | 0.576 |
| earned | 0.665 | 0.662 | 0.645 | 0.609 | 0.622 | 0.640 |
| unearned | 0.376 | 0.374 | 0.372 | 0.357 | 0.371 | 0.371 |

Key deltas:
- **(e) vs (c)** — count parity: macroF1 0.287 vs 0.304 (gap −0.017
  survives); acc 0.467 vs 0.437 (+0.030). Retry still wins sua, medical,
  hhcomp, arithmetic individually.
- **(g) vs (f)** — count parity at 2x: macroF1 0.290 vs 0.286 (gap −0.004,
  nearly closed but not reversed); acc 0.451 vs 0.401.
- **(f) vs (c)** — dose response, retry: macroF1 0.304→0.286, acc
  0.437→0.401. Doubling distinct rare cases *hurt*.
- **(g) vs (e)** — dose response, persistent: macroF1 0.287→0.290, acc
  0.467→0.451. Doubling is ~neutral on macroF1, costs accuracy.
- **(e) vs (b)** — gen-oversampling vs plain balanced, same generator:
  macroF1 0.287 vs 0.288, acc 0.467 vs 0.478. A wash-to-negative; adding
  571 distinct rare cases didn't even lift hhcomp F1 (0.159 vs 0.165).
- **(e) vs (d)** — distinct generation vs row duplication: macroF1 0.287
  vs 0.296. Duplication wins (note: (d) also rebalances common buckets and
  trains unbalanced on 17,944 rows, so this is not a pure
  distinct-vs-duplicate comparison).

Anti-count evidence: the persistent generator had *more* distinct medical
(310 vs 264) and sua (781 vs 738) cases than the retry loop, yet worse F1
(medical 0.181 vs 0.279, sua 0.079 vs 0.163). More distinct examples did
not buy better boundaries there.

Calibration cost:
- Pool finding-mix L1 vs real (0.603/0.239/0.158): persistent 20k 0.036,
  retry 20k 0.029, persistent 100k 0.036, retry 100k 0.027. The generator
  pools stay faithful — oversampling distorts only the *training* mix, not
  the data product.
- Training-subset element-mix L1 vs real: (e) 0.273, (g) 0.579, (f) 0.616.
  The 2x subsets are heavily distorted, as intended for a training mix.
- Training-subset direction-mix (over/under | error) L1 vs real
  (0.602/0.398): (e) 0.039, (g) 0.024, (f) 0.105.

Mechanism scratch check (15k-case pools, not part of the battery):
per-bucket mean |dollar error| is nearly identical between generators
(hhcomp 226.7 vs 225.7, arithmetic 38.8 vs 36.0, medical 52.5 vs 69.2) —
ruling out "the retry loop records bigger, more decisive corruptions" as
the residual mechanism. One structural difference stands out: retry-loop
error cases carry far more second variances (sua 0.27 vs 0.09, medical
0.26 vs 0.11, shelter 0.22 vs 0.10, hhcomp 0.17 vs 0.06), because the
retry budget redraws the whole case until something materializes.

## Verdict
Hypothesis **did not hold**. Matching the retry loop's distinct
per-class counts at generation time did not close the transfer gap:
(e) 0.287 vs (c) 0.304 on macroF1, and the retry loop still wins four of
five rare buckets individually — including medical and sua, where the
persistent generator actually had *more* distinct training cases. The
distinct-example-count mechanism from exp9 is falsified as the full
explanation: count parity leaves a residual edge, and the dose response
is an inverted U, not monotonic — doubling distinct rare cases hurt the
retry loop (0.304→0.286) and was ~neutral for persistent (0.287→0.290).
Under `class_weight="balanced"`, the retry loop's natural rare-bucket
count is already at or above the macroF1 optimum; pushing past it makes
the model predict rare buckets too aggressively (accuracy collapses:
0.437→0.401 on the retry arm).

The revised picture: **the retry loop's distortion carries something
beyond count.** The scratch check rules out bigger dollar moves. Open
candidates: (1) the retry loop's higher multi-variance rate — its error
cases are structurally different (more second variances), which may give
the classifier richer co-occurrence signal or, conversely, noisier
labels; (2) household selection — retry keeps redrawing until something
materializes, so its error cases are drawn from "easy to move"
households, a selected subpopulation whose error signatures may be more
prototypical.

Doctrine update: "retry-loop + class balancing" is still the best-macroF1
training recipe (0.304), but the *reason* is no longer distinct-example
count — that mechanism is dead, so the recipe now rests on an unexplained
residual. Meanwhile the margin narrowed substantially: plain persistent
unbalanced reaches 0.290 macroF1 with the best accuracy (0.510), because
exp11–13 fixed the starvation that motivated the doctrine in the first
place. For the LM-pretraining stage this matters: the faithful persistent
generator remains the right data product, and the classifier-training
recipe needs its justification re-derived, not inherited from exp9.

## Next steps
1. (Recommended) Ablate the multi-variance candidate: train on retry-loop
   cases restricted to single-variance errors, and separately upsample
   persistent 2-variance cases to the retry rate. If the gap moves, the
   residual edge is case structure, not household selection.
   - **Done →** [exp22](exp22_second_variance_transfer.md): Multi-variance structure ablated: it explains little; household selection explains 89.3% of the gap.
2. Test household selection directly: reweight the retry-loop training set
   to the persistent generator's household-feature distribution (or vice
   versa). If the gap survives, selection isn't the mechanism either.
   - **Done →** [exp22](exp22_second_variance_transfer.md): Household selection tested directly: it is the mechanism.
3. Re-derive the classifier-training recipe from the current generator
   rather than exp9's: with starvation largely fixed, check whether the
   retry loop's 0.014 macroF1 margin over persistent-unbalanced justifies
   training on the distorted mix, or whether the faithful mix + balancing
   is now the simpler recommendation.
   - **Done →** [exp25](exp25_training_recipe.md): Recipe re-derived: faithful persistent + balanced is best; the retry loop has no remaining role.
