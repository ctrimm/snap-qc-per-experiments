#!/bin/bash
# Score each saved checkpoint of an exp52 SFT run on real dev (no synthetic).
#   experiments/exp52_ckpt_sweep.sh RUN_NAME "100 200 300 ..."
set -uo pipefail
cd "$(dirname "$0")/.."
D="$(cd .. && pwd)/snap-qc-data/derived"; R="$D/exp52_sft_runs/$1"
for step in $2; do
  ck=$(printf "%07d" "$step"); tmp="$R/ckpt_$step"; mkdir -p "$tmp"
  cp "$R/${ck}_adapters.safetensors" "$tmp/adapters.safetensors"; cp "$R/adapter_config.json" "$tmp/"
  "$HOME/throwaway-mlxlora/.venv/bin/python" experiments/exp52_quick_eval.py --adapter "$tmp" \
    --out "$tmp/dev.jsonl" --base-preds "$D/exp52_rlvr/sweep/dev_base.jsonl" 2>&1 | grep -v -i "warn\|fetching" > "$tmp/eval.txt"
  python3 experiments/exp52_sft_log.py "$1_ckpt$step" "$tmp/eval.txt" "checkpoint $step of $1"
done
