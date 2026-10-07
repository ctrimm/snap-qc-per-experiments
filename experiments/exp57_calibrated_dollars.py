"""Exp 57 — quotable expected dollars for the exp56 triage rankers.

exp56's ranker scores cases by P(error) x E[dollars | error]. The ordering
is what drives dollars recovered, but the score itself is also what a state
would quote ("the top 20% of the queue holds ~$X of errors"). Two known
biases make the raw number unreliable:
  1. P(error) from gradient boosting is not calibrated.
  2. The dollar regressor predicts log1p(dollars); expm1 of the mean log is
     the geometric mean, which underestimates the arithmetic mean (PA5 saw up
     to ~40% low).
Fixes, both fit on out-of-fold (OOF) predictions inside the training rows:
  isotonic calibration of P(error); Duan's smearing for the dollar part
  (multiply exp(prediction) by the mean of exp(OOF residuals), then -1).
Both preserve the ranking order (isotonic is monotone; smearing is a
constant factor on the dollar part), so recovered dollars barely move; what
changes is how close expected dollars land to actual dollars.

Per state: exp56 final configs (`exp56_results_<ST>_with_issued.json`), the
state's existing holdout as the check. Not a selection step.

Usage: python3 experiments/exp57_calibrated_dollars.py [--states PA,NY,TX,SD,UT,ID]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402


def run_state(st, qc_dir):
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    from sklearn.isotonic import IsotonicRegression
    from sklearn.model_selection import StratifiedKFold
    E56.WITH_ISSUED = True
    res = json.loads((ROOT / "experiments" / f"exp56_results_{st}_with_issued.json").read_text()) \
        if st != "PA" else json.loads((ROOT / "experiments" / "exp56b_results_with_issued.json").read_text())
    cfg_c, cfg_r = res["final_cfg"]["clf"], res["final_cfg"]["reg"]
    code, hfile, _, _ = E56.STATES[st]
    real = E56.load_state_real(qc_dir, code)
    hold = {tuple(k) for k in json.loads((ROOT / "experiments" / hfile).read_text())["holdout_keys"]}
    tr = [k for k in sorted(real) if k not in hold]
    te = [k for k in sorted(real) if k in hold]
    X = np.array([E56.feats(real[k][0]) for k in tr]); y = np.array([real[k][1] != "1" for k in tr], int)
    a = np.array([real[k][2] for k in tr])
    Xh = np.array([E56.feats(real[k][0]) for k in te]); yh = np.array([real[k][1] != "1" for k in te], int)
    ah = np.array([real[k][2] for k in te])

    # out-of-fold raw probabilities and log-dollar residuals on the training rows
    p_oof = np.zeros(len(y)); resid = []; s_oof = np.zeros(len(y))
    for a_idx, b_idx in StratifiedKFold(5, shuffle=True, random_state=57).split(X, y):
        c = HistGradientBoostingClassifier(random_state=0, **cfg_c).fit(X[a_idx], y[a_idx])
        p_oof[b_idx] = c.predict_proba(X[b_idx])[:, 1]
        ea = a_idx[a[a_idx] > 0]; eb = b_idx[a[b_idx] > 0]
        r = HistGradientBoostingRegressor(random_state=0, **cfg_r).fit(X[ea], np.log1p(a[ea]))
        resid += list(np.log1p(a[eb]) - r.predict(X[eb]))
        s_oof[b_idx] = p_oof[b_idx] * np.clip(np.expm1(r.predict(X[b_idx])), 0, None)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(p_oof, y)
    smear = float(np.mean(np.exp(resid)))
    # variant 3: calibrate the final dollar score directly (isotonic of actual
    # dollars on the raw OOF expected-dollar score; monotone, so order kept)
    iso_d = IsotonicRegression(out_of_bounds="clip", y_min=0).fit(s_oof, a)

    clf = HistGradientBoostingClassifier(random_state=0, **cfg_c).fit(X, y)
    reg = HistGradientBoostingRegressor(random_state=0, **cfg_r).fit(X[a > 0], np.log1p(a[a > 0]))
    p_raw = clf.predict_proba(Xh)[:, 1]; lp = reg.predict(Xh)
    exp_raw = p_raw * np.clip(np.expm1(lp), 0, None)
    exp_cal = iso.predict(p_raw) * np.clip(np.exp(lp) * smear - 1, 0, None)

    out = {"state": st, "smearing_factor": round(smear, 3), "n_holdout": len(te)}
    exp_iso = iso_d.predict(exp_raw)
    for name, score in (("raw", exp_raw), ("calibrated", exp_cal), ("isotonic_$", exp_iso)):
        row = {}
        for frac in (0.10, 0.20, 0.30, 1.0):
            k = int(round(len(score) * frac)); idx = np.argsort(-exp_raw, kind="stable")[:k]  # same order
            row[f"top{int(frac * 100)}"] = {"expected_$": round(float(score[idx].sum()), 0),
                                            "actual_$": round(float(ah[idx].sum()), 0),
                                            "ratio": round(float(score[idx].sum() / max(ah[idx].sum(), 1)), 3)}
        out[name] = row
    # P(error) calibration by decile of the raw score
    for name, p in (("raw", p_raw), ("calibrated", iso.predict(p_raw))):
        order = np.argsort(p); bins = np.array_split(order, 10)
        out[f"ece_{name}"] = round(float(sum(len(b) * abs(p[b].mean() - yh[b].mean()) for b in bins) / len(p)), 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-dir", default=str(ROOT.parent / "snap-qc-data/raw"))
    ap.add_argument("--states", default="PA,NY,TX,SD,UT,ID")
    args = ap.parse_args()
    results = []
    print(f"{'state':5s} {'smear':>6s} | expected / actual: top 10% / top 20% / all  [raw | smear+iso-P | iso-$]")
    for st in args.states.split(","):
        r = run_state(st, args.qc_dir)
        results.append(r)
        cells = ["/".join(f"{r[v][t]['ratio']:.2f}" for t in ("top10", "top20", "top100"))
                 for v in ("raw", "calibrated", "isotonic_$")]
        print(f"{st:5s} {r['smearing_factor']:6.2f} | " + " | ".join(cells), flush=True)
    (ROOT / "experiments" / "exp57_results.json").write_text(json.dumps(results, indent=1))
    print("wrote experiments/exp57_results.json")


if __name__ == "__main__":
    main()
