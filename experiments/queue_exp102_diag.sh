#!/bin/bash
# After exp102 arm 1 (pid 36836) and the diagnostic (pid 77393), both running: close the paused queue (36787),
# score arm 1 and the diagnostic, then run arm 2 as registered.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived/exp102_logs
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-20 snap-qc exp102 combined setup on the expanded corpus.md"
while kill -0 36836 2>/dev/null || kill -0 77393 2>/dev/null; do sleep 30; done
kill -9 36787 2>/dev/null
$PY exp102_analyze.py > /dev/null; $PY exp102_diag.py
echo "- $(date '+%b %-d, %H:%M'): arm 1 and the diagnostic finished; tables filled; arm 2 started." >> "$VAULT"
echo "== $(date) exp102 arm 2: full combined"
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false -T mode=agent \
  -T as_of=2026-06-01 -T passages=true -T verify=true --reasoning-effort high --max-connections 4 --no-fail-on-error \
  --retry-on-error 2 --log-dir $D/full_combo --display none 2>&1 | tail -2
$L unload --all >/dev/null 2>&1
$PY exp102_analyze.py; echo "- $(date '+%b %-d, %H:%M'): exp102 finished; tables filled." >> "$VAULT"
cd .. && git add experiments/exp102_combined_expanded_corpus.md experiments/exp102_results.json && git commit -q -m "Exp102 results (auto-scored)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
echo "== $(date) done"
