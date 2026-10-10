"""Build the map dashboard's datasets from exp68 (rankers) and exp69 (cost scenarios).

Writes, next to this file:
  state_results.json         one row per jurisdiction (all fields the page reads)
  scenario_assumptions.json  the exp69 scenario inputs
  (state_shapes.json is built once from us-atlas; see the exp68 chronicle)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent.parent.parent / "experiments"

r68 = {r["state"]: r for r in json.loads((EXP / "exp68_results.json").read_text())}
r69 = json.loads((EXP / "exp69_results.json").read_text())
import sys  # noqa: E402
sys.path.insert(0, str(EXP))
from exp69_cost_share_scenarios import NAME_TO_USPS  # noqa: E402

NAMES = {v: " ".join(w.capitalize() if w != "OF" else "of" for w in k.split()) for k, v in NAME_TO_USPS.items()}
rows = []
for ab, r in sorted(r68.items()):
    s = r69["states"][ab]
    sc = s["scenarios"]
    rows.append({
        "state": ab, "name": NAMES[ab], "n_rows": r["n_rows"], "low_sample": r["low_sample"],
        "lift_top20": r["holdout"]["top20"]["lift"], "lift_top10": r["holdout"]["top10"]["lift"],
        "per_hour": r["holdout"]["top20"]["per_hour_$"], "random_per_hour": r["holdout"]["top20"]["random_per_hour_$"],
        "time_split_lift": r["time_split_top20_lift"][r["chosen"]],
        "exp_over_act": r["holdout"]["top20"]["expected_over_actual"],
        "per_fy2025": s["per_fy2025"], "share_now": s["cost_share_now"], "annual_benefits": s["annual_benefits"],
        "per_central": sc["central"]["ranker"]["per"], "per_central_random": sc["central"]["random"]["per"],
        "share_central": sc["central"]["ranker"]["cost_share"],
        "saving_low": sc["low"]["ranker"]["saving_vs_now"], "saving_central": sc["central"]["ranker"]["saving_vs_now"],
        "saving_high": sc["high"]["ranker"]["saving_vs_now"],
        "reviews_per_month": sc["central"]["reviews_per_month"], "fte": sc["central"]["fte"],
    })
# exp72 fairness and exp75 pooled models for small jurisdictions
r72 = {r["state"]: r for r in json.loads((EXP / "exp72_results.json").read_text())}
r75 = json.loads((EXP / "exp75_results.json").read_text())
for row in rows:
    f = r72[row["state"]]
    row["lift_floor"] = f["floor"]["lift"]
    row["elderly_ratio"] = f["baseline"]["ratio"].get("elderly")
    row["elderly_ratio_floor"] = f["floor"]["ratio"].get("elderly")
    row["disabled_ratio"] = f["baseline"]["ratio"].get("disabled")
    p = r75.get(row["state"])
    pooled = p is not None and p["adopted"] != "A"
    row["model_type"] = "pooled with other states" if pooled else "own cases only"
    row["lift_deployed"] = p[p["adopted"]]["holdout"] if pooled else row["lift_top20"]
(HERE / "state_results.json").write_text(json.dumps(rows, indent=1))
ass = [{"scenario": k, "review_share": v["R"], "lift_basis": "top-20% lift" if v["lift"] == "top20" else "top-10% lift",
        "fix_rate": v["f"], "error_months": v["m"]} for k, v in r69["scenarios"].items()]
(HERE / "scenario_assumptions.json").write_text(json.dumps(ass, indent=1))
print(f"state_results.json: {len(rows)} rows; scenario_assumptions.json: {len(ass)} rows")
