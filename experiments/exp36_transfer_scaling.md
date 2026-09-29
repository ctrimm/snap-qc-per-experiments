# Experiment 36 — transfer scaling curve: element transfer vs synthetic N
**Date:** 2026-09-29 · **Code:** `experiments/exp36_transfer_scaling.py`

## Hypothesis
North-star gate: **transfer**. The LM-pretraining corpus has to be sized on
something: this experiment measures where synth-trained classifier transfer
saturates, as the best available proxy for where LM pretraining volume stops
helping. We hypothesized that element transfer (accuracy / macroF1 on real
FY2024 QC) saturates at some synthetic volume N* — beyond which doubling N
buys <0.005 macroF1 — and that N* directly sizes the LM pretraining corpus.

Glossary (see terms.md): *accuracy* = share of real cases where the predicted
element bucket is exactly right; *macroF1* = average per-bucket F1, treating
rare buckets equally with common ones — the headline element-transfer metric;
*class_weight="balanced"* = the classifier penalizes mistakes on rare classes
more heavily (it cannot create examples that were never generated); GBM =
gradient-boosted tree classifier (HistGradientBoostingClassifier), the
discriminative proxy used throughout the recipe experiments.

## Method
Exp25's closed recipe, exactly, applied at five synthetic volumes:

- **Generator:** faithful persistent default (no `--no-persistent-buckets`),
  `--max-attempts 12`, current in-flight defaults, **seed 7 for every N** so
  the curve is not seed noise. Pools: N = 2000, 5000, 10000, 20000, 40000
  cases; the 40000 arm was included because generation ran well under the
  60-minute time box (whole run ~15 min).
- **Training rows:** error rows only (`variances` non-empty): 787 / 1,974 /
  3,990 / 7,979 / 15,920 rows across N. Element task, v1 features (9 raw),
  `HistGradientBoostingClassifier(random_state=0)`, `class_weight="balanced"`.
- **Test split:** the same real FY2024 QC split as exp19/exp22/exp25 —
  17,318 rows, keep-buckets fixed from the N=20000 faithful pool (all 8
  buckets), applied identically to every N. Test set never touched; real
  microdata read in place from
  `~/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv` (never copied
  into the repo).
- **Knee rule (pre-registered):** saturation knee = smallest N where doubling
  N buys <0.005 macroF1.

Reproducibility stamp (in-flight generator; another researcher's edits were
uncommitted at run time, and HEAD moved during the session):

```
git HEAD: 411ddd761f1bc24f1709c434a42c1b8ea948956a
git status --short (relevant entries):
 M experiments/inject.json
 M src/synth/dollar_mech.py
 M src/synth/errors.py
 M src/synth/household.py
?? experiments/exp36_transfer_scaling.py   (this experiment's script)
```

## Results

### Scaling curve (element, v1, balanced, seed 7)

| N (cases) | train error rows | acc | macroF1 | Δacc vs prev | ΔmacroF1 vs prev |
|---|---|---|---|---|---|
| 2,000 | 787 | 0.426 | 0.205 | — | — |
| 5,000 | 1,974 | 0.475 | 0.280 | +0.049 | **+0.075** |
| 10,000 | 3,990 | 0.436 | 0.295 | −0.039 | +0.015 |
| 20,000 | 7,979 | 0.452 | 0.279 | +0.016 | −0.016 |
| 40,000 | 15,920 | 0.449 | 0.292 | −0.003 | +0.013 |

macroF1 against log2(N):

```
0.30 |                       *
0.29 |                    *     *
0.28 |             *
0.27 |
0.26 |
0.25 |
0.24 |
0.23 |
0.22 |
0.21 |  *
     +---------------------------
       2k   5k   10k  20k   40k
```

Doubling gains (macroF1): 2k→5k **+0.075**; 5k→10k +0.015; 10k→20k −0.016;
20k→40k +0.013. Under the pre-registered knee rule the first doubling that
buys <0.005 is 10k→20k (−0.016, a loss) — but 20k→40k then buys +0.013, so
there is no clean monotone knee. The honest read: **macroF1 enters a flat
band of 0.28–0.30 at N≈5,000 and stays there**; everything past 5k is
±0.015 wobble, not a trend. The aggregate signal saturates by
**N* ≈ 5,000–10,000 faithful cases (~2,000–4,000 training error rows)**.

### Per-bucket F1 vs N (rare buckets marked *)

| bucket | 2k | 5k | 10k | 20k | 40k |
|---|---|---|---|---|---|
| earned | 0.604 | 0.663 | 0.681 | 0.678 | 0.669 |
| shelter | 0.520 | 0.545 | 0.460 | 0.514 | 0.529 |
| unearned | 0.259 | 0.359 | 0.361 | 0.362 | 0.356 |
| sua * | 0.076 | 0.103 | 0.158 | 0.093 | 0.119 |
| medical * | 0.115 | 0.137 | 0.175 | 0.186 | **0.205** |
| hhcomp * | 0.015 | 0.015 | 0.127 | 0.128 | **0.153** |
| arithmetic * | 0.044 | **0.152** | 0.121 | 0.108 | 0.089 |
| depcare * | 0.008 | 0.270 | 0.280 | 0.162 | 0.219 |

Three things the aggregate hides:

1. **medical and hhcomp do NOT saturate.** medical climbs 0.115 → 0.205 and
   hhcomp 0.015 → 0.153 across the full range — the rare-bucket tail keeps
   gaining from volume while the aggregate sits still.
2. **arithmetic declines as its own count grows**: 0.152 at N=5k (38 examples)
   → 0.089 at N=40k (332 examples). An 8.7x count increase with F1 nearly
   halved. Second data point for exp19's inverted-U and exp25's
   "provenance, not just count" doctrine: more of the faithful generator's
   arithmetic examples do not teach a better arithmetic detector.
3. **depcare is count-starved noise**: F1 0.008 at N=2k (only 9 training
   rows), then 0.16–0.28 with huge swings. Its swings are a large part of the
   aggregate wobble.

### Replication sanity vs exp25
The N=20000 arm reproduces exp25's arm-(a) macroF1 to 0.002 (0.279 vs 0.281)
but not its accuracy (0.452 vs 0.481). Expected: the generator has in-flight
uncommitted edits between the two measurements, and the accuracy wobble
across N here (±0.04) shows accuracy is noisier than macroF1 under the fixed
seed anyway. The curve is internally valid — all five points share the same
generator, seed, features, and test split.

## Verdict
**Hypothesis partially held — saturation is real, but it is a noisy plateau,
not a clean knee.** There is no continued macroF1 gain from volume past
N≈5,000: the aggregate band is 0.28–0.30 from 5k to 40k with ±0.015 wobble
and no trend, so a strict reading of the knee rule lands N* at 5,000–10,000
cases. Two qualifications for the LM plan:

- **The saturation claim holds only for the aggregate.** The rare-bucket tail
  (medical, hhcomp) keeps improving through 40k, and depcare is still
  count-starved at every N. If the LM copilot must serve the rare buckets —
  it should — the tail argues for *more* than N*, not N* itself.
- **GBM transfer is a proxy for LM transfer, not the thing.** An LM needs
  orders of magnitude more tokens to learn the task format at all; this
  curve sizes the *task-signal* component, not the language-modeling
  component. It says: past ~5–10k faithful cases, the GBM bottleneck is
  feature/distributional fidelity, not volume — volume alone will not fix
  sua (F1 ≤ 0.16 at every N) or arithmetic's decline.

Practically: a 10k-case faithful corpus captures essentially all the
discriminative transfer the aggregate can give; budget beyond that buys the
tail, not the head. The 2k→5k jump (+0.075) also warns that *too-small*
corpora (under ~2k error rows) are genuinely harmful, not just noisier.

## Next steps
1. **(recommended)** Accept N* ≈ 5–10k faithful cases as the task-signal
   sizing input for the LM-pretraining plan, with the explicit tail caveat:
   size the actual pretraining corpus from the rare-bucket requirement
   (medical/hhcomp/depcare still improving at 40k), not from the aggregate.
2. Single-seed caveat: the knee estimate is ±a doubling. If the LM plan
   needs a tighter N*, rerun the curve at seed 11/23 (2 seeds × 5 N ≈
   30 min) and take the mean.
3. sua and arithmetic remain the fidelity problems, not volume problems:
   sua F1 never exceeds 0.16 at any N and arithmetic's F1 falls as its
   count grows — generator-fidelity work (per exp33/exp38 threads), not more
   cases, is the lever for these two.
