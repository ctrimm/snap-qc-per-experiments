"""Exp 87 — the rule tools on our own held-out SNAP question set (dated, citation-labeled).

Pre-registered (this docstring, committed before the scored runs):
  Data: experiments/exp87_heldout.jsonl, built by exp87_build_heldout.py from the state-policy-docs
  corpus only (FNS table lookups for dates in FY2024-27, benefit computations scored by the calculator,
  and hand-written rule questions each tied to a citation and a date, with pre/post H.R. 1 pairs).
  Every question starts "As of <date>". Answers A-E.
  Model: google/gemma-4-e4b via LM Studio (Q4_K_M, 128k context, 4 slots), temperature 0; then
  google/gemma-4-31b for the no-tools and agent arms.
  Arms (E4B):
    notools
    auto_undated   top 5 get_passages(question, jurisdiction="ca"), no date
    auto_filter    same, as_of = the question's date, date_mode=filter
    auto_label     same, as_of = the question's date, date_mode=label
    agent          react agent with get_passages, lookup_rule, get_section, calculate_benefit; the
                   prompt says to pass the question's date as as_of; attempts=1, message limit 30
  Arms (31B): notools, agent.
  Corpus: state-policy-docs with every CFR version in force since 2024-01-01 (ecfr-markdown --since)
  and the date-windows metadata.
  Readouts: accuracy overall and by part (table / compute / rule); paired differences vs notools and
  filter vs undated vs label with 95% bootstrap CIs (2,000 resamples, seed 87); retrieval hit rate
  (a gold document among the attached passages) per auto arm; agent tool use, including how often it
  passed as_of and called calculate_benefit.
  Hypotheses: H1 dated retrieval (filter or label) beats undated on table questions, where the right
  fiscal year decides the answer. H2 the agent with calculate_benefit beats notools on compute
  questions. H3 auto arms beat notools overall.
  This set is ours: after this first run it may be used to tune retrieval (unlike the Cornell quiz).

Run: inspect eval experiments/exp87_heldout_task.py@heldout --model openai/google/gemma-4-e4b -T arm=auto_filter
"""
import json
import os
import re
import sys
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState, generate, system_message
from inspect_ai.tool import mcp_server_stdio, mcp_tools

HERE = Path(__file__).resolve().parent
DATA = HERE / "exp87_heldout.jsonl"
SPD = Path(os.environ.get("EXP87_SPD", HERE.parents[1] / "state-policy-docs"))
BASE = "You answer multiple-choice questions about SNAP (CalFresh in California) rules. Each question gives a date; answer under the rules in force on that date. "
ONE_LETTER = "Respond with EXACTLY one letter: A, B, C, D or E. Nothing else — no explanation, no punctuation."
AUTO = BASE + "Excerpts from official policy documents that may be relevant are included, each with its in-force date or status; use them where they help. " + ONE_LETTER
AGENT = (BASE + "You have tools over official federal and California SNAP rules: get_passages (rule passages with citations), "
         "lookup_rule (the governing rules for a topic), get_section (the text of a citation such as '7 CFR 273.9(d)(6)') and "
         "calculate_benefit (the federal SNAP benefit computation, with the year's official tables). Pass the question's date as "
         "as_of (YYYY-MM-DD) to every tool. Look up the rule or compute the amount if you are not certain, then call submit() "
         "with EXACTLY one letter: A, B, C, D or E. Nothing else.")


def samples(arm: str):
    rows = [json.loads(l) for l in open(DATA)]
    get_passages = None
    if arm.startswith("auto"):
        sys.path.insert(0, str(SPD))
        os.environ.setdefault("STATE_POLICY_CORPUS", str(SPD / "corpus"))
        from mcp_server import server
        get_passages = server.get_passages
    out = []
    for r in rows:
        body = r["question"] + "\n\nAnswer with one letter."
        meta = {"category": r["category"], "as_of": r["as_of"], "gold_paths": r["gold_paths"], "retrieved": []}
        if get_passages:
            kw = {} if arm == "auto_undated" else {"as_of": r["as_of"], "date_mode": "label" if arm == "auto_label" else "filter"}
            stem = r["question"].split("\nA. ")[0]
            ps = get_passages(stem, jurisdiction="ca", k=5, **kw)["passages"]
            meta["retrieved"] = [p["path"] for p in ps]
            ctx = "\n\n".join(f"[{i + 1}] {p['citation']} ({p['document']}; {p.get('date_status', '')} {p.get('date_note', '') or p['effective_from']})\n{p['text']}"
                              for i, p in enumerate(ps))
            body = f"Policy excerpts:\n\n{ctx}\n\n---\n\n{body}"
        out.append(Sample(input=body, target=r["answer"], id=r["id"], metadata=meta))
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
def heldout(arm: str = "notools"):
    assert arm in ("notools", "auto_undated", "auto_filter", "auto_label", "agent")
    if arm == "agent":
        server = mcp_server_stdio(name="state-policy-docs", command=str(SPD / ".venv/bin/python") if (SPD / ".venv").exists()
                                  else str(HERE.parents[1] / "state-policy-docs/.venv/bin/python"),
                                  args=["mcp_server/server.py"], cwd=str(SPD), env={"STATE_POLICY_CORPUS": str(SPD / "corpus")})
        tools = mcp_tools(server, tools=["get_passages", "lookup_rule", "get_section", "calculate_benefit"])
        solver = react(prompt=AGENT, tools=[tools], attempts=1, submit=True)
    else:
        solver = [system_message(AUTO if arm.startswith("auto") else BASE + ONE_LETTER), generate()]
    return Task(dataset=samples(arm), solver=solver, scorer=letter_match(), message_limit=30,
                config=GenerateConfig(temperature=0.0))
