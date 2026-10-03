"""Experiment 38 - rare-rule mass audit.

Hypothesis (calibration gate): the generator is missing structural error mass
from SNAP rules it doesn't model - student eligibility (E111), ABAWD
time-limited participation / work rules (E160-166), and elderly/disabled
special provisions (E810 SNAP simplification project incl. ESAP, E820
demonstration projects) - and that missing mass is quantitatively material.

Method:
  real: FY2020-2024 QC public-use microdata (held out; NEVER copied into the
        repo). For each target element set, compute per FY:
          * weighted variance share = FYWGT-weighted target variances /
            FYWGT-weighted all variances
          * weighted case share = FYWGT-weighted error cases with >=1 target
            variance / FYWGT-weighted error cases (STATUS in 2,3)
          * weighted dollar share = FYWGT*|AMTERR| over error cases with >=1
            target variance / over all error cases. (Microdata has no
            per-variance dollar field, so dollars are attributed at case level.)
  synth: generate.py (seed 7, experiments/dist.json) element distribution;
         check whether target codes are produced at all, and compute the
         element-marginal L1 vs real FY2024, with the target sets' contribution.

Usage:
    python3 -m src.synth.generate --n 20000 --seed 7 \
        --dist experiments/dist.json --out /tmp/exp38_synth.csv
    python3 experiments/exp38_rare_rule_mass.py \
        --real-dir ../snap-qc-data/raw --synth /tmp/exp38_synth.csv

ML vocabulary: L1 distance = sum over categories of |p_real - p_synth|,
a measure of how far the synthetic marginal distribution is from the real
one (0 = identical, 2 = completely disjoint for a discrete distribution).
Held-out validation = evaluating against real data the generator never saw.
"""
import argparse
import json
import sys

import pandas as pd

TARGETS = {
    "student": {111},
    "workrule": {160, 161, 162, 163, 164, 165, 166},  # 161 = ABAWD time-limited participation
    "elderly_demo": {810, 820},  # 810 = SNAP simplification project (incl. ESAP); 820 = demo projects
}
# extra unmodeled elements, for context only (not part of the hypothesis)
CONTEXT = {
    "citizenship": {130},
    "residency": {140},
    "disqualification": {151},
    "ssn": {170},
    "homeless_shelter": {362},
    "transitional_benefits": {530},
}

EL_COLS = [f"ELEMENT{i}" for i in range(1, 10)]
NAT_COLS = [f"NATURE{i}" for i in range(1, 10)]
USE_COLS = EL_COLS + ["STATUS", "AMTERR", "FYWGT"]


def load_fy(path):
    df = pd.read_csv(path, usecols=lambda c: c in USE_COLS or c in NAT_COLS,
                     low_memory=False)
    return df


def audit_year(df, fy, sets):
    err = df[df["STATUS"].isin([2, 3])].copy()
    w_err = err["FYWGT"].fillna(0).astype(float)
    # long-form variances
    long = []
    for i in range(1, 10):
        e = pd.to_numeric(err[f"ELEMENT{i}"], errors="coerce")
        m = e.notna()
        sub = pd.DataFrame({
            "w": w_err[m].values,
            "el": e[m].astype(int).values,
            "nat": pd.to_numeric(err.loc[m, f"NATURE{i}"], errors="coerce")
                         .fillna(0).astype(int).values,
            "status": err.loc[m, "STATUS"].values,
        })
        long.append(sub)
    var = pd.concat(long, ignore_index=True)
    total_var_w = var["w"].sum()

    # per-case: does the case carry >=1 target variance?
    out = {}
    for name, codes in sets.items():
        w_var = var.loc[var["el"].isin(codes), "w"].sum()
        # case-level: any variance with target element
        per_case = err.copy()
        hit = pd.Series(False, index=err.index)
        for i in range(1, 10):
            e = pd.to_numeric(err[f"ELEMENT{i}"], errors="coerce")
            hit |= e.isin(codes)
        per_case["hit"] = hit.values
        w_case = per_case.loc[hit, "FYWGT"].fillna(0).astype(float).sum()
        w_dol = (per_case.loc[hit, "FYWGT"].fillna(0).astype(float)
                 * per_case.loc[hit, "AMTERR"].fillna(0).astype(float).abs()).sum()
        w_dol_all = (w_err * err["AMTERR"].fillna(0).astype(float).abs()).sum()
        n_var = int((var["el"].isin(codes)).sum())
        n_case = int(hit.sum())
        st_mix = per_case.loc[hit, "STATUS"].value_counts().to_dict()
        amts = (per_case.loc[hit, "FYWGT"].fillna(0).astype(float)
                * per_case.loc[hit, "AMTERR"].fillna(0).astype(float).abs())
        mean_amt = float((amts.sum() / per_case.loc[hit, "FYWGT"].fillna(0).astype(float).sum())
                         ) if hit.sum() else float("nan")
        nature = var.loc[var["el"].isin(codes), "nat"].value_counts().to_dict()
        out[name] = {
            "fy": fy,
            "n_var": n_var, "n_case": n_case,
            "var_share": w_var / total_var_w if total_var_w else 0.0,
            "case_share": w_case / w_err.sum() if w_err.sum() else 0.0,
            "dollar_share": w_dol / w_dol_all if w_dol_all else 0.0,
            "mean_amt_per_case": mean_amt,
            "status_mix": {int(k): int(v) for k, v in st_mix.items()},
            "nature_counts": {int(k): int(v) for k, v in nature.items()},
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real-dir", required=True)
    ap.add_argument("--synth", required=True)
    args = ap.parse_args()

    all_sets = {**TARGETS, **CONTEXT}
    rows = []
    el_real_2024 = None
    for fy in (2020, 2021, 2022, 2023, 2024):
        path = f"{args.real_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        df = load_fy(path)
        res = audit_year(df, fy, all_sets)
        for name, r in res.items():
            rows.append((name, r))
        if fy == 2024:
            # element marginal for L1 vs synth (each variance weighted by case weight)
            err = df[df["STATUS"].isin([2, 3])]
            vw = []
            for i in range(1, 10):
                e = pd.to_numeric(err[f"ELEMENT{i}"], errors="coerce")
                m = e.notna()
                vw.append(pd.DataFrame({"el": e[m].astype(int).values,
                                        "w": err.loc[m, "FYWGT"].fillna(0).astype(float).values}))
            vdf = pd.concat(vw, ignore_index=True)
            el_real_2024 = (vdf.groupby("el")["w"].sum() / vdf["w"].sum()).to_dict()

    print("=== real QC: target sets by FY (weighted) ===")
    hdr = (f"{'set':<16}{'fy':<6}{'n_var':>7}{'n_case':>8}{'var_sh%':>9}"
           f"{'case_sh%':>10}{'dollar_sh%':>12}{'mean_amt$':>11}{'status(2/3/4)':>16}")
    print(hdr)
    for name, r in rows:
        if name in CONTEXT:
            continue
        st = r["status_mix"]
        print(f"{name:<16}{r['fy']:<6}{r['n_var']:>7}{r['n_case']:>8}"
              f"{100*r['var_share']:>8.2f}%{100*r['case_share']:>9.2f}%"
              f"{100*r['dollar_share']:>11.2f}%{r['mean_amt_per_case']:>11.0f}"
              f"{str(st):>16}")

    print("\n=== context: other unmodeled elements, FY2024 only (weighted) ===")
    print(f"{'set':<22}{'n_var':>7}{'var_sh%':>9}{'case_sh%':>10}{'dollar_sh%':>12}")
    for name, r in rows:
        if name not in CONTEXT or r["fy"] != 2024:
            continue
        print(f"{name:<22}{r['n_var']:>7}{100*r['var_share']:>8.2f}%"
              f"{100*r['case_share']:>9.2f}%{100*r['dollar_share']:>11.2f}%")

    print("\n=== nature/status detail for hypothesis sets, FY2024 (unweighted counts) ===")
    for name, r in rows:
        if name in CONTEXT or r["fy"] != 2024:
            continue
        print(f"{name}: nature={r['nature_counts']} status={r['status_mix']}")

    # ---- synth side ----
    cases = [json.loads(line) for line in open(args.synth) if line.strip()]
    sels = []
    for c in cases:
        for v in c.get("variances", []):
            sels.append(v.get("element"))
    s = pd.Series(sels)
    print(f"\n=== synth: n={len(cases)} cases, n_var={len(s)} ===")
    print("element distribution:")
    print(s.value_counts().to_string())
    synth_dist = (s.value_counts(normalize=True)).to_dict()
    for name, codes in TARGETS.items():
        got = sum(synth_dist.get(e, 0.0) for e in codes)
        print(f"synth share of {name} {sorted(codes)}: {100*got:.3f}%")

    # L1 element marginal: real FY2024 vs synth
    keys = set(el_real_2024) | set(synth_dist)
    l1 = sum(abs(el_real_2024.get(k, 0.0) - synth_dist.get(k, 0.0)) for k in keys)
    target_keys = set().union(*TARGETS.values())
    l1_target = sum(abs(el_real_2024.get(k, 0.0) - synth_dist.get(k, 0.0))
                    for k in target_keys)
    print(f"\nelement-marginal L1 (real FY2024 vs synth): {l1:.4f}")
    print(f"  contribution of hypothesis target sets {sorted(target_keys)}: {l1_target:.4f} "
          f"({100*l1_target/l1:.1f}% of L1)")
    all_unmodeled = set().union(*CONTEXT.values()) | target_keys
    l1_unmodeled = sum(abs(el_real_2024.get(k, 0.0) - synth_dist.get(k, 0.0))
                       for k in all_unmodeled)
    print(f"  contribution of ALL unmodeled elements: {l1_unmodeled:.4f} "
          f"({100*l1_unmodeled/l1:.1f}% of L1)")


if __name__ == "__main__":
    main()
