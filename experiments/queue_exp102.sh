#!/bin/bash
# Queue (2026-10-20): exp102 after the local state-policy-docs syncs to 7a265f0 (CDSS letters import). 35-40 hours.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived/exp102_logs; mkdir -p $D
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-20 snap-qc exp102 combined setup on the expanded corpus.md"
until [ "$(git -C $SPD rev-parse --short HEAD)" = "7a265f0" ]; do sleep 120; done
echo "- $(date '+%b %-d, %H:%M'): started on state-policy-docs $(git -C $SPD log --oneline -1 | cut -c1-7) ($(python3 -c "import json;m=json.load(open('$SPD/manifest.json'));print(len(m.get('documents',m)))") documents)." >> "$VAULT"
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 262144 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) exp102 full combined"
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-31b -M responses_api=false -T mode=agent \
  -T as_of=2026-06-01 -T passages=true -T verify=true --reasoning-effort high --max-connections 4 --no-fail-on-error \
  --retry-on-error 2 --log-dir $D/full_combo --display none 2>&1 | tail -2
$L unload --all >/dev/null 2>&1
echo "== $(date) scoring"; $PY exp102_analyze.py
echo "- $(date '+%b %-d, %H:%M'): exp102 finished; tables filled by exp102_analyze.py." >> "$VAULT"
cd .. && git add experiments/exp102_combined_expanded_corpus.md experiments/exp102_results.json && \
  git commit -q -m "Exp102 results (auto-scored by exp102_analyze.py)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
echo "== $(date) done"
