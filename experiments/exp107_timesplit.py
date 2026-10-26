"""Exp107 amendment 1: the later-years test (train FY2020-22 incl. other jurisdictions, test own FY2023-24) under
SNAPQC_FEATURES=leakfree, as exp82 computed it for the adopted variant. Writes exp107_timesplit_results.json.

Usage: SNAPQC_FEATURES=leakfree python3 experiments/exp107_timesplit.py [--workers 8]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
_G = {}


def init():
    import exp80_state_context as X80
    _G["data"] = X80.load_all(str(ROOT.parent / "snap-qc-data/raw"))


def run_one(job):
    ab, code, variant = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    from exp75_small_state_pooling import fit_w, lift
    data = _G["data"]; own = data[code]
    early = [k for k in sorted(own) if k[0] <= 2022]; late = [k for k in sorted(own) if k[0] >= 2023]
    X, y, a = E58.arrays(own, early); Xl, yl, al = E58.arrays(own, late)
    others = [(c, k) for c in data if c != code for k in data[c] if k[0] <= 2022]
    Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
    ao = np.array([data[c][k][2] for c, k in others])
    wown = 10.0 if variant == "C_ctx" else 1.0
    f = fit_w(np.vstack([X, Xo]), np.concatenate([y, yo]), np.concatenate([a, ao]),
              np.concatenate([np.full(len(y), wown), np.ones(len(yo))]), E56.DEFAULT, E56.DEFAULT)
    return {"state": ab, "variant": variant, "time_split": round(lift(f(Xl), al), 3)}


def main():
    import exp58_agency_rankers as E58
    assert E58.LEAKFREE, "run with SNAPQC_FEATURES=leakfree"
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8); args = ap.parse_args()
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    adopted = {}
    for fn in ("exp80_results.json", "exp82_results.json"):
        for k, v in json.loads((ROOT / "experiments" / fn).read_text()).items():
            adopted[k] = v["adopted"]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    with get_context("spawn").Pool(args.workers, initializer=init) as pool:
        res = {r["state"]: r for r in pool.imap_unordered(run_one, [(ab, hold[ab]["code"], adopted[ab]) for ab in sorted(adopted)])}
    (ROOT / "experiments" / {"official": "exp107_timesplit_official_results.json", "gap": "exp107_timesplit_gap_results.json", "any": "exp107_timesplit_results.json"}[E58.SNAPQC_LABEL]).write_text(json.dumps(dict(sorted(res.items())), indent=1))
    print("median time split", float(np.median([r["time_split"] for r in res.values()])))


if __name__ == "__main__":
    main()
