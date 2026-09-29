"""Exp40 — published-rate calibration.

Compares generator-implied SNAP payment error rates against FNS-published
official rates and microdata-implied rates at national level.

Rate definitions (FNS official payment error rate):
  dollar-weighted rate = (erroneous benefit dollars) / (total benefit dollars)
  = over-payment dollars + under-payment dollars, dollar-weighted, NOT netted.
The official rate applies a tolerance threshold (FY2024: $56 — generator
param QC_ERROR_THRESHOLD in src/synth/params.py; errors at or below it do
not count) and mixes in procedural errors + federal re-review adjustments
that the public-use microdata STATUS/AMTERR do not capture.

Inputs:
  - synthetic cases: /tmp/exp40_synth.jsonl (20k, seed 7, dist.json)
  - real microdata: ~/workspace/snap-qc-data/raw/qcfy20{20..24}_csv/qc_pub_fy20XX.csv
    (held-out validation; NEVER committed)
  - published figures (web): FNS FY2023 = 11.68% (over 10.03 / under 1.64),
    FY2024 = 10.93% (over 9.26 / under 1.67). See exp40 chronicle for URLs.
"""

import csv
import json
import os
import sys

DATA = os.path.expanduser("~/workspace/snap-qc-data/raw")
SYNTH = "/tmp/exp40_synth.jsonl"

FILES = {
    2020: "qcfy2020_csv/qc_pub_fy2020.csv",
    2021: "qcfy2021_csv/qc_pub_fy2021.csv",
    2022: "qcfy2022_csv/qc_pub_fy2022.csv",
    2023: "qcfy2023_csv/qc_pub_fy2023.csv",
    2024: "qcfy2024_csv/qc_pub_fy2024.csv",
}

PUBLISHED = {
    2023: {"total": 11.68, "over": 10.03, "under": 1.64},
    2024: {"total": 10.93, "over": 9.26, "under": 1.67},
}

NUM_FIELDS = ["STATUS", "FSBEN", "RAWBEN", "AMTERR", "HWGT", "FYWGT"]


def synth_rates(path=SYNTH):
    n = n_rep = 0
    err_rep = err_all = issued = 0
    over_rep = over_all = under_rep = under_all = 0
    n_over = n_under = 0
    with open(path) as f:
        for line in f:
            c = json.loads(line)
            n += 1
            issued += c["issued_benefit"]
            d = abs(c["dollar_error"])
            if c["finding"] == 2:
                n_over += 1
            elif c["finding"] == 3:
                n_under += 1
            if d > 0:
                err_all += d
                if c["finding"] == 2:
                    over_all += d
                else:
                    under_all += d
            if c.get("reportable"):
                n_rep += 1
                err_rep += d
                if c["finding"] == 2:
                    over_rep += d
                else:
                    under_rep += d
    return {
        "n": n,
        "dollar_all": 100 * err_all / issued,          # tolerance ignored
        "dollar_rep": 100 * err_rep / issued,          # FNS-style (tolerance on)
        "over_rep": 100 * over_rep / issued,
        "under_rep": 100 * under_rep / issued,
        "case_rate": 100 * (n_over + n_under) / n,     # any variance
        "case_rep": 100 * n_rep / n,                   # reportable finding
        "issued": issued,
    }


def micro_rates(fy):
    path = os.path.join(DATA, FILES[fy])
    n = 0
    w = w_err = 0.0
    err = err_over = err_under = 0.0
    issued = 0.0
    n_err = n_over = n_under = 0
    n_full_benefit_over = 0  # STATUS=2 and AMTERR >= RAWBEN: procedural-like
    err_full_benefit = 0.0
    n_status1_with_amterr = 0
    with open(path) as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            try:
                st = int(float(row["STATUS"]))
                fsben = float(row["FSBEN"] or 0)
                rawben = float(row["RAWBEN"] or 0)
                amterr = float(row["AMTERR"] or 0)
                fywgt = float(row["FYWGT"] or 0)
            except (TypeError, ValueError):
                continue
            n += 1
            w += fywgt
            issued += fywgt * rawben
            if st in (2, 3):
                n_err += 1
                w_err += fywgt
                err += fywgt * abs(amterr)
                if st == 2:
                    n_over += 1
                    err_over += fywgt * abs(amterr)
                    if rawben > 0 and abs(amterr) >= rawben:
                        n_full_benefit_over += 1
                        err_full_benefit += fywgt * abs(amterr)
                else:
                    n_under += 1
                    err_under += fywgt * abs(amterr)
            elif abs(amterr) > 0:
                n_status1_with_amterr += 1
    return {
        "fy": fy, "n": n,
        "dollar": 100 * err / issued,
        "over": 100 * err_over / issued,
        "under": 100 * err_under / issued,
        "case_rate": 100 * w_err / w,
        "case_unwt": 100 * n_err / n,
        "fullbenefit_share_cases": 100 * n_full_benefit_over / max(n_over, 1),
        "fullbenefit_share_dollars": 100 * err_full_benefit / max(err, 1e-9),
        "status1_with_amterr": n_status1_with_amterr,
    }


def main():
    print("== exp40: published-rate calibration ==\n")
    s = synth_rates()
    print("--- generator-implied (n=20000, seed 7, dist.json) ---")
    print(f"dollar-weighted rate (tolerance-applied, FNS-style): {s['dollar_rep']:.2f}%")
    print(f"  over component: {s['over_rep']:.2f}%   under component: {s['under_rep']:.2f}%")
    print(f"dollar-weighted rate (all errors, no tolerance):     {s['dollar_all']:.2f}%")
    print(f"case rate (any variance): {s['case_rate']:.2f}%  |  reportable case rate: {s['case_rep']:.2f}%")
    print(f"total issued benefit dollars (synth): {s['issued']:,.0f}")

    print("\n--- real microdata-implied (FYWGT-weighted) ---")
    print(f"{'FY':>4} {'dollar':>8} {'over':>8} {'under':>8} {'case_wt':>8} {'case_uw':>8} {'fullBen$':>8} {'n':>7}")
    micro = {}
    for fy in (2020, 2021, 2022, 2023, 2024):
        m = micro_rates(fy)
        micro[fy] = m
        print(f"{fy:>4} {m['dollar']:>7.2f}% {m['over']:>7.2f}% {m['under']:>7.2f}% "
              f"{m['case_rate']:>7.2f}% {m['case_unwt']:>7.2f}% {m['fullbenefit_share_dollars']:>7.2f}% {m['n']:>7}")
    print("(fullBen$ = share of error dollars from full-benefit overissuances, AMTERR>=RAWBEN;")
    print(" STATUS=1 cases carrying AMTERR>0:", {fy: micro[fy]['status1_with_amterr'] for fy in micro}, ")")

    print("\n--- national comparison: published vs microdata-implied vs generator-implied ---")
    print(f"{'source':<28} {'FY2023':>10} {'FY2024':>10}")
    p3, p4 = PUBLISHED[2023], PUBLISHED[2024]
    print(f"{'FNS published (total)':<28} {p3['total']:>9.2f}% {p4['total']:>9.2f}%")
    print(f"{'FNS published (over/under)':<28} {p3['over']:.2f}/{p3['under']:.2f}   {p4['over']:.2f}/{p4['under']:.2f}")
    print(f"{'microdata-implied':<28} {micro[2023]['dollar']:>9.2f}% {micro[2024]['dollar']:>9.2f}%")
    print(f"{'  over/under':<28} {micro[2023]['over']:.2f}/{micro[2023]['under']:.2f}   {micro[2024]['over']:.2f}/{micro[2024]['under']:.2f}")
    print(f"{'generator-implied (FNS-style)':<28} {s['dollar_rep']:>9.2f}% {s['dollar_rep']:>9.2f}%")
    print(f"{'  over/under':<28} {s['over_rep']:.2f}/{s['under_rep']:.2f}   {s['over_rep']:.2f}/{s['under_rep']:.2f}")

    print("\n--- reconciliation gaps (published - microdata-implied) ---")
    for fy in (2023, 2024):
        gap = PUBLISHED[fy]["total"] - micro[fy]["dollar"]
        over_gap = PUBLISHED[fy]["over"] - micro[fy]["over"]
        print(f"FY{fy}: total gap {gap:+.2f}pp  (over component {over_gap:+.2f}pp, under {PUBLISHED[fy]['under'] - micro[fy]['under']:+.2f}pp)")


if __name__ == "__main__":
    sys.exit(main())
