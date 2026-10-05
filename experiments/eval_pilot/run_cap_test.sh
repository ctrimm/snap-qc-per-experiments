#!/bin/bash
# exp30 v1.1 cap test: few/jargon on the stratified 300-item subset.
#   1. gemma-4-31b at max_tokens 1500 (pairs with v1 preds_base_few_jargon at 400)
#   2. gemma-4-e4b at 1500 and at 400 (same paired cap readout for the small model)
set -u
cd "$(dirname "$0")"
LMS="$HOME/.lmstudio/bin/lms"
run() {  # model tag max_tokens
  echo "=== $(date '+%F %T') start $2 mt$3"
  QC_EVAL_MODEL="$1" python3 run_lm.py --condition few --template jargon \
    --split test --ids subset_300.txt --max-tokens "$3" \
    --out "preds_v11_${2}_few_jargon_mt${3}.jsonl"
  echo "=== $(date '+%F %T') done $2 mt$3 (exit $?)"
}
run google/gemma-4-31b 31b 1500
"$LMS" ps | grep -q "google/gemma-4-e4b" || "$LMS" load google/gemma-4-e4b -y
run google/gemma-4-e4b e4b 1500
run google/gemma-4-e4b e4b 400
