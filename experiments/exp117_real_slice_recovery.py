"""Experiment 117 - real-data slice recovery on the FY2024 QC public file.

Semantics (FY2024 tech doc, Mathematica): RAWBEN = reported benefit the
unit received (the issued benefit). FSBEN = benefit calculated by the QC
minimodel from QC-verified case data. BENFIX = FSBEN adjusted for the
errors the QC reviewer found (the corrected benefit). FS*DED fields are
the minimodel's calculated deductions from the verified data.

Slice: CERTHHSZ in 1..4, FSEARN == 0 (no earnings -> no earned-income
deduction in play), SSI_CAP == 0 (CAP cases get standard benefits, not
the formula).

Tests:
  T1 reconstruction: statutory prediction from each case's own verified
     inputs + FS deduction fields vs FSBEN. If the minimodel is this
     formula with FY2024 parameters, agreement should be ~100%.
  T2 same prediction vs BENFIX (reviewer-adjusted truth).
  T3 issued function: prediction vs RAWBEN - residuals are the agency
     error surface for this slice. Plus an effective-parameter fit on
     the no-other-deductions sub-slice (grid over the standard
     deduction and the benefit rate) run against both FSBEN (control:
     should return the statutory values) and RAWBEN (target).

Writes experiments/exp117_results.json.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PATH = "/home/hatch/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
ALLOT = {1: 291, 2: 535, 3: 766, 4: 973}
STD = {1: 198, 2: 198, 3: 198, 4: 208}

cols = ["CERTHHSZ", "FSEARN", "FSUNEARN", "FSSTDDED", "FSSLTDED",
        "FSMEDDED", "FSDEPDED", "FSCSDED", "FSBEN", "BENFIX", "RAWBEN",
        "STATUS", "STATE", "STATENAME", "HWGT", "SSI_CAP"]
df = pd.read_csv(PATH, usecols=cols)
out = {"n_file": int(len(df))}

s_all = df[(df["CERTHHSZ"].between(1, 4)) & (df["FSEARN"] == 0)
           & (df["SSI_CAP"] == 0)].copy()
out["slice_n_all_areas"] = int(len(s_all))
TERR = ["Alaska", "Hawaii", "Guam", "Virgin Islands"]
out["excluded_territory_cases"] = int(s_all["STATENAME"].isin(TERR).sum())
s = s_all[~s_all["STATENAME"].isin(TERR)].copy()  # AK/HI/GU/VI use their own
# allotment tables (T1 exact share there is 0.0% under mainland parameters -
# the formula is the same shape, the tables are different law)
out["slice_n"] = int(len(s))
out["slice_n_by_size"] = {int(k): int(v) for k, v in s["CERTHHSZ"].value_counts().items()}

_pred_ok = (s["FSUNEARN"].notna() & s["FSSTDDED"].notna() & s["FSSLTDED"].notna()
            & s["FSMEDDED"].notna() & s["FSDEPDED"].notna() & s["FSCSDED"].notna())
out["dropped_nan_predictors"] = int((~_pred_ok).sum())
s = s[_pred_ok].copy()
U = s["FSUNEARN"].clip(lower=0).to_numpy(float)
deds = (s["FSSTDDED"] + s["FSSLTDED"] + s["FSMEDDED"] + s["FSDEPDED"]
        + s["FSCSDED"]).to_numpy(float)
sizes = s["CERTHHSZ"].to_numpy(int)
allot = np.array([ALLOT[z] for z in sizes], dtype=float)
net = np.maximum(0.0, U - deds)
cont = allot - 0.30 * net
_p = np.maximum(cont, 0.0)
_p = np.where(sizes <= 2, np.maximum(_p, 23.0), _p)
pred = np.floor(_p)


def compare(target: np.ndarray, name: str) -> dict:
    r = target - pred
    exact = r == 0
    res = {"exact_share": float(exact.mean()),
           "n": int(len(r)),
           "mean_signed_resid": float(r.mean()),
           "share_overissued_vs_pred": float((r > 0).mean()),
           "share_underissued_vs_pred": float((r < 0).mean()),
           "top_residuals": [[int(k), int(v)] for k, v in
                             Counter(r[~exact]).most_common(8)]}
    w = s["HWGT"].to_numpy(float)
    res["exact_share_weighted"] = float(np.average(exact, weights=w))
    out[name] = res
    return res


compare(s["FSBEN"].to_numpy(float), "T1_pred_vs_FSBEN")
compare(s["BENFIX"].to_numpy(float), "T2_pred_vs_BENFIX")
compare(s["RAWBEN"].to_numpy(float), "T3_pred_vs_RAWBEN")

# FSBEN vs BENFIX (reviewer adjustments beyond the minimodel)
fb = (s["BENFIX"] - s["FSBEN"]).to_numpy(float)
out["FSBEN_vs_BENFIX"] = {"differ_share": float((fb != 0).mean()),
                          "mean_abs": float(np.abs(fb[fb != 0]).mean()) if (fb != 0).any() else 0.0}

# Per-size T1/T3
for z in (1, 2, 3, 4):
    m = sizes == z
    if m.sum() < 50:
        continue
    out[f"size{z}"] = {
        "n": int(m.sum()),
        "T1_exact": float((s['FSBEN'].to_numpy(float)[m] == pred[m]).mean()),
        "T3_exact": float((s['RAWBEN'].to_numpy(float)[m] == pred[m]).mean()),
    }

# Effective-parameter fit, no-other-deductions sub-slice
other = (s["FSSLTDED"] + s["FSMEDDED"] + s["FSDEPDED"] + s["FSCSDED"]).to_numpy(float)
sub = other == 0
out["fit_subslice_n"] = int(sub.sum())

def fit(target: np.ndarray):
    Uu, aa, zz = U[sub], allot[sub], sizes[sub]
    tt = target[sub]
    def predict(rate, s_cand):
        c = aa - rate * np.maximum(0.0, Uu - s_cand)
        p = np.maximum(c, 0.0)
        p = np.where(zz <= 2, np.maximum(p, 23.0), p)
        return np.floor(p)
    best = None
    for s_cand in range(120, 281):
        m = float((predict(0.30, s_cand) == tt).mean())
        if best is None or m > best[1]:
            best = (s_cand, m)
    s_best, m_best = best
    best_r = None
    for r100 in range(24, 37):
        r_cand = r100 / 100.0
        m = float((predict(r_cand, s_best) == tt).mean())
        if best_r is None or m > best_r[1]:
            best_r = (r_cand, m)
    return {"std_fit": s_best, "std_fit_match": m_best,
            "rate_fit": best_r[0], "rate_fit_match": best_r[1]}

out["fit_vs_FSBEN_control"] = fit(s["FSBEN"].to_numpy(float))
out["fit_vs_RAWBEN_target"] = fit(s["RAWBEN"].to_numpy(float))
out["fit_vs_BENFIX"] = fit(s["BENFIX"].to_numpy(float))

# Per-state T3 (states with >= 300 slice cases): the geographic surface
st = s["STATENAME"].to_numpy()
raw = s["RAWBEN"].to_numpy(float)
rows = []
for name in np.unique(st):
    m = st == name
    if m.sum() >= 300:
        rows.append({"state": str(name), "n": int(m.sum()),
                     "T3_exact": float((raw[m] == pred[m]).mean())})
rows.sort(key=lambda r: r["T3_exact"])
out["states_T3"] = rows

Path(__file__).with_name("exp117_results.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
