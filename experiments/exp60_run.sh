#!/bin/bash
# Exp60: train E2B on the exp52 recipe, pick a checkpoint on the retired test set, score once on the fresh set.
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"; E=experiments/eval_pilot
M=mlx-community/gemma-4-e2b-it-bf16; NAME=e2b_sft_lr1e-5_600
R="$(cd .. && pwd)/snap-qc-data/derived/exp52_sft_runs/$NAME"
echo "== $(date) train"
[ -f "$R/0000600_adapters.safetensors" ] || MODEL=$M SKIP_EVAL=1 experiments/exp52_sft_train.sh $NAME 600 1e-5 || exit 1
grep -E "Iter (100|600):.*Train loss|nan" "$R/train.log" | head -4
echo "== $(date) checkpoint selection on retired test set (items.json)"
for s in 100 200 300 400 500 600; do
  C="$R/ckpt_$s"; mkdir -p "$C"; cp "$R/adapter_config.json" "$C/"; cp "$R/$(printf %07d $s)_adapters.safetensors" "$C/adapters.safetensors"
  P=$E/preds_exp60_e2b_ckpt${s}_retired.jsonl
  [ -s $P ] && [ $(wc -l < $P) -eq 1200 ] || "$PY" experiments/exp52_quick_eval.py --model $M --split test --items $E/items.json --adapter "$C" --out $P > /dev/null 2>&1
  python3 $E/score.py --items $E/items.json --preds $P --split test | grep composite | sed "s/^/step $s: /"
done
python3 - <<'PY'
import json, subprocess, re
best=None; rows={}
for s in (100,200,300,400,500,600):
    out=subprocess.run(["python3","experiments/eval_pilot/score.py","--items","experiments/eval_pilot/items.json",
        "--preds",f"experiments/eval_pilot/preds_exp60_e2b_ckpt{s}_retired.jsonl","--split","test"],capture_output=True,text=True).stdout
    c=float(re.search(r"composite \(T1-T5\): ([0-9.\-]+)",out).group(1)); rows[s]=c
    if best is None or c>rows[best]: best=s
json.dump({"selected_step":best,"retired_test_composite":rows},open("experiments/exp60_selection.json","w"),indent=1)
print("selected step",best,rows)
PY
S=$(python3 -c "import json;print(json.load(open('experiments/exp60_selection.json'))['selected_step'])")
echo "== $(date) fresh set: untrained E2B"
P0=$E/preds_exp60_e2b_base_fresh.jsonl
[ -s $P0 ] && [ $(wc -l < $P0) -eq 1200 ] || { t0=$(date +%s); "$PY" experiments/exp52_quick_eval.py --model $M --split test --items $E/items_confirm.json --out $P0 > /dev/null 2>&1; echo "base took $(( $(date +%s)-t0 ))s"; }
echo "== $(date) fresh set: E2B step $S"
P1=$E/preds_exp60_e2b_sft${S}_fresh.jsonl
[ -s $P1 ] && [ $(wc -l < $P1) -eq 1200 ] || { t0=$(date +%s); "$PY" experiments/exp52_quick_eval.py --model $M --split test --items $E/items_confirm.json --adapter "$R/ckpt_$S" --out $P1 > /dev/null 2>&1; echo "tuned took $(( $(date +%s)-t0 ))s"; }
echo "== $(date) readouts"
for split in test test_2024; do
  python3 $E/score.py --items $E/items_confirm.json --preds $P1 --base-preds $P0 --split $split --out $E/gate_exp60_e2b_vs_base_$split.json | tail -8
done
python3 $E/score.py --items $E/items_confirm.json --preds $P1 --base-preds $E/preds_exp59_e4b_sft400_class.jsonl --split test --out $E/gate_exp60_e2b_vs_e4b_test.json | tail -8
echo "== $(date) done"
