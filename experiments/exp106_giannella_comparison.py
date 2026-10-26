"""Exp 106 — our rankers on giannella/snap_qc's test and definitions (pre-registered in exp106_giannella_comparison.md).

B0  exp83's refit (adopted variant, exp68 holdout): top-20% lift on all error dollars (gate: must reproduce exp83) and
    on over-threshold error dollars only (AMTERR of cases with |RAWBEN - FSBEN| above the fiscal year's tolerance).
B1  our recipe trained on FY2022-23 (all 53 jurisdictions pooled, adopted variant), scored on each state's FY2024 cases
    (their exclusions: MN_FIP, SSI_CAP, |RAWBEN-FSBEN| vs AMTERR > $5); top 5% / 10% by expected dollars; their
    metrics: precision, dollar recall, lift (error = |RAWBEN - FSBEN| > $56).
B2  as B1, trained on their target (over-threshold errors and dollars).
Compared per state with their published v2.5.0 2024 benchmark (giannella/snap_qc methods/v250_benchmark_2024).

Usage: python3 experiments/exp106_giannella_comparison.py [--workers 8]
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
RAW = ROOT.parent / "snap-qc-data/raw"
THEIRS = ROOT.parent / "giannella-snap_qc/methods/v250_benchmark_2024/v250_benchmark_2024.csv"
THRESHOLD = {2020: 38, 2021: 39, 2022: 48, 2023: 54, 2024: 56}  # giannella additional_data/year_data.csv
_G = {}


def fnum(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def load_extra():
    """{code: {(fy, idx): (absbendiff, amterr, mfip, ssicap)}, keyed exactly as exp80.load_all; plus code -> name."""
    out, names = {}, {}
    for fy in sorted(THRESHOLD):
        path = next(iter((RAW / f"qcfy{fy}_csv").glob("*.csv")))
        idx = {}
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                c = row["STATE"].strip(); i = idx.get(c, 0); idx[c] = i + 1
                names.setdefault(c, (row.get("STATENAME") or "").strip())
                out.setdefault(c, {})[(fy, i)] = (abs(fnum(row.get("RAWBEN")) - fnum(row.get("FSBEN"))), fnum(row.get("AMTERR")),
                                                  fnum(row.get("MN_FIP")) != 0, fnum(row.get("SSI_CAP")) != 0)
    return out, names


def init():
    import exp80_state_context as X80
    _G["data"] = X80.load_all(str(RAW))
    _G["extra"], _ = load_extra()


def over(code, k):
    absb = _G["extra"][code][k][0]
    return absb > THRESHOLD[k[0]]


def budget_metrics(score, err, dollars, budget):
    k = int(round(budget * len(score)))
    idx = np.argsort(-score, kind="stable")[:k]
    prec = float(err[idx].mean()) if k else 0.0
    base = float(err.mean())
    return {"n_te": len(score), "n_flagged": k, "precision": round(prec, 4), "base_rate": round(base, 4),
            "lift": round(prec / base, 3) if base else None, "dollar_recall": round(float(dollars[idx].sum() / max(dollars.sum(), 1e-9)), 4)}


def run_one(job):
    ab, code, hold_keys, variant = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    from exp75_small_state_pooling import fit_w, lift
    data, extra = _G["data"], _G["extra"]
    own = data[code]
    D = E56.DEFAULT
    wown = 10.0 if variant == "C_ctx" else 1.0
    res = {"state": ab, "variant": variant}

    # B0: exp83 refit on the exp68 holdout
    ho = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
    X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
    others = [(c, k) for c in data if c != code for k in data[c]]
    Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
    ao = np.array([data[c][k][2] for c, k in others])
    f = fit_w(np.vstack([X, Xo]), np.concatenate([y, yo]), np.concatenate([a, ao]),
              np.concatenate([np.full(len(y), wown), np.ones(len(yo))]), D, D)
    s = f(Xh)
    a_over = np.array([ah[i] if over(code, k) else 0.0 for i, k in enumerate(te)])
    res["B0"] = {"lift_any": round(lift(s, ah), 3), "lift_over": round(lift(s, a_over), 3),
                 "over_share_of_dollars": round(float(a_over.sum() / max(ah.sum(), 1e-9)), 4)}

    # B1 / B2: train FY2022-23 (all jurisdictions), test own FY2024 with their exclusions
    def rows(c, years):
        return [k for k in sorted(data[c]) if k[0] in years]
    trk = [(c, k) for c in data for k in rows(c, (2022, 2023))]
    Xt = np.array([data[c][k][0] for c, k in trk])
    wt = np.array([wown if c == code else 1.0 for c, _ in trk])
    tek = [k for k in rows(code, (2024,))
           if not extra[code][k][2] and not extra[code][k][3] and abs(extra[code][k][0] - extra[code][k][1]) <= 5]
    Xe = np.array([own[k][0] for k in tek])
    err = np.array([over(code, k) for k in tek], int)
    dol = np.array([extra[code][k][0] if over(code, k) else 0.0 for k in tek])
    arms = {
        "B1": (np.array([data[c][k][1] != "1" for c, k in trk], int), np.array([data[c][k][2] for c, k in trk])),
        "B2": (np.array([over(c, k) for c, k in trk], int),
               np.array([extra[c][k][0] if over(c, k) else 0.0 for c, k in trk])),
    }
    for arm, (yt, at) in arms.items():
        sc = fit_w(Xt, yt, at, wt, D, D)(Xe)
        res[arm] = {f"budget{int(b * 100):02d}": budget_metrics(sc, err, dol, b) for b in (0.05, 0.10)}
    return res


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
            print(f"{r['state']}: B0 any {r['B0']['lift_any']} over {r['B0']['lift_over']} | B1 10% prec {r['B1']['budget10']['precision']} "
                  f"dr {r['B1']['budget10']['dollar_recall']}", flush=True)
            (ROOT / "experiments/exp106_results.json").write_text(json.dumps(dict(sorted(out.items())), indent=1))


if __name__ == "__main__":
    main()
