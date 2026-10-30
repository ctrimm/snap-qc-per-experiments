"""Exp 110 — train on the official (over-threshold) error definition vs any error (pre-registered in
exp110_official_error_definition.md). Leak-free features (default), exp83 pooled design, exp68 holdouts.

Usage: python3 experiments/exp110_official_error_definition.py [--workers 8]
"""
import argparse
import json
import os
import statistics as st
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp106_better_government_lab_comparison as G  # noqa: E402
import exp106_leakfree as LF  # noqa: E402

_G = G._G


def run_one(job):
    ab, code, hold_keys, variant = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    import exp72_fairness_all_states as F
    from exp75_small_state_pooling import fit_w
    from exp93_cost_share_current_models import floor_select
    assert E58.LEAKFREE
    data, extra, types = _G["data"], _G["extra"], _G["types"]
    D = E56.DEFAULT; wown = 10.0 if variant == "C_ctx" else 1.0
    own = data[code]; ho = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
    trk = [(code, k) for k in tr] + [(c, k) for c in data if c != code for k in sorted(data[c])]
    Xa = np.array([data[c][k][0] for c, k in trk]); wa = np.array([wown if c == code else 1.0 for c, _ in trk])
    labels = {
        "ANY": (np.array([data[c][k][1] != "1" for c, k in trk], int), np.array([data[c][k][2] for c, k in trk])),
        "OVER": (np.array([G.over(c, k) for c, k in trk], int),
                 np.array([extra[c][k][0] if G.over(c, k) else 0.0 for c, k in trk])),
    }
    Xh, yh, ah = E58.arrays(own, te)
    ov = np.array([G.over(code, k) for k in te], int)
    ao = np.array([extra[code][k][0] if G.over(code, k) else 0.0 for k in te])
    ht_raw = np.array([types[code][k] for k in te]); cnt = Counter(ht_raw)
    ht = np.array([t if cnt[t] >= 25 and t in F.TYPES else "other" for t in ht_raw])
    tlist = [t for t in F.TYPES + ["other"] if (ht == t).any()]
    ht_tr = np.array([t if t in tlist else "other" for t in (types[code][k] for k in tr)])
    n_own = len(tr)
    res = {"state": ab, "variant": variant}
    for arm, (ya, aa) in labels.items():
        s = fit_w(Xa, ya, aa, wa, D, D)(Xh)
        err_h = yh if arm == "ANY" else ov
        r = {}
        for frac in (0.10, 0.20):
            k = int(round(len(te) * frac)); base = np.argsort(-s, kind="stable")[:k]
            fl = floor_select(s, err_h, ht, ht_tr, ya[:n_own], tlist, k)
            r[f"top{int(frac * 100)}"] = {
                "lift_any": round(float(ah[base].sum() / max(ah.sum() * frac, 1)), 3),
                "lift_over": round(float(ao[base].sum() / max(ao.sum() * frac, 1)), 3),
                "floor_lift_any": round(float(ah[fl].sum() / max(ah.sum() * frac, 1)), 3),
                "floor_lift_over": round(float(ao[fl].sum() / max(ao.sum() * frac, 1)), 3),
                "precision_any": round(float(yh[base].mean()), 3), "precision_over": round(float(ov[base].mean()), 3)}
            if frac == 0.20:
                r["ratios_own_definition"] = LF.ratios(base, err_h, ht, tlist)
        res[arm] = r
    # D1 with the OVER label (exp106 frame and exclusions)
    t2 = [(c, k) for c in data for k in sorted(data[c]) if k[0] in (2022, 2023)]
    Xt = np.array([data[c][k][0] for c, k in t2]); wt = np.array([wown if c == code else 1.0 for c, _ in t2])
    yt = np.array([G.over(c, k) for c, k in t2], int); at = np.array([extra[c][k][0] if G.over(c, k) else 0.0 for c, k in t2])
    tek = [k for k in sorted(own) if k[0] == 2024 and not extra[code][k][2] and not extra[code][k][3]
           and abs(extra[code][k][0] - extra[code][k][1]) <= 5]
    Xe = np.array([own[k][0] for k in tek])
    err = np.array([G.over(code, k) for k in tek], int)
    dol = np.array([extra[code][k][0] if G.over(code, k) else 0.0 for k in tek])
    sc = fit_w(Xt, yt, at, wt, D, D)(Xe)
    res["D1_OVER"] = {f"budget{int(b * 100):02d}": G.budget_metrics(sc, err, dol, b) for b in (0.05, 0.10)}
    return res


def cost_share(results, arm, key):
    import exp69_cost_share_scenarios as X
    e93 = json.loads((ROOT / "experiments/exp93_leakfree_results.json").read_text())["states"]
    tot = {}
    for scen, basis in (("low", "top20"), ("central", "top10"), ("high", "top10")):
        sc = X.SCEN[scen]; t = 0.0
        for ab, r in results.items():
            p0 = e93[ab]["per_fy2025"]; ben = e93[ab]["annual_benefits"]
            L = r[arm][basis][key]
            t += (X.share(p0) - X.share(p0 / (1 + sc["R"] * L * sc["f"] * sc["m"]))) * ben
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
    with get_context("spawn").Pool(args.workers, initializer=LF.init) as pool:
        for r in pool.imap_unordered(run_one, jobs):
            out[r["state"]] = r
            print(f"{r['state']}: ANY {r['ANY']['top20']['lift_any']}/{r['ANY']['top20']['lift_over']} "
                  f"OVER {r['OVER']['top20']['lift_any']}/{r['OVER']['top20']['lift_over']}", flush=True)
    out = dict(sorted(out.items()))
    e83 = json.loads((ROOT / "experiments/exp83_leakfree_results.json").read_text())
    gate = sum(abs(out[s]["ANY"]["top20"]["lift_any"] - e83[s]["top20"]["lift"]) < 0.002 for s in out)
    cs = {"ANY_any": cost_share(out, "ANY", "floor_lift_any"), "ANY_over": cost_share(out, "ANY", "floor_lift_over"),
          "OVER_over": cost_share(out, "OVER", "floor_lift_over")}
    print("gate (ANY reproduces exp83_leakfree top20):", gate, "of", len(out))
    print("cost share:", cs)
    import exp58_agency_rankers as E58
    E58.results_path("exp110_results.json").write_text(json.dumps({"gate": gate, "cost_share": cs, "states": out}, indent=1))


if __name__ == "__main__":
    main()
