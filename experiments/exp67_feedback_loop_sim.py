"""Exp 67 — simulate the pilot feedback loop, with and without random reviews.

In a pilot the ranker is retrained on what reviewers find, but reviewers only
see the cases it flags. That can lock the model into its own blind spots.
The fix proposed for loop 2: spend a share (epsilon) of the review budget on
randomly chosen cases.

Simulation per state on FY2020-2024 QC samples (agency-side features, exp58):
  - cold start: ranker trained on all FY2020 cases (a state's past QC records)
  - each later year: score that year's cases; review 20% of them, of which
    (1 - eps) are the top-scored and eps are random among the rest; only the
    reviewed cases' outcomes become new training data; retrain
  - reference: "all labels" retrains on every past case each year (what exp58 does)
Metrics per year (prospective, before that year's labels are used): share of
the year's error dollars found by the reviews actually done, and the
pure-exploitation top-20% lift of the current model (its quality).
eps in {0, 0.1, 0.2}; 10 seeds for the random part; default ranker config.

Usage: OMP_NUM_THREADS=8 python3 experiments/exp67_feedback_loop_sim.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402
import exp58_agency_rankers as E58  # noqa: E402

STATES = ["PA", "NY", "TX", "SD", "UT", "ID"]
EPS = [0.0, 0.1, 0.2]
SEEDS = 10
BUDGET = 0.20


def run_state(st, qc_dir):
    code = E56.STATES[st][0]
    real = E58.load_state(qc_dir, code)
    keys = sorted(real)
    X, y, a = E58.arrays(real, keys)
    fy = np.array([k[0] for k in keys])
    D = E56.DEFAULT
    res = {}
    for eps in EPS + ["all"]:
        per_seed = []
        for seed in range(SEEDS if eps not in (0.0, "all") else 1):
            rng = np.random.RandomState(seed)
            train = list(np.where(fy == 2020)[0])
            found, quality = [], []
            for year in (2021, 2022, 2023, 2024):
                idx = np.where(fy == year)[0]
                f, _ = E56.fit_two_part(X[train], y[train], a[train], D, D)
                s = f(X[idx])
                order = idx[np.argsort(-s, kind="stable")]
                k = int(round(BUDGET * len(idx)))
                quality.append(a[order[:k]].sum() / (a[idx].sum() * BUDGET))
                if eps == "all":
                    reviewed = order[:k]
                    train += list(idx)
                else:
                    n_rand = int(round(eps * k))
                    top = list(order[:k - n_rand])
                    rest = np.setdiff1d(idx, top)
                    rand = list(rng.choice(rest, n_rand, replace=False)) if n_rand else []
                    reviewed = np.array(top + rand)
                    train += list(reviewed)
                found.append(a[reviewed].sum() / a[idx].sum())
            per_seed.append((found, quality))
        F = np.mean([p[0] for p in per_seed], axis=0)
        Q = np.mean([p[1] for p in per_seed], axis=0)
        res[str(eps)] = {"found_share_by_year": [round(v, 3) for v in F], "found_share_mean": round(float(F.mean()), 3),
                         "model_lift_by_year": [round(v, 3) for v in Q], "model_lift_2024": round(float(Q[-1]), 3)}
    return res


def main():
    qc_dir = str(ROOT.parent / "snap-qc-data/raw")
    out = {}
    print("share of each year's error dollars found by the reviews done (2021-24 mean) | model lift in 2024")
    for st in STATES:
        r = run_state(st, qc_dir)
        out[st] = r
        print(f"{st}: " + " | ".join(f"eps={e}: found {r[e]['found_share_mean']:.1%} lift24 {r[e]['model_lift_2024']:.2f}x"
                                      for e in r), flush=True)
    avg = {e: {"found": float(np.mean([out[s][e]["found_share_mean"] for s in STATES])),
               "lift24": float(np.mean([out[s][e]["model_lift_2024"] for s in STATES]))} for e in out[STATES[0]]}
    print("MEAN: " + " | ".join(f"eps={e}: found {v['found']:.1%} lift24 {v['lift24']:.2f}x" for e, v in avg.items()))
    out["_mean"] = avg
    E58.results_path("exp67_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
