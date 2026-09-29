# NY2 — NY-filtered transfer: the first decision point of the NY POC track

**Date:** 2026-09-29
**Status:** Complete — decision: **MIXED** (element leg: no pass; finding leg: pass), see Verdict.
**Deliverables (new files only; no existing file modified):**
- `experiments/ny2_ny_transfer.py` — holdout builder + transfer battery
- `experiments/ny2_ny_transfer.md` — this chronicle
- `experiments/ny2_holdout_idx.json` — the shared holdout definition

Plain-language terms: accuracy = share of test cases where the model names
the right answer; macroF1 = the average of the per-bucket F1 scores, treating
every element bucket equally (so a rare bucket like medical counts as much
as shelter — this is why it is the transfer gate's currency alongside
accuracy); binary AUC = how well the model's error-probability ranking
separates error cases from correct ones (0.5 is a coin flip, 1.0 is
perfect); GBM = gradient-boosted trees, the classifier used throughout.

## Hypothesis

NY1's NY-conditioned generator reproduces NY's error *mixes* (finding L1
0.020, element L1 0.044). The NY POC decision point is whether that
NY-specific synthetic signal *transfers*: does a classifier trained on
NY-conditioned synthetic cases predict real NY cases better than
majority-class baseline, better than one trained on national synthetic, and
how far below a real→real ceiling does it sit? The element task is the
transfer gate's currency (accuracy + macroF1); the finding task feeds NY4's
P(error) need. PA2's PASS on this same protocol was bought by PA's
shelter-heavy signature; NY's signature is different (timing-dominated,
medical/sua/hhcomp above national), so the question is genuinely open.

## Method

**Holdout (your choice, documented):** stratified 75/25 split of NY's 3,257
pooled FY2020–2024 QC rows (seed 20260929), stratified on a key where correct
cases form one stratum and error cases are stratified on finding × element
bucket, with ultra-rare buckets (arithmetic, depcare, childsupport,
standard, income_total, other, reporting, the blank) merged into a "rare"
stratum — the 1-member cells (3|income_total, 3|reporting) made sklearn's
splitter refuse, which forced the merge. I chose stratified random over a
temporal train-FY/test-FY split for the same reason as PA2: NY1's offsets
were fit on pooled FY2020–2024 anyway, so a temporal test would measure FY
drift rather than pure transfer, and the stratified split keeps the
real→real ceiling's training pool larger (2,442 vs ~1,629). **The same
holdout serves every arm** — saved at `experiments/ny2_holdout_idx.json`
(815 test rows: 299 error cases; row key = [fy, 0-based index among NY rows
in that FY's CSV]; train = complement). It also serves NY7 and NY8.

**Features:** v1 (9 raw agency-view features), per exp4_v3's verdict that v2's
derived features don't help. Classifier: sklearn
`HistGradientBoostingClassifier(random_state=0)`, defaults, with and without
`class_weight="balanced"` (exp37 warned balanced is GBM-specific — tested
both ways).

**Generation (exact commands):**
```bash
python3 -m src.synth.ny_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out /tmp/ny2out/ny_synth.jsonl
cd src && python3 -m synth.generate --n 20000 --seed 7 \
    --dist ../experiments/dist.json --max-attempts 12 \
    --out /tmp/ny2out/nat_synth.jsonl
# seed-robustness extras: same two commands with --seed 8 / --seed 9
# into ny_synth_s8/s9.jsonl and nat_synth_s8/s9.jsonl
```
**Training/eval (exact command):**
```bash
python3 experiments/ny2_ny_transfer.py \
    --ny-synth /tmp/ny2out/ny_synth.jsonl \
    --nat-synth /tmp/ny2out/nat_synth.jsonl \
    --qc-dir ~/workspace/snap-qc-data/raw \
    --holdout-json experiments/ny2_holdout_idx.json \
    --ny-synth-s8 /tmp/ny2out/ny_synth_s8.jsonl \
    --ny-synth-s9 /tmp/ny2out/ny_synth_s9.jsonl \
    --nat-synth-s8 /tmp/ny2out/nat_synth_s8.jsonl \
    --nat-synth-s9 /tmp/ny2out/nat_synth_s9.jsonl
```
No model weights are written anywhere; NY4/NY7/NY8 retrain via the commands
above plus the holdout JSON.

**Caveat on fairness (read this first):** NY1's offsets were fit on pooled
FY2020–2024 NY microdata, which *includes the holdout rows*. The NY-synth
arms are therefore not pristine with respect to the test set; the real→real
ceiling arm is. The headroom comparison is approximate and slightly favors
the synth arms — the offset fit sees only pooled *marginals*, not the test
rows' labels, so the advantage is small, but it is not zero. NY8 tests this
caveat directly with a pristine refit. Note the caveat cuts both ways for
the verdict below: the NY arms carried the small optimism and still did not
beat national on element.

## Results

### Element classification (299 test error cases), seed 7

| arm | acc | macroF1 | medical F1 | sua F1 | hhcomp F1 | earned F1 | shelter F1 | unearned F1 |
|---|---|---|---|---|---|---|---|---|
| a) NY synth + GBM balanced | 0.381 | 0.157 | 0.213 | 0.275 | 0.000 | 0.633 | 0.408 | 0.260 |
| b) NY synth + GBM no-classweight | 0.435 | 0.168 | 0.065 | 0.129 | 0.000 | 0.646 | 0.491 | 0.354 |
| c) national synth + GBM balanced | 0.408 | 0.187 | 0.364 | 0.210 | 0.308 | 0.685 | 0.424 | 0.269 |
| d) national synth + GBM no-classweight | 0.468 | 0.151 | 0.320 | 0.067 | 0.000 | 0.671 | 0.549 | 0.352 |
| e) REAL→REAL NY ceiling (GBM balanced) | 0.488 | 0.195 | 0.067 | 0.417 | 0.444 | 0.735 | 0.481 | 0.395 |
| f) majority baseline | 0.274 | 0.033 | 0.000 | 0.000 | 0.000 | 0.000 | 0.430 | 0.000 |

### Finding classification (815 test cases), seed 7

| arm | acc | macroF1 | binary AUC (err vs corr) |
|---|---|---|---|
| a) NY synth + GBM balanced | 0.293 | 0.296 | 0.657 |
| b) NY synth + GBM no-classweight | 0.393 | 0.354 | 0.648 |
| c) national synth + GBM balanced | 0.295 | 0.295 | 0.624 |
| d) national synth + GBM no-classweight | 0.356 | 0.323 | 0.611 |
| e) REAL→REAL NY ceiling (GBM balanced) | 0.714 | 0.612 | 0.860 |
| f) majority baseline | 0.633 | 0.259 | 0.500 |

### Seed robustness (seeds 8, 9; arms a–d)

Element accuracy — NY vs national, same class-weight setting:
- seed 7: NY 0.381/0.435 vs nat 0.408/0.468 (national wins both)
- seed 8: NY 0.395/0.458 vs nat 0.431/0.448 (NY no-cw +0.010, nat balanced +0.036)
- seed 9: NY 0.371/0.462 vs nat 0.428/0.468 (national wins both)

Element macroF1 — NY vs national: seed 7: 0.157/0.168 vs 0.187/0.151;
seed 8: 0.137/0.156 vs 0.193/0.182; seed 9: 0.168/0.155 vs 0.169/0.152.
National wins 4 of 6; NY's two wins are +0.017 and +0.003.

Finding binary AUC — NY vs national: seed 7: 0.657/0.648 vs 0.624/0.611;
seed 8: 0.647/0.652 vs 0.635/0.605; seed 9: 0.659/0.624 vs 0.622/0.577.
**NY wins 6 of 6** (+0.02 to +0.05). Finding acc: NY wins 4 of 6 (all four
with no-cw); finding macroF1: NY wins 4 of 6.

No-classweight vs balanced: no-cw beats balanced on element accuracy at
every seed for both NY and national (+0.02 to +0.09); on finding acc and
macroF1 no-cw wins all 12 comparisons. Balanced only helps element macroF1
(4 of 6, small margins).

## Verdict

**MIXED — the element leg does not pass; the finding leg does.** Answering
the three decision questions:

1. **Does NY-specific synthetic signal predict real NY errors above
   baseline? Yes on element, weakly on finding.** Element: NY-synth/no-cw
   reaches acc 0.435 vs 0.274 baseline and macroF1 0.168 vs 0.033 — real
   signal. Finding: hard-prediction accuracy is *below* majority (0.393 vs
   0.633) — same mis-calibration as PA2, the synth-trained classifier
   predicts error too eagerly — but binary AUC 0.648 shows it *ranks* error
   vs correct above chance.
2. **Does NY-conditioning beat national-trained on NY cases? Not on
   element; yes on finding ranking.** Element: national wins or ties on
   accuracy at all 3 seeds (NY wins 1 of 6 comparisons) and wins 4 of 6 on
   macroF1 — there is no NY value-add for the element task. Finding: NY
   wins binary AUC at all 3 seeds and 4 of 6 on acc/macroF1 — NY-conditioning
   consistently improves P(error) ranking.
3. **With or without class_weight? Without, for GBM on NY.** No-classweight
   beats balanced on element accuracy at every seed and on finding acc and
   macroF1 at every seed (12 of 12). This matches PA2's verdict: the
   balanced recipe was tuned on the national mix and loses on the state mix.

**Why NY differs from PA2.** PA2's PASS was bought by shelter: PA's errors
are shelter-heavy (1.45x) and PA-conditioning matched that prior, buying
shelter F1 (0.741 vs 0.679). NY's signature sits in the rare tail — medical
(7.8% of NY errors), sua (8.4%), hhcomp (3.7%) — where the generator has a
mechanics gap the per-bucket F1s expose (NY no-cw: medical 0.065, sua 0.129,
hhcomp 0.000). NY-conditioning shifts training mass toward buckets the
classifier cannot learn, while national-trained keeps mass on
shelter/earned/unearned (82+75+77 = 234 of 299 test errors) where
transferable signal lives. At seed 7 no-cw, national beats NY on medical
(0.320 vs 0.065), shelter (0.549 vs 0.491), earned (0.671 vs 0.646) — the
opposite of PA2's mechanism.

**What this means for the NY chain:** the NY generator's value is on the
finding leg, not the element leg. NY4's P(error) work should use the
NY-synth arm (binary AUC 0.648, consistent NY edge over national at 3
seeds) with threshold calibration on a real-NY validation slice — never
hard classification. If the copilot's element task matters, national-trained
is as good as NY-trained; no NY-specific element story. The open generator
lever is mechanics for medical/sua/hhcomp — the same tail PA2 flagged.

## Next steps

- **NY4** proceeds on the calibrated-ranking plan with the NY-synth arm's
  binary AUC 0.648 as the reference (replaces PA4's 0.645/PA8's 0.691 for
  the NY track).
- **NY8** will test whether the finding-task NY edge survives pristine
  fitting (the contamination caveat above); on element it can only confirm
  the negative — the NY arms had the small optimism and still lost.
- Optional: the medical/sua/hhcomp mechanics question is now NY's version
  of PA2's open lever; a generator extension (97-vs-non97 dollar scales were
  NY1's defined lever) is staged but not started.
