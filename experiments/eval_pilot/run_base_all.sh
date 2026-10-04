#!/bin/bash
# exp30 base-model run: 4 prompt conditions, sequential, resume-safe.
set -u
cd "$(dirname "$0")"
export QC_EVAL_MODEL="${QC_EVAL_MODEL:-google/gemma-4-31b}"
for ct in "zero jargon" "zero plain" "few jargon" "few plain"; do
  set -- $ct
  echo "=== $(date '+%F %T') start $1/$2"
  python3 run_lm.py --condition "$1" --template "$2" --split test \
    --out "preds_base_${1}_${2}.jsonl"
  echo "=== $(date '+%F %T') done $1/$2 (exit $?)"
done
