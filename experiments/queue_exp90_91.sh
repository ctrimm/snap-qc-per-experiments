#!/bin/bash
# Queue (2026-10-12): after exp89 finishes. exp90 (harder rule questions) and exp91 (tool-calling fixes for E4B).
#  E4B:  exp90 notools, auto_filter, agent, agent_strict, agent_recipe
#        exp91 on exp87 set: agent (same-day rerun), agent_strict, agent_recipe
#        exp91 on the Cornell quiz: agent (dated, rerun), agent + recipe (dated)
#  31B:  exp90 notools, agent
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived; mkdir -p $D/exp90_logs $D/exp91_logs
while pgrep -f "exp89_run[.]sh" >/dev/null; do sleep 60; done
load() { $L unload --all >/dev/null 2>&1; $L load "$1" --context-length 131072 --parallel 4 -y >/dev/null 2>&1; }
held() { echo "== $(date) $4 $1 $2 data=$3"; $I eval exp87_heldout_task.py@heldout --model openai/$1 -M responses_api=false \
  -T arm=$2 -T data=$3 --max-connections 4 --no-fail-on-error --log-dir $D/$4_logs/$5_$2 --display none 2>&1 | tail -2; }
load google/gemma-4-e4b
for arm in notools auto_filter agent agent_strict agent_recipe; do held google/gemma-4-e4b $arm exp90_hard.jsonl exp90 e4b; done
for arm in agent agent_strict agent_recipe; do held google/gemma-4-e4b $arm exp87_heldout.jsonl exp91 e4b_exp87set; done
for recipe in false true; do
  echo "== $(date) exp91 cornell agent dated recipe=$recipe"
  $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-e4b -M responses_api=false \
    -T mode=agent -T corpus=new -T dated=true -T recipe=$recipe --max-connections 4 --no-fail-on-error \
    --log-dir $D/exp91_logs/e4b_cornell_agent_recipe_$recipe --display none 2>&1 | tail -2
done
load google/gemma-4-31b
for arm in notools agent; do held google/gemma-4-31b $arm exp90_hard.jsonl exp90 31b; done
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
