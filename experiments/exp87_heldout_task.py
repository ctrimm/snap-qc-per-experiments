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

  AMENDMENT (2026-10-16, exp95/exp96; before those runs): arm agent_recipe_passages = agent_recipe plus the
  auto_filter passages (top 5, as_of the question's date) attached to the question as in the auto arms (exp95).
  Parameter guard=N (exp96): react on_continue hook from exp96_guard.py (budget message after N tool calls,
  loop ends after N+2) and a final no-tools answer step when submit() was never called; message limit 40
  for guarded runs so the answer step always runs. guard=0 (default) leaves every earlier arm unchanged.

Run: inspect eval experiments/exp87_heldout_task.py@heldout --model openai/google/gemma-4-e4b -T arm=auto_filter
"""
import json
import os
import re
import sys
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.agent import AgentSubmit, as_solver, react
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


RECIPE = (" Follow these steps for every question. "
          "1. If it asks what benefit a household gets, call calculate_benefit with every fact the question gives "
          "(household size, each income, rent or shelter costs, the utility allowance, medical costs, whether a member "
          "is elderly or disabled) and as_of set to the question's date. "
          "2. If it asks for a figure from the yearly tables (an allotment, a deduction, an income or asset limit), "
          "call lookup_rule with that topic and as_of; the result includes that year's table. "
          "3. Otherwise call lookup_rule with the topic and as_of, then call get_section on the citation that fits "
          "best, with the same as_of, and read it. "
          "4. Answer only from what the tools returned.")


def samples(arm: str, data: str = ""):
    rows = [json.loads(l) for l in open(HERE / data if data else DATA)]
    get_passages = None
    if arm.startswith("auto") or arm == "agent_recipe_passages":
        sys.path.insert(0, str(SPD))
        os.environ.setdefault("STATE_POLICY_CORPUS", str(SPD / "corpus"))
        from mcp_server import server
        get_passages = server.get_passages
    out = []
    for r in rows:
        body = r["question"] + "\n\nAnswer with one letter."
        meta = {"category": r["category"], "as_of": r["as_of"], "gold_paths": r["gold_paths"], "retrieved": []}
        if get_passages:
            kw = {} if arm == "auto_undated" else {"as_of": r["as_of"], "date_mode": "label" if arm == "auto_label" else "filter"}  # agent_recipe_passages: filter
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
def heldout(arm: str = "notools", data: str = "", guard: int = 0):
    """data: a question file in experiments/ (default exp87_heldout.jsonl; exp90 uses exp90_hard.jsonl, exp94 exp94_hard.jsonl).
    guard: exp96 answer guard (0 = off)."""
    assert arm in ("notools", "auto_undated", "auto_filter", "auto_label", "agent", "agent_strict", "agent_recipe",
                   "agent_recipe_passages")
    if arm.startswith("agent"):
        env = {"STATE_POLICY_CORPUS": str(SPD / "corpus")}
        if arm in ("agent_strict", "agent_recipe", "agent_recipe_passages"):  # exp91: as_of required in the tool schemas
            env["STATE_POLICY_REQUIRE_AS_OF"] = "1"
        server = mcp_server_stdio(name="state-policy-docs", command=str(SPD / ".venv/bin/python") if (SPD / ".venv").exists()
                                  else str(HERE.parents[1] / "state-policy-docs/.venv/bin/python"),
                                  args=["mcp_server/server.py"], cwd=str(SPD), env=env)
        tools = mcp_tools(server, tools=["get_passages", "lookup_rule", "get_section", "calculate_benefit"])
        prompt = AGENT.replace(" Look up the rule", RECIPE + " Look up the rule") if arm.startswith("agent_recipe") else AGENT
        if arm == "agent_recipe_passages":
            prompt = prompt.replace(" Follow these steps", " Excerpts from official policy documents in force on the question's date are included with the question; use them where they help. Follow these steps")
        if guard:
            sys.path.insert(0, str(HERE))
            from exp96_guard import force_answer, guard_continue
            solver = [as_solver(react(prompt=prompt, tools=[tools], attempts=1, submit=AgentSubmit(keep_in_messages=True),
                                        on_continue=guard_continue(guard))),
                      force_answer()]
        else:
            solver = react(prompt=prompt, tools=[tools], attempts=1, submit=True)
    else:
        solver = [system_message(AUTO if arm.startswith("auto") else BASE + ONE_LETTER), generate()]
    return Task(dataset=samples(arm, data), solver=solver, scorer=letter_match(), message_limit=40 if guard else 30,
                config=GenerateConfig(temperature=0.0))
