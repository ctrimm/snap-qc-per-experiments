# Experiment UT7: feature sanity audit — the "defend this to a CIO" check

**Date:** 2026-10-04 · **Code:** `experiments/ut7_feature_audit.py`

## Hypothesis

Tied to the north star: the transfer signal UT2 found must come from
legitimate certification-time process signals (income, deductions,
household composition as the caseworker saw them), not from post-decision
fields or reviewer-coded label smuggling. If the model's top features
match UT3's anatomy and no material leakage survives, the POC numbers
stand.

## Method

1. Retrain UT2's best element arm EXACTLY per its recipe (UT-conditioned
   synthetic n=20k seed 7, HistGradientBoostingClassifier(random_state=0),
   no class_weight, v1 9 features) — must reproduce to ~4 decimals.
2. Two importance measures on the same model: GBM gain shares and
   permutation importance (20 repeats on the holdout, drop in acc and
   macroF1).
3. Leakage audit: trace every v1 feature to its QC field; classify
   known-at-certification vs post-decision/reviewer-coded (anything
   touching AMTERR, RAWBEN, FSBEN, STATUS, or the ELEMENT/NATURE/CAUSE
   label arrays is flagged).
4. Retrain with flagged features removed; report the delta. Adopt the
   clean feature set for all downstream training.

## Results

**Retrain reproduces UT2 to 4 decimals:** acc 0.5119, macroF1 0.1836 —
exact.

**GBM gain shares:** earned 0.2823, shelter 0.2127, unearned 0.1652,
issued_benefit 0.1569, senior_disabled 0.0698, medical_exp 0.0456, depcare
0.0366, hh_size 0.0209, sua 0.0101.

**Permutation importance (holdout, drop in acc):** earned +0.1866 (the
dominant signal by far), shelter +0.0610, senior_disabled +0.0341,
unearned +0.0324, medical_exp +0.0064; sua/depcare/hh_size ~0;
issued_benefit **−0.0260** (negative — permuting it *improves* accuracy;
it is noise to the element task, not signal).

**Cross-check vs UT3's anatomy: passes with a UT accent.** Earned on top
(UT3: earned 1.24x national, earned×97 the #1 pattern at 1.95x), shelter
second (UT3: shelter×53-over at 2.21x, shelter×52-under at 1.33x),
unearned third — exactly the three buckets where UT is most distinctive.
Medical is elevated (0.0456 gain) where UT runs 1.09x. The model keys on
the fingerprint UT3 described.

**Leakage audit:** exactly one post-decision feature —
`issued_benefit` (RAWBEN, the benefit amount actually issued, the decision
outcome). All other eight features trace to cert-time fields (CERTHHSZ,
FSEARN, FSUNEARN, SHELDED, SUA1, FSMEDEXP, FSDEPDED, FSNELDER/FSNDIS).
AMTERR, FSBEN, STATUS, and the label arrays never enter as features.

**Retrain without issued_benefit:** acc 0.5327 (+0.0208), macroF1 0.2009
(+0.0173). Removing the leakage feature *improves* the model — the delta
is immaterial-to-positive, so the POC numbers stand with the corrected
figures. (Same verdict shape as NY7/SD7: one leakage feature, immaterial
delta.)

**Adopted clean feature set (CLEAN8):** hh_size, earned, unearned,
shelter, sua, medical_exp, depcare, senior_disabled. Clean-arm gain
shares: earned 0.3144, shelter 0.2600, unearned 0.1988, senior_disabled
0.0762, medical_exp 0.0518, hh_size 0.0469, depcare 0.0406, sua 0.0112.
UT4/UT5 train on CLEAN8.

## Verdict

**PASS.** (a) Top features match UT3's anatomy — earned/shelter/unearned
on top, exactly where UT is most distinctive. (b) No material leakage:
the single post-decision feature (issued_benefit/RAWBEN) is removed with
a +0.021/+0.017 delta — the POC numbers stand, corrected upward. The
model learns certification-time process signals a caseworker would
recognize: wages on the budget, the shelter deduction, unearned income.

## Next steps

- UT4/UT5 use CLEAN8 (8 features, `issued_benefit` dropped).
- The permutation result (issued_benefit dAcc −0.026) is worth one line in
  the whitepaper's limitations: the issued amount carries no element
  signal beyond what the budget fields already say.
