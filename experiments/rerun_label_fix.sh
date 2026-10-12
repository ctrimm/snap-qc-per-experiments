#!/bin/bash
# Reruns after the label-mode fix (state-policy-docs 2026-10-12): exp87 auto_label (E4B), exp85 label and label+hint (E4B).
set -uo pipefail
cd "$(dirname "$0")"
L=~/.lmstudio/bin/lms; I=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-e4b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) exp87 auto_label (fixed)"
$I eval exp87_heldout_task.py@heldout --model openai/google/gemma-4-e4b -M responses_api=false -T arm=auto_label \
  --max-connections 4 --no-fail-on-error --log-dir $D/exp87_logs/e4b_auto_label_fixed --display none 2>&1 | tail -2
for hint in false true; do
  echo "== $(date) exp85 label hint=$hint (fixed)"
  $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-e4b -M responses_api=false \
    -T mode=auto -T corpus=dates -T dated=true -T date_mode=label -T hint=$hint --max-connections 4 --no-fail-on-error \
    --log-dir $D/exp85_logs/auto_dates_label_hint_${hint}_fixed --display none 2>&1 | tail -2
done
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
