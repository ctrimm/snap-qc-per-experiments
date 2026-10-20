#!/bin/bash
# Queue (2026-10-20, amended exp101): three citizenship arms, then the combined arm + date on all 500 (30-40 hours).
# 31B loaded with a 262,144-token context (about 65k per slot); exp98 arm 4's errors were context overflows.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived/exp101_logs; mkdir -p $D
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-20 snap-qc exp101 telling the model the date.md"
echo "- $(date '+%b %-d, %H:%M'): started (amended) on state-policy-docs $(git -C $SPD log --oneline -1 | cut -c1-7); 31B context 262,144." >> "$VAULT"
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 262144 --parallel 4 -y >/dev/null 2>&1
corn() { echo "== $(date) $1"; $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false \
  -T mode=agent -T as_of=2026-06-01 "${@:2}" --max-connections 4 --no-fail-on-error --retry-on-error 2 --log-dir $D/$1 --display none 2>&1 | tail -2; }
corn cit_baseline -T subset=citizenship
corn cit_date -T subset=citizenship -T date_in_prompt=true
corn cit_date_notes -T subset=citizenship -T date_in_prompt=true -T supersession=true -T precedence=true
$PY exp101_analyze.py > /dev/null; echo "- $(date '+%b %-d, %H:%M'): citizenship runs done; tables filled; full combined + date run started." >> "$VAULT"
corn full_combo_date -T passages=true -T verify=true -T date_in_prompt=true --reasoning-effort high
$L unload --all >/dev/null 2>&1
echo "== $(date) scoring"; $PY exp101_analyze.py
echo "- $(date '+%b %-d, %H:%M'): exp101 finished; tables filled by exp101_analyze.py." >> "$VAULT"
cd .. && git add experiments/exp101_date_in_prompt.md experiments/exp101_results.json && \
  git commit -q -m "Exp101 results (auto-scored by exp101_analyze.py)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
echo "== $(date) done"
