"""Run mlx_lm.lora with prompts rendered the way the eval serves them
(thinking off, no system turn) -- same fix as exp52_grpo_launch.py."""
import sys

from mlx_lm.tokenizer_utils import TokenizerWrapper

_orig = TokenizerWrapper.apply_chat_template


def _eval_style(self, conversation, *args, **kwargs):
    kwargs["enable_thinking"] = False
    if conversation and conversation[0].get("role") == "system" \
            and not str(conversation[0].get("content", "")).strip():
        conversation = conversation[1:]
    return _orig(self, conversation, *args, **kwargs)


TokenizerWrapper.apply_chat_template = _eval_style

if __name__ == "__main__":
    from mlx_lm import lora
    sys.argv[0] = "mlx_lm.lora"
    lora.main()
