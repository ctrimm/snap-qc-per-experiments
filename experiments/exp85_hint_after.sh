#!/bin/bash
# Exp85 post-hoc arm (amendment 3): auto / new / undated + pre-H.R. 1 hint. Waits for exp85_run.sh to finish.
set -uo pipefail
cd "$(dirname "$0")"
while pgrep -f "exp85_run[.]sh" >/dev/null; do sleep 60; done
L=~/.lmstudio/bin/lms; I=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
OUT=../../snap-qc-data/derived/exp85_logs
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-e4b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) mode=auto corpus=new dated=false hint=true"
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-e4b -M responses_api=false \
  -T mode=auto -T corpus=new -T dated=false -T hint=true --max-connections 4 --no-fail-on-error \
  --log-dir $OUT/auto_new_dated_false_hint --display none 2>&1 | tail -3
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
