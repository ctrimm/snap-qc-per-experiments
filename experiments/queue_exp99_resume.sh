#!/bin/bash
# Resume exp99 (paused 2026-10-19 after 270 of 500 questions so exp100 could run first): the remaining 230 questions,
# same settings, into a second log; exp99_analyze.py merges the two. Then sync the local state-policy-docs.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived/exp99_logs
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-19 snap-qc exp98-99 Cornell ceiling and the answer check.md"
while pgrep -f "queue_exp10[0][.]sh" >/dev/null; do sleep 120; done
echo "- $(date '+%b %-d, %H:%M'): exp99 resumed (230 remaining questions)." >> "$VAULT"
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) exp99 part 2"
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false -T mode=agent \
  -T as_of=2026-06-01 -T verify=true --sample-id "$(cat $D/remaining_ids.txt)" --max-connections 4 --no-fail-on-error \
  --log-dir $D/31b_agent_2026_verify_part2 --display none 2>&1 | tail -2
$L unload --all >/dev/null 2>&1
echo "== $(date) scoring"; $PY exp99_analyze.py; $PY exp100_analyze.py > /dev/null
echo "- $(date '+%b %-d, %H:%M'): exp99 finished (two logs merged); tables filled." >> "$VAULT"
cd .. && git add experiments/exp98_cornell_ceiling.md experiments/exp99_verify_plain_agent.md experiments/exp98_99_results.json experiments/exp100_supersession_notes.md experiments/exp100_results.json && \
  git commit -q -m "Exp99 results (resumed run, two logs merged; auto-scored)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
cd /Users/corytrimm/Documents/GitHub/state-policy-docs && git fetch -q origin && git merge -q --ff-only origin/main && \
  git worktree remove ../state-policy-docs-merge && git branch -q -d merge-hf-2026-10-18 && echo "$(date) state-policy-docs synced to $(git log --oneline -1)"
echo "== $(date) done"
