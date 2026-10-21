#!/bin/bash
# Exp103: after exp102 arm 1 (pid 36836) finishes, close exp102's paused queue (36787), score arm 1, build the
# screening set, run A0, A1, A2 one at a time (about 3 hours each), score.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived/exp103_logs; mkdir -p $D
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-21 snap-qc exp103 screening the expanded corpus.md"
VAULT102="$HOME/Documents/Obsidian Vault/Labs/2026-10-20 snap-qc exp102 combined setup on the expanded corpus.md"
while kill -0 36836 2>/dev/null; do sleep 30; done
kill -9 36787 2>/dev/null
$PY exp102_analyze.py > /dev/null
echo "- $(date '+%b %-d, %H:%M'): arm 1 finished; tables filled. Diagnostic and arm 2 replaced by exp103's screening." >> "$VAULT102"
$PY exp103_build_screen.py
IDS=$(cd ..; cd ..; pwd)/snap-qc-data/derived/exp103_screen/screen_ids.txt
echo "- $(date '+%b %-d, %H:%M'): screening set built ($(wc -l < $IDS | tr -d ' ') questions); A0 started." >> "$VAULT"
$L ps | grep -q "gemma-4-31b" || $L load google/gemma-4-31b --context-length 262144 --parallel 4 -y >/dev/null 2>&1
arm() { echo "== $(date) $1"; $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false \
  -T mode=agent -T as_of=2026-06-01 -T "subset=ids:$IDS" "${@:2}" --max-connections 4 --no-fail-on-error --retry-on-error 2 \
  --log-dir $D/$1 --display none 2>&1 | tail -2; $PY exp103_analyze.py > /dev/null; echo "- $(date '+%b %-d, %H:%M'): $1 done; tables filled." >> "$VAULT"; }
arm A0
arm A1 -T letter_decay=true
arm A2 -T letter_decay=true -T date_in_prompt=true -T supersession=true -T precedence=true
$L unload --all >/dev/null 2>&1
$PY exp103_analyze.py
cd .. && git add experiments/exp103_screen_corpus.md experiments/exp103_results.json experiments/exp102_combined_expanded_corpus.md experiments/exp102_results.json && \
  git commit -q -m "Exp103 screening results (auto-scored)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
echo "== $(date) done"
