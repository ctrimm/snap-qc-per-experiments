#!/bin/bash
# Exp52 gate evaluation: tuned gemma-4-e4b (bf16 + LoRA, loaded directly)
# vs the matched bf16 base on the 1,200 test items, eval v1.1 class-only.
# Direct loading, not mlx_lm.server: the server drops --adapter-path for
# requests naming "default_model" (see eval_pilot/invalid_server_adapter/).
# The bf16 base preds (served, no adapter) matched direct loading.
#   experiments/exp52_gate_eval.sh ADAPTER_DIR TAG
set -uo pipefail
cd "$(dirname "$0")/.."
E=experiments/eval_pilot
"$HOME/throwaway-mlxlora/.venv/bin/python" experiments/exp52_quick_eval.py --split test \
  --adapter "$1" --out "$E/preds_e4b_${2}_direct_class.jsonl" \
  --base-preds "$E/preds_e4b_bf16_base_few_jargon_class.jsonl"
for split in test test_2024; do
  python3 "$E/score.py" --items "$E/items.json" --preds "$E/preds_e4b_${2}_direct_class.jsonl" \
    --base-preds "$E/preds_e4b_bf16_base_few_jargon_class.jsonl" \
    --ref-preds "$E/preds_base_few_jargon.jsonl" --split "$split" \
    --out "$E/gate_exp52_${2}_direct_${split}.json" | tail -3
done
