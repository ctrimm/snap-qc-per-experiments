#!/bin/bash
# Queue (2026-10-22): exp105. Part 0 (~3.5 h): 31B agent on our 121 California hard-set questions, current defaults vs
# cite-only + curated guidance; exp105_decide.py picks part 1's config. Part 1 (~12 h): E4B topic labels, plain dated
# agent on all 500, date + notes on the noncitizens-labeled questions. Pre-registration: exp105_topic_router.md.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio EXP87_SPD=$SPD
D=../../snap-qc-data/derived/exp105_logs; mkdir -p $D
VAULT="$HOME/Documents/Obsidian Vault/Labs/2026-10-22 snap-qc exp105 topic router.md"
log() { echo "- $(date '+%b %-d, %H:%M'): $1" >> "$VAULT"; }
B=google/gemma-4-31b; E=google/gemma-4-e4b
log "started on state-policy-docs $(git -C $SPD log --oneline -1 | cut -c1-8)."

# part 1 step 1 first (avoids an extra reload): E4B topic labels
$L unload --all >/dev/null 2>&1; $L load $E --context-length 32768 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) E4B topic labels"
$I eval exp104_signals_task.py@signals --model openai/$E -M responses_api=false -T mode=topic --max-connections 4 \
  --no-fail-on-error --log-dir $D/e4b_topic --display none 2>&1 | tail -2
NC=$($PY exp105_decide.py ids 2>/dev/null | tail -1); log "E4B labels done: $NC questions labeled noncitizens."

$L unload --all >/dev/null 2>&1; $L load $B --context-length 262144 --parallel 4 -y >/dev/null 2>&1
for arm in A C; do
  extra=""; [ $arm = C ] && extra="-T cite_only=true -T curated=true"
  echo "== $(date) part 0 arm $arm"
  $I eval exp87_heldout_task.py@heldout --model openai/$B -M responses_api=false -T arm=agent -T data=exp105_ca_hard.jsonl $extra \
    --max-connections 4 --no-fail-on-error --retry-on-error 2 --log-dir $D/p0_$arm --display none 2>&1 | tail -2
done
CFG=$($PY exp105_decide.py config 2>/dev/null | tail -1)
$PY exp105_analyze.py > /dev/null 2>&1; log "part 0 done: $(cat ../../snap-qc-data/derived/exp105/config.txt). Part 1 plain started."

echo "== $(date) part 1 plain ($CFG)"
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/$B -M responses_api=false -T mode=agent -T as_of=2026-06-01 $CFG \
  --max-connections 4 --no-fail-on-error --retry-on-error 2 --log-dir $D/plain --display none 2>&1 | tail -2
log "plain done."
echo "== $(date) part 1 date + notes on noncitizens-labeled"
$I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/$B -M responses_api=false -T mode=agent -T as_of=2026-06-01 $CFG \
  -T date_in_prompt=true -T supersession=true -T precedence=true -T subset=ids:$(cd ../../snap-qc-data/derived/exp105 && pwd)/noncit_ids.txt \
  --max-connections 4 --no-fail-on-error --retry-on-error 2 --log-dir $D/datenotes_noncit --display none 2>&1 | tail -2
$L unload --all >/dev/null 2>&1
echo "== $(date) scoring"; $PY exp105_analyze.py
log "exp105 finished; tables filled by exp105_analyze.py."
cd .. && git add experiments/exp105_topic_router.md && git commit -q -m "Exp105 results (auto-scored by exp105_analyze.py)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FEmxrXJ1o2WY8mdD7JsA7r" && git push -q origin main
echo "== $(date) done"
