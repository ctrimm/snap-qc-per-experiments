#!/bin/bash
# Exp62 step 2: 31B teacher notes on training cards -> filter -> SFT E2B -> pick checkpoint on 100 held-out
# training cards -> score once on the 200 eval cards.
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"; D="$(cd .. && pwd)/snap-qc-data/derived"
M=mlx-community/gemma-4-e2b-it-bf16; NAME=exp62_e2b_explainer; R="$D/exp52_sft_runs/$NAME"
echo "== $(date) teacher"
"$PY" experiments/exp62_rewrite.py --model mlx-community/gemma-4-31b-it-bf16 --teacher \
  --cards experiments/exp62_train_cards.jsonl --ids all --out experiments/exp62_teacher_notes.jsonl > /dev/null 2>&1
wc -l < experiments/exp62_teacher_notes.jsonl
echo "== $(date) filter"; python3 experiments/exp62_step2_data.py || exit 1
echo "== $(date) train"
[ -f "$R/0000500_adapters.safetensors" ] || MODEL=$M SKIP_EVAL=1 DATA="$D/exp62_sft" experiments/exp52_sft_train.sh $NAME 500 1e-5 || exit 1
grep -E "Iter (100|500):.*(Train|Val) loss" "$R/train.log"
echo "== $(date) checkpoint selection (100 held-out training cards)"
best=0; bestp=-1
for s in 100 200 300 400 500; do
  C="$R/ckpt_$s"; mkdir -p "$C"; cp "$R/adapter_config.json" "$C/"; cp "$R/$(printf %07d $s)_adapters.safetensors" "$C/adapters.safetensors"
  O=experiments/exp62_select_notes_ckpt$s.jsonl; rm -f $O
  "$PY" experiments/exp62_rewrite.py --model $M --adapter "$C" --cards experiments/exp62_train_cards.jsonl \
    --ids experiments/exp62_select_ids.txt --out $O > /dev/null 2>&1
  p=$(python3 - "$O" <<'PY'
import json,sys; f=sys.argv[1]; sys.argv=sys.argv[:1]; sys.path.insert(0,'experiments')
import exp62_check as K
cards={c['card_id']:c for c in map(json.loads,open('experiments/exp62_train_cards.jsonl'))}
rows=[K.check(cards[r['card_id']],r['note']) for r in map(json.loads,open(f))]
print(round(sum(r['pass'] for r in rows)/len(rows),3))
PY
)
  echo "step $s: selection pass $p"
  if python3 -c "import sys; sys.exit(0 if $p > $bestp else 1)"; then best=$s; bestp=$p; fi
done
echo "{\"selected_step\": $best, \"selection_pass\": $bestp}" > experiments/exp62_step2_selection.json; echo "selected step $best"
echo "== $(date) eval (200 cards, once)"
O=experiments/exp62_notes_e2b_distilled.jsonl; rm -f $O
"$PY" experiments/exp62_rewrite.py --model $M --adapter "$R/ckpt_$best" --out $O > /dev/null 2>&1
python3 experiments/exp62_check.py template experiments/exp62_notes_e2b_zeroshot.jsonl experiments/exp62_notes_e4b_zeroshot.jsonl $O
echo "== $(date) done"
