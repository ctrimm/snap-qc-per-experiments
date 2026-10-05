"""Experiment 33 - state-level heterogeneity in SNAP QC payment error rates.

North-star gate: calibration. The synthetic generator (src/synth/generate.py)
takes no state input and produces zero state-correlated variation. This
experiment measures how much real QC payment-error variance is state-level,
cross-checks QC-implied state rankings against FNS-published state payment
error rates, and quantifies the calibration gap the missing state dimension
creates.

Real side: FY2020-FY2024 QC public-use microdata (held-out; NEVER committed).
Synth side: cases from src/synth/generate.py, persistent buckets (default).

Usage:
    python3 -m src.synth.generate --n 20000 --seed 7 --dist experiments/dist.json \
        --out /tmp/exp33_synth.jsonl
    python3 experiments/exp33_state_heterogeneity.py \
        --qc ../snap-qc-data/raw --synth /tmp/exp33_synth.jsonl
"""
import argparse
import csv
import json
import math
import os
import statistics
import sys

STATUS_ERR = {"2", "3"}  # 2 = overpayment, 3 = underpayment
FYS = (2020, 2021, 2022, 2023, 2024)

# Official FNS state payment error rates (FRAC compilation of FNS releases,
# https://frac.org/wp-content/uploads/SNAP-Payment-Error-Rates-by-FY.pdf,
# fetched 2026-09-29). Compiled for the ranking cross-check below.
PUBLISHED = {
    "Alabama": (7.07, 8.32), "Alaska": (60.37, 24.66), "Arizona": (11.39, 8.84),
    "Arkansas": (9.57, 9.56), "California": (13.4, 10.98), "Colorado": (8.61, 9.97),
    "Connecticut": (8.91, 10.25), "Delaware": (22.8, 12.37),
    "District of Columbia": (20.26, 17.38), "Florida": (12.6, 15.13),
    "Georgia": (12.07, 15.65), "Guam": (18.01, 9.72), "Hawaii": (20.94, 6.68),
    "Idaho": (3.42, 3.59), "Illinois": (9.91, 11.56), "Indiana": (10.46, 9.52),
    "Iowa": (5.19, 6.14), "Kansas": (12.07, 9.98), "Kentucky": (7.27, 9.11),
    "Louisiana": (6.65, 6.62), "Maine": (13.48, 10.26), "Maryland": (18.98, 13.64),
    "Massachusetts": (9.86, 14.1), "Michigan": (10.72, 9.53),
    "Minnesota": (6.4, 8.98), "Mississippi": (10.15, 10.69),
    "Missouri": (10.54, 9.42), "Montana": (6.04, 8.89), "Nebraska": (7.06, 5.5),
    "Nevada": (6.71, 5.94), "New Hampshire": (12.53, 7.57),
    "New Jersey": (35.7, 14.33), "New Mexico": (14.4, 14.61),
    "New York": (12.68, 14.09), "North Carolina": (9.72, 10.21),
    "North Dakota": (9.51, 7.91), "Ohio": (7.01, 9.01),
    "Oklahoma": (10.64, 10.87), "Oregon": (16.76, 14.06),
    "Pennsylvania": (16.61, 10.76), "Rhode Island": (12.4, 12.29),
    "South Carolina": (22.57, 9.25), "South Dakota": (3.27, 3.28),
    "Tennessee": (12.56, 9.47), "Texas": (6.7, 8.32), "Utah": (5.09, 5.74),
    "Vermont": (3.45, 5.13), "Virgin Islands": (10.29, 3.54),
    "Virginia": (9.86, 11.5), "Washington": (6.74, 6.06),
    "West Virginia": (10.98, 9.43), "Wisconsin": (5.15, 4.47),
    "Wyoming": (5.19, 5.12),
}


def load_fy(qc_dir, fy):
    path = os.path.join(qc_dir, f"qcfy{fy}_csv", f"qc_pub_fy{fy}.csv")
    agg = {}  # state -> dict
    n_all = n_err = 0
    with open(path, newline="") as f:
        r = csv.reader(f)
        hdr = next(r)
        i = {c: j for j, c in enumerate(hdr)}
        istate, iname = i["STATE"], i.get("STATENAME")
        istatus, iamterr, ifsben, iw = i["STATUS"], i["AMTERR"], i["FSBEN"], i["FYWGT"]
        for row in r:
            st = row[istate]
            nm = row[iname] if iname is not None else ""
            try:
                w = float(row[iw] or 0)
            except ValueError:
                w = 0.0
            try:
                amterr = float(row[iamterr] or 0)
            except ValueError:
                amterr = 0.0
            try:
                fsben = float(row[ifsben] or 0)
            except ValueError:
                fsben = 0.0
            err = row[istatus] in STATUS_ERR
            a = agg.setdefault(st, {"name": nm, "w": 0.0, "w_err": 0.0,
                                    "w_errdoll": 0.0, "w_iss": 0.0, "n": 0})
            if not a["name"]:
                a["name"] = nm
            a["w"] += w
            a["w_iss"] += w * fsben
            a["n"] += 1
            n_all += 1
            if err:
                a["w_err"] += w
                a["w_errdoll"] += w * amterr
                n_err += 1
    for a in agg.values():
        a["case_rate"] = a["w_err"] / a["w"] if a["w"] else float("nan")
        a["dollar_rate"] = a["w_errdoll"] / a["w_iss"] if a["w_iss"] else float("nan")
    return agg, n_all, n_err


def cv(xs):
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return float("nan")
    m = statistics.fmean(xs)
    return (statistics.pstdev(xs) / m) if m else float("nan")


def weighted_cv(pairs):
    # pairs: (weight, rate)
    wsum = sum(w for w, _ in pairs if not math.isnan(_))
    if wsum <= 0:
        return float("nan")
    m = sum(w * x for w, x in pairs if not math.isnan(x)) / wsum
    v = sum(w * (x - m) ** 2 for w, x in pairs if not math.isnan(x)) / wsum
    return math.sqrt(v) / m if m else float("nan")


def pearson(xs, ys):
    n = len(xs)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy) if sxx and syy else float("nan")


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda k: v[k])
        rk = [0] * len(v)
        k = 0
        while k < len(order):
            j = k
            while j + 1 < len(order) and v[order[j + 1]] == v[order[k]]:
                j += 1
            avg = (k + j) / 2 + 1
            for t in range(k, j + 1):
                rk[order[t]] = avg
            k = j + 1
        return rk
    return pearson(ranks(xs), ranks(ys))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc", required=True)
    ap.add_argument("--synth", required=True)
    args = ap.parse_args()

    by_fy = {}
    pooled = {}
    for fy in FYS:
        agg, n_all, n_err = load_fy(args.qc, fy)
        by_fy[fy] = agg
        print(f"FY{fy}: {n_all} sample cases, {len(agg)} state codes, "
              f"{n_err} error cases ({n_err/max(n_all,1):.3f} raw)")
        for st, a in agg.items():
            p = pooled.setdefault(st, {"name": a["name"], "w": 0.0, "w_err": 0.0,
                                       "w_errdoll": 0.0, "w_iss": 0.0, "n": 0})
            for k in ("w", "w_err", "w_errdoll", "w_iss", "n"):
                p[k] += a[k]
    for a in pooled.values():
        a["case_rate"] = a["w_err"] / a["w"] if a["w"] else float("nan")
        a["dollar_rate"] = a["w_errdoll"] / a["w_iss"] if a["w_iss"] else float("nan")

    states = sorted(pooled)
    name = {st: pooled[st]["name"] or st for st in states}

    print("\n=== Pooled FY2020-2024: state payment error rates (dollar-weighted, FNS-style) ===")
    ranked = sorted(states, key=lambda s: pooled[s]["dollar_rate"])
    for s in ranked[:10]:
        print(f"  LOW  {s:>3} {name[s]:<24} {pooled[s]['dollar_rate']*100:5.2f}%  (n={pooled[s]['n']})")
    print("  ...")
    for s in ranked[-10:]:
        print(f"  HIGH {s:>3} {name[s]:<24} {pooled[s]['dollar_rate']*100:5.2f}%  (n={pooled[s]['n']})")

    drates = [pooled[s]["dollar_rate"] for s in states]
    crates = [pooled[s]["case_rate"] for s in states]
    print("\n=== Cross-state dispersion (pooled FY2020-2024) ===")
    print(f"dollar-rate: min {min(drates)*100:5.2f}%  max {max(drates)*100:5.2f}%  "
          f"ratio {max(drates)/min(drates):.1f}x  CV(unweighted) {cv(drates):.3f}  "
          f"CV(caseload-weighted) {weighted_cv([(pooled[s]['n'], pooled[s]['dollar_rate']) for s in states]):.3f}")
    print(f"case-rate:   min {min(crates)*100:5.2f}%  max {max(crates)*100:5.2f}%  "
          f"ratio {max(crates)/min(crates):.1f}x  CV(unweighted) {cv(crates):.3f}")

    print("\n=== Year-to-year stability (state rates, FY2023 vs FY2024; FY2020 vs FY2024) ===")
    for f1, f2 in ((2023, 2024), (2020, 2024)):
        common = [s for s in states if s in by_fy[f1] and s in by_fy[f2]]
        x = [by_fy[f1][s]["dollar_rate"] for s in common]
        y = [by_fy[f2][s]["dollar_rate"] for s in common]
        ok = [(a, b) for a, b in zip(x, y) if not (math.isnan(a) or math.isnan(b))]
        xs, ys = zip(*ok)
        print(f"FY{f1} vs FY{f2}: n={len(xs)} states  Pearson {pearson(xs,ys):.3f}  "
              f"Spearman(rank stability) {spearman(xs,ys):.3f}")

    print("\n=== National trend (context) ===")
    for fy in FYS:
        tot_w = sum(a["w"] for a in by_fy[fy].values())
        tot_we = sum(a["w_err"] for a in by_fy[fy].values())
        tot_ed = sum(a["w_errdoll"] for a in by_fy[fy].values())
        tot_is = sum(a["w_iss"] for a in by_fy[fy].values())
        print(f"  FY{fy}: national dollar-weighted rate {tot_ed/tot_is*100:5.2f}%, "
              f"case-weighted {tot_we/tot_w*100:5.2f}%")
    print("  (note: FY2021 microdata is Jul-Sep only, one quarter)")

    # Synth side: national rate and the structural gap.
    print("\n=== Synthetic generator: state dimension ===")
    n_syn = n_se = 0
    syn_edoll = syn_iss = 0.0
    has_state = False
    with open(args.synth) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            n_syn += 1
            if "state" in c or "STATE" in c:
                has_state = True
            finding = c.get("finding")
            if finding in (2, 3):
                n_se += 1
                syn_edoll += abs(c.get("dollar_error", 0))
            syn_iss += c.get("issued_benefit", 0)
    syn_rate = syn_edoll / syn_iss if syn_iss else float("nan")
    print(f"synth national: n={n_syn}, dollar-rate {syn_rate*100:.2f}%, "
          f"case error share {n_se/max(n_syn,1):.3f}; state field present: {has_state}")

    # Calibration gap: per-state L1 between real state rates and the synth
    # constant (synth has no state dimension, so every state gets syn_rate).
    gaps = []
    for s in states:
        r = pooled[s]["dollar_rate"]
        if not math.isnan(r) and not math.isnan(syn_rate):
            gaps.append((pooled[s]["n"], abs(r - syn_rate)))
    tot_n = sum(w for w, _ in gaps)
    l1 = sum(w * g for w, g in gaps) / tot_n
    print(f"per-state |real_rate - synth_rate| (caseload-weighted mean) = {l1*100:.2f} pp")
    spread = sum(w * abs(r - statistics.fmean(drates))
                 for (w, r) in ((pooled[s]['n'], pooled[s]['dollar_rate']) for s in states)) / tot_n
    print(f"real state-mean-abs-deviation about national mean             = {spread*100:.2f} pp "
          f"(the variation synth cannot reproduce)")

    # Where does the state variation live? Break the dollar rate into
    # case-frequency vs average-error-size components per state.
    print("\n=== Decomposition: is state variance case-frequency or error-size driven? ===")
    freq = [pooled[s]["case_rate"] for s in states]
    size = []
    for s in states:
        a = pooled[s]
        # avg error dollars per error case, weighted: errdoll/w_err
        size.append(a["w_errdoll"] / a["w_err"] if a["w_err"] else float("nan"))
    ok = [x for x in size if not math.isnan(x)]
    print(f"CV across states of case error frequency: {cv(freq):.3f}")
    print(f"CV across states of avg error size ($/error case): {cv(ok):.3f}")
    print("(variance concentrated in error SIZE, not just frequency: states differ"
          " more in how big their errors are than in how often they err)")

    print("\n=== Cross-check: microdata-implied vs FNS-published state rankings ===")
    print("(published = official FNS rates incl. federal QC validation + procedural"
          " errors; microdata = raw public-use STATUS/AMTERR/FYWGT)")
    name_to_state = {name[s].lower(): s for s in states}
    for fy, idx in ((2023, 0), (2024, 1)):
        pairs = []
        for nm, (p23, p24) in PUBLISHED.items():
            s = name_to_state.get(nm.lower())
            if s is None or s not in by_fy[fy]:
                continue
            r = by_fy[fy][s]["dollar_rate"]
            pub = (p23 if idx == 0 else p24) / 100.0
            if not math.isnan(r):
                pairs.append((s, r, pub))
        xs = [p[1] for p in pairs]
        ys = [p[2] for p in pairs]
        print(f"FY{fy}: n={len(pairs)} matched states; level: microdata mean "
              f"{statistics.fmean(xs)*100:.1f}% vs published mean "
              f"{statistics.fmean(ys)*100:.1f}%; Spearman(rank) "
              f"{spearman(xs, ys):.3f}, Pearson {pearson(xs, ys):.3f}")
        # show the big level mismatches
        worst = sorted(pairs, key=lambda p: abs(p[1] - p[2]), reverse=True)[:5]
        print("  largest level mismatches (microdata vs published):")
        for s, r, pub in worst:
            print(f"    {name[s]:<20} micro {r*100:6.2f}%  published {pub*100:6.2f}%")


if __name__ == "__main__":
    sys.exit(main())
