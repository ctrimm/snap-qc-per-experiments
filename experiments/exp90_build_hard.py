"""Exp90 — build the harder rule-question set (exp90_hard.jsonl) from exp90_hard.json.

Each question has one or more sources (a citation resolved as of the question's date, or a corpus
document path) and one or more evidence phrases; every phrase must appear (whitespace- and
case-normalized) in at least one source's text, or the build fails. options[0] is correct; options are
shuffled with seed 90. Kinds: apply (a rule applied to a household's facts, often with arithmetic),
date (which rule applies on a date, including state implementation lag), exception (exemptions and
their limits), california (CDSS letters), combine (two rules together).
Usage: EXP87_SPD=... python experiments/exp90_build_hard.py
"""
import json
import os
import random
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPD = Path(os.environ.get("EXP87_SPD", HERE.parents[1] / "state-policy-docs"))
sys.path.insert(0, str(SPD))
from mcp_server.policy_index import get_index, resolve_citation  # noqa: E402

LET = "ABCDE"


def norm(t):
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(t.split()).lower()


def main():
    spec = json.loads((HERE / "exp90_hard.json").read_text())["questions"]
    ix = get_index()
    rng = random.Random(90)
    items, problems = [], []
    for k, q in enumerate(spec):
        d = date.fromisoformat(q["as_of"])
        texts, paths, cites = [], [], []
        for s in q["sources"]:
            if s.startswith("benefits/"):
                if s not in ix.by_path:
                    problems.append(f"{k}: no document {s}"); continue
                texts.append(ix.docs[ix.by_path[s]].body); paths.append(s); cites.append(s)
            else:
                r = resolve_citation(ix, s, d)
                if "error" in r:
                    problems.append(f"{k}: {s}: {r['error']}"); continue
                texts.append(r["text"]); paths += r["docs"]; cites.append(r["citation"])
        blob = [norm(t) for t in texts]
        for ev in q["evidence"]:
            if not any(norm(ev) in b for b in blob):
                problems.append(f"{k}: evidence not found: {ev[:70]!r}")
        if len(set(q["options"])) != 5:
            problems.append(f"{k}: needs 5 distinct options")
        opts = q["options"][:]
        correct = opts[0]
        rng.shuffle(opts)
        body = f"As of {d:%B %-d, %Y}: {q['stem']}\n" + "\n".join(f"{LET[i]}. {o}" for i, o in enumerate(opts))
        items.append({"id": f"x{k:03d}", "category": f"{q['kind']}: {q['topic']}", "question": body,
                      "answer": LET[opts.index(correct)], "as_of": q["as_of"], "citation": "; ".join(cites),
                      "gold_paths": sorted(set(paths))})
    for p in problems:
        print("PROBLEM", p)
    if problems:
        sys.exit(1)
    (HERE / "exp90_hard.jsonl").write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items))
    from collections import Counter
    print(len(items), "questions;", dict(Counter(i["category"].split(":")[0] for i in items)),
          dict(sorted(Counter(i["answer"] for i in items).items())))


if __name__ == "__main__":
    main()
