"""Exp 52 — verifiable rewards for GRPO on the QC-variance classification task.

Pure scoring logic (no mlx dependency); exp52_rlvr_rewards.py registers these
with mlx-lm-lora's GRPO trainer. Completions are parsed with the eval's own
parser (eval_pilot/run_lm.parse_class), so training rewards exactly what the
eval scores.

  task reward   -- share of applicable tasks answered correctly: T1 and T2
                   always, T3-T5 only when the label exists (error cases with
                   a primary variance; T4 only for the 12 standard nature
                   codes). An unparseable completion scores 0.
  format reward -- 1 if the completion parses (T1 and T2 valid options, no
                   unparseable T3-T5), else 0. Guards against the truncation
                   and format failures exp30 measured.

Uniform per-example reward, no class weighting (exp43: balanced weighting
does not port to transformer-class models).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "eval_pilot"))
import run_lm  # noqa: E402

TASKS = ("t1", "t2", "t3", "t4", "t5")


def task_reward(completion, answer_json):
    parsed, ok = run_lm.parse_class(completion)
    if not ok:
        return 0.0
    gold = json.loads(answer_json)
    applicable = [t for t in TASKS if gold.get(t) is not None]
    return sum(1 for t in applicable if parsed.get(t) == gold[t]) / len(applicable)


def t12_reward(completion, answer_json):
    """T1 + T2 only: the two tasks the model can most plausibly learn first."""
    parsed, ok = run_lm.parse_class(completion)
    if not ok:
        return 0.0
    gold = json.loads(answer_json)
    return sum(parsed.get(t) == gold[t] for t in ("t1", "t2")) / 2


def format_reward(completion, answer_json=None):
    return 1.0 if run_lm.parse_class(completion)[1] else 0.0


def score_task_batch(completions, answer, types=None):
    return [task_reward(c, a) for c, a in zip(completions, answer)]


def score_t12_batch(completions, answer, types=None):
    return [t12_reward(c, a) for c, a in zip(completions, answer)]


def score_format_batch(completions, answer, types=None):
    return [format_reward(c) for c in completions]
