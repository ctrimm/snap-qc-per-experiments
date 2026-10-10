#!/bin/bash
# Exp62 step 1: zero-shot rewrite of the 200 eval cards with E2B and E4B, then the frozen checks.
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"
for m in e2b e4b; do
  O=experiments/exp62_notes_${m}_zeroshot.jsonl
  echo "== $(date) $m"
  [ -s $O ] && [ $(wc -l < $O) -eq 200 ] || "$PY" experiments/exp62_rewrite.py --model mlx-community/gemma-4-${m}-it-bf16 --out $O > /dev/null 2>&1
done
echo "== $(date) checks"
python3 experiments/exp62_check.py template experiments/exp62_notes_e2b_zeroshot.jsonl experiments/exp62_notes_e4b_zeroshot.jsonl
echo "== $(date) done"
