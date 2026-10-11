#!/bin/bash
# Exp85 post-hoc arms (amendment 4): auto / dates corpus / as_of 2025-06-01 / label date mode, without and with the hint.
# Waits for exp85_run.sh and exp85_hint_after.sh to finish.
set -uo pipefail
cd "$(dirname "$0")"
while pgrep -f "exp85_run[.]sh|exp85_hint_after[.]sh" >/dev/null; do sleep 60; done
L=~/.lmstudio/bin/lms; I=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
OUT=../../snap-qc-data/derived/exp85_logs
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-e4b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
for hint in false true; do
  echo "== $(date) mode=auto corpus=dates dated=true date_mode=label hint=$hint"
  $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-e4b -M responses_api=false \
    -T mode=auto -T corpus=dates -T dated=true -T date_mode=label -T hint=$hint --max-connections 4 --no-fail-on-error \
    --log-dir $OUT/auto_dates_label_hint_$hint --display none 2>&1 | tail -3
done
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
