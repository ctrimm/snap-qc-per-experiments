# Experiment SD7: feature sanity audit — the "defend this to a CIO" check

**Date:** 2026-10-03 · **Code:** `experiments/sd7_feature_audit.py`
(results: `/tmp/sd7out/sd7_results.json`)

## Hypothesis

Tied to the north star (a ranker a CIO can defend): SD2's best arm (SD
synth + GBM no-classweight, element acc 0.5658 / macroF1 0.2609) must key
on legitimate certification-time process signals — income, deductions,
household facts a caseworker actually sees — not on post-decision fields
or reviewer-coded labels that would smuggle the answer. NY7 found exactly
one post-decision feature (`issued_benefit`/RAWBEN) with an immaterial
delta; SD7 repeats the audit for the SD track and adopts the clean feature
set for SD4/SD5.

## Method

Mirror of NY7 with STATE="46": (1) retrain SD2's best arm exactly (SD
synth n=20,000 seed 7, `HistGradientBoostingClassifier(random_state=0)`
no class_weight — SD2's battery says no-cw wins) on the element task
against the shared holdout (`experiments/sd_holdout_idx.json`, 152 test
error cases); (2) two importance measures on the same model — GBM gain
shares (sum of node split gains per feature across all trees — "gain"
just means how much each split reduced the training loss) and permutation
importance (20 repeats on the holdout: shuffle one feature, measure the
drop in accuracy and macroF1); (3) leakage audit: trace every v1 feature
to its QC field, classify known-at-certification vs post-decision/
reviewer-coded (anything touching AMTERR, RAWBEN, FSBEN, STATUS, or the
ELEMENT/NATURE/CAUSE label arrays is flagged); (4) retrain with flagged
features removed, report the delta; (5) cross-check top features against
SD3's anatomy.

## Results

### Best-arm retrain reproduces SD2

acc 0.5657, macroF1 0.2609 vs SD2 arm (b) 0.5658/0.2609 — exact to ~4
decimals. The recipe is stable.

### Importance: earned income dominates, SD's signature on top

GBM gain shares (v1, 9 features): earned 0.32 (top), shelter 0.24,
unearned 0.21, issued_benefit 0.16, depcare 0.06, senior_disabled 0.04,
medical_exp 0.04, hh_size 0.02, sua 0.01.

Permutation importance on the holdout (drop when shuffled): earned
dAcc +0.224 / dF1 +0.103 — by far the most load-bearing; unearned
+0.080/+0.089; senior_disabled +0.035/+0.049; shelter +0.033/+0.038;
medical_exp +0.015/+0.036; issued_benefit +0.013/+0.055; the rest ~0.

### Cross-check vs SD3's anatomy: passes with a state accent

SD3's fingerprint is timing/reporting on wages (earned 1.45x national,
39% of SD errors), shelter, RSDI/unearned, and medical (1.40x). The
model's top features — earned, shelter, unearned, senior_disabled/
medical_exp — are exactly the certification-time budget lines where SD's
timing errors live. The cross-check passes: the model learns SD's
process-failure fingerprint, not an artifact.

### Leakage audit: one post-decision feature, immaterial delta

`issued_benefit` (RAWBEN — the benefit actually issued, the decision
outcome) is the only post-decision feature, same as PA7/NY7. Everything
else traces to certification-time budget inputs (CERTHHSZ, FSEARN,
FSUNEARN, SHELDED, SUA1, FSMEDEXP, FSDEPDED, FSNELDER/FSNDIS). Retraining
without it: acc 0.5789 (+0.0132), macroF1 0.2605 (−0.0004) — immaterial,
same verdict as NY7 (+0.017/−0.021 there). The POC numbers stand; the
clean-8 set is adopted for all downstream training.

Clean-8 gain shares: earned 0.3245, shelter 0.2442, unearned 0.2139,
depcare 0.0629, senior_disabled 0.0499, medical_exp 0.0463, hh_size
0.0441, sua 0.0141.

## Verdict

**PASS.** (a) Top features match SD3's anatomy — earned income dominates
exactly where SD is most distinctive (1.45x national, 39% of errors), with
shelter/unearned/medical elevated on the timing fingerprint. (b) No
material leakage: the single post-decision feature (`issued_benefit`)
moves accuracy +0.013 and macroF1 −0.000 on removal. **The clean 8-feature
set** (`hh_size, earned, unearned, shelter, sua, medical_exp, depcare,
senior_disabled`) **is adopted for SD4/SD5/SD6/SD8** — SD2's v1 numbers
are superseded by the clean-8 figures wherever the difference matters
(it doesn't: the deltas are noise).

## Next steps

- SD4/SD5 train on the clean-8 set (this audit ran before them, per the
  runbook's ordering for new states).
- SD2's transfer verdict is unaffected (the leakage delta is immaterial).
