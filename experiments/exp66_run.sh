#!/bin/bash
# Exp66 (queued after exp65): explanation self-training loop. Up to 3 rounds:
# current student samples 2 notes/card (temp 0.8) on 1,200 training cards -> keep passing notes ->
# retrain E2B from base on teacher + student passes (300 steps) -> pick checkpoint on 100 selection cards.
# Stop when the selection pass rate gains < 1 point. Final model scored once on the 200 eval cards.
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"; D="$(cd .. && pwd)/snap-qc-data/derived"; M=mlx-community/gemma-4-e2b-it-bf16
echo "== $(date) waiting for exp65"
while pgrep -f "[e]xp65_run.sh" >/dev/null || pgrep -f "[e]xp62_step2.sh" >/dev/null; do sleep 60; done
[ -f experiments/exp62_step2_selection.json ] || { echo "no exp62 student; stopping"; exit 1; }
S0=$(python3 -c "import json;print(json.load(open('experiments/exp62_step2_selection.json'))['selected_step'])")
CUR="$D/exp52_sft_runs/exp62_e2b_explainer/ckpt_$S0"
O=experiments/exp66_select_r0.jsonl; rm -f $O
"$PY" experiments/exp62_rewrite.py --model $M --adapter "$CUR" --cards experiments/exp62_train_cards.jsonl --ids experiments/exp62_select_ids.txt --out $O > /dev/null 2>&1
PREV=$(python3 experiments/exp66_round.py score $O); echo "round 0 (exp62 student, step $S0): $PREV"
for r in 1 2 3; do
  echo "== $(date) round $r: sample"
  python3 - $r <<'PY'
import json, random, sys
r=int(sys.argv[1]); sel=set(open('experiments/exp62_select_ids.txt').read().split())
ids=[json.loads(l)['card_id'] for l in open('experiments/exp62_train_cards.jsonl')]
ids=[i for i in ids if i not in sel]; random.Random(660+r).shuffle(ids)
open(f'experiments/exp66_r{r}_ids.txt','w').write('\n'.join(ids[:1200])+'\n')
PY
  SM=experiments/exp66_r${r}_samples.jsonl
  "$PY" experiments/exp62_rewrite.py --model $M --adapter "$CUR" --cards experiments/exp62_train_cards.jsonl \
    --ids experiments/exp66_r${r}_ids.txt --temp 0.8 --samples 2 --seed $((66+r)) --out $SM > /dev/null 2>&1
  python3 experiments/exp66_round.py build $r $SM || exit 1
  echo "== $(date) round $r: train"
  NAME=exp66_r$r; RR="$D/exp52_sft_runs/$NAME"
  [ -f "$RR/0000300_adapters.safetensors" ] || MODEL=$M SKIP_EVAL=1 DATA="$D/exp66_r$r" experiments/exp52_sft_train.sh $NAME 300 1e-5 || exit 1
  best=""; bestp=-1; bestline=""
  for s in 100 200 300; do
    C="$RR/ckpt_$s"; mkdir -p "$C"; cp "$RR/adapter_config.json" "$C/"; cp "$RR/$(printf %07d $s)_adapters.safetensors" "$C/adapters.safetensors"
    O=experiments/exp66_select_r${r}_s$s.jsonl; rm -f $O
    "$PY" experiments/exp62_rewrite.py --model $M --adapter "$C" --cards experiments/exp62_train_cards.jsonl --ids experiments/exp62_select_ids.txt --out $O > /dev/null 2>&1
    line=$(python3 experiments/exp66_round.py score $O); echo "round $r step $s: $line"
    p=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['pass'])" "$line")
    if python3 -c "import sys;sys.exit(0 if $p > $bestp else 1)"; then best=$C; bestp=$p; bestline=$line; fi
  done
  pp=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['pass'])" "$PREV")
  echo "round $r best: $bestline (previous $pp)"
  if python3 -c "import sys;sys.exit(0 if $bestp >= $pp + 0.01 else 1)"; then CUR=$best; PREV=$bestline; echo "round $r adopted"
  else echo "round $r did not improve by 1 point: stop, keep previous"; break; fi
done
echo "{\"final_adapter\": \"$CUR\"}" > experiments/exp66_final.json
echo "== $(date) final eval (200 cards, once)"
O=experiments/exp66_notes_final.jsonl; rm -f $O
"$PY" experiments/exp62_rewrite.py --model $M --adapter "$CUR" --out $O > /dev/null 2>&1
python3 experiments/exp62_check.py template experiments/exp62_notes_e2b_distilled.jsonl $O
echo "== $(date) done"
