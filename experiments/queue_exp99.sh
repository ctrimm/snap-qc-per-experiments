#!/bin/bash
# Queue (2026-10-19): exp99, after queue_exp98.sh finishes. 31B dated agent + answer check (about 9 hours), then
# exp99_analyze.py fills the tables in exp98/exp99 chronicles and the vault note, and the results are committed.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived; mkdir -p $D/exp99_logs
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-19 snap-qc exp98-99 Cornell ceiling and the answer check.md"
while pgrep -f "queue_exp9[8][.]sh" >/dev/null; do sleep 120; done
echo "== $(date) exp98 finished; scoring"; $PY exp99_analyze.py > /dev/null
echo "- $(date '+%b %-d, %H:%M'): exp98 finished; tables filled; exp99 started." >> "$VAULT"
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) exp99 31B agent 2026-06-01 + verify"
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false -T mode=agent \
  -T as_of=2026-06-01 -T verify=true --max-connections 4 --no-fail-on-error --log-dir $D/exp99_logs/31b_agent_2026_verify \
  --display none 2>&1 | tail -2
$L unload --all >/dev/null 2>&1
echo "== $(date) scoring"; $PY exp99_analyze.py
echo "- $(date '+%b %-d, %H:%M'): exp99 finished; tables filled by exp99_analyze.py." >> "$VAULT"
cd .. && git add experiments/exp98_cornell_ceiling.md experiments/exp99_verify_plain_agent.md experiments/exp98_99_results.json && \
  git commit -q -m "Exp98/99 results (auto-scored by exp99_analyze.py)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
echo "== $(date) done"
