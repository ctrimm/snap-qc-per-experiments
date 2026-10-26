"""Exp 109 — our leak-free ranker on giannella's rebuilt pre-review inputs vs the reviewer-recorded inputs, and vs
their lists (pre-registered in exp109_rebuilt_inputs.md).

Usage: python3 experiments/exp109_rebuilt_inputs.py --frame /path/to/exp109_frame.parquet [--workers 8]
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
RAW = ROOT.parent / "snap-qc-data/raw"
BENCH = ROOT.parent / "giannella-snap_qc/methods/v250_benchmark_2024/v250_benchmark_2024.csv"
TOL = {2022: 48, 2023: 54, 2024: 56}
# our QC field -> giannella frame column (rebuilt, nominal); several frame columns are renamed late in their script
REBUILT = {"CERTHHSZ": ["cert_HH_size_FS_n", "rawusize"], "RAWHSIZE": ["people_in_HH_n", "ctprhh"],
           "RAWGROSS": ["rawgrinc", "rawgross"], "RAWNET": ["rawnet_capped"], "RAWERND": ["rawernded"],
           "SHELDED": ["rawsltded"], "RENT": ["rawrent"], "UTIL": ["utilities", "rawutil"],
           "FSMEDEXP": ["medical_deductions", "rawmedded"], "FSDEPDED": ["rawdepded"], "FSCSEXP": ["rawcsded"],
           "BENMAX": ["maximum_benefit_for_HH_size", "rawbenmax"]}
_G = {}


def fnum(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def build(frame_path):
    """Rows of giannella's frame for FY2022-24, each with R and B feature vectors, label, dollars, over flag."""
    import pandas as pd
    import exp80_state_context as X80
    fr = pd.read_parquet(frame_path)
    cols = {}
    for f, cands in REBUILT.items():
        hit = [c for c in cands if c in fr.columns]
        assert hit, (f, cands)
        cols[f] = hit[0]
    fr = fr[fr["fiscal_year"].astype(int).isin([2022, 2023, 2024])]
    fr_idx = {(int(r.fiscal_year), str(int(r.hhldno))): r for r in fr.itertuples(index=False)}
    rows = []
    for fy in (2022, 2023, 2024):
        path = next(iter((RAW / f"qcfy{fy}_csv").glob("*.csv")))
        with open(path, newline="", encoding="latin-1") as fh:
            for row in csv.DictReader(fh):
                key = (fy, row["HHLDNO"].strip())
                g = fr_idx.get(key)
                if g is None:
                    continue
                reb = dict(row)
                for f, c in cols.items():
                    reb[f] = getattr(g, c)
                d = abs(fnum(row["RAWBEN"]) - fnum(row["FSBEN"]))
                rows.append({"fy": fy, "code": row["STATE"].strip(), "name": (row.get("STATENAME") or "").strip(),
                             "R": X80.context_features(row), "B": X80.context_features(reb),
                             "any": int(row["STATUS"].strip() != "1"), "amterr": fnum(row["AMTERR"]),
                             "over": int(d > TOL[fy]), "dollars_over": d if d > TOL[fy] else 0.0})
    return rows, len(fr), cols


def init(rows):
    _G["rows"] = rows


def budget(score, err, dol, b):
    k = int(round(b * len(score))); idx = np.argsort(-score, kind="stable")[:k]
    return {"n_te": len(score), "n_flagged": k, "precision": round(float(err[idx].mean()), 4) if k else 0.0,
            "base_rate": round(float(err.mean()), 4), "dollar_recall": round(float(dol[idx].sum() / max(dol.sum(), 1e-9)), 4)}


def run_one(job):
    code, variant = job
    import exp56_pa_tuned_classifier as E56
    from exp75_small_state_pooling import fit_w
    rows = _G["rows"]; D = E56.DEFAULT; wown = 10.0 if variant == "C_ctx" else 1.0
    tr = [r for r in rows if r["fy"] in (2022, 2023)]; te = [r for r in rows if r["fy"] == 2024 and r["code"] == code]
    w = np.array([wown if r["code"] == code else 1.0 for r in tr])
    err = np.array([r["over"] for r in te]); dol = np.array([r["dollars_over"] for r in te])
    out = {"code": code, "variant": variant}
    for arm, feat, lab in (("R", "R", "any"), ("B", "B", "any"), ("B_over", "B", "over")):
        X = np.array([r[feat] for r in tr]); Xe = np.array([r[feat] for r in te])
        y = np.array([r[lab] for r in tr]); a = np.array([r["amterr"] if lab == "any" else r["dollars_over"] for r in tr])
        s = fit_w(X, y, a, w, D, D)(Xe)
        out[arm] = {f"budget{int(b * 100):02d}": budget(s, err, dol, b) for b in (0.05, 0.10)}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--frame", required=True); ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    import exp58_agency_rankers as E58
    assert E58.LEAKFREE
    rows, n_frame, cols = build(args.frame)
    print(f"frame rows (all years) {n_frame}; linked FY2022-24 rows {len(rows)}; columns {cols}", flush=True)
    adopted = {}
    for fn in ("exp80_results.json", "exp82_results.json"):
        for k, v in json.loads((ROOT / "experiments" / fn).read_text()).items():
            adopted[k] = v["adopted"]
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    ab_of = {hold[ab]["code"]: ab for ab in hold}
    names = {}
    for r in rows:
        names.setdefault(r["code"], r["name"])
    bench = {(r["state"], round(float(r["budget"]), 2)): r for r in csv.DictReader(open(BENCH))}
    norm = lambda s: " ".join(w.capitalize() if w.lower() != "of" else "of" for w in s.split())  # noqa: E731
    codes = [c for c in sorted(names) if (norm(names[c]), 0.05) in bench and c in ab_of]
    jobs = [(c, adopted[ab_of[c]]) for c in codes]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    res = {}
    with get_context("fork").Pool(args.workers, initializer=init, initargs=(rows,)) as pool:
        for r in pool.imap_unordered(run_one, jobs):
            ab = ab_of[r["code"]]; t = {b: bench[(norm(names[r["code"]]), b)] for b in (0.05, 0.10)}
            r["giannella"] = {f"budget{int(b * 100):02d}": {"n_te": int(float(t[b]["n_te"])), "precision": float(t[b]["precision"]),
                                                            "dollar_recall": float(t[b]["dollar_recall"])} for b in t}
            res[ab] = r
            print(ab, "n", r["B"]["budget05"]["n_te"], "vs", r["giannella"]["budget05"]["n_te"],
                  "| dr10 R", r["R"]["budget10"]["dollar_recall"], "B", r["B"]["budget10"]["dollar_recall"],
                  "G", r["giannella"]["budget10"]["dollar_recall"], flush=True)
    res = dict(sorted(res.items()))
    gate = sum(r["B"]["budget05"]["n_te"] == r["giannella"]["budget05"]["n_te"] for r in res.values())
    summ = {"states": len(res), "gate_n_te_equal": gate}
    for b in ("budget05", "budget10"):
        for m in ("precision", "dollar_recall"):
            v = {a: [r[a][b][m] for r in res.values()] for a in ("R", "B", "B_over", "giannella")}
            summ[f"{b}_{m}"] = {
                "median": {a: round(st.median(x), 4) for a, x in v.items()},
                "R_minus_B_median_paired": round(st.median(np.subtract(v["R"], v["B"])), 4),
                "B_vs_giannella_higher_lower": [int(sum(x > y for x, y in zip(v["B"], v["giannella"]))),
                                                int(sum(x < y for x, y in zip(v["B"], v["giannella"])))],
                "B_vs_giannella_median_paired": round(st.median(np.subtract(v["B"], v["giannella"])), 4),
                "B_over_vs_giannella_higher_lower": [int(sum(x > y for x, y in zip(v["B_over"], v["giannella"]))),
                                                     int(sum(x < y for x, y in zip(v["B_over"], v["giannella"])))]}
    print(json.dumps(summ, indent=1))
    E58.results_path("exp109_results.json").write_text(json.dumps({"summary": summ, "columns": cols, "states": res}, indent=1))


if __name__ == "__main__":
    main()
