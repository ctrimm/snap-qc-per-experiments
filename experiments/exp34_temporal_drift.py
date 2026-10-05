"""Experiment 34 - temporal drift across FY2020-2024 real QC microdata.

North-star gate: calibration. If finding/element/dollar mixes drifted
materially across FY2020-2024 (COVID-era waivers through unwinding), a single
FY2024-calibrated dist.json may misrepresent other years and a
year-conditioned dist is warranted.

Real side: ../snap-qc-data/raw/qcfyYYYY_csv/qc_pub_fyYYYY.csv
(held-out; NEVER committed). FY2021 covers Jul-Sep only. Unweighted
microdata, same convention as exp16.

Synth side: jsonl from
    python3 -m src.synth.generate --n 15000 --seed 7 \\
        --dist experiments/dist.json --out /tmp/exp34_synth.jsonl
(dist.json is the single current national dist, FY2024-calibrated.)

Usage:
    python3 experiments/exp34_temporal_drift.py --synth /tmp/exp34_synth.jsonl
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

import pandas as pd

from src.synth.codebook import element_bucket, cause_bucket

ROOT = Path(__file__).resolve().parent.parent

QUANTS = (0.10, 0.25, 0.50, 0.90, 0.99)
ELEMS = [f"ELEMENT{i}" for i in range(1, 10)]
NATS = [f"NATURE{i}" for i in range(1, 10)]
AGS = [f"AGENCY{i}" for i in range(1, 10)]

REAL_FILES = {
    2020: str(ROOT.parent / "snap-qc-data/raw/qcfy2020_csv/qc_pub_fy2020.csv"),
    2021: str(ROOT.parent / "snap-qc-data/raw/qcfy2021_csv/qc_pub_fy2021.csv"),
    2022: str(ROOT.parent / "snap-qc-data/raw/qcfy2022_csv/qc_pub_fy2022.csv"),
    2023: str(ROOT.parent / "snap-qc-data/raw/qcfy2023_csv/qc_pub_fy2023.csv"),
    2024: str(ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"),
}


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def l1(a, b):
    keys = set(a) | set(b)
    return sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)


def load_real(path):
    """One pandas pass. Returns dict of mixes + dollar quantiles."""
    df = pd.read_csv(
        path,
        usecols=["STATUS", "AMTERR"] + ELEMS + NATS + AGS,
        dtype=str, keep_default_na=False,
    )
    n = len(df)
    status = df["STATUS"].value_counts(normalize=True)
    finding_mix = {
        "correct": float(status.get("1", 0.0)),
        "over": float(status.get("2", 0.0)),
        "under": float(status.get("3", 0.0)),
    }
    status_codes = sorted(df["STATUS"].unique())

    # variance-level mixes: stack the 9 variance slots
    elem_counts, nat_counts, cause_counts = {}, {}, {}
    nvar = 0
    for e_col, n_col, a_col in zip(ELEMS, NATS, AGS):
        for e, na, ag in zip(df[e_col], df[n_col], df[a_col]):
            if not e:
                continue
            nvar += 1
            b = element_bucket(int(e))
            elem_counts[b] = elem_counts.get(b, 0) + 1
            nat_counts[na] = nat_counts.get(na, 0) + 1
            cb = "blank" if not ag else cause_bucket(int(ag))
            cause_counts[cb] = cause_counts.get(cb, 0) + 1
    elem_mix = {k: v / nvar for k, v in elem_counts.items()} if nvar else {}
    nat_mix = {k: v / nvar for k, v in nat_counts.items()} if nvar else {}
    cause_mix = {k: v / nvar for k, v in cause_counts.items()} if nvar else {}

    # dollar-error quantiles, over vs under (AMTERR is non-negative)
    amterr = pd.to_numeric(df["AMTERR"], errors="coerce").fillna(0.0)
    over_amt = amterr[df["STATUS"] == "2"].tolist()
    under_amt = amterr[df["STATUS"] == "3"].tolist()
    dq = {
        "over": {f"p{int(q*100)}": pct(over_amt, q) for q in QUANTS},
        "under": {f"p{int(q*100)}": pct(under_amt, q) for q in QUANTS},
        "n_over": len(over_amt),
        "n_under": len(under_amt),
        "median_over": pct(over_amt, 0.5),
        "median_under": pct(under_amt, 0.5),
    }
    return {
        "n": n, "nvar": nvar, "status_codes": status_codes,
        "finding_mix": finding_mix, "element_mix": elem_mix,
        "nature_mix": nat_mix, "cause_mix": cause_mix, "dollars": dq,
    }


def load_synth(path):
    finding = {}
    elem_counts, nat_counts, cause_counts = {}, {}, {}
    over_amt, under_amt = [], []
    n = 0
    nvar = 0
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        n += 1
        case = json.loads(line)
        f = case["finding"]
        finding[f] = finding.get(f, 0) + 1
        if f in (2, 3):
            s = case["issued_benefit"] - case["correct_benefit"]
            (over_amt if f == 2 else under_amt).append(abs(s))
        for v in case.get("variances", []):
            nvar += 1
            b = v["element_bucket"]
            elem_counts[b] = elem_counts.get(b, 0) + 1
            nat_counts[str(v["nature"])] = nat_counts.get(str(v["nature"]), 0) + 1
            c = v["cause"]
            cb = "blank" if c is None else cause_bucket(int(c))
            cause_counts[cb] = cause_counts.get(cb, 0) + 1
    finding_mix = {
        "correct": finding.get(1, 0) / n,
        "over": finding.get(2, 0) / n,
        "under": finding.get(3, 0) / n,
    }
    dq = {
        "over": {f"p{int(q*100)}": pct(over_amt, q) for q in QUANTS},
        "under": {f"p{int(q*100)}": pct(under_amt, q) for q in QUANTS},
        "n_over": len(over_amt), "n_under": len(under_amt),
        "median_over": pct(over_amt, 0.5), "median_under": pct(under_amt, 0.5),
    }
    return {
        "n": n, "nvar": nvar,
        "finding_mix": finding_mix,
        "element_mix": {k: v / nvar for k, v in elem_counts.items()} if nvar else {},
        "nature_mix": {k: v / nvar for k, v in nat_counts.items()} if nvar else {},
        "cause_mix": {k: v / nvar for k, v in cause_counts.items()} if nvar else {},
        "dollars": dq,
    }


def print_mix(label, years, key, topn=8):
    print(f"\n== {label} (shares) ==")
    cats = set()
    for y in years:
        cats |= set(years[y][key])
    cats = sorted(cats)
    hdr = f"{'cat':>14}" + "".join(f"{y:>9}" for y in years)
    print(hdr)
    totals = {y: sum(years[y][key].get(c, 0.0) for c in cats) for y in years}
    for c in cats:
        row = f"{c:>14}" + "".join(
            f"{years[y][key].get(c, 0.0):9.3f}" for y in years)
        print(row)
    print("  (categories shown: variance-level shares)")
    _ = totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", required=True)
    args = ap.parse_args()

    years = {fy: load_real(p) for fy, p in REAL_FILES.items()}
    synth = load_synth(args.synth)

    print("rows/variances per FY (FY2021 = Jul-Sep only):")
    for fy, d in years.items():
        print(f"  FY{fy}: n={d['n']:,} rows, {d['nvar']:,} variances, "
              f"STATUS codes={d['status_codes']}")
    print(f"  synth: n={synth['n']:,} cases, {synth['nvar']:,} variances")

    f = years
    print_mix("finding mix (case-level)", f, "finding_mix")
    print_mix("element bucket mix (variance-level)", f, "element_mix")
    print_mix("nature mix (variance-level, raw codes)", f, "nature_mix")
    print_mix("cause mix (variance-level, coarse)", f, "cause_mix")

    print("\n== dollar-error quantiles, |AMTERR| over vs under, by FY ==")
    print(f"{'':>12}" + "".join(f"{y:>9}" for y in years))
    for q in QUANTS:
        lab = f"over p{int(q*100)}"
        print(f"{lab:>12}" + "".join(
            f"{years[y]['dollars']['over'][f'p{int(q*100)}']:9.1f}" for y in years))
    for q in QUANTS:
        lab = f"under p{int(q*100)}"
        print(f"{lab:>12}" + "".join(
            f"{years[y]['dollars']['under'][f'p{int(q*100)}']:9.1f}" for y in years))
    print(f"{'med over':>12}" + "".join(
        f"{years[y]['dollars']['median_over']:9.1f}" for y in years))
    print(f"{'med under':>12}" + "".join(
        f"{years[y]['dollars']['median_under']:9.1f}" for y in years))

    # drift: pairwise L1 on each mix
    fys = sorted(years)
    print("\n== drift: pairwise L1 between FY mixes ==")
    for key, lab in [("finding_mix", "finding"), ("element_mix", "element"),
                     ("nature_mix", "nature"), ("cause_mix", "cause")]:
        vals = []
        for i in range(len(fys)):
            for j in range(i + 1, len(fys)):
                a, b = fys[i], fys[j]
                vals.append((l1(years[a][key], years[b][key]), a, b))
        vals.sort(reverse=True)
        worst = vals[0]
        adj = max(vals[k] for k in range(len(vals))
                  if vals[k][2] - vals[k][1] == 1)
        print(f"  {lab:>8}: max L1 {worst[0]:.3f} "
              f"(FY{worst[1]}-FY{worst[2]}); max adjacent-year L1 "
              f"{adj[0]:.3f} (FY{adj[1]}-FY{adj[2]})")

    # where does the synth point sit relative to each FY?
    print("\n== synth L1 distance to each FY (pooled/FY2024 dist) ==")
    print(f"{'mix':>10}" + "".join(f"{y:>9}" for y in fys))
    for key, lab in [("finding_mix", "finding"), ("element_mix", "element"),
                     ("nature_mix", "nature"), ("cause_mix", "cause")]:
        print(f"{lab:>10}" + "".join(
            f"{l1(synth[key], years[y][key]):9.3f}" for y in fys))

    print("\n== synth dollar quantiles vs FYs ==")
    for q in QUANTS:
        lab = f"over p{int(q*100)}"
        real = " ".join(f"{years[y]['dollars']['over'][f'p{int(q*100)}']:9.1f}"
                        for y in fys)
        print(f"{lab:>12} synth {synth['dollars']['over'][f'p{int(q*100)}']:7.1f}"
              f" | real:{real}")
    for q in QUANTS:
        lab = f"under p{int(q*100)}"
        real = " ".join(f"{years[y]['dollars']['under'][f'p{int(q*100)}']:9.1f}"
                        for y in fys)
        print(f"{lab:>12} synth {synth['dollars']['under'][f'p{int(q*100)}']:7.1f}"
              f" | real:{real}")

    # biggest per-category shifts for the max-drift pairs
    print("\n== largest single-category share shifts between consecutive FYs ==")
    for key, lab in [("finding_mix", "finding"), ("element_mix", "element"),
                     ("nature_mix", "nature"), ("cause_mix", "cause")]:
        shifts = []
        for a, b in zip(fys[:-1], fys[1:]):
            for c in set(years[a][key]) | set(years[b][key]):
                d = years[b][key].get(c, 0.0) - years[a][key].get(c, 0.0)
                shifts.append((abs(d), d, c, a, b))
        shifts.sort(reverse=True)
        print(f"  {lab}:")
        for s in shifts[:4]:
            print(f"    FY{s[3]}->FY{s[4]} {s[2]}: {s[1]:+.3f}")

    out = {"real": {str(k): v for k, v in years.items()}, "synth": synth}
    with open("/tmp/exp34_results.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nresults -> /tmp/exp34_results.json")


if __name__ == "__main__":
    sys.exit(main())
