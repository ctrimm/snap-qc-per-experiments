# Experiment IDF: household-type review burden of Idaho's P(error)-only winner

**Date:** 2026-10-04 · **Code:** `experiments/idf_id_household_burden.py`
(results: `/tmp/idfout/idf_results.json`, scratch; run log:
`/tmp/id8cout/idf_run.txt`)

## Hypothesis

Exp47 found that PA/NY *dollar-maximizing* rankers are risk-regressive:
they deprioritize elderly/disabled households (the highest-error groups,
ratios 0.22–0.35) because those errors are frequent but small-dollar,
while over-reviewing childless adults (ratios 1.41–1.45). The caveat is
currently scoped to dollar-maximizing rankers. Idaho's ID5 winner is (a)
P(error)-only — which does not chase dollars. Does the regressivity
replicate, or is the scoping correct?

## Method

Exp47 pattern applied to Idaho. Household taxonomy from the FY2024
tech-doc codebook (COMPOSITION/FSELDER/FSDIS), priority elderly >
disabled > composition. Shared holdout (`experiments/id2_holdout_idx.json`,
960). The ID5 winner (a) reproduced exactly: ID synth (seed-7, 20k) +
`HistGradientBoostingClassifier(class_weight="balanced")`, isotonic
calibration on the real-ID train split, clean-8 features. **Reproduction
check:** top-20% recovers $3,000 — matches ID5's published $3,000 exactly.
Per-type review_rate / base_error_rate at top-10%/20%/30%, vs random.

## Results

### ID top-20% (k=192; overall $3,000 / 28.0%, precision 0.479)

| type | n | base_err | rev_rate | prec | ratio rev/base |
|---|---|---|---|---|---|
| elderly | 266 | 0.342 | 0.196 | 0.442 | 0.571 |
| disabled_nonelderly | 253 | 0.431 | 0.233 | 0.475 | 0.541 |
| single_parent | 163 | 0.331 | 0.258 | 0.405 | 0.778 |
| married_with_kids | 70 | 0.443 | 0.300 | 0.619 | 0.677 |
| multiadult_with_kids | 26 | 0.423 | 0.154 | 0.500 | 0.364 |
| childless_adult | 160 | 0.125 | 0.050 | 0.625 | **0.400** |
| other_small | 22 | 0.318 | 0.273 | 0.667 | 0.857 |

Proportionality CV = **0.285** (range 0.364–0.857). Top-10%: CV 0.385
(range 0.100–0.389). Top-30%: CV 0.157 (range 0.798–1.286) — nearly
proportional.

### Comparison vs PA/NY dollar rankers (exp47, top-20%)

| | PA two-part | NY direct | **ID P(error)-only** |
|---|---|---|---|
| proportionality CV | 0.598 | 0.585 | **0.285** |
| elderly ratio | 0.219 | 0.336 | **0.571** |
| disabled ratio | 0.330 | 0.354 | **0.541** |
| childless-adult ratio | 1.409 | 1.447 | **0.400** |

## Verdict

**The risk-regressivity caveat is correctly scoped to dollar-maximizing
rankers and does NOT replicate for Idaho's P(error)-only winner.**
The P(error) ranker is roughly twice as proportional to error risk
(CV 0.285 vs ~0.59). Elderly/disabled households are still somewhat
under-reviewed relative to their risk (0.54–0.57 vs 1.0), but nowhere
near the 0.22–0.35 of the dollar rankers — and childless adults, the
lowest-error group, are *under*-reviewed (0.40), not over-reviewed
(1.41–1.45).

**Mechanism:** dollar rankers chase income errors, which concentrate in
working/childless households, rationally deprioritizing the frequent-but-
small-dollar errors of elderly/disabled households. The P(error) ranker
finds errors wherever they are — and elderly/disabled have the highest
error rates (0.342/0.431), so the ranker reviews them at reasonable rates.
The tilt is a property of the dollar objective, not of ranking per se.

**For the whitepaper:** Idaho's recommended configuration (P(error)-only)
is *fairer* on the review-burden dimension than the dollar rankers — a
genuine advantage of the simpler rule, and one more reason the per-state
rule selection matters. The residual tilt (elderly/disabled 0.54–0.57)
should still be disclosed, with the type-aware-budget mitigation from
exp47 available if the pilot wants it.

## Next steps

- The whitepaper's review-burden note reports these numbers and the
  confirmed scoping.
- If a future Phase 1 selects a dollar-aware rule for ID, re-run this
  analysis on ID data before deployment (the exp47 regressivity would be
  expected to appear).
