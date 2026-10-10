#!/bin/bash
# Exp70: CalFresh 500-question policy quiz, untrained vs QC-fine-tuned E4B, plus 31B setup check.
set -uo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/throwaway-mlxlora/.venv/bin/python"; D="$(cd .. && pwd)/snap-qc-data/derived"; E=experiments
A=$D/exp52_sft_runs/sft_lr1e-5_600/ckpt_400
echo "== $(date) e4b untrained"; "$PY" $E/exp70_calfresh_mcq.py --model mlx-community/gemma-4-e4b-it-bf16 --out $E/exp70_e4b_base.jsonl
echo "== $(date) e4b sft400"; "$PY" $E/exp70_calfresh_mcq.py --model mlx-community/gemma-4-e4b-it-bf16 --adapter $A --out $E/exp70_e4b_sft400.jsonl
echo "== $(date) 31b untrained"; "$PY" $E/exp70_calfresh_mcq.py --model mlx-community/gemma-4-31b-it-bf16 --out $E/exp70_31b_base.jsonl
echo "== $(date) score"
python3 $E/exp70_calfresh_mcq.py --score $E/exp70_e4b_base.jsonl $E/exp70_e4b_sft400.jsonl
python3 $E/exp70_calfresh_mcq.py --score $E/exp70_31b_base.jsonl
echo "== $(date) done"
