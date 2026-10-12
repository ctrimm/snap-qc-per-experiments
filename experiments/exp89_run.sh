#!/bin/bash
# Exp89: E4B writes grounded_end notes; 31B re-judges plain, grounded and grounded_end with judge v2.
set -uo pipefail
cd "$(dirname "$0")"
L=~/.lmstudio/bin/lms; PY=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/python
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-e4b --context-length 32768 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) write grounded_end"; $PY exp89_rejudge_and_end_cites.py write
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 32768 --parallel 4 -y >/dev/null 2>&1
echo "== $(date) judge v2"; $PY exp89_rejudge_and_end_cites.py judge
$L unload --all >/dev/null 2>&1
$PY exp89_rejudge_and_end_cites.py score > ../../snap-qc-data/derived/exp89_results.txt 2>/dev/null
echo "== $(date) done"
