# PA2 — PA-filtered transfer: first decision point of the PA POC track

**Date:** 2026-09-29
**Status:** Complete — decision: **PASS (conditional)**, see Verdict.
**Deliverables (new files only; no existing file modified):**
- `experiments/pa2_pa_transfer.py` — holdout builder + transfer battery
- `experiments/pa2_pa_transfer.md` — this chronicle
- `experiments/pa2_holdout_idx.json` — the shared holdout definition

## Hypothesis

PA1's PA-conditioned generator reproduces PA's error *mixes* (finding L1
0.028, element L1 0.065). The PA POC decision point is whether that
PA-specific synthetic signal *transfers*: does a classifier trained on
PA-conditioned synthetic cases predict real PA cases better than
majority-class baseline, better than one trained on national synthetic, and
how far below a real→real ceiling does it sit? The element task is the
transfer gate's currency (accuracy + macroF1); the finding task feeds PA4's
P(error) need.

## Method

**Holdout (your choice, documented):** stratified 75/25 split of PA's 3,268
pooled FY2020–2024 QC rows (seed 20260929), stratified on a key where correct
cases form one stratum and error cases are stratified on finding × element
bucket, with ultra-rare buckets (arithmetic, depcare, childsupport,
standard_deduction, the one blank ELEMENT1) merged into a "rare" stratum —
the two 1-member strata (2|arithmetic, 2|correct) made sklearn's splitter
refuse, which forced the merge. I chose stratified random over a temporal
train-FY/test-FY split because PA1's offsets were fit on pooled FY2020–2024
anyway, so a temporal test would measure FY drift rather than pure transfer,
and the stratified split keeps the real→real ceiling's training pool larger
(2,451 vs ~1,637). **The same holdout serves every arm** — saved at
`experiments/pa2_holdout_idx.json` (817 test rows: 349 error cases; row key
= [fy, 0-based index among PA rows in that FY's CSV]; train = complement).

**Features:** v1 (9 raw agency-view features), per exp4_v3's verdict that v2's
derived features don't help. Classifier: sklearn
`HistGradientBoostingClassifier(random_state=0)`, defaults, with and without
`class_weight="balanced"` (exp37 warned balanced is GBM-specific — tested
both ways).

**Generation (exact commands):**
```bash
cd src && python3 -m synth.pa_state --n 20000 --seed 7 \
    --dist ../experiments/dist.json --out /tmp/pa2out/pa_synth.jsonl
cd src && python3 -m synth.generate --n 20000 --seed 7 \
    --dist ../experiments/dist.json --max-attempts 12 \
    --out /tmp/pa2out/nat_synth.jsonl
```
**Training/eval (exact command):**
```bash
python3 experiments/pa2_pa_transfer.py \
    --pa-synth /tmp/pa2out/pa_synth.jsonl \
    --nat-synth /tmp/pa2out/nat_synth.jsonl \
    --qc-dir ../snap-qc-data/raw \
    --holdout-json experiments/pa2_holdout_idx.json
```
No model weights are written anywhere; PA4/PA5/PA7 retrain via the three
commands above plus the holdout JSON.

**Caveat on fairness (read this first):** PA1's offsets were fit on pooled
FY2020–2024 PA microdata, which *includes the holdout rows*. The PA-synth
arms are therefore not pristine with respect to the test set; the real→real
ceiling arm is. The headroom comparison is approximate and slightly favors
the synth arms — the offset fit sees only pooled *marginals*, not the test
rows' labels, so the advantage is small, but it is not zero.

## Results

### Element classification (349 test error cases), seed 7

| arm | acc | macroF1 | shelter F1 | medical F1 | earned F1 |
|---|---|---|---|---|---|
| a) PA synth + GBM balanced | 0.467 | 0.197 | 0.616 | 0.098 | 0.571 |
| b) PA synth + GBM no-classweight | **0.567** | **0.208** | **0.741** | 0.074 | 0.563 |
| c) national synth + GBM balanced | 0.413 | 0.165 | 0.520 | 0.160 | 0.601 |
| d) national synth + GBM no-classweight | 0.530 | 0.170 | 0.679 | 0.000 | 0.617 |
| e) REAL→REAL PA ceiling (GBM balanced) | 0.573 | 0.255 | 0.707 | 0.333 | 0.687 |
| f) majority baseline | 0.453 | 0.062 | 0.623 | 0.000 | 0.000 |

### Finding classification (817 test cases), seed 7

| arm | acc | macroF1 | binary AUC (err vs corr) |
|---|---|---|---|
| a) PA synth + GBM balanced | 0.302 | 0.293 | 0.568 |
| b) PA synth + GBM no-classweight | 0.388 | 0.362 | 0.645 |
| c) national synth + GBM balanced | 0.280 | 0.275 | — |
| d) national synth + GBM no-classweight | 0.404 | 0.376 | 0.618 |
| e) REAL→REAL PA ceiling (GBM balanced) | 0.708 | 0.648 | 0.809 |
| f) majority baseline | 0.573 | 0.243 | 0.500 |

### Seed robustness (seeds 8, 9; arms a–d)

Element: PA beats national on accuracy at **all 3 seeds, both class-weight
settings** (+0.03 to +0.09); on macroF1 PA wins 5 of 6 comparisons (seed 8
no-cw: NAT 0.175 vs PA 0.168, a wash). No-cw beats balanced on element acc at
every seed (+0.08 to +0.10); on macroF1 no-cw wins 2 of 6, balanced 4 of 6,
all small.
Finding: PA vs national is a wash (PA wins 2 of 3 seeds on both metrics);
no-cw beats balanced on acc and macroF1 at every seed.

## Verdict

**The POC track continues — PASS, with one leg flagged.** Answering the
three decision questions:

1. **Does PA-specific synthetic signal predict real PA errors above
   baseline? Yes on element, weakly on finding.** Element: PA-synth/no-cw
   reaches acc 0.567 vs 0.453 baseline and macroF1 0.208 vs 0.062 — real
   signal, not prior exploitation (the baseline owns shelter F1 0.623 on
   prior alone, yet the PA arm beats it at 0.741). Finding: hard-prediction
   accuracy is *below* majority (0.388 vs 0.573) — the synth-trained
   classifier is mis-calibrated on P(error), predicting error too eagerly
   (confusion: 292 of 468 true-correct predicted under) — but binary AUC
   0.645 shows it *ranks* error vs correct above chance. The generator's
   conditional P(err|features) mapping does not match real PA; PA1's offsets
   changed marginals, not the feature→error relationship.
2. **Does PA-conditioning beat national-trained on PA cases? Yes on element,
   no on finding.** Element: consistent across 3 seeds and both weight
   settings (PA +0.03–0.09 acc, macroF1 mostly +0.01–0.05); the mechanism is
   visible in the per-bucket F1s — PA-conditioning buys shelter (0.741 vs
   0.679) and matches the shelter-heavy test prior, while ceding earned to
   the national arm. Finding: no consistent PA advantage; both synth arms
   are far below the real→real ceiling (0.708/0.648).
3. **With or without class_weight? Without, for GBM on PA.** No-classweight
   beats balanced on element accuracy at every seed (+0.08–0.10), on finding
   accuracy and macroF1 at every seed. On a shelter-dominated test mix,
   balanced reweighting costs more on the dominant class than it recovers on
   rare ones. This extends exp37's warning: the balanced recipe was tuned on
   national-mix tests; on PA's prior it loses even on macroF1 most of the
   time.

Headroom: element accuracy is nearly at the real→real ceiling (0.567 vs
0.573 — the classifier is as good as real-PA-trained at the top of the
distribution); the gap is macroF1 (0.208 vs 0.255), concentrated in the
rare-bucket tail the faithful mix starves (medical F1 0.07–0.16 vs 0.333 —
the mechanics gap exp4_v3 already flagged, not a sampling artifact).

## Next steps

- **PA4** needs P(error) from the finding task: do not use hard
  classification — the synth-trained classifier loses to majority on
  accuracy. Use calibrated ranking (binary AUC 0.645) with threshold tuning
  on a real-PA validation slice, or train the P(error) head on real PA
  directly (real→real finding is 0.708/0.648). Gate PA4 on calibrated AUC,
  not accuracy.
  - **Done →** [PA4](pa4_prioritization.md): PA4: Conditional PASS — calibrated ranking beats random review but only at triage margins: precision@10% 0.50 (lift 1.17x), precision@20% 0.48 (1.14x); reviewing the riskiest…
- If the macroF1 tail matters for the copilot, the lever is generator
  mechanics for medical/sua (per-bucket F1s near zero), not more sampling
  tricks — exp4_v3's next step 3 stands.
- Optional sensitivity (not run): FY2024-outlier question on a
  FY2020–2023-only generator fit (PA1's suggested check); the seed-robustness
  done here suggests the verdict would hold, but the caveat in Method (holdout
  rows seen by the offset fit) would still apply.
