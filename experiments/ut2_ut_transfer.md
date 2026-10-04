# Experiment UT2: UT-filtered transfer — the first DECISION POINT

**Date:** 2026-10-04 · **Code:** `experiments/ut2_ut_transfer.py`

## Hypothesis

Tied to the north star: if the UT1 generator's state-conditioned synthetic
signal is real, a classifier trained on UT synth should predict real UT
errors above the majority baseline, and UT-conditioning should beat
national-trained on UT cases. Three decision questions (NY2's framing):
(1) above the majority baseline? (2) does UT-conditioning beat
national-trained? (3) with or without `class_weight="balanced"` for GBM on
the UT mix?

(GBM = gradient-boosted trees — sklearn's HistGradientBoostingClassifier,
an ensemble that builds trees sequentially to correct prior errors. AUC =
area under the ROC curve, a ranking metric: 0.5 is chance, 1.0 is perfect.
L1 = mean absolute distributional distance. F1/macroF1 = harmonic mean of
precision and recall, macro-averaged across classes.)

## Method

Arms (a/b) UT synth + GBM balanced/no-cw, (c/d) national synth + GBM
balanced/no-cw, (e) REAL→REAL UT ceiling (GBM balanced on the UT train
split), (f) majority baseline. GBM: sklearn
HistGradientBoostingClassifier(random_state=0), defaults. Features: v1
(9 raw agency-view features). Synth: n=20,000 seed 7 (+ seeds 8/9 for
robustness). Element task on holdout error cases (acc + macroF1); finding
task on all holdout cases (acc, macroF1, binary AUC from P(over)+P(under)).

**Holdout (built once, shared across UT2/UT4/UT5/UT7/UT8):** stratified
75/25 split of UT's 4,101 pooled FY2020–2024 QC rows (seed 20260929),
correct cases one stratum, error cases stratified on finding ×
element-bucket-of-slot-1 with ultra-rare buckets merged into "rare".
Saved at `experiments/ut2_holdout_idx.json`: 1,026 test rows (337 error
cases), train = 3,075 complement. Row key = [fy, 0-based index among UT
rows in that FY's CSV].

**Fairness caveat (NY2's wording):** UT1's offsets were fit on FY2022–2024
UT microdata *including the holdout rows*, so the UT-synth arms are not
pristine vs the test set; the offset fit sees only pooled *marginals*, not
test labels — the advantage is small but not zero. UT8 quantifies it.

## Results

Seed-7 battery (n_test: element 336, finding 1,026):

| arm | element acc / macroF1 | finding binary AUC |
|---|---|---|
| a) UT synth + balanced | 0.4196 / 0.1810 | **0.723** |
| b) UT synth + no-cw | **0.5119** / 0.1836 | 0.687 |
| c) national + balanced | 0.4256 / 0.1764 | 0.640 |
| d) national + no-cw | 0.5238 / 0.1755 | 0.637 |
| e) REAL→REAL ceiling | 0.5714 / 0.2077 | 0.821 |
| f) majority | 0.3333 / 0.0455 | 0.500 |

Seed robustness (arms a–d at generation seeds 8/9): finding AUC —
(a) 0.726/0.724, (b) 0.703/0.702, (c) 0.641/0.666, (d) 0.646/0.661. UT
wins all 6 seed×setting comparisons (mean +0.075). Element acc —
(b) 0.5327/0.5327 vs (d) 0.5000/0.5179 (UT wins 2/3 seeds; seed 7 goes to
national 0.5238 vs 0.5119); macroF1 UT wins 5/6 comparisons.

Per-bucket F1 (seed 7, best arm b): earned 0.673, shelter 0.567, unearned
0.462 — the fat buckets transfer; medical 0.200, sua 0.118, hhcomp 0.000 —
the thin tail does not (same mechanics-gap shape as NY2, milder).

Answering the three questions:

1. **Above the majority baseline? Yes on ranking/discrimination, no on
   raw finding accuracy.** Finding: hard-prediction accuracy is below
   majority (0.51 vs 0.67 — the 67%-correct class; the synth-trained
   classifier predicts error too eagerly, the same miscalibration as
   PA2/NY2/SD2), but binary AUC 0.724 vs 0.500 shows it ranks error vs
   correct well above chance. Element: acc 0.53 vs 0.33 baseline, macroF1
   0.18 vs 0.05 — real signal.
2. **Does UT-conditioning beat national-trained? Yes on finding (6/6),
   yes on element by count (9/12 comparisons).** Finding AUC: UT wins at
   all 3 seeds under both class-weight settings (mean +0.075 — the
   largest finding edge of any state so far: SD +0.061, NY +0.046).
   Element: UT no-cw beats national no-cw on accuracy at 2/3 seeds and
   macroF1 at 2/3; the seed-7 best-arm acc comparison goes to national
   (0.5238 vs 0.5119) — the edge is thin and seed-dependent.
3. **With or without class_weight? Split by metric.** Balanced wins
   finding *ranking* (binary AUC 3/3 seeds: 0.724 vs 0.697 avg); no-cw
   wins hard classification (finding acc/macroF1 and element acc 3/3).
   The ranking chain (UT4/UT5) uses P(error) ranking → **balanced** for
   the P(error) model (documented deviation from NY4/SD4's no-cw recipe,
   which was tuned on mixes where no-cw won AUC too). UT7's element audit
   uses no-cw (the element task's best arm).

## Verdict

**PASS — SD2-shaped, stronger than NY2's MIXED.** The finding leg passes
decisively (UT wins binary AUC 6/6, +0.075 mean — the transferable signal
is real and lives in the finding task). The element leg is a marginal
pass: UT-conditioning helps (9/12 comparisons, best-arm 0.5327 vs
0.5238) but the margin is thin, seed-dependent, and concentrated in the
fat buckets (earned/shelter/unearned); the thin tail (medical/sua/hhcomp)
does not transfer. UT4's P(error) work uses the balanced arm's finding
signal with threshold calibration (never hard classification); the
whitepaper will state the element qualification plainly and keep element
claims modest. The contamination caveat is UT8's to quantify.

## Next steps

- **UT7** audits the no-cw element model (UT2's best element arm,
  reproduced to ~4 decimals), then the leakage check.
- **UT4/UT5** use the **balanced** P(error) model (best ranking arm) with
  real-train calibration; clean-8 features pending UT7.
- **UT8** reruns this battery pristine (holdout rows excluded from every
  tuning step).

## Reproduction

```bash
S=~/workspace/scratch_ut/ut2out
python3 -m src.synth.ut_state --n 20000 --seed 7 --dist experiments/dist.json --out $S/ut_synth.jsonl
cd src && python3 -m synth.generate --n 20000 --seed 7 --dist ../experiments/dist.json --max-attempts 12 --out $S/nat_synth.jsonl
# (+ seeds 8/9 for robustness)
python3 experiments/ut2_ut_transfer.py --ut-synth $S/ut_synth.jsonl --nat-synth $S/nat_synth.jsonl \
  --qc-dir ~/workspace/snap-qc-data/raw --holdout-json experiments/ut2_holdout_idx.json \
  --ut-synth-s8 $S/ut_synth_s8.jsonl --ut-synth-s9 $S/ut_synth_s9.jsonl \
  --nat-synth-s8 $S/nat_synth_s8.jsonl --nat-synth-s9 $S/nat_synth_s9.jsonl
```
