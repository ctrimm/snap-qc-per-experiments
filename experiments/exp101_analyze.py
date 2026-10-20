"""Exp101 readouts; writes the tables into exp101_date_in_prompt.md and the vault note (aggregate only).
Usage: python experiments/exp101_analyze.py
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

VAULT = Path.home() / "Documents/Obsidian Vault/Labs/2026-10-20 snap-qc exp101 telling the model the date.md"
SIX = ["35", "343", "407", "413", "437", "442"]  # the refugee/asylee questions keyed to post-H.R. 1 rules (exp98 audit)


def main():
    arms = {"citizenship 34: baseline (same day)": "exp101_logs/cit_baseline",
            "citizenship 34: date in prompt": "exp101_logs/cit_date",
            "citizenship 34: date + notes + precedence": "exp101_logs/cit_date_notes",
            "500: combined + date, after check": "exp101_logs/full_combo_date",
            "exp98-4: combined, after check": "exp98_logs/31b_combo_think_verify",
            "exp98-3: 31B agent 2026": "exp98_logs/31b_agent_2026",
            "exp100: notes + precedence, after check": "exp100_logs/full_notes_verify"}
    data = {k: A.load(v) for k, v in arms.items()}
    data["500: combined + date, before check"] = pre_rows("exp101_logs/full_combo_date")
    data["exp100: notes + precedence, before check"] = pre_rows("exp100_logs/full_notes_verify")
    t = ["| Arm | n | Accuracy | Refugee/asylee (6) | Errored |", "|---|---|---|---|---|"]
    res = {"arms": {}, "pairs": {}}
    for k, r in data.items():
        if r:
            six = int(sum(r[i]["ok"] for i in SIX if i in r))
            err = sum(1 for x in r.values() if x.get("errored"))
            res["arms"][k] = {"n": len(r), "accuracy": A.acc(r), "six": six, "errored": err}
            t.append(f"| {k} | {len(r)} | {A.acc(r)}% | {six} of 6 | {err} |")
    p = ["| Paired contrast (95% CI) | Difference |", "|---|---|"]
    for a, b in [("citizenship 34: date in prompt", "citizenship 34: baseline (same day)"),
                 ("citizenship 34: date + notes + precedence", "citizenship 34: baseline (same day)"),
                 ("500: combined + date, after check", "exp98-4: combined, after check"),
                 ("500: combined + date, after check", "exp98-3: 31B agent 2026"),
                 ("500: combined + date, after check", "500: combined + date, before check")]:
        if data.get(a) and data.get(b):
            ids = sorted(set(data[a]) & set(data[b]))
            ci = A.boot(data[a], data[b], ids, 101); res["pairs"][f"{a} − {b}"] = ci
            p.append(f"| {a} − {b} (n = {len(ids)}) | {fmt(ci)} |")
    block = f"Scored {datetime.now():%Y-%m-%d %H:%M} by `exp101_analyze.py` (aggregate only).\n\n" + "\n".join(t) + "\n\n" + "\n".join(p) + "\n"
    (HERE / "exp101_results.json").write_text(json.dumps(res, indent=1))
    for f in (HERE / "exp101_date_in_prompt.md", VAULT):
        if f.exists():
            s = f.read_text()
            f.write_text(re.sub(r"<!-- AUTO-RESULTS:START -->.*?<!-- AUTO-RESULTS:END -->",
                                "<!-- AUTO-RESULTS:START -->\n" + block + "<!-- AUTO-RESULTS:END -->", s, flags=re.S))
    print(block)


if __name__ == "__main__":
    main()
