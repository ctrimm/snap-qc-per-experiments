"""Exp100 readouts; writes the tables into exp100_supersession_notes.md and the vault note (aggregate only).
Usage: python experiments/exp100_analyze.py
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402
from exp99_analyze import fmt, pre_rows  # noqa: E402

VAULT = Path.home() / "Documents/Obsidian Vault/Labs/2026-10-19 snap-qc exp100 supersession notes.md"


def main():
    arms = {"dev 28: baseline": "exp100_logs/dev_baseline", "dev 28: notes + precedence": "exp100_logs/dev_notes",
            "Cornell 34 citizenship: baseline": "exp100_logs/cit_baseline",
            "Cornell 34 citizenship: notes + precedence": "exp100_logs/cit_notes",
            "Cornell 500: notes + precedence, after check": "exp100_logs/full_notes_verify",
            "exp98-3: 31B agent 2026 (no notes)": "exp98_logs/31b_agent_2026",
            "exp99: 31B agent 2026, after check": "exp99_logs/31b_agent_2026_verify"}
    data = {k: A.load(v) for k, v in arms.items()}
    data["Cornell 500: notes + precedence, before check"] = pre_rows("exp100_logs/full_notes_verify")
    data["exp99: before check"] = pre_rows("exp99_logs/31b_agent_2026_verify")
    t = ["| Arm | n | Accuracy |", "|---|---|---|"]
    res = {"arms": {}, "pairs": {}}
    for k, r in data.items():
        if r:
            res["arms"][k] = {"n": len(r), "accuracy": A.acc(r)}
            t.append(f"| {k} | {len(r)} | {A.acc(r)}% |")
    cit = None
    if data.get("exp98-3: 31B agent 2026 (no notes)") and data.get("Cornell 34 citizenship: notes + precedence"):
        ids = set(data["Cornell 34 citizenship: notes + precedence"])
        cit = A.acc(data["exp98-3: 31B agent 2026 (no notes)"], [i for i in data["exp98-3: 31B agent 2026 (no notes)"] if i in ids])
    p = ["| Paired contrast (95% CI) | Difference |", "|---|---|"]
    for a, b in [("dev 28: notes + precedence", "dev 28: baseline"),
                 ("Cornell 34 citizenship: notes + precedence", "Cornell 34 citizenship: baseline"),
                 ("Cornell 500: notes + precedence, before check", "exp98-3: 31B agent 2026 (no notes)"),
                 ("Cornell 500: notes + precedence, after check", "exp99: 31B agent 2026, after check"),
                 ("Cornell 500: notes + precedence, after check", "Cornell 500: notes + precedence, before check")]:
        if data.get(a) and data.get(b):
            ids = sorted(set(data[a]) & set(data[b]))
            ci = A.boot(data[a], data[b], ids, 100); res["pairs"][f"{a} − {b}"] = ci
            p.append(f"| {a} − {b} (n = {len(ids)}) | {fmt(ci)} |")
    block = (f"Scored {datetime.now():%Y-%m-%d %H:%M} by `exp100_analyze.py` (aggregate only).\n\n" + "\n".join(t) + "\n\n" + "\n".join(p)
             + (f"\n\nFor reference, exp98 arm 3 on the same 34 citizenship questions: {cit}%.\n" if cit is not None else "\n"))
    (HERE / "exp100_results.json").write_text(json.dumps(res, indent=1))
    for f in (HERE / "exp100_supersession_notes.md", VAULT):
        if f.exists():
            s = f.read_text()
            f.write_text(re.sub(r"<!-- AUTO-RESULTS:START -->.*?<!-- AUTO-RESULTS:END -->",
                                "<!-- AUTO-RESULTS:START -->\n" + block + "<!-- AUTO-RESULTS:END -->", s, flags=re.S))
    print(block)


if __name__ == "__main__":
    main()
