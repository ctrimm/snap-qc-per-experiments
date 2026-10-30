"""Exp 106, amendment 2 — the leak-free re-run (pre-registered in exp106_better_government_lab_comparison.md before running).

L1 = our 22 features minus issued_benefit (RAWBEN, index 15) and benefit_share_of_max (RAWBEN/BENMAX, index 21).
Per jurisdiction (adopted variant, same seeds and engine):
  D0  exp83 design (exp68 holdout): top-10/20% lift on all and on over-threshold error dollars; floor-on lifts; for L1
      and, as the reference, the full (leaky) feature set.
  D1  one-year-ahead test (train FY2022-23 all jurisdictions, test own FY2024 with giannella's exclusions), L1.
  C   review ratios by household type (any-error and over-threshold risk), dollar-only and floor, plus random review.
Then exp93's cost-share scenarios recomputed from the L1 floor-on lifts.

Usage: python3 experiments/exp106_leakfree.py [--workers 8]
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp106_better_government_lab_comparison as G  # noqa: E402

L1 = [i for i in range(22) if i not in (15, 21)]
_G = G._G


def init():
    G.init()
    import exp72_fairness_all_states as F
    import exp58_agency_rankers as E58
    import csv
    types = {}
    for fy in E58.FY_FILES:
        path = next(iter((G.RAW / f"qcfy{fy}_csv").glob("*.csv")))
        idx = {}
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                c = row["STATE"].strip(); i = idx.get(c, 0); idx[c] = i + 1
                types.setdefault(c, {})[(fy, i)] = F.htype(row)
    _G["types"] = types


def ratios(sel, err, ht, tlist):
    all_ratio = (len(sel) / len(err)) / max(err.mean(), 1e-9)
    out = {}
    for t in tlist:
        m = ht == t
        if m.sum() == 0 or err[m].sum() == 0:
            continue
        rev = np.isin(np.where(m)[0], sel).mean()
        out[t] = round(float((rev / err[m].mean()) / all_ratio), 3)
    return out


def random_ratio(err, ht, tlist):
    """What random review gives on this measure: overall error rate / the type's error rate."""
    return {t: round(float(err.mean() / err[ht == t].mean()), 3) for t in tlist if (ht == t).any() and err[ht == t].sum() > 0}


def run_one(job):
    ab, code, hold_keys, variant = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    import exp72_fairness_all_states as F
    from exp75_small_state_pooling import fit_w
    from exp93_cost_share_current_models import floor_select
    data, extra, types = _G["data"], _G["extra"], _G["types"]
    own = data[code]; D = E56.DEFAULT
    wown = 10.0 if variant == "C_ctx" else 1.0
    ho = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
    X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
    others = [(c, k) for c in data if c != code for k in data[c]]
    Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
    ao = np.array([data[c][k][2] for c, k in others])
    Xa = np.vstack([X, Xo]); ya = np.concatenate([y, yo]); aa = np.concatenate([a, ao])
    wa = np.concatenate([np.full(len(y), wown), np.ones(len(yo))])
    ov = np.array([G.over(code, k) for k in te], int)
    a_over = ah * ov
    ht_raw = np.array([types[code][k] for k in te]); cnt = Counter(ht_raw)
    ht = np.array([t if cnt[t] >= 25 and t in F.TYPES else "other" for t in ht_raw])
    tlist = [t for t in F.TYPES + ["other"] if (ht == t).any()]
    ht_tr = np.array([types[code][k] for k in tr]); ht_tr = np.array([t if t in tlist else "other" for t in ht_tr])
    res = {"state": ab, "variant": variant,
           "random": {"any": random_ratio(yh, ht, tlist), "over": random_ratio(ov, ht, tlist)}}
    for name, cols in (("leaky", list(range(22))), ("L1", L1)):
        s = fit_w(Xa[:, cols], ya, aa, wa, D, D)(Xh[:, cols])
        arm = {}
        for frac in (0.10, 0.20):
            k = int(round(len(te) * frac)); base = np.argsort(-s, kind="stable")[:k]
            fl = floor_select(s, yh, ht, ht_tr, y, tlist, k)
            arm[f"top{int(frac * 100)}"] = {
                "lift_any": round(float(ah[base].sum() / max(ah.sum() * frac, 1)), 3),
                "lift_over": round(float(a_over[base].sum() / max(a_over.sum() * frac, 1)), 3),
                "floor_lift_any": round(float(ah[fl].sum() / max(ah.sum() * frac, 1)), 3),
                "precision_any": round(float(yh[base].mean()), 3), "precision_over": round(float(ov[base].mean()), 3)}
            if frac == 0.20:
                arm["ratios"] = {"any": {"dollar": ratios(base, yh, ht, tlist), "floor": ratios(fl, yh, ht, tlist)},
                                 "over": {"dollar": ratios(base, ov, ht, tlist), "floor": ratios(fl, ov, ht, tlist)}}
        res[name] = arm
    # D1: one year ahead, their definitions, L1
    trk = [(c, k) for c in data for k in sorted(data[c]) if k[0] in (2022, 2023)]
    Xt = np.array([data[c][k][0] for c, k in trk])[:, L1]
    yt = np.array([data[c][k][1] != "1" for c, k in trk], int); at = np.array([data[c][k][2] for c, k in trk])
    wt = np.array([wown if c == code else 1.0 for c, _ in trk])
    tek = [k for k in sorted(own) if k[0] == 2024 and not extra[code][k][2] and not extra[code][k][3]
           and abs(extra[code][k][0] - extra[code][k][1]) <= 5]
    Xe = np.array([own[k][0] for k in tek])[:, L1]
    err = np.array([G.over(code, k) for k in tek], int)
    dol = np.array([extra[code][k][0] if G.over(code, k) else 0.0 for k in tek])
    sc = fit_w(Xt, yt, at, wt, D, D)(Xe)
    res["D1"] = {f"budget{int(b * 100):02d}": G.budget_metrics(sc, err, dol, b) for b in (0.05, 0.10)}
    return res


def cost_share(results):
    import exp69_cost_share_scenarios as X
    per = json.loads((ROOT / "experiments/exp69_published_per.json").read_text())
    e93 = json.loads((ROOT / "experiments/exp93_results.json").read_text())["states"]
    tot = {}
    for scen, basis in (("low", "top20"), ("central", "top10"), ("high", "top10"), ("central_top20", "top20")):
        sc = X.SCEN["central" if scen == "central_top20" else scen]
        t = 0.0
        for ab, r in results.items():
            p0 = e93[ab]["per_fy2025"]; ben = e93[ab]["annual_benefits"]
            L = r["L1"][basis]["floor_lift_any"]
            p1 = p0 / (1 + sc["R"] * L * sc["f"] * sc["m"])
            t += (X.share(p0) - X.share(p1)) * ben
        tot[scen] = round(t / 1e9, 2)
    return tot


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8); args = ap.parse_args()
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    adopted = {}
    for fn in ("exp80_results.json", "exp82_results.json"):
        for k, v in json.loads((ROOT / "experiments" / fn).read_text()).items():
            adopted[k] = v["adopted"]
    jobs = [(ab, hold[ab]["code"], hold[ab]["keys"], adopted[ab]) for ab in sorted(adopted)]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    out = {}
    with get_context("spawn").Pool(args.workers, initializer=init) as pool:
        for r in pool.imap_unordered(run_one, jobs):
            out[r["state"]] = r
            print(f"{r['state']}: top20 leaky {r['leaky']['top20']['lift_any']} L1 {r['L1']['top20']['lift_any']} | "
                  f"D1 5% prec {r['D1']['budget05']['precision']}", flush=True)
            (ROOT / "experiments/exp106_leakfree_results.json").write_text(json.dumps(dict(sorted(out.items())), indent=1))
    cs = cost_share(out)
    print("cost share (L1, floor on):", cs)
    full = {"states": dict(sorted(out.items())), "cost_share_L1": cs}
    (ROOT / "experiments/exp106_leakfree_results.json").write_text(json.dumps(full, indent=1))


if __name__ == "__main__":
    main()
