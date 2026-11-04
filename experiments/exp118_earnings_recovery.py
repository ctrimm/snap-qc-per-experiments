"""Experiment 118 - earnings cases: does the issued function treat
earned income the way the statute does?

exp117 covered the no-earnings slice and found the issued function
running statutory parameters ($198 / 0.30). This experiment extends the
frame to cases WITH earnings (mainland + DC, sizes 1-4, non-CAP), where
the earned-income deduction (20%, floored) and earnings-fact errors are
in play. Adjacent prior work: exp27 audited earned-income error
mechanics inside the generator; this experiment recovers the effective
earned treatment from real issued benefits (RAWBEN).

Tests mirror exp117: T1 reconstruction vs the QC minimodel (FSBEN),
T2 vs the corrected benefit (BENFIX), T3 vs the issued benefit (RAWBEN),
plus a joint fit of (standard deduction, earned-deduction structure)
on the sub-slice where no other deductions are in play - structure
candidates: floor(r * E) and smooth r * E for r in 0.10..0.30.

Writes experiments/exp118_results.json.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PATH = "/home/hatch/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
ALLOT = {1: 291, 2: 535, 3: 766, 4: 973}
TERR = ["Alaska", "Hawaii", "Guam", "Virgin Islands"]

cols = ["CERTHHSZ", "FSEARN", "FSUNEARN", "FSERNDED", "FSSTDDED", "FSSLTDED",
        "FSMEDDED", "FSDEPDED", "FSCSDED", "FSBEN", "BENFIX", "RAWBEN",
        "STATENAME", "HWGT", "SSI_CAP"]
df = pd.read_csv(PATH, usecols=cols)
s = df[(df["CERTHHSZ"].between(1, 4)) & (df["FSEARN"] > 0)
       & (df["SSI_CAP"] == 0) & (~df["STATENAME"].isin(TERR))].copy()
out = {"slice_n_before_complete": int(len(s))}
need = ["FSEARN", "FSUNEARN", "FSERNDED", "FSSTDDED", "FSSLTDED",
        "FSMEDDED", "FSDEPDED", "FSCSDED"]
s = s[s[need].notna().all(axis=1)].copy()
out["slice_n"] = int(len(s))

E = s["FSEARN"].to_numpy(float)
U = s["FSUNEARN"].clip(lower=0).to_numpy(float)
deds = (s["FSERNDED"] + s["FSSTDDED"] + s["FSSLTDED"] + s["FSMEDDED"]
        + s["FSDEPDED"] + s["FSCSDED"]).to_numpy(float)
sizes = s["CERTHHSZ"].to_numpy(int)
allot = np.array([ALLOT[z] for z in sizes], float)


def finish(cont, sizes):
    p = np.maximum(cont, 0.0)
    p = np.where(sizes <= 2, np.maximum(p, 23.0), p)
    return np.floor(p)


pred = finish(allot - 0.30 * np.maximum(0.0, E + U - deds), sizes)


def compare(target, name):
    r = target - pred
    exact = r == 0
    w = s["HWGT"].to_numpy(float)
    out[name] = {"exact_share": float(exact.mean()),
                 "exact_share_weighted": float(np.average(exact, weights=w)),
                 "share_over": float((r > 0).mean()),
                 "share_under": float((r < 0).mean()),
                 "top_residuals": [[int(k), int(v)] for k, v in
                                   Counter(r[~exact]).most_common(6)]}


compare(s["FSBEN"].to_numpy(float), "T1_pred_vs_FSBEN")
compare(s["BENFIX"].to_numpy(float), "T2_pred_vs_BENFIX")
compare(s["RAWBEN"].to_numpy(float), "T3_pred_vs_RAWBEN")

# Per-state T3
st = s["STATENAME"].to_numpy()
raw = s["RAWBEN"].to_numpy(float)
rows = []
for nm in np.unique(st):
    m = st == nm
    if m.sum() >= 150:
        rows.append({"state": str(nm), "n": int(m.sum()),
                     "T3_exact": float((raw[m] == pred[m]).mean())})
rows.sort(key=lambda r: r["T3_exact"])
out["states_T3"] = rows

# Earned-treatment fit: sub-slice with no shelter/medical/depcare/CS deds
other = (s["FSSLTDED"] + s["FSMEDDED"] + s["FSDEPDED"] + s["FSCSDED"]).to_numpy(float)
sub = other == 0
out["fit_subslice_n"] = int(sub.sum())
Es, Us, As, Zs = E[sub], U[sub], allot[sub], sizes[sub]


def fit(target):
    tt = target[sub]
    results = []
    for s_cand in range(150, 251, 2):
        for kind in ("floor", "smooth"):
            for r100 in range(10, 31):
                r = r100 / 100.0
                g = np.floor(r * Es) if kind == "floor" else r * Es
                p = finish(As - 0.30 * np.maximum(0.0, Es + Us - g - s_cand), Zs)
                results.append((float((p == tt).mean()), s_cand, kind, r))
    results.sort(reverse=True)
    best = results[0]
    return {"std_fit": best[1], "earn_kind": best[2], "earn_rate": best[3],
            "match": best[0],
            "runner_up": {"std": results[1][1], "earn_kind": results[1][2],
                          "earn_rate": results[1][3], "match": results[1][0]}}


out["fit_vs_FSBEN_control"] = fit(s["FSBEN"].to_numpy(float))
out["fit_vs_BENFIX"] = fit(s["BENFIX"].to_numpy(float))
out["fit_vs_RAWBEN_target"] = fit(s["RAWBEN"].to_numpy(float))

Path(__file__).with_name("exp118_results.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
