# TX2: TX transfer — does TX-conditioned synthetic signal predict real TX errors?

**Date:** 2026-10-03 · **Code:** `experiments/tx2_tx_transfer.py`
**Holdout:** `experiments/tx_holdout_idx.json` (shared across TX2/TX4/TX5/TX7/TX8)

## Hypothesis

TX1 built a TX-conditioned generator with tight calibration (finding L1
0.028, element 0.034, cause 0.029). If the TX conditioning captures real
TX process signal — the underissuance tilt, the depcare/sua-heavy mix, the
nature-99 coding signature — then a gradient-boosted tree (GBM)
classifier trained on TX synthetic cases should predict real TX errors
above the majority baseline, and should beat a national-trained model on
TX cases. Two tasks: element classification on error cases (which benefit
element is in error — accuracy + macroF1, the transfer gate's currency)
and finding classification on all cases (correct vs over vs under —
accuracy, macroF1, and binary AUC, i.e. AUC, a ranking metric where 0.5 is
chance and 1.0 is perfect). Plain-language terms: F1 = harmonic mean of
precision and recall per class (macroF1 averages it); GBM = gradient-
boosted trees, an ensemble of shallow decision trees.

## Method

Stratified 75/25 holdout of TX's 3,457 pooled QC rows (seed 20260929):
correct cases form one stratum; error cases stratified on finding ×
element-bucket-of-slot-1, with ultra-rare buckets (None, arithmetic,
childsupport, standard, standard_deduction, income_total, other,
reporting) merged into "rare" so every stratum can split. TX-specific
adaptation from NY2: depcare stays its own stratum (n=10/20, splittable)
because it is TX's most distinctive bucket (1.59x national) — NY2 had
merged it as ultra-rare. Row key = [fy, 0-based index among TX rows in that
FY's CSV]; train = complement. Saved at `experiments/tx_holdout_idx.json`
(note: the runbook's `<st>2_holdout_idx` pattern is renamed to
`tx_holdout_idx.json` per the track spec). Test: 865 rows (383 errors).

Six arms, sklearn `HistGradientBoostingClassifier(random_state=0)`,
defaults, with and without `class_weight="balanced"`:
(a/b) TX synth balanced/no-cw, (c/d) national synth balanced/no-cw,
(e) REAL→REAL ceiling (GBM balanced on the TX train split),
(f) majority baseline (`DummyClassifier`). Features: v1 (9 raw agency-view
features; TX7 audits this set). N=20,000 synth, seeds 7/8/9 for the
a-d arms (seed-robustness).

**Fairness caveat (NY2's wording, carried over):** TX1's offsets were fit
on pooled FY2020–2024 TX microdata *including the holdout rows*, so the
TX-synth arms are not pristine vs the test set; the offset fit sees only
pooled *marginals*, not test labels — the advantage is small but not zero.
TX8 quantifies it.

## Results

Seed-7 battery (canonical):

| Arm | Element acc | Element macroF1 | Finding acc | Finding macroF1 | Finding binary AUC |
|---|---|---|---|---|---|
| a) TX synth balanced | 0.3570 | 0.1965 | 0.3584 | 0.3493 | 0.694 |
| b) TX synth no-cw | **0.4068** | 0.1846 | **0.4324** | **0.4090** | 0.688 |
| c) national balanced | 0.3648 | 0.1959 | 0.3607 | 0.3532 | 0.689 |
| d) national no-cw | **0.4409** | **0.2043** | 0.3838 | 0.3661 | 0.670 |
| e) REAL→REAL | 0.5013 | 0.3445 | 0.6624 | 0.6141 | 0.837 |
| f) majority | 0.2861 | 0.0404 | 0.5572 | 0.2386 | 0.500 |

Seed robustness, binary AUC (TX a/b vs national c/d):
- seed 7: TX 0.694/0.688 vs nat 0.689/0.670 — TX wins 2/2
- seed 8: TX 0.678/0.688 vs nat 0.686/0.690 — national wins 2/2
- seed 9: TX 0.693/0.687 vs nat 0.717/0.694 — national wins 2/2

TX wins 2 of 6 AUC comparisons. Element accuracy across seeds: TX no-cw
0.407/0.420/0.428 vs national no-cw 0.441/0.428/0.430 — national wins or
ties every seed.

Per-bucket element F1 (seed 7, TX no-cw vs national no-cw): depcare 0.421
vs 0.375 (TX wins on its signature bucket), sua 0.125 vs 0.045, earned
0.614 vs 0.563, medical 0.000 vs 0.250, shelter 0.498 vs 0.563, unearned
0.304 vs 0.382. TX-conditioning buys depcare/sua/earned; national wins
medical/shelter/unearned.

## Verdict

**MIXED — weaker than NY2's MIXED.** Answering the three decision
questions:

1. **Does TX-specific synthetic signal predict real TX errors above
   baseline? Yes.** Element: TX-synth/no-cw reaches acc 0.407 vs 0.286
   baseline and macroF1 0.185 vs 0.040 — real signal. Finding: hard-
   prediction accuracy is *below* majority (0.432 vs 0.557) — the same
   mis-calibration PA2/NY2 saw, the synth-trained classifier predicts
   error too eagerly — but binary AUC 0.688 vs 0.500 shows it *ranks*
   error vs correct well above chance.
2. **Does TX-conditioning beat national-trained on TX cases? Not on
   element; no clear win on finding.** Element: national wins or ties on
   accuracy at all 3 seeds (TX wins 0 of 6 comparisons on acc). Finding:
   TX wins binary AUC 2 of 6 across seeds — a wash, not NY2's 6/6.
   TX-conditioning does not add measurable value over national-training
   for either task.
3. **With or without class_weight? Without, for GBM on TX.** No-
   classweight beats balanced on element accuracy and finding acc/macroF1
   at seed 7 (and the pattern holds across seeds). The balanced recipe was
   tuned on the national mix and loses on the state mix — same as PA2/NY2.

**Why TX differs from NY2.** NY2's MIXED had a clean finding-leg pass
(6/6 AUC) because NY's timing-heavy signature (97 at 62% of errors) gave
the finding classifier a learnable NY-vs-national distinction in the
feature space. TX's signature is *coding practice* (nature 99 "Other" at
24.7%) — and
"reviewer coded Other" has no correlate in agency-view features, so
TX-conditioning shifts training mass toward a pattern the classifier
cannot learn. What transfers is the coarse structure (error vs correct,
which the finding AUC captures); the fine TX accent does not. TX's one
conditioning win is depcare F1 (0.421 vs 0.375) — its most distinctive
*learnable* bucket.

**What this means for the TX chain:** the transferable signal is real but
lives in the finding task's ranking ability, not in TX-conditioning
beating national. TX4's P(error) work uses the TX-synth no-cw arm with
threshold calibration on the real-TX train split — never hard
classification — and reports the national-trained comparison honestly.
Element claims are dropped from the whitepaper (same re-scoping as NY2's
MIXED). TX8 will confirm whether the weak finding edge is a contamination
artifact or real.

## Next steps

- **TX7** (feature audit) runs with `--balanced` OFF (no-cw won).
- **TX4/TX5** use the TX-synth no-cw arm's finding signal, calibrated.
- **TX8** (pristine rerun) is decisive for whether the 2/6 AUC edge is
  contamination or signal.
