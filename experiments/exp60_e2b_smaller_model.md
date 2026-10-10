# Experiment 60 — a smaller model: Gemma 4 E2B on the exp52 recipe

**Date:** 2026-10-09 · **Code:** `exp60_run.sh` (uses `exp52_sft_train.sh`, `exp52_quick_eval.py`, `eval_pilot/score.py`) · **Results:** `eval_pilot/gate_exp60_*.json`, `exp60_selection.json`

## Pre-registration (committed before training)

### Question

How much skill do we lose by going from Gemma 4 E4B (about 4B effective parameters, 7.5B total) to E2B (about 2B effective), with the same synthetic data and recipe? A smaller model is cheaper to run on a state's own hardware. This tests the size cost only; reasoning traces and explanations are separate experiments.

### Fixed in advance

| What | Value |
|---|---|
| Model | `mlx-community/gemma-4-e2b-it-bf16` (35 layers) |
| Recipe | identical to the exp52 best run (`sft_lr1e-5_600`): data `exp52_sft` (balanced mix), answer-only SFT, LoRA rank 16 / scale 20 / dropout 0.05 on the last 16 layers, lr 1e-5, batch 4, 600 steps, seed 52, checkpoint every 100 |
| Runner / prompt | `exp52_quick_eval.py --model …e2b…`: direct load, greedy, class-only, locked v1.1 few-shot + jargon prompt (examples from `items.json` dev) |
| Checkpoint choice | highest eval v1.2 composite on the **retired original test set** (`items.json`, 1,200 items, now dev use) among steps 100–600; ties go to the earlier step. Chosen automatically by the run script and written to `exp60_selection.json` before the fresh set is touched |
| Final scoring | the chosen checkpoint and untrained E2B, once each, on the exp59 fresh set (`items_confirm.json`), eval v1.2 |

### Pre-declared readouts

1. **Gate (E2B trained vs E2B untrained, fresh set):** the usual three legs (composite CI above 0, ≥ 4/5 wins, T3 ≥ 0.210).
2. **Size cost (E2B trained vs E4B trained, fresh set, paired bootstrap):** E2B counts as **good enough** if the lower bound of the 95% CI on (E2B − E4B) composite is above **−0.05** (no more than 5 points worse). Per-task differences reported.
3. **Speed:** items per minute for E2B vs E4B on the same machine (information).

Rules as in exp59: one scoring pass on the fresh set, no changes after training starts, any deviation written here before results, result reported as is.

## Results

Run 2026-10-09 19:21–23:42, one pass, no deviations. Training: 13.6M trainable parameters, 0.10 it/s (E4B 0.066), final train loss 0.106 (E4B 0.094).

**Checkpoint selection (retired original test set, v1.2 composite):** step 100 0.079, 200 0.152, 300 0.205, **400 0.221**, 500 0.209, 600 0.218 → step 400 (the same step E4B used).

**Fresh set (1,200 items, eval v1.2):**

| Model | composite | skill | T1 | T2 | T3 (n=642) | T4 | T5 |
|---|---|---|---|---|---|---|---|
| E2B untrained | 0.000 | 0.020 | — | — | — | — | — |
| exp53 classifier | 0.240 | 0.154 | 0.617 | 0.404 | 0.184 | 0.059 | 0.224 |
| **E2B SFT step 400** | **0.249** | **0.185** | 0.687 | 0.407 | 0.190 | 0.023 | 0.177 |
| E4B SFT step 400 (exp59) | 0.334 | 0.276 | 0.750 | 0.516 | 0.244 | 0.053 | 0.137 |

E2B tuned κ: T1 0.374, T2 0.157, T3 0.121, T4 −0.006, T5 −0.027.

1. **Gate vs untrained E2B:** composite +0.249 [+0.229, +0.269] (pass), 5/5 wins (pass), T3 0.190 < 0.210 (**fail**) → **2 of 3, no pass.** FY2024 slice: +0.236 [+0.190, +0.282], 5/5, T3 0.180, same pattern.
2. **Size cost vs E4B:** composite −0.084 [−0.104, −0.064]. Lower bound −0.104 is below the −0.05 margin → **not good enough.** E2B is lower on T1–T4.
3. **Speed:** untrained 1,237 s and tuned 1,159 s for 1,200 items (about 60 items/min) vs E4B 2,029 s and 2,222 s (about 33/min): **~1.8× faster.**

### Verdict

Did not hold. Halving the model costs about 8 points overall and a third of the skill above chance (0.276 → 0.185), and the error-location check fails. Trained E2B lands at roughly the level of the conventional classifier trained on the same data (composite 0.249 vs 0.240, skill 0.185 vs 0.154), so at this size the language model adds little over a tree model for classification. E4B stays the smallest model that clears the gate.

### Next steps

1. Keep E4B for any language-model work. A 1.8× speedup doesn't make up for losing a third of the skill.
2. For ranker explanations, model size matters less: rewriting a ranker's reasons into plain language is an easier task than reading a case cold, so E2B may still do it. Test it there rather than ruling it out.

