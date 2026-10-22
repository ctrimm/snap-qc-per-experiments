"""Exp104 part A: retrieval quality, no model. Hit@1 / hit@5 (the gold document among get_passages' top results).

Question sets:
  qa     state-policy-docs/scripts/qa_pairs.jsonl, verified pairs (2,658; generated per document section on 2026-10-18)
  hard   experiments/exp94_hard.jsonl (224; gold_paths per question, as of each question's date)
Run once per corpus/config (the server reads its env at import):
  STATE_POLICY_CORPUS=... STATE_POLICY_LETTER_DECAY=0|1 python exp104_retrieval.py LABEL
Appends one JSON line per config to snap-qc-data/derived/exp104/retrieval.jsonl.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPD = Path("/Users/corytrimm/Documents/GitHub/state-policy-docs")
sys.path.insert(0, str(SPD))
from mcp_server import server  # noqa: E402

OUT = HERE.parents[1] / "snap-qc-data/derived/exp104"


def hits(passages, golds):
    paths = [p["path"] for p in passages]
    first = next((r for r, p in enumerate(paths) if any(p.startswith(g) for g in golds)), None)
    return first == 0, first is not None


def main(label):
    res = {"label": label, "corpus": os.environ.get("STATE_POLICY_CORPUS", ""), "decay": server.LETTER_DECAY}
    qa = [json.loads(l) for l in open(SPD / "scripts/qa_pairs.jsonl")]
    qa = [r for r in qa if r.get("verified")]
    by = {}
    for r in qa:
        rel = r["doc_id"].removeprefix("corpus/")
        realm, jur = rel.split("/")[:2]
        out = server.get_passages(r["question"], jurisdiction=jur, realm=realm, k=5)["passages"]
        h1, h5 = hits(out, [rel])
        key = "ca" if jur == "ca" else ("us" if jur == "us" else "other states")
        b = by.setdefault(key, [0, 0, 0]); b[0] += 1; b[1] += h1; b[2] += h5
    res["qa"] = {k: {"n": v[0], "hit1": round(100 * v[1] / v[0], 1), "hit5": round(100 * v[2] / v[0], 1)} for k, v in by.items()}
    hard = [json.loads(l) for l in open(HERE / "exp94_hard.jsonl")]
    n = h1s = h5s = 0
    for r in hard:
        stem = r["question"].split("\nA. ")[0]
        out = server.get_passages(stem, jurisdiction="ca", as_of=r["as_of"], k=5)["passages"]
        h1, h5 = hits(out, r["gold_paths"]); n += 1; h1s += h1; h5s += h5
    res["hard"] = {"n": n, "hit1": round(100 * h1s / n, 1), "hit5": round(100 * h5s / n, 1)}
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "retrieval.jsonl", "a") as f:
        f.write(json.dumps(res) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1])
