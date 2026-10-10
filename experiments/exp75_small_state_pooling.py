"""Exp 75 — can pooling other states' cases rescue the small-jurisdiction rankers?

exp68: Alaska (1.26x) and Wyoming (1.72x) are weak; both have few QC cases.

Pre-registered (this docstring, committed before running):
  Targets: every jurisdiction with fewer than 2,500 QC cases (FY2020-24).
  Variants (agency-side features, exp58 two-part model):
    A own      the target's own training rows, its exp68 configuration (= exp68)
    B pooled   own training rows + every other jurisdiction's rows, default config
    C weighted as B, own rows weighted x10 (sample_weight), default config
  Evaluation, target only: (1) top-20% lift on its exp68 holdout; (2) time
  split: train on FY2020-22 rows (own + pooled FY2020-22 for B/C), test on
  the target's FY2023-24 rows.
  Adoption: B or C replaces A for a target only if it beats A on BOTH
  readouts (if both qualify, the higher holdout lift). The targets'
  holdouts were already scored in exp68/72; nothing is selected on them
  beyond this pre-declared rule.

Usage: OMP_NUM_THREADS=8 python3 experiments/exp75_small_state_pooling.py
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402
import exp58_agency_rankers as E58  # noqa: E402
from exp68_all_state_rankers import USPS  # noqa: E402


def load_all(qc_dir):
    """{code: {(fy, idx): (features, status, amterr)}} in E58.load_state's indexing, one pass per file."""
    out = {}
    for fy in E58.FY_FILES:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")))
        idx = {}
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                c = row["STATE"].strip()
                i = idx.get(c, 0); idx[c] = i + 1
                out.setdefault(c, {})[(fy, i)] = (E58.agency_features(row), row["STATUS"].strip(), E58.fnum(row["AMTERR"]))
    return out


def fit_w(X, y, a, w, cfg_c, cfg_r):
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    clf = HistGradientBoostingClassifier(random_state=0, **cfg_c).fit(X, y, sample_weight=w)
    pos = a > 0
    reg = HistGradientBoostingRegressor(random_state=0, **cfg_r).fit(X[pos], np.log1p(a[pos]), sample_weight=w[pos])
    return lambda Z: clf.predict_proba(Z)[:, 1] * np.clip(np.expm1(reg.predict(Z)), 0, None)


def lift(score, a):
    k = int(round(0.2 * len(a)))
    return float(a[np.argsort(-score, kind="stable")[:k]].sum() / max(a.sum() * 0.2, 1.0))


def main():
    qc_dir = str(ROOT.parent / "snap-qc-data/raw")
    data = load_all(qc_dir)
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    r68 = {r["state"]: r for r in json.loads((ROOT / "experiments/exp68_results.json").read_text())}
    targets = [ab for ab, h in hold.items() if len(data[h["code"]]) < 2500]
    D = E56.DEFAULT
    out = {}
    for ab in sorted(targets, key=lambda s: len(data[hold[s]["code"]])):
        code = hold[ab]["code"]; own = data[code]
        ho = {tuple(k) for k in hold[ab]["keys"]}
        tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
        X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
        others = [(c, k) for c in data if c != code for k in data[c]]
        Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
        ao = np.array([data[c][k][2] for c, k in others]); fyo = np.array([k[0] for c, k in others])
        fy_tr = np.array([k[0] for k in tr])
        cfg = r68[ab]["cfg"]
        res = {"n_rows": len(own)}
        # A: own only, exp68 configuration
        fA = fit_w(X, y, a, np.ones(len(y)), cfg["clf"], cfg["reg"])
        e = fy_tr <= 2022; late = [k for k in sorted(own) if k[0] >= 2023]
        Xl, yl, al = E58.arrays(own, late)
        fA_ts = fit_w(X[e], y[e], a[e], np.ones(e.sum()), cfg["clf"], cfg["reg"])
        res["A"] = {"holdout": round(lift(fA(Xh), ah), 3), "time_split": round(lift(fA_ts(Xl), al), 3)}
        for name, wown in (("B", 1.0), ("C", 10.0)):
            XX = np.vstack([X, Xo]); yy = np.concatenate([y, yo]); aa = np.concatenate([a, ao])
            ww = np.concatenate([np.full(len(y), wown), np.ones(len(yo))])
            f = fit_w(XX, yy, aa, ww, D, D)
            eo = fyo <= 2022
            XX2 = np.vstack([X[e], Xo[eo]]); yy2 = np.concatenate([y[e], yo[eo]]); aa2 = np.concatenate([a[e], ao[eo]])
            ww2 = np.concatenate([np.full(e.sum(), wown), np.ones(eo.sum())])
            f2 = fit_w(XX2, yy2, aa2, ww2, D, D)
            res[name] = {"holdout": round(lift(f(Xh), ah), 3), "time_split": round(lift(f2(Xl), al), 3)}
        ok = [v for v in ("B", "C") if res[v]["holdout"] > res["A"]["holdout"] and res[v]["time_split"] > res["A"]["time_split"]]
        res["adopted"] = max(ok, key=lambda v: res[v]["holdout"]) if ok else "A"
        out[ab] = res
        print(f"{ab}: n={len(own)} | A own {res['A']['holdout']:.2f}x / {res['A']['time_split']:.2f}x | "
              f"B pooled {res['B']['holdout']:.2f}x / {res['B']['time_split']:.2f}x | "
              f"C weighted {res['C']['holdout']:.2f}x / {res['C']['time_split']:.2f}x | adopted {res['adopted']}", flush=True)
    (ROOT / "experiments/exp75_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
