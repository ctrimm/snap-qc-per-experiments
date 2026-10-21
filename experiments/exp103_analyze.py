"""Exp103 screening readouts; writes the tables into exp103_screen_corpus.md and the vault note (aggregate only)."""
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402
from exp99_analyze import fmt  # noqa: E402

VAULT = Path.home() / "Documents/Obsidian Vault/Labs/2026-10-21 snap-qc exp103 screening the expanded corpus.md"
SIX = ["35", "343", "407", "413", "437", "442"]


def main():
    g = json.loads((A.D / "exp103_screen/groups.json").read_text())
    hard, ctrl = g["hard"], g["controls"]
    rows = {r["question_id"]: r for r in csv.DictReader(open(A.CORNELL, encoding="utf-8-sig"))}
    cit = [i for i in hard if rows[i]["error_element"].startswith("Citizenship")]
    arms = {"A0: new corpus": "exp103_logs/A0", "A1: + letter weighting": "exp103_logs/A1",
            "A2: + weighting + date + notes + precedence": "exp103_logs/A2",
            "ref exp98-3: old corpus, plain": "exp98_logs/31b_agent_2026",
            "ref exp102-1: new corpus + date + notes, no weighting": "exp102_logs/full_plain_date_notes"}
    data = {k: A.load(v) for k, v in arms.items()}
    allids = hard + ctrl
    t = ["| Arm | All (%d) | Hard (%d) | Controls (%d) | Citizenship (%d) | Refugee/asylee (6) |" % (len(allids), len(hard), len(ctrl), len(cit)),
         "|---|---|---|---|---|---|"]
    res = {"arms": {}, "pairs": {}}
    for k, r in data.items():
        if not r:
            continue
        ids = [i for i in allids if i in r]
        lost = sum(1 for i in ctrl if i in r and not r[i]["ok"])
        res["arms"][k] = {"all": A.acc(r, ids), "hard": A.acc(r, [i for i in hard if i in r]),
                          "controls_lost": lost, "citizenship": A.acc(r, [i for i in cit if i in r]),
                          "six": int(sum(r[i]["ok"] for i in SIX if i in r))}
        a = res["arms"][k]
        t.append(f"| {k} | {a['all']}% | {a['hard']}% | {len(ctrl) - lost} of {len(ctrl)} | {a['citizenship']}% | {a['six']} of 6 |")
    p = ["| Effect (95% CI) | Difference |", "|---|---|"]
    for lab, a, b in [("letter weighting: A1 − A0", "A1: + letter weighting", "A0: new corpus"),
                      ("prompt given weighting: A2 − A1", "A2: + weighting + date + notes + precedence", "A1: + letter weighting"),
                      ("corpus: A0 − exp98-3", "A0: new corpus", "ref exp98-3: old corpus, plain"),
                      ("A2 − exp98-3", "A2: + weighting + date + notes + precedence", "ref exp98-3: old corpus, plain")]:
        if data.get(a) and data.get(b):
            ids = [i for i in allids if i in data[a] and i in data[b]]
            ci = A.boot(data[a], data[b], ids, 103); res["pairs"][lab] = ci
            p.append(f"| {lab} | {fmt(ci)} |")
    ref = res["arms"].get("ref exp98-3: old corpus, plain", {}).get("all")
    cands = [(v["all"], k) for k, v in res["arms"].items() if k.startswith("A") and ref is not None
             and v["all"] - ref >= 3 and v["controls_lost"] <= 2]
    decision = (f"**Decision rule:** {max(cands)[1]} qualifies for a full 500-question run." if cands
                else "**Decision rule:** no arm qualifies (needs +3 over exp98-3 on this set and at most 2 controls lost).")
    block = (f"Scored {datetime.now():%Y-%m-%d %H:%M} by `exp103_analyze.py` (aggregate only; screening set chosen from test results).\n\n"
             + "\n".join(t) + "\n\n" + "\n".join(p) + "\n\n" + decision + "\n")
    (HERE / "exp103_results.json").write_text(json.dumps(res, indent=1))
    for f in (HERE / "exp103_screen_corpus.md", VAULT):
        if f.exists():
            s = f.read_text()
            f.write_text(re.sub(r"<!-- AUTO-RESULTS:START -->.*?<!-- AUTO-RESULTS:END -->",
                                "<!-- AUTO-RESULTS:START -->\n" + block + "<!-- AUTO-RESULTS:END -->", s, flags=re.S))
    print(block)


if __name__ == "__main__":
    main()
