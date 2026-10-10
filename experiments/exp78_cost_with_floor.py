"""Exp 78 — FY2028 cost-share scenarios with the fairness floor on.

exp69's figures assume dollar-only ranking; the recommended default is the
exp72 per-household-type floor. exp72 measured the floor's top-20% lift
only, so this compares like with like on the top-20% basis.

Pre-registered (this docstring, committed before running): exp69's model and
inputs; scenarios low/central/high as exp69 except the lift used is the
top-20% holdout lift for BOTH arms: dollar-only (exp68) vs with floor (exp72).
Report national cost share avoided per year and jurisdictions dropping a bracket.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp69_cost_share_scenarios as X  # noqa: E402

per = json.loads((ROOT / "experiments/exp69_published_per.json").read_text())["rates"]["2025"]
dollar = {r["state"]: r["holdout"]["top20"]["lift"] for r in json.loads((ROOT / "experiments/exp68_results.json").read_text())}
floor = {r["state"]: r["floor"]["lift"] for r in json.loads((ROOT / "experiments/exp72_results.json").read_text())}
hh, ben = X.caseload_and_benefits()
out = {}
for k, s in X.SCEN.items():
    row = {}
    for arm, L in (("dollar_only", dollar), ("with_floor", floor), ("random", None)):
        tot = 0.0; moved = 0
        for name, ab in X.NAME_TO_USPS.items():
            p0 = per[name]["per"]; lift = 1.0 if L is None else L[ab]
            p1 = p0 / (1 + s["R"] * lift * s["f"] * s["m"])
            tot += (X.share(p0) - X.share(p1)) * ben[ab]; moved += X.share(p1) < X.share(p0)
        row[arm] = {"avoided": round(tot), "states_dropping_bracket": moved}
    out[k] = row
    print(f"{k:8s} " + " | ".join(f"{a}: ${v['avoided'] / 1e9:.2f}B ({v['states_dropping_bracket']} drop)" for a, v in row.items()))
(ROOT / "experiments/exp78_results.json").write_text(json.dumps(out, indent=1))
