#!/bin/bash
# Exp59 confirmatory run: classifier, base, tuned on items_confirm.json; one pass each, then v1.2 gate.
set -uo pipefail
cd "$(dirname "$0")/.."
E=experiments/eval_pilot; I=$E/items_confirm.json; PY="$HOME/throwaway-mlxlora/.venv/bin/python"
A=../snap-qc-data/derived/exp52_sft_runs/sft_lr1e-5_600/ckpt_400
echo "== $(date) sha check"; shasum -a 256 $A/adapters.safetensors
echo "== $(date) classifier"; OMP_NUM_THREADS=4 python3 experiments/exp53_classifier_vs_llm.py --items $I --out $E/preds_exp59_gbm_class.jsonl
echo "== $(date) base"; [ -s $E/preds_exp59_e4b_base_class.jsonl ] && [ $(wc -l < $E/preds_exp59_e4b_base_class.jsonl) -eq 1200 ] || \
  "$PY" experiments/exp52_quick_eval.py --split test --items $I --out $E/preds_exp59_e4b_base_class.jsonl
echo "== $(date) tuned"; [ -s $E/preds_exp59_e4b_sft400_class.jsonl ] && [ $(wc -l < $E/preds_exp59_e4b_sft400_class.jsonl) -eq 1200 ] || \
  "$PY" experiments/exp52_quick_eval.py --split test --items $I --adapter $A --out $E/preds_exp59_e4b_sft400_class.jsonl \
  --base-preds $E/preds_exp59_e4b_base_class.jsonl
echo "== $(date) gate"
for split in test test_2024; do
  python3 $E/score.py --items $I --preds $E/preds_exp59_e4b_sft400_class.jsonl --base-preds $E/preds_exp59_e4b_base_class.jsonl \
    --split $split --out $E/gate_exp59_sft400_$split.json | tail -4
done
python3 $E/score.py --items $I --preds $E/preds_exp59_gbm_class.jsonl --split test --out $E/score_exp59_gbm_test.json | grep -E "^t3|composite"
echo "== $(date) done"
