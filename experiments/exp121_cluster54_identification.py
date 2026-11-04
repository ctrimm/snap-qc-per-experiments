"""Experiment 121 - identify the +$54 minimodel cluster.

exp117/exp118's reconstruction of the QC minimodel (FSBEN) is exact
except for a thin residual tail whose modal value is +$54 (28 cases
in the no-earnings slice, 9 in the earnings slice): the minimodel
pays $54 more than the statutory formula predicts from the case's own
verified inputs and FS deduction fields. $54 = 0.30 x $180, so a $180
deduction the formula here does not see is the standing hypothesis;
this experiment hunts the shared trait directly: rebuild both frames,
isolate the cluster, and scan the file's columns for a value whose
distribution in the cluster diverges from the frame baseline.

Writes experiments/exp121_results.json with the ranked scan; the
chronicle interprets the winner.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PATH = "/home/hatch/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
ALLOT = {1: 291, 2: 535, 3: 766, 4: 973}
TERR = ["Alaska", "Hawaii", "Guam", "Virgin Islands"]
DED = ["FSERNDED", "FSSTDDED", "FSSLTDED", "FSMEDDED", "FSDEPDED", "FSCSDED"]

df = pd.read_csv(PATH, low_memory=False)
df["_row"] = np.arange(len(df))
need = ["FSEARN", "FSUNEARN"] + DED
base = df[(df["CERTHHSZ"].between(1, 4)) & (df["SSI_CAP"] == 0)
          & (~df["STATENAME"].isin(TERR)) & (df[need].notna().all(axis=1))].copy()
E = base["FSEARN"].to_numpy(float)
U = base["FSUNEARN"].clip(lower=0).to_numpy(float)
deds = sum(base[c].to_numpy(float) for c in DED)
sizes = base["CERTHHSZ"].to_numpy(int)
allot = np.array([ALLOT[z] for z in sizes], float)
cont = allot - 0.30 * np.maximum(0.0, E + U - deds)
p = np.maximum(cont, 0.0)
p = np.where(sizes <= 2, np.maximum(p, 23.0), p)
pred = np.floor(p)
base["_pred"] = pred
base["_resid_fsben"] = base["FSBEN"].to_numpy(float) - pred
cluster = base[base["_resid_fsben"] == 54]
out = {"frame_n": int(len(base)), "cluster_n": int(len(cluster)),
       "cluster_by_earn": {"noearn": int((cluster["FSEARN"] == 0).sum()),
                           "earn": int((cluster["FSEARN"] > 0).sum())}}

# Scan: categorical-ish columns (<= 40 distinct values in the frame).
# Score = max over values of (cluster share - baseline share), with the
# value and counts reported for the top columns.
cluster_rows = set(cluster["_row"])
scan = []
skip = set(need) | {"FSBEN", "BENFIX", "RAWBEN", "HWGT", "HWGT_OLD", "FYWGT",
                    "FYWGT_OLD", "_pred", "_resid_fsben", "_row", "AMTERR"}
for col in base.columns:
    if col in skip:
        continue
    nun = base[col].nunique(dropna=True)
    if nun < 2 or nun > 40:
        continue
    ct = cluster[col].value_counts(normalize=True)
    bt = base[col].value_counts(normalize=True)
    best_val, best_lift = None, 0.0
    for v, share in ct.items():
        lift = share - bt.get(v, 0.0)
        if lift > best_lift:
            best_val, best_lift = v, float(lift)
    if best_val is not None:
        scan.append({"column": col, "value": str(best_val),
                     "cluster_share": float(ct[best_val]),
                     "baseline_share": float(bt.get(best_val, 0.0)),
                     "lift": best_lift,
                     "cluster_n_with_value": int((cluster[col] == best_val).sum())})
scan.sort(key=lambda r: -r["lift"])
out["scan_top15"] = scan[:15]

# Direct summaries of the usual suspects in the cluster
for col in ["STATENAME", "CERTHHSZ", "SUA1", "SUA2", "SHELCAP"]:
    if col in base.columns:
        out[f"cluster_{col}"] = {str(k): int(v) for k, v in
                                 cluster[col].value_counts().head(8).items()}
for col in ["FSDEPDED", "FSSLTDED", "FSMEDDED", "FSCSDED"]:
    out[f"cluster_{col}_summary"] = {
        "share_positive": float((cluster[col] > 0).mean()),
        "baseline_share_positive": float((base[col] > 0).mean()),
        "median": float(cluster[col].median())}

# Verification (added after the scan pointed at SHELDED / HOMELESS_DED):
# every cluster case carries HOMELESS_DED = 180 with FSSLTDED = 0, and
# 0.30 x 180 = 54 exactly. Test: add HOMELESS_DED to the shelter
# deduction and re-score the whole frame.
hd = base["HOMELESS_DED"].fillna(0).to_numpy(float)
deds_fix = deds + hd
cont_fix = allot - 0.30 * np.maximum(0.0, E + U - deds_fix)
pf = np.maximum(cont_fix, 0.0)
pf = np.where(sizes <= 2, np.maximum(pf, 23.0), pf)
resid_fix = base["FSBEN"].to_numpy(float) - np.floor(pf)
out["verification"] = {
    "frame_cases_with_homeless_ded_180": int((hd == 180).sum()),
    "their_residuals_before_fix": {str(int(k)): int(v) for k, v in
                                   pd.Series(base.loc[hd == 180, "_resid_fsben"]).value_counts().items()},
    "exact_share_before_fix": float((base["_resid_fsben"] == 0).mean()),
    "exact_share_after_fix": float((resid_fix == 0).mean()),
    "residual_+54_remaining_after_fix": int((resid_fix == 54).sum()),
}

Path(__file__).with_name("exp121_results.json").write_text(json.dumps(out, indent=2, default=str))
print(json.dumps(out, indent=2, default=str))
