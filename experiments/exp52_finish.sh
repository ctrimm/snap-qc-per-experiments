#!/bin/bash
# Exp52: finish the 800-step GRPO run after the Metal resource-limit crash,
# and gate-evaluate both the step-250 checkpoint and the final one.
#
# The crash ([metal::malloc] Resource limit (499000) exceeded, ml-explore/mlx
# #3849) is mx.compile caching one variant per completion length; a fresh
# process resets it (snap-eval note 2026-08-30, Sept 2 update). So training
# continues in segments from the latest checkpoint, each segment in its own
# adapter dir and log (resumes restart checkpoint numbering, and a shared dir
# would overwrite earlier checkpoints), with a new seed so data order differs.
# --resume-adapter-file restores weights only, not optimizer state.
set -uo pipefail
cd "$(dirname "$0")/.."
D="$(cd .. && pwd)/snap-qc-data/derived/exp52_rlvr"
TARGET=800
done_steps=250
resume="$D/adapters/grpo-v1/0000250_adapters.safetensors"

# 1. matched bf16 base + the existing step-250 tuned preds -> gate at step 250
experiments/exp52_gate_eval.sh "$D/adapters/grpo-v1" grpo_v1_step250

# 2. training segments until TARGET
seg=2
while [ "$done_steps" -lt "$TARGET" ]; do
  remaining=$((TARGET - done_steps))
  dir="$D/adapters/grpo-v1-seg$seg"
  echo "=== $(date '+%F %T') segment $seg: resume $resume, $remaining iters -> $dir"
  RESUME="$resume" SEED=$((20261005 + seg)) VAL_BATCHES=10 \
    experiments/exp52_grpo_train.sh "$remaining" "$dir" > "$D/train-grpo-v1-seg$seg.log" 2>&1
  if grep -q "Saved final weights" "$D/train-grpo-v1-seg$seg.log"; then
    progress=$remaining
    resume="$dir/adapters.safetensors"
  else
    last=$(ls "$dir" 2>/dev/null | grep -E '^[0-9]+_adapters' | sort | tail -1)
    [ -z "$last" ] && { echo "segment $seg made no checkpoint; stopping"; exit 1; }
    progress=$((10#${last%%_*}))
    resume="$dir/$last"
  fi
  done_steps=$((done_steps + progress))
  echo "=== $(date '+%F %T') segment $seg ended: +$progress -> $done_steps/$TARGET"
  final_dir="$dir"
  seg=$((seg + 1))
done

# 3. gate on the final checkpoint (copy it to a clean dir with its config)
fin="$D/adapters/grpo-v1-final"
mkdir -p "$fin"
cp "$resume" "$fin/adapters.safetensors"
cp "$final_dir/adapter_config.json" "$fin/"
experiments/exp52_gate_eval.sh "$fin" grpo_v1_step800
echo "=== $(date '+%F %T') exp52 finish complete"
