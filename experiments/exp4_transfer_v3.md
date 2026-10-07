# Experiment 4 — Transfer v3: the persistent generator
**Date:** 2026-09-29 · **Code:** `experiments/exp4_transfer_v2.py` (unchanged;
`src/synth/generate.py` now defaults to `--persistent-buckets`)

## Hypothesis
North star gate: **transfer**. Exp 7 killed the retry loop's bucket lottery
(hhcomp 2.86x→1.27x, arithmetic 3.47x→1.42x), making the synthetic element
mix far more faithful to the real QC file. We hypothesized the faithful mix
would lift element-bucket transfer past exp4 v2's 0.493 accuracy — the
classifier would stop learning a distorted prior. (Metric definitions in
`terms.md`: accuracy = fraction exactly right; macroF1 = F1 averaged over
classes, punishing ignored rare classes; AUC = probability a random positive
outranks a random negative.)

## Method
Identical battery to exp4 v2: train gradient-boosted trees on 20,000
synthetic cases (seed 7), test on all 44,891 real FY2024 QC cases, v1 (9 raw
features) and v2 (19 features), three tasks (binary error/correct, finding
1/2/3, element bucket given error), most-frequent dummy floor and real→real
5-fold CV ceiling. The only change is the generator: `generate.py` now
defaults to persistent (hybrid single-draw-and-drop); the transfer script
itself was not modified. One interface fix was required: `--persistent-
buckets` had been left opt-in (`store_true`, default False) despite the exp7
chronicle claiming persistent as default — changed to
`BooleanOptionalAction(default=True)` with `--no-persistent-buckets` as the
opt-out, so the chronicle's claim is now true.

## Results
| Task (synth→real, v1) | exp4 v2 (retry) | exp4 v3 (persistent) | real→real |
|---|---|---|---|
| Binary acc / macroF1 / AUC | 0.593 / 0.592 / 0.630 | **0.608 / 0.606 / 0.656** | 0.857 / 0.853 |
| Finding acc / macroF1 | 0.502 / 0.401 | 0.462 / 0.387 | 0.871 / 0.832 |
| Element acc / macroF1 | **0.493 / 0.276** | 0.442 / 0.214 | 0.619 / 0.422 |

v2 features: binary 0.639/0.639 (was 0.616/0.616), finding 0.525/0.477 (was
0.523/0.453), element 0.447/0.225 (was 0.451/0.240).

Per-bucket F1, element task, v1, persistent generator: earned 0.616,
shelter 0.549, unearned 0.343, sua 0.090, medical 0.062, hhcomp 0.032,
arithmetic 0.025, depcare 0.000. (Exp2 reference, older generator: earned
0.61, shelter/unearned 0.42, medical 0.28, hhcomp 0.20, arithmetic/sua 0.10,
depcare 0.00.)

## Verdict
Hypothesis **did not hold** — and the failure is the finding. Element
accuracy *fell* 0.493 → 0.442 with the more faithful generator, while binary
and finding improved or held. The per-bucket F1s show where: hhcomp collapsed
0.20 → 0.032, medical 0.28 → 0.062, arithmetic 0.10 → 0.025; only shelter
improved (0.42 → 0.549).

The mechanism is class starvation, not a bug. A classifier is
discriminative: it learns decision boundaries, and rare classes need
*over-sampled* examples to learn — not the true prior. The old generator's
"unfaithful" over-production of hhcomp/arithmetic was accidentally doing the
classifier a favor, feeding it training signal for rare-but-distinctive
buckets. The faithful mix starves them. **Calibration fidelity (matching the
real distribution) and transfer utility (training a good classifier) are
different objectives**: the former wants the true prior, the latter wants
balanced classes. Exp 7 was still the right call for the generator — a
synthetic data product must be faithful — but downstream classifiers should
be trained with class rebalancing (oversampling or class weights), not on
the raw faithful mix.

## Next steps
1. (Recommended) Re-run element transfer with class-balanced training
   (oversample rare buckets to uniform, or `class_weight="balanced"`):
   does the persistent generator's *cleaner feature→bucket mapping* beat
   the old generator once starvation is removed? That isolates fidelity
   from sampling.
   - **Done →** [exp9](exp9_class_balanced_transfer.md): Class-balanced transfer tested: retry-loop + balanced (0.274 macroF1) beat persistent + balanced (0.252).
2. Prefer v1-style raw features (confirmed again: v2's derived features
   don't help element, 0.447 vs 0.442).
3. The sua/medical/depcare mechanics gaps remain (F1s 0.090/0.062/0.000) —
   generator mechanics work, not a sampling artifact.
   - **Partly done →** [exp11](exp11_senior_bucket_mix.md), [exp12](exp12_kid_depcare.md), [exp42](exp42_depcare_medical_deepdive.md): Medical/depcare mechanics improved; SUA still open.
