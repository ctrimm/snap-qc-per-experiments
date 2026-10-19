"""Exp98/99 readouts on the Cornell quiz; writes the tables into the chronicles and the Obsidian note.

Aggregate numbers only (no question text or answer key). Replaces the text between the AUTO-RESULTS markers in
exp98_cornell_ceiling.md, exp99_verify_plain_agent.md and the vault note, and writes exp98_99_results.json.
Usage: python experiments/exp99_analyze.py
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

VAULT = Path.home() / "Documents/Obsidian Vault/Labs/2026-10-19 snap-qc exp98-99 Cornell ceiling and the answer check.md"
rows = {r["question_id"]: r for r in csv.DictReader(open(A.CORNELL, encoding="utf-8-sig"))}


def pre_rows(logdir):
    """Score the pre-check letter (metadata pre_verify) as its own arm."""
    import glob
    from inspect_ai.log import read_eval_log
    fs = sorted(glob.glob(str(A.D / logdir / "*.eval")))
    if not fs:
        return None
    log = read_eval_log(fs[-1])
    if log.status != "success":
        return None
    return {str(s.id): {"ok": float((s.metadata or {}).get("pre_verify") == s.target)} for s in log.samples}


def sub(r, key):
    ids = [i for i in r if key(rows[i])]
    return A.acc(r, ids), len(ids)


def fmt(ci):
    return f"{ci[0]:+.1f} [{ci[1]:+.1f}, {ci[2]:+.1f}]"


def main():
    arms = {
        "exp86: 31B agent, dated 2025-06-01": "exp86_logs/agent_new_dated_true",
        "exp86: 31B no tools": "exp86_logs/notools_new_dated_false",
        "exp98-1: E4B recipe + passages, 2026-06-01": "exp98_logs/e4b_rp_2026",
        "exp98-2: 31B no tools, thinking high": "exp98_logs/31b_notools_think",
        "exp98-3: 31B agent, 2026-06-01": "exp98_logs/31b_agent_2026",
        "exp98-4: 31B agent + passages + thinking, 2026-06-01, after check": "exp98_logs/31b_combo_think_verify",
        "exp99: 31B agent, 2026-06-01, after check": "exp99_logs/31b_agent_2026_verify",
    }
    data = {k: A.load(v) for k, v in arms.items()}
    data["exp98-4: before check"] = pre_rows("exp98_logs/31b_combo_think_verify")
    data["exp99: before check"] = pre_rows("exp99_logs/31b_agent_2026_verify")
    cit = lambda r: r["error_element"].startswith("Citizenship")
    d3 = lambda r: r["difficulty_rating"].startswith("3")
    table = ["| Arm | Accuracy | Citizenship (34) | Difficulty 3 (75) |", "|---|---|---|---|"]
    res = {"arms": {}, "pairs": {}, "flips": {}}
    for k, r in data.items():
        if not r:
            continue
        res["arms"][k] = {"accuracy": A.acc(r), "citizenship": sub(r, cit)[0], "difficulty3": sub(r, d3)[0], "n": len(r)}
        table.append(f"| {k} | {A.acc(r)}% | {sub(r, cit)[0]}% | {sub(r, d3)[0]}% |")
    pairs = [("exp99: 31B agent, 2026-06-01, after check", "exp99: before check"),
             ("exp99: 31B agent, 2026-06-01, after check", "exp98-3: 31B agent, 2026-06-01"),
             ("exp99: 31B agent, 2026-06-01, after check", "exp86: 31B agent, dated 2025-06-01"),
             ("exp98-4: 31B agent + passages + thinking, 2026-06-01, after check", "exp98-4: before check"),
             ("exp98-4: 31B agent + passages + thinking, 2026-06-01, after check", "exp98-3: 31B agent, 2026-06-01"),
             ("exp98-3: 31B agent, 2026-06-01", "exp86: 31B agent, dated 2025-06-01"),
             ("exp98-2: 31B no tools, thinking high", "exp86: 31B no tools"),
             ("exp98-1: E4B recipe + passages, 2026-06-01", None)]
    ptable = ["| Paired contrast (95% CI, 2,000 resamples) | Difference |", "|---|---|"]
    for a, b in pairs:
        if b is None:
            b, bl = "e4b95", A.load("exp95_logs/e4b_rp_cornell")
            data[b] = bl; label = f"{a} − exp95 (2025-06-01)"
        else:
            label = f"{a} − {b}"
        if data.get(a) and data.get(b):
            ids = sorted(set(data[a]) & set(data[b]))
            ci = A.boot(data[a], data[b], ids, 99)
            res["pairs"][label] = ci
            ptable.append(f"| {label} | {fmt(ci)} |")
    for k, pre in (("exp99", "exp99: before check"), ("exp98-4", "exp98-4: before check")):
        fin = data.get(next(x for x in arms if x.startswith(k) and "after check" in x))
        if fin and data.get(pre):
            w2r = sum(1 for i in fin if fin[i]["ok"] > data[pre][i]["ok"]); r2w = sum(1 for i in fin if fin[i]["ok"] < data[pre][i]["ok"])
            res["flips"][k] = {"wrong_to_right": w2r, "right_to_wrong": r2w}
    flips = "\n".join(f"- **{k}:** the check changed {v['wrong_to_right']} wrong answers to right and {v['right_to_wrong']} right answers to wrong." for k, v in res["flips"].items())
    best = max(res["arms"].items(), key=lambda kv: kv[1]["accuracy"])
    block = (f"Scored {datetime.now():%Y-%m-%d %H:%M} by `exp99_analyze.py` (aggregate only). Reference: GPT-6 Astra, untuned baseline, 92.2% (Nava PBC).\n\n"
             + "\n".join(table) + "\n\n" + "\n".join(ptable) + "\n\n" + flips +
             f"\n\nBest arm: **{best[0]}, {best[1]['accuracy']}%**.\n")
    (HERE / "exp98_99_results.json").write_text(json.dumps(res, indent=1))
    for p in (HERE / "exp98_cornell_ceiling.md", HERE / "exp99_verify_plain_agent.md", VAULT):
        if not p.exists():
            continue
        s = p.read_text()
        new = re.sub(r"<!-- AUTO-RESULTS:START -->.*?<!-- AUTO-RESULTS:END -->",
                     "<!-- AUTO-RESULTS:START -->\n" + block + "<!-- AUTO-RESULTS:END -->", s, flags=re.S)
        if new == s and "AUTO-RESULTS" not in s:
            new = s.rstrip() + "\n\n<!-- AUTO-RESULTS:START -->\n" + block + "<!-- AUTO-RESULTS:END -->\n"
        p.write_text(new)
    print(block)


if __name__ == "__main__":
    main()
