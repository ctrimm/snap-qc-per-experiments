"""Experiment 31 - adopt the dollar mechanisms as a generator default.

North-star gates: **calibration** (finding mix, element mix, dollar-error
marginal) and **transfer** (exp19's battery). Exp26 combined exp23's dollar
mechanisms (97 small-error mode, whole-unit ineligibility recoded as
earned/35, coarse-under rescale) with exp24's defaults and recalibrated,
landing finding L1 0.016, share <=$56 0.69, element L1 0.060. But the
recalibration lives only as in-memory fitting inside exp26's script: calling
dollar_mech.enable() alone (no recalibration) gives finding L1 0.103
(coordinator-verified). Adoption means the mechanisms work WITHOUT a
separate fitting step.

Stages:
  capture   - seed-set-A partial refit (exp26's exact seeds/n) capturing the
              full fitted tables (under scales, V, unit factor, eff_new,
              97-resolution coins) as JSON for the module port.
  refit_b   - full recalibration on seed set B (new seeds) for the
              stability comparison behind the design decision.
  rebaseline- calibration + transfer battery: baseline (stock, current
              defaults) vs adopted (module-default calibration, enabled via
              the new --dollar-mechanisms path), paired seeds 7/8, 20k.
  NOTE: the module constants are filled from `capture` output by hand
  (documented in the chronicle); `rebaseline` requires the edited module.

Usage:
    python3 experiments/exp31_adopt_dollar.py capture --real ... --dist ...
    python3 experiments/exp31_adopt_dollar.py refit_b --real ... --dist ...
    python3 experiments/exp31_adopt_dollar.py rebaseline --real ... --dist ...

Real microdata is held-out validation: aggregates are read, nothing
per-row is committed.
"""
import argparse
import copy
import csv
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR))                      # exp26 script
sys.path.insert(0, str(EXP_DIR.parent / "src"))        # synth package
import exp26_combine_dollar as e26                     # noqa: E402
from synth import dollar_mech, errors, household        # noqa: E402
from synth.codebook import element_bucket              # noqa: E402
from synth.distutil import load_dist                   # noqa: E402

REAL_DEFAULT = (Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv"
                / "qc_pub_fy2024.csv")
P_UNIT = dollar_mech.P_UNIT_DEFAULT
BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]
SEEDS = (7, 8)
N_CASES = 20000


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, float):
        return round(o, 6)
    return o


def refit(seed_pre, seed_eff, seed_cal97, seed_boost, real_meds, r_over,
          r_under, dist, boost_n=10000, label=""):
    """Full exp26 recalibration procedure on a given seed set. Returns the
    fitted values (the port's raw material)."""
    print(f"\n===== refit {label}: seeds pre={seed_pre} eff={seed_eff} "
          f"cal97={seed_cal97} boost={seed_boost} =====")
    over_target = (r_over - P_UNIT) / (1 - P_UNIT)
    under_target = r_under / (1 - P_UNIT)

    dollar_mech.enable()  # mech 1 on (exp26 small-under defaults); 4 off
    pre = e26.gen_cases(30000, seed_pre, dist, mech=True)
    scales = e26.fit_under_scales(pre, real_meds)
    v_per_case = sum(len(c["variances"]) for c in pre) / len(pre)
    print(f"recorded variances per case: {v_per_case:.4f}")

    dollar_mech.enable(under_scale=scales)  # add mechanism 4
    eff_new = e26.measure_eff(dist, 20000, seed=seed_eff)
    print("eff bucket:", json.dumps(eff_new["bucket"]))

    dist_b = dollar_mech.apply_unit_bucket_correction(dist, P_UNIT, v_per_case)
    dist_b["effectiveness"] = eff_new
    unit_factor = dist_b["_exp26"]["unit_bucket_factor"]
    print(f"unit bucket correction factor: {unit_factor}")

    coins97 = e26.calibrate_97(dist_b, 4000, seed=seed_cal97)
    inj = dict(dist_b["injection_rate"])
    inj["p_over_97_resolve"] = coins97
    dist_b["injection_rate"] = inj

    d_bal, r_final, boosts = e26.fit_direction_balance(
        dist_b, over_target, under_target, boost_n, seed_boost, P_UNIT)
    coins1 = e26.calibrate_phase1_dir(d_bal, dist, r_final, P_UNIT)
    dollar_mech.disable()

    return {
        "under_scales": scales,
        "v_per_case": v_per_case,
        "unit_factor": unit_factor,
        "eff_new": eff_new,
        "coins97": coins97,
        "boosts": boosts,
        "residual_final": {k: (r_final[k] if not isinstance(r_final[k], dict)
                               else dict(r_final[k])) for k in r_final},
        "phase1_coins": coins1,
    }


def stage_capture(args):
    """Seed-set A = exp26's exact seeds: capture the full fitted tables."""
    dist = load_dist(args.dist)
    real = e26.load_real(str(args.real))
    real_meds = e26.real_per_nature_medians(str(args.real))
    r_over = real["n_over"] / real["n"]
    r_under = real["n_under"] / real["n"]
    fit = refit(5000, 11, 21, 31, real_meds, r_over, r_under, dist,
                label="seed-set A (exp26 exact)")
    out = EXP_DIR / "exp31_capture_A.json"
    out.write_text(json.dumps(_jsonable(fit), indent=1))
    print(f"\nwrote {out}")


def stage_refit_b(args):
    """Seed-set B = new seeds: the stability comparison."""
    dist = load_dist(args.dist)
    real = e26.load_real(str(args.real))
    real_meds = e26.real_per_nature_medians(str(args.real))
    r_over = real["n_over"] / real["n"]
    r_under = real["n_under"] / real["n"]
    fit = refit(5001, 13, 23, 33, real_meds, r_over, r_under, dist,
                label="seed-set B (stability)")
    out = EXP_DIR / "exp31_refit_B.json"
    out.write_text(json.dumps(_jsonable(fit), indent=1))
    print(f"\nwrote {out}")


# --------------------------------------------------------------------------
# stage: rebaseline (calibration + transfer), baseline vs adopted
# --------------------------------------------------------------------------

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]


def gen_stock(n, seed, dist, persistent):
    rng = random.Random(seed)
    return [errors.inject(household.sample_household(rng), rng, dist,
                          max_attempts=12, persistent_buckets=persistent)
            for _ in range(n)]


def gen_adopted(n, seed, dist_ad, persistent):
    """Adopted path: mechanisms enabled (patches installed) + calibrated
    dist; the whole-unit draw layers on via inject_case."""
    rng = random.Random(seed)
    return [dollar_mech.inject_case(household.sample_household(rng), rng,
                                   dist_ad, max_attempts=12,
                                   persistent_buckets=persistent)
            for _ in range(n)]


def mixes(cases):
    f = Counter(c["finding"] for c in cases)
    n = len(cases)
    b = Counter()
    d_all, d_over, d_under = [], [], []
    nat = defaultdict(list)
    for c in cases:
        if c["finding"] == 2:
            d_over.append(c["dollar_error"])
            signed = c["dollar_error"]
        elif c["finding"] == 3:
            d_under.append(c["dollar_error"])
            signed = -c["dollar_error"]
        else:
            continue
        d_all.append(signed)
        if len(c["variances"]) == 1:
            v = c["variances"][0]
            nat[(c["finding"], v["nature"])].append(abs(signed))
    for c in cases:
        for v in c["variances"]:
            b[v["element_bucket"]] += 1
    v = sum(b.values())
    return {
        "finding": {k: f[k] / n for k in (1, 2, 3)},
        "elem_share": {k: b[k] / v for k in BUCKETS} if v else {},
        "per_case": {k: b[k] / n for k in BUCKETS},
        "d_all": d_all, "d_over": d_over, "d_under": d_under,
        "nat_med": {k: (statistics.median(x), len(x)) for k, x in nat.items()},
        "n": n,
    }


def l1(a, b):
    return sum(abs(a[k] - b.get(k, 0.0)) for k in a)


def dollar_stats(vals):
    ab = sorted(abs(x) for x in vals)
    n = len(ab)
    get = lambda p: ab[min(n - 1, int(p / 100 * n))] if n else float("nan")
    mean = statistics.fmean(ab) if n else float("nan")
    return {"n": n, "mean": mean, "p10": get(10), "p25": get(25),
            "p50": get(50), "p90": get(90), "p99": get(99),
            "le56": sum(1 for x in ab if x <= 56) / n if n else float("nan")}


def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def real_aggregates(path):
    from synth import params
    SUA_YES = {"3", "4", "5", "6", "7", "8"}
    finding = Counter()
    bucket = Counter()
    n = 0
    signed, overs, unders = [], [], []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            st = row["STATUS"].strip()
            finding[st] += 1
            amt = fnum(row["AMTERR"])
            if st == "2":
                signed.append(amt)
                overs.append(amt)
            elif st == "3":
                signed.append(-amt)
                unders.append(amt)
            for i in range(1, 10):
                e = (row[f"ELEMENT{i}"] or "").strip()
                if e:
                    bucket[element_bucket(int(e))] += 1
    v = sum(bucket.values())
    return {
        "finding": {1: finding["1"] / n, 2: finding["2"] / n,
                    3: finding["3"] / n},
        "elem_share": {b: bucket[b] / v for b in BUCKETS},
        "per_case": {b: bucket[b] / n for b in BUCKETS},
        "signed": signed, "overs": overs, "unders": unders, "n": n,
    }


# ---- transfer battery (exp19/exp24) ----

def synth_case_features(case):
    from synth import benefit as benefit_mod
    from synth import params
    f = case["issued_facts"]
    calc = benefit_mod.compute(f)
    size = f["hh_size"]
    mallot = params.max_allotment(size)
    issued = float(case["issued_benefit"])
    return {"hh_size": float(size), "earned": f["earned"],
            "unearned": f["unearned"], "shelter": f["shelter"],
            "sua": float(f["sua"]), "medical_exp": f["medical_exp"],
            "depcare": f["depcare"],
            "senior_disabled": float(f["senior_disabled"]),
            "issued_benefit": issued}


def real_row_features(row):
    from synth import params
    SUA_YES = {"3", "4", "5", "6", "7", "8"}
    size = int(fnum(row["CERTHHSZ"]))
    earned = fnum(row["FSEARN"])
    return {"hh_size": float(size), "earned": earned,
            "unearned": fnum(row["FSUNEARN"]), "shelter": fnum(row["SHELDED"]),
            "sua": 1.0 if row["SUA1"].strip() in SUA_YES else 0.0,
            "medical_exp": fnum(row["FSMEDEXP"]),
            "depcare": fnum(row["FSDEPDED"]),
            "senior_disabled": 1.0 if (fnum(row["FSNELDER"]) > 0 or
                                      fnum(row["FSNDIS"]) > 0) else 0.0,
            "issued_benefit": fnum(row["RAWBEN"])}


def load_real_rows(path):
    rows = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            status = row["STATUS"].strip()
            e1 = row.get("ELEMENT1", "").strip()
            rows.append((real_row_features(row),
                         element_bucket(int(e1)) if e1 and status != "1"
                         else None))
    return rows


def synth_rows(cases):
    return [(synth_case_features(c),
             c["variances"][0]["element_bucket"] if c["variances"] else None)
            for c in cases]


def evaluate(name, s_rows, r_rows, class_weight=None):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score
    sX = [[r[0][k] for k in V1] for r in s_rows]
    sy = [r[1] for r in s_rows]
    rX = [[r[0][k] for k in V1] for r in r_rows]
    ry = [r[1] for r in r_rows]
    clf = HistGradientBoostingClassifier(
        random_state=0, class_weight=class_weight).fit(sX, sy)
    pred = clf.predict(rX)
    acc = accuracy_score(ry, pred)
    macro = f1_score(ry, pred, average="macro", zero_division=0)
    per = f1_score(ry, pred, labels=BUCKETS, average=None, zero_division=0)
    print(f"{name}: acc={acc:.3f} macroF1={macro:.3f} "
          f"(train n={len(sX)}, classes={len(set(sy))})")
    for b, f in zip(BUCKETS, per):
        print(f"    F1 {b:10s} {f:.3f}")
    return acc, macro, dict(zip(BUCKETS, per))


def stage_rebaseline(args):
    assert hasattr(dollar_mech, "enable_adopted"), \
        "rebaseline needs the exp31 module port (enable_adopted)"
    dist = load_dist(args.dist)
    real = real_aggregates(str(args.real))
    real_meds = e26.real_per_nature_medians(str(args.real))
    r_dollar = dollar_stats(real["signed"])
    print(f"real: n={real['n']} finding "
          f"{real['finding'][1]:.3f}/{real['finding'][2]:.3f}/"
          f"{real['finding'][3]:.3f}")

    arms = {}
    for sd in SEEDS:
        print(f"\n--- seed {sd}: baseline (stock) ---", flush=True)
        dollar_mech.disable()
        b_p = gen_stock(N_CASES, sd, dist, persistent=True)
        b_r = gen_stock(N_CASES, sd, dist, persistent=False)
        print(f"--- seed {sd}: adopted (dollar mechanisms) ---", flush=True)
        dist_ad = dollar_mech.enable_adopted(dist)
        a_p = gen_adopted(N_CASES, sd, dist_ad, persistent=True)
        a_r = gen_adopted(N_CASES, sd, dist_ad, persistent=False)
        dollar_mech.disable()
        # keep mixes + transfer rows only (drop the heavy case dicts)
        packed = {}
        for k, v in (("base-persist", b_p), ("base-retry", b_r),
                     ("adopt-persist", a_p), ("adopt-retry", a_r)):
            packed[k] = (mixes(v),
                         [r for r in synth_rows(v) if r[1]],
                         sum(1 for c in v if c.get("unit_ineligible")))
        arms[sd] = packed

    # ---- calibration ----
    print("\n== CALIBRATION ==")
    for sd in SEEDS:
        print(f"\n-- seed {sd} --")
        packed = arms[sd]
        mm = {k: v[0] for k, v in packed.items()}
        for k, m in mm.items():
            fm = m["finding"]
            print(f"  {k:13s} finding {fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f} "
                  f"L1={l1(fm, real['finding']):.3f}")
        print("  per-case element ratios (1.0x = matches real):")
        for b in BUCKETS:
            print(f"    {b:10s}" + "".join(
                f"{(mm[k]['per_case'][b] / real['per_case'][b]):>13.2f}x"
                for k in mm))
        print("  element share L1 vs real:",
              " ".join(f"{k}={l1(mm[k]['elem_share'], real['elem_share']):.3f}"
                       for k in mm))
        print("  dollar marginals (absolute $, error cases):")
        ds = {k: dollar_stats(m["d_all"]) for k, m in mm.items()}
        print(f"  {'':13s}{'p10':>6}{'p25':>6}{'p50':>6}{'p90':>6}{'p99':>6}"
              f"{'mean':>6}{'<=56':>6}")
        print(f"  {'real':13s}{r_dollar['p10']:6.0f}{r_dollar['p25']:6.0f}"
              f"{r_dollar['p50']:6.0f}{r_dollar['p90']:6.0f}"
              f"{r_dollar['p99']:6.0f}{r_dollar['mean']:6.0f}"
              f"{r_dollar['le56']:6.2f}")
        for k, d in ds.items():
            print(f"  {k:13s}{d['p10']:6.0f}{d['p25']:6.0f}{d['p50']:6.0f}"
                  f"{d['p90']:6.0f}{d['p99']:6.0f}{d['mean']:6.0f}"
                  f"{d['le56']:6.2f}")
        print("  over/under asymmetry (absolute $ within finding):")
        for k, m in mm.items():
            so, su = sorted(m["d_over"]), sorted(m["d_under"])
            if so and su:
                medO, medU = statistics.median(so), statistics.median(su)
                mnO, mnU = statistics.fmean(so), statistics.fmean(su)
                p90O, p90U = so[int(0.9 * len(so))], su[int(0.9 * len(su))]
                ok = "".join("Y" if x else "n" for x in
                             (medO > medU, mnO > mnU, p90O > p90U))
            else:
                medO = medU = mnO = mnU = 0
                ok = "---"
            print(f"    {k:13s} medO={medO:5.0f} medU={medU:5.0f} "
                  f"mnO={mnO:5.0f} mnU={mnU:5.0f} signs(med/mn/p90)={ok}")
        print(f"  real asymmetry: medO={statistics.median(real['overs']):.0f} "
              f"medU={statistics.median(real['unders']):.0f} "
              f"mnO={statistics.fmean(real['overs']):.0f} "
              f"mnU={statistics.fmean(real['unders']):.0f}")
        print("  per-nature medians (single-variance; 52-under + 97 watches):")
        for tag, nat in (("under", 44), ("under", 57), ("under", 52),
                         ("under", 97), ("over", 97)):
            r_med, r_n = real_meds.get((tag, nat), (float("nan"), 0))
            cells = []
            for k, m in mm.items():
                s_med, s_n = m["nat_med"].get((2 if tag == "over" else 3, nat),
                                             (float("nan"), 0))
                cells.append(f"{k}={s_med:.0f}(n={s_n})")
            print(f"    {tag} nat{nat}: real={r_med:.0f}(n={r_n}) "
                  + " ".join(cells))
        n_unit = {k: v[2] for k, v in packed.items()}
        print("  whole-unit cases:", {k: f"{v}/{N_CASES}" for k, v in n_unit.items()})

    # ---- transfer ----
    print("\n== TRANSFER (exp19 battery: element, v1, HGB) ==")
    real_rows = load_real_rows(str(args.real))
    summary = {}
    for sd in SEEDS:
        print(f"\n-- seed {sd} --")
        rows = {k: v[1] for k, v in arms[sd].items()}
        keep = sorted(set(r[1] for r in rows["base-persist"]) |
                      set(r[1] for r in rows["adopt-persist"]))
        r_rows = [r for r in real_rows if r[1] in set(keep)]
        print(f"real test rows: {len(r_rows)} (buckets: {keep})")
        print("(a) persistent + unbalanced:")
        summary[(sd, "base-a")] = evaluate(f"s{sd}-base-a",
                                           rows["base-persist"], r_rows)
        summary[(sd, "adopt-a")] = evaluate(f"s{sd}-adopt-a",
                                            rows["adopt-persist"], r_rows)
        print("(b) persistent + class_weight=balanced:")
        summary[(sd, "base-b")] = evaluate(f"s{sd}-base-b",
                                           rows["base-persist"], r_rows,
                                           class_weight="balanced")
        summary[(sd, "adopt-b")] = evaluate(f"s{sd}-adopt-b",
                                            rows["adopt-persist"], r_rows,
                                            class_weight="balanced")
        print("(c) retry-loop + class_weight=balanced:")
        summary[(sd, "base-c")] = evaluate(f"s{sd}-base-c",
                                           rows["base-retry"], r_rows,
                                           class_weight="balanced")
        summary[(sd, "adopt-c")] = evaluate(f"s{sd}-adopt-r",
                                            rows["adopt-retry"], r_rows,
                                            class_weight="balanced")
    print("\n== transfer summary (acc / macroF1) ==")
    for sd in SEEDS:
        for arm in ("a", "b", "c"):
            ba, ma, _ = summary[(sd, f"base-{arm}")]
            aa, am, _ = summary[(sd, f"adopt-{arm}")]
            print(f"  seed {sd} arm {arm}: base {ba:.3f}/{ma:.3f}  "
                  f"adopt {aa:.3f}/{am:.3f}  "
                  f"delta {aa-ba:+.3f}/{am-ma:+.3f}")
    print("\nper-bucket F1 (adopt-b vs base-b, both seeds):")
    for b in BUCKETS:
        cells = " ".join(
            f"s{sd}:B{summary[(sd,'base-b')][2][b]:.3f}/A{summary[(sd,'adopt-b')][2][b]:.3f}"
            for sd in SEEDS)
        print(f"  {b:10s} {cells}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["capture", "refit_b", "rebaseline"])
    ap.add_argument("--real", default=str(REAL_DEFAULT))
    ap.add_argument("--dist", default=str(EXP_DIR / "dist.json"))
    args = ap.parse_args()
    {"capture": stage_capture, "refit_b": stage_refit_b,
     "rebaseline": stage_rebaseline}[args.stage](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
