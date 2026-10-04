# UT fairness check: household-type review burden for the two-part winner

**Date:** 2026-10-04 · **Code:** `experiments/ut_fairness.py` (exp47
pattern)

## Hypothesis

Tied to the north star: the risk-regressivity caveat is currently scoped
to *dollar-maximizing* rankers (exp47/exp48: PA/NY dollar rankers
deprioritized elderly/disabled households because their errors are
frequent but small-dollar). UT's winner is the two-part P(error)×E[$] — a
dollar-maximizing ranker. Does the caveat hold for UT, or does UT's
different error economics change the scoping?

## Method

Exp47's recipe on UT: household taxonomy from the FY2024 tech-doc
codebook (COMPOSITION/FSELDER/FSDIS; priority elderly > disabled >
composition); shared holdout (1,026 rows); the UT5 two-part winner
reproduced exactly (balanced P(error) + synth-$ regressor, CLEAN8);
per-type review_rate / base_error_rate at top-10/20/30% with a P-alone
comparison arm to isolate the dollar leg's contribution.

## Results

**Two-part winner, top-20% (k=205):** $4,604 recovered (34.1% of $13,519),
precision 0.385.

| type | n | base_err | rev_rate | ratio (rev/base) |
|---|---|---|---|---|
| elderly | 195 | 0.364 | 0.056 | **0.155** |
| disabled_nonelderly | 204 | 0.412 | 0.064 | **0.155** |
| single_parent | 212 | 0.406 | 0.387 | 0.953 |
| married_with_kids | 81 | 0.481 | 0.284 | 0.590 |
| multiadult_with_kids | 28 | 0.643 | 0.321 | 0.500 |
| child_only | 30 | 0.200 | 0.267 | 1.333 |
| childless_adult | 276 | 0.120 | 0.214 | 1.788 |

Proportionality CV = 0.725, range [0.155, 1.788] — highly non-proportional.

**The caveat is confirmed — starkly.** Elderly and disabled households
have the *highest* base error rates (0.364/0.412) but the *lowest*
review-to-risk ratios (0.155): they are reviewed at roughly one-sixth the
rate their error risk warrants. Childless adults (base_err 0.120, the
lowest risk) are over-reviewed at 1.788x. The mechanism: the E[dollar] leg
suppresses elderly/disabled cases because their errors are small-dollar —
the ranker correctly identifies that reviewing them recovers fewer
dollars, but the fairness cost is that their errors (including
*underpayments owed to them*) get less review attention.

**P(error)-alone comparison (top-20%):** elderly 0.366, disabled 0.655,
single_parent 0.605, childless_adult 0.970; CV = 0.318 (vs two-part 0.725).
P-alone is more than twice as proportional — **the dollar leg is the
driver of the regressivity**, not the P(error) leg. (P-alone still
under-reviews elderly at 0.366 — the P(error) model itself carries some
tilt — but the extreme 0.155 is the dollar leg's doing.)

## Verdict

**Scoping CONFIRMED and strengthened.** The risk-regressivity caveat holds
for UT's dollar-maximizing winner — more extremely than in PA/NY
(elderly/disabled at 0.155 vs risk). The P-alone comparison isolates the
cause: the E[dollar] multiplier, not the error-probability model. The
caveat stays scoped to dollar-maximizing rankers; UT adds the nuance that
*within* that class, the regressivity falls hardest on elderly/disabled
households (the highest-error, smallest-dollar groups).

## Next steps

- Whitepaper's review-burden note (unlike SD's, which could waive it for
  P-alone): UT's recommended rule IS dollar-maximizing, so the note must
  state the regressivity plainly and require the type-stratified
  burden analysis as a Phase-1 gate before deployment.
- Operational mitigation for Phase 1: a per-type review floor (e.g.,
  elderly/disabled review rates no lower than X% of their base error
  rate), or a hybrid queue blending P-alone and two-part rankings.
- exp48's over/under-by-household follow-up could quantify how much of
  the unreviewed under-issuance sits with elderly/disabled households.
