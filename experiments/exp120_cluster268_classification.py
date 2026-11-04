"""Experiment 120 - classify the +$268 cluster by its QC variance codes.

exp118 found 205 earnings cases whose issued benefit exceeded the
statutory prediction by exactly $268 - in 95.1% the full allotment was
issued where verified earnings implied the $23 minimum. exp118 could
not say whether that is unreported earnings (client) or agency failure
to act. The QC file records the answer per case: up to nine variances
with ELEMENT (what), NATURE (how), and AGENCY (responsibility - the
column is literally named AGENCY) codes. This experiment reads them
for the cluster and for a comparison set of ordinary error cases.

Writes experiments/exp120_results.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth.codebook import ELEMENT_BUCKETS, ELEMENT_LABELS, NATURE_LABELS, CAUSE_LABELS

PATH = "/home/hatch/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
ALLOT = {1: 291, 2: 535, 3: 766, 4: 973}
TERR = ["Alaska", "Hawaii", "Guam", "Virgin Islands"]

AGENCY_CAUSE = {10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25}
CLIENT_CAUSE = {1, 2, 3, 4}


def coarse(code):
    if code is None:
        return "unrecorded"
    if code in AGENCY_CAUSE:
        return "agency"
    if code in CLIENT_CAUSE:
        return "client"
    return "other/no-fault"


var_cols = [f"{p}{i}" for p in ("ELEMENT", "NATURE", "AGENCY") for i in range(1, 10)]
cols = ["CERTHHSZ", "FSEARN", "FSUNEARN", "FSERNDED", "FSSTDDED", "FSSLTDED",
        "FSMEDDED", "FSDEPDED", "FSCSDED", "FSBEN", "BENFIX", "RAWBEN",
        "STATENAME", "AMTERR", "SSI_CAP"] + var_cols
df = pd.read_csv(PATH, usecols=cols)
need = ["FSEARN", "FSUNEARN", "FSERNDED", "FSSTDDED", "FSSLTDED",
        "FSMEDDED", "FSDEPDED", "FSCSDED"]
s = df[(df["CERTHHSZ"].between(1, 4)) & (df["FSEARN"] > 0)
       & (df["SSI_CAP"] == 0) & (~df["STATENAME"].isin(TERR))].copy()
s = s[s[need].notna().all(axis=1)]
E = s["FSEARN"].to_numpy(float)
U = s["FSUNEARN"].clip(lower=0).to_numpy(float)
deds = (s["FSERNDED"] + s["FSSTDDED"] + s["FSSLTDED"] + s["FSMEDDED"]
        + s["FSDEPDED"] + s["FSCSDED"]).to_numpy(float)
sizes = s["CERTHHSZ"].to_numpy(int)
allot = np.array([ALLOT[z] for z in sizes], float)
cont = allot - 0.30 * np.maximum(0.0, E + U - deds)
p = np.maximum(cont, 0.0)
p = np.where(sizes <= 2, np.maximum(p, 23.0), p)
pred = np.floor(p)
raw = s["RAWBEN"].to_numpy(float)
benfix = s["BENFIX"].to_numpy(float)

cluster_mask = (raw - pred) == 268
error_mask = benfix != raw  # QC found an error of any size


def profile(mask, name):
    sub = s[mask]
    out = {"n": int(mask.sum())}
    elems, natures, causes = Counter(), Counter(), Counter()
    first_elem, first_cause = Counter(), Counter()
    nvars = []
    for _, row in sub.iterrows():
        case_vars = []
        for i in range(1, 10):
            e = row[f"ELEMENT{i}"]
            if pd.isna(e):
                continue
            e = int(e)
            n = row[f"NATURE{i}"]
            c = row[f"AGENCY{i}"]
            case_vars.append((e, None if pd.isna(n) else int(n),
                              None if pd.isna(c) else int(c)))
        nvars.append(len(case_vars))
        for j, (e, n, c) in enumerate(case_vars):
            elems[ELEMENT_BUCKETS.get(e, f"code{e}")] += 1
            if n is not None:
                natures[n] += 1
            causes[coarse(c)] += 1
            if j == 0:
                first_elem[ELEMENT_BUCKETS.get(e, f"code{e}")] += 1
                first_cause[coarse(c)] += 1
    out["cases_with_any_variance"] = float(np.mean([n > 0 for n in nvars])) if nvars else 0.0
    out["mean_variances_per_case"] = float(np.mean(nvars)) if nvars else 0.0
    out["element_buckets_all"] = elems.most_common()
    out["first_variance_element"] = first_elem.most_common()
    out["cause_buckets_all"] = causes.most_common()
    out["first_variance_cause"] = first_cause.most_common()
    out["nature_top"] = [[NATURE_LABELS.get(k, str(k)), v] for k, v in natures.most_common(6)]
    amterr = sub["AMTERR"].dropna()
    out["amterr_median"] = float(amterr.median()) if len(amterr) else None
    globals()[name] = out
    return out


res = {"cluster268": profile(cluster_mask, "c"),
       "comparison_error_cases": profile(error_mask & ~cluster_mask, "e")}
Path(__file__).with_name("exp120_results.json").write_text(json.dumps(res, indent=2, default=str))
print(json.dumps(res, indent=2, default=str))
