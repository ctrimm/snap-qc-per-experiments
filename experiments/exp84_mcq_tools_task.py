"""Exp 84 — do the state-policy-docs MCP tools raise Gemma 4 E2B/E4B accuracy on the CalFresh MCQ?

Pre-registered (this docstring, committed before the full runs):
  Data: the 500 Better Government Lab CalFresh scenario questions (local copy
  ~/datasets/snap_scenarios), formatted as exp70 (client attributes +
  question with its embedded options; answers A-E). The sibling repo's
  harness can't load this file (it expects four separate option columns,
  A-D only), so this task reuses its tool setup with exp70's format.
  Models: google/gemma-4-e2b and google/gemma-4-e4b served by LM Studio
  (both Q4_K_M GGUF, loaded with a 32k context), temperature 0.
  Conditions: notools (instruction + question, one generate) vs tools
  (Inspect react agent with the state-policy-docs MCP tools search_documents,
  get_document, list_documents; submit() with one letter; attempts=1;
  message limit 30). Same instruction wording otherwise.
  Score: last standalone letter A-E in the final answer; no answer or an
  error counts wrong.
  Readouts: accuracy per model x condition; paired tools - notools per model
  with a 95% bootstrap CI (2,000 resamples, seed 84); tool use (share of
  questions with at least one tool call, calls per question).
  Note: Q4 GGUF via LM Studio differs from exp70's bf16 MLX runs, so the
  notools numbers needn't match exp70; the comparison is within each model.

Run: inspect eval experiments/exp84_mcq_tools_task.py@calfresh_mcq_e --model openai/google/gemma-4-e4b -T use_tools=true
"""
import csv
import re
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState, generate, system_message
from inspect_ai.tool import mcp_server_stdio, mcp_tools

DATA = Path.home() / "datasets/snap_scenarios/snap_scenarios.csv"
CORPUS_ROOT = Path(__file__).resolve().parents[2] / "state-policy-docs"
BASE = "You answer multiple-choice questions about CalFresh, California's SNAP program. "
NO_TOOLS = BASE + "Respond with EXACTLY one letter: A, B, C, D or E. Nothing else — no explanation, no punctuation."
WITH_TOOLS = (BASE + "You have search tools over a corpus of official California and federal SNAP policy documents "
              "(All County Letters, E&T state plans, FNS memos). If you are not certain of the rule, search the corpus "
              "(search_documents), read the most relevant document (get_document), then decide. When you have the answer, "
              "call submit() with EXACTLY one letter: A, B, C, D or E. Nothing else.")


def samples():
    out = []
    for r in csv.DictReader(open(DATA, newline="", encoding="utf-8-sig")):
        body = f"Client:\n{r['preamble_attributes'].strip()}\n\n{r['question'].strip()}\n\nAnswer with one letter."
        out.append(Sample(input=body, target=r["correct_single_answer"].strip(), id=r["question_id"]))
    return out


@scorer(metrics=[mean(), stderr()])
def letter_match():
    async def score(state: TaskState, target: Target):
        found = re.findall(r"\b([A-E])\b", (state.output.completion or "").upper())
        pred = found[-1] if found else None
        return Score(value=1.0 if pred == target.text.strip().upper() else 0.0, answer=pred,
                     explanation=f"predicted={pred} target={target.text}")
    return score


@task
def calfresh_mcq_e(use_tools: bool = False):
    if use_tools:
        server = mcp_server_stdio(name="state-policy-docs", command=str(CORPUS_ROOT / ".venv/bin/python"),
                                  args=["mcp_server/server.py"], cwd=str(CORPUS_ROOT))
        tools = mcp_tools(server, tools=["search_documents", "get_document", "list_documents"])
        solver = react(prompt=WITH_TOOLS, tools=[tools], attempts=1, submit=True)
    else:
        solver = [system_message(NO_TOOLS), generate()]
    return Task(dataset=samples(), solver=solver, scorer=letter_match(), message_limit=30,
                config=GenerateConfig(temperature=0.0))
