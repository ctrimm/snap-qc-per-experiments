# Experiment ID4: prioritization simulation

**Date:** 2026-10-04 · **Code:** `experiments/id4_id_prioritization.py`
(results: `/tmp/id45out/id4_results.json`, scratch; run log:
`/tmp/id8cout/id4_run.txt`)

## Hypothesis

Tied to the north star (a CIO-facing triage metric — errors found per
reviewer-hour): a calibrated P(error) ranker trained on ID-conditioned
synthetic should beat random review order at every budget, with the value
concentrated in deprioritizing the safe half (the flat-topped
cumulative-gains shape PA4/NY4/SD4 found).

## Method

Port of `experiments/sd4_prioritization.py`. **Recipe (per ID2/ID7):**
ID2's best finding arm — ID synth + GBM **with** `class_weight="balanced"`
(balanced wins finding AUC 3/3 on the ID arms; a documented departure from
the PA/NY/SD no-cw recipe) — 3-class correct/over/under, P(error) = 1 −
P(correct), **clean-8 features** (ID7: `issued_benefit` dropped as
post-decision leakage). Recalibrate the scores on the real-ID **train
split** (2,879 rows — the holdout complement, never the holdout),
choosing isotonic vs Platt by 5-fold stratified CV Brier score; score the
960-case holdout once, rank by calibrated P(error).

## Results

**Calibration:** raw AUC 0.6555 on the train split; CV Brier isotonic
0.20414 vs Platt 0.20630 → isotonic chosen. Holdout: raw AUC 0.6762,
calibrated AUC 0.6731 (calibration is monotone: identical ranking).
Notable: the clean-8 + balanced finding AUC (0.676) exceeds ID2's v1
balanced seed-7 AUC (0.626) — dropping the leakage feature *improved*
finding ranking; `issued_benefit` was noise for error-vs-correct.

| top-k | precision | lift vs random | caught | errors/100 reviews |
|---|---|---|---|---|
| 10% (n=96) | 0.427 | 1.27x | 41/323 (12.7%) | 42.7 (base 33.6) |
| 20% (n=192) | 0.479 | 1.42x | 92/323 (28.5%) | 47.9 |
| 30% (n=288) | 0.476 | 1.41x | 137/323 (42.4%) | 47.6 |
| 40% (n=384) | 0.458 | 1.36x | 176/323 (54.5%) | 45.8 |
| 50% (n=480) | 0.454 | 1.35x | 218/323 (67.5%) | 45.4 |

**What the ranker catches (top-20%):** over 53 / under 39 (57.6%/42.4%
vs holdout-wide 61%/39% — slight under-tilt, no small-dollar skew);
caught median AMTERR $11 vs holdout-wide $18; mean $22.63, p90 $45.

**Cumulative-gains shape:** flat-topped, same as PA4/NY4/SD4 — the value
is deprioritizing the safe half (top-50% catches 67.5% of errors), not
targeting the riskiest few. The deliverable is *triage*, never a short
high-confidence hit list.

## Verdict

**CONDITIONAL PASS.** Lift > 1 at every budget (1.27x–1.42x); the
calibrated AUC (0.6731) will be checked against ID8's pristine reference.
Caveats: retrospective ranking on QC-labeled cases; the
holdout-contamination caveat (ID8 quantifies — expected small, as the
offsets see only pooled marginals).

## Next steps

- ID5 tests whether dollar-aware ranking beats this P(error) baseline —
  the track's key scientific question (does SD's P-alone reversal
  replicate in Idaho?).
  - **Done →** [ID5](id5_id_dollar_ranking.md): ID5: CONDITIONAL PASS — the SD replication: P(error)-alone wins (top-10% 1.77x, top-20% 1.40x, top-30% 1.26x): top-20% $3,000 vs $2,143 random ($31/hr vs $22/hr); over/under $…
- ID8's pristine rerun confirms the 0.6731 AUC is not a contamination
  artifact.
  - **Done →** [ID8](id8_id_pristine_rerun.md): ID8: MIXED stands with qualification — pristine element accuracy edge persists (+0.054 over national) but macroF1 ties (−0.002); finding AUC margin unchanged (+0.017). Contami…
