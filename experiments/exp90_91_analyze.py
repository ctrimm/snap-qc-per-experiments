"""Exp90/91 readouts: accuracy by arm and kind, paired bootstrap CIs (seed 90), agent tool use incl. as_of."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exp87_analyze as A  # noqa: E402

D = Path(__file__).resolve().parents[2] / "snap-qc-data/derived"
SETS = {
    "exp90": (D / "exp90_logs", ["e4b_notools", "e4b_auto_filter", "e4b_agent", "e4b_agent_strict", "e4b_agent_recipe",
                                 "31b_notools", "31b_agent"],
              [("e4b_auto_filter", "e4b_notools"), ("e4b_agent", "e4b_notools"), ("e4b_agent_strict", "e4b_agent"),
               ("e4b_agent_recipe", "e4b_agent"), ("e4b_agent_recipe", "31b_agent"), ("31b_agent", "31b_notools")]),
    "exp91_exp87set": (D / "exp91_logs", ["e4b_exp87set_agent", "e4b_exp87set_agent_strict", "e4b_exp87set_agent_recipe"],
                       [("e4b_exp87set_agent_strict", "e4b_exp87set_agent"), ("e4b_exp87set_agent_recipe", "e4b_exp87set_agent")]),
}


def main():
    out = {}
    for name, (logs, arms, pairs) in SETS.items():
        A.LOGS = logs
        data = {a: A.load(a) for a in arms}
        r = {"accuracy": {}, "by_kind": {}, "tools": {}, "pairs": []}
        for a, rows in data.items():
            if not rows:
                continue
            r["accuracy"][a] = round(100 * sum(x["ok"] for x in rows.values()) / len(rows), 1)
            kinds = {}
            for x in rows.values():
                kinds.setdefault(x["part"], []).append(x["ok"])
            r["by_kind"][a] = {k: [round(100 * sum(v) / len(v), 1), len(v)] for k, v in sorted(kinds.items())}
            n = sum(x["ncalls"] for x in rows.values())
            if n:
                r["tools"][a] = {"calls_per_q": round(n / len(rows), 2),
                                 "share_of_calls_with_as_of": round(sum(x["as_of_passed"] for x in rows.values()) / n, 2)}
        for a, b in pairs:
            if data.get(a) and data.get(b):
                ids = sorted(set(data[a]) & set(data[b]))
                r["pairs"].append({"pair": f"{a} - {b}", "all": A.boot(data[a], data[b], ids, seed=90)})
        out[name] = r
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
