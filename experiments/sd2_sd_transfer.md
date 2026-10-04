# Experiment SD2: SD-filtered transfer — the first decision point

**Date:** 2026-10-03 · **Code:** `experiments/sd2_sd_transfer.py`
(results: `/tmp/sd2out/sd2_results.json`)

## Hypothesis

Tied to the north star (does state-conditioned synthetic signal predict
real state errors?): SD1 built an SD-conditioned generator. The three
decision questions (NY2's framing): (1) does SD-specific synthetic signal
predict real SD errors above the majority baseline? (2) does
SD-conditioning beat national-trained on SD cases? (3) with or without
`class_weight="balanced"` for GBM on the state mix? The scientific stake
is the track's key question: does the transfer signal hold where errors
are rare (SD: 24.75% microdata case-error rate vs 38.6% national)?

## Method

Mirror of NY2 with STATE="46". Arms: (a/b) SD synth + GBM
balanced/no-cw, (c/d) national synth + GBM balanced/no-cw, (e) REAL→REAL
SD ceiling (GBM balanced on the SD train split), (f) majority baseline.
Features: v1 (9 raw agency-view features, incl. `issued_benefit` — SD7
audits leakage later). Classifier: sklearn
`HistGradientBoostingClassifier(random_state=0)`, defaults. Two tasks:
element classification on test error cases (accuracy + macroF1 — macroF1 is
the unweighted mean of per-class F1, so rare buckets count equally), and
finding classification on all test cases (accuracy, macroF1, binary AUC —
AUC is a ranking metric where 0.5 is chance and 1.0 is perfect, computed
from P(over)+P(under)).

**Holdout** (shared across SD2/SD4/SD5/SD7/SD8): stratified 75/25 split of
SD's 2,365 pooled rows, seed 20260929, saved at
`experiments/sd_holdout_idx.json`. Correct cases form one stratum; error
cases stratified on finding × element-bucket-of-slot-1, with ultra-rare
buckets (assets/childsupport/depcare/hhcomp/other/missing — merged 2|rare
n=22, 3|rare n=10) in a "rare" stratum. Row key = [fy, 0-based index among
SD rows in that FY's CSV]; train = complement. Result: **592 test rows,
152 test error cases** — thin, especially per-bucket (sua 5, medical 8
test errors). Confidence intervals are wide; per-seed results are
reported and thin margins are disclosed, NY2-style.

Generation (exact): `python3 -m src.synth.sd_state --n 20000 --seed
{7,8,9}` and `cd src && python3 -m synth.generate --n 20000 --seed {7,8,9}
--max-attempts 12` → `/tmp/sd2out/`. Train n=20,000 each arm.

**Fairness caveat** (NY2's wording, carried over): the SD1 offsets were
fit on pooled FY2020–2024 SD microdata *including the holdout rows*, so
the SD-synth arms are not pristine vs the test set; the offset fit sees
only pooled *marginals*, not test labels — the advantage is small but not
zero. SD8 quantifies it.

## Results

### Element classification (152 test error cases), seed 7

| arm | acc | macroF1 |
|---|---|---|
| a) SD synth balanced | 0.4737 | 0.2045 |
| b) SD synth no-cw | **0.5658** | **0.2609** |
| c) nat synth balanced | 0.4737 | 0.2251 |
| d) nat synth no-cw | 0.5461 | 0.1644 |
| e) REAL→REAL ceiling | 0.6053 | 0.3146 |
| f) majority baseline | 0.3882 | 0.0621 |

Per-bucket F1 (seed 7, no-cw arms — SD's 6 buckets of interest):
earned SD 0.786 vs nat 0.667; medical 0.375 vs 0.000; shelter 0.468 vs
0.586; unearned 0.480 vs 0.556; sua 0.0/0.0 (5 test cases); hhcomp 0.5
vs 0.0 (tiny-n). SD-conditioning wins exactly where SD's signature lives
(earned 39% of SD errors at 1.45x national; medical 1.40x) and loses where
national's mass sits (shelter, unearned).

### Finding classification (592 test cases), seed 7

| arm | acc | macroF1 | binary AUC |
|---|---|---|---|
| a) SD synth balanced | 0.3412 | 0.3051 | 0.7204 |
| b) SD synth no-cw | **0.6537** | **0.4140** | **0.7278** |
| c) nat synth balanced | 0.2889 | 0.2712 | 0.6366 |
| d) nat synth no-cw | 0.3699 | 0.3136 | 0.6382 |
| e) REAL→REAL ceiling | 0.6672 | 0.4444 | 0.7610 |
| f) majority baseline | 0.7432 | 0.2842 | 0.5000 |

### Seed robustness (seeds 8, 9; arms a–d) — finding binary AUC, SD vs national

| seed | SD no-cw | nat no-cw | Δ | SD bal | nat bal | Δ |
|---|---|---|---|---|---|---|
| 7 | 0.7278 | 0.6382 | **+0.090** | 0.7204 | 0.6366 | +0.084 |
| 8 | 0.7109 | 0.6533 | **+0.058** | 0.7257 | 0.6534 | +0.072 |
| 9 | 0.6456 | 0.6283 | +0.017 | 0.6995 | 0.6511 | +0.048 |

SD wins finding AUC **6/6** (mean margin +0.061). The seed-9 no-cw margin
(+0.017) is within noise — disclosed, not hidden.

Element seed robustness (SD vs nat): no-cw acc 2/3 SD wins
(0.5658/0.5461, 0.5526/0.5197, 0.5592/0.5789), no-cw macroF1 3/3 SD wins
(0.261/0.164, 0.159/0.153, 0.219/0.189); balanced acc 1 tie + 2 nat wins,
balanced macroF1 3/3 nat wins.

## Verdict

**PASS — stronger than NY2's MIXED.** Answering the three decision
questions:

1. **Above the majority baseline? Yes on ranking/discrimination, no on
   raw finding accuracy.** Element: SD no-cw reaches acc 0.566 vs 0.388
   baseline and macroF1 0.261 vs 0.062 — real signal. Finding:
   hard-prediction accuracy is below majority (0.654 vs 0.743 — the
   75%-correct class, same mis-calibration as PA2/NY2: the synth-trained
   classifier predicts error too eagerly), but macroF1 0.414 vs 0.284 and
   binary AUC 0.728 vs 0.500 show it ranks error vs correct well above
   chance.
2. **Does SD-conditioning beat national-trained? Yes on finding (6/6),
   yes on element with the no-cw recipe (5/6).** Finding AUC: SD wins at
   all 3 seeds under both class-weight settings (mean +0.061). Element:
   SD no-cw beats nat no-cw on macroF1 at all 3 seeds and accuracy at 2/3;
   the balanced recipe favors national (the recipe was tuned on the
   national mix — same as NY2).
3. **With or without class_weight? Without, for GBM on the SD mix.**
   No-cw beats balanced on 10 of 12 arm×seed×metric comparisons (all 6 at
   seed 7; 4/5 at seeds 8 and 9, losing only finding AUC). Matches PA2/NY2.

**Why SD differs from NY2.** NY2 came back MIXED because NY's signature
sits in the rare tail (medical 7.8%, sua 8.4%, hhcomp 3.7% of NY errors)
where the generator has a mechanics gap. SD's signature sits in the fat
part of the distribution — earned income (39% of SD errors, 1.45x
national) and the timing-97 profile (74.9% of variances) — where SD1's
calibration is faithful. SD-conditioning shifts training mass toward
earned/timing, which the classifier learns; the per-bucket F1s confirm
the mechanism (earned 0.786 vs 0.667, medical 0.375 vs 0.000).

**The key scientific question — does transfer hold where errors are
rare? — answers yes on this evidence.** SD's microdata error rate
(24.75%) is the lowest of the three states, yet SD-conditioning buys a
larger finding-AUC margin over national (+0.06 mean) than NY's (+0.05).
The signal is not an artifact of high base rates.

**Honest qualifications:** (a) n=152 test error cases — per-bucket F1s
are noisy (sua 5 cases, medical 8); (b) the seed-9 no-cw finding margin
(+0.017) is within the ~±0.05 AUC 95% CI; (c) the balanced recipe erases
SD's element edge — the winning recipe is no-cw, documented; (d) raw
finding accuracy never beats the always-correct majority (0.743) — the
deliverable is ranking, not hard classification; (e) the fairness caveat
above — SD8 will quantify the contamination premium.

## Next steps

- **SD4/SD5** use arm (b) — SD synth + GBM no-cw — for P(error) work,
  with threshold/calibration on the real-SD train split (never the
  holdout), mirroring NY4/NY5's use of NY2's winning arm.
- **SD7** runs before SD4/SD5 are finalized (feature-set audit) — or
  SD4/SD5 carry NY's clean-8 set with a documented assumption.
- **SD8** pristine rerun: exclude all holdout rows from the SD1 fit,
  regenerate, re-run this battery; the verdict must survive.
