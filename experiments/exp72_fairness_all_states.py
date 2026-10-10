"""Exp 72 — household-type fairness of the exp68 rankers, all 53 jurisdictions.

exp47-49 audited the older six-state rankers. This reruns the audit on the
current agency-side rankers before any pilot conversation.

Pre-registered (this docstring, committed before running):
  Per jurisdiction: refit the exp68 configuration on its training rows,
  score its exp68 holdout, review the top 20% (k cases).
  Household types as exp47 (priority elderly > disabled > composition):
  elderly, disabled (non-elderly), single parent, married with kids,
  multi-adult with kids, child-only, childless adult; types with < 25
  holdout rows merge into "other".
  Measure: for each type, (share of its cases reviewed) / (share of its cases
  with an error), divided by the same ratio for all cases. 1.0 = reviewed in
  proportion to error risk; < 1 = under-reviewed for its risk.
  Remedy check: exp49's per-type floor at f = 1.0 (the whole budget split
  across types in proportion to each type's share of training errors, top
  scores within type), compared on dollars found and the ratios.
  Readouts: per jurisdiction and the 53-jurisdiction median, for elderly
  and disabled households especially; dollars-found cost of the floor.

Usage: python3 experiments/exp72_fairness_all_states.py [--workers 8]
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
TYPES = ["elderly", "disabled", "single_parent", "married_with_kids", "multiadult_with_kids", "child_only", "childless_adult"]


def htype(row):
    if (row.get("FSELDER") or "").strip() == "1":
        return "elderly"
    if (row.get("FSDIS") or "").strip() == "1":
        return "disabled"
    c = (row.get("COMPOSITION") or "").strip()
    return {"2": "single_parent", "3": "single_parent", "6": "single_parent", "4": "married_with_kids",
            "5": "multiadult_with_kids", "1": "child_only", "0": "childless_adult"}.get(c, "other")


def types_for(qc_dir, code):
    import exp58_agency_rankers as E58
    out = {}
    for fy in E58.FY_FILES:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")))
        idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != code:
                    continue
                out[(fy, idx)] = htype(row)
                idx += 1
    return out


def ratios(sel, y, ht, tlist):
    all_ratio = (len(sel) / len(y)) / max(y.mean(), 1e-9)
    out = {}
    for t in tlist:
        m = ht == t
        if m.sum() == 0 or y[m].sum() == 0:
            continue
        rev = np.isin(np.where(m)[0], sel).mean()
        out[t] = round(float((rev / y[m].mean()) / all_ratio), 3)
    return out


def run_one(job):
    ab, code, hold_keys, cfg, qc_dir = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    real = E58.load_state(qc_dir, code)
    ht_map = types_for(qc_dir, code)
    hold = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(real) if k not in hold]
    te = [k for k in sorted(real) if k in hold]
    X, y, a = E58.arrays(real, tr)
    Xh, yh, ah = E58.arrays(real, te)
    f, _ = E56.fit_two_part(X, y, a, cfg["clf"], cfg["reg"])
    s = f(Xh)
    ht = np.array([ht_map[k] for k in te])
    cnt = Counter(ht)
    ht = np.array([t if cnt[t] >= 25 and t in TYPES else "other" for t in ht])
    tlist = [t for t in TYPES + ["other"] if (ht == t).any()]
    k = int(round(0.2 * len(te)))
    base = np.argsort(-s, kind="stable")[:k]
    # floor at f = 1.0: budget split by each type's share of training errors
    ht_tr = np.array([ht_map[kk] for kk in tr])
    ht_tr = np.array([t if t in tlist else "other" for t in ht_tr])
    err_share = {t: float(((ht_tr == t) & (y == 1)).sum()) / max(y.sum(), 1) for t in tlist}
    quota = {t: err_share[t] * k for t in tlist}
    floors = {t: int(np.floor(q)) for t, q in quota.items()}
    for t in sorted(tlist, key=lambda t: -(quota[t] - floors[t]))[: k - sum(floors.values())]:
        floors[t] += 1
    sel = []
    for t in tlist:
        idx = np.where(ht == t)[0]
        sel += list(idx[np.argsort(-s[idx], kind="stable")[: min(floors[t], len(idx))]])
    rest = [i for i in np.argsort(-s, kind="stable") if i not in set(sel)]
    sel = np.array(sel + rest[: k - len(sel)])
    rand_dollars = ah.sum() * 0.2
    return {"state": ab, "n_holdout": len(te), "types": {t: int((ht == t).sum()) for t in tlist},
            "baseline": {"lift": round(float(ah[base].sum() / rand_dollars), 3), "ratio": ratios(base, yh, ht, tlist)},
            "floor": {"lift": round(float(ah[sel].sum() / rand_dollars), 3), "ratio": ratios(sel, yh, ht, tlist)}}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8); args = ap.parse_args()
    qc_dir = str(ROOT.parent / "snap-qc-data/raw")
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    cfg = {r["state"]: r["cfg"] for r in json.loads((ROOT / "experiments/exp68_results.json").read_text())}
    jobs = [(ab, h["code"], h["keys"], cfg[ab], qc_dir) for ab, h in hold.items()]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    with get_context("spawn").Pool(args.workers) as pool:
        res = sorted(pool.map(run_one, jobs), key=lambda r: r["state"])
    (ROOT / "experiments/exp72_results.json").write_text(json.dumps(res, indent=1))
    med = lambda xs: float(np.median(xs)) if xs else float("nan")
    for arm in ("baseline", "floor"):
        line = f"{arm:8s} median lift {med([r[arm]['lift'] for r in res]):.2f}x | median ratio "
        line += " ".join(f"{t} {med([r[arm]['ratio'][t] for r in res if t in r[arm]['ratio']]):.2f}" for t in TYPES)
        print(line)
    for t in ("elderly", "disabled"):
        b = [r["baseline"]["ratio"][t] for r in res if t in r["baseline"]["ratio"]]
        print(f"{t}: under-reviewed (ratio < 0.8) in {sum(x < 0.8 for x in b)} of {len(b)} jurisdictions at baseline; "
              f"{sum(r['floor']['ratio'].get(t, 1) < 0.8 for r in res if t in r['baseline']['ratio'])} with the floor")
    d = [r["floor"]["lift"] - r["baseline"]["lift"] for r in res]
    print(f"floor cost in lift: median {np.median(d):+.2f}x, worst {min(d):+.2f}x")


if __name__ == "__main__":
    main()
