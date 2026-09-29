# Experiment 37 — transfer across model classes
**Date:** 2026-09-29 · **Code:** `experiments/exp37_transfer_model_classes.py`

### Hypothesis
The faithful-persistent + class-balanced training recipe (exp25) is a
property of the synthetic data, not of gradient-boosted trees. If the
persistent-vs-retry transfer advantage holds for a linear model and a
neural net too, the recipe generalizes; if it only holds for GBM, the
recipe is model-specific. This matters for the **transfer gate** (gate 2)
and for the LM plan, since a transformer is a third model class entirely.

### Method
Replicated one exp25 transfer arm — **arm (a): faithful persistent 20k +
balanced** — three times, swapping only the classifier:
- (a) `HistGradientBoostingClassifier(random_state=0,
  class_weight="balanced")` — baseline reference (gradient-boosted trees)
- (b) `LogisticRegression(class_weight="balanced", max_iter=5000,
  random_state=0)` on standardized features (linear model)
- (c) `MLPClassifier(hidden_layer_sizes=(100,), max_iter=300,
  random_state=0)` on standardized features, `class_weight="balanced"`
  emulated via sample weights (MLPClassifier has no class_weight
  parameter; weight_i = n / (n_classes * n_class_i)) — one-hidden-layer
  neural net

Each classifier was trained twice: on the persistent pool
(`--max-attempts 12`, persistent-buckets default) and on the retry-loop
pool (`--no-persistent-buckets`), so the persistent-vs-retry ranking can
be compared per model class.

Generation: `python3 -m synth.generate --n 20000 --seed 7 --dist
experiments/dist.json --max-attempts 12 --out <tmp>` from `src/`.
Features: v1 (hh_size, earned, unearned, shelter, sua, medical_exp,
depcare, senior_disabled, issued_benefit), exactly as exp25.

Eval: real FY2024 QC public-use file
(`~/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv`), held
out — never trained on, never copied into the repo. Eval split identical
to exp9/exp19/exp22/exp25: all real rows whose ELEMENT1 element bucket
appears in the persistent baseline — 17,318 of 44,891 rows; buckets:
arithmetic, depcare, earned, hhcomp, medical, shelter, sua, unearned.
Metrics: element **accuracy** (fraction of predictions exactly right) and
**macroF1** (F1 computed per element bucket, then plain-averaged, so rare
error types count equally). "class_weight='balanced'" reweights training
classes inversely to their frequency for the same reason.

Reproducibility: the main run executed against git HEAD
`f515930843d66d784ee1b95288e600de22353bfa` with uncommitted edits from
another researcher's in-flight work (`experiments/inject.json`,
`src/synth/dollar_mech.py`, `src/synth/errors.py`,
`src/synth/household.py` — since committed as `1748ab7`; the uncommitted
exp31 `--dollar-mechanisms` flag is default-off and did not affect
generation). The post-hoc logreg diagnostic (see below) ran at
`1748ab798030371cab96e1103c39d1348c6ebfc7` + that default-off flag; pool
regeneration is internal to each run, so each run's comparisons are
self-consistent.

### Results

**GBM replication check (was the arm reproduced?):** persistent-pool
class counts matched exp24/exp25 seed-7 expectations within tolerance
(hhcomp 271 vs 281 OK; arithmetic 164 vs 166 OK; medical 254 vs 241 OK)
except sua: 719 vs 669 — drifted beyond the ±25 check, attributed to the
in-flight `dollar_mech.py` edits present at run time. GBM/persistent
scored acc 0.452 / macroF1 0.279 vs exp25 arm-(a)'s reported 0.481 /
0.281: macroF1 reproduces within 0.002, accuracy 0.029 lower. The
reference arm is close but not identical — read all deltas below against
that caveat.

**Element accuracy / macroF1 on real FY2024 QC, by model class and pool:**

| model  | persistent      | retry-loop      | persistent−retry macroF1 Δ |
|--------|-----------------|-----------------|----------------------------|
| gbm    | 0.452 / 0.279   | 0.447 / 0.277   | +0.002 → persistent wins (tiny) |
| logreg | 0.175 / 0.158   | 0.374 / 0.242   | −0.084 → **retry wins (large)** |
| mlp    | 0.347 / 0.244   | 0.384 / 0.242   | +0.002 → persistent wins on macroF1 (wash) |

(Train sizes: persistent 7,979 rows / 8 classes; retry 8,150 rows / 8
classes. Retry pool carries more rare-bucket examples: hhcomp 467 vs 271,
arithmetic 316 vs 164.)

**Per-bucket F1, persistent pool, by model class:**

| bucket     | gbm   | logreg | mlp   |
|------------|-------|--------|-------|
| earned     | 0.678 | 0.394  | 0.684 |
| shelter    | 0.514 | 0.069  | 0.283 |
| unearned   | 0.362 | 0.140  | 0.256 |
| sua        | 0.093 | 0.076  | 0.138 |
| medical    | 0.186 | 0.161  | 0.185 |
| hhcomp     | 0.128 | 0.173  | 0.081 |
| arithmetic | 0.108 | 0.147  | 0.082 |
| depcare    | 0.162 | 0.105  | 0.240 |

The standout is logreg/persistent: the worst arm in the table by far
(acc 0.175 — it even misses shelter, the best-represented class, at
F1 0.069), while logreg/retry is a respectable 0.374/0.242.

**Post-hoc logreg diagnostic** (`--diagnose-logreg`; C sweep and
class_weight on/off on both pools, convergence checked via `n_iter_`;
each pool regenerated in-process, so comparisons are self-consistent):

| pool       | C   | class_weight | acc   | macroF1 | converged (n_iter) |
|------------|-----|--------------|-------|---------|--------------------|
| persistent | 0.1 | balanced     | 0.231 | 0.188   | yes (41)           |
| persistent | 1.0 | balanced     | 0.175 | 0.158   | yes (70)           |
| persistent | 10  | balanced     | 0.171 | 0.153   | yes (59)           |
| persistent | 100 | balanced     | 0.169 | 0.152   | yes (58)           |
| persistent | 1.0 | none         | 0.485 | 0.244   | yes (86)           |
| retry      | 0.1 | balanced     | 0.369 | 0.236   | yes (38)           |
| retry      | 1.0 | balanced     | 0.374 | 0.242   | yes (55)           |
| retry      | 10  | balanced     | 0.369 | 0.240   | yes (58)           |
| retry      | 100 | balanced     | 0.368 | 0.239   | yes (60)           |
| retry      | 1.0 | none         | 0.507 | 0.250   | yes (89)           |

The C sweep does not fix the collapse (0.152–0.188 across C=0.1–100),
so it is **not a convergence failure and not under/over-regularization**.
The entire gap is the `class_weight="balanced"` term: turning it off
moves logreg/persistent from 0.175/0.158 to 0.485/0.244 — better than
GBM/persistent on accuracy, tied with MLP on macroF1. On the retry pool,
balanced weights also hurt logreg (0.374/0.242 → 0.507/0.250 without),
just less catastrophically. Mechanism: balanced weights upweight rare
classes up to ~19x (depcare 144/7,979 rows vs shelter 2,721); a linear
model's rigid decision boundaries get yanked toward rare-class regions
and the majority classes collapse (shelter F1 fell to 0.069). GBM's
piecewise-constant trees absorb the same weights without global boundary
distortion. Note the retry pool still edges the persistent pool for
logreg even with weights off (+0.022 acc, +0.006 macroF1) — weak but
consistent evidence that retry-loop cases are somewhat more linearly
separable, matching the materialization-selection story (the retry loop
only keeps cases where the corruption moved the benefit, selecting
"easy", strongly-separated examples; the persistent pool also has fewer
rare-bucket rows: hhcomp 271 vs 467, arithmetic 164 vs 316).

### Verdict
**Hypothesis rejected as stated: the recipe does not transfer as a
whole.** Its two components split apart across model classes:

1. **The faithful-persistent pool is weakly model-agnostic.** On macroF1
   it wins or ties for both nonlinear models (GBM +0.002, MLP +0.002 —
   both tiny, within noise) and loses slightly for the linear model
   (−0.006 with weights off). No model class shows a large persistent
   advantage; the exp25 recipe's persistent-vs-retry edge was always
   small, and it stays small.
2. **`class_weight="balanced"` is NOT model-agnostic.** It is fine for
   GBM (the model exp25 tuned it on) and actively harmful for logistic
   regression — catastrophically on the persistent pool (0.158 → 0.244
   macroF1 when removed) and materially on the retry pool too. The
   headline logreg flip was mostly this interaction, not the pool.

The persistent pool is the harder, more faithful mix (single-draw-and-
drop keeps cases the retry loop's materialization screen would discard;
fewer rare-bucket rows), and it needs model capacity to exploit: the
two nonlinear models handle it, the linear model does slightly better
on the retry pool's easier, more separable cases even after the weight
artifact is removed.

**Implication for the LM plan:** a transformer is a high-capacity
nonlinear model class, so the persistent-pool half of the recipe is
plausibly portable — but this experiment's real lesson is cautionary:
recipe components tuned on one model class do not port for free. The
transfer recipe for LM pretraining data (including whatever replaces
class_weight in a cross-entropy-loss world, e.g. loss reweighting or
resampling) should be re-validated with a transformer-class probe
before locking it, not inherited from GBM results.

### Next steps
1. **(Recommended)** Transformer-class probe: fine-tune a small
   open-weight model (or a small transformer classifier on the v1
   features) on persistent vs retry pools, with and without loss
   reweighting for class balance; confirm which recipe components hold
   for a transformer-class model before locking the LM pretraining
   recipe.
2. MLP class-weight follow-up (small): the MLP used sample-weight-
   emulated balanced weights, which this experiment shows can hurt
   non-tree models; re-run MLP/persistent vs retry with uniform weights
   to see if the persistent ranking strengthens.
