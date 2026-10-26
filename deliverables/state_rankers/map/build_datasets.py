"""Build the map dashboard's datasets from the leak-free rebuild (exp107): exp83_leakfree (rankers), exp107_timesplit
(later-years test) and exp93_leakfree (cost scenarios); exp68 for sample sizes.

Writes, next to this file:
  state_results.json         one row per jurisdiction (all fields the page reads)
  scenario_assumptions.json  the exp69 scenario inputs, as run in exp93 (deployed models, fairness floor on)
  (state_shapes.json is built once from us-atlas; see the exp68 chronicle)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent.parent.parent / "experiments"

r68 = {r["state"]: r for r in json.loads((EXP / "exp68_results.json").read_text())}
# exp93: exp69's scenarios re-run on the deployed models (exp83) with the fairness floor on
r69 = json.loads((EXP / "exp69_results.json").read_text())
r93 = json.loads((EXP / "exp93_leakfree_results.json").read_text())  # leak-free (exp107)
import sys  # noqa: E402
sys.path.insert(0, str(EXP))
from exp69_cost_share_scenarios import NAME_TO_USPS  # noqa: E402

NAMES = {v: " ".join(w.capitalize() if w != "OF" else "of" for w in k.split()) for k, v in NAME_TO_USPS.items()}
rows = []
for ab, r in sorted(r68.items()):
    s = r93["states"][ab]
    sc = s["scenarios"]
    rows.append({
        "state": ab, "name": NAMES[ab], "n_rows": r["n_rows"], "low_sample": r["low_sample"],
        "lift_top10": r["holdout"]["top10"]["lift"],
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
# deployed models (exp80/82: context-aware pooled, all 53), measured in exp83 on each holdout;
# Cost scenarios come from exp93's leak-free run.
r83 = json.loads((EXP / "exp83_leakfree_results.json").read_text())  # leak-free (exp107)
ts107 = json.loads((EXP / "exp107_timesplit_results.json").read_text())
adopt = {}
for f in ("exp80_results.json", "exp82_results.json"):
    for k, v in json.loads((EXP / f).read_text()).items():
        adopt[k] = v
for row in rows:
    m = r83[row["state"]]; a = adopt[row["state"]]
    row["model_type"] = "pooled with state context"
    row["lift_deployed"] = m["top20"]["lift"]
    row["lift_top10"] = m["top10"]["lift"]
    row["per_hour"] = m["top20"]["per_hour_$"]
    row["random_per_hour"] = m["top20"]["random_per_hour_$"]
    row["exp_over_act"] = m["top20"]["expected_over_actual"]
    row["time_split_lift"] = ts107[row["state"]]["time_split"]
    row["lift_floor"] = m["fairness"]["floor_lift"]
    row["elderly_ratio"] = m["fairness"]["baseline_ratio"].get("elderly")
    row["elderly_ratio_floor"] = m["fairness"]["floor_ratio"].get("elderly")
    row["disabled_ratio"] = m["fairness"]["baseline_ratio"].get("disabled")
(HERE / "state_results.json").write_text(json.dumps(rows, indent=1))
ass = [{"scenario": k, "review_share": v["R"],
        "lift_basis": ("top-20% lift" if v["lift"] == "top20" else "top-10% lift") + ", fairness floor on",
        "fix_rate": v["f"], "error_months": v["m"]} for k, v in r69["scenarios"].items()]
(HERE / "scenario_assumptions.json").write_text(json.dumps(ass, indent=1))
print(f"state_results.json: {len(rows)} rows; scenario_assumptions.json: {len(ass)} rows")
