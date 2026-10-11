"""Audit: does any file under the given roots contain text from the CalFresh MCQ (cornellbgl/SNAP_scenarios)?

Every question's text is split into 10-word sequences; sequences shared by more than 3 questions
(boilerplate such as "[Select one correct answer.]") are dropped, leaving ~34,700 probes. Each data,
code and notes file is scanned line by line. Prints only file paths and counts, never quiz text.
Positive control (2026-10-11): finds all 500 questions in a copy of the CSV and 20 questions embedded
in a fake training jsonl.

Usage: python experiments/audit_mcq_contamination.py ROOT [ROOT ...]
"""
import csv, re, os, sys, collections, json
from pathlib import Path
Q = list(csv.DictReader(open(Path.home()/"datasets/snap_scenarios/snap_scenarios.csv", encoding="utf-8-sig")))
tok = lambda s: re.findall(r"[a-z0-9$]+", s.lower())
N = 10
owner = collections.defaultdict(set)
for r in Q:
    w = tok(r["question"])
    for i in range(len(w) - N + 1):
        owner[" ".join(w[i:i+N])].add(r["question_id"])
probes = {g: ids for g, ids in owner.items() if len(ids) <= 3}  # drop boilerplate shared by many questions
print("questions", len(Q), "probe 10-grams", len(probes), file=sys.stderr)
roots = [Path(p).expanduser() for p in sys.argv[1:]]
skip = re.compile(r"/(\.git|\.venv|node_modules|exp84_logs|exp85_logs|exp70_logs)/|snap_scenarios")
hits = collections.defaultdict(lambda: collections.Counter())
scanned = big = 0
for root in roots:
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", ".venv", "node_modules", "__pycache__")]
        for f in fn:
            p = os.path.join(dp, f)
            if skip.search(p) or not f.endswith((".jsonl", ".json", ".csv", ".txt", ".md", ".py", ".tsv")):
                continue
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if sz > 3_000_000_000:
                big += 1; print("SKIPPED (size)", p, sz, file=sys.stderr); continue
            scanned += 1
            with open(p, errors="ignore") as fh:
                for line in fh:
                    if len(line) < 60:
                        continue
                    w = tok(line)
                    for i in range(len(w) - N + 1):
                        g = " ".join(w[i:i+N])
                        if g in probes:
                            for q in probes[g]:
                                hits[p][q] += 1
print(json.dumps({"files_scanned": scanned, "skipped_big": big,
                  "files_with_hits": {p: {"questions": len(c), "matches": sum(c.values())} for p, c in hits.items()}}, indent=1))
