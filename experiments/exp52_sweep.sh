#!/bin/bash
# Exp52 autoresearch-style sweep: short GRPO trials, each scored on the eval's
# dev split (197 real items, never the test set) with exp52_quick_eval.py.
# One line per trial in exp52_sweep_results.tsv. Usage:
#   experiments/exp52_sweep.sh NAME ITERS [ENV=VAL ...]   e.g. LR=1e-5 GROUP=8
set -uo pipefail
cd "$(dirname "$0")/.."
NAME="$1"; ITERS="$2"; shift 2
S="$(cd .. && pwd)/snap-qc-data/derived/exp52_rlvr/sweep"
TSV=experiments/exp52_sweep_results.tsv
[ -f "$TSV" ] || printf "trial\titers\tconfig\tdev_composite\tt1\tt2\tt3\tchanged_vs_base\ttrain_reward_last\tminutes\n" > "$TSV"
start=$(date +%s)
# SCALE=<x> / RANK=<r> write a per-trial LoRA yaml (defaults: scale 20,
# rank 16, dropout 0.05, fuse off); DATA=<dir> picks a training-set variant
extra=(); scale=20; rank=16; custom=0
for kv in "$@"; do case "$kv" in
  SCALE=*) scale="${kv#SCALE=}"; custom=1;;
  RANK=*) rank="${kv#RANK=}"; custom=1;;
  DATA=*) extra+=(EXP52_DATA="${kv#DATA=}");; esac; done
if [ "$custom" = 1 ]; then
  y="$S/$NAME.lora.yaml"
  printf "lora_parameters:\n  rank: %s\n  scale: %s\n  dropout: 0.05\nfuse: false\n" "$rank" "$scale" > "$y"
  extra+=(LORA_YAML="$y"); fi
env "$@" ${extra[@]+"${extra[@]}"} VAL_BATCHES=1 EVAL_EVERY=1000 SAVE_EVERY=1000 \
  experiments/exp52_grpo_train.sh "$ITERS" "$S/$NAME" > "$S/$NAME.train.log" 2>&1 &
tp=$!
# fast-fail: kill the trial as soon as KL goes NaN (weights are gone by then)
while kill -0 "$tp" 2>/dev/null; do
  if grep -q "KL Divergence: nan" "$S/$NAME.train.log"; then
    pkill -f "exp52_grpo_launch.py.*$NAME"; sleep 5; break; fi
  sleep 20
done
wait "$tp" 2>/dev/null
if ! grep -q "Saved final weights" "$S/$NAME.train.log"; then
  why=crash; grep -q "KL Divergence: nan" "$S/$NAME.train.log" && why="nan@$(sed 's/\x1b\[[0-9;]*m//g' "$S/$NAME.train.log" | grep -B12 'KL Divergence: nan' | grep -oE '^Iter [0-9]+' | head -1 | cut -d' ' -f2)"
  printf "%s\t%s\t%s\t%s\t\t\t\t\t\t%s\n" "$NAME" "$ITERS" "$*" "$why" $(( ($(date +%s)-start)/60 )) >> "$TSV"; exit 1
fi
"$HOME/throwaway-mlxlora/.venv/bin/python" experiments/exp52_quick_eval.py \
  --adapter "$S/$NAME" --out "$S/$NAME.dev.jsonl" --base-preds "$S/dev_base.jsonl" \
  > "$S/$NAME.eval.txt" 2>&1
comp=$(grep -oE "composite \(T1-T5\): [0-9.]+" "$S/$NAME.eval.txt" | awk '{print $3}')
t1=$(awk '$1=="t1"{print $2}' "$S/$NAME.eval.txt"); t2=$(awk '$1=="t2"{print $2}' "$S/$NAME.eval.txt")
t3=$(awk '$1=="t3"{print $2}' "$S/$NAME.eval.txt")
chg=$(grep -oE "changed_vs_base: [0-9/]+" "$S/$NAME.eval.txt" | awk '{print $2}')
rew=$(sed 's/\x1b\[[0-9;]*m//g' "$S/$NAME.train.log" | grep "qc_task_reward" | tail -1 | grep -oE "μ=[0-9.]+" | cut -c3-)
printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$NAME" "$ITERS" "$*" "$comp" "$t1" "$t2" "$t3" "$chg" "$rew" $(( ($(date +%s)-start)/60 )) >> "$TSV"
tail -1 "$TSV"
