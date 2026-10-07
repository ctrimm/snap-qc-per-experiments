"""Exp 54 — real label targets for eval-consistent synthetic labels.

Measures, on real FY2021-2024 QC public-use files with the eval's denylisted
items excluded, the label mix the exp30 eval actually scores: T3 element
bucket, T4 nature, T5 cause bucket of the *largest reportable* variance
(labels.label_case), by fiscal-year era. Also P(cause bucket | element
bucket) under the pre-FY2024 coding convention, used to re-draw cause 26
(no-fault, a FY2024-only code). Writes aggregate shares only to
exp54_label_targets.json.

Usage: python3 experiments/exp54_label_targets.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments" / "eval_pilot"), str(ROOT / "src")]
import labels as L  # noqa: E402
import sample as S  # noqa: E402

deny = set((ROOT / "experiments/eval_pilot/denylist.txt").read_text().split()[1::2])
era_of = {2021: "pre2024", 2022: "pre2024", 2023: "pre2024", 2024: "fy2024"}
marg = {e: {t: Counter() for t in ("t3", "t4", "t5")} for e in ("pre2024", "fy2024")}
cause_given_t3 = defaultdict(Counter)
for fy in (2021, 2022, 2023, 2024):
    for _, row in S.load_year(fy).iterrows():
        r = S.row_dict(row)
        if S.case_id_hash(fy, r.get("STATE"), r.get("YRMONTH"), r.get("HHLDNO")) in deny:
            continue
        if L._int_or_none(L._num(r, "STATUS")) not in (2, 3):
            continue
        lab = L.label_case(r)
        e = era_of[fy]
        for t in ("t3", "t4", "t5"):
            if lab[t]:
                marg[e][t][lab[t]] += 1
        if e == "pre2024" and lab["t3"] and lab["t5"]:
            cause_given_t3[lab["t3"]][lab["t5"]] += 1
share = lambda c: {k: v / sum(c.values()) for k, v in c.most_common()}  # noqa: E731
out = {"source": "FY2021-2024 QC public-use, eval denylist excluded; primary = largest reportable variance",
       "marginals": {e: {t: share(c) for t, c in d.items()} for e, d in marg.items()},
       "cause_given_t3_pre2024": {b: share(c) for b, c in cause_given_t3.items()}}
(ROOT / "experiments/exp54_label_targets.json").write_text(json.dumps(out, indent=1))
for e in out["marginals"]:
    print(e, {t: dict(list(v.items())[:5]) for t, v in out["marginals"][e].items()})
