#!/bin/bash
# Exp52 answer-only SFT on gemma-4-e4b (bf16), then quick eval on synthetic
# valid (learnability) and real dev (transfer), both chance-corrected.
#   experiments/exp52_sft_train.sh NAME [ITERS] [LR]   (env: DATA, BATCH, SEED, LORA_YAML, MODEL, SKIP_EVAL)
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"
NAME="$1"; ITERS="${2:-500}"; LR="${3:-1e-5}"
D="$(cd .. && pwd)/snap-qc-data/derived"
DATA="${DATA:-$D/exp52_sft}"
OUT="$D/exp52_sft_runs/$NAME"; mkdir -p "$OUT"
"$PY" experiments/exp52_sft_launch.py \
  -c "${LORA_YAML:-experiments/exp52_sft_lora.yaml}" \
  --model "${MODEL:-mlx-community/gemma-4-e4b-it-bf16}" --train --data "$DATA" \
  --fine-tune-type lora --num-layers 16 --mask-prompt \
  --iters "$ITERS" --batch-size "${BATCH:-4}" --learning-rate "$LR" \
  --max-seq-length 4096 --grad-checkpoint \
  --steps-per-report 10 --steps-per-eval 100 --val-batches 10 --save-every 100 \
  --adapter-path "$OUT" --seed "${SEED:-52}" > "$OUT/train.log" 2>&1 || { echo "train failed"; exit 1; }
[ -n "${SKIP_EVAL:-}" ] && exit 0
"$PY" experiments/exp52_quick_eval.py --model "${MODEL:-mlx-community/gemma-4-e4b-it-bf16}" --adapter "$OUT" \
  --out "$OUT/dev.jsonl" --base-preds "$D/exp52_rlvr/sweep/dev_base.jsonl" \
  --synthetic "$D/exp52_rlvr/valid.jsonl:120" > "$OUT/eval.txt" 2>&1
cat "$OUT/eval.txt" | grep -v -i "warn\|fetching"
