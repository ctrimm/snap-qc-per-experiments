"""Recompute the FY2028 SNAP cost-share figure (exp93) nationally or for one state, from committed inputs.

No model fitting: uses each jurisdiction's measured ranker lift from exp93_results.json, the official FY2025
payment error rates (exp69_published_per.json) and annual benefits from FY2024 QC microdata (exp93's rows).
Any input can be overridden for a state, so it also works for a state with newer or its own figures.

  python3 experiments/cost_share_replicate.py                       # national, all three scenarios
  python3 experiments/cost_share_replicate.py --state PA            # one state, step by step
  python3 experiments/cost_share_replicate.py --state PA --per 8.7 --benefits 4.3e9 --lift 5.0 --R 0.015
See COST-SHARE-REPLICATE.md.
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCEN = {"low": {"R": 0.01, "lift": "top20", "f": 0.6, "m": 4},       # exp69, unchanged in exp93
        "central": {"R": 0.02, "lift": "top10", "f": 0.8, "m": 6},
        "high": {"R": 0.03, "lift": "top10", "f": 0.9, "m": 8}}
MEDIAN_FLOOR_LIFT = {"top10": 6.17, "top20": 3.93}  # exp93 medians across 53 jurisdictions (fallback for a state with no ranker)


def share(per):
    """H.R. 1 state match on benefit costs from FY2028, by payment error rate (percent)."""
    return 0.0 if per < 6 else 0.05 if per < 8 else 0.10 if per < 10 else 0.15


def after(per0, R, L, f, m):
    """Steady-state error rate after reviews correct a share c = R x L x f of error dollars a month."""
    return per0 / (1 + R * L * f * m)


def inputs():
    r = json.loads((HERE / "exp93_results.json").read_text())
    rows = {}
    for ab, s in r["states"].items():
        lift = r["measured"][ab]
        rows[ab] = {"per": s["per_fy2025"], "benefits": s["annual_benefits"],
                    "lift": {"top10": lift["top10"]["floor_lift"], "top20": lift["top20"]["floor_lift"]},
                    "households": s["scenarios"]["central"]["reviews_per_month"] / SCEN["central"]["R"]}
    return rows


def state_report(ab, row, over):
    per0 = over.per if over.per is not None else row["per"]
    ben = over.benefits if over.benefits is not None else row["benefits"]
    hh = over.households if over.households is not None else row["households"]
    print(f"{ab}: payment error rate {per0:.2f}% -> state share {share(per0):.0%} of ${ben / 1e9:.2f}B "
          f"= ${share(per0) * ben / 1e6:,.0f}M a year at FY2028 rules")
    for k, s in SCEN.items():
        R = over.R if over.R is not None else s["R"]
        L = over.lift if over.lift is not None else row["lift"][s["lift"]]
        p1 = after(per0, R, L, s["f"], s["m"]); pr = after(per0, R, 1.0, s["f"], s["m"])
        saved = (share(per0) - share(p1)) * ben; saved_r = (share(per0) - share(pr)) * ben
        print(f"  {k:7s} R={R:.1%} L={L:.2f} f={s['f']} m={s['m']}: c={R * L * s['f']:.4f}, "
              f"rate {per0:.2f} / (1 + c x m) = {p1:.2f}% -> share {share(p1):.0%}; avoided ${saved / 1e6:,.0f}M/yr "
              f"(random reviews: {pr:.2f}%, ${saved_r / 1e6:,.0f}M); {R * hh:,.0f} reviews/mo, {R * hh * 0.5 / 140:,.1f} FTE")


def national(rows):
    now = sum(share(r["per"]) * r["benefits"] for r in rows.values())
    print(f"All {len(rows)} jurisdictions: cost share due at FY2025 rates ${now / 1e9:.2f}B a year")
    for k, s in SCEN.items():
        for label, use in (("ranker, floor on", True), ("random reviews", False)):
            tot = sum((share(r["per"]) - share(after(r["per"], s["R"], r["lift"][s["lift"]] if use else 1.0, s["f"], s["m"]))) * r["benefits"]
                      for r in rows.values())
            print(f"  {k:7s} {label:17s} avoided ${tot / 1e9:.2f}B a year")
    s = SCEN["central"]
    tot = sum((share(r["per"]) - share(after(r["per"], s["R"], r["lift"]["top20"], s["f"], s["m"]))) * r["benefits"] for r in rows.values())
    print(f"  central, floor on, top-20% lift basis (conservative): ${tot / 1e9:.2f}B a year")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", help="USPS code, e.g. PA; a code not in the 53 needs --per, --benefits and --households")
    ap.add_argument("--per", type=float, help="payment error rate in percent (e.g. a newer FY2026 rate)")
    ap.add_argument("--benefits", type=float, help="annual SNAP benefits in dollars")
    ap.add_argument("--households", type=float, help="monthly SNAP households (for review counts and FTEs)")
    ap.add_argument("--lift", type=float, help="the state's ranker lift (default: its measured floor-on lift)")
    ap.add_argument("--R", type=float, help="share of the caseload reviewed a month (overrides every scenario)")
    a = ap.parse_args()
    rows = inputs()
    if not a.state:
        return national(rows)
    row = rows.get(a.state.upper()) or {"per": None, "benefits": None, "households": None, "lift": MEDIAN_FLOOR_LIFT}
    if row["per"] is None and (a.per is None or a.benefits is None or a.households is None):
        ap.error("a state outside the 53 needs --per, --benefits and --households (lift defaults to the 53-state median)")
    state_report(a.state.upper(), row, a)


if __name__ == "__main__":
    main()
