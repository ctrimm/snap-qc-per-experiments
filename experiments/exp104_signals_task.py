"""Exp104 part B: cheap per-question routing signals on the Cornell quiz (no tools, evaluation only).

  mode=letter       one letter (as exp85 notools); run with --epochs 5 and temperature 0.7 for self-consistency
  mode=confidence   "LETTER CONFIDENCE" with a 0-100 self-rated confidence (temperature 0)
  mode=topic        the question's topic from lookup_rule's 38 topics (routing without hand-picked keywords)
Scoring: letter modes score the letter; topic mode is unscored (the label is kept in the score answer).
Run: inspect eval experiments/exp104_signals_task.py@signals --model openai/google/gemma-4-31b -T mode=confidence
"""
import csv
import json
import re
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import Score, Target, mean, scorer
from inspect_ai.solver import TaskState, generate, system_message

DATA = Path.home() / "datasets/snap_scenarios/snap_scenarios.csv"
RULES = Path("/Users/corytrimm/Documents/GitHub/state-policy-docs/mcp_server/rule_index.json")
BASE = "You answer multiple-choice questions about CalFresh, California's SNAP program. "
PROMPTS = {
    "letter": BASE + "Respond with EXACTLY one letter: A, B, C, D or E. Nothing else.",
    "confidence": BASE + ("Respond with the letter of your answer, a space, and how confident you are that it is correct as a "
                          "number from 0 to 100. Example: \"C 70\". Nothing else."),
}


def samples():
    out = []
    for r in csv.DictReader(open(DATA, newline="", encoding="utf-8-sig")):
        body = f"Client:\n{r['preamble_attributes'].strip()}\n\n{r['question'].strip()}"
        out.append(Sample(input=body, target=r["correct_single_answer"].strip(), id=r["question_id"]))
    return out


@scorer(metrics=[mean()])
def letter_conf():
    async def score(state: TaskState, target: Target):
        txt = (state.output.completion or "").strip()
        m = re.search(r"\b([A-E])\b(?:\D{0,10}(\d{1,3}))?", txt.upper())
        pred = m.group(1) if m else None
        conf = int(m.group(2)) if m and m.group(2) else None
        return Score(value=1.0 if pred == target.text.strip().upper() else 0.0, answer=pred,
                     metadata={"confidence": conf})
    return score


@scorer(metrics=[mean()])
def topic_label():
    async def score(state: TaskState, target: Target):
        return Score(value=0.0, answer=(state.output.completion or "").strip().split("\n")[0][:60])
    return score


@task
def signals(mode: str = "letter"):
    assert mode in ("letter", "confidence", "topic")
    if mode == "topic":
        topics = sorted(json.loads(RULES.read_text())["topics"])
        prompt = ("Classify the CalFresh question below by the rule topic it turns on. Answer with exactly one topic name from "
                  "this list and nothing else: " + ", ".join(topics) + ". If none fits, answer other.")
        return Task(dataset=samples(), solver=[system_message(prompt), generate()], scorer=topic_label(),
                    config=GenerateConfig(temperature=0.0, max_tokens=30))
    return Task(dataset=samples(), solver=[system_message(PROMPTS[mode]), generate()], scorer=letter_conf(),
                config=GenerateConfig(temperature=0.0, max_tokens=20))
