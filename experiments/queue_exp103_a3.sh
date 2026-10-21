#!/bin/bash
# Exp103 A3 (added after A0): after queue_exp103.sh finishes, run A3 (weighting + date + notes, no precedence), score, commit.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived/exp103_logs
IDS=/Users/corytrimm/Documents/GitHub/snap-qc-data/derived/exp103_screen/screen_ids.txt
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-21 snap-qc exp103 screening the expanded corpus.md"
while pgrep -f "queue_exp10[3][.]sh" >/dev/null; do sleep 60; done
$L ps | grep -q "gemma-4-31b" || $L load google/gemma-4-31b --context-length 262144 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) A3"
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false -T mode=agent \
  -T as_of=2026-06-01 -T "subset=ids:$IDS" -T letter_decay=true -T date_in_prompt=true -T supersession=true \
  --max-connections 4 --no-fail-on-error --retry-on-error 2 --log-dir $D/A3 --display none 2>&1 | tail -2
$L unload --all >/dev/null 2>&1
$PY exp103_analyze.py; echo "- $(date '+%b %-d, %H:%M'): A3 done; tables filled." >> "$VAULT"
cd .. && git add experiments/exp103_screen_corpus.md experiments/exp103_results.json && git commit -q -m "Exp103 A3 results (auto-scored)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
echo "== $(date) done"
