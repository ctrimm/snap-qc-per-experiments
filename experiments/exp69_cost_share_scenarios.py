"""Exp 69 — what could ranker-guided reviews mean for a state's error rate and cost share?

A scenario model, not a forecast. Every input is stated here and in the
chronicle; the output is a range per state.

Law (H.R. 1, 2025; verified Oct 10, 2026 against public summaries): from
FY2028 a state pays a share of SNAP benefit costs set by its payment error
rate (PER): < 6% -> 0%; 6-8% -> 5%; 8-10% -> 10%; >= 10% -> 15%. FY2028 uses
the state's choice of its FY2025 or FY2026 PER; later years use the PER from
three years earlier. States with PER x 1.5 >= 20% can delay to FY2029/2030.

Baseline: the official FY2025 PER per state (FNA, June 24, 2026;
exp69_published_per.json). Annual benefits: FY2024 QC microdata,
sum(FYWGT x RAWBEN) x 12.

Mechanism (stock-and-flow of error dollars in the active caseload):
  error dollars arise at a steady rate and leave when a case is recertified
  (average time an error stays in the caseload: m months). Reviews correct a
  share c of the caseload's error dollars each month:
      c = R x L x f
  R = share of the caseload reviewed per month, L = how many times random the
  reviews' error-dollar yield is (the state's exp68 holdout lift; random
  reviews have L = 1), f = share of found errors actually fixed going forward.
  Steady state: error dollars fall by the factor 1 / (1 + c x m), and the PER
  is assumed to fall in proportion (the QC sample is a random draw from the
  same caseload).
Scenarios (low / central / high):
  R = 1% / 2% / 3% of cases a month;  L = top-20% / top-10% holdout lift
  (low uses the top-20% lift for all R; central and high the top-10% lift);
  f = 0.6 / 0.8 / 0.9;  m = 4 / 6 / 8 months.
Staff: reviews x 30 minutes; 1 FTE = 140 productive hours a month.

Not modelled: whether corrections reach the cases the federal sample draws
(timing), procedural errors outside the microdata (published rates run 2-3
points above microdata-implied rates, exp40), behaviour changes, and the
delayed-implementation option. Treat results as the size of the opportunity.

Usage: python3 experiments/exp69_cost_share_scenarios.py   (needs exp68_results.json)
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME_TO_USPS = {"ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA", "COLORADO": "CO",
                "CONNECTICUT": "CT", "DELAWARE": "DE", "DISTRICT OF COLUMBIA": "DC", "FLORIDA": "FL", "GEORGIA": "GA",
                "GUAM": "GU", "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
                "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI",
                "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
                "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC",
                "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA",
                "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX",
                "UTAH": "UT", "VERMONT": "VT", "VIRGIN ISLANDS": "VI", "VIRGINIA": "VA", "WASHINGTON": "WA",
                "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY"}
SCEN = {"low": {"R": 0.01, "lift": "top20", "f": 0.6, "m": 4},
        "central": {"R": 0.02, "lift": "top10", "f": 0.8, "m": 6},
        "high": {"R": 0.03, "lift": "top10", "f": 0.9, "m": 8}}


def share(per):
    return 0.0 if per < 6 else 0.05 if per < 8 else 0.10 if per < 10 else 0.15


def caseload_and_benefits():
    from exp68_all_state_rankers import USPS
    hh, ben = {}, {}
    path = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
    for r in csv.DictReader(open(path, newline="")):
        ab = USPS.get(int(r["STATE"]))
        w = float(r.get("FYWGT") or 0)
        hh[ab] = hh.get(ab, 0) + w
        ben[ab] = ben.get(ab, 0) + w * float(r.get("RAWBEN") or 0) * 12
    return hh, ben


def main():
    import sys
    sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
    per = json.loads((ROOT / "experiments/exp69_published_per.json").read_text())["rates"]["2025"]
    lifts = {r["state"]: r["holdout"] for r in json.loads((ROOT / "experiments/exp68_results.json").read_text())}
    hh, ben = caseload_and_benefits()
    out = {}
    tot_now = {k: 0.0 for k in SCEN}; tot_base = 0.0
    for name, ab in NAME_TO_USPS.items():
        p0 = per[name]["per"]; b = ben[ab]; base_cost = share(p0) * b
        row = {"per_fy2025": p0, "annual_benefits": round(b), "households": round(hh[ab]),
               "cost_share_now": share(p0), "cost_now": round(base_cost), "scenarios": {}}
        for k, s in SCEN.items():
            L = lifts[ab][s["lift"]]["lift"]
            for label, lift in (("ranker", L), ("random", 1.0)):
                c = s["R"] * lift * s["f"]
                p1 = p0 / (1 + c * s["m"])
                row["scenarios"].setdefault(k, {})[label] = {
                    "per": round(p1, 2), "cost_share": share(p1), "annual_cost": round(share(p1) * b),
                    "saving_vs_now": round(base_cost - share(p1) * b)}
            row["scenarios"][k]["reviews_per_month"] = round(s["R"] * hh[ab])
            row["scenarios"][k]["fte"] = round(s["R"] * hh[ab] * 0.5 / 140, 1)
            tot_now[k] += share(row["scenarios"][k]["ranker"]["per"]) * b
        tot_base += base_cost
        out[ab] = row
    print(f"{'':3s} {'PER25':>6s} {'share':>5s} {'benefits':>9s} | central: PER ranker / random -> share | savings ranker (low-high)")
    for ab, r in sorted(out.items(), key=lambda x: -x[1]["annual_benefits"]):
        c = r["scenarios"]["central"]
        print(f"{ab:3s} {r['per_fy2025']:6.2f} {r['cost_share_now']:5.0%} {r['annual_benefits'] / 1e9:8.2f}B | "
              f"{c['ranker']['per']:5.2f} / {c['random']['per']:5.2f} -> {c['ranker']['cost_share']:.0%} | "
              f"${r['scenarios']['low']['ranker']['saving_vs_now'] / 1e6:,.0f}M - ${r['scenarios']['high']['ranker']['saving_vs_now'] / 1e6:,.0f}M"
              f" | {c['reviews_per_month']:,} reviews/mo, {c['fte']} FTE")
    print(f"ALL: cost share now ${tot_base / 1e9:.2f}B/yr; with ranker reviews: " +
          ", ".join(f"{k} ${v / 1e9:.2f}B" for k, v in tot_now.items()) + f"; national benefits ${sum(ben.values()) / 1e9:.1f}B")
    (ROOT / "experiments/exp69_results.json").write_text(json.dumps(
        {"scenarios": SCEN, "states": out, "totals": {"cost_now": tot_base, **{f"cost_{k}": v for k, v in tot_now.items()}}}, indent=1))


if __name__ == "__main__":
    main()
