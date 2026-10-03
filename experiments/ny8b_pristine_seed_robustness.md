# NY8b — pristine seed-robustness: does the +0.016 finding edge hold at seeds 8 and 9?

**Date:** 2026-10-03
**Status:** Complete — decision: **PASS**, see Verdict.
**Deliverables (new files only; no existing file modified):**
- `experiments/ny8b_pristine_seed_robustness.py` — per-seed pristine recipe + finding battery
- `experiments/ny8b_pristine_seed_robustness.md` — this chronicle

Plain-language terms: pristine = generator offsets refit on microdata with
the 815 holdout rows excluded before any aggregate is touched; binary AUC =
how well the model's error-probability ranking separates error cases from
correct ones (0.5 = coin flip, 1.0 = perfect); no-classweight = the GBM
setting NY2 found wins for NY on every seed.

## Hypothesis

NY8's pristine refit ran at seed 7 only (finding binary AUC 0.6262 NY
no-classweight vs 0.6107 national no-classweight, edge +0.016). NY2's
contaminated edge held at all 3 seeds, but the pristine gap could be seed
luck. If the NY-vs-national finding edge is positive at seeds 8 and 9 under
the exact pristine recipe, the edge is seed-robust; if it flips sign, NY8's
+0.016 is a seed-7 artifact and the "wins at all three seeds" claim does not
survive pristine fitting.

## Method

**Pristine fit:** NY8's `fit_ny_targets_excl` (holdout rows from
`experiments/ny2_holdout_idx.json` excluded before any aggregate is
touched) — deterministic and seed-independent, so run once and shared
across seeds.

**Per seed (8, 9):** NY8's stage-2 recipe verbatim (see
`experiments/ny8b_pristine_seed_robustness.py`): 20k pilot at
NY_COIN_CAL=1.0 → one-step realized-output calibrations (bucket ratios ×
real/synth share; 97-resolution coins × real/synth P(over|97,b); direction
margins × real/synth on the non-97 slice; depcare/arithmetic sparsity
guards kept) → NY_COIN_CAL grid search over {0.90, 0.93, 0.96, 1.0} on 8k
pilots against the pristine marginal case-error rate → final 20k.
Constants installed by monkey-patching `src.synth.ny_state` (no src edits).
National arm regenerated per NY2's exact recipe
(`python3 -m synth.generate --n 20000 --seed <s> --dist
../experiments/dist.json --max-attempts 12`) at the same seed.

**Transfer battery:** NY2's recipe on the shared 815-row holdout
(`ny2_holdout_idx.json`) — v1 features, sklearn
`HistGradientBoostingClassifier(random_state=0)` **without** class_weight
(NY2's winning setting), finding task only, binary AUC from P(error) =
proba(2)+proba(3). Results in `/tmp/ny8bout/ny8b_results.json` (scratch,
not the repo).

## Results

### Per-seed pristine finding AUC (GBM no-classweight, shared holdout)

| seed | NY no-cw AUC | national no-cw AUC | NY edge | pristine finding L1 | NY_COIN_CAL |
|---|---|---|---|---|---|
| 7 (NY8) | 0.6262 | 0.6107 | **+0.0155** | 0.0434 | 0.93 |
| 8 | 0.6112 | 0.6048 | **+0.0064** | 0.0493 | 0.96 |
| 9 | 0.6407 | 0.5765 | **+0.0642** | 0.0528 | 0.96 |

The NY edge is **positive at all three seeds** (mean +0.029). Three notes:

1. **Seed 8 is thin (+0.0064).** The edge holds but barely — both arms sit
   near 0.60–0.61, i.e. the ranking signal is weak at this seed for both
   models. This is the honest bound on the claim: "wins at all three seeds"
   is true, but at seed 8 it is a +0.006 win.
2. **Seed 9's edge is partly a weak national arm.** National no-cw drops to
   0.5765 (vs 0.6107/0.6048 at seeds 7/8) while NY holds at 0.6407. The edge
   is real — NY's absolute AUC is its best of the three seeds — but the
   +0.064 magnitude should not be quoted alone; it flatters via the
   denominator.
3. **Calibration sensitivity, not mechanics.** The coin-cal grid landed on
   0.96 at both new seeds vs 0.93 at seed 7 (NY8's grid had a 0.93/0.96 tie,
   picked first) — an 8k-pilot line-search wobble. Pristine finding L1 stays
   ~0.05 at all three seeds (0.0434/0.0493/0.0528), all worse than NY1's
   pooled 0.0202: the minus-holdout under-share shortfall (synth ~0.134 vs
   real 0.156) persists across seeds, consistent with NY8's diagnosis of
   calibration noise on 2,442 rows.

## Verdict

**PASS — the pristine finding edge is seed-robust.** NY beats national on
finding binary AUC at all three seeds under the exact pristine recipe
(+0.0155 / +0.0064 / +0.0642, mean +0.029). The "wins at all three random
seeds" claim survives pristine fitting for the no-classweight arm — the arm
the verdicts recommend. Quote the seed-7 pristine 0.626 as the reference
AUC with the 3-seed robustness as the qualifier; do not quote the +0.064
seed-9 edge or the 3-seed mean as the headline. NY4's calibrated-ranking
plan keeps its foundation.

## Next steps

- NY4 proceeds on the calibrated-ranking plan (pristine 0.626 reference,
  seed-robust at 3/3).
- No further seed work on the pristine gap — the open check from NY8's
  next-steps is closed.
