# Experiment UT4: prioritization simulation — errors found per reviewer-hour

**Date:** 2026-10-04 · **Code:** `experiments/ut4_prioritization.py`

## Hypothesis

Tied to the north star: a CIO-facing triage metric — if the UT2 finding
signal is real, ranking held-out real UT cases by calibrated P(error)
should find errors faster than random review order, with the value
concentrated in deprioritizing the safe half (the PA4/NY4/SD4
flat-topped-gains shape).

## Method

Retrain UT2's best **ranking** arm exactly: UT-conditioned synthetic
(n=20k, seed 7), HistGradientBoostingClassifier(random_state=0) with
**class_weight="balanced"** (balanced wins UT2 finding binary AUC 3/3
seeds, 0.724 vs 0.697 avg — ranking is this stage's currency, so the
P(error) model uses balanced; documented deviation from NY4/SD4's no-cw
recipe, where no-cw won AUC too), 3-class correct/over/under,
P(error) = 1 − P(correct), CLEAN8 features (UT7). Recalibrate the
error-eager scores on the real-UT **train split** (3,075 rows, disjoint
from the holdout), choosing isotonic vs Platt by 5-fold stratified CV
Brier score; score the 1,026-row holdout once; rank by calibrated
P(error). Report precision@k, lift vs random, errors-per-100-reviews at
10/20/30/40/50% budgets; caught-error anatomy (direction mix, AMTERR
median vs holdout-wide).

## Results

**Calibration:** isotonic chosen (CV Brier 0.17931 vs Platt 0.18142);
calibrated P(error) AUC on holdout 0.7308 (raw 0.7234) — above the
provisional UT8 reference (UT2 seed-7 arm (a) 0.723; UT7's clean-8 delta
was immaterial-to-positive, so no downward adjustment).

| budget | precision | lift | caught | errors/100 reviews |
|---|---|---|---|---|
| top 10% (103) | 0.466 | 1.42x | 48/337 (14.2%) | 46.6 (baseline 32.8) |
| top 20% (205) | 0.483 | 1.47x | 99/337 (29.4%) | 48.3 |
| top 30% (308) | 0.503 | 1.53 | 155/337 (46.0%) | 50.3 |
| top 40% (410) | 0.510 | 1.55x | 209/337 (62.0%) | 51.0 |
| top 50% (513) | 0.487 | 1.48x | 250/337 (74.2%) | 48.7 |

The cumulative-gains curve is flat-topped (PA4/NY4/SD4 shape): lift is
1.42–1.55x across all budgets — the value is deprioritizing the safe
half, not targeting a tiny high-risk list. The riskiest half catches
74.2% of errors with half the reviews.

**Caught-error anatomy (top 20%):** over 54 / under 45 (54.5%/45.5% vs
holdout-wide 57.9%/42.1%); median AMTERR $20 vs $21 holdout-wide, mean
$28.74, p90 $50 — **no small-dollar skew** (unlike PA4's; like NY4's $26
vs $30). The ranker is not just skimming big cases.

## Verdict

**CONDITIONAL PASS.** Calibrated AUC (0.7308) clears the provisional UT8
reference and lift > 1 at every budget (1.42–1.55x). Framed as *triage*:
the riskiest half catches 74.2% of errors with half the reviews — never
as a short high-confidence hit list. Caveats: retrospective ranking on
QC-labeled cases; the holdout-contamination caveat (UT1's offsets saw
pooled FY2022–2024 marginals including holdout rows — UT8 quantifies,
expected small).

## Next steps

- UT5 puts dollars on this ranking (the CIO's real metric).
- UT8 replaces the provisional 0.723 reference with the pristine number;
  if pristine AUC holds, the CONDITIONAL becomes a full PASS.
