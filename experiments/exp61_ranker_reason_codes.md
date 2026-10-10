# Experiment 61 — can the ranker say where to look?

**Date:** 2026-10-09 · **Code:** `experiments/exp61_ranker_reason_codes.py` · **Results:** `experiments/exp61_results.json`

### Hypothesis

Ranker-grounded explanations ("why was this case flagged, and what should the caseworker check?") are only as good as the pointer underneath them. If the exp58 ranker's own top reasons point at the part of the case where the error actually was (the eval's T3 element bucket), a plain-language explanation can be built directly on them. Moves the production track (explanations for reviewers).

### Method

For PA, NY, ID, UT and SD (the states that record per-variance amounts, so T3 labels exist; TX doesn't), refit the exp58 ranker on the non-holdout rows with its chosen configuration. Flag the top 20% of each holdout by expected dollars. For flagged cases that turned out to be errors with a T3 label:

1. **Ranker reasons.** Ablate one feature group at a time (set it to the training median) and rank groups by how much the expected-dollar score drops. Nine groups map to T3 buckets (earned, unearned, total income → earned or unearned, shelter, SUA, medical, dependent care, child support, household size). Hit = the real T3 is in the top reason's bucket(s).
2. **"Where to look" model.** A per-state multiclass gradient-boosted classifier, P(T3 | agency-side features), trained on non-holdout error cases. Hit = real T3 in its top one or two buckets.
3. **Baseline.** The state's most common T3 buckets among training error cases.

Each state's holdout has now been used by exp56–58 and here; nothing was selected on it here (one fixed configuration per model).

### Results

Share of flagged error cases where the named part of the case was the real error location:

| state | n | ranker reasons top-1 / top-2 | **where-to-look top-1 / top-2** | baseline top-1 / top-2 |
|---|---|---|---|---|
| PA | 127 | 39% / 54% | **61% / 78%** | 31% / 66% (shelter, earned) |
| NY | 127 | 57% / 67% | **57% / 74%** | 16% / 39% (shelter, unearned) |
| ID | 82 | 40% / 58% | **45% / 77%** | 29% / 55% (shelter, earned) |
| UT | 46 | 30% / 54% | 39% / 61% | 26% / 59% (shelter, earned) |
| SD | 27 | 37% / 70% | 52% / 59% | 44% / 70% (earned, unearned) |

The ranker's top reason is "total income" in 40–65% of flagged cases, and that reason covers two buckets, so its top-1 should be read against the baseline's top-2. On that footing the ranker's reasons beat generic advice only in NY. The issued-benefit size alone accounts for 15–42% of a flagged case's score: much of the flag is "a lot of money is at stake", not "this part looks wrong".

### Verdict

Held in part. The ranker's reasons are faithful to *why* a case scored high (risk and dollars at stake) but are a weak pointer to *where* the error is. A separate where-to-look model on the same agency fields names the right part of the case in its top two for 74–78% of flagged errors in PA, NY and ID, versus 39–66% for generic advice. UT and SD have too few labeled cases to judge.

### Next steps

1. Build explanations from three deterministic layers: the ranker (why flagged, dollars at stake), the where-to-look model (which part first), and a policy-based verification checklist (what to ask for). A language model only rewrites the finished card in plain language (design: `exp62_explainer_design.md`).
2. Add the most common type of mistake within each part (T4, per state) to make the next step more specific.
3. Have reviewers record what they found; that feedback is the training data for the where-to-look model in states that don't record amounts (TX).
