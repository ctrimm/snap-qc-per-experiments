#!/bin/bash
# Exp85: CalFresh MCQ, Gemma 4 E4B (LM Studio, Q4_K_M, 128k context, 4 slots): notools; auto x {old undated, new undated, new as_of 2025-06-01}; agent x {new as_of, new undated}.
set -uo pipefail
cd "$(dirname "$0")"
L=~/.lmstudio/bin/lms; I=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
OUT=../../snap-qc-data/derived/exp85_logs; mkdir -p $OUT
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-e4b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
CONDS=${*:-notools:new:false auto:old:false auto:new:false auto:new:true agent:new:true agent:new:false}
for cond in $CONDS; do
  IFS=: read mode corpus dated <<< "$cond"
  echo "== $(date) mode=$mode corpus=$corpus dated=$dated"
  $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-e4b -M responses_api=false \
    -T mode=$mode -T corpus=$corpus -T dated=$dated --max-connections 4 --no-fail-on-error --log-dir $OUT/${mode}_${corpus}_dated_${dated} --display none 2>&1 | tail -3
done
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
