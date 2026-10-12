#!/bin/bash
# Queue (2026-10-11): after exp86 finishes, (1) merge state-policy-docs branch ecfr-versions (every CFR
# version since 2024) into main and run its tests, (2) exp87 held-out set: E4B five arms, 31B two arms,
# (3) exp88 grounded flag-card notes: E4B writes plain and grounded notes, 31B judges both,
# (4) analyses. Stops at the first failure. Log: ../../snap-qc-data/derived/queue_after_exp86.log
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect; PY=$SPD/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
D=../../snap-qc-data/derived; OUT=$D/exp87_logs; mkdir -p $OUT
while pgrep -f "exp86_run[.]sh" >/dev/null; do sleep 60; done
echo "== $(date) exp86 done; merging ecfr-versions"
[ -f $D/ecfr_versions_READY ] || { echo "branch not marked ready; stopping"; exit 1; }
git -C $SPD merge-base --is-ancestor ecfr-versions main || git -C $SPD merge --ff-only ecfr-versions || { echo "merge failed; stopping"; exit 1; }
# whole output: the last line is a harmless DeprecationWarning (a tail -1 here stopped the first run)
# (captured first: grep -q on a pipe exits early and, with pipefail, fails the pipeline)
TESTS=$(cd $SPD && .venv/bin/python -m unittest discover -s tests 2>&1)
echo "$TESTS" | grep -x "OK" >/dev/null || { echo "state-policy-docs tests failed; stopping"; echo "$TESTS" | tail -20; exit 1; }
git -C $SPD push -q origin main
load() { $L unload --all >/dev/null 2>&1; $L load "$1" --context-length 131072 --parallel 4 -y >/dev/null 2>&1; }
run87() { echo "== $(date) exp87 $1 $2"; $I eval exp87_heldout_task.py@heldout --model openai/$1 -M responses_api=false \
  -T arm=$2 --max-connections 4 --no-fail-on-error --log-dir $OUT/$3_$2 --display none 2>&1 | tail -2; }
load google/gemma-4-e4b
for arm in notools auto_undated auto_filter auto_label agent; do run87 google/gemma-4-e4b $arm e4b; done
echo "== $(date) exp88 write"
$PY exp88_grounded_notes.py write --arm plain && $PY exp88_grounded_notes.py write --arm grounded
load google/gemma-4-31b
for arm in notools agent; do run87 google/gemma-4-31b $arm 31b; done
echo "== $(date) exp88 judge"
$PY exp88_grounded_notes.py judge --arm plain && $PY exp88_grounded_notes.py judge --arm grounded
$L unload --all >/dev/null 2>&1
$PY exp87_analyze.py > $D/exp87_results.json 2>/dev/null
$PY exp88_grounded_notes.py score > $D/exp88_results.json 2>/dev/null
echo "== $(date) done"
