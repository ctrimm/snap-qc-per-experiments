# Experiment 63 — how much caseworker feedback does "where to look" need?

**Date:** 2026-10-10 · **Code:** `experiments/exp63_feedback_learning_curve.py` · **Results:** `experiments/exp63_results.json`

### Hypothesis

exp62's flag cards rely on a per-state where-to-look model trained on error cases with a known location. States that don't record error locations (TX) would build that label set from reviewer feedback. If the model needs only a few hundred labelled error cases to beat generic advice, a feedback loop can bootstrap it within a pilot. Moves the production track (explanations for reviewers, TX coverage).

### Method

PA, NY and ID. Train the exp61 where-to-look classifier on random subsets of n labelled training error cases (n = 25 … all; 10 repeats per size), score top-2 coverage on the same flagged holdout errors as exp61/62. Baseline per subset: the two most common locations in that subset.

### Results

Top-2 coverage of the real error location on flagged holdout errors (mean of 10 subsets):

| labelled error cases | PA model / generic | NY model / generic | ID model / generic |
|---|---|---|---|
| 25 | 66% / 66% | 50% / 49% | 55% / 55% |
| 50 | 66% / 64% | 65% / 49% | 59% / 56% |
| 100 | 72% / 64% | 68% / 50% | 70% / 55% |
| 200 | 76% / 66% | 70% / 48% | 72% / 55% |
| 400 | 77% / 66% | 73% / 47% | 75% / 55% |
| all (598–1,045) | 78% / 66% | 74% / 39% | 77% / 55% |

Subset-to-subset spread is ±2–5 points from 100 cases on.

**Flagged-only feedback (`--flagged-only`, added 2026-10-10).** In a pilot, reviewers only report on cases the ranker flagged. Restricting the label pool to training errors the ranker would flag (top 20%):

| labelled error cases | PA model / generic | NY model / generic | ID model / generic |
|---|---|---|---|
| 25 | 66% / 65% | 55% / 54% | 54% / 54% |
| 50 | 68% / 65% | 67% / 59% | 58% / 54% |
| 100 | 74% / 66% | 68% / 59% | 70% / 55% |
| 200 | 74% / 66% | 70% / 60% | 69% / 54% |
| 400 | 78% / 66% | 69% / 61% | — |
| all (260–484) | 76% / 66% | 70% / 61% | 65% / 54% |

The model still clears generic advice by 8–15 points from about 100 findings, but it levels off lower in NY and ID (about 70% vs 74–77% with all records), and generic advice built from flagged feedback is stronger (NY 59–61% vs 39–49%), because those labels already come from the right kind of case. ID's last row (65%) is a single fit on 260 cases and sits within the subset spread.

### Verdict

Held. About 100 labelled error cases give most of the gain over generic advice, and about 200 come within a few points of a model trained on five years of records. With realistic flagged-only feedback the gain over generic advice is 8–15 points from about 100 findings, and more feedback adds little after 200. At pilot volumes (a few hundred flagged reviews a month, roughly half of them errors), reviewer feedback could train a usable where-to-look model for a state like TX in two to four months. Until then, its cards would show generic advice.

### Next steps

1. Build the one-step feedback form into the pilot from day one (error or not, which part, dollars).
2. For new states, show generic advice until 100 findings are logged, then switch to the state's own model; refit as feedback grows.
