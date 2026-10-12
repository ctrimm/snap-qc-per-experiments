"""Exp92 — build the tool-use training questions (never the test sets).

  structured  250 table/benefit questions from the exp87 generator with a different seed (92); any whose
              question text equals an exp87 test question is dropped. (Same templates as exp87, so
              exp87 becomes an in-distribution test; Cornell and exp90 are the out-of-distribution tests.)
  open        rule questions written by Gemma 4 31B from passages sampled (seed 92) from the SNAP rule
              documents in state-policy-docs: 7 CFR 271-275, the Food and Nutrition Act (before and after
              P.L. 119-21), FNS Handbook 310, California MPP Division 63 and the CDSS letters. Each must
              return valid JSON with five distinct options and an evidence phrase found in the passage.
  guard       any question sharing a 10-word sequence with the Cornell quiz, exp87 or exp90 is dropped
              (counts printed; quiz text never written out).
Usage: python experiments/exp92_build_train.py structured | open | merge
"""
import csv
import json
import os
import random
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPD = Path(os.environ.get("EXP87_SPD", HERE.parents[1] / "state-policy-docs"))
OUT = HERE.parents[1] / "snap-qc-data" / "derived" / "exp92"
API = os.environ.get("OPENAI_BASE_URL", "http://localhost:1234/v1")
LET = "ABCDE"
GEN = """You write multiple-choice questions for training SNAP (CalFresh in California) caseworkers.

Rule passage ({citation}; {title}; in force on {as_of}):
{text}

Write ONE question that a caseworker could answer only by knowing what this passage says. Prefer applying the rule to a short case (a household, an applicant, a date) over asking for a definition. The question must be fully answerable from the passage. Give five answer options: one correct and four plausible but wrong. Do not mention the passage or its citation in the question.
Answer with JSON only: {{"stem": "...", "options": ["correct option", "wrong", "wrong", "wrong", "wrong"], "evidence": "a phrase copied exactly from the passage that supports the correct option"}}"""


def norm(t):
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(t.split()).lower()


def tokens(s):
    return re.findall(r"[a-z0-9$]+", s.lower())


def grams(s, n=10):
    w = tokens(s)
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def test_grams():
    g = set()
    for r in csv.DictReader(open(Path.home() / "datasets/snap_scenarios/snap_scenarios.csv", encoding="utf-8-sig")):
        g |= grams(r["question"])
    for f in ("exp87_heldout.jsonl", "exp90_hard.jsonl"):
        for l in open(HERE / f):
            g |= grams(json.loads(l)["question"].split("\nA. ")[0])
    return g


def structured():
    sys.argv = sys.argv[:1]
    sys.path.insert(0, str(HERE))
    import exp87_build_heldout as B
    B.rng = random.Random(92)
    items = B.tables_part(150) + B.compute_part(100)
    test_q = {json.loads(l)["question"] for l in open(HERE / "exp87_heldout.jsonl")}
    kept = [it for it in items if it["question"] not in test_q]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "train_structured.jsonl").write_text("".join(json.dumps(it) + "\n" for it in kept))
    print(f"structured: {len(items)} built, {len(items) - len(kept)} dropped as exact exp87 duplicates, {len(kept)} kept")


def chat(prompt):
    body = json.dumps({"model": "google/gemma-4-31b", "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.7, "max_tokens": 700}).encode()
    req = urllib.request.Request(f"{API}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer lm-studio"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def passage_pool():
    sys.path.insert(0, str(SPD))
    os.environ.setdefault("STATE_POLICY_CORPUS", str(SPD / "corpus"))
    from mcp_server.policy_index import get_index, parse_date
    ix = get_index()
    groups = {"cfr": r"^benefits/us/ecfr-7-cfr-27[1-5]-", "act": r"^benefits/us/(food-and-nutrition-act|usc-7-)",
              "handbook": r"^benefits/us/fns-handbook-310-", "mpp": r"^benefits/ca/mpp-63-[3-5]",
              "ca_letters": r"^benefits/ca/(cdss|calfresh)-"}
    quota = {"cfr": 170, "act": 60, "handbook": 60, "mpp": 60, "ca_letters": 50}
    rng = random.Random(92)
    pool = []
    for g, rx in groups.items():
        cand = [p for p in ix.passages if re.match(rx, ix.docs[p.doc].path) and len(p.text.split()) >= 150
                and not p.text.lstrip().startswith("|")]
        rng.shuffle(cand)
        for p in cand[:quota[g]]:
            d = ix.docs[p.doc]
            lo = max(parse_date(d.fm.get("effective_from")) or date(2024, 1, 1), date(2024, 1, 1))
            hi = min(parse_date(d.fm.get("effective_to")) or date(2026, 9, 30), date(2026, 9, 30))
            if g == "mpp":
                lo = hi = date(2025, 6, 1)  # MPP text is in force in the corpus; avoid pre-2024 dates
            if hi < lo:
                continue
            as_of = lo + timedelta(days=rng.randrange(0, (hi - lo).days + 1))
            pool.append({"group": g, "path": d.path, "title": d.title, "citation": p.citation, "as_of": as_of.isoformat(),
                         "text": p.text})
    return pool


def open_questions():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "train_open_raw.jsonl"
    done = {json.loads(l)["key"] for l in open(path)} if path.exists() else set()
    from concurrent.futures import ThreadPoolExecutor
    import threading
    lock = threading.Lock()
    todo = [(f"{p['path']}#{k}", p) for k, p in enumerate(passage_pool()) if f"{p['path']}#{k}" not in done]

    def one(kp):
        key, p = kp
        raw = chat(GEN.format(citation=p["citation"], title=p["title"], as_of=p["as_of"], text=p["text"][:6000]))
        with lock:
            fh.write(json.dumps({"key": key, **{x: p[x] for x in ("group", "path", "citation", "as_of")},
                                 "passage": p["text"], "raw": raw}) + "\n"); fh.flush()
    with open(path, "a") as fh, ThreadPoolExecutor(4) as ex:
        list(ex.map(one, todo))


def merge():
    tg = test_grams()
    rng = random.Random(92)
    items, drop = [], {"parse": 0, "options": 0, "evidence": 0, "overlap": 0}
    for l in open(OUT / "train_open_raw.jsonl"):
        r = json.loads(l)
        m = re.search(r"\{.*\}", r["raw"], re.S)
        try:
            q = json.loads(m.group(0)) if m else None
            assert q and isinstance(q.get("options"), list) and q.get("stem")
        except Exception:
            drop["parse"] += 1; continue
        opts = [str(o).strip() for o in q["options"]]
        if len(opts) != 5 or len(set(opts)) != 5:
            drop["options"] += 1; continue
        pieces = [x for x in re.split(r"\s*(?:\.\.\.|…)\s*", str(q.get("evidence") or "")) if len(x) > 10]
        if not pieces or not all(norm(x) in norm(r["passage"]) for x in pieces):
            drop["evidence"] += 1; continue
        d = date.fromisoformat(r["as_of"])
        stem = f"As of {d:%B %-d, %Y}: {q['stem'].strip()}"
        if grams(stem + " " + " ".join(opts)) & tg:
            drop["overlap"] += 1; continue
        correct = opts[0]
        rng.shuffle(opts)
        items.append({"id": f"t{len(items):04d}", "category": f"open: {r['group']}", "as_of": r["as_of"],
                      "question": stem + "\n" + "\n".join(f"{LET[i]}. {o}" for i, o in enumerate(opts)),
                      "answer": LET[opts.index(correct)], "citation": r["citation"], "gold_paths": [r["path"]]})
    structured_rows = [json.loads(l) for l in open(OUT / "train_structured.jsonl")]
    n0 = len(structured_rows)
    structured_rows = [s for s in structured_rows if not (grams(s["question"].split("\nA. ")[0]) & tg)]
    drop["overlap"] += n0 - len(structured_rows)
    for i, s in enumerate(structured_rows):
        s["id"] = f"s{i:04d}"
    allq = items + structured_rows
    random.Random(92).shuffle(allq)
    (HERE / "exp92_train.jsonl").write_text("".join(json.dumps(x) + "\n" for x in allq))
    print(f"open kept {len(items)}, structured kept {len(structured_rows)}, dropped {drop}; total {len(allq)}")


if __name__ == "__main__":
    {"structured": structured, "open": open_questions, "merge": merge}[sys.argv[1]]()
