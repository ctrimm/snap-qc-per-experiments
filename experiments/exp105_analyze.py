"""Exp105 readouts (aggregate only); writes the AUTO-RESULTS blocks of exp105_topic_router.md and the vault note."""
import glob
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from inspect_ai.log import read_eval_log

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402
from exp99_analyze import fmt  # noqa: E402

VAULT = Path.home() / "Documents/Obsidian Vault/Labs/2026-10-22 snap-qc exp105 topic router.md"


def answers(d):
    fs = sorted(glob.glob(str(A.D / d / "*.eval")))
    if not fs:
        return None, None
    l = read_eval_log(fs[-1])
    out = {str(s.id): (list(s.scores.values())[0].answer if s.scores else None) for s in l.samples}
    mins = (datetime.fromisoformat(l.stats.completed_at) - datetime.fromisoformat(l.stats.started_at)).total_seconds() / 60 \
        if l.stats.completed_at else None
    return out, mins


def main():
    import csv
    rows = {r["question_id"]: r for r in csv.DictReader(open(A.CORNELL, encoding="utf-8-sig"))}
    key = {i: rows[i]["correct_single_answer"].strip() for i in rows}
    ids = sorted(rows, key=int)
    cit = [i for i in ids if rows[i]["error_element"].startswith("Citizenship")]
    out = []
    cfg = A.D / "exp105/config.txt"
    pa, pc = A.load("exp105_logs/p0_A") if glob.glob(str(A.D / "exp105_logs/p0_A/*.eval")) else None, \
        A.load("exp105_logs/p0_C") if glob.glob(str(A.D / "exp105_logs/p0_C/*.eval")) else None
    if pa or pc:
        out += ["### Part 0: our 121 California hard-set questions (31B agent)", "", "| Arm | Accuracy |", "|---|---|"]
        if pa:
            out.append(f"| P0-A: current corpus defaults | {A.acc(pa)}% |")
        if pc:
            out.append(f"| P0-C: cite-only letters + curated guidance | {A.acc(pc)}% |")
        if pa and pc:
            common = [i for i in pa if i in pc]
            out.append(f"| C − A (95% CI) | {fmt(A.boot(pc, pa, common, 105))} |")
        if cfg.exists():
            out += ["", f"Part-1 config: `{cfg.read_text().strip()}`"]
    P, pm = answers("exp105_logs/plain")
    if P and len(P) == 500:
        ok = lambda ans, xs=ids: round(100 * sum(ans.get(i) == key[i] for i in xs) / len(xs), 1)  # noqa: E731
        nf = A.D / "exp105/noncit_ids.txt"
        nc = [x for x in nf.read_text().split()] if nf.exists() else []
        Dn, dm = answers("exp105_logs/datenotes_noncit")
        R = {i: (Dn[i] if Dn and i in Dn and i in set(nc) else P[i]) for i in ids}
        row = lambda ans: {i: {"ok": float(ans.get(i) == key[i])} for i in ids}  # noqa: E731
        ref = {"exp98-3 (old corpus, plain)": "exp98_logs/31b_agent_2026", "exp102-1 (new corpus, date + notes)": "exp102_logs/full_plain_date_notes"}
        refs = {k: answers(v)[0] for k, v in ref.items()}
        out += ["", "### Part 1: Cornell (500)", "", "| Setup | Accuracy | Citizenship (%d) |" % len(cit), "|---|---|---|",
                f"| Plain (this run) | {ok(P)}% | {ok(P, cit)}% |"]
        if Dn:
            out.append(f"| **Router** (E4B `noncitizens` → date + notes; {len(nc)} questions, {sum(R[i] != P[i] for i in ids)} answers changed) | **{ok(R)}%** | {ok(R, cit)}% |")
        for k, v in refs.items():
            out.append(f"| ref {k} | {ok(v)}% | {ok(v, cit)}% |")
        out += ["", "| Comparison (paired) | Difference, points (95% CI) |", "|---|---|"]
        if Dn:
            out.append(f"| **H1:** router − plain (this run) | {fmt(A.boot(row(R), row(P), ids, 105))} |")
            out.append(f"| **H2:** router − exp98-3 | {fmt(A.boot(row(R), row(refs['exp98-3 (old corpus, plain)']), ids, 105))} |")
        out.append(f"| plain (this run) − exp98-3 | {fmt(A.boot(row(P), row(refs['exp98-3 (old corpus, plain)']), ids, 105))} |")
        out += ["", f"Minutes: plain {round(pm) if pm else '?'} ({round(pm / 500, 2) if pm else '?'} per question)"
                + (f"; date + notes on the routed questions {round(dm)}" if Dn and dm else "") + "."]
    block = f"Scored {datetime.now():%Y-%m-%d %H:%M} by `exp105_analyze.py`.\n\n" + "\n".join(out) + "\n"
    for f in (HERE / "exp105_topic_router.md", VAULT):
        if f.exists():
            s = f.read_text()
            f.write_text(re.sub(r"<!-- AUTO-RESULTS:START -->.*?<!-- AUTO-RESULTS:END -->",
                                "<!-- AUTO-RESULTS:START -->\n" + block + "<!-- AUTO-RESULTS:END -->", s, flags=re.S))
    print(block)


if __name__ == "__main__":
    main()
