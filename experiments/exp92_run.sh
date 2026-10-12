#!/bin/bash
# Exp92: distill Gemma 4 31B tool use into E4B. Stages (stops at the first failure):
#  1 wait for question generation; merge; overlap audit vs the Cornell quiz
#  2 31B agent trajectories on exp92_train.jsonl (exp87 task, plain agent prompt)
#  3 SFT data (correct trajectories, one example per model turn)
#  4 LoRA SFT of mlx-community/gemma-4-e4b-it-bf16 (exp52 recipe; 2 epochs; final checkpoint)
#  5 fuse into LM Studio (snap-qc/gemma-4-e4b-exp92-tooluse)
#  6 evaluate base bf16 vs tuned (same engine, precision, settings): Cornell agent dated + no tools, exp90 agent, exp87 agent
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python; MPY=$HOME/throwaway-mlxlora/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived; X=$D/exp92; mkdir -p $X $D/exp92_logs
die() { echo "STOP: $1"; exit 1; }
while pgrep -f "exp92_build_train[.]py open" >/dev/null; do sleep 60; done
echo "== $(date) merge"
$PY exp92_build_train.py merge || die merge
rm -rf $X/audit_dir && mkdir -p $X/audit_dir && cp exp92_train.jsonl $X/audit_dir/
$PY audit_mcq_contamination.py $X/audit_dir > $X/audit_train.json 2>/dev/null
grep -q '"files_scanned": 1,' $X/audit_train.json && grep -q '"files_with_hits": {}' $X/audit_train.json \
  || die "overlap audit failed or found Cornell text (see $X/audit_train.json)"
echo "== $(date) 31B trajectories"
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
$I eval exp87_heldout_task.py@heldout --model openai/google/gemma-4-31b -M responses_api=false -T arm=agent \
  -T data=exp92_train.jsonl --max-connections 4 --no-fail-on-error --log-dir $D/exp92_logs/31b_traj --display none 2>&1 | tail -2
$L unload --all >/dev/null 2>&1
echo "== $(date) SFT data"
$PY exp92_make_sft.py $D/exp92_logs/31b_traj $X/sft || die "sft data"
N=$(wc -l < $X/sft/train.jsonl); ITERS=$(( (2 * N + 3) / 4 ))
echo "== $(date) train: $N examples, $ITERS iters"
$MPY exp52_sft_launch.py --model mlx-community/gemma-4-e4b-it-bf16 --train --data $X/sft --adapter-path $X/adapter \
  -c exp52_sft_lora.yaml --iters $ITERS --batch-size 4 --learning-rate 1e-5 --max-seq-length 8192 --grad-checkpoint \
  --mask-prompt --steps-per-eval 100 --val-batches 10 --save-every 200 --seed 92 > $X/train.log 2>&1 || die "training (see $X/train.log)"
echo "== $(date) fuse"
rm -rf ~/.lmstudio/models/snap-qc/gemma-4-e4b-exp92-tooluse
$MPY -m mlx_lm fuse --model mlx-community/gemma-4-e4b-it-bf16 --adapter-path $X/adapter \
  --save-path ~/.lmstudio/models/snap-qc/gemma-4-e4b-exp92-tooluse > $X/fuse.log 2>&1 || die fuse
TUNED=$($L ls --json | $PY -c "import json,sys; print(next(m['modelKey'] for m in json.load(sys.stdin) if 'exp92-tooluse' in (m.get('path') or '')))")
BASE=gemma-4-e4b-base
echo "== $(date) evaluate base=$BASE tuned=$TUNED"
for M in $BASE $TUNED; do
  $L unload --all >/dev/null 2>&1; $L load $M --context-length 131072 --parallel 4 -y >/dev/null 2>&1
  tag=$([ "$M" = "$BASE" ] && echo base || echo tuned)
  for mode in notools agent; do
    echo "== $(date) $tag cornell $mode"
    $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/$M -M responses_api=false -T mode=$mode -T corpus=new \
      -T dated=true --max-connections 4 --no-fail-on-error --log-dir $D/exp92_logs/${tag}_cornell_$mode --display none 2>&1 | tail -2
  done
  for data in exp90_hard.jsonl exp87_heldout.jsonl; do
    echo "== $(date) $tag $data agent"
    $I eval exp87_heldout_task.py@heldout --model openai/$M -M responses_api=false -T arm=agent -T data=$data \
      --max-connections 4 --no-fail-on-error --log-dir $D/exp92_logs/${tag}_${data%%_*}_agent --display none 2>&1 | tail -2
  done
done
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
