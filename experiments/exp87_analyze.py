"""Exp87 readouts: accuracy by arm and part, paired bootstrap CIs (seed 87), retrieval hit rate, agent tool use."""
import collections
import glob
import json
import random
from pathlib import Path

from inspect_ai.log import read_eval_log

LOGS = Path(__file__).resolve().parents[2] / "snap-qc-data/derived/exp87_logs"
ARMS = ["e4b_notools", "e4b_auto_undated", "e4b_auto_filter", "e4b_auto_label", "e4b_agent", "31b_notools", "31b_agent"]
PAIRS = [("e4b_auto_undated", "e4b_notools"), ("e4b_auto_filter", "e4b_notools"), ("e4b_auto_label", "e4b_notools"),
         ("e4b_agent", "e4b_notools"), ("e4b_auto_filter", "e4b_auto_undated"), ("e4b_auto_label", "e4b_auto_filter"),
         ("31b_agent", "31b_notools"), ("31b_notools", "e4b_notools")]


def load(arm):
    fs = sorted(glob.glob(str(LOGS / arm / "*.eval")))
    if not fs:
        return None
    log = read_eval_log(fs[-1])
    if log.status != "success" or not log.samples:
        return None
    rows = {}
    for s in log.samples:
        sc = list(s.scores.values())[0]
        calls = collections.Counter(); as_of_passed = 0; ncalls = 0
        for m in s.messages:
            for tc in (getattr(m, "tool_calls", None) or []):
                calls[tc.function] += 1; ncalls += 1
                as_of_passed += int(bool((tc.arguments or {}).get("as_of")))
        md = s.metadata or {}
        rows[str(s.id)] = {"ok": float(sc.value or 0), "part": md.get("category", "").split(":")[0],
                           "hit": bool(set(md.get("retrieved", [])) & set(md.get("gold_paths", []))) if md.get("retrieved") else None,
                           "calls": calls, "ncalls": ncalls, "as_of_passed": as_of_passed}
    return rows


def boot(a, b, ids, n=2000, seed=87):
    d = [a[i]["ok"] - b[i]["ok"] for i in ids]
    rng = random.Random(seed)
    ms = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return [round(100 * sum(d) / len(d), 1), round(100 * ms[50], 1), round(100 * ms[1949], 1)]


def main():
    data = {a: load(a) for a in ARMS}
    out = {"accuracy": {}, "by_part": {}, "retrieval_hit": {}, "tools": {}, "pairs": []}
    for a, r in data.items():
        if not r:
            continue
        out["accuracy"][a] = round(100 * sum(x["ok"] for x in r.values()) / len(r), 1)
        parts = collections.defaultdict(list)
        for x in r.values():
            parts[x["part"]].append(x["ok"])
        out["by_part"][a] = {p: [round(100 * sum(v) / len(v), 1), len(v)] for p, v in sorted(parts.items())}
        hits = [x["hit"] for x in r.values() if x["hit"] is not None]
        if hits:
            out["retrieval_hit"][a] = round(100 * sum(hits) / len(hits), 1)
        if any(x["ncalls"] for x in r.values()):
            tot = collections.Counter()
            for x in r.values():
                tot.update(x["calls"])
            n = sum(x["ncalls"] for x in r.values())
            out["tools"][a] = {"calls_per_q": round(n / len(r), 2), **{k: round(v / len(r), 2) for k, v in tot.items()},
                               "share_of_calls_with_as_of": round(sum(x["as_of_passed"] for x in r.values()) / max(1, n), 2)}
    for a, b in PAIRS:
        if data.get(a) and data.get(b):
            ids = sorted(set(data[a]) & set(data[b]))
            row = {"pair": f"{a} - {b}", "all": boot(data[a], data[b], ids)}
            for part in ("table", "compute", "rule"):
                pid = [i for i in ids if data[a][i]["part"] == part]
                if pid:
                    row[part] = boot(data[a], data[b], pid)
            out["pairs"].append(row)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
