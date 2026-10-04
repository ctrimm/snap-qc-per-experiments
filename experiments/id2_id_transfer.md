# Experiment ID2: Idaho-filtered transfer — the first decision point

**Date:** 2026-10-04 · **Code:** `experiments/id2_id_transfer.py`
(results: `/tmp/id2out/id2_results.json`; run log: `/tmp/id8cout/id2_run.txt`)

## Hypothesis

Tied to the north star (does state-conditioned synthetic signal predict
real state errors?): ID1 built an ID-conditioned generator. The three
decision questions (NY2's framing): (1) does ID-specific synthetic signal
predict real ID errors above the majority baseline? (2) does
ID-conditioning beat national-trained on ID cases? (3) with or without
`class_weight="balanced"` for GBM on the state mix?

## Method

Mirror of SD2 with STATE="16". Arms: (a/b) ID synth + GBM
balanced/no-cw, (c/d) national synth + GBM balanced/no-cw, (e) REAL→REAL
ID ceiling (GBM balanced on the ID train split), (f) majority baseline.
Features: v1 (9 raw agency-view features, incl. `issued_benefit` — ID7
audits leakage later). Classifier: sklearn
`HistGradientBoostingClassifier(random_state=0)`, defaults. Two tasks:
element classification on test error cases (accuracy + macroF1 — macroF1
is the unweighted mean of per-class F1, so rare buckets count equally),
and finding classification on all test cases (accuracy, macroF1, binary
AUC — AUC is a ranking metric where 0.5 is chance and 1.0 is perfect,
computed from P(over)+P(under)).

**Holdout** (shared across ID2/ID4/ID5/ID7/ID8): stratified 75/25 split of
ID's 3,839 pooled rows (all FY2020-2024), seed 20260929, saved at
`experiments/id2_holdout_idx.json`. Correct cases form one stratum; error
cases stratified on finding × element-bucket-of-slot-1, with ultra-rare
buckets merged into a "rare" stratum. Row key = [fy, 0-based index among
ID rows in that FY's CSV]; train = complement. Result: **960 test rows,
323 test error cases** (test label mix: earned 85, shelter 138, unearned
53, sua 16, medical 9, …). Confidence intervals are wide on the rare
buckets; per-seed results are reported.

Generation (exact): `python3 -m src.synth.id_state --n 20000 --seed
{7,8,9}` and `cd src && python3 -m synth.generate --n 20000 --seed {7,8,9}
--max-attempts 12` → `/tmp/id2out/`. Train n=20,000 each arm.

**Fairness caveat** (NY2's wording, carried over): the ID1 offsets were
fit on FY2022-2024 ID microdata *including the holdout rows*, so the
ID-synth arms are not pristine vs the test set; the offset fit sees only
pooled *marginals*, not test labels — the advantage is small but not
zero. ID8 quantifies it.

## Results

### Element classification (323 test error cases)

| seed | arm | acc | macroF1 |
|---|---|---|---|
| 7 | a) ID bal | 0.4706 | 0.1881 |
| 7 | b) ID no-cw | 0.4675 | 0.1886 |
| 7 | c) nat bal | 0.3220 | 0.1692 |
| 7 | d) nat no-cw | 0.4737 | 0.1359 |
| 8 | a) ID bal | 0.4458 | 0.1739 |
| 8 | b) ID no-cw | **0.5232** | **0.1848** |
| 8 | c) nat bal | 0.3467 | 0.1530 |
| 8 | d) nat no-cw | 0.4737 | 0.1370 |
| 9 | a) ID bal | 0.4551 | 0.1817 |
| 9 | b) ID no-cw | 0.4954 | 0.1702 |
| 9 | c) nat bal | 0.3158 | 0.1130 |
| 9 | d) nat no-cw | 0.4675 | 0.1316 |
| — | e) REAL→REAL | 0.5294 | 0.1440 |
| — | f) majority | 0.4272 | 0.0499 |

ID beats national on macroF1 **6/6** and on accuracy 5/6 (seed-7 no-cw:
0.4675 vs 0.4737, −0.006). Per-bucket F1 (seed 7, no-cw): earned ID 0.649
vs nat 0.598; shelter 0.535 vs 0.600; unearned 0.321 vs 0.304; sua 0.091
vs 0.129; medical 0.000/0.000. ID-conditioning wins where ID's signature
lives (earned 1.15x, shelter 1.31x national share).

### Finding classification (960 test cases) — binary AUC

| seed | ID no-cw | nat no-cw | Δ | ID bal | nat bal | Δ |
|---|---|---|---|---|---|---|
| 7 | 0.611 | 0.621 | −0.010 | 0.626 | 0.612 | +0.014 |
| 8 | 0.612 | 0.624 | −0.012 | 0.614 | 0.608 | +0.006 |
| 9 | 0.610 | 0.626 | −0.016 | 0.638 | 0.639 | −0.001 |

ID wins finding AUC **2/6**; national wins or ties 4/6. Mean margins:
no-cw −0.013 (national), balanced +0.006 (ID). All margins within ±0.016 —
noise against a ~±0.05 AUC 95% CI. REAL→REAL ceiling: 0.740 (substantial
headroom over all synth arms). Majority baseline: acc 0.6635 / AUC 0.500;
synth hard-prediction accuracy (0.35–0.46) never beats the always-correct
majority — the deliverable is ranking, not hard classification (same
mis-calibration as PA2/NY2/SD2).

### Class weight (Q3)

For GBM on the ID mix: **balanced wins finding AUC 3/3** on the ID arms
(0.626/0.614/0.638 vs 0.611/0.612/0.610); no-cw wins element 4/6 (acc 2/3,
macroF1 2/3). The P(error) ranking work (ID4/ID5) uses the **balanced** arm
— finding AUC is its load-bearing metric — a documented departure from
the PA/NY/SD no-cw recipe.

## Verdict

**MIXED — the mirror image of NY2.** Answering the three decision
questions:

1. **Above the majority baseline? Yes on ranking/discrimination, no on
   raw finding accuracy.** Element: ID arms reach acc 0.47–0.52 vs 0.427
   baseline and macroF1 0.17–0.19 vs 0.050 — real signal. Finding:
   hard-prediction accuracy below majority (0.66), but macroF1 0.34–0.39
   vs 0.266 and binary AUC 0.61–0.64 vs 0.500 — ranks error vs correct
   above chance.
2. **Does ID-conditioning beat national-trained? Yes on element (macroF1
   6/6, acc 5/6), NO on finding (2/6 AUC).** Idaho's signature sits in the
   element mix (shelter/earned), which the element classifier learns; the
   error-vs-correct boundary is not improved over the national mix.
3. **With or without class_weight? With (balanced), for the finding task**
   — balanced wins ID finding AUC 3/3. No-cw keeps a small element edge.

**Why ID differs from SD2/NY2.** SD2 passed on both legs (finding +0.06
mean AUC); NY2 passed finding but not element. ID2 passes element but not
finding. The three states now cover three of the four cells — there is no
universal "state-conditioning always helps finding" story. ID's
finding-AUC tie suggests Idaho's error/no-error boundary is already
well-captured by the national feature→finding conditional; the state's
distinctiveness is compositional (which errors), not separability (whether
error).

**Downstream consequences:** ID4/ID5's P(error) classifier uses arm (a) —
ID synth + GBM **balanced** (best finding AUC, 0.626 mean) — with
threshold/calibration on the real-ID train split (never the holdout). The
whitepaper states the qualification plainly ("the transferable signal is
real, but it lives in the element task, not in fine-grained
error-vs-correct ranking") and drops any claim that ID-conditioning
improves finding ranking. ID8's pristine rerun must confirm the element
pass is not a contamination artifact.

## Next steps

- **ID4/ID5** use arm (a) — ID synth + GBM balanced — for P(error) work,
  with calibration on the real-ID train split, mirroring SD4/SD5's use of
  SD2's winning arm (but the balanced recipe, documented above).
- **ID7** runs before ID4/ID5 are finalized (feature-set audit) — or
  ID4/ID5 carry the clean-8 set with a documented assumption.
- **ID8** pristine rerun: exclude all holdout rows from the ID1 fit,
  regenerate, re-run this battery; the element verdict must survive.
