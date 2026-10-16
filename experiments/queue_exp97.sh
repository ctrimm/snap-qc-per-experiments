#!/bin/bash
# Queue (2026-10-16): exp97, after queue_exp94_96.sh finishes. Notes with mlx (E2B exp77 model, E4B zero-shot), then the
# 31B part-reference judge in LM Studio, then scoring. Pre-registration: exp97_rules_line.py docstring and .md.
set -uo pipefail
cd "$(dirname "$0")/.."
E=experiments; D="$(cd .. && pwd)/snap-qc-data/derived"; O=$D/exp97; mkdir -p $O
PY="$HOME/throwaway-mlxlora/.venv/bin/python"; SPY=/Users/corytrimm/Documents/GitHub/state-policy-docs/.venv/bin/python
L=~/.lmstudio/bin/lms; export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio
while pgrep -f "queue_exp94_9[6][.]sh" >/dev/null; do sleep 120; done
echo "== $(date) exp97 notes e2b (exp77 step 500)"
C=$D/exp52_sft_runs/exp77_e2b_explainer_v2/ckpt_500
[ -d $C ] || { mkdir -p $C; cp $D/exp52_sft_runs/exp77_e2b_explainer_v2/adapter_config.json $C/; cp $D/exp52_sft_runs/exp77_e2b_explainer_v2/0000500_adapters.safetensors $C/adapters.safetensors; }
"$PY" $E/exp62_rewrite.py --model mlx-community/gemma-4-e2b-it-bf16 --adapter $C --wording v2 --cards $E/exp97_cards.jsonl \
  --ids $E/exp97_ids.txt --out $O/notes_e2b.jsonl > $O/notes_e2b.log 2>&1
echo "== $(date) exp97 notes e4b (zero-shot)"
"$PY" $E/exp62_rewrite.py --model mlx-community/gemma-4-e4b-it-bf16 --wording v2 --cards $E/exp97_cards.jsonl \
  --ids $E/exp97_ids.txt --out $O/notes_e4b.jsonl > $O/notes_e4b.log 2>&1
echo "== $(date) exp97 judge (31B)"
$L unload --all >/dev/null 2>&1; $L load google/gemma-4-31b --context-length 32768 --parallel 1 -y >/dev/null 2>&1
for w in e2b e4b; do python3 $E/exp97_rules_line.py judge $w; done
$L unload --all >/dev/null 2>&1
echo "== $(date) exp97 score"
$SPY $E/exp97_rules_line.py score | tee $D/exp97_results.json
echo "== $(date) done"
