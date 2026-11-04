"""Experiment 122 - Alaska schedule assignment.

exp119 recovered Alaska's three allotment schedules (Urban / Rural 1 /
Rural 2) as benefit clusters but could not assign households to
schedules - the fields it used carry no geography below the state.
This experiment scans the full public file for a field that separates
the clusters: among Alaska size-1 cases with net income <= 0, the
benefit is the schedule's size-1 allotment (374 / 477 / 581), so any
column whose values partition those three values cleanly is the
assignment field. If a separator is found, per-schedule tables are
recovered and the reconstruction is rerun with assignment. If none
is found, per-schedule tables are still recovered as clusters for
every size where the data shows them, with schedule shares.

Writes experiments/exp122_results.json.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PATH = "/home/hatch/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
DED = ["FSSTDDED", "FSSLTDED", "FSMEDDED", "FSDEPDED", "FSCSDED"]

df = pd.read_csv(PATH, low_memory=False)
need = ["FSEARN", "FSUNEARN"] + DED
ak = df[(df["STATENAME"] == "Alaska") & (df["SSI_CAP"] == 0)
        & (df["FSEARN"] == 0)
        & (df[need].notna().all(axis=1))].copy()
U = ak["FSUNEARN"].clip(lower=0).to_numpy(float)
ded = sum(ak[c].to_numpy(float) for c in DED)
ak["_net"] = U - ded
ak["_fsben"] = ak["FSBEN"].to_numpy(float)

out = {"ak_n": int(len(ak))}

# Separation scan on size-1, net <= 0, NO EARNINGS (benefit == schedule
# allotment). Outcome columns (BENFIX/RAWBEN/AMTERR) are excluded: an
# early pass that left them in "found" BENFIX, a restatement of the
# answer. BENMAX / MINIMUM_BEN are parameter lookups, not outcomes,
# and stay in.
probe = ak[(ak["CERTHHSZ"] == 1) & (ak["_net"] <= 0) & (ak["FSEARN"] == 0)]
plateau = probe["_fsben"]
out["probe_n"] = int(len(probe))
out["probe_plateau_values"] = {str(int(k)): int(v) for k, v in
                               Counter(plateau).most_common()}
maj = plateau.mode().iloc[0]
scan = []
for col in ak.columns:
    if col.startswith(("FS", "_")) or col in ("STATENAME", "BENFIX", "RAWBEN", "AMTERR"):
        continue
    sub = probe[col]
    if sub.nunique(dropna=True) < 2 or sub.nunique(dropna=True) > 25:
        continue
    # purity: for each column value, the modal plateau; weighted share
    pure, tot = 0, 0
    for v, g in probe.groupby(col)["_fsben"]:
        pure += Counter(g).most_common(1)[0][1]
        tot += len(g)
    if tot >= 30:
        scan.append({"column": col, "purity": pure / tot, "n": int(tot),
                     "n_values": int(sub.nunique(dropna=True))})
scan.sort(key=lambda r: -r["purity"])
out["separation_scan_top10"] = scan[:10]

# Cluster tables per size (all sizes 1-8, no earnings restriction beyond
# the frame; net <= 0 groups)
tables = {}
for z in range(1, 9):
    g = ak[(ak["CERTHHSZ"] == z) & (ak["_net"] <= 0)]
    vals = [[int(k), int(v)] for k, v in Counter(g["_fsben"]).most_common(6)
            if v >= 2]
    tables[str(z)] = {"n_net_le_0": int(len(g)), "plateau_clusters": vals}
out["ak_plateau_clusters_by_size"] = tables

# If a near-perfect separator exists, reconstruct with assignment
winner = scan[0] if scan and scan[0]["purity"] >= 0.97 else None
out["separator_found"] = winner["column"] if winner else None

# BENMAX analysis: the file carries each case's maximum allotment as a
# parameter lookup. If BENMAX == FSBEN on every net <= 0 case, it is the
# schedule fingerprint: assign each case the schedule whose recovered
# table value at its size equals its BENMAX, then reconstruct with the
# per-schedule std fit (grid, rate 0.30, as in exp119).
if winner and winner["column"] == "BENMAX":
    nz = ak[ak["_net"] <= 0]
    out["benmax_equals_fsben_at_net_le_0"] = float((nz["BENMAX"] == nz["_fsben"]).mean())
    out["benmax_values_by_size"] = {
        str(z): {str(int(k)): int(v) for k, v in
                 Counter(ak[ak["CERTHHSZ"] == z]["BENMAX"]).most_common()}
        for z in range(1, 9)}
    URBAN = {1: 374, 2: 686, 3: 983, 4: 1248, 5: 1482, 6: 1778}
    RURAL2 = {1: 581, 2: 1065, 3: 1525, 4: 1937, 5: 2300, 6: 2760}

    def schedule(row):
        b, z = row["BENMAX"], int(row["CERTHHSZ"])
        if URBAN.get(z) == b:
            return "Urban"
        if RURAL2.get(z) == b:
            return "Rural 2"
        return "Rural 1 (by elimination)"

    ak["_sched"] = ak.apply(schedule, axis=1)
    out["schedule_shares_full_frame"] = {k: int(v) for k, v in
                                         Counter(ak["_sched"]).items()}
    UU = ak["FSUNEARN"].clip(lower=0).to_numpy(float)
    other = (ak["FSSLTDED"] + ak["FSMEDDED"] + ak["FSDEPDED"]
             + ak["FSCSDED"]).to_numpy(float)
    fsben = ak["_fsben"].to_numpy(float)
    allot_c = ak["BENMAX"].to_numpy(float)

    def reconstruct(std_map):
        std = ak["_sched"].map(std_map).to_numpy(float)
        cont = allot_c - 0.30 * np.maximum(0.0, UU - (std + other))
        p = np.maximum(cont, 0.0)
        small = ak["CERTHHSZ"].to_numpy(int) <= 2
        p = np.where(small, np.maximum(p, ak["MINIMUM_BEN"].to_numpy(float)), p)
        return np.floor(p)

    def fit_std(mask):
        best, best_exact = None, -1.0
        for cand in range(150, 451):
            std_map = {"Urban": cand, "Rural 1 (by elimination)": cand, "Rural 2": cand}
            std = np.where(mask, cand, 338.0)
            cont = allot_c - 0.30 * np.maximum(0.0, UU - (std + other))
            p = np.maximum(cont, 0.0)
            small = ak["CERTHHSZ"].to_numpy(int) <= 2
            p = np.where(small, np.maximum(p, ak["MINIMUM_BEN"].to_numpy(float)), p)
            ex = float((np.floor(p)[mask] == fsben[mask]).mean())
            if ex > best_exact:
                best, best_exact = cand, ex
        return best, best_exact

    sched_arr = ak["_sched"].to_numpy()
    fits = {}
    for name in ["Urban", "Rural 2"]:
        m = sched_arr == name
        if m.sum() >= 20:
            fits[name] = fit_std(m)
    pooled_std, _ = fit_std(np.ones(len(ak), bool))
    std_map = {"Urban": fits.get("Urban", (pooled_std,))[0],
               "Rural 2": fits.get("Rural 2", (pooled_std,))[0],
               "Rural 1 (by elimination)": pooled_std}
    pred_assigned = reconstruct(std_map)
    out["std_fits"] = {"pooled": pooled_std,
                       **{k: v[0] for k, v in fits.items()},
                       "fit_slice_exact": {k: v[1] for k, v in fits.items()}}
    out["reconstruction_exact_with_assignment"] = float((pred_assigned == fsben).mean())
    # Honest single-table control on the sizes where the Urban table is
    # fully observed (1-6): allotment = Urban value for every case,
    # std 338 - the exp119 method, same subset for both numbers.
    zarr = ak["CERTHHSZ"].to_numpy(int)
    sub = zarr <= 6
    urban_allot = np.array([URBAN.get(z, 0) for z in zarr], float)
    cont_c = urban_allot - 0.30 * np.maximum(0.0, UU - (338.0 + other))
    pc = np.maximum(cont_c, 0.0)
    pc = np.where(zarr <= 2, np.maximum(pc, ak["MINIMUM_BEN"].to_numpy(float)), pc)
    out["control_single_table_urban_sizes1_6"] = {
        "n": int(sub.sum()),
        "exact_single_table": float((np.floor(pc)[sub] == fsben[sub]).mean()),
        "exact_with_assignment": float((pred_assigned[sub] == fsben[sub]).mean())}
    resid_a = fsben - pred_assigned
    miss = ak[resid_a != 0]
    out["assigned_misses"] = {"n": int((resid_a != 0).sum()),
                              "sizes": {str(int(k)): int(v) for k, v in
                                        Counter(miss["CERTHHSZ"]).items()},
                              "residuals": {str(int(k)): int(v) for k, v in
                                            Counter(resid_a[resid_a != 0]).items()}}
    # Cross-check exp119's other territory tables against BENMAX
    for st, tbl in [("Hawaii", {1: 527, 2: 967, 3: 1385, 4: 1759}),
                    ("Guam", {1: 430, 2: 788, 3: 1129, 4: 1434}),
                    ("Virgin Islands", {1: 375, 2: 688, 3: 985, 4: 1251})]:
        t = df[(df["STATENAME"] == st) & (df["SSI_CAP"] == 0) & (df["FSEARN"] == 0)
               & (df["CERTHHSZ"].between(1, 4))]
        tn = (t["FSUNEARN"].clip(lower=0)
              - (t["FSSTDDED"] + t["FSSLTDED"] + t["FSMEDDED"] + t["FSDEPDED"] + t["FSCSDED"]))
        tnz = t[tn <= 0]
        match = [tbl.get(int(z)) == b for z, b in zip(tnz["CERTHHSZ"], tnz["BENMAX"])]
        out[f"benmax_crosscheck_{st}"] = {"n_net_le_0": int(len(tnz)),
                                          "benmax_matches_exp119_table": float(np.mean(match)) if match else None}

Path(__file__).with_name("exp122_results.json").write_text(json.dumps(out, indent=2, default=str))
print(json.dumps(out, indent=2, default=str))
