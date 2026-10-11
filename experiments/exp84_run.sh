#!/bin/bash
# Exp84: CalFresh MCQ, Gemma 4 E2B and E4B (LM Studio, Q4_K_M, 128k context, 4 slots), without and with MCP tools.
set -uo pipefail
cd "$(dirname "$0")"
L=~/.lmstudio/bin/lms; I=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
OUT=../../snap-qc-data/derived/exp84_logs; mkdir -p $OUT
for m in e4b e2b; do
  $L unload --all >/dev/null 2>&1; $L load google/gemma-4-$m --context-length 131072 --parallel 4 -y >/dev/null 2>&1
  for tools in false true; do
    echo "== $(date) $m tools=$tools"
    $I eval exp84_mcq_tools_task.py@calfresh_mcq_e --model openai/google/gemma-4-$m -M responses_api=false \
      -T use_tools=$tools --max-connections 4 --no-fail-on-error --log-dir $OUT/${m}_tools_$tools --display none 2>&1 | tail -3
  done
done
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
