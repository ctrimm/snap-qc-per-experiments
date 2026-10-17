#!/bin/bash
# Queue (2026-10-17): exp98 Cornell ceiling arms. Pre-registration: exp98_cornell_ceiling.md. About 30+ hours.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived/exp98_logs; mkdir -p $D
load() { $L unload --all >/dev/null 2>&1; $L load "$1" --context-length 131072 --parallel 4 -y >/dev/null 2>&1; }
run() {  # model logdir args...
  echo "== $(date) $1 -> $2 ${*:3}"
  $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/$1 -M responses_api=false "${@:3}" \
    --max-connections 4 --no-fail-on-error --log-dir $D/$2 --display none 2>&1 | tail -2
}
load google/gemma-4-e4b
run google/gemma-4-e4b e4b_rp_2026 -T mode=agent -T recipe=true -T passages=true -T as_of=2026-06-01
load google/gemma-4-31b
run google/gemma-4-31b 31b_notools_think -T mode=notools --reasoning-effort high
run google/gemma-4-31b 31b_agent_2026 -T mode=agent -T as_of=2026-06-01
run google/gemma-4-31b 31b_combo_think_verify -T mode=agent -T passages=true -T as_of=2026-06-01 -T verify=true --reasoning-effort high
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
