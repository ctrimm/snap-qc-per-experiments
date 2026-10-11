#!/bin/bash
# Exp86: CalFresh MCQ, Gemma 4 31B (LM Studio google/gemma-4-31b, 128k context, 4 slots): no tools vs exp85's best arm
# (agent + new rule tools, expanded corpus, dated 2025-06-01), same task code (exp85_mcq_rag_task.py).
set -uo pipefail
cd "$(dirname "$0")"
L=~/.lmstudio/bin/lms; I=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
OUT=../../snap-qc-data/derived/exp86_logs; mkdir -p $OUT
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
for cond in notools:new:false agent:new:true; do
  IFS=: read mode corpus dated <<< "$cond"
  echo "== $(date) mode=$mode corpus=$corpus dated=$dated"
  $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false \
    -T mode=$mode -T corpus=$corpus -T dated=$dated --max-connections 4 --no-fail-on-error \
    --log-dir $OUT/${mode}_${corpus}_dated_${dated} --display none 2>&1 | tail -3
done
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
