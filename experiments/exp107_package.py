"""Exp107: package the leak-free models for all 53 jurisdictions, in parallel (exp80's package_adopted logic, one
process per jurisdiction). Run with the default SNAPQC_FEATURES (leakfree).

Usage: python3 experiments/exp107_package.py [--workers 8]
"""
import argparse
import datetime
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
    ab, code, adopted, prev = job
    import joblib
    import sklearn
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    from sklearn.isotonic import IsotonicRegression
    from sklearn.model_selection import StratifiedKFold
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    import exp80_state_context as X80
    from exp75_small_state_pooling import fit_w
    data = _G["data"]; D = E56.DEFAULT
    wown = 10.0 if adopted == "C_ctx" else 1.0
    own = data[code]; keys = sorted(own)
    X, y, a = E58.arrays(own, keys)
    others = [(c, k) for c in data if c != code for k in data[c]]
    Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
    ao = np.array([data[c][k][2] for c, k in others])
    s_oof = np.zeros(len(y))
    for tr_i, te_i in StratifiedKFold(5, shuffle=True, random_state=80).split(X, y):
        f = fit_w(np.vstack([X[tr_i], Xo]), np.concatenate([y[tr_i], yo]), np.concatenate([a[tr_i], ao]),
                  np.concatenate([np.full(len(tr_i), wown), np.ones(len(yo))]), D, D)
        s_oof[te_i] = f(X[te_i])
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0).fit(s_oof, a)
    XX = np.vstack([X, Xo]); yy = np.concatenate([y, yo]); aa = np.concatenate([a, ao])
    ww = np.concatenate([np.full(len(y), wown), np.ones(len(yo))])
    clf = HistGradientBoostingClassifier(random_state=0, **D).fit(XX, yy, sample_weight=ww)
    pos = aa > 0
    reg = HistGradientBoostingRegressor(random_state=0, **D).fit(XX[pos], np.log1p(aa[pos]), sample_weight=ww[pos])
    out = ROOT / "deliverables/state_rankers" / ab
    feats = E58.FEATURES + X80.CONTEXT
    joblib.dump({"features": feats, "classifier": clf, "dollar_regressor": reg, "dollar_calibrator": iso, "state": ab},
                out / "model.joblib")
    card = json.loads((out / "model_card.json").read_text())
    card.update({"built": datetime.date.today().isoformat(), "sklearn_version": sklearn.__version__, "features": feats,
                 "feature_set": E58.SNAPQC_FEATURES, "error_label": E58.SNAPQC_LABEL,
                 "feature_note": "exp107 leak-free: QC case facts plus the case's maximum allotment (BENMAX); the issued benefit "
                                 "is NOT an input (exp106: the QC file's RAW* facts are reviewer values, so pairing them with "
                                 "RAWBEN leaked the error)",
                 "model": "P(error) x E[dollars | error], HistGradientBoosting; expected dollars calibrated by isotonic "
                          f"regression on out-of-fold scores; trained on this jurisdiction's rows (weight {wown:g}) pooled with "
                          "all other jurisdictions' rows (exp80 design, exp107 leak-free features)",
                 "chosen": f"exp80/82 variant {adopted}", "config": {"clf": D, "reg": D},
                 "evaluation_current": ("experiments/exp83_official_results.json (held-out); exp107_timesplit_official_results.json" if E58.OFFICIAL else "experiments/exp83_leakfree_results.json (held-out); exp107_timesplit_results.json"),
                 "source": "snap-qc-per-experiments exp107 (experiments/exp107_package.py)"})
    (out / "model_card.json").write_text(json.dumps(card, indent=1))
    return ab


def main():
    import exp58_agency_rankers as E58
    assert E58.LEAKFREE, "packages the leak-free models; unset SNAPQC_FEATURES or set it to leakfree"
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8); args = ap.parse_args()
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    adopted = {}
    for fn in ("exp80_results.json", "exp82_results.json"):
        for k, v in json.loads((ROOT / "experiments" / fn).read_text()).items():
            adopted[k] = v
    jobs = [(ab, hold[ab]["code"], v["adopted"], v.get("deployed")) for ab, v in sorted(adopted.items()) if v["adopted"] != "keep"]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    with get_context("spawn").Pool(args.workers, initializer=init) as pool:
        for ab in pool.imap_unordered(run_one, jobs):
            print("packaged", ab, flush=True)
    print("done", len(jobs))


if __name__ == "__main__":
    main()
