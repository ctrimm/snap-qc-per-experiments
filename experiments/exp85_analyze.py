"""Exp85 readouts: accuracy per arm, paired bootstrap CIs (2,000 resamples, seed 85), tool use, topic breakdown."""
import collections
import glob
import json
import random
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

LOGS = Path(__file__).resolve().parents[2] / "snap-qc-data/derived/exp85_logs"
ARMS = {"notools": "notools_new_dated_false", "auto_old": "auto_old_dated_false", "auto_new": "auto_new_dated_false",
        "auto_new_dated": "auto_new_dated_true", "agent_new_dated": "agent_new_dated_true", "agent_new": "agent_new_dated_false", "auto_new_hint": "auto_new_dated_false_hint"}
PAIRS = [("auto_old", "notools"), ("auto_new", "notools"), ("auto_new_dated", "notools"), ("agent_new_dated", "notools"),
         ("agent_new", "notools"), ("auto_new_dated", "auto_new"), ("agent_new_dated", "agent_new"),
         ("auto_new", "auto_old"), ("agent_new_dated", "auto_new_dated"), ("auto_new_hint", "auto_new"), ("auto_new_hint", "notools")]


def load(d):
    fs = sorted(glob.glob(str(LOGS / d / "*.eval")))
    if not fs:
        return None
    log = read_eval_log(fs[-1])
    if log.status != "success" or not log.samples:  # still running or failed
        return None
    res, tools, topic = {}, collections.Counter(), {}
    for s in log.samples:
        sc = list(s.scores.values())[0]
        res[str(s.id)] = float(sc.value) if sc.value is not None else 0.0
        topic[str(s.id)] = (s.metadata or {}).get("error_element", "") or "(none)"
        for m in s.messages:
            for tc in (getattr(m, "tool_calls", None) or []):
                tools[tc.function] += 1
    return res, tools, topic, len(log.samples)


def boot(a, b, n=2000, seed=85):
    ids = sorted(set(a) & set(b))
    d = [a[i] - b[i] for i in ids]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return 100 * sum(d) / len(d), 100 * means[int(0.025 * n)], 100 * means[int(0.975 * n)], \
        sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)


def main():
    data = {k: load(v) for k, v in ARMS.items()}
    out = {"accuracy": {}, "pairs": [], "tools": {}, "topics": {}}
    for k, v in data.items():
        if v:
            out["accuracy"][k] = round(100 * sum(v[0].values()) / len(v[0]), 1)
            if v[1]:
                out["tools"][k] = {t: round(c / v[3], 2) for t, c in v[1].items()}
    for a, b in PAIRS:
        if data.get(a) and data.get(b):
            m, lo, hi, g, l = boot(data[a][0], data[b][0])
            out["pairs"].append({"pair": f"{a} - {b}", "diff": round(m, 1), "ci": [round(lo, 1), round(hi, 1)],
                                 "gained": g, "lost": l})
    base = data.get("notools")
    if base:
        topics = collections.defaultdict(list)
        for i, t in base[2].items():
            topics[t].append(i)
        for t, ids in sorted(topics.items(), key=lambda kv: -len(kv[1])):
            if len(ids) < 15:
                continue
            out["topics"][t] = {"n": len(ids), **{k: round(100 * sum(v[0][i] for i in ids) / len(ids), 1)
                                                for k, v in data.items() if v}}
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
