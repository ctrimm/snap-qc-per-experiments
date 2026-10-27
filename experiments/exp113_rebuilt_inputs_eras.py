"""Exp 113 — our ranker on giannella's rebuilt pre-review inputs, three test windows, CPI and nominal frames, against
their delivery lists (pre-registered in exp113_rebuilt_inputs_eras.md).

Usage: python3 experiments/exp113_rebuilt_inputs_eras.py --cpi CPI.parquet --nominal NOMINAL.parquet [--workers 8]
"""
import argparse
import csv
import json
import os
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
G_OUT = ROOT.parent / "giannella-snap_qc/methods/cpi_inflate_test/out"
TOL = {2017: 38, 2018: 37, 2019: 37, 2022: 48, 2023: 54, 2024: 56}  # giannella additional_data/year_data.csv
WINDOWS = {"W1": ((2022, 2023), 2024, "2223_24"), "W2": ((2017, 2018), 2019, "1718_19"), "W3": ((2017, 2018, 2019), 2022, "1719_22")}
REBUILT = {"CERTHHSZ": ["cert_HH_size_FS_n", "rawusize"], "RAWHSIZE": ["people_in_HH_n", "ctprhh"],
           "RAWGROSS": ["rawgrinc", "rawgross"], "RAWNET": ["rawnet_capped"], "RAWERND": ["rawernded"],
           "SHELDED": ["rawsltded"], "RENT": ["rawrent"], "UTIL": ["utilities", "rawutil"],
           "FSMEDEXP": ["medical_deductions", "rawmedded"], "FSDEPDED": ["rawdepded"], "FSCSEXP": ["rawcsded"],
           "BENMAX": ["maximum_benefit_for_HH_size", "rawbenmax"], "SUA1": ["sua1"], "HOMEDED": ["homeded"]}
_G = {}


def build(path):
    import pandas as pd
    import exp80_state_context as X80
    fr = pd.read_parquet(path)
    cols = {f: next(c for c in cands if c in fr.columns) for f, cands in REBUILT.items()}
    out = []
    for r in fr.itertuples(index=False):
        row = {f: ("" if v != v else (str(int(v)) if f in ("SUA1", "HOMEDED") else v)) for f, v in ((f, getattr(r, c)) for f, c in cols.items())}
        fy = int(r.fiscal_year); status = int(r.status) if r.status == r.status else 1; amt = abs(float(r.amterr or 0))
        ov = str(r.over_threshold) == "1"
        out.append({"fy": fy, "state": r.state_name, "x": X80.context_features(row),
                    "y": int(status in (2, 3) and amt > TOL[fy]), "a": amt if (status in (2, 3) and amt > TOL[fy]) else 0.0,
                    "ev_err": int(ov), "ev_dol": float(r.total_error_amount or 0) if ov else 0.0})
    return out, cols


def init(frames):
    _G["frames"] = frames


def budget(score, err, dol, b):
    k = int(round(b * len(score))); idx = np.argsort(-score, kind="stable")[:k]
    return {"n_te": len(score), "n_flagged": k, "precision": round(float(err[idx].mean()), 4) if k else 0.0,
            "dollar_recall": round(float(dol[idx].sum() / max(dol.sum(), 1e-9)), 4)}


def run_one(job):
    state, variant, frame_key, win = job
    import exp56_pa_tuned_classifier as E56
    from exp75_small_state_pooling import fit_w
    rows = _G["frames"][frame_key]; tr_years, te_year, _ = WINDOWS[win]
    wown = 10.0 if variant == "C_ctx" else 1.0
    tr = [r for r in rows if r["fy"] in tr_years]; te = [r for r in rows if r["fy"] == te_year and r["state"] == state]
    X = np.array([r["x"] for r in tr]); y = np.array([r["y"] for r in tr]); a = np.array([r["a"] for r in tr])
    w = np.array([wown if r["state"] == state else 1.0 for r in tr])
    s = fit_w(X, y, a, w, E56.DEFAULT, E56.DEFAULT)(np.array([r["x"] for r in te]))
    err = np.array([r["ev_err"] for r in te]); dol = np.array([r["ev_dol"] for r in te])
    k20 = int(round(0.2 * len(te))); idx = np.argsort(-s, kind="stable")[:k20]
    return {"state": state, "frame": frame_key, "window": win,
            "budget05": budget(s, err, dol, 0.05), "budget10": budget(s, err, dol, 0.10),
            "top20_dollar_lift": round(float(dol[idx].sum() / max(dol.sum() * 0.2, 1e-9)), 3)}


def theirs(arm, tag, seed2=False):
    p = G_OUT / f"lists_{tag}_{arm}{'_seed2' if seed2 else ''}.csv"
    return {(r["state"], round(float(r["budget"]), 2)): r for r in csv.DictReader(open(p))}


def paired(ours, them):
    d = [o - t for o, t in zip(ours, them)]
    return {"ours_median": round(st.median(ours), 4), "theirs_median": round(st.median(them), 4),
            "median_diff": round(st.median(d), 4), "mean_diff": round(st.mean(d), 4),
            "helped": sum(x > 0.05 for x in d), "harmed": sum(x < -0.05 for x in d), "higher": sum(x > 0 for x in d), "n": len(d)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cpi", required=True); ap.add_argument("--nominal", required=True)
    ap.add_argument("--workers", type=int, default=8); args = ap.parse_args()
    import exp58_agency_rankers as E58
    from exp69_cost_share_scenarios import NAME_TO_USPS
    assert E58.LEAKFREE and E58.OFFICIAL
    frames = {}
    for key, path in (("cpi", args.cpi), ("nominal", args.nominal)):
        frames[key], cols = build(path)
        print(key, len(frames[key]), "rows; columns", cols, flush=True)
    adopted = {}
    for fn in ("exp80_results.json", "exp82_results.json"):
        for k, v in json.loads((ROOT / "experiments" / fn).read_text()).items():
            adopted[k] = v["adopted"]
    usps = {" ".join(w.capitalize() if w != "OF" else "of" for w in k.split()): v for k, v in NAME_TO_USPS.items()}
    states = sorted({r["state"] for r in frames["cpi"]})
    jobs = [(s, adopted[usps[s]], f, w) for s in states for f in ("cpi", "nominal") for w in WINDOWS]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    res = []
    with get_context("fork").Pool(args.workers, initializer=init, initargs=(frames,)) as pool:
        for i, r in enumerate(pool.imap_unordered(run_one, jobs)):
            res.append(r)
            if i % 25 == 0:
                print(f"{i + 1}/{len(jobs)}", flush=True)
    summary = {}
    gate_bad = []
    for f in ("cpi", "nominal"):
        for w, (_, _, tag) in WINDOWS.items():
            R = {r["state"]: r for r in res if r["frame"] == f and r["window"] == w}
            T1, T2 = theirs(f, tag), theirs(f, tag, seed2=True)
            out = {"top20_dollar_lift_median": round(st.median(r["top20_dollar_lift"] for r in R.values()), 3),
                   "top20_at_2x": sum(r["top20_dollar_lift"] >= 2.0 for r in R.values()), "n_states": len(R)}
            for b, bk in ((0.05, "budget05"), (0.10, "budget10")):
                ss = [s for s in sorted(R) if (s, b) in T1]
                for s in ss:
                    if R[s][bk]["n_te"] != int(float(T1[(s, b)]["n_te"])):
                        gate_bad.append((f, w, s, b, R[s][bk]["n_te"], T1[(s, b)]["n_te"]))
                for m in ("precision", "dollar_recall"):
                    o = [R[s][bk][m] for s in ss]
                    out[f"{bk}_{m}"] = paired(o, [float(T1[(s, b)][m]) for s in ss])
                    out[f"{bk}_{m}"]["vs_seed2"] = paired(o, [float(T2[(s, b)][m]) for s in ss if (s, b) in T2])["median_diff"]
            summary[f"{f}_{w}"] = out
            print(f, w, json.dumps(out), flush=True)
    summary["gate_mismatches"] = gate_bad[:20]; summary["gate_mismatch_count"] = len(gate_bad)
    print("gate mismatches:", len(gate_bad), gate_bad[:5])
    E58.results_path("exp113_results.json").write_text(json.dumps({"summary": summary, "states": res}, indent=1))


if __name__ == "__main__":
    main()
