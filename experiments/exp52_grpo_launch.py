"""Launch mlx_lm_lora GRPO with prompts rendered the way the eval serves them.

mlx-lm's TokenizerWrapper defaults enable_thinking to True for Gemma 4, and
GRPODataset always sends a system turn (an empty one when the record's
"system" is ""). LM Studio serves the exp30 eval with thinking off and the
prompt as a single user turn, so training under the defaults would optimize
a thinking-on, system-prompted policy the eval never sees: in a smoke run
96% of completions hit the token cap with no answer. This wrapper forces
enable_thinking=False and drops empty system turns, then hands off to
mlx_lm_lora.train.main() with the original CLI arguments.
"""
from mlx_lm.tokenizer_utils import TokenizerWrapper
from mlx_lm_lora import train

_orig = TokenizerWrapper.apply_chat_template


def _eval_style(self, conversation, *args, **kwargs):
    kwargs["enable_thinking"] = False
    if conversation and conversation[0].get("role") == "system" \
            and not str(conversation[0].get("content", "")).strip():
        conversation = conversation[1:]
    return _orig(self, conversation, *args, **kwargs)


TokenizerWrapper.apply_chat_template = _eval_style

if __name__ == "__main__":
    train.main()
