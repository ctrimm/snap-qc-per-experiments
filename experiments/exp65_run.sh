#!/bin/bash
# Exp65 (queued after exp62 step 2): three-part flag cards. Same 200 eval cases, top-3 "check first".
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"; D="$(cd .. && pwd)/snap-qc-data/derived"
echo "== $(date) waiting for exp62 step 2"
while pgrep -f "[e]xp62_step2.sh" >/dev/null; do sleep 60; done
echo "== $(date) build three-part cards"
OMP_NUM_THREADS=8 python3 experiments/exp62_flag_cards.py --top-k 3 --out experiments/exp65_cards.jsonl
python3 - <<'PY'
import json
c=[json.loads(l) for l in open('experiments/exp65_cards.jsonl')]
for st in ('PA','NY'):
    e=[x for x in c if x['state']==st and x['truth']['error'] and x['truth']['t3']]
    for k in (1,2,3):
        print(st, f"top-{k} coverage {sum(x['truth']['t3'] in {p['part'] for p in x['check_first'][:k]} for x in e)/len(e):.0%}", end="  ")
    print()
PY
echo "== $(date) model notes"
"$PY" experiments/exp62_rewrite.py --model mlx-community/gemma-4-e4b-it-bf16 --cards experiments/exp65_cards.jsonl \
  --out experiments/exp65_notes_e4b_zeroshot.jsonl > /dev/null 2>&1
NOTES="experiments/exp65_notes_e4b_zeroshot.jsonl"
if [ -f experiments/exp62_step2_selection.json ]; then
  S=$(python3 -c "import json;print(json.load(open('experiments/exp62_step2_selection.json'))['selected_step'])")
  "$PY" experiments/exp62_rewrite.py --model mlx-community/gemma-4-e2b-it-bf16 --adapter "$D/exp52_sft_runs/exp62_e2b_explainer/ckpt_$S" \
    --cards experiments/exp65_cards.jsonl --out experiments/exp65_notes_e2b_distilled.jsonl > /dev/null 2>&1
  NOTES="$NOTES experiments/exp65_notes_e2b_distilled.jsonl"
fi
echo "== $(date) checks"
python3 experiments/exp65_check.py template $NOTES
BEST=$(python3 - $NOTES <<'PY'
import json,sys
paths=sys.argv[1:]; sys.argv=sys.argv[:1]; sys.path.insert(0,'experiments')
import exp65_check as X
K=X.K; best=None
for p in paths:
    agg,_=K.score({r['card_id']:r['note'] for r in map(json.loads,open(p))})
    if agg['faithful']==1.0 and (best is None or agg['pass']>best[1]): best=(p,agg['pass'])
print(best[0] if best else paths[0])
PY
)
echo "packet model: $BEST"; python3 experiments/exp65_check.py --packet $BEST
echo "== $(date) done"
