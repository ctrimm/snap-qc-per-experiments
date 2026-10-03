"""Experiment 8c -- PA-filtered deviations as candidate engine misconfigurations.

Replicates exp8b's national parameter-fitting machinery restricted to
Pennsylvania (STATE=42, FY2020-2024) and compares PA's fitted benefit-formula
parameters against (a) the national fleet fitted the same way and (b) published
federal statute per fiscal year. Also tests the exp8b New England shelter-cap
anomaly pattern in PA specifically, and scans rounding, disregards, SUA
application, minimum benefit, and proration for PA-specific deviations.

Rules: fits use only clean engine rows (STATUS=1, RAWBEN==FSBEN,
SSI_CAP==0, housed) -- reported fields are the engine's inputs. Error rows
are examined descriptively only (reviewer-verified inputs, not the engine's).
Findings are framed as PA-program behavior; the file carries no engine/vendor
identifier, so no vendor attribution is possible.

Read-only wrt the microdata: reads ~/workspace/snap-qc-data/raw/, prints to
stdout. No repo writes (no JSON; the chronicle .md carries the numbers).
Run: python3 experiments/exp8c_pa_deviations.py
"""

import numpy as np
import pandas as pd

DATA = "/home/hatch/workspace/snap-qc-data/raw"

# Statutory parameters, 48 contiguous states + DC, per fiscal year.
# Sources: USDA FNS COLA memos (FY2020 eff 10/1/2019; FY2021 7/29/2020 memo;
# FY2022 via IL DHS MR #21.23; FY2023 COLA memo 8/2022 + FRAC Table 2;
# FY2024 exp10-audited). FY2021 QC file covers Jul-Sep 2021 sample months
# only, i.e. after the 1/1/2021 15% allotment increase -- post-increase
# max allotments are used.
STATUTE = {
    2020: {"benmax": {1: 194, 2: 355, 3: 509, 4: 646, 5: 768, 6: 924,
                      7: 1022, 8: 1164, "addl": 146},
           "std_ded": {1: 167, 2: 167, 3: 167, 4: 178, 5: 209, "6+": 240},
           "shelter_cap": 569, "homeless": 152.06, "min_benefit": 16},
    2021: {"benmax": {1: 234, 2: 430, 3: 616, 4: 782, 5: 929, 6: 1114,
                      7: 1232, 8: 1408, "addl": 176},
           "std_ded": {1: 167, 2: 167, 3: 167, 4: 181, 5: 212, "6+": 243},
           # min benefit $19 Jan-Sep 2021 (tech doc Table F.6b): 8% of the
           # $234 HH1 max after the 15% increase; the file covers Jul-Sep.
           "shelter_cap": 586, "homeless": 156.74, "min_benefit": 19},
    2022: {"benmax": {1: 250, 2: 459, 3: 658, 4: 835, 5: 992, 6: 1190,
                      7: 1316, 8: 1504, "addl": 188},
           # std ded corrected 2026-09-29: fleet-fitted point masses
           # (n=250-5425) are 177/177/177/184/215/246, not the IDHS memo's
           # 170/177/208/239; RI DHS notice corroborates 177/215/246.
           "std_ded": {1: 177, 2: 177, 3: 177, 4: 184, 5: 215, "6+": 246},
           "shelter_cap": 597, "homeless": 159.73, "min_benefit": 20},
    2023: {"benmax": {1: 281, 2: 516, 3: 740, 4: 939, 5: 1116, 6: 1339,
                      7: 1480, 8: 1691, "addl": 211},
           "std_ded": {1: 193, 2: 193, 3: 193, 4: 193, 5: 225, "6+": 258},
           "shelter_cap": 624, "homeless": 166.81, "min_benefit": 23},
    2024: {"benmax": {1: 291, 2: 535, 3: 766, 4: 973, 5: 1155, 6: 1386,
                      7: 1532, 8: 1751, "addl": 219},
           "std_ded": {1: 198, 2: 198, 3: 198, 4: 208, 5: 244, "6+": 279},
           "shelter_cap": 672, "homeless": 179.66, "min_benefit": 23},
}
NON_CONTIG = [2, 15, 66, 78]  # AK, HI, Guam, VI: own COLA tables
NE_ANOMALY_STATES = [9, 23, 25, 33, 36, 44]  # CT ME MA NH NY RI (exp8b)

USECOLS = ["STATE", "STATUS", "AMTERR", "RAWHSIZE", "RAWBEN", "RAWNET",
           "RAWGROSS", "RAWERND", "SHELDED", "FSDEPDED", "FSMEDEXP",
           "HOMEDED", "FSEARN", "FSBEN", "BENMAX", "FSELDER", "FSDIS",
           "FSCSDED", "SSI_CAP", "ELEMENT1"]


def eff_size(benmax, table):
    inv = {v: k for k, v in table.items() if k != "addl"}
    if benmax in inv:
        return inv[benmax]
    if benmax > table[8] and (benmax - table[8]) % table["addl"] == 0:
        return 8 + (benmax - table[8]) // table["addl"]
    return np.nan


def std_ded_stat(size, table):
    return table[size if size <= 5 else "6+"]


def load(fy):
    df = pd.read_csv(f"{DATA}/qcfy{fy}_csv/qc_pub_fy{fy}.csv",
                     usecols=USECOLS, low_memory=False)
    df = df[~df["STATE"].isin(NON_CONTIG)].copy()
    st = STATUTE[fy]
    for c in ["AMTERR", "RAWBEN", "RAWNET", "RAWGROSS", "RAWERND",
              "SHELDED", "FSDEPDED", "FSMEDEXP", "FSEARN", "FSBEN",
              "BENMAX", "FSELDER", "FSDIS", "SSI_CAP", "FSCSDED"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["FSDEPDED", "FSMEDEXP", "FSCSDED"]:
        df[c] = df[c].fillna(0)
    df["HOMEDED"] = pd.to_numeric(df["HOMEDED"],
                                  errors="coerce").fillna(1).astype(int)
    df["housed"] = df["HOMEDED"] == 1
    df["effsize"] = df["BENMAX"].map(lambda b: eff_size(b, st["benmax"]))
    # Standard-formula rows: not MN/MFIP, not SSI-CAP (PA runs PACAP;
    # SSI_CAP flags those cases and they skip the standard deductions).
    df["std_formula"] = (df["STATE"] != 27) & (df["SSI_CAP"] == 0)
    return df


def cleaned_set(df):
    """exp8a cleaned observation set (same definition as exp8b)."""
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


def clean_engine(df):
    """Rows where reported inputs are the engine's true inputs: QC agreed."""
    return df[(df["STATUS"] == 1) & (df["RAWBEN"] == df["FSBEN"])
              & df["std_formula"] & df["housed"]]


def interior(df, st):
    return df[(df["RAWBEN"] < df["BENMAX"] - 1)
              & (df["RAWBEN"] > st["min_benefit"] + 1)
              & (df["RAWNET"] > 0) & df["effsize"].notna()]


def fit_params(ok, st):
    """Fit effective engine parameters on clean-engine rows. Mirrors exp8b."""
    out = {}
    bm, btab = {}, st["benmax"]
    z = ok[(ok["RAWNET"] == 0) & (ok["RAWBEN"] > 0)]
    for s in range(1, 9):
        v = z[z["BENMAX"] == btab[s]]["RAWBEN"]
        if len(v) >= 30:
            bm[s] = {"fitted": float(v.median()), "n": int(len(v))}
    out["benmax"] = bm

    inn = interior(ok, st)
    x = inn["RAWNET"].to_numpy()
    y = (inn["BENMAX"] - inn["RAWBEN"]).to_numpy()
    out["benefit_rate"] = float(np.polyfit(x, y, 1)[0]) if len(inn) >= 30 \
        else None
    out["benefit_rate_n"] = int(len(inn))
    prod = 0.3 * inn["RAWNET"]
    pred = inn["BENMAX"] - inn["RAWBEN"]
    out["rounding_match"] = {
        name: float((f(prod).to_numpy() == pred.to_numpy()).mean())
        for name, f in [("ceil", np.ceil), ("round", np.round),
                        ("floor", np.floor)]} if len(inn) else {}

    small = ok[ok["BENMAX"].isin([btab[1], btab[2]])]
    pred_s = small["BENMAX"] - np.ceil(0.3 * small["RAWNET"])
    floored = small[pred_s < st["min_benefit"]]
    out["min_benefit"] = (float(floored["RAWBEN"].mode().iloc[0])
                          if len(floored) >= 10 else None)
    out["min_benefit_n"] = int(len(floored))
    out["min_benefit_mode_share"] = (
        float((floored["RAWBEN"] == out["min_benefit"]).mean())
        if len(floored) >= 10 else None)

    e = ok[ok["FSEARN"] > 0]
    out["earned_rate"] = float((e["RAWERND"] / e["FSEARN"]).median()) \
        if len(e) >= 30 else None
    out["earned_rate_n"] = int(len(e))
    if len(e) >= 30:
        er = 0.2 * e["FSEARN"]
        out["earned_rounding"] = {
            "floor": float((np.floor(er) == e["RAWERND"]).mean()),
            "round": float((np.round(er) == e["RAWERND"]).mean())}
    else:
        out["earned_rounding"] = {}

    c = ok[(ok["FSMEDEXP"] == 0) & (ok["RAWNET"] > 0)]
    impl = (c["RAWGROSS"] - c["RAWERND"] - c["FSDEPDED"] - c["FSCSDED"]
            - c["SHELDED"] - c["RAWNET"])
    sd = {}
    for s, stat in [(1, st["std_ded"][1]), (2, st["std_ded"][2]),
                    (3, st["std_ded"][3]), (4, st["std_ded"][4]),
                    (5, st["std_ded"][5]), ("6+", st["std_ded"]["6+"])]:
        v = impl[c["effsize"] == s] if s != "6+" else impl[c["effsize"] >= 6]
        v = v[v.notna()]
        if len(v) >= 30:
            sd[str(s)] = {"fitted": float(v.median()), "statutory": stat,
                          "within1": float((v - stat).abs().le(1).mean()),
                          "n": int(len(v))}
    out["std_ded"] = sd

    eld = (ok["FSELDER"] == 1) | (ok["FSDIS"] == 1)
    nz = ok["RAWNET"] > 0
    cap = st["shelter_cap"]
    nh = ok[(~eld) & (ok["SHELDED"] > 0) & nz]
    eh = ok[eld & (ok["SHELDED"] > 0) & nz]
    out["shelter"] = {
        "nonelder_frac_at_cap": float((nh["SHELDED"] == cap).mean())
        if len(nh) else None,
        "nonelder_frac_above_cap": float((nh["SHELDED"] > cap).mean())
        if len(nh) else None,
        "nonelder_max": float(nh["SHELDED"].max()) if len(nh) else None,
        "elder_max": float(eh["SHELDED"].max()) if len(eh) else None,
        "elder_frac_above_cap": float((eh["SHELDED"] > cap).mean())
        if len(eh) else None,
        "n_nonelder": int(len(nh)), "n_elder": int(len(eh)),
    }

    hs = ok[(ok["HOMEDED"] == 3) & (ok["SHELDED"] > 0)]
    out["homeless_n"] = int(len(hs))
    out["homeless_mode"] = float(hs["SHELDED"].mode().iloc[0]) \
        if len(hs) >= 5 else None
    return out


def shelter_anomaly_test(df, st, label):
    """exp8b New England pattern: non-elderly SHELDED > cap with the
    uncapped value entering the reported net-income identity 1:1.

    For each over-cap row, check whether RAWNET matches the net identity
    with the shelter deduction capped vs uncapped (within $1).
    """
    eld = (df["FSELDER"] == 1) | (df["FSDIS"] == 1)
    cap = st["shelter_cap"]
    over = df[(~eld) & (df["SHELDED"] > cap) & (df["RAWNET"] > 0)
              & df["effsize"].notna()].copy()
    res = {"label": label, "n_over_cap": int(len(over)),
           "n_nonelder_shelter": int(((~eld) & (df["SHELDED"] > 0)
                                     & (df["RAWNET"] > 0)).sum())}
    if not len(over):
        res.update({"uncapped_only": 0, "capped_only": 0, "both": 0,
                    "neither": 0})
        return res
    std = over["effsize"].map(lambda s: std_ded_stat(s, st["std_ded"]))
    base = (over["RAWGROSS"] - over["RAWERND"] - std - over["FSDEPDED"]
            - over["FSMEDEXP"] - over["FSCSDED"])
    uncapped = (base - over["SHELDED"] - over["RAWNET"]).abs() <= 1
    capped = (base - over["SHELDED"].clip(upper=cap)
              - over["RAWNET"]).abs() <= 1
    res.update({"uncapped_only": int((uncapped & ~capped).sum()),
                "capped_only": int((~uncapped & capped).sum()),
                "both": int((uncapped & capped).sum()),
                "neither": int((~uncapped & ~capped).sum()),
                "max_shelded": float(over["SHELDED"].max())})
    return res


def predict_statutory(df, st):
    bmax = df["BENMAX"]
    raw = bmax - np.ceil(0.30 * df["RAWNET"])
    fl = np.where(bmax.isin([st["benmax"][1], st["benmax"][2]]),
                  st["min_benefit"], -np.inf)
    return np.maximum(raw, fl)


def main():
    FYS = [2020, 2021, 2022, 2023, 2024]
    pa_fits, fleet_fits = {}, {}
    print("=== exp8c: PA parameter fits vs fleet vs statute ===\n")
    for fy in FYS:
        st = STATUTE[fy]
        df = load(fy)
        pa = df[df["STATE"] == 42]
        fleet = df[df["STATE"] != 42]
        pa_c, pa_info = cleaned_set(pa)
        fl_c, fl_info = cleaned_set(fleet)
        pa_ok = clean_engine(pa_c)
        fl_ok = clean_engine(fl_c)
        pa_fits[fy] = fit_params(pa_ok, st)
        fleet_fits[fy] = fit_params(fl_ok, st)
        print(f"FY{fy}: PA n={pa_info['n']} cleaned={pa_info['clean']} "
              f"(S1 exact {pa_info['keep_s1']}, 2/3 {pa_info['keep_23']}, "
              f"drop recoup {pa_info['drop_recoup']}, anom "
              f"{pa_info['drop_anom']}); clean-engine n={len(pa_ok)}; "
              f"fleet clean-engine n={len(fl_ok)}; "
              f"PA PACAP(SSI_CAP!=0) in cleaned: "
              f"{int((pa_c['SSI_CAP'] != 0).sum())}")

    def row(name, pa_v, fl_v, stat_v, fmt="{:.4f}", tol=1.0):
        flag = ""
        if pa_v is not None and fl_v is not None and abs(pa_v - fl_v) > tol:
            flag += " PA!=fleet"
        if pa_v is not None and abs(pa_v - stat_v) > tol:
            flag += " PA!=stat"
        if fl_v is not None and abs(fl_v - stat_v) > tol:
            flag += " FLEET!=stat(!)"
        print(f"  {name:28s} PA={fmt.format(pa_v) if pa_v is not None else 'n/a':>10s} "
              f"fleet={fmt.format(fl_v) if fl_v is not None else 'n/a':>10s} "
              f"stat={fmt.format(stat_v):>10s}{flag}")

    print("\n--- per-FY parameter comparison (tol $1 / 0.02 rate) ---")
    for fy in FYS:
        st, pf, ff = STATUTE[fy], pa_fits[fy], fleet_fits[fy]
        print(f"\nFY{fy} (cap ${st['shelter_cap']}, min ${st['min_benefit']}):")
        r = pf["benefit_rate"]
        row("30% rate (OLS slope)", r, ff["benefit_rate"], 0.30,
            tol=0.02)
        print(f"    PA n={pf['benefit_rate_n']}, fleet n={ff['benefit_rate_n']}; "
              f"PA rounding exact: { {k: round(v, 3) for k, v in pf['rounding_match'].items()} }; "
              f"fleet: { {k: round(v, 3) for k, v in ff['rounding_match'].items()} }")
        row("earned disregard", pf["earned_rate"], ff["earned_rate"], 0.20,
            tol=0.005)
        print(f"    PA n={pf['earned_rate_n']}, fleet n={ff['earned_rate_n']}; "
              f"PA earned rounding: { {k: round(v, 3) for k, v in pf['earned_rounding'].items()} }")
        mb = pf["min_benefit"]
        print(f"  min benefit: PA={mb} (n={pf['min_benefit_n']}, mode share "
              f"{pf['min_benefit_mode_share']}) fleet={ff['min_benefit']} "
              f"stat={st['min_benefit']}")
        for s, d in sorted(pf["std_ded"].items(),
                           key=lambda kv: (kv[0] == "6+", kv[0])):
            fd = ff["std_ded"].get(s, {})
            row(f"std ded size {s}", d["fitted"], fd.get("fitted"),
                d["statutory"], fmt="{:.0f}")
            print(f"      PA n={d['n']} within$1={d['within1']:.3f}; "
                  f"fleet n={fd.get('n')} within$1={fd.get('within1')}")
        for s in range(1, 5):
            if s in pf["benmax"]:
                d, fd = pf["benmax"][s], ff["benmax"].get(s, {})
                row(f"max allot size {s}", d["fitted"], fd.get("fitted"),
                    st["benmax"][s], fmt="{:.0f}")
        sh, fsh = pf["shelter"], ff["shelter"]
        print(f"  shelter: PA non-eld at-cap share {sh['nonelder_frac_at_cap']:.3f} "
              f"(n={sh['n_nonelder']}) above-cap share {sh['nonelder_frac_above_cap']:.3f} "
              f"max {sh['nonelder_max']}; fleet at-cap {fsh['nonelder_frac_at_cap']:.3f} "
              f"above-cap {fsh['nonelder_frac_above_cap']:.3f}; "
              f"PA elder max {sh['elder_max']} (n={sh['n_elder']})")
        print(f"  homeless: PA n={pf['homeless_n']} mode={pf['homeless_mode']} "
              f"fleet n={ff['homeless_n']} mode={ff['homeless_mode']} "
              f"stat recorded~{round(st['homeless'])}")

    print("\n=== shelter-cap anomaly test (exp8b New England pattern) ===")
    print("non-elderly, RAWNET>0, SHELDED>cap: does RAWNET match the net "
          "identity with the deduction capped vs uncapped?")
    for fy in FYS:
        st = STATUTE[fy]
        df = load(fy)
        pa_c, _ = cleaned_set(df[df["STATE"] == 42])
        fl_c, _ = cleaned_set(df[df["STATE"] != 42])
        ne_c, _ = cleaned_set(df[df["STATE"].isin(NE_ANOMALY_STATES)])
        for label, d, engine_only in [
                ("PA clean-engine", clean_engine(pa_c), True),
                ("PA error rows (suggestive)", pa_c[pa_c["STATUS"].isin([2, 3])], False),
                ("fleet clean-engine", clean_engine(fl_c), True),
                ("NE-six clean-engine", clean_engine(ne_c), True)]:
            r = shelter_anomaly_test(d, st, label)
            print(f"FY{fy} {r['label']}: over-cap n={r['n_over_cap']} "
                  f"(of {r['n_nonelder_shelter']} non-eld w/ shelter); "
                  f"uncapped-only={r['uncapped_only']} capped-only={r['capped_only']} "
                  f"both={r['both']} neither={r['neither']}"
                  + (f" max SHELDED={r['max_shelded']:.0f}" if r['n_over_cap'] else ""))

    print("\n=== output-side holdout: statutory formula on PA clean-engine rows ===")
    print("pred = max(BENMAX - ceil(0.3*RAWNET), minbenefit for 1-2 person)")
    for fy in FYS:
        st = STATUTE[fy]
        df = load(fy)
        pa_c, _ = cleaned_set(df[df["STATE"] == 42])
        fl_c, _ = cleaned_set(df[df["STATE"] != 42])
        pa_ok = clean_engine(pa_c).copy()
        fl_ok = clean_engine(fl_c).copy()
        for label, d in [("PA", pa_ok), ("fleet", fl_ok)]:
            dd = d[d["effsize"].notna()]
            e = (predict_statutory(dd, st) - dd["RAWBEN"]).abs()
            tail = dd[e > 1]
            pror = ((dd["RAWNET"] == 0) & (dd["RAWBEN"] < dd["BENMAX"] - 1))
            print(f"FY{fy} {label} (n={len(dd)}): exact {(e == 0).mean():.4f}, "
                  f"within $1 {(e <= 1).mean():.4f}, MAE ${e.mean():.2f}, "
                  f"tail>$1 n={len(tail)}, prorated(RAWNET=0 & RAWBEN<max) "
                  f"share={pror.mean():.4f} (n={int(pror.sum())})")

    print("\n=== PA SUA application spot-check (FY2024: HCSUA $750, LUA $401, tel $34) ===")
    df = load(2024)
    pa_c, _ = cleaned_set(df[df["STATE"] == 42])
    pa_ok = clean_engine(pa_c)
    sh = pa_ok["SHELDED"]
    print(f"PA FY2024 clean-engine SHELDED: n={len(sh)}, "
          f"share==401 (LUA): {(sh == 401).mean():.4f} (n={int((sh == 401).sum())}), "
          f"share==750 (HCSUA): {(sh == 750).mean():.4f}, "
          f"share==34 (tel): {(sh == 34).mean():.4f}")
    print("top SHELDED values:", sh.value_counts().head(8).to_dict())
    pacap = pa_c[pa_c["SSI_CAP"] != 0]
    print(f"PA FY2024 PACAP cases in cleaned set: n={len(pacap)}; "
          f"SHELDED values: {sorted(pacap['SHELDED'].dropna().unique())[:10]}")


if __name__ == "__main__":
    main()
