# Experiment ID8: pristine rerun — closing the fairness caveat

**Date:** 2026-10-04 · **Code:** `experiments/id8_id_pristine_rerun.py --balanced`
(results: `/tmp/id8out/id8_results.json`, scratch; run log:
`/tmp/id8cout/id8_run.txt`)

## Hypothesis

Tied to the north star (honesty): ID2's fairness caveat — the ID1 offsets
were fit on FY2022-2024 microdata *including the holdout rows* — must be
quantified. If the MIXED verdict survives a refit that excludes every
holdout row from every tuning step, it is not a contamination artifact.

## Method

Port of `experiments/sd8_sd_pristine_rerun.py`, run with `--balanced`
(ID2's finding-task winner). A verbatim port of ID1's
`fit_id_targets` with one change: rows whose (fy, state-relative row
index) key appears in `experiments/id2_holdout_idx.json` are skipped
before any aggregate is touched (2,330 kept rows of the 3,111 FY2022-24
fit window; 781 of the 960 holdout rows fall in FY2022-24, 179 are
FY2020-21 and were never in the fit). Refit constants installed by
monkey-patching `src.synth.id_state` (ID1's it2 recipe: pure-empirical →
20k pilot → one-step bucket calibration → coin-cal line search over
{1.05…1.25} → final 20k, seed 7). ID2's battery re-run: pristine-ID synth
vs national synth on the same holdout, GBM balanced, ID7's clean-8
features. The regenerated national arm verified byte-identical to ID2's
file (md5 6f46f0569eb2625cd282f211c7b7fd15) as a sanity check.

## Results

**Pristine refit diagnostics:** coin-cal chose **1.15** (vs ID1's 1.20 —
stable); bucket ratios nearly identical (earned 1.4184 vs 1.4167, shelter
1.2886 vs 1.3036, sua 0.5701 vs 0.5914); pristine finding L1 0.0299. The
refit is stable — excluding 25% of rows moves the constants by <5%.

**Battery (seed 7, balanced, clean-8):**

| task | pristine ID | national | ID-vs-nat gap | ID2 gap (v1, seed 7) |
|---|---|---|---|---|
| element acc | 0.3653 | 0.3096 | **+0.054** | +0.149 |
| element macroF1 | 0.1591 | 0.1613 | −0.002 | +0.019 |
| finding binary AUC | 0.6623 | 0.6454 | **+0.017** | +0.014 |

**Contamination premium (honest accounting):** ID2's ID arm was v1
features; ID8 is clean-8. ID7 measured the v1→clean8 delta on the ID arm
(−0.028 acc / −0.016 macroF1). Implied ID2-on-clean8: acc ~0.4426,
macroF1 ~0.1721. Pristine: 0.3653/0.1591. **Premium ≈ +0.077 acc / +0.013
macroF1** — material on accuracy, unlike NY8's ~0. The holdout rows in the
fit were buying real element-accuracy points, concentrated in shelter
(pristine shelter F1 0.321 vs ID2's 0.560).

**But the verdict-relevant gaps persist:** pristine ID still beats
national on element accuracy (+0.054) and the finding-AUC margin (+0.017)
matches ID2's (+0.014). The macroF1 edge does not survive pristine
conditions (−0.002, noise) — ID2's "wins macroF1 6/6" claim is weakened to
"wins accuracy; macroF1 tied."

## Verdict

**MIXED verdict stands, with a qualification.** The contamination premium
is larger than NY8's (~+0.08 acc on element, not ~0) — disclosed, not
hidden. But: (a) the element *accuracy* edge over national persists
pristine (+0.054); (b) the finding-AUC margin is unchanged (+0.017 vs
+0.014); (c) the refit constants are stable (<5% moves). ID2's MIXED
(element passes on accuracy, finding does not) is not a contamination
artifact — though the element claim is now accuracy-only, not macroF1.

**Reference numbers for ID4/the whitepaper:** the pristine finding AUC
(0.6623) replaces ID2's v1 AUC as the clean reference. ID4's calibrated
AUC (0.6731) clears it — the CONDITIONAL PASS stands.

## Next steps

- The whitepaper reports pristine numbers (0.662 finding AUC; element
  accuracy edge +0.054) with the macroF1 qualification.
- The (a)-rule economics from ID5 rest on P(error) AUC — the load-bearing
  metric — which the pristine rerun confirms.
