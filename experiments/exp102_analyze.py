"""Exp102 readouts; writes the tables into exp102_combined_expanded_corpus.md and the vault note (aggregate only).
Usage: python experiments/exp102_analyze.py
"""
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402
from exp99_analyze import fmt, pre_rows  # noqa: E402

VAULT = Path.home() / "Documents/Obsidian Vault/Labs/2026-10-20 snap-qc exp102 combined setup on the expanded corpus.md"
SIX = ["35", "343", "407", "413", "437", "442"]
rows = {r["question_id"]: r for r in csv.DictReader(open(A.CORNELL, encoding="utf-8-sig"))}


def main():
    data = {"exp102-1: plain agent + date + notes + precedence": A.load("exp102_logs/full_plain_date_notes"),
            "exp102: combined, expanded corpus, after check": A.load("exp102_logs/full_combo"),
            "exp98-4: combined, after check": A.load("exp98_logs/31b_combo_think_verify"),
            "exp98-3: 31B agent 2026 (best so far)": A.load("exp98_logs/31b_agent_2026")}
    data["exp102: before check"] = pre_rows("exp102_logs/full_combo")
    data["exp98-4: before check"] = pre_rows("exp98_logs/31b_combo_think_verify")
    cit = lambda i: rows[i]["error_element"].startswith("Citizenship")
    d3 = lambda i: rows[i]["difficulty_rating"].startswith("3")
    t = ["| Arm | n | Accuracy | Citizenship | Difficulty 3 | Refugee/asylee (6) | Errored |", "|---|---|---|---|---|---|---|"]
    res = {"arms": {}, "pairs": {}}
    for k, r in data.items():
        if not r:
            continue
        c = A.acc(r, [i for i in r if cit(i)]); h = A.acc(r, [i for i in r if d3(i)])
        six = int(sum(r[i]["ok"] for i in SIX if i in r)); err = sum(1 for x in r.values() if x.get("errored"))
        res["arms"][k] = {"n": len(r), "accuracy": A.acc(r), "citizenship": c, "difficulty3": h, "six": six, "errored": err}
        t.append(f"| {k} | {len(r)} | {A.acc(r)}% | {c}% | {h}% | {six} of 6 | {err} |")
    p = ["| Paired contrast (95% CI) | Difference |", "|---|---|"]
    for a, b in [("exp102-1: plain agent + date + notes + precedence", "exp98-3: 31B agent 2026 (best so far)"),
                 ("exp102-1: plain agent + date + notes + precedence", "exp102: combined, expanded corpus, after check"),
                 ("exp102: combined, expanded corpus, after check", "exp98-4: combined, after check"),
                 ("exp102: combined, expanded corpus, after check", "exp98-3: 31B agent 2026 (best so far)"),
                 ("exp102: combined, expanded corpus, after check", "exp102: before check")]:
        if data.get(a) and data.get(b):
            ids = sorted(set(data[a]) & set(data[b]))
            ci = A.boot(data[a], data[b], ids, 102); res["pairs"][f"{a} − {b}"] = ci
            p.append(f"| {a} − {b} (n = {len(ids)}) | {fmt(ci)} |")
    block = (f"Scored {datetime.now():%Y-%m-%d %H:%M} by `exp102_analyze.py` (aggregate only). GPT-6 Astra, untuned: 92.2%.\n\n"
             + "\n".join(t) + "\n\n" + "\n".join(p) + "\n")
    (HERE / "exp102_results.json").write_text(json.dumps(res, indent=1))
    for f in (HERE / "exp102_combined_expanded_corpus.md", VAULT):
        if f.exists():
            s = f.read_text()
            f.write_text(re.sub(r"<!-- AUTO-RESULTS:START -->.*?<!-- AUTO-RESULTS:END -->",
                                "<!-- AUTO-RESULTS:START -->\n" + block + "<!-- AUTO-RESULTS:END -->", s, flags=re.S))
    print(block)


if __name__ == "__main__":
    main()
