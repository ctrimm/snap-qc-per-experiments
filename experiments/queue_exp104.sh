#!/bin/bash
# Exp104 part B: no-tool routing signals on the Cornell quiz (about 1 hour in all).
set -uo pipefail
cd "$(dirname "$0")"
L=~/.lmstudio/bin/lms; I=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived/exp104_logs; mkdir -p $D
run() { echo "== $(date) $1 $2"; $I eval exp104_signals_task.py@signals --model openai/$1 -M responses_api=false "${@:3}" \
  --max-connections 4 --no-fail-on-error --log-dir $D/$2 --display none 2>&1 | tail -1; }
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 32768 --parallel 4 -y >/dev/null 2>&1
run google/gemma-4-31b 31b_confidence -T mode=confidence
run google/gemma-4-31b 31b_topic -T mode=topic
run google/gemma-4-31b 31b_sc5 -T mode=letter --epochs 5 --temperature 0.7
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-e4b --context-length 32768 --parallel 4 -y >/dev/null 2>&1
run google/gemma-4-e4b e4b_sc5 -T mode=letter --epochs 5 --temperature 0.7
run google/gemma-4-e4b e4b_topic -T mode=topic
run google/gemma-4-e4b e4b_confidence -T mode=confidence
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
