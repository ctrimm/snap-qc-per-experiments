#!/bin/bash
# Queue (2026-10-16): exp94 (224-question hard set), exp95 (recipe + passages; routers are computed afterwards),
# exp96 (answer guard on the exp92 fine-tune). About 18 hours. Pre-registrations: exp94/95/96 *.md.
set -uo pipefail
cd "$(dirname "$0")"
SPD=/Users/corytrimm/Documents/GitHub/state-policy-docs
L=~/.lmstudio/bin/lms; I=$SPD/.venv/bin/inspect
export OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=lm-studio EXP87_SPD=$SPD
D=../../snap-qc-data/derived; mkdir -p $D/exp94_logs $D/exp95_logs $D/exp96_logs
load() { $L unload --all >/dev/null 2>&1; $L load "$1" --context-length 131072 --parallel 4 -y >/dev/null 2>&1; }
probe() {  # memory: a broken Gemma 4 build never stops; check before any long run
  r=$(curl -s $OPENAI_BASE_URL/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"$1\",\"messages\":[{\"role\":\"user\",\"content\":\"Say OK.\"}],\"max_tokens\":40}" \
      | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['finish_reason'])" 2>/dev/null)
  echo "== probe $1 finish_reason=$r"; [ "$r" = "stop" ]
}
held() {  # model arm data logdir [extra -T args]
  echo "== $(date) $1 $2 data=$3 -> $4"
  $I eval exp87_heldout_task.py@heldout --model openai/$1 -M responses_api=false -T arm=$2 -T data=$3 "${@:5}" \
    --max-connections 4 --no-fail-on-error --log-dir $D/$4 --display none 2>&1 | tail -2
}
cornell() {  # model logdir [extra -T args]
  echo "== $(date) $1 cornell -> $2"
  $I eval exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/$1 -M responses_api=false -T mode=agent -T corpus=new \
    -T dated=true "${@:3}" --max-connections 4 --no-fail-on-error --log-dir $D/$2 --display none 2>&1 | tail -2
}

# exp94 + exp95, E4B Q4_K_M
E=google/gemma-4-e4b; load $E
for arm in notools auto_filter agent agent_strict agent_recipe; do held $E $arm exp94_hard.jsonl exp94_logs/e4b_$arm; done
held $E agent_recipe_passages exp94_hard.jsonl exp95_logs/e4b_rp_exp94
held $E agent_recipe_passages exp87_heldout.jsonl exp95_logs/e4b_rp_exp87
cornell $E exp95_logs/e4b_rp_cornell -T recipe=true -T passages=true

# exp94, 31B
B=google/gemma-4-31b; load $B
for arm in notools agent; do held $B $arm exp94_hard.jsonl exp94_logs/31b_$arm; done

# exp96, bf16 exp92 models
T=gemma-4-e4b-exp92-tooluse-full; load $T
if probe $T; then
  for g in 4 6 8; do cornell $T exp96_logs/tuned_cornell_g$g -T guard=$g; done
  held $T agent exp94_hard.jsonl exp96_logs/tuned_exp94_g6 -T guard=6
  held $T agent exp94_hard.jsonl exp96_logs/tuned_exp94_g0
else echo "== tuned model failed the probe; skipping its runs"; fi
M=gemma-4-e4b-base; load $M
if probe $M; then
  cornell $M exp96_logs/base_cornell_g6 -T guard=6
  held $M agent exp94_hard.jsonl exp96_logs/base_exp94_g6 -T guard=6
  held $M agent exp94_hard.jsonl exp96_logs/base_exp94_g0
else echo "== base model failed the probe; skipping its runs"; fi
$L unload --all >/dev/null 2>&1
echo "== $(date) done"
