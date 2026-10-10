"""Exp 73 — which exp69 assumption drives the cost-share range?

One factor at a time around the exp69 central scenario (R 2%, top-10% lift,
f 0.8, m 6): R in {0.5, 1, 2, 3, 5}% of cases a month; lift basis in
{top-20%, top-10%, top-10% x 0.75 haircut}; f in {0.5, 0.6, 0.8, 0.9, 1.0};
m in {2, 4, 6, 8, 12} months. Output: national FY2028 cost share avoided per
year, ranker-guided vs random reviews, and jurisdictions under 6%.
Same model and inputs as exp69 (no new assumptions besides the grid).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp69_cost_share_scenarios as X  # noqa: E402

per = json.loads((ROOT / "experiments/exp69_published_per.json").read_text())["rates"]["2025"]
lifts = {r["state"]: r["holdout"] for r in json.loads((ROOT / "experiments/exp68_results.json").read_text())}
hh, ben = X.caseload_and_benefits()
C = {"R": 0.02, "lift": "top10", "hair": 1.0, "f": 0.8, "m": 6}


def run(p):
    tot = rnd = 0.0; under = 0
    for name, ab in X.NAME_TO_USPS.items():
        p0, b = per[name]["per"], ben[ab]
        for L, acc in ((lifts[ab][p["lift"]]["lift"] * p["hair"], "r"), (1.0, "x")):
            p1 = p0 / (1 + p["R"] * L * p["f"] * p["m"])
            sv = (X.share(p0) - X.share(p1)) * b
            if acc == "r":
                tot += sv; under += p1 < 6
            else:
                rnd += sv
    return tot, rnd, under


rows = []
grid = [("R", [0.005, 0.01, 0.02, 0.03, 0.05]), ("lift", [("top20", 1.0), ("top10", 1.0), ("top10", 0.75)]),
        ("f", [0.5, 0.6, 0.8, 0.9, 1.0]), ("m", [2, 4, 6, 8, 12])]
for k, vals in grid:
    for v in vals:
        p = dict(C)
        if k == "lift":
            p["lift"], p["hair"] = v
            label = f"{v[0]}{' x0.75' if v[1] != 1 else ''}"
        else:
            p[k] = v
            label = f"{v:.1%}" if k == "R" else str(v)
        t, r, u = run(p)
        rows.append({"factor": k, "value": label, "avoided_ranker": round(t), "avoided_random": round(r), "under_6pct": u})
        print(f"{k:4s} {label:12s} ranker ${t / 1e9:5.2f}B  random ${r / 1e9:5.2f}B  under 6%: {u}")
(ROOT / "experiments/exp73_results.json").write_text(json.dumps({"central": C, "rows": rows}, indent=1))
