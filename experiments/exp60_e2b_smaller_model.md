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

_Pending._
