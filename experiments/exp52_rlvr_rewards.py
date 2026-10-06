"""Registers the exp52 reward functions with mlx-lm-lora's GRPO trainer.

Imports mlx_lm_lora, so it only loads in the training venv
(~/throwaway-mlxlora/.venv, as in snap-eval's RLVR runs). The logic lives in
exp52_rlvr_scoring.py.

    --reward-functions-file experiments/exp52_rlvr_rewards.py \\
    --reward-functions "qc_task_reward,qc_format_reward" \\
    --reward-weights "[0.9, 0.1]"
"""
import sys
from pathlib import Path

from mlx_lm_lora.trainer.grpo_reward_functions import register_reward_function

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exp52_rlvr_scoring import score_format_batch, score_t12_batch, score_task_batch  # noqa: E402


@register_reward_function()
def qc_task_reward(prompts: list, completions: list, answer: list, types: list | None = None) -> list[float]:
    return score_task_batch(completions, answer, types)


@register_reward_function()
def qc_format_reward(prompts: list, completions: list, answer: list, types: list | None = None) -> list[float]:
    return score_format_batch(completions, answer, types)


@register_reward_function()
def qc_t12_reward(prompts: list, completions: list, answer: list, types: list | None = None) -> list[float]:
    return score_t12_batch(completions, answer, types)
