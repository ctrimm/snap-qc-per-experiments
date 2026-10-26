"""Exp 108 amendment 1: pooled (exp83_leakfree) vs state-only top-20% lift, leak-free features, exp68 holdouts."""
import json
import os
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "experiments" / "eval_pilot"), str(ROOT / "src")]
_G = {}


def init():
    import exp80_state_context as X80
    _G["data"] = X80.load_all(str(ROOT.parent / "snap-qc-data/raw"))


def run_one(job):
    ab, code, hold_keys = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    from exp75_small_state_pooling import fit_w, lift
    own = _G["data"][code]; ho = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
    X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
    s = fit_w(X, y, a, np.ones(len(y)), E56.DEFAULT, E56.DEFAULT)(Xh)
    return ab, round(lift(s, ah), 3)


def main():
    import exp58_agency_rankers as E58
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    pooled = json.loads((ROOT / "experiments/exp83_leakfree_results.json").read_text())
    jobs = [(ab, h["code"], h["keys"]) for ab, h in sorted(hold.items())]
    with Pool(int(os.environ.get("WORKERS", 8)), initializer=init) as p:
        so = dict(p.map(run_one, jobs))
    rows = {ab: {"pooled": pooled[ab]["top20"]["lift"], "state_only": so[ab]} for ab in so}
    out = {"feature_set": E58.SNAPQC_FEATURES, "states": rows,
           "median_pooled": st.median(r["pooled"] for r in rows.values()),
           "median_state_only": st.median(r["state_only"] for r in rows.values()),
           "pooled_higher": sum(r["pooled"] > r["state_only"] for r in rows.values()), "n": len(rows)}
    print({k: v for k, v in out.items() if k != "states"})
    E58.results_path("exp108_pooling_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
