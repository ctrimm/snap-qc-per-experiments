#!/bin/bash
# Exp92 resume: evaluate the tuned model rebuilt with the full multimodal structure (base tensors + the 665
# fine-tuned language-model tensors). mlx_lm.fuse had written a text-only model that LM Studio would not stop.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived; M=gemma-4-e4b-exp92-tooluse-full
$L unload --all >/dev/null 2>&1; $L load $M --context-length 131072 --parallel 4 -y >/dev/null 2>&1
for mode in notools agent; do
  echo "== $(date) tuned cornell $mode"
  $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/$M -M responses_api=false -T mode=$mode -T corpus=new \
    -T dated=true --max-connections 4 --no-fail-on-error --log-dir $D/exp92_logs/tuned_cornell_$mode --display none 2>&1 | tail -2
done
for data in exp90_hard.jsonl exp87_heldout.jsonl; do
  echo "== $(date) tuned $data agent"
  $I eval exp87_heldout_task.py@heldout --model openai/$M -M responses_api=false -T arm=agent -T data=$data \
    --max-connections 4 --no-fail-on-error --log-dir $D/exp92_logs/tuned_${data%%_*}_agent --display none 2>&1 | tail -2
done
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
