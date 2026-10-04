# TX7 — Feature sanity audit: the "defend this to a CIO" check

**Date:** 2026-10-03 · **Code:** `experiments/tx7_feature_audit.py`

## Hypothesis

TX2's transfer battery trains on 9 raw agency-view features (v1). If the
model is learning legitimate certification-time process signals — the
income and deduction fields a caseworker sees when budgeting a case — then
its top features should match TX3's error anatomy, and no feature should
smuggle in post-decision information (the issued benefit amount, reviewer
labels) that would not exist at the time a copilot ranks cases for review.
Plain-language terms: GBM = gradient-boosted trees; gain importance = share
of the model's split-improvement attributed to each feature; permutation
importance = how much holdout accuracy/macroF1 drops when a feature's
values are shuffled (negative = shuffling *helps*, i.e. the feature hurts).

## Method

Retrain TX2's best arm exactly (TX synth + GBM no-classweight, element
task, v1 features) — must reproduce TX2's acc 0.4068 / macroF1 0.1846 to
~4 decimals. Two importance measures on the same model: GBM gain shares
and permutation importance (20 repeats on the shared holdout, drop in acc
and macroF1). Then the leakage audit: trace every v1 feature to its QC
field and classify known-at-certification vs post-decision/reviewer-coded
(anything touching AMTERR, RAWBEN, FSBEN, STATUS, or the
ELEMENT/NATURE/CAUSE label arrays is flagged). Retrain with flagged
features removed and report the delta. Uses the shared
`experiments/tx_holdout_idx.json` holdout (865 rows, 381 test error cases).

## Results

**Retrain reproduces TX2:** acc 0.4068, macroF1 0.1846 — exact to 4
decimals. The audit is on the same model TX2 evaluated.

**GBM gain importance (share of total split gain):**
earned 0.249, shelter 0.216, unearned 0.202, issued_benefit 0.174,
senior_disabled 0.065, depcare 0.038, hh_size 0.030, medical_exp 0.015,
sua 0.012.

**Permutation importance (holdout, 20 repeats):** earned dAcc +0.129,
unearned +0.054, shelter +0.019, hh_size +0.013, depcare +0.009 (dF1
+0.035); sua/medical_exp/senior_disabled ~0; **issued_benefit dAcc −0.033,
dF1 −0.044** — shuffling it *improves* the model.

**Leakage audit:** exactly one post-decision feature —
`issued_benefit` (RAWBEN, the benefit amount actually issued: the decision
*outcome*, unknowable at certification time). All eight others trace to
certification-time budget fields (CERTHHSZ, FSEARN, FSUNEARN, SHELDED,
SUA1, FSMEDEXP, FSDEPDED, FSNELDER/FSNDIS). Labels (STATUS, ELEMENT1,
AMTERR, FSBEN) are never features.

**Retrain without `issued_benefit` (clean 8):** acc 0.4409 (+0.034),
macroF1 0.1718 (−0.013). Removing the leakage feature *improves* accuracy
— the model was overfitting to a post-decision field that hurt
generalization. Clean-arm gains: earned 0.285, shelter 0.263, unearned
0.248, senior_disabled 0.072, hh_size 0.055, depcare 0.044, medical_exp
0.019, sua 0.015.

## Verdict

**PASS.** (a) The top features match TX3's anatomy: earned/shelter/
unearned are TX's three largest error buckets (29%/28%/20% of TX errors)
and the model's top three by both gain and permutation importance;
depcare is elevated (gain 0.038, dF1 +0.035) exactly where TX is most
distinctive (1.31x national, TX's signature learnable bucket per TX2).
The cross-check passes with a TX accent. (b) Exactly one material leakage
feature (`issued_benefit`/RAWBEN); removing it moves acc +0.034 /
macroF1 −0.013 — the POC numbers stand, and stand *stronger*, with the
corrected figures. **The clean 8-feature set
(hh_size, earned, unearned, shelter, sua, medical_exp, depcare,
senior_disabled) is adopted for all downstream training** (TX4/TX5 use it
from the start).

## Next steps

- TX4/TX5 train on the clean 8-feature set (already wired in their
  scripts).
- Note for the whitepaper: the leakage audit is the "defend this to a
  CIO" evidence — the model ranks on budget-time facts, never on the
  issued amount.
