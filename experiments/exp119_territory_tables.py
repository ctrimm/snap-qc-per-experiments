"""Experiment 119 - territory tables: recover the AK/HI/GU/VI allotment
schedules from their own QC slices.

exp117 excluded Alaska, Hawaii, Guam, and the Virgin Islands because
they use their own allotment tables (under mainland parameters their
reconstruction score was 0.0%). This experiment recovers those tables
from the FY2024 QC public file itself, sizes 1-8, no earnings:

- Allotment per size: among cases whose net income is <= 0 (unearned
  minus the case's FS deduction fields), the minimodel benefit equals
  the max allotment, so the modal FSBEN in that group is the table
  entry. Alaska is checked for multiple schedules (urban / rural).
- Standard deduction per territory: grid fit at rate 0.30 against
  FSBEN on the no-other-deductions sub-slice, using recovered
  allotments (the fit control that the shape is right).
- Reconstruction with recovered allotments + the case's own deduction
  fields vs FSBEN (T1) and vs the issued benefit RAWBEN (T3): the
  territories' own error surface.

Writes experiments/exp119_results.json.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PATH = "/home/hatch/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
TERRS = ["Alaska", "Hawaii", "Guam", "Virgin Islands"]

cols = ["CERTHHSZ", "FSEARN", "FSUNEARN", "FSSTDDED", "FSSLTDED",
        "FSMEDDED", "FSDEPDED", "FSCSDED", "FSBEN", "BENFIX", "RAWBEN",
        "STATENAME", "HWGT", "SSI_CAP"]
df = pd.read_csv(PATH, usecols=cols)
need = ["FSUNEARN", "FSSTDDED", "FSSLTDED", "FSMEDDED", "FSDEPDED", "FSCSDED"]
out = {}


def finish(cont, sizes):
    p = np.maximum(cont, 0.0)
    p = np.where(sizes <= 2, np.maximum(p, 23.0), p)
    return np.floor(p)


for terr in TERRS:
    s = df[(df["STATENAME"] == terr) & (df["CERTHHSZ"].between(1, 8))
           & (df["FSEARN"] == 0) & (df["SSI_CAP"] == 0)].copy()
    s = s[s[need].notna().all(axis=1)]
    res = {"n": int(len(s))}
    U = s["FSUNEARN"].clip(lower=0).to_numpy(float)
    ded = (s["FSSTDDED"] + s["FSSLTDED"] + s["FSMEDDED"] + s["FSDEPDED"]
           + s["FSCSDED"]).to_numpy(float)
    sizes = s["CERTHHSZ"].to_numpy(int)
    fs = s["FSBEN"].to_numpy(float)
    raw = s["RAWBEN"].to_numpy(float)
    net = U - ded

    # Allotment recovery: mode of FSBEN where net <= 0, per size
    allot = {}
    allot_detail = {}
    for z in range(1, 9):
        m = (sizes == z) & (net <= 0)
        if m.sum() >= 3:
            vals = Counter(fs[m]).most_common(3)
            allot[z] = int(vals[0][0])
            allot_detail[str(z)] = {"n_net_le_0": int(m.sum()),
                                    "top_values": [[int(k), int(v)] for k, v in vals]}
        else:
            allot_detail[str(z)] = {"n_net_le_0": int(m.sum()), "note": "thin"}
    res["recovered_allotments"] = {str(k): v for k, v in allot.items()}
    res["allotment_detail"] = allot_detail

    # Alaska schedule check: distinct modal clusters for size 1
    if terr == "Alaska":
        m = (sizes == 1) & (net <= 0)
        res["ak_size1_net_le_0_values"] = [[int(k), int(v)] for k, v in
                                           Counter(fs[m]).most_common(8)]

    if len(allot) >= 4:
        allot_v = np.array([allot.get(z, np.nan) for z in sizes], float)
        have = ~np.isnan(allot_v)
        pred = finish(allot_v - 0.30 * np.maximum(0.0, net), sizes)
        res["T1_reconstruction_FSBEN"] = float((pred[have] == fs[have]).mean())
        res["T3_vs_RAWBEN"] = float((pred[have] == raw[have]).mean())
        res["reconstruction_n"] = int(have.sum())

        # Standard deduction fit on the no-other-deductions sub-slice
        other = (s["FSSLTDED"] + s["FSMEDDED"] + s["FSDEPDED"]
                 + s["FSCSDED"]).to_numpy(float)
        sub = (other == 0) & have
        if sub.sum() >= 50:
            best = None
            for s_cand in range(150, 421):
                p = finish(allot_v[sub] - 0.30 * np.maximum(0.0, U[sub] - s_cand),
                           sizes[sub])
                m = float((p == fs[sub]).mean())
                if best is None or m > best[1]:
                    best = (s_cand, m)
            res["std_fit_vs_FSBEN"] = {"std": best[0], "match": best[1],
                                       "n": int(sub.sum())}
            best_r = None
            for s_cand in range(150, 421):
                p = finish(allot_v[sub] - 0.30 * np.maximum(0.0, U[sub] - s_cand),
                           sizes[sub])
                m = float((p == raw[sub]).mean())
                if best_r is None or m > best_r[1]:
                    best_r = (s_cand, m)
            res["std_fit_vs_RAWBEN"] = {"std": best_r[0], "match": best_r[1]}
    out[terr] = res

Path(__file__).with_name("exp119_results.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
