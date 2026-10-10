#!/bin/bash
# Exp71: E4B trained to list agency-vs-verified differences before answering; step 400 fixed; fresh set once.
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"; D="$(cd .. && pwd)/snap-qc-data/derived"; E=experiments/eval_pilot
R=$D/exp52_sft_runs/exp71_rationale
echo "== $(date) train"
[ -f "$R/0000400_adapters.safetensors" ] || DATA=$D/exp71_sft SKIP_EVAL=1 experiments/exp52_sft_train.sh exp71_rationale 400 1e-5 || exit 1
C=$R/ckpt_400; mkdir -p $C; cp $R/adapter_config.json $C/; cp $R/0000400_adapters.safetensors $C/adapters.safetensors
echo "== $(date) eval (fresh set, once)"
"$PY" experiments/exp52_quick_eval.py --split test --items $E/items_confirm.json --adapter $C --max-tokens 200 \
  --out $E/preds_exp71_rationale_fresh.jsonl > /dev/null 2>&1
echo "== $(date) readouts"
python3 $E/score.py --items $E/items_confirm.json --preds $E/preds_exp71_rationale_fresh.jsonl \
  --base-preds $E/preds_exp59_e4b_sft400_class.jsonl --split test --out $E/gate_exp71_vs_answeronly_all.json | tail -9
python3 $E/score.py --items $E/items_confirm.json --preds $E/preds_exp71_rationale_fresh.jsonl \
  --base-preds $E/preds_exp59_e4b_sft400_class.jsonl --split test --ids $E/exp71_visible_ids.txt --out $E/gate_exp71_vs_answeronly_visible.json | tail -9
echo "== $(date) done"
