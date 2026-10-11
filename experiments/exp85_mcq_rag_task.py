"""Exp 85 — does a fuller rulebook, or putting the rule in front of the model, help E4B on the CalFresh MCQ?

Pre-registered (this docstring, committed before the scored runs):
  Data: the same 500 Better Government Lab CalFresh questions as exp84
  (~/datasets/snap_scenarios; client attributes + question with embedded
  options; answers A-E).
  Model: google/gemma-4-e4b via LM Studio (Q4_K_M GGUF, 128k context,
  4 parallel slots), temperature 0.
  Design: same-day no-tools baseline plus a 2x2:
    corpus  = old (state-policy-docs at e20d2e0: the 507-document corpus
              exp84 used) vs new (the expanded corpus: CFR for 15 programs,
              Food and Nutrition Act, FNS Handbook 310, FY2024-27 FNS
              tables, California MPP Division 63; ~3,300 documents)
    mode    = auto (no agent: the top 5 passages from get_passages(question,
              jurisdiction="ca"), state + federal, at most 2 per document,
              are put in the prompt; one generate) vs agent (Inspect react
              agent with the new tools get_passages, lookup_rule,
              get_section, calculate_benefit; submit() one letter;
              attempts=1; message limit 30).
  The same server code serves both corpora (STATE_POLICY_CORPUS points it at
  the old snapshot), so the corpus factor varies content only. With the old
  corpus, lookup_rule/get_section find no citations and calculate_benefit
  has no tables; that is part of what the old corpus lacks.
  Retrieval query (auto): the question text including its options (no
  client attributes). Passages are current (no as_of).
  Score: last standalone letter A-E in the final answer; missing answer or
  error counts wrong.
  Readouts: accuracy per condition; paired differences with 95% bootstrap
  CIs (2,000 resamples, seed 85) for: each condition - notools; new - old
  within each mode; agent - auto within each corpus. Tool use for agent
  runs (calls per question by tool). Descriptive: accuracy by the dataset's
  error_element topic.
  Hypotheses: H1 auto/new beats notools (CI above 0). H2 new beats old in
  both modes. H3 (descriptive) agent/new vs exp84's agent with the old tools
  (68.6%) and vs notools.
  Run order: notools, auto/old, auto/new, agent/new, agent/old.

  AMENDMENT (2026-10-11, before any scored run; only 3-question smoke tests
  had run): the owner noted the question set predates H.R. 1 (P.L. 119-21,
  July 4, 2025). Only 1 of the old corpus's 326 documents was in force on
  2025-06-01 (it is almost entirely post-H.R. 1 letters), so an old-corpus
  arm with a date filter would be empty, and an agent/old arm adds little
  over exp84. Revised conditions (prompts identical within a mode):
    notools
    auto  / old / current       (what exp84's corpus offers, undated)
    auto  / new / current
    auto  / new / as_of 2025-06-01
    agent / new / as_of 2025-06-01
    agent / new / current
  as_of 2025-06-01 (pre-H.R. 1, FY2025) applies to every retrieval: the
  auto passages, and in agent runs the server's default
  (STATE_POLICY_DEFAULT_AS_OF), so the model needn't pass it. Note the new
  corpus has no pre-H.R. 1 statute text (the Act compilation is as amended
  through P.L. 119-21), so dated arms rely on the CFR (2024-06-01 versions
  where changed), FY2025 FNS tables, Handbook 310 and MPP Division 63.
  Revised hypotheses: H1 auto/new/as_of beats notools (CI above 0).
  H2 dating helps: auto/new/as_of beats auto/new/current, and agent likewise.
  H3 the rulebook helps: auto/new/current beats auto/old/current.
  H4 (descriptive) agent/new/as_of vs notools and vs exp84's agent (68.6%).
  Contrasts with paired bootstrap CIs (2,000 resamples, seed 85): each arm -
  notools, and the H2/H3 pairs.

Run: inspect eval experiments/exp85_mcq_rag_task.py@calfresh_mcq_rag --model openai/google/gemma-4-e4b -T mode=auto -T corpus=new -T dated=true
"""
import csv
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

DATA = Path.home() / "datasets/snap_scenarios/snap_scenarios.csv"
SPD = Path(__file__).resolve().parents[2] / "state-policy-docs"
CORPORA = {"new": SPD / "corpus", "old": Path(__file__).resolve().parents[2] / "snap-qc-data/derived/exp85_spd_old/corpus"}
BASE = "You answer multiple-choice questions about CalFresh, California's SNAP program. "
ONE_LETTER = "Respond with EXACTLY one letter: A, B, C, D or E. Nothing else — no explanation, no punctuation."
AUTO = (BASE + "Excerpts from official federal and California policy documents that may be relevant are included with "
        "the question. They may not all apply, and older documents can be superseded by newer ones; use them where "
        "they help. " + ONE_LETTER)
AGENT = (BASE + "You have tools over a corpus of official federal and California SNAP/CalFresh rules: get_passages "
         "(the most relevant rule passages for a question, with citations), lookup_rule (the governing rules for a "
         "topic such as 'students', 'shelter deduction' or 'ABAWD'), get_section (the text of a citation such as "
         "'7 CFR 273.5(b)' or 'MPP 63-502.3') and calculate_benefit (a SNAP eligibility and benefit computation). "
         "If you are not certain of the rule, look it up, then decide. When you have the answer, call submit() with "
         "EXACTLY one letter: A, B, C, D or E. Nothing else.")


AS_OF = "2025-06-01"


def _passages_fn(corpus: str):
    os.environ["STATE_POLICY_CORPUS"] = str(CORPORA[corpus])
    sys.path.insert(0, str(SPD))
    from mcp_server import server  # imported after the env var so it indexes the chosen corpus
    return server.get_passages


def samples(mode: str, corpus: str, dated: bool):
    rows = list(csv.DictReader(open(DATA, newline="", encoding="utf-8-sig")))
    get_passages = _passages_fn(corpus) if mode == "auto" else None
    out = []
    for r in rows:
        q = r["question"].strip()
        body = f"Client:\n{r['preamble_attributes'].strip()}\n\n{q}\n\nAnswer with one letter."
        meta = {"error_element": r.get("error_element", ""), "passages": []}
        if get_passages:
            ps = get_passages(q, jurisdiction="ca", k=5, as_of=AS_OF if dated else "")["passages"]
            meta["passages"] = [p["citation"] for p in ps]
            ctx = "\n\n".join(f"[{i + 1}] {p['citation']} ({p['document']}; in force from {p['effective_from'] or 'n/a'})\n"
                              f"{p['text']}" for i, p in enumerate(ps))
            body = f"Policy excerpts:\n\n{ctx}\n\n---\n\n{body}"
        out.append(Sample(input=body, target=r["correct_single_answer"].strip(), id=r["question_id"], metadata=meta))
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
def calfresh_mcq_rag(mode: str = "notools", corpus: str = "new", dated: bool = False):
    assert mode in ("notools", "auto", "agent") and corpus in CORPORA
    if mode == "agent":
        server = mcp_server_stdio(name="state-policy-docs", command=str(SPD / ".venv/bin/python"),
                                  args=["mcp_server/server.py"], cwd=str(SPD),
                                  env={"STATE_POLICY_CORPUS": str(CORPORA[corpus]),
                                       "STATE_POLICY_DEFAULT_AS_OF": AS_OF if dated else ""})
        tools = mcp_tools(server, tools=["get_passages", "lookup_rule", "get_section", "calculate_benefit"])
        solver = react(prompt=AGENT, tools=[tools], attempts=1, submit=True)
    else:
        solver = [system_message(AUTO if mode == "auto" else BASE + ONE_LETTER), generate()]
    return Task(dataset=samples(mode, corpus, dated), solver=solver, scorer=letter_match(), message_limit=30,
                config=GenerateConfig(temperature=0.0))
