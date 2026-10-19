#!/bin/bash
# Queue (2026-10-19): exp100, after queue_exp99.sh finishes. 31B agent: dev on our noncitizen questions, Cornell
# citizenship subset, then the full Cornell quiz with notes + precedence + check. About 11 hours.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio EXP87_SPD=$SPD
D=../../snap-qc-data/derived/exp100_logs; mkdir -p $D
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-19 snap-qc exp100 supersession notes.md"
DEV="noncitizen|five-year|cfap|cuban|cofa|parolee|refugee|asyl|u visa|trafficking|cross-border|afghan|save"
while pgrep -f "queue_exp9[9][.]sh" >/dev/null; do sleep 120; done
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 131072 --parallel 4 -y >/dev/null 2>&1
M=openai/google/gemma-4-31b
held() { echo "== $(date) dev $1"; $I eval exp87_heldout_task.py@heldout --model $M -M responses_api=false -T arm=agent \
  -T data=exp94_hard.jsonl -T "category=$DEV" "${@:2}" --max-connections 4 --no-fail-on-error --log-dir $D/$1 --display none 2>&1 | tail -2; }
corn() { echo "== $(date) cornell $1"; $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model $M -M responses_api=false -T mode=agent \
  -T as_of=2026-06-01 "${@:2}" --max-connections 4 --no-fail-on-error --log-dir $D/$1 --display none 2>&1 | tail -2; }
held dev_baseline
held dev_notes -T supersession=true -T precedence=true
corn cit_baseline -T subset=citizenship
corn cit_notes -T subset=citizenship -T supersession=true -T precedence=true
$PY exp100_analyze.py > /dev/null; echo "- $(date '+%b %-d, %H:%M'): dev and citizenship runs done; tables filled; full Cornell run started." >> "$VAULT"
corn full_notes_verify -T supersession=true -T precedence=true -T verify=true
$L unload --all >/dev/null 2>&1
echo "== $(date) scoring"; $PY exp100_analyze.py
echo "- $(date '+%b %-d, %H:%M'): exp100 finished; tables filled by exp100_analyze.py." >> "$VAULT"
cd .. && git add experiments/exp100_supersession_notes.md experiments/exp100_results.json && \
  git commit -q -m "Exp100 results (auto-scored by exp100_analyze.py)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
echo "== $(date) done"
