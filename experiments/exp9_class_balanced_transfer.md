# Experiment 9 — Class-balanced element transfer
**Date:** 2026-09-29 · **Code:** `experiments/exp9_class_balanced_transfer.py`

## Hypothesis
North star gate: **transfer**. Exp 4 v3 found that the more faithful
persistent generator *lowered* element-bucket transfer (acc 0.493 -> 0.442,
macroF1 0.276 -> 0.214) because rare buckets were starved of training
examples (hhcomp F1 0.20 -> 0.032). That verdict blamed the *sampling*, not
the generator's feature->bucket mapping: the persistent generator draws
each bucket once and drops non-materializing corruptions, so its
recorded (feature, bucket) pairs should be cleaner — less contaminated by
the retry loop's redraw lottery. We hypothesized that once starvation is
removed by class rebalancing, the persistent generator's cleaner mapping
would beat the old retry-loop generator on synth->real element transfer.

(Metric definitions in `terms.md`: accuracy = fraction of cases where the
predicted element bucket is exactly right; macroF1 = per-bucket F1 averaged
plainly, so rare buckets count as much as common ones — the headline
metric for element classification transfer.)

## Method
Element task only (bucket given error), v1 features (9 raw; exp4 v3
confirmed v1 beats v2 for element). All configs: train gradient-boosted
trees (`HistGradientBoostingClassifier`, random_state=0) on 20,000
synthetic cases (seed 7), test on the same 44,891 real FY2024 QC cases.
The real test set is never touched — identical rows across configs.
Four configs:
- **(a)** persistent generator (default), unbalanced — reproduces the v3
  reference.
- **(b)** persistent generator + `class_weight="balanced"` (tells the
  classifier to penalize mistakes on rare buckets more, rebalancing by
  gradient rather than by data).
- **(c)** old retry-loop generator (`--no-persistent-buckets`) +
  `class_weight="balanced"`.
- **(d)** persistent generator + explicit oversampling: rare buckets
  resampled with replacement to uniform training counts (2,490 per bucket,
  19,920 training rows).

Secondary check: (b) with v2 features (19 features), since derived
features could in principle interact with balancing.

## Results

| Config (synth->real, element, v1) | acc | macroF1 |
|---|---|---|
| (a) persistent, unbalanced (v3 reference) | 0.442 | 0.214 |
| (b) persistent + class_weight=balanced | 0.443 | 0.252 |
| (c) retry-loop + class_weight=balanced | **0.458** | **0.274** |
| (d) persistent + oversample-to-uniform | 0.430 | 0.262 |
| (b-v2) persistent + balanced, v2 features | 0.422 | 0.230 |

Reference points: real->real 5-fold CV ceiling is 0.619 acc / 0.422
macroF1; exp4 v2's retry-loop *unbalanced* run was 0.493 / 0.276. Config
(a) reproduces the v3 reference exactly (0.442 / 0.214).

Per-bucket F1s (v1):

| bucket | (a) | (b) | (c) retry+balanced | (d) oversample | (b-v2) |
|---|---|---|---|---|---|
| earned | 0.616 | 0.687 | 0.716 | 0.661 | 0.661 |
| shelter | 0.549 | 0.486 | 0.457 | 0.480 | 0.516 |
| unearned | 0.343 | 0.376 | 0.384 | 0.375 | 0.352 |
| sua | 0.090 | 0.157 | 0.186 | 0.165 | 0.105 |
| medical | 0.062 | 0.098 | 0.103 | 0.130 | 0.066 |
| hhcomp | 0.032 | 0.129 | 0.175 | 0.157 | 0.027 |
| arithmetic | 0.025 | 0.084 | 0.103 | 0.082 | 0.057 |
| depcare | 0.000 | 0.000 | 0.072 | 0.049 | 0.055 |

Training class counts (before rebalancing), rare buckets: persistent
hhcomp 328 / arithmetic 238 / medical 47 / depcare 4, vs retry-loop
hhcomp 672 / arithmetic 553 / medical 57 / depcare 2.

Balancing helps the persistent generator (macroF1 0.214 -> 0.252), and
oversampling helps more on the rarest buckets (medical 0.098 -> 0.130,
hhcomp 0.129 -> 0.157), at a small accuracy cost (0.443 -> 0.430: the
model predicts rare buckets more aggressively, misfiring on common ones).
v2 features still lose to v1 (0.230 vs 0.252 macroF1) — v1 raw features
stay the preference for element.

## Verdict
Hypothesis **did not hold**. The headline (b) vs (c) comparison goes to
the old retry-loop generator: 0.458/0.274 vs 0.443/0.252, and the retry
loop also wins every rare bucket individually (hhcomp 0.175 vs 0.129,
depcare 0.072 vs 0.000, sua 0.186 vs 0.157, arithmetic 0.103 vs 0.084).
No per-bucket evidence of a "cleaner feature->bucket mapping" from
persistence.

The mechanism is count, not just prior. `class_weight="balanced"`
rebalances the *gradient* — each rare example counts more — but it cannot
create examples that were never generated. The retry loop's distortion
genuinely produces ~2x more *distinct* hhcomp and arithmetic cases (672 vs
328, 553 vs 238), and decision boundaries for rare buckets are learned
from distinct examples, not from repeated or upweighted ones. Config (d)
confirms the same point from the other side: oversampling persistent
hhcomp's 328 distinct cases to 2,490 copies reaches only F1 0.157, below
the retry loop's 672 distinct cases at 0.175. Starvation is not fully
removable by rebalancing; the generator's raw per-class example count is
the binding constraint.

The revised picture of exp4 v3's "starvation" finding: the retry loop's
"unfaithful" mix is doing *two* favors — a distorted prior *and* more
distinct rare-bucket examples — and only the first is fixable with class
weights. Calibration fidelity (faithful distribution, exp7) remains the
right goal for the synthetic data *product*, but for *training element
classifiers*, the recommended recipe is now: retry-loop generator (or
deliberate rare-bucket oversampling at generation time) + class balancing.
Sua, medical, and depcare mechanics gaps persist under every config
(F1s <= 0.186) — generator mechanics work, not a sampling artifact.

## Next steps
1. (Recommended) Test the interaction term: retry-loop generator +
   explicit oversampling to uniform (was config (c) with config (d)'s
   resampling). If more distinct rare examples is the mechanism, this
   should beat (c)'s 0.274 macroF1.
   - **Done →** [exp19](exp19_retry_oversample_transfer.md): Retry loop + oversampling tested: the count mechanism was falsified (gap survives at count parity).
2. Raise generation-time rare-bucket quotas (e.g. floor each bucket at a
   few hundred *distinct* cases) as a generator knob, then rebalance —
   this makes the "two favors" decomposition a design parameter.
3. Continue sua/medical/depcare mechanics work (exp7 thread); sampling
   cannot fix those.
   - **Partly done →** [exp11](exp11_senior_bucket_mix.md), [exp12](exp12_kid_depcare.md), [exp42](exp42_depcare_medical_deepdive.md): Medical/depcare mechanics improved; SUA still open.
