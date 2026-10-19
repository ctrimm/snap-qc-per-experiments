"""Exp94-96 readouts: accuracy, paired bootstrap CIs, the exp95 keyword routers, exp96 guard counts.

Prints JSON only (no question text). Cornell question text is read locally for the router and never written out.
Usage: python experiments/exp94_96_analyze.py [exp94|exp95|exp96]  (default all)
"""
import collections
import csv
import glob
import json
import random
import re
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

HERE = Path(__file__).resolve().parent
D = HERE.parents[1] / "snap-qc-data/derived"
CORNELL = Path.home() / "datasets/snap_scenarios/snap_scenarios.csv"
STRUCTURED = re.compile(r"monthly (snap |calfresh )?benefit|how much|what (is|are) the (maximum|minimum)|resource limit|asset limit|"
                        r"standard deduction|utility allowance|income (eligibility )?(standard|limit)|gross income standard|"
                        r"deduction (is|amount)", re.I)


def load(logdir):
    fs = sorted(glob.glob(str(D / logdir / "*.eval")))
    if not fs:
        return None
    log = read_eval_log(fs[-1])
    if log.status != "success" or not log.samples:
        return None
    rows = {}
    for s in log.samples:
        if not s.scores:  # sample ended in an error without a score: counts as wrong, unanswered
            rows[str(s.id)] = {"ok": 0.0, "kind": (s.metadata or {}).get("category", "").split(":")[0], "answered": False,
                               "limit": s.limit is not None, "forced": (s.metadata or {}).get("forced"), "calls": collections.Counter(),
                               "errored": True}
            continue
        sc = list(s.scores.values())[0]
        calls = collections.Counter(tc.function for m in s.messages if m.role == "assistant" for tc in (m.tool_calls or [])
                                    if tc.function != "submit")
        md = s.metadata or {}
        rows[str(s.id)] = {"ok": float(sc.value or 0), "kind": md.get("category", "").split(":")[0],
                           "answered": sc.answer is not None, "limit": s.limit is not None, "forced": md.get("forced"),
                           "calls": calls}
    return rows


def boot(a, b, ids, seed, n=2000):
    d = [a[i]["ok"] - b[i]["ok"] for i in ids]
    rng = random.Random(seed)
    ms = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return [round(100 * sum(d) / len(d), 1), round(100 * ms[int(0.025 * n)], 1), round(100 * ms[int(0.975 * n) - 1], 1)]


def acc(rows, ids=None):
    ids = list(rows) if ids is None else ids
    return round(100 * sum(rows[i]["ok"] for i in ids) / len(ids), 1) if ids else None


def summary(rows):
    n = len(rows)
    tot = collections.Counter()
    for x in rows.values():
        tot.update(x["calls"])
    out = {"n": n, "accuracy": acc(rows), "unanswered": sum(not x["answered"] for x in rows.values()),
           "message_limit": sum(x["limit"] for x in rows.values()), "calls_per_q": round(sum(tot.values()) / n, 2),
           "get_section_per_q": round(tot["get_section"] / n, 2)}
    forced = [i for i, x in rows.items() if x["forced"]]
    if any(x["forced"] is not None for x in rows.values()):
        out["forced"] = len(forced)
        out["forced_accuracy"] = acc(rows, forced)
    return out


def pairs(data, spec, seed):
    out = []
    for a, b in spec:
        if data.get(a) and data.get(b):
            ids = sorted(set(data[a]) & set(data[b]))
            out.append({"pair": f"{a} - {b}", "n": len(ids), "diff_ci": boot(data[a], data[b], ids, seed)})
    return out


def stems(dataset):
    if dataset == "cornell":
        return {r["question_id"]: r["question"] for r in csv.DictReader(open(CORNELL, encoding="utf-8-sig"))}
    return {json.loads(l)["id"]: json.loads(l)["question"].split("\nA. ")[0] for l in open(HERE / dataset)}


def exp94():
    arms = {a: f"exp94_logs/{a}" for a in ["e4b_notools", "e4b_auto_filter", "e4b_agent", "e4b_agent_strict",
                                           "e4b_agent_recipe", "31b_notools", "31b_agent"]}
    data = {a: load(p) for a, p in arms.items()}
    sets = {json.loads(l)["id"]: json.loads(l)["set"] for l in open(HERE / "exp94_hard.jsonl")}
    out = {"arms": {}, "by_kind": {}, "by_subset": {}, "pairs": [], "repro_exp90": {}}
    for a, r in data.items():
        if not r:
            continue
        out["arms"][a] = summary(r)
        kinds = collections.defaultdict(list)
        for i, x in r.items():
            kinds[x["kind"]].append(i)
        out["by_kind"][a] = {k: [acc(r, v), len(v)] for k, v in sorted(kinds.items())}
        out["by_subset"][a] = {s: acc(r, [i for i in r if sets.get(i) == s]) for s in ("exp90", "exp94")}
        old = load(f"exp90_logs/{a}")
        if old:
            ids = [i for i in r if i in old]
            out["repro_exp90"][a] = {"oct12": acc(old, ids), "today": acc(r, ids),
                                     "same_answer_correctness": round(100 * sum(old[i]["ok"] == r[i]["ok"] for i in ids) / len(ids), 1)}
    spec = [("e4b_auto_filter", "e4b_notools"), ("e4b_agent", "e4b_notools"), ("e4b_agent_strict", "e4b_agent"),
            ("e4b_agent_recipe", "e4b_agent"), ("31b_agent", "31b_notools"), ("31b_agent", "e4b_agent_recipe")]
    out["pairs"] = pairs(data, spec, 94)
    date_ids = [i for i, x in (data.get("e4b_auto_filter") or {}).items() if x["kind"] == "date"]
    out["h2_date"] = {a: acc(data[a], date_ids) for a in ("e4b_auto_filter", "e4b_agent", "e4b_agent_strict", "e4b_agent_recipe")
                      if data.get(a) and date_ids}
    return out


def route(st, structured_arm, open_arm, ids):
    rows, big = {}, 0
    for i in ids:
        use_small = bool(STRUCTURED.search(st[i]))
        rows[i] = (structured_arm if use_small else open_arm)[i]
        big += not use_small
    return rows, round(100 * big / len(ids), 1)


def exp95():
    out = {}
    cfg = {
        "exp94": ("exp94_hard.jsonl", "exp95_logs/e4b_rp_exp94", "exp94_logs/e4b_agent_recipe", "exp94_logs/31b_agent"),
        "exp87": ("exp87_heldout.jsonl", "exp95_logs/e4b_rp_exp87", "exp91_logs/e4b_exp87set_agent_recipe", "exp87_logs/31b_agent"),
        "cornell": ("cornell", "exp95_logs/e4b_rp_cornell", "exp91_logs/e4b_cornell_agent_recipe_true", "exp86_logs/agent_new_dated_true"),
    }
    for name, (ds, rp_p, rec_p, big_p) in cfg.items():
        rp, rec, big = load(rp_p), load(rec_p), load(big_p)
        r = {"arms": {}, "pairs": []}
        for a, x in (("e4b_recipe_passages", rp), ("e4b_recipe", rec), ("31b_agent", big)):
            if x:
                r["arms"][a] = summary(x)
        if rp and rec:
            ids = sorted(set(rp) & set(rec))
            r["pairs"].append({"pair": "recipe_passages - recipe", "n": len(ids), "diff_ci": boot(rp, rec, ids, 95)})
            if name == "exp94":
                dids = [i for i in ids if rec[i]["kind"] == "date"]
                r["date_only"] = {"recipe_passages": acc(rp, dids), "recipe": acc(rec, dids), "n": len(dids)}
        st = stems(ds)
        if rec and big:
            ids = sorted(set(rec) & set(big) & set(st))
            rt, share = route(st, rec, big, ids)
            r["big_router"] = {"accuracy": acc(rt, ids), "share_to_31b": share,
                               "vs_e4b_recipe": boot(rt, rec, ids, 95), "vs_31b_agent": boot(rt, big, ids, 95)}
        if rec and rp:
            ids = sorted(set(rec) & set(rp) & set(st))
            rt, share = route(st, rec, rp, ids)
            r["small_router"] = {"accuracy": acc(rt, ids), "share_open": share, "vs_e4b_recipe": boot(rt, rec, ids, 95)}
        out[name] = r
    return out


def exp96():
    arms = {"tuned_cornell_g0": "exp92_logs/tuned_cornell_agent", "base_cornell_g0": "exp92_logs/base_cornell_agent",
            **{f"tuned_cornell_g{g}": f"exp96_logs/tuned_cornell_g{g}" for g in (4, 6, 8)},
            "base_cornell_g6": "exp96_logs/base_cornell_g6",
            **{f"{m}_exp94_g{g}": f"exp96_logs/{m}_exp94_g{g}" for m in ("tuned", "base") for g in (0, 6)}}
    data = {a: load(p) for a, p in arms.items()}
    spec = [(f"tuned_cornell_g{g}", "tuned_cornell_g0") for g in (4, 6, 8)] + \
           [(f"tuned_cornell_g{g}", "base_cornell_g0") for g in (4, 6, 8)] + \
           [("base_cornell_g6", "base_cornell_g0"), ("tuned_exp94_g6", "tuned_exp94_g0"), ("base_exp94_g6", "base_exp94_g0"),
            ("tuned_exp94_g6", "base_exp94_g0")]
    return {"arms": {a: summary(r) for a, r in data.items() if r}, "pairs": pairs(data, spec, 96)}


if __name__ == "__main__":
    which = sys.argv[1:] or ["exp94", "exp95", "exp96"]
    print(json.dumps({w: globals()[w]() for w in which}, indent=1))
