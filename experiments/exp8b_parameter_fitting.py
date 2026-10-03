"""Experiment 8b — rules-recovery parameter fitting.

Fit the production eligibility engine's effective benefit-formula parameters
from (reported facts -> RAWBEN) pairs on the exp8a cleaned observation set,
then compare each fitted value to FY2024 published statute.

Why reported variables: fields with Origin=R in the tech doc (RAWGROSS,
RAWERND, RAWNET, SHELDED, FSDEPDED, FSMEDEXP) are what the state agency's
system saw and used -- i.e. the engine's actual inputs -- while RAWBEN is
its output. The QC-calculated fields (FSEARN, FSNETINC, FSBEN, BENMAX)
are the reviewer's corrected values, used here only to build the cleaned
set, never as engine inputs.

Two subtleties the first draft got wrong (kept as comments so the next
worker doesn't repeat them):
- The benefit-relevant household size is NOT RAWHSIZE (reported size agrees
  with the benefit actually paid only 85% of the time). QC's BENMAX field
  implies the effective size exactly (matches FSUSIZE 99.8%), and on
  STATUS=1 rows agency and QC used the same size. Output-side fits use
  BENMAX directly, never a size mapping.
- Minnesota MFIP cases use a 50% earnings disregard and no other
  deductions; SSI-CAP standard-benefit cases skip deductions. Both are
  excluded from the deduction-identity fits.

Read-only wrt the microdata: this script only reads
../snap-qc-data/raw/ (beside the repo checkout) and writes a small aggregate
JSON next to itself. Run: python3 experiments/exp8b_parameter_fitting.py [--fy 2024]
"""

import argparse
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(os.path.dirname(ROOT), "snap-qc-data", "raw")

# FY2024 statutory parameters, contiguous US + DC (exp10-audited; tech doc
# Appendix F Tables F.3/F.5/F.6).
STATUTE = {
    "benmax": {1: 291, 2: 535, 3: 766, 4: 973, 5: 1155, 6: 1386, 7: 1532,
               8: 1751, "addl": 219},
    "std_ded": {1: 198, 2: 198, 3: 198, 4: 208, 5: 244, "6+": 279},
    "shelter_cap": 672,
    "earned_rate": 0.20,
    "med_threshold": 35,
    "min_benefit": 23,
    "benefit_rate": 0.30,
    "homeless_shelter": 180,  # $179.66 recorded rounded up
}
NON_CONTIG = [2, 15, 66, 78]  # AK, HI, Guam, VI have their own tables
# States with a standard medical deduction demo in FY2024 (tech doc Table
# F.4) -- medical deduction is a flat standard amount there, not actual-35.
MED_DEMO_FIPS = [1, 4, 5, 6, 8, 13, 16, 17, 19, 20, 21, 22, 25, 26, 29,
                 33, 38, 41, 44, 45, 46, 48, 50, 51, 56]

USECOLS = ["STATE", "STATUS", "AMTERR", "RAWHSIZE", "RAWBEN", "RAWNET",
           "RAWGROSS", "RAWERND", "SHELDED", "FSDEPDED", "FSMEDEXP",
           "HOMEDED", "FSEARN", "FSBEN", "BENMAX", "FSELDER", "FSDIS",
           "FSCSDED",
           "SSI_CAP", "ELEMENT1"]


def eff_size(benmax):
    """Benefit-relevant household size implied by QC's BENMAX."""
    b = STATUTE["benmax"]
    inv = {v: k for k, v in b.items() if k != "addl"}
    if benmax in inv:
        return inv[benmax]
    if benmax > b[8] and (benmax - b[8]) % b["addl"] == 0:
        return 8 + (benmax - b[8]) // b["addl"]
    return np.nan


def std_ded_stat(size):
    return STATUTE["std_ded"][size if size <= 5 else "6+"]


def load(fy):
    df = pd.read_csv(f"{DATA}/qcfy{fy}_csv/qc_pub_fy{fy}.csv",
                     usecols=USECOLS, low_memory=False)
    df = df[~df["STATE"].isin(NON_CONTIG)].copy()  # contiguous US + DC
    for c in ["AMTERR", "RAWBEN", "RAWNET", "RAWGROSS", "RAWERND",
              "SHELDED", "FSDEPDED", "FSMEDEXP", "FSEARN", "FSBEN",
              "BENMAX", "FSELDER", "FSDIS", "SSI_CAP", "FSCSDED"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["FSDEPDED", "FSMEDEXP", "FSCSDED"]:
        df[c] = df[c].fillna(0)  # missing deduction = not claimed
    df["HOMEDED"] = pd.to_numeric(df["HOMEDED"],
                                  errors="coerce").fillna(1).astype(int)
    df["housed"] = df["HOMEDED"] == 1
    df["effsize"] = df["BENMAX"].map(eff_size)
    # Rows whose benefit math follows the standard formula: not MFIP (MN),
    # not SSI-CAP standard-benefit cases.
    df["std_formula"] = (df["STATE"] != 27) & (df["SSI_CAP"] == 0)
    return df


def cleaned_set(df):
    """exp8a cleaned observation set.

    Keep STATUS=1 with RAWBEN==FSBEN (agency computed correctly) and
    STATUS 2/3 where RAWBEN = FSBEN +/- AMTERR (agency computed from wrong
    inputs -- still engine behavior; the *reported* inputs are the engine's
    true inputs). Drop recoupment-type rows (STATUS=1, RAWBEN != FSBEN, no
    variance, diff > $1) and reporting anomalies (|FSBEN-RAWBEN| wildly
    exceeding AMTERR). Tolerate +/-$1 rounding.
    """
    s1 = (df["STATUS"] == 1) & (df["RAWBEN"] == df["FSBEN"])
    diff = (df["FSBEN"] - df["RAWBEN"]).abs()
    keep23 = df["STATUS"].isin([2, 3]) & ((diff - df["AMTERR"]).abs() <= 1)
    novar = df["ELEMENT1"].isna()
    recoup = ((df["STATUS"] == 1) & (df["RAWBEN"] != df["FSBEN"])
              & novar & (diff > 1))
    anom = (diff - df["AMTERR"]).abs() > 1
    keep = (s1 | keep23) & ~anom & ~recoup
    info = {"n": len(df), "keep_s1": int(s1.sum()),
            "keep_23": int(keep23.sum()), "drop_recoup": int(recoup.sum()),
            "drop_anom": int(anom.sum()), "clean": int(keep.sum())}
    return df[keep].copy(), info


def interior(df):
    """Rows where the benefit is strictly inside (min, max): the 30% rate
    is identified, not the bounds."""
    return df[(df["RAWBEN"] < df["BENMAX"] - 1)
              & (df["RAWBEN"] > STATUTE["min_benefit"] + 1)
              & (df["RAWNET"] > 0) & df["effsize"].notna()]


def fit(train):
    out = {}
    # Clean engine behavior: QC verified every input (STATUS=1,
    # RAWBEN==FSBEN) and the standard formula applies.
    ok = train[(train["STATUS"] == 1) & (train["RAWBEN"] == train["FSBEN"])
               & train["std_formula"] & train["housed"]]

    # A. Max allotments: zero reported net -> benefit = max allotment.
    z = ok[(ok["RAWNET"] == 0) & (ok["RAWBEN"] > 0)]
    bm = {}
    for s in range(1, 9):
        stat = STATUTE["benmax"][s]
        v = z[z["BENMAX"] == stat]["RAWBEN"]
        if len(v) >= 30:
            bm[s] = {"fitted": float(v.median()), "n": len(v)}
    big = z[z["BENMAX"] > STATUTE["benmax"][8]]
    if len(big) >= 30:
        out["benmax_addl"] = float(
            ((big["RAWBEN"] - STATUTE["benmax"][8])
             / (big["effsize"] - 8)).median())
        out["benmax_addl_n"] = len(big)
    out["benmax"] = bm

    # B. 30% benefit rate: slope of (BENMAX - RAWBEN) on RAWNET, interior.
    inn = interior(ok)
    x = inn["RAWNET"].to_numpy()
    y = (inn["BENMAX"] - inn["RAWBEN"]).to_numpy()
    out["benefit_rate"] = float(np.polyfit(x, y, 1)[0])
    out["benefit_rate_n"] = len(inn)
    prod = 0.3 * inn["RAWNET"]
    pred = inn["BENMAX"] - inn["RAWBEN"]
    out["rounding_match"] = {
        name: float((f(prod).to_numpy() == pred.to_numpy()).mean())
        for name, f in [("ceil", np.ceil), ("round", np.round),
                        ("floor", np.floor)]}

    # C. Minimum benefit: 1-2 person units (BENMAX 291/535) where the
    # formula gives < $23.
    small = ok[ok["BENMAX"].isin([291, 535])]
    pred_s = small["BENMAX"] - np.ceil(0.3 * small["RAWNET"])
    floored = small[pred_s < STATUTE["min_benefit"]]
    out["min_benefit"] = (float(floored["RAWBEN"].mode().iloc[0])
                          if len(floored) else None)
    out["min_benefit_n"] = len(floored)
    out["min_benefit_mode_share"] = (
        float((floored["RAWBEN"] == out["min_benefit"]).mean())
        if len(floored) else None)

    # D. Earned-income disregard: RAWERND vs countable earned income.
    e = ok[ok["FSEARN"] > 0]
    out["earned_rate"] = float((e["RAWERND"] / e["FSEARN"]).median())
    out["earned_rate_n"] = len(e)
    er = 0.2 * e["FSEARN"]
    out["earned_rounding"] = {
        "floor": float((np.floor(er) == e["RAWERND"]).mean()),
        "round": float((np.round(er) == e["RAWERND"]).mean()),
    }

    # E. Standard deduction as the residual of the reported net identity
    # (net = gross - earned_ded - std - med - depcare - childsupport -
    #  shelter).
    c = ok[(ok["FSMEDEXP"] == 0) & (ok["RAWNET"] > 0)]
    impl = (c["RAWGROSS"] - c["RAWERND"] - c["FSDEPDED"] - c["FSCSDED"]
            - c["SHELDED"] - c["RAWNET"])
    sd = {}
    for s, stat in [(1, 198), (2, 198), (3, 198), (4, 208), (5, 244),
                    ("6+", 279)]:
        v = impl[c["effsize"] == s] if s != "6+" else impl[c["effsize"] >= 6]
        v = v[v.notna()]
        if len(v) >= 30:
            sd[str(s)] = {"fitted": float(v.median()), "statutory": stat,
                          "within1": float((v - stat).abs().le(1).mean()),
                          "n": int(len(v))}
    out["std_ded"] = sd

    # F. Medical deduction: the file records the *applied* deduction, not raw
    # expenses (values cluster at demo-state standard amounts; the $35
    # disregard is already netted out). So the $35 threshold itself is NOT
    # identifiable -- but we can check the recorded deduction is the one
    # the net identity implies.
    m = ok[(ok["FSMEDEXP"] > 0) & (ok["RAWNET"] > 0)
           & ((ok["FSELDER"] == 1) | (ok["FSDIS"] == 1))]
    med_ded = (m["RAWGROSS"] - m["RAWERND"]
               - m["effsize"].map(std_ded_stat)
               - m["FSDEPDED"] - m["FSCSDED"] - m["SHELDED"] - m["RAWNET"])
    agree = (m["FSMEDEXP"] - med_ded).abs().le(1)
    out["med_deduction"] = {
        "recorded_vs_implied_within1": float(agree.mean()) if len(m) else None,
        "corr": float(m["FSMEDEXP"].corr(med_ded)) if len(m) else None,
        "n": int(len(m)),
        "threshold_identifiable": False,
    }

    # G. Shelter cap: point mass at the cap for non-elderly/disabled HH,
    # restricted to RAWNET>0 so the cap binds materially (when net is 0 the
    # recorded SHELDED is moot and sometimes exceeds the cap).
    eld = (ok["FSELDER"] == 1) | (ok["FSDIS"] == 1)
    nz = ok["RAWNET"] > 0
    nh = ok[(~eld) & (ok["SHELDED"] > 0) & nz]
    eh = ok[eld & (ok["SHELDED"] > 0) & nz]
    out["shelter"] = {
        "nonelder_frac_at_672": float((nh["SHELDED"] == 672).mean()),
        "nonelder_max": float(nh["SHELDED"].max()),
        "elder_max": float(eh["SHELDED"].max()),
        "elder_frac_above_672": float((eh["SHELDED"] > 672).mean()),
        "n_nonelder": int(len(nh)), "n_elder": int(len(eh)),
    }

    # Homeless standard shelter deduction (HOMEDED==3 -> $180 recorded).
    hs = train[(train["HOMEDED"] == 3) & (train["SHELDED"] > 0)]
    out["homeless_shelter"] = {
        "frac_at_180": float((hs["SHELDED"] == 180).mean()) if len(hs) else None,
        "n": int(len(hs)),
    }

    # I. Per-state 30% rate scan: any state's engine on a different rate?
    per_state = {}
    for st, g in interior(ok).groupby("STATE"):
        if len(g) < 50:
            continue
        xx = g["RAWNET"].to_numpy()
        yy = (g["BENMAX"] - g["RAWBEN"]).to_numpy()
        per_state[int(st)] = {"slope": float(np.polyfit(xx, yy, 1)[0]),
                              "n": int(len(g))}
    out["per_state_slope"] = per_state
    return out


def predict(df, rate, min_ben):
    bmax = df["BENMAX"]
    raw = bmax - np.ceil(rate * df["RAWNET"])
    fl = np.where(bmax.isin([291, 535]), min_ben, -np.inf)
    return np.maximum(raw, fl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fy", type=int, default=2024)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    df = load(args.fy)
    clean, info = cleaned_set(df)
    print(f"FY{args.fy}: n={info['n']} contig-US+DC; cleaned n={info['clean']} "
          f"(STATUS=1 exact: {info['keep_s1']}, STATUS 2/3: {info['keep_23']}, "
          f"drop recoupment: {info['drop_recoup']}, drop anomalies: "
          f"{info['drop_anom']})")

    rng = np.random.default_rng(args.seed)
    idx = clean.index.to_numpy()
    rng.shuffle(idx)
    cut = len(idx) // 2
    train, hold = clean.loc[idx[:cut]], clean.loc[idx[cut:]]
    print(f"train n={len(train)}, holdout n={len(hold)} (seed {args.seed})")

    f = fit(train)

    print("\n-- A. Max allotments: median RAWBEN at RAWNET==0, by BENMAX --")
    for s in range(1, 9):
        if s not in f["benmax"]:
            continue
        stat = STATUTE["benmax"][s]
        d = f["benmax"][s]
        print(f"  size {s}: fitted {d['fitted']:.0f}  statutory {stat}  "
              f"n={d['n']}")
    if "benmax_addl" in f:
        print(f"  each addl person: fitted {f['benmax_addl']:.1f}  statutory "
              f"{STATUTE['benmax']['addl']}  n={f['benmax_addl_n']}")

    print(f"\n-- B. Benefit rate: fitted {f['benefit_rate']:.4f} (statutory "
          f"0.30), n={f['benefit_rate_n']}")
    print("   0.3*net rounding exact-match:",
          {k: round(v, 4) for k, v in f["rounding_match"].items()})

    print(f"\n-- C. Minimum benefit: fitted {f['min_benefit']} (statutory 23), "
          f"mode share {f['min_benefit_mode_share']:.3f}, "
          f"n={f['min_benefit_n']}")

    print(f"\n-- D. Earned-income disregard: fitted {f['earned_rate']:.4f} "
          f"(statutory 0.20), n={f['earned_rate_n']}")
    print("   RAWERND rounding exact-match:",
          {k: round(v, 4) for k, v in f["earned_rounding"].items()})

    print("\n-- E. Standard deduction (residual of reported-net identity) --")
    for s, d in f["std_ded"].items():
        print(f"  size {s}: fitted {d['fitted']:.0f}  statutory "
              f"{d['statutory']}  within $1: {d['within1']:.3f}  n={d['n']}")

    print(f"\n-- F. Medical deduction: recorded FSMEDEXP vs net-identity-implied "
          f"deduction: within $1 {f['med_deduction']['recorded_vs_implied_within1']:.3f}, "
          f"corr {f['med_deduction']['corr']:.3f}, n={f['med_deduction']['n']}")
    print("   The $35 threshold is NOT identifiable: the file records the "
          "post-threshold deduction (values cluster at demo-state standard "
          "amounts), not raw expenses.")
    sh = f["shelter"]
    print(f"\n-- G. Shelter cap: non-elderly/disabled SHELDED==672 share "
          f"{sh['nonelder_frac_at_672']:.3f} (n={sh['n_nonelder']}), max "
          f"{sh['nonelder_max']:.0f}; elderly/disabled max "
          f"{sh['elder_max']:.0f}, share >672 {sh['elder_frac_above_672']:.3f} "
          f"(n={sh['n_elder']}) [statutory: cap 672, waived if eld/dis]")
    hs = f["homeless_shelter"]
    print(f"   homeless std shelter ded: SHELDED==180 share {hs['frac_at_180']}"
          f" (n={hs['n']}) [statutory $179.66, recorded $180]")
    print("\n-- H. SUA: state-set (tech doc Table F.7), no single national "
          "value -- not fitted.")

    print("\n-- I. Per-state 30% rate scan (STATUS=1 interior rows, n>=50) --")
    slopes = f["per_state_slope"]
    dev = {st: d for st, d in slopes.items()
           if abs(d["slope"] - 0.30) > 0.02}
    print(f"   {len(slopes)} states scanned, "
          f"{len(dev)} deviate >0.02 from 0.30: "
          f"{ {st: round(d['slope'], 3) for st, d in sorted(dev.items())} }")
    vals = sorted(d["slope"] for d in slopes.values())
    print(f"   slope range [{vals[0]:.3f}, {vals[-1]:.3f}]")

    # Holdout: fitted vs statutory output-side formula, on clean rows and
    # on error rows (where residuals should look like input errors).
    ok_hold = hold[(hold["STATUS"] == 1) & (hold["RAWBEN"] == hold["FSBEN"])
                   & hold["std_formula"] & hold["housed"]]
    err_hold = hold[hold["STATUS"].isin([2, 3])]
    for name, rate, mb in [("fitted", f["benefit_rate"], f["min_benefit"]),
                           ("statutory", 0.30, 23.0)]:
        for label, d in [("STATUS=1", ok_hold), ("STATUS 2/3", err_hold)]:
            dd = d[d["effsize"].notna()]
            pred = predict(dd, rate, mb)
            e = (pred - dd["RAWBEN"]).abs()
            print(f"holdout [{name}] {label} (n={len(dd)}): exact "
                  f"{(e == 0).mean():.4f}, within $1 {(e <= 1).mean():.4f}, "
                  f"MAE ${e.mean():.2f}")

    with open(os.path.join(HERE, "exp8b_fitted_params.json"), "w") as fh:
        json.dump({"fy": args.fy, "seed": args.seed, "cleaned_info": info,
                   "fitted": f}, fh, indent=2, default=float)
    print("\nwrote experiments/exp8b_fitted_params.json")


if __name__ == "__main__":
    main()
