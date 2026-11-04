"""Experiment 52b - real-data scoping audit for formula recovery.

Question: does the FY2024 QC public-use file contain what black-box
recovery would need - case circumstances, the issued benefit, and the
QC-corrected benefit - densely enough that a statutory kink is visible
in real data?

Reads ~/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv.
Prints a JSON summary; the chronicle interprets it.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

PATH = "/home/hatch/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

df_head = pd.read_csv(PATH, nrows=0)
cols = list(df_head.columns)
fs_ded = [c for c in cols if c.startswith("FS") and ("DED" in c or "SHELT" in c)]
print("FS deduction/shelter columns:", fs_ded)

use = ["CERTHHSZ", "FSEARN", "FSUNEARN", "FSBEN", "BENFIX", "RAWBEN"]
use = [c for c in use if c in cols]
df = pd.read_csv(PATH, usecols=use)
out = {"n_rows": int(len(df)), "columns_used": use}

# Case-level error signal: issued vs QC-corrected benefit
diff = (df["FSBEN"] - df["BENFIX"]).abs()
out["cases_benfix_ne_fsbens"] = int((diff > 0).sum())
out["share_cases_with_correction"] = float((diff > 0).mean())
out["mean_abs_correction_where_diff"] = float(diff[diff > 0].mean()) if (diff > 0).any() else 0.0

# Slice: size 1, no earnings. Statutory (FY2024, harness params) lower
# envelope with no deductions beyond standard: 291 - 0.3*max(0, U-198),
# floored at the $23 minimum. Shelter/medical/depcare deductions only
# push real cases ABOVE this line, so the line should bound the slice
# from below and the low percentiles should track it.
s = df[(df["CERTHHSZ"] == 1) & (df["FSEARN"] == 0)].copy()
out["slice_size1_noearn_n"] = int(len(s))

def statute(u):
    return np.maximum(291 - 0.30 * np.maximum(0.0, u - 198), 23)

bins = [(0, 198), (199, 400), (401, 700), (701, 1000), (1001, 1500)]
rows = []
for lo, hi in bins:
    g = s[(s["FSUNEARN"] >= lo) & (s["FSUNEARN"] <= hi)]
    if len(g) < 30:
        rows.append({"bin": [lo, hi], "n": int(len(g)), "note": "thin"})
        continue
    pred_mid = float(statute((lo + hi) / 2))
    rows.append({
        "bin": [lo, hi], "n": int(len(g)),
        "fsben_p10": float(g["FSBEN"].quantile(0.10)),
        "fsben_median": float(g["FSBEN"].median()),
        "statute_at_bin_mid": pred_mid,
        "share_below_statute_minus_1": float((g["FSBEN"] < statute(g["FSUNEARN"]) - 1).mean()),
    })
out["slice_bins"] = rows

# Density of other simple slices recovery would want
for size in (1, 2, 3, 4):
    out[f"n_size{size}_noearn"] = int(((df["CERTHHSZ"] == size) & (df["FSEARN"] == 0)).sum())

print(json.dumps(out, indent=2))
from pathlib import Path
Path(__file__).with_name("exp116b_qc_audit_results.json").write_text(json.dumps(out, indent=2))
