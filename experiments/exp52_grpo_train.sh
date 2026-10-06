#!/bin/bash
# Exp52: GRPO (Dr.GRPO) on gemma-4-e4b with verifiable QC rewards.
# Data from exp52_rlvr_dataset.py; rewards from exp52_rlvr_rewards.py.
# Runs in the snap-eval RLVR venv via exp52_grpo_launch.py (thinking off,
# no system turn, matching how the eval serves the model). Usage:
#   experiments/exp52_grpo_train.sh [ITERS] [ADAPTER_DIR]
set -euo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"
DATA="${EXP52_DATA:-../snap-qc-data/derived/exp52_rlvr}"
ITERS="${1:-400}"
ADAPTERS="${2:-../snap-qc-data/derived/exp52_rlvr/adapters/grpo-v1}"
mkdir -p "$ADAPTERS"
"$PY" experiments/exp52_grpo_launch.py \
  -c "${LORA_YAML:-experiments/exp52_grpo_lora.yaml}" \
  --model mlx-community/gemma-4-e4b-it-bf16 \
  --train --train-type lora --train-mode grpo --grpo-loss-type dr_grpo \
  --data "$DATA" --mask-prompt \
  --num-layers "${NUM_LAYERS:-16}" \
  --iters "$ITERS" --batch-size 1 --group-size "${GROUP:-16}" \
  --max-completion-length "${MAXC:-256}" --max-seq-length 4096 --temperature "${TEMP:-1.2}" \
  --learning-rate "${LR:-1e-6}" --grad-checkpoint \
  --gradient-accumulation-steps "${GRAD_ACCUM:-1}" --beta "${BETA:-0.1}" \
  --reward-functions-file experiments/exp52_rlvr_rewards.py \
  --reward-functions "${REWARD_FUNCS:-qc_task_reward,qc_format_reward}" \
  --reward-weights "${REWARD_WEIGHTS:-[0.9, 0.1]}" \
  --adapter-path "$ADAPTERS" --save-every "${SAVE_EVERY:-50}" \
  --steps-per-report 5 --steps-per-eval "${EVAL_EVERY:-50}" --val-batches "${VAL_BATCHES:-25}" \
  --seed "${SEED:-20261005}" \
  ${RESUME:+--resume-adapter-file "$RESUME"}
