"""Exp 93 — FY2028 cost-share scenarios on the deployed models, fairness floor on.

Why: the headline cost-share figure ($5.28B central, exp69) used the old
own-case lifts (exp68), the top-10% lift and no floor. exp78 re-ran it with the
floor but had to switch to the top-20% basis (the floor's top-10% lift was never
measured), giving $3.49B; the switch of basis, not the floor, made most of that
difference ($5.28B -> $3.85B basis, $3.85B -> $3.49B floor). Neither figure uses
the context-aware pooled models now deployed (exp80/82/83).

Pre-registered (this docstring, written before running):
  1. Re-run exp83's per-jurisdiction fit exactly (adopted variant, exp68
     holdouts, same seeds) and measure the exp72 per-type floor (f = 1.0) at
     BOTH top 10% and top 20% (exp83 measured top 20% only). Gate: top-10% lift,
     top-20% lift and top-20% floor lift must reproduce exp83_results.json
     exactly in every jurisdiction; otherwise stop and report.
  2. exp69's model, inputs and scenarios unchanged (low: R 1%, top-20% lift,
     f 0.6, m 4; central: R 2%, top-10% lift, f 0.8, m 6; high: R 3%, top-10%
     lift, f 0.9, m 8), with the lift taken from the deployed models:
       arms = floor on (the recommended default; headline), dollar-only, random.
     Also report the floor-on central on the top-20% basis (exp78's basis) as
     the conservative reading.
  3. Per jurisdiction, write the floor-on scenario rows in exp69's format so the
     dashboard can use them.

Usage: python3 experiments/exp93_cost_share_current_models.py [--workers 6]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp83_context_models_full_eval as E83  # noqa: E402


def _np(o):
    """json default: numpy scalars to Python numbers."""
    return o.item()


def floor_select(s, yh, ht, ht_tr, y, tlist, k):
    """exp72/exp83 per-type floor (f = 1.0) for a budget of k cases."""
    share = {t: float(((ht_tr == t) & (y == 1)).sum()) / max(y.sum(), 1) for t in tlist}
    quota = {t: share[t] * k for t in tlist}; floors = {t: int(np.floor(q)) for t, q in quota.items()}
    for t in sorted(tlist, key=lambda t: -(quota[t] - floors[t]))[: k - sum(floors.values())]:
        floors[t] += 1
    sel = []
    for t in tlist:
        idx = np.where(ht == t)[0]; sel += list(idx[np.argsort(-s[idx], kind="stable")[: min(floors[t], len(idx))]])
    rest = [i for i in np.argsort(-s, kind="stable") if i not in set(sel)]
    return np.array(sel + rest[: k - len(sel)])


def run_one(job):
    """exp83.run_one, with the floor measured at top 10% and top 20%."""
    ab, code, hold_keys, variant = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    import exp72_fairness_all_states as F
    from exp75_small_state_pooling import fit_w
    from collections import Counter
    data = E83._G["data"]; own = data[code]
    ho = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
    X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
    others = [(c, k) for c in data if c != code for k in data[c]]
    Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
    ao = np.array([data[c][k][2] for c, k in others])
    wown = 10.0 if variant == "C_ctx" else 1.0
    D = E56.DEFAULT
    s = fit_w(np.vstack([X, Xo]), np.concatenate([y, yo]), np.concatenate([a, ao]),
              np.concatenate([np.full(len(y), wown), np.ones(len(yo))]), D, D)(Xh)
    ht_map = F.types_for(str(ROOT.parent / "snap-qc-data/raw"), code)
    ht = np.array([ht_map[k] for k in te]); cnt = Counter(ht)
    ht = np.array([t if cnt[t] >= 25 and t in F.TYPES else "other" for t in ht])
    tlist = [t for t in F.TYPES + ["other"] if (ht == t).any()]
    ht_tr = np.array([ht_map[kk] for kk in tr]); ht_tr = np.array([t if t in tlist else "other" for t in ht_tr])
    res = {"state": ab, "variant": variant}
    for frac in (0.10, 0.20):
        k = int(round(len(te) * frac)); denom = max(ah.sum() * frac, 1.0)
        top = np.argsort(-s, kind="stable")[:k]; sel = floor_select(s, yh, ht, ht_tr, y, tlist, k)
        res[f"top{int(frac * 100)}"] = {"lift": round(float(ah[top].sum()) / denom, 3),
                                        "floor_lift": round(float(ah[sel].sum()) / denom, 3),
                                        "floor_elderly_ratio": F.ratios(sel, yh, ht, tlist).get("elderly")}
    return res


def scenarios(lifts_by_arm):
    import exp69_cost_share_scenarios as X
    per = json.loads((ROOT / "experiments/exp69_published_per.json").read_text())["rates"]["2025"]
    hh, ben = X.caseload_and_benefits()
    out = {"totals": {}, "states": {}}
    for k, sc in X.SCEN.items():
        for arm, lifts in lifts_by_arm.items():
            tot = 0.0; moved = 0; under = 0
            for name, ab in X.NAME_TO_USPS.items():
                p0 = per[name]["per"]; L = 1.0 if lifts is None else lifts[ab][sc["lift"]]
                p1 = p0 / (1 + sc["R"] * L * sc["f"] * sc["m"])
                tot += (X.share(p0) - X.share(p1)) * ben[ab]; moved += X.share(p1) < X.share(p0); under += p1 < 6
                if arm == "floor_on":
                    row = out["states"].setdefault(ab, {"per_fy2025": p0, "annual_benefits": round(ben[ab]),
                                                        "cost_share_now": X.share(p0), "scenarios": {}})
                    pr = p0 / (1 + sc["R"] * sc["f"] * sc["m"])
                    row["scenarios"][k] = {"ranker": {"per": round(p1, 2), "cost_share": X.share(p1),
                                                      "saving_vs_now": round((X.share(p0) - X.share(p1)) * ben[ab])},
                                           "random": {"per": round(pr, 2), "cost_share": X.share(pr)},
                                           "reviews_per_month": round(sc["R"] * hh[ab]),
                                           "fte": round(sc["R"] * hh[ab] * 0.5 / 140, 1)}
            out["totals"].setdefault(k, {})[arm] = {"avoided": round(tot), "states_dropping_bracket": moved, "under_6pct": under}
    # conservative reading: floor on, central, top-20% basis (exp78's basis)
    sc = X.SCEN["central"]; tot = 0.0
    for name, ab in X.NAME_TO_USPS.items():
        p0 = per[name]["per"]; p1 = p0 / (1 + sc["R"] * lifts_by_arm["floor_on"][ab]["top20"] * sc["f"] * sc["m"])
        tot += (X.share(p0) - X.share(p1)) * ben[ab]
    out["totals"]["central_top20_floor_on"] = round(tot)
    out["cost_share_now"] = round(sum(X.share(per[n]["per"]) * ben[ab] for n, ab in X.NAME_TO_USPS.items()))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=6); args = ap.parse_args()
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    adopted = {}
    for f in ("exp80_results.json", "exp82_results.json"):
        for ab, r in json.loads((ROOT / "experiments" / f).read_text()).items():
            adopted[ab] = r["adopted"]
    jobs = [(ab, hold[ab]["code"], hold[ab]["keys"], v) for ab, v in sorted(adopted.items()) if v != "keep"]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    meas = {}
    with get_context("spawn").Pool(args.workers, initializer=E83.init) as pool:
        for r in pool.imap_unordered(run_one, jobs):
            meas[r["state"]] = r
            print(f"{r['state']}: top10 {r['top10']['lift']:.3f} (floor {r['top10']['floor_lift']:.3f}) "
                  f"top20 {r['top20']['lift']:.3f} (floor {r['top20']['floor_lift']:.3f})", flush=True)
    # gate: reproduce exp83
    r83 = json.loads(__import__("exp58_agency_rankers").results_path("exp83_results.json").read_text())
    bad = [ab for ab, r in meas.items() if (r["top10"]["lift"], r["top20"]["lift"], r["top20"]["floor_lift"])
           != (r83[ab]["top10"]["lift"], r83[ab]["top20"]["lift"], r83[ab]["fairness"]["floor_lift"])]
    print(f"GATE: {len(meas) - len(bad)} of {len(meas)} reproduce exp83" + (f"; mismatches {sorted(bad)}" if bad else ""))
    if bad or len(meas) != 53:
        (__import__("exp58_agency_rankers").results_path("exp93_results.json")).write_text(json.dumps({"gate": "FAILED", "mismatch": sorted(bad), "measured": meas}, indent=1, default=_np))
        sys.exit(1)
    floor_on = {ab: {"top10": r["top10"]["floor_lift"], "top20": r["top20"]["floor_lift"]} for ab, r in meas.items()}
    dollar = {ab: {"top10": r["top10"]["lift"], "top20": r["top20"]["lift"]} for ab, r in meas.items()}
    sc = scenarios({"floor_on": floor_on, "dollar_only": dollar, "random": None})
    med = lambda xs: float(np.median(xs))
    sc["medians"] = {"top10_lift": med([d["top10"] for d in dollar.values()]), "top10_floor_lift": med([d["top10"] for d in floor_on.values()]),
                     "top20_lift": med([d["top20"] for d in dollar.values()]), "top20_floor_lift": med([d["top20"] for d in floor_on.values()]),
                     "top10_floor_elderly_ratio": med([r["top10"]["floor_elderly_ratio"] for r in meas.values() if r["top10"]["floor_elderly_ratio"] is not None])}
    sc["gate"] = "PASSED"; sc["measured"] = dict(sorted(meas.items()))
    (__import__("exp58_agency_rankers").results_path("exp93_results.json")).write_text(json.dumps(sc, indent=1, default=_np))
    for k in ("low", "central", "high"):
        print(k, " | ".join(f"{a}: ${v['avoided'] / 1e9:.2f}B ({v['states_dropping_bracket']} drop)" for a, v in sc["totals"][k].items()))
    print(f"central, floor on, top-20% basis: ${sc['totals']['central_top20_floor_on'] / 1e9:.2f}B; medians {sc['medians']}")


if __name__ == "__main__":
    main()
