# Experiment 52 — synthetic-only training for the QC eval (SFT→GRPO passes legs 1–2, beats untuned 31B)

**Date:** 2026-10-05 · **Code:** `experiments/exp52_rlvr_dataset.py`, `exp52_rlvr_scoring.py`, `exp52_rlvr_rewards.py`, `exp52_grpo_launch.py`, `exp52_grpo_train.sh`, `exp52_grpo_lora.yaml` · **Calibration:** `experiments/exp52_view_calibration.json`

### In plain English

We want a small language model that can review a SNAP case the way a QC reviewer does: look at what the agency had on file and what the reviewer verified, then say whether the payment was wrong, which way, what caused it, what kind of mistake it was, and whose fault. The exp30 eval measures exactly that on 1,200 real QC cases. Out of the box, the small model we'd deploy (Gemma 4 E4B, about 4B parameters) scores at the level of guessing.

This experiment teaches it on **fake cases only**. Our generator makes realistic synthetic SNAP cases where we know the right answer for certain, because we created the error. We show the model a fake case in exactly the eval's format, let it answer, and reward it for each question it gets right. Over many rounds it should get better at the questions. That training style is called RLVR (reinforcement learning with verifiable rewards). The specific algorithm is GRPO: the model answers each case 16 times, and answers that scored better than the group average get reinforced.

The test is simple. Score the trained model on the real eval and compare it with the same model before training. If fake-case training makes it measurably better at real QC review, the synthetic-data strategy works for language models. If not, we learn that before investing further.

### Hypothesis

GRPO on view-calibrated synthetic cases, rendered in the exp30 eval format and rewarded on T1–T5 correctness, improves gemma-4-e4b on the real eval: v1.1 composite up versus its own untuned base with a 95% CI excluding zero, and at least 4 of 5 per-task wins (exp30 gate legs 1–2). This moves gate 3 (LM eval) of the north star. Leg 3 (T3 ≥ 0.214) is not expected to pass: the floor is under re-derivation, and the generator can't produce 6 of the eval's 14 element buckets (see Method).

### Method

**Training data** (`exp52_rlvr_dataset.py`). 30,000 cases from the persistent generator (`--max-attempts 12`, `experiments/dist.json`, seed 52; the exp43 recipe pool). Findings balanced to thirds to match the eval's sampling frame. 4,000 train and 200 valid records in mlx-lm-lora GRPODataset shape: `prompt` is `run_lm.build_class_prompt(...)` verbatim (few-shot + jargon, the locked v1.1 condition), `answer` is the T1–T5 labels as JSON. All training cases are synthetic; no real QC record is written.

**Synthetic → eval record mapping.** Agency view from `issued_facts`, verification view from `facts`, both through `synth.benefit.compute`. Not modeled, rendered "not reported": state, rent/utility split, SUA codes, homeless flag, composition, CAT_ELIG. Child support is 0. Income by source is collapsed to wages plus other unearned income. T3–T5 come from the first variance; the eval uses the largest-dollar variance, and the two agreed on 67.7% of multi-variance test items (exp30 Q2).

**View-identity calibration.** Raw synthetic records leak the label. Agency and verified gross income, net income and household size match on 100% of synthetic correct cases and 3–6% of error cases. In real QC records the rates are 79% and 54–55% (FY2021–2023 public-use files, n = 92,422, the eval's 1,400 denylisted items excluded). `--calibrate` stores only those aggregate rates and delta quantiles. The builder then perturbs the agency view of a matching share of correct cases with real-sized deltas, and copies verified values into the agency view of a matching share of error cases. After calibration, train rates are 0.81 / 0.54 / 0.57 (correct / over / under).

**Rewards** (`exp52_rlvr_scoring.py`). Task reward is the share of applicable T1–T5 answered correctly, parsed with the eval's own `run_lm.parse_class`; an unparseable completion scores 0. Format reward is 1 if the completion parses. Weights 0.9 / 0.1. Uniform per-example reward, no class weighting (exp43).

**Training** (`exp52_grpo_train.sh`). mlx-lm-lora Dr.GRPO on `mlx-community/gemma-4-e4b-it-bf16`, LoRA rank 16 / scale 20 / 16 layers, lr 1e-6, batch 1, group 16, temperature 1.2, completion cap 256, `--mask-prompt --grad-checkpoint`, seed 20261005. Run through `exp52_grpo_launch.py`, which renders prompts the way the eval serves them (see Smoke runs).

**Evaluation.** Fuse the adapter into bf16 and score it on the 1,200 test items under eval v1.1, classification prompt only (`run_lm.py --kinds class`; T6 is outside the composite and its prompt dominates eval time). Compare against the untuned bf16 e4b **served the same way**. A tuned-vs-base comparison across different quantizations would credit a quantization delta to training (snap-cot HANDOFF lesson). The LM Studio Q4_K_M GGUF baseline is a deployment-format reference, not the gate's base.

### Smoke runs (2026-10-05)

| run | finding | fix |
|---|---|---|
| 3 iters, defaults | rewards all 0; 96% of completions hit the 256-token cap | mlx-lm's TokenizerWrapper defaults Gemma 4 to `enable_thinking=True`, and GRPODataset always adds a system turn; the eval serves thinking off as a single user turn. `exp52_grpo_launch.py` forces thinking off and drops empty system turns |
| 5 iters, thinking off | ~29-token answers in eval format, format reward 1.0, task reward 0.08; reward σ = 0 (all 8 completions identical, loss 0) | at temperature 0.8 the short answers barely vary, so GRPO gets no advantage signal. Measured distinct answers per 16 samples: 2–3 at 0.8, 2–7 at 1.2, 6–13 at 1.6 |
| 10 iters, temp 1.2, group 16 | reward σ 0.10, nonzero loss, task reward 0.05 → 0.12 (noise-level at this scale); 0.29 it/s, 73 GB | settings adopted |

`--fuse` is store_true with a None default, so the YAML value applies; `fuse: false` lives in `exp52_grpo_lora.yaml`.

Ops note: running the 73 GB training smoke alongside ~150 GB of LM Studio models and the e4b baseline froze the machine; LM Studio unloaded everything and the baseline stopped at 628/1,200 (resumed cleanly). Run training with only the model it needs loaded.

### Results

**e4b deployment-format baseline** (LM Studio Q4_K_M GGUF, few/jargon, v1.1, 1,200 test items; `eval_pilot/preds_base_e4b_few_jargon_v11.jsonl`):

| | e4b Q4 base | 31B base (v1 few/jargon) | dummy |
|---|---|---|---|
| composite (T1–T5) | 0.014 | 0.121 | 0.000 |
| T1 | 0.377 | 0.559 | 0.400 |
| T2 | 0.226 | 0.348 | 0.182 |
| T3 | 0.005 | 0.049 | 0.014 |
| T4 | 0.004 | 0.036 | 0.036 |
| T5 | 0.067 | 0.135 | 0.170 |

FY2024 slice composite 0.019. Predicts "correct" on 1,022/1,200 (T1 below dummy). 0 classification parse failures; 108 dollar answers missing at 1,500 tokens. vs 31B: −0.108 [−0.123, −0.093], 0/5 wins.

**What happened after the baseline** (full log in the vault note):

1. *GRPO alone, lr 1e-6, 250 steps:* adapter shifts logits but changes 0 greedy answers. Crashed at step ~287 on the known MLX compile-cache limit (`[metal::malloc] Resource limit (499000)`, ml-explore/mlx#3849).
2. *Autoresearch-style sweep* (`exp52_sweep.sh`, 80-step trials scored on the 197 dev items, `exp52_sweep_results.tsv`): lr ≥ 1e-5 at LoRA scale 20 diverges (KL NaN by step 10); 5e-6 is stable. Best dev composite 0.089 (error-weighted mix) turned out to be a **prior shift**: its error calls had precision 0.681 vs a 0.665 base rate, and even on synthetic validation the model was at chance. GRPO on a chance-level policy reinforces label frequencies.
3. *Chance-corrected metrics* added to `score.py` (per-task Cohen's kappa; permutation excess = macro-F1 minus its mean with the model's answers shuffled; rolled into a composite skill). The pre-registered composite can be raised by prior shifts alone.
4. *Answer-only SFT* (`exp52_sft_*`, case prompt → gold answer block, prompt masked) and then GRPO on top. Dev results (`exp52_sft_results.tsv`):

| (real dev, n = 197) | composite | skill | T1 κ | T2 κ | T3 κ |
|---|---|---|---|---|---|
| base | 0.014 | 0.019 | 0.037 | 0.038 | 0.003 |
| SFT lr 1e-5, 300 steps | 0.179 | 0.132 | 0.246 | 0.186 | 0.079 |
| SFT lr 2e-5 | 0.139 | 0.098 | 0.186 | 0.109 | 0.078 |
| SFT error-weighted mix | 0.101 | 0.051 | 0.049 | 0.073 | 0.135 |
| **SFT lr 1e-5 → GRPO lr 5e-6, 80 steps, group 8** | **0.200** | **0.160** | **0.263** | 0.181 | **0.142** |

5. *Test gate (once, on the dev winner).* The first attempt went through `mlx_lm.server`, which silently drops `--adapter-path` when a request names `"default_model"` (it remaps the model path before the adapter lookup); every server-served tuned run equalled base (files in `eval_pilot/invalid_server_adapter/`). Re-run with direct loading (`exp52_quick_eval.py --split test`):

| (test, n = 1,200) | bf16 base | **SFT→GRPO** | untuned 31B |
|---|---|---|---|
| composite (T1–T5) | 0.011 | **0.188** | 0.121 |
| composite skill | — | **0.138** | 0.061 |
| T1 κ / acc | — / 0.365 | 0.284 / 0.734 | 0.140 / 0.572 |
| T2 κ | — | 0.131 | 0.089 |
| T3 κ / macro-F1 | — / 0.005 | 0.098 / 0.110 | 0.019 / 0.049 |

Gate vs own base: composite +0.177 [+0.159, +0.195], wins 5/5, T3 0.110 < 0.214 → **PASS=False on leg 3 only**. vs untuned 31B (informational): +0.066 [+0.046, +0.087]. FY2024 slice: +0.167 [+0.122, +0.213] vs base, +0.054 [+0.005, +0.103] vs 31B. Chance-corrected: real skill on T1/T2/T3 (p < 0.001), marginal on T4 (excess 0.013, p 0.022), none on T5 (κ ≈ 0), so the T4/T5 macro-F1 wins are mostly prior shifts.

**Rounds 3–4 (2026-10-06).** GRPO 160 on SFT-300: dev skill 0.164 (≈80 steps). **SFT 600 steps: dev 0.200.** GRPO 80 on SFT-600 *hurt* (0.150). Correct-heavy mix (50/25/25) SFT-300: 0.142, fewer error calls (161 vs 176/197); +GRPO 80: 0.155. GRPO helps an undertrained SFT model and hurts a well-trained one.

**Test gate on SFT 600 (direct loading):** composite 0.238 vs base 0.011 (+0.227 [+0.210, +0.245]), 5/5 wins, T3 macro-F1 0.117 < 0.214 → PASS=False on leg 3 only. Composite skill 0.178. vs untuned 31B: +0.116 [+0.097, +0.136]. vs the earlier SFT-300→GRPO model: +0.050 [+0.034, +0.066]. FY2024: +0.195 vs base, +0.082 vs 31B. T1 accuracy 75.6%, κ T1 0.385 / T2 0.198 / T3 0.133. Error calls 971/1,200 (truth 800), precision 0.761. The test set has now been scored on two dev-chosen models; the dev ranking held.

**Colab port (HF transformers + PEFT, `google_drive/`).** SFT 1,200 on an A100: synthetic mean excess 0.176 (best yet) but real dev skill 0.104; its step-600 checkpoint scored 0.129 on dev (Studio SFT-600: 0.200). More steps fit synthetic better and real worse; the Colab-vs-Studio gap at 600 steps is unresolved (port difference vs single-run variance).

### Verdict

Hypothesis confirmed for legs 1–2, not leg 3. Training gemma-4-e4b on synthetic cases only produces real, chance-corrected QC skill on held-out real cases. Best recipe: answer-only SFT, 600 steps, no GRPO: test composite 0.011 → 0.238, 5/5 task wins, and +0.116 over an untuned model ~8× its size. It holds on the FY2024 year-shift slice. T3 (0.110) misses the tabular 0.214 floor; under the "beat own base on T3 with a CI excluding zero" option it would pass. Two method lessons: GRPO only helps once the policy is above chance (SFT first), and macro-F1 composites need a chance-corrected companion.

### Next steps

1. **Decide the T3 bar** (options in the exp30 vault note); with option B this run passes the gate.
2. Training-mix balance: SFT over-calls "error" (176/197 dev); try a mix near the real prior (~2:1 error:correct).
   - **Done:** Tested on Oct 6: the balanced mix was already 1/3 correct; a correct-heavy mix (50/25/25) eased over-calling (176 → 161 error calls) but trailed longer SFT.
3. More GRPO on top of SFT (80 steps helped; the compile-cache crash needs per-segment resumes past ~250 steps).
   - **Done:** Tested on Oct 6: GRPO 160 ≈ GRPO 80 (dev skill 0.164 vs 0.160), and GRPO on SFT-600 hurt (0.200 → 0.150).
4. Generator coverage for the six T3 buckets it never produces (~22% of T3 test items), and a T5 signal (no skill yet).
5. Serve adapters correctly for deployment: fuse, or pass `"adapters"` in the request body, since `mlx_lm.server --adapter-path` is ignored for `"default_model"`.
