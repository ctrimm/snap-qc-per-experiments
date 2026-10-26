"""Exp 83 — full held-out evaluation of the adopted context-aware pooled models.

exp80/82 adopted context-aware pooled models in all 53 jurisdictions on two
readouts (top-20% holdout lift, time split). The deliverable also reports the
top-10% lift, the dollar forecast check, and household-type fairness with and
without the floor; those were measured on the old own-case models. This
re-measures them for the adopted models.

Pre-registered (this docstring, committed before running):
  Per jurisdiction: the adopted variant (B_ctx or C_ctx) fit on the target's
  training rows + all other jurisdictions' rows (exp80 features, default
  configuration), dollar calibrator = isotonic on 5-fold out-of-fold scores of
  the target's training rows (as exp57/58). Scored on the exp68 holdout:
  top-10% and top-20% lift, $ per review hour, expected / actual (top 20%),
  and exp72's household-type ratios and per-type floor (f = 1.0).
  This is a measurement of models already adopted, not a selection step.

Usage: python3 experiments/exp83_context_models_full_eval.py [--workers 6]
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
    ab, code, hold_keys, variant = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    import exp72_fairness_all_states as F
    from exp75_small_state_pooling import fit_w
    from sklearn.isotonic import IsotonicRegression
    from sklearn.model_selection import StratifiedKFold
    from collections import Counter
    data = _G["data"]; own = data[code]
    ho = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
    X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
    others = [(c, k) for c in data if c != code for k in data[c]]
    Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
    ao = np.array([data[c][k][2] for c, k in others])
    wown = 10.0 if variant == "C_ctx" else 1.0
    D = E56.DEFAULT
    fit = lambda Xa, ya, aa: fit_w(np.vstack([Xa, Xo]), np.concatenate([ya, yo]), np.concatenate([aa, ao]),
                                   np.concatenate([np.full(len(ya), wown), np.ones(len(yo))]), D, D)
    s_oof = np.zeros(len(y))
    for i_tr, i_te in StratifiedKFold(5, shuffle=True, random_state=83).split(X, y):
        s_oof[i_te] = fit(X[i_tr], y[i_tr], a[i_tr])(X[i_te])
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0).fit(s_oof, a)
    s = fit(X, y, a)(Xh); cal = iso.predict(s)
    res = {"state": ab, "variant": variant}
    for frac in (0.10, 0.20):
        k = int(round(len(te) * frac)); idx = np.argsort(-s, kind="stable")[:k]; rec = float(ah[idx].sum())
        res[f"top{int(frac * 100)}"] = {"lift": round(rec / max(ah.sum() * frac, 1.0), 3),
                                        "per_hour_$": round(rec / (k * E56.REVIEW_MIN / 60), 1),
                                        "random_per_hour_$": round(float(ah.sum()) * frac / (k * E56.REVIEW_MIN / 60), 1),
                                        "expected_over_actual": round(float(cal[idx].sum()) / max(rec, 1.0), 3)}
    # fairness, exp72 method
    ht_map = F.types_for(str(ROOT.parent / "snap-qc-data/raw"), code)
    ht = np.array([ht_map[k] for k in te]); cnt = Counter(ht)
    ht = np.array([t if cnt[t] >= 25 and t in F.TYPES else "other" for t in ht])
    tlist = [t for t in F.TYPES + ["other"] if (ht == t).any()]
    k = int(round(0.2 * len(te))); base = np.argsort(-s, kind="stable")[:k]
    ht_tr = np.array([ht_map[kk] for kk in tr]); ht_tr = np.array([t if t in tlist else "other" for t in ht_tr])
    share = {t: float(((ht_tr == t) & (y == 1)).sum()) / max(y.sum(), 1) for t in tlist}
    quota = {t: share[t] * k for t in tlist}; floors = {t: int(np.floor(q)) for t, q in quota.items()}
    for t in sorted(tlist, key=lambda t: -(quota[t] - floors[t]))[: k - sum(floors.values())]:
        floors[t] += 1
    sel = []
    for t in tlist:
        idx = np.where(ht == t)[0]; sel += list(idx[np.argsort(-s[idx], kind="stable")[: min(floors[t], len(idx))]])
    rest = [i for i in np.argsort(-s, kind="stable") if i not in set(sel)]
    sel = np.array(sel + rest[: k - len(sel)])
    res["fairness"] = {"baseline_ratio": F.ratios(base, yh, ht, tlist), "floor_ratio": F.ratios(sel, yh, ht, tlist),
                       "floor_lift": round(float(ah[sel].sum() / max(ah.sum() * 0.2, 1.0)), 3)}
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=6); args = ap.parse_args()
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    adopted = {}
    for f in ("exp80_results.json", "exp82_results.json"):
        for ab, r in json.loads((ROOT / "experiments" / f).read_text()).items():
            adopted[ab] = r["adopted"]
    jobs = [(ab, hold[ab]["code"], hold[ab]["keys"], v) for ab, v in sorted(adopted.items()) if v != "keep"]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    out = {}
    with get_context("spawn").Pool(args.workers, initializer=init) as pool:
        for r in pool.imap_unordered(run_one, jobs):
            out[r["state"]] = r
            print(f"{r['state']}: top20 {r['top20']['lift']:.2f}x top10 {r['top10']['lift']:.2f}x exp/act {r['top20']['expected_over_actual']:.2f} "
                  f"| elderly {r['fairness']['baseline_ratio'].get('elderly')} -> {r['fairness']['floor_ratio'].get('elderly')} "
                  f"floor lift {r['fairness']['floor_lift']:.2f}x", flush=True)
            (__import__("exp58_agency_rankers").results_path("exp83_results.json")).write_text(json.dumps(dict(sorted(out.items())), indent=1))
    v = list(out.values()); med = lambda xs: float(np.median([x for x in xs if x is not None]))
    print(f"MEDIAN top20 {med([r['top20']['lift'] for r in v]):.2f}x | top10 {med([r['top10']['lift'] for r in v]):.2f}x | "
          f"exp/act {med([r['top20']['expected_over_actual'] for r in v]):.2f} (within +-20% in "
          f"{sum(0.8 <= r['top20']['expected_over_actual'] <= 1.2 for r in v)} of {len(v)}) | floor lift "
          f"{med([r['fairness']['floor_lift'] for r in v]):.2f}x | elderly ratio {med([r['fairness']['baseline_ratio'].get('elderly') for r in v]):.2f}"
          f" -> {med([r['fairness']['floor_ratio'].get('elderly') for r in v]):.2f}")


if __name__ == "__main__":
    main()
