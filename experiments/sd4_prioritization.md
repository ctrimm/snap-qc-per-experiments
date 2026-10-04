# Experiment SD4: prioritization simulation — triage, not a hit list

**Date:** 2026-10-03 · **Code:** `experiments/sd4_prioritization.py`
(results: `/tmp/sd45out/sd4_results.json`)

## Hypothesis

Tied to the north star (a CIO-facing triage metric): SD2 showed the
SD-synth finding arm ranks real SD errors above chance (binary AUC 0.728
seed 7) but hard-classifies below the majority baseline — so the
deliverable is a *ranked review queue*, never a short high-confidence hit
list. If calibrated P(error) from SD2's winning arm ranks the shared
holdout's 592 real SD cases with lift > 1 at every review budget, the
triage story holds for the lowest-error-rate state in the nation.

## Method

Mirror of NY4 with STATE="46" and SD7's clean 8-feature set
(`hh_size, earned, unearned, shelter, sua, medical_exp, depcare,
senior_disabled` — `issued_benefit` dropped as post-decision leakage per
SD7, which ran before SD4 per the runbook's new-state ordering).
Retrain SD2's winning arm exactly: SD synth n=20,000 seed 7 (regenerated
at `/tmp/sd45out/sd_synth.jsonl` per the exact commands) + 3-class
`HistGradientBoostingClassifier(random_state=0)`, no class_weight;
P(error) = 1 − P(correct). Recalibrate the error-eager scores on the
real-SD **train split** (1,773 rows, the holdout complement — never the
holdout), choosing isotonic vs Platt by 5-fold stratified CV Brier score;
score the holdout once, rank by calibrated P(error). AMTERR is the
evaluation target only, never a feature.

**Fairness caveat** (carried from SD2): SD1's offsets were fit on pooled
FY2020–2024 SD microdata *including the holdout rows* (pooled marginals
only). SD8's pristine refit was not yet run when SD4 ran — the
contamination premium is unquantified for SD; SD2's seed-7/pristine
comparison will supply it. The SD8 reference in the results JSON is
provisional (SD2's v1 seed-7 AUC 0.7278; SD7 showed the clean-8 delta is
immaterial).

## Results

Holdout: 592 cases, 152 errors, base error rate 0.2568. Calibration:
isotonic chosen (CV Brier 0.16941 vs Platt 0.17458), fit on the 1,773-row
real-SD train split (in-sample Brier 0.16667). Calibrated holdout AUC
0.7239 (raw 0.7228 — calibration is monotone, ranking unchanged).

| review budget | precision | lift vs random | errors caught | share of all errors | errors / 100 reviews |
|---|---|---|---|---|---|
| top 10% (n=59) | 0.322 | 1.25x | 19/152 | 12.5% | 32.2 (base 25.7) |
| top 20% (n=118) | 0.347 | 1.35x | 41/152 | 27.0% | 34.7 |
| top 30% (n=178) | 0.410 | 1.60x | 73/152 | 48.0% | 41.0 |
| top 40% (n=237) | 0.418 | 1.63x | 99/152 | 65.1% | 41.8 |
| top 50% (n=296) | 0.389 | 1.51x | 115/152 | 75.7% | 38.9 |

Lift > 1 at every budget. The curve is flat-topped (PA4/NY4 shape): the
value is *deprioritizing the safe half* — the riskiest half catches
75.7% of errors with half the reviews — not targeting a tiny risky set
(top-10% lift is only 1.25x).

What the ranker catches (top-20% cut): 41 errors, over 21 / under 20
(balanced — SD's direction fingerprint survives ranking); median AMTERR
$23 vs $20 holdout-wide, mean $56.71 — **no small-dollar skew** (NY4's
pattern: caught median $26 vs $30; unlike PA4). The ranker does not cheat
by skimming tiny errors.

## Verdict

**CONDITIONAL PASS** (provisional on SD8's pristine reference). Lift > 1
at every budget; the riskiest-half framing holds (75.7% of errors, half
the reviews). Calibrated AUC 0.7239 sits just under the provisional SD8
reference 0.7278 (SD2's v1 seed-7 number); SD8 will replace the reference
with the true pristine clean-8 figure — expected to move ≤0.02 either way
given SD7's immaterial clean-8 delta and NY8's ~0.02 premium. The
deliverable is framed as *triage*, never a short hit list.

Caveats to state: retrospective ranking on QC-labeled cases; the
holdout-contamination caveat (unquantified until SD8); n=592 holdout with
152 errors — the top-10% cell is 59 cases / 19 errors, so the 1.25x lift
there is noisy.

## Next steps

- SD8's pristine refit replaces the provisional reference; if the
  pristine AUC clears 0.72 the CONDITIONAL becomes a full PASS.
- SD5 (dollar ranking) consumes the same calibrated P(error) machinery.
