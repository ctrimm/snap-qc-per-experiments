"""Exp94 — enlarge the exp90 hard set: exp94_more.json (new questions) + exp90_hard.json -> exp94_hard.jsonl.

New questions follow exp90's format and checks exactly (see exp90_build_hard.py): every evidence phrase must
appear (whitespace-, quote- and case-normalized) in a source's text as of the question's date, five distinct
options, options[0] correct, shuffled with seed 94. The 75 exp90 questions are carried over unchanged (same ids,
same option order); new ids are y000... Also refuses a new stem when more than half of its 12-word
sequences appear in one exp90 stem or one other new stem on the same date (near-duplicates; deliberate date
pairs differ in as_of; shared template phrases such as "Under the Act as in force on that date" are allowed).
Usage: EXP87_SPD=... python experiments/exp94_build_more.py [--check FILE ...]  (--check validates draft batches only)
"""
import json
import random
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from exp90_build_hard import SPD, LET, norm  # noqa: E402,F401
from mcp_server.policy_index import get_index, resolve_citation  # noqa: E402


def grams(s, n=12):
    w = re.findall(r"[a-z0-9$]+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def check(spec, ix, base_stems):
    problems = []
    seen = {g: ("exp90", None) for s in base_stems for g in grams(s)}
    for k, q in enumerate(spec):
        tag = f"{k} ({q.get('topic')})"
        d = date.fromisoformat(q["as_of"])
        texts = []
        for s in q["sources"]:
            if s.startswith("benefits/"):
                if s not in ix.by_path:
                    problems.append(f"{tag}: no document {s}"); continue
                texts.append(ix.docs[ix.by_path[s]].body)
            else:
                r = resolve_citation(ix, s, d)
                if "error" in r:
                    problems.append(f"{tag}: {s}: {r['error']}"); continue
                texts.append(r["text"])
        blob = [norm(t) for t in texts]
        for ev in q["evidence"]:
            if not any(norm(ev) in b for b in blob):
                problems.append(f"{tag}: evidence not found: {ev[:80]!r}")
        if len(set(q["options"])) != 5:
            problems.append(f"{tag}: needs 5 distinct options")
        gs = grams(q["stem"])
        hits = Counter(seen[g][0] for g in gs if g in seen and seen[g][1] in (None, q["as_of"]))
        if hits and max(hits.values()) > len(gs) / 2:
            problems.append(f"{tag}: near-duplicate stem of {hits.most_common(1)[0][0]}")
        for g in gs:
            seen.setdefault(g, (k, q["as_of"]))
    return problems


def main():
    ix = get_index()
    base = json.loads((HERE / "exp90_hard.json").read_text())["questions"]
    if "--check" in sys.argv:
        spec = [q for f in sys.argv[sys.argv.index("--check") + 1:] for q in json.load(open(f))]
    else:
        spec = json.loads((HERE / "exp94_more.json").read_text())["questions"]
    problems = check(spec, ix, [q["stem"] for q in base])
    for p in problems:
        print("PROBLEM", p)
    print(len(spec), "new questions;", dict(Counter(q["kind"] for q in spec)))
    if problems:
        sys.exit(1)
    if "--check" in sys.argv:
        return
    old = [json.loads(l) for l in open(HERE / "exp90_hard.jsonl")]
    rng = random.Random(94)
    items = []
    for k, q in enumerate(spec):
        d = date.fromisoformat(q["as_of"])
        opts = q["options"][:]
        correct = opts[0]
        rng.shuffle(opts)
        paths, cites = [], []
        for s in q["sources"]:
            if s.startswith("benefits/"):
                paths.append(s); cites.append(s)
            else:
                r = resolve_citation(ix, s, d)
                paths += r["docs"]; cites.append(r["citation"])
        body = f"As of {d:%B %-d, %Y}: {q['stem']}\n" + "\n".join(f"{LET[i]}. {o}" for i, o in enumerate(opts))
        items.append({"id": f"y{k:03d}", "category": f"{q['kind']}: {q['topic']}", "question": body,
                      "answer": LET[opts.index(correct)], "as_of": q["as_of"], "citation": "; ".join(cites),
                      "gold_paths": sorted(set(paths)), "set": "exp94"})
    for o in old:
        o["set"] = "exp90"
    allq = old + items
    (HERE / "exp94_hard.jsonl").write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in allq))
    print(len(allq), "questions total;", dict(Counter(i["category"].split(":")[0] for i in allq)),
          "new answers", dict(sorted(Counter(i["answer"] for i in items).items())))


if __name__ == "__main__":
    main()
