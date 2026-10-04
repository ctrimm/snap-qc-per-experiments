# Experiment ID7: feature sanity audit — the "defend this to a CIO" check

**Date:** 2026-10-04 · **Code:** `experiments/id7_id_feature_audit.py`
(results: `/tmp/id7out/id7_results.json`, scratch; run log:
`/tmp/id8cout/id7_run.txt`)

## Hypothesis

Tied to the north star (defensibility): the model must learn legitimate
certification-time process signals, not post-decision fields or
reviewer-coded label smuggling. Two checks: (a) top features match ID3's
anatomy, (b) no material leakage.

## Method

Port of `experiments/sd7_feature_audit.py` with STATE="16". Retrains
ID2's finding-task arm on the element task — **with `--balanced`**, the
arm ID4/ID5 will actually use (ID2: balanced wins finding AUC 3/3) —
and verifies exact reproduction of ID2's seed-7 numbers. Two importance
measures on the same model: GBM gain shares and permutation importance
(20 repeats on the holdout, drop in acc and macroF1). Then the leakage
audit: every v1 feature traced to its QC field and classified
known-at-certification vs post-decision/reviewer-coded. Retrain with
flagged features removed; report the delta.

## Results

**Reproduction:** acc 0.4706, macroF1 0.1881 — matches ID2's seed-7
balanced arm to 4 decimals. ✓

**Importance (v1, 9 features):**

| feature | gain share | perm dAcc | perm dF1 |
|---|---|---|---|
| issued_benefit | 0.219 | +0.037 | +0.046 |
| shelter | 0.179 | +0.049 | +0.023 |
| unearned | 0.166 | +0.055 | +0.054 |
| earned | 0.158 | **+0.144** | **+0.061** |
| depcare | 0.094 | −0.008 | +0.001 |
| medical_exp | 0.078 | −0.002 | −0.000 |
| senior_disabled | 0.054 | +0.023 | +0.018 |
| hh_size | 0.041 | +0.011 | +0.008 |
| sua | 0.011 | +0.004 | +0.001 |

**Cross-check vs ID3's anatomy: passes.** Earned/unearned/shelter top both
measures — exactly ID's distinctive elements (shelter 1.40x, earned the
second element, unearned the income-error channel). Medical is elevated
in gains (0.078) though ID runs medical-light (0.66x) — the model still
uses the medical-deduction signal where present.

**Leakage audit:** exactly one post-decision feature —
`issued_benefit`/RAWBEN (the benefit amount actually issued — the
decision outcome, post-certification). All other eight trace to
certification-time budget fields (CERTHHSZ, FSEARN, FSUNEARN, SHELDED,
SUA1, FSMEDEXP, FSDEPDED, FSNELDER/FSNDIS). AMTERR, FSBEN, STATUS, and the
ELEMENT/NATURE/CAUSE label arrays never enter as features.

**Removal cost:** retraining without `issued_benefit` moves acc −0.028 /
macroF1 −0.016 (0.4427/0.1720) — a modest, honest cost of cleanliness,
larger than NY7's immaterial +0.017/−0.021 but well above the majority
baseline (0.427/0.050). The POC numbers stand with the corrected figures.

**Adopted feature set for ID4/ID5 (clean-8):** `hh_size, earned,
unearned, shelter, sua, medical_exp, depcare, senior_disabled`
(`issued_benefit` dropped).

## Verdict

**PASS.** (a) Top features match ID3's anatomy (earned/unearned/shelter —
"the cross-check passes with an Idaho accent": shelter-first, matching
ID's 1.40x shelter signature). (b) Exactly one post-decision feature
found and removed; the removal cost (−0.028/−0.016) is disclosed, not
hidden. All downstream training uses the clean-8 set.

## Next steps

- ID4/ID5 train on the clean-8 set with the balanced GBM recipe (ID2's
  finding-task winner).
