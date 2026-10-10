"""Exp 64 — first sizing pass: other programs SNAP households likely qualify for.

FY2024 QC public-use file, all sampled SNAP households (STATUS 1-3), weighted
by FYWGT to monthly caseloads. Simple proxies from household facts the SNAP
case already holds; potential eligibility only (the file does not show
enrollment in WIC, Medicaid, etc., and asset tests, immigration rules and
state program rules are not modelled).

Proxies (FY2024; 2024 HHS poverty guideline, 48 states: $15,060 + $5,380 per
additional person, per year):
  school_meals   any member aged 5-17 (SNAP -> direct certification for free meals)
  summer_ebt     same children; only where the state runs Summer EBT
  wic            any member aged 0-4 (infants/children; pregnancy not observed)
  liheap         household pays utilities (UTIL > 0 or a heating/cooling SUA)
  lifeline       every SNAP household (SNAP is a qualifying program)
  medicare_help  any member 65+ and gross income <= 150% of poverty (Extra Help
                 limit; Medicare Savings Programs are lower and have asset tests)
  medicaid_adult any member 19-64 and gross income <= 138% of poverty
                 (expansion states only; TX has not expanded)

Usage: python3 experiments/exp64_cross_program_sizing.py
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POC = {"42": "PA", "36": "NY", "48": "TX", "46": "SD", "49": "UT", "16": "ID"}
NON_EXPANSION = {"48"}  # among POC states, as of FY2024
SUA_HEAT = {"3", "4"}  # heating/cooling standard utility allowance codes (exp58 SUA_YES superset)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    path = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
    progs = ["school_meals", "wic", "liheap", "lifeline", "medicare_help", "medicaid_adult"]
    W = defaultdict(lambda: defaultdict(float))
    N = defaultdict(lambda: defaultdict(int))
    kids = defaultdict(float)
    for r in csv.DictReader(open(path, newline="")):
        if r["STATUS"].strip() not in ("1", "2", "3"):
            continue
        w = fnum(r.get("FYWGT")) or 0.0
        size = int(fnum(r.get("CERTHHSZ")) or 1)
        ages = [fnum(r.get(f"AGE{i}")) for i in range(1, 17)]
        ages = [a for a in ages[:max(size, 1)] if a is not None]
        gross = fnum(r.get("RAWGROSS")) or 0.0
        fpl = (15060 + 5380 * (max(size, 1) - 1)) / 12
        flags = {
            "school_meals": any(5 <= a <= 17 for a in ages),
            "wic": any(0 <= a <= 4 for a in ages),
            "liheap": (fnum(r.get("UTIL")) or 0) > 0 or (r.get("SUA1") or "").strip() in SUA_HEAT,
            "lifeline": True,
            "medicare_help": any(a >= 65 for a in ages) and gross <= 1.5 * fpl,
            "medicaid_adult": r["STATE"].strip() not in NON_EXPANSION and any(19 <= a <= 64 for a in ages)
                              and gross <= 1.38 * fpl,
        }
        st = POC.get(r["STATE"].strip())
        for key in (["US"] + ([st] if st else [])):
            W[key]["_all"] += w; N[key]["_all"] += 1
            for p in progs:
                if flags[p]:
                    W[key][p] += w; N[key][p] += 1
            kids[key] += w * sum(1 for a in ages if 5 <= a <= 17)
    out = {}
    print(f"{'':4s} {'SNAP hh/mo':>11s} " + " ".join(f"{p:>15s}" for p in progs) + f" {'school-age kids':>16s}")
    for key in ["US", "PA", "NY", "TX", "SD", "UT", "ID"]:
        tot = W[key]["_all"]
        row = {p: {"share": round(W[key][p] / tot, 3), "households": round(W[key][p])} for p in progs}
        row["_snap_households"] = round(tot); row["_sample"] = N[key]["_all"]; row["_school_age_children"] = round(kids[key])
        out[key] = row
        print(f"{key:4s} {tot:11,.0f} " + " ".join(f"{row[p]['share']:>8.0%} {row[p]['households']/1000:>5.0f}k" for p in progs)
              + f" {kids[key]/1000:>15,.0f}k")
    (ROOT / "experiments" / "exp64_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
