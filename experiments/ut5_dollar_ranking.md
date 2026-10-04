# Experiment UT5: dollar-impact ranking — the CIO headline

**Date:** 2026-10-04 · **Code:** `experiments/ut5_dollar_ranking.py`

## Hypothesis

Tied to the north star: the whitepaper's headline economics — error
dollars recovered per review hour vs random order. Three ranking
structures tested (PA5's surprise demands all three): (a) calibrated
P(error)-only, (b) two-part P(error)×E[dollars], (c) direct
expected-dollar. **The low-PER panel question:** SD5's reversal was
P(error)-alone winning at 2.07x (dollars so small and uniform that dollar
prediction added only noise). Does UT replicate it, or is SD a one-off?

## Method

Shared 1,026-row holdout (never touched in training; UT2's fairness caveat
carries over). Models: UT2's recipe on UT synth (n=20k, seed 7), CLEAN8
(UT7), GBM; P(error) with class_weight="balanced" (UT2's best ranking arm),
calibrated on the real-UT train split (isotonic/Platt by CV Brier).
AMTERR is the evaluation target only, never an input. Rules at
top-10/20/30%: (a) P(error)-only; (b) two-part = calibrated P(error) ×
E[AMTERR|features] (HistGradientBoostingRegressor on synth *error* cases,
log1p target); (c) direct = one regressor on *all* synth cases, log1p
AMTERR (0 for correct); (b-r)/(c-r) headroom = same structures trained on
the real-UT train split via 5-fold. Metric: actual AMTERR recovered in
top-k vs random; $/hr at the 30-min/case review assumption (sensitivity
15/60 — lift is invariant). Over/under split at top-20%.

## Results

| budget | random | (a) P-only | (b) two-part | (c) direct | headroom (b-r)/(c-r) |
|---|---|---|---|---|---|
| top-10% | $1,357 ($26/hr) | $1,555 1.15x ($30) | $2,011 1.48x ($39) | **$2,102 1.55x ($41)** | 2.47x/2.72x |
| top-20% | $2,701 ($26/hr) | $2,908 1.08x ($28) | **$4,604 1.70x ($45)** | $3,986 1.48x ($39) | 1.92x/2.07x |
| top-30% | $4,058 ($26/hr) | $4,391 1.08x ($29) | **$6,387 1.57x ($41)** | $6,289 1.55x ($41) | 1.88x/1.92x |

**Winner: (b) two-part P(error)×E[dollars]** — wins top-20% and top-30%,
best headline at top-20%: **$4,604 recovered vs $2,701 random (1.70x),
$45/hr vs $26/hr**. Direct wins only the top-10% (1.55x vs 1.48x — more
aggressive at the very top). **P(error)-alone is the worst of the three**
at every budget (1.15x/1.08x/1.08x) — above random (unlike PA/NY, where it
was *below* random at top-10°), but decisively beaten by both dollar-aware
rules.

**The panel answer: SD is (so far) a one-off — UT does NOT replicate the
P-alone reversal.** The mechanism is visible in the oracle: rank the
holdout by *actual* AMTERR and the top-10% of cases hold 74.8% of all
error dollars; the top-20% hold 93.0% (top buckets: earned 76, shelter 54,
unearned 36 cases). UT's dollars, small on average (p50 $22), concentrate
in a heavy tail the dollar models can target — the two-part's E[dollar]
leg earns its keep. SD had no such tail (p90 $70, uniform small errors),
so dollar prediction added only noise there. The panel question's
refinement: it is not "low PER → P-alone wins"; it is "no dollar tail →
P-alone wins". UT is low-PER *with* a tail.

**Over/under split (winner, top-20%):** over $3,124 / under $1,480
(68%/32%) — program savings $30/hr vs ~$15/hr random; under-issuance
$1,480 found (households owed — outreach, not recovery).

**Headroom honesty:** synth two-part 1.70x vs real-trained 1.92x (synth
captures 89% of the headroom — the generator's feature→dollar conditional
is close); synth direct 1.48x vs 2.07x (71%). The binding constraint is
the direct model's dollar conditional, not the two-part's. Log-target
regressors underestimate the mean (Jensen, no smearing — ranking
unaffected; never quote raw expected-$ as point forecasts).

**Calibration note:** (a)'s expected-$ overshoots at top-10% ($2,205
expected vs $1,555 actual) — the P(error)-only rule has no dollar
calibration; the two-part's expected $4,329 vs actual $4,604 is the
closest.

## Verdict

**CONDITIONAL PASS — winner (b) two-part, 1.70x at top-20%.** The
whitepaper's headline: $4,604 vs $2,701 per 205 reviews, $45/hr vs $26/hr
at the 30-min assumption. The panel divergence is the story: UT's winner
is PA-style two-part, not SD-style P-alone — low PER alone does not imply
the P-alone reversal; the dollar tail does the work. Caveats: headroom
(1.70x vs 1.92x); retrospective on QC-labeled cases; UT1's +6.5pp
over-share residual is calibrated out at the margin (winner's over/under
68/32 matches the holdout's 58/42 over-share directionally).

## Next steps

- UT8 reruns the battery pristine; the winner declaration should survive
  (the contamination premium was ~+0.02 AUC in NY8/SD8).
- The fairness check (review-to-risk by household type) runs on the
  **two-part winner** — the risk-regressivity caveat is currently scoped
  to dollar-maximizing rankers; UT confirms or updates that scoping.
- Whitepaper callout table: top-20% $4,604 vs $2,701, $45/hr vs $26/hr,
  34.1% of all error dollars captured ($4,604/$13,519), over $3,124
  savings ($30/hr) / under $1,480 owed.
