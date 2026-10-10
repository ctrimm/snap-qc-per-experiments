#!/bin/bash
# Exp76 (v2 cards + exp62 student) then exp77 (re-distill with odds kept). Overnight GPU chain.
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"; D="$(cd .. && pwd)/snap-qc-data/derived"; E=experiments
M=mlx-community/gemma-4-e2b-it-bf16; IDS=$E/exp62_eval_ids.txt
echo "== $(date) exp76 cards"
OMP_NUM_THREADS=8 python3 $E/exp62_flag_cards.py --top-k 3 --calibrate --wording v2 --out $E/exp76_cards.jsonl
OMP_NUM_THREADS=8 python3 $E/exp62_flag_cards.py --top-k 3 --calibrate --wording v2 --train-cards --states PA,NY,ID,UT,SD --out $E/exp76_train_cards.jsonl
python3 - <<'PY'
import json
c=[json.loads(l) for l in open('experiments/exp76_cards.jsonl')]
for st in ('PA','NY'):
    e=[x for x in c if x['state']==st and x['truth']['error'] and x['truth']['t3']]
    print(st,'top-3 coverage',f"{sum(x['truth']['t3'] in {p['part'] for p in x['check_first']} for x in e)/len(e):.0%}",
          '| first-pick odds mix', sorted({x['check_first'][0]['in_10'] for x in c}))
PY
echo "== $(date) exp76 notes (exp62 student, v2 wording)"
S0=$(python3 -c "import json;print(json.load(open('experiments/exp62_step2_selection.json'))['selected_step'])")
rm -f $E/exp76_notes_e2b_exp62student.jsonl
"$PY" $E/exp62_rewrite.py --model $M --adapter $D/exp52_sft_runs/exp62_e2b_explainer/ckpt_$S0 --wording v2 \
  --cards $E/exp76_cards.jsonl --out $E/exp76_notes_e2b_exp62student.jsonl > /dev/null 2>&1
python3 $E/exp76_check.py $E/exp76_cards.jsonl $IDS template $E/exp76_notes_e2b_exp62student.jsonl
echo "== $(date) exp77 teacher (31B, style v2, 1,200 cards)"
python3 -c "
import json,random; ids=[json.loads(l)['card_id'] for l in open('experiments/exp76_train_cards.jsonl')]
random.Random(77).shuffle(ids); open('experiments/exp77_teacher_ids.txt','w').write('\n'.join(ids[:1200])+'\n')"
"$PY" $E/exp62_rewrite.py --model mlx-community/gemma-4-31b-it-bf16 --teacher --teacher-style v2 --wording v2 \
  --cards $E/exp76_train_cards.jsonl --ids $E/exp77_teacher_ids.txt --out $E/exp77_teacher_notes.jsonl > /dev/null 2>&1
echo "== $(date) exp77 filter"; python3 $E/exp77_data.py || exit 1
echo "== $(date) exp77 train"
R=$D/exp52_sft_runs/exp77_e2b_explainer_v2
[ -f "$R/0000500_adapters.safetensors" ] || MODEL=$M SKIP_EVAL=1 DATA=$D/exp77_sft experiments/exp52_sft_train.sh exp77_e2b_explainer_v2 500 1e-5 || exit 1
echo "== $(date) exp77 checkpoint selection"
best=0; bestp=-1
for s in 100 200 300 400 500; do
  C=$R/ckpt_$s; mkdir -p $C; cp $R/adapter_config.json $C/; cp $R/$(printf %07d $s)_adapters.safetensors $C/adapters.safetensors
  O=$E/exp77_select_ckpt$s.jsonl; rm -f $O
  "$PY" $E/exp62_rewrite.py --model $M --adapter $C --wording v2 --cards $E/exp76_train_cards.jsonl --ids $E/exp77_select_ids.txt --out $O > /dev/null 2>&1
  p=$(python3 - $O <<'PY'
import json,sys; f=sys.argv[1]; sys.argv=sys.argv[:1]; sys.path.insert(0,'experiments')
import exp76_check as C
cards={c['card_id']:c for c in map(json.loads,open('experiments/exp76_train_cards.jsonl'))}
C.K.CARDS=cards
notes={r['card_id']:r['note'] for r in map(json.loads,open(f))}
ids=open('experiments/exp77_select_ids.txt').read().split()
rows=[(C.K.check(cards[i],notes[i])['pass'] and C.keeps_odds(cards[i],notes[i])) for i in ids]
print(round(sum(rows)/len(rows),3))
PY
)
  echo "step $s: selection pass (all checks + odds) $p"
  if python3 -c "import sys;sys.exit(0 if $p > $bestp else 1)"; then best=$s; bestp=$p; fi
done
echo "{\"selected_step\": $best, \"selection_pass\": $bestp}" > $E/exp77_selection.json
echo "== $(date) exp77 eval (200 v2 cards, once)"
O=$E/exp77_notes_e2b_v2.jsonl; rm -f $O
"$PY" $E/exp62_rewrite.py --model $M --adapter $R/ckpt_$best --wording v2 --cards $E/exp76_cards.jsonl --out $O > /dev/null 2>&1
python3 $E/exp76_check.py $E/exp76_cards.jsonl $IDS template $E/exp76_notes_e2b_exp62student.jsonl $O
echo "== $(date) packet"
python3 - <<'PY'
import json,subprocess,sys
sys.argv=sys.argv[:1]; sys.path.insert(0,'experiments')
import exp76_check as C
cards,ids=C.load('experiments/exp76_cards.jsonl','experiments/exp62_eval_ids.txt'); C.K.CARDS=cards
n={r['card_id']:r['note'] for r in map(json.loads,open('experiments/exp77_notes_e2b_v2.jsonl'))}
g=C.score(cards,ids,n); ok=g['faithful']==1.0 and g['pass']>=0.95 and g['keeps_odds']>=0.95
src='experiments/exp77_notes_e2b_v2.jsonl' if ok else 'experiments/exp76_notes_e2b_exp62student.jsonl'
print('exp77 acceptable:',ok,'| packet model:',src)
subprocess.run(['python3','experiments/exp76_check.py','--packet','experiments/exp76_cards.jsonl','experiments/exp62_eval_ids.txt',src,'experiments/exp77_reviewer'])
PY
echo "== $(date) done"
