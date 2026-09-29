"""Experiment 42 - depcare / medical deep dive.

North-star gate: calibration. Depcare is at ~0.41x and medical at ~0.53x of
real variance-element shares. Exp12 added kid-gated depcare (0.03x->0.56x,
slipped to 0.41x); exp11 added senior-conditioned mixes for medical
(0.11x->0.67x, slipped to ~0.53x). Hypothesis: the residuals have identifiable
missing mechanisms discoverable by close quantitative analysis of real error
cases.

Real side: FY2020-2024 QC public-use files (held out; NEVER committed).
Variances = per-case ELEMENT1-9 / NATURE1-9 / AGENCY1-9 / AMOUNT1-9 arrays.
Case features: FSNKID (kids), FSNK0T4 (kids 0-4), FSNELDER, FSNDIS,
earner = (FSEARN > 0) or any EMPSTA in {3..8} (military/farm/self/employee),
FSDEPDED > 0 (depcare deduction on file), FSMEDEXP / FSMEDDED (medical).

Synth side: 40k cases from src/synth/generate.py (seed 7, experiments/dist.json).
Variances carry element_bucket/nature/cause; facts carry n_kids, earned,
senior_disabled, medical_exp, depcare. Synth dollar size for a single-variance
case is proxied by the case's signed dollar_error (issued - correct).

Usage:
    python3 experiments/exp42_depcare_medical_deepdive.py \
        --real-dir ~/workspace/snap-qc-data/raw --synth /tmp/exp42_synth.csv
Writes /tmp/exp42_results.json and prints the tables for the chronicle.
"""
import argparse
import csv
import glob
import json
import os
import statistics
import sys

# import the repo's codebook read-only for labels/bucket mapping
sys.path.insert(0, os.path.expanduser("~/workspace/snap-qc-per-experiments"))
from src.synth.codebook import (NATURE_LABELS, CAUSE_BUCKETS, element_bucket,
                                cause_bucket)

DEPCARE_EL, MEDICAL_EL = 323, 365
WORK_EMPSTA = {"3", "4", "5", "6", "7", "8"}


def fnum(x):
    try:
        return float(str(x).strip())
    except Exception:
        return 0.0


def load_real(real_dir):
    """Return list of case dicts with variances + household features."""
    cases = []
    years = []
    for year in ("2020", "2021", "2022", "2023", "2024"):
        pats = glob.glob(os.path.join(real_dir, f"qcfy{year}_csv", "*.csv"))
        if not pats:
            continue
        years.append(year)
        with open(pats[0], newline="") as f:
            for row in csv.DictReader(f):
                n_kids = int(fnum(row.get("FSNKID", 0)))
                n_k04 = int(fnum(row.get("FSNK0T4", 0)))
                n_eld = int(fnum(row.get("FSNELDER", 0)))
                n_dis = int(fnum(row.get("FSNDIS", 0)))
                # per-person fallback for senior/disabled (FS fields can lag)
                per_sen = per_dis = False
                earner = fnum(row.get("FSEARN", 0)) > 0
                for i in range(1, 19):
                    fs = row.get(f"FSAFIL{i}", "").strip()
                    if fs not in ("1", "2"):
                        continue  # not in SNAP unit
                    a = fnum(row.get(f"AGE{i}", 0))
                    if 60 <= a <= 120:
                        per_sen = True
                    if row.get(f"DIS{i}", "").strip() == "1":
                        per_dis = True
                    if not earner and row.get(f"EMPSTA{i}", "").strip() in WORK_EMPSTA:
                        earner = True
                depded_pos = fnum(row.get("FSDEPDED", 0)) > 0
                dpcost_pos = any(fnum(row.get(f"DPCOST{i}", 0)) > 0 for i in range(1, 19))
                medexp = fnum(row.get("FSMEDEXP", 0))
                medded_pos = fnum(row.get("FSMEDDED", 0)) > 0
                senior_dis = (n_eld > 0 or n_dis > 0 or per_sen or per_dis)
                variances = []
                for i in range(1, 10):
                    el = row.get(f"ELEMENT{i}", "").strip()
                    if not el or el == "0":
                        continue
                    try:
                        elc = int(el)
                    except ValueError:
                        continue
                    nat = row.get(f"NATURE{i}", "").strip()
                    ag = row.get(f"AGENCY{i}", "").strip()
                    amt = fnum(row.get(f"AMOUNT{i}", 0))
                    variances.append({
                        "element": elc,
                        "bucket": element_bucket(elc),
                        "nature": int(nat) if nat.isdigit() else None,
                        "cause": cause_bucket(int(ag)) if ag.isdigit() else "other",
                        "cause_raw": int(ag) if ag.isdigit() else None,
                        "amount": amt,
                    })
                cases.append({
                    "year": year,
                    "kids": n_kids > 0,
                    "n_kids": n_kids,
                    "kids04": n_k04 > 0,
                    "n_k04": n_k04,
                    "senior_dis": senior_dis,
                    "n_eld": n_eld,
                    "n_dis": n_dis,
                    "elderly_only": senior_dis and n_dis == 0 and not per_dis,
                    "earner": earner,
                    "depded_pos": depded_pos,
                    "dpcost_pos": dpcost_pos,
                    "medexp": medexp,
                    "medexp_pos": medexp > 0,
                    "medexp_gt35": medexp > 35,
                    "medded_pos": medded_pos,
                    "variances": variances,
                })
    return cases, years


def load_synth(path):
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            facts = r["facts"]
            cases.append({
                "kids": facts.get("n_kids", 0) > 0,
                "n_kids": facts.get("n_kids", 0),
                # synth has no young-kid concept: mark unavailable
                "kids04": None,
                "senior_dis": bool(facts.get("senior_disabled", 0)),
                "earner": fnum(facts.get("earned", 0)) > 0,
                "depded_pos": fnum(facts.get("depcare", 0)) > 0,
                "medexp_pos": fnum(facts.get("medical_exp", 0)) > 0,
                "medexp": fnum(facts.get("medical_exp", 0)),
                # synth does not apply the $35 offset; proxy the calculated
                # deduction as max(0, expenses - 35)
                "medexp_gt35": fnum(facts.get("medical_exp", 0)) > 35,
                "medded_pos": fnum(facts.get("medical_exp", 0)) > 35,
                # synth n_elderly/n_disabled are 0/1 flags
                "elderly_only": fnum(facts.get("n_elderly", 0)) > 0
                                and fnum(facts.get("n_disabled", 0)) == 0,
                "variances": [{
                    "element": v["element"],
                    "bucket": v["element_bucket"],
                    "nature": v["nature"],
                    "cause": cause_bucket(v["cause"]) if isinstance(v.get("cause"), int) else "other",
                    "cause_raw": v.get("cause"),
                } for v in r["variances"]],
                "finding": r["finding"],
                "dollar_error": abs(r["issued_benefit"] - r["correct_benefit"]),
            })
    return cases


def el_variances(cases, bucket):
    """All variances in the bucket (real: has amount; synth: no amount)."""
    return [v for c in cases for v in c["variances"] if v["bucket"] == bucket]


def has_bucket(c, bucket):
    return any(v["bucket"] == bucket for v in c["variances"])


def mix(counter, tot=None):
    tot = tot if tot is not None else sum(counter.values())
    if not tot:
        return {}
    return {k: round(v / tot, 4) for k, v in sorted(counter.items())}


def tab(counter):
    return mix(counter)


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def stratum_rates(cases, bucket, feats):
    """P(case has >=1 bucket variance | stratum) per stratum tuple."""
    cells = {}
    for c in cases:
        key = tuple(bool(c[f]) for f in feats)
        n, e = cells.get(key, (0, 0))
        cells[key] = (n + 1, e + (1 if has_bucket(c, bucket) else 0))
    out = {}
    for key, (n, e) in sorted(cells.items()):
        out[key] = {"n": n, "n_err": e, "rate": e / n if n else 0.0}
    return out


def project_draw_fix(synth_cases, real_cases, bucket, feats):
    """If the synth draw matched the REAL per-stratum rates (holding the synth
    case mix fixed), what would the overall P(case has bucket variance) be?
    Returns (synth_rate, projected_rate, real_rate)."""
    s_rates = stratum_rates(synth_cases, bucket, feats)
    r_rates = stratum_rates(real_cases, bucket, feats)
    s_by = {}
    for c in synth_cases:
        key = tuple(bool(c[f]) for f in feats)
        n, e = s_by.get(key, (0, 0))
        s_by[key] = (n + 1, e + (1 if has_bucket(c, bucket) else 0))
    proj_num = proj_den = 0
    for key, (n, e) in s_by.items():
        r = r_rates.get(key, {}).get("rate", 0.0)
        proj_num += n * r
        proj_den += n
    synth_rate = sum(e for _, e in s_by.values()) / max(proj_den, 1)
    real_rate = sum(1 for c in real_cases if has_bucket(c, bucket)) / max(len(real_cases), 1)
    return synth_rate, proj_num / max(proj_den, 1), real_rate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real-dir", required=True)
    ap.add_argument("--synth", required=True)
    args = ap.parse_args()

    real, years = load_real(args.real_dir)
    synth = load_synth(args.synth)
    print(f"real: {len(real)} cases, years {years}; synth: {len(synth)} cases")

    real24 = [c for c in real if c["year"] == "2024"]
    res = {"n_real": len(real), "n_real24": len(real24), "n_synth": len(synth)}

    # ---------- A. overall element shares ----------
    from collections import Counter
    rc, sc = Counter(), Counter()
    for c in real:
        for v in c["variances"]:
            rc[v["bucket"]] += 1
    for c in synth:
        for v in c["variances"]:
            sc[v["bucket"]] += 1
    rtot, stot = sum(rc.values()), sum(sc.values())
    print("\n== A. variance-element shares (all years pooled) ==")
    print(f"{'bucket':>10} {'real_n':>9} {'real%':>7} {'synth_n':>9} {'synth%':>7} {'ratio':>6}")
    for b in sorted(set(rc) | set(sc)):
        rp, sp = rc[b] / rtot, sc[b] / stot
        print(f"{b:>10} {rc[b]:>9} {rp:>7.4f} {sc[b]:>9} {sp:>7.4f} {sp/rp:>6.2f}x")
        res[f"share_{b}"] = {"real": round(rp, 5), "synth": round(sp, 5),
                             "ratio": round(sp / rp, 3)}

    # ---------- B. nature / cause mixes for depcare, medical ----------
    for bucket in ("depcare", "medical"):
        rv, sv = el_variances(real, bucket), el_variances(synth, bucket)
        print(f"\n== B. {bucket}: real n={len(rv)}, synth n={len(sv)} ==")
        rn = Counter(v["nature"] for v in rv if v["nature"])
        sn = Counter(v["nature"] for v in sv if v["nature"])
        rnt, snt = sum(rn.values()), sum(sn.values())
        print(f"{'nature':>7} {'label':<52} {'real%':>6} {'synth%':>7}")
        for n in sorted(set(rn) | set(sn)):
            lab = NATURE_LABELS.get(n, "?")
            print(f"{n:>7} {lab:<52} {rn[n]/rnt:>6.3f} "
                  f"{sn[n]/snt:>7.3f}")
        rcau = Counter(v["cause"] for v in rv)
        scau = Counter(v["cause"] for v in sv)
        print(f"{'cause':>8} {'real%':>6} {'synth%':>7}")
        for k in sorted(set(rcau) | set(scau)):
            print(f"{k:>8} {rcau[k]/len(rv):>6.3f} {scau[k]/len(sv):>7.3f}")
        res[f"{bucket}_nature"] = {"real": mix(rn), "synth": mix(sn)}
        res[f"{bucket}_cause"] = {"real": mix(rcau, len(rv)), "synth": mix(scau, len(sv))}

    # ---------- C. depcare conditionals ----------
    print("\n== C. depcare: real conditional rates ==")
    for feats, label in [
        (("kids", "earner"), "kids x earner"),
        (("kids", "depded_pos"), "kids x depded>0"),
        (("kids", "earner", "depded_pos"), "kids x earner x depded>0"),
    ]:
        rt = stratum_rates(real, "depcare", feats)
        st = stratum_rates(synth, "depcare", feats)
        print(f"--- {label} ---")
        print(f"{'stratum':>28} {'real_n':>9} {'real%':>7} "
              f"{'syn_n':>8} {'syn%':>6}")
        for key in sorted(set(rt) | set(st)):
            r = rt.get(key, {"n": 0, "rate": float("nan")})
            s = st.get(key, {"n": 0, "rate": float("nan")})
            print(f"{str(key):>28} {r['n']:>9} {r['rate']*100:>7.3f} "
                  f"{s['n']:>8} {s['rate']*100:>6.3f}")
        res[f"depcare_strata_{label.replace(' ', '_')}"] = {
            str(k): {"real": rt.get(k), "synth": st.get(k)} for k in set(rt) | set(st)}

    # depcare: real-only kids04 cut (synth has no young-kid concept)
    print("--- kids x kids04 [REAL ONLY] ---")
    rt = stratum_rates(real, "depcare", ("kids", "kids04"))
    for key in sorted(rt):
        r = rt[key]
        print(f"{str(key):>28} {r['n']:>9} {r['rate']*100:>7.3f}")
    res["depcare_strata_kids_x_kids04_realonly"] = {str(k): v for k, v in rt.items()}

    # depcare nature x household cut (real only - where do the errors live?)
    rv = el_variances(real, "depcare")
    print("\n== C2. real depcare: nature x earner / depded ==")
    for feats, label in [(("earner",), "earner"), (("depded_pos",), "depded_pos"),
                         (("kids04",), "kids04")]:
        d = {}
        for c in real:
            for v in c["variances"]:
                if v["bucket"] != "depcare":
                    continue
                key = tuple(bool(c[f]) for f in feats)
                d.setdefault(key, Counter())[v["nature"]] += 1
        for key in sorted(d):
            tot = sum(d[key].values())
            top = ", ".join(f"{n}:{d[key][n]/tot:.2f}" for n in sorted(d[key]))
            print(f"  {label}={key}: n={tot} nature mix -> {top}")

    # ---------- D. medical conditionals ----------
    print("\n== D. medical: real conditional rates ==")
    for feats, label in [
        (("senior_dis", "earner"), "senior_dis x earner"),
        (("senior_dis", "medexp_pos"), "senior_dis x medexp>0"),
        (("senior_dis", "medexp_gt35"), "senior_dis x medexp>35"),
        (("senior_dis", "medded_pos"), "senior_dis x medded>0"),
        (("elderly_only", "earner"), "elderly_only x earner"),
    ]:
        rt = stratum_rates(real, "medical", feats)
        st = stratum_rates(synth, "medical", feats)
        print(f"--- {label} ---")
        print(f"{'stratum':>24} {'real_n':>9} {'real%':>7} "
              f"{'syn_n':>8} {'syn%':>6}")
        for key in sorted(set(rt) | set(st)):
            r = rt.get(key, {"n": 0, "rate": float("nan")})
            s = st.get(key, {"n": 0, "rate": float("nan")})
            print(f"{str(key):>24} {r['n']:>9} {r['rate']*100:>7.3f} "
                  f"{s['n']:>8} {s['rate']*100:>6.3f}")
        res[f"medical_strata_{label.replace(' ', '_')}"] = {
            str(k): {"real": rt.get(k), "synth": st.get(k)} for k in set(rt) | set(st)}

    # medical threshold clustering: FSMEDEXP distribution
    print("\n== D2. medical: FSMEDEXP threshold clustering (real, senior_dis cases) ==")
    sd = [c for c in real if c["senior_dis"]]
    sd_med = [c for c in sd if has_bucket(c, "medical")]
    bins = [(0, 0), (0.01, 35), (35.01, 50), (50.01, 100), (100.01, 200), (200.01, 1e9)]
    print(f"{'FSMEDEXP bin':>18} {'all_sd n':>9} {'med_err n':>10} {'rate%':>7}")
    for lo, hi in bins:
        n_all = sum(1 for c in sd if lo <= c["medexp"] <= hi)
        n_err = sum(1 for c in sd_med if lo <= c["medexp"] <= hi)
        print(f"{f'{lo}-{hi}':>18} {n_all:>9} {n_err:>10} "
              f"{(100*n_err/n_all if n_all else 0):>7.3f}")
    res["medical_threshold_bins"] = [
        {"lo": lo, "hi": hi,
         "n_all": sum(1 for c in sd if lo <= c["medexp"] <= hi),
         "n_err": sum(1 for c in sd_med if lo <= c["medexp"] <= hi)}
        for lo, hi in bins]

    # medical nature x medexp cut (real only)
    print("\n== D3. real medical: nature x medexp>0 / medded>0 ==")
    for feats, label in [(("medexp_pos",), "medexp_pos"), (("medded_pos",), "medded_pos")]:
        d = {}
        for c in real:
            for v in c["variances"]:
                if v["bucket"] != "medical":
                    continue
                key = tuple(bool(c[f]) for f in feats)
                d.setdefault(key, Counter())[v["nature"]] += 1
        for key in sorted(d):
            tot = sum(d[key].values())
            top = ", ".join(f"{n}:{d[key][n]/tot:.2f}" for n in sorted(d[key]))
            print(f"  {label}={key}: n={tot} nature mix -> {top}")

    # ---------- E. dollar sizes ----------
    print("\n== E. dollar-error size: real per-variance AMOUNT vs "
          "synth single-variance dollar_error ==")
    for bucket in ("depcare", "medical"):
        r_amt = [v["amount"] for v in el_variances(real, bucket) if v["amount"] > 0]
        s_amt = [c["dollar_error"] for c in synth
                 if sum(1 for v in c["variances"] if v["bucket"] == bucket) == 1
                 and all(v["bucket"] == bucket for v in c["variances"])]
        qs = [0.25, 0.50, 0.75, 0.90]
        rl = [round(pct(r_amt, q), 1) for q in qs]
        sl = [round(pct(s_amt, q), 1) for q in qs]
        print(f"{bucket}: real n={len(r_amt)} quants {dict(zip(['p25','p50','p75','p90'], rl))} "
              f"mean={statistics.fmean(r_amt):.1f}")
        print(f"{bucket}: synth n={len(s_amt)} quants {dict(zip(['p25','p50','p75','p90'], sl))} "
              f"mean={statistics.fmean(s_amt):.1f}")
        res[f"{bucket}_dollars"] = {"real_n": len(r_amt), "real_q": rl,
                                    "real_mean": round(statistics.fmean(r_amt), 1),
                                    "synth_n": len(s_amt), "synth_q": sl,
                                    "synth_mean": round(statistics.fmean(s_amt), 1)}

    # ---------- F. draw-fix projections (effect-size estimates) ----------
    print("\n== F. draw-fix projections: match real per-stratum rates, "
          "hold synth case mix ==")
    for bucket, featsets in [
        ("depcare", [[["kids", "earner"], ["kids", "earner", "depded_pos"],
                      ["kids"]]]),
        ("medical", [[["senior_dis", "earner"], ["senior_dis", "medexp_pos"],
                      ["senior_dis"]]]),
    ]:
        for feats in featsets[0]:
            s_rate, proj, r_rate = project_draw_fix(synth, real, bucket, feats)
            cur = s_rate / r_rate if r_rate else float("nan")
            new = proj / r_rate if r_rate else float("nan")
            print(f"{bucket} | strata={feats}: synth {s_rate:.4f} vs real "
                  f"{r_rate:.4f} (now {cur:.2f}x) -> projected {proj:.4f} "
                  f"({new:.2f}x)")
            res[f"proj_{bucket}_{'_'.join(feats)}"] = {
                "synth": round(s_rate, 5), "proj": round(proj, 5),
                "real": round(r_rate, 5), "now_x": round(cur, 3), "new_x": round(new, 3)}

    with open("/tmp/exp42_results.json", "w") as f:
        json.dump(res, f, indent=2, default=str)
    print("\nresults -> /tmp/exp42_results.json")


if __name__ == "__main__":
    sys.exit(main())
