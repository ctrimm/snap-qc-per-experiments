# Experiment 4 — Transfer v2: richer shared features on the exp6 generator
**Date:** 2026-09-28 · **Code:** `experiments/exp4_transfer_v2.py`

## Hypothesis
North star gate: **transfer**. Exp 2's residual was synth→real element
accuracy 0.422 vs 0.614 real→real — how much of that gap is features vs
generator fidelity? We hypothesized both contribute: the exp6 generator
(better finding prior, conditional mixes, stochastic-97) should lift all
three tasks, and a richer shared feature set (v2: 19 features vs v1's 9)
should close more of the gap. The v1-vs-v2 ablation on the *same* generator
isolates the feature contribution; exp2's numbers isolate the generator's.

## Method
- Train: 20,000 synthetic cases from the exp6 generator. Test: all 44,891
  real FY2024 QC cases.
- Model: gradient-boosted trees. v1 = exp 2's original 9 features
  (household size, earned, unearned, shelter, sua, medical, depcare,
  senior/disabled, issued benefit). v2 adds 10 derived features, all
  computable in both worlds from agency-view facts: gross/net income, gap
  to max allotment, benefit as fraction of max, review month,
  elderly/disabled counts, earned/unearned indicators, earned share of
  gross.
- Three tasks (binary error/correct, finding 1/2/3, element bucket given
  error), each vs a most-frequent dummy; control is real→real 5-fold CV.

## Results
| Task | Dummy | Synth→real v1 | Synth→real v2 | Real→real |
|---|---|---|---|---|
| Binary (acc / macroF1 / AUC) | 0.603 / 0.376 / — | 0.593 / 0.592 / 0.630 | **0.616 / 0.616 / 0.656** | 0.857 / 0.853 / — |
| Finding 1/2/3 (acc / macroF1) | 0.603 / 0.251 | 0.502 / 0.401 | **0.523 / 0.453** | 0.871 / 0.832 |
| Element \| error (acc / macroF1) | 0.322 / 0.061 | **0.493 / 0.276** | 0.451 / 0.240 | 0.619 / 0.422 |

Exp 2 reference (old generator + v1): binary AUC 0.656 / macroF1 0.567;
finding acc 0.510 / macroF1 0.366; element acc 0.422 / macroF1 0.264.

## Verdict
Hypothesis **held, with a surprise**:
- **Binary:** the prior-mismatch artifact from exp 2 is gone — accuracy
  now beats dummy (0.616 vs 0.603) because the synthetic error rate
  realizes at 0.396 ≈ real 0.397. AUC holds at 0.656; macroF1 improves
  0.567 → 0.616. The calibration work paid off directly in transfer.
- **Finding:** macroF1 0.366 → 0.453 with v2 features. Accuracy (0.523)
  still trails the majority-class dummy (0.603) — expected: any model that
  actually predicts over/under-issuances sacrifices majority-class
  accuracy; macroF1 is the honest metric here.
- **Element:** the generator contributed +0.071 accuracy (0.422 → 0.493 on
  v1) — the better element mix transfers. But the **v2 features hurt**
  (0.493 → 0.451): the derived features (gap-to-max, benefit-frac,
  earned-share) embed our harness's benefit-math assumptions, which don't
  match the real state systems' joint distribution. Rawer features transfer
  better than clever derived ones when the derivation bakes in generator
  assumptions. Lesson for the LM stage: pretraining features/text should
  stay close to observable case facts, not our computed intermediates.
- Element is now at 80% of the real→real accuracy ceiling (0.493/0.619);
  the rest is generator mechanics (hhcomp/arithmetic over-representation,
  medical/depcare under-representation, sua mechanics).

## Next steps
1. (Recommended) Exp 7: per-bucket persistence in the retry loop — the
   hhcomp/arithmetic selection bias is now the binding constraint on
   element transfer.
   - **Done →** [exp7](exp7_per_bucket_persistence.md): Per-bucket persistence cut hhcomp 2.86x → 1.27x and arithmetic 3.47x → 1.42x.
2. Prefer v1-style raw features for any downstream classifier; treat
   derived features as suspect until validated.
3. Re-run this transfer battery after exp 7 and the sua/medical/depcare
   mechanics fixes; the element macroF1 (0.276 vs 0.422 ceiling) is the
   metric to watch.
   - **Done →** [exp4b](exp4_transfer_v3.md): Transfer re-run on the persistent generator: element accuracy fell 0.493 → 0.442 (class starvation), binary improved.
