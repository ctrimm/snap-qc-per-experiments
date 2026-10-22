"""Exp104 part C: per-question routing analysis on the Cornell quiz from existing full runs + exp104 signals.

Exploratory (evaluation set; no thresholds carried into a confirmatory claim without a fresh run). Threshold routers
are scored with split-half cross-validation (seed 104): pick the threshold on one half, score on the other, average.
Writes the AUTO-RESULTS block of exp104_routing_signals.md and the vault note; aggregate numbers only.
"""
import collections
import csv
import glob
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path

from inspect_ai.log import read_eval_log

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp94_96_analyze as A  # noqa: E402
from exp99_analyze import fmt  # noqa: E402

VAULT = Path.home() / "Documents/Obsidian Vault/Labs/2026-10-22 snap-qc exp104 routing signals.md"
ROWS = {r["question_id"]: r for r in csv.DictReader(open(A.CORNELL, encoding="utf-8-sig"))}
IDS = sorted(ROWS, key=int)
KEY = {i: ROWS[i]["correct_single_answer"].strip() for i in IDS}


def full(d):
    """{id: (answer, tool_calls)} from the latest log of a full agent run."""
    l = read_eval_log(sorted(glob.glob(str(A.D / d / "*.eval")))[-1])
    out = {}
    for s in l.samples:
        sc = list(s.scores.values())[0] if s.scores else None
        calls = sum(1 for m in s.messages if m.role == "assistant" for tc in (m.tool_calls or []) if tc.function != "submit")
        out[str(s.id)] = (sc.answer if sc else None, calls)
    return out


def signal(d):
    """{id: [ (answer, confidence), ... per epoch ]} from an exp104 signal run."""
    fs = sorted(glob.glob(str(A.D / "exp104_logs" / d / "*.eval")))
    if not fs:
        return None
    out = collections.defaultdict(list)
    for s in read_eval_log(fs[-1]).samples:
        sc = list(s.scores.values())[0] if s.scores else None
        out[str(s.id)].append((sc.answer if sc else None, (sc.metadata or {}).get("confidence") if sc else None))
    return out


def auroc(scores_wrong, scores_right):
    """P(score of a wrong answer > score of a right answer): risk scores, higher = more likely wrong."""
    n = len(scores_wrong) * len(scores_right)
    if not n:
        return None
    s = sum((w > r) + 0.5 * (w == r) for w in scores_wrong for r in scores_right)
    return round(s / n, 3)


def acc(ans):
    return round(100 * sum(ans[i] == KEY[i] for i in IDS) / len(IDS), 1)


def main():
    runs = {"plain": "exp98_logs/31b_agent_2026", "datenotes": "exp102_logs/full_plain_date_notes",
            "combined": "exp98_logs/31b_combo_think_verify", "notes_check": "exp100_logs/full_notes_verify"}
    R = {k: full(v) for k, v in runs.items()}
    P = {i: R["plain"][i][0] for i in IDS}
    out = ["### Single setups (full runs)", "", "| Setup | Accuracy |", "|---|---|"]
    for k in R:
        out.append(f"| {k} | {acc({i: R[k][i][0] for i in IDS})}% |")
    wrong = [i for i in IDS if P[i] != KEY[i]]
    right = [i for i in IDS if P[i] == KEY[i]]

    # signals
    sig = {k: signal(k) for k in ("31b_confidence", "31b_topic", "31b_sc5", "e4b_sc5", "e4b_topic", "e4b_confidence")}
    risk = {}
    if sig["31b_confidence"]:
        risk["31B stated confidence (100 − c)"] = {i: 100 - (sig["31b_confidence"][i][0][1] or 0) for i in IDS}
    for k, lab in (("31b_sc5", "31B no-tool agreement (5 samples)"), ("e4b_sc5", "E4B no-tool agreement (5 samples)")):
        if sig[k]:
            risk[lab] = {i: 1 - collections.Counter(a for a, _ in sig[k][i]).most_common(1)[0][1] / len(sig[k][i]) for i in IDS}
            risk[lab.replace("agreement", "disagrees with plain agent")] = {
                i: float(collections.Counter(a for a, _ in sig[k][i]).most_common(1)[0][0] != P[i]) for i in IDS}
    if sig["e4b_confidence"]:
        risk["E4B stated confidence (100 − c)"] = {i: 100 - (sig["e4b_confidence"][i][0][1] or 0) for i in IDS}
    risk["plain agent tool calls"] = {i: R["plain"][i][1] for i in IDS}
    risk["plain vs date+notes answers differ"] = {i: float(P[i] != R["datenotes"][i][0]) for i in IDS}
    risk["plain vs combined answers differ"] = {i: float(P[i] != R["combined"][i][0]) for i in IDS}
    for k in ("31b_topic", "e4b_topic"):
        if sig[k]:
            risk[f"{k[:3].upper()} topic = noncitizens"] = {i: float("noncitizen" in (sig[k][i][0][0] or "")) for i in IDS}
    out += ["", f"### How well each signal flags the plain agent's mistakes ({len(wrong)} wrong of 500)", "",
            "| Signal (higher = riskier) | AUROC | Plain-agent accuracy when flagged / not flagged |", "|---|---|---|"]
    for lab, r in risk.items():
        a = auroc([r[i] for i in wrong], [r[i] for i in right])
        med = sorted(r.values())[len(r) // 2]
        hi = [i for i in IDS if r[i] > med] or [i for i in IDS if r[i] >= med]
        lo = [i for i in IDS if i not in set(hi)]
        f = lambda xs: round(100 * sum(P[i] == KEY[i] for i in xs) / max(1, len(xs)), 1)
        out.append(f"| {lab} | {a} | {f(hi)}% (n={len(hi)}) / {f(lo)}% (n={len(lo)}) |")

    # routers
    D, C = {i: R["datenotes"][i][0] for i in IDS}, {i: R["combined"][i][0] for i in IDS}
    N = {i: R["notes_check"][i][0] for i in IDS}
    routers = {}
    for k in ("31b_topic", "e4b_topic"):
        if sig[k]:
            routers[f"{k[:3].upper()} topic = noncitizens → date+notes, else plain"] = {
                i: D[i] if "noncitizen" in (sig[k][i][0][0] or "") else P[i] for i in IDS}
    routers["answers differ (plain vs date+notes) → combined breaks the tie"] = {
        i: P[i] if P[i] == D[i] else (C[i] if C[i] in (P[i], D[i]) else P[i]) for i in IDS}
    vote = {}
    for i in IDS:
        c = collections.Counter([P[i], D[i], C[i]]).most_common()
        vote[i] = c[0][0] if c[0][1] > 1 else P[i]
    routers["majority of plain, date+notes, combined (ties → plain)"] = vote
    if sig["31b_sc5"]:
        maj = {i: collections.Counter(a for a, _ in sig["31b_sc5"][i]).most_common(1)[0][0] for i in IDS}
        vote4 = {}
        for i in IDS:
            c = collections.Counter([P[i], D[i], C[i], maj[i]]).most_common()
            vote4[i] = c[0][0] if c[0][1] > 1 and (len(c) == 1 or c[0][1] > c[1][1]) else P[i]
        routers["majority of plain, date+notes, combined, 31B no-tool majority (ties → plain)"] = vote4
    out += ["", "### Routers (all answers from existing runs)", "", "| Router | Accuracy | vs plain (95% CI) | Questions sent to a second setup |",
            "|---|---|---|---|"]
    prow = {i: {"ok": float(P[i] == KEY[i])} for i in IDS}
    for lab, ans in routers.items():
        rr = {i: {"ok": float(ans[i] == KEY[i])} for i in IDS}
        moved = sum(1 for i in IDS if ans[i] != P[i])
        out.append(f"| {lab} | {acc(ans)}% | {fmt(A.boot(rr, prow, IDS, 104))} | answers changed on {moved} |")

    # threshold routers with split-half CV: escalate the riskiest x% (by a signal) to a target setup
    rng = random.Random(104); half = set(rng.sample(IDS, 250))
    halves = [[i for i in IDS if i in half], [i for i in IDS if i not in half]]
    out += ["", "### Threshold routers, split-half cross-validated (threshold picked on one half, scored on the other)", "",
            "| Signal → escalate to | Cross-validated accuracy | Plain on the same halves | Share escalated |", "|---|---|---|---|"]
    for lab, r in risk.items():
        if "topic" in lab:
            continue
        for tname, T in (("combined", C), ("date+notes", D), ("notes+check", N)):
            tot = base = esc = 0
            for k in (0, 1):
                fit, test = halves[k], halves[1 - k]
                best, bt = -1, None
                for t in sorted(set(r[i] for i in fit)):
                    a = sum((T[i] if r[i] > t else P[i]) == KEY[i] for i in fit)
                    if a > best:
                        best, bt = a, t
                tot += sum((T[i] if r[i] > bt else P[i]) == KEY[i] for i in test)
                base += sum(P[i] == KEY[i] for i in test); esc += sum(r[i] > bt for i in test)
            out.append(f"| {lab} → {tname} | {round(100 * tot / 500, 1)}% | {round(100 * base / 500, 1)}% | {round(100 * esc / 500, 1)}% |")

    # ceilings
    def oracle(sets):
        return round(100 * sum(any(s[i] == KEY[i] for s in sets) for i in IDS) / 500, 1)
    out += ["", "### Ceilings (a perfect router)", "", "| Setups available | Oracle accuracy |", "|---|---|",
            f"| plain + date+notes | {oracle([P, D])}% |", f"| plain + date+notes + combined | {oracle([P, D, C])}% |",
            f"| plain + date+notes + combined + notes+check | {oracle([P, D, C, N])}% |"]
    block = f"Scored {datetime.now():%Y-%m-%d %H:%M} by `exp104_route.py` (exploratory; evaluation set).\n\n" + "\n".join(out) + "\n"
    retr = A.D / "exp104/retrieval.jsonl"
    if retr.exists():
        rows = [json.loads(l) for l in open(retr)]
        rt = ["### Retrieval (part A): gold document in get_passages' top results", "",
              "| Config | Our hard set hit@1 / hit@5 (224) | QA pairs, California hit@5 | QA pairs, federal hit@5 | QA pairs, other states hit@5 |",
              "|---|---|---|---|---|"]
        for r in rows:
            q = r["qa"]
            rt.append(f"| {r['label']} | {r['hard']['hit1']}% / {r['hard']['hit5']}% | {q.get('ca', {}).get('hit5')}% (n={q.get('ca', {}).get('n')}) | "
                      f"{q.get('us', {}).get('hit5')}% | {q.get('other states', {}).get('hit5')}% |")
        block = "\n".join(rt) + "\n\n" + block
    for f in (HERE / "exp104_routing_signals.md", VAULT):
        if f.exists():
            s = f.read_text()
            f.write_text(re.sub(r"<!-- AUTO-RESULTS:START -->.*?<!-- AUTO-RESULTS:END -->",
                                "<!-- AUTO-RESULTS:START -->\n" + block + "<!-- AUTO-RESULTS:END -->", s, flags=re.S))
    print(block)


if __name__ == "__main__":
    main()
