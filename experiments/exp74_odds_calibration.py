"""Exp 74 — are the flag cards' "about N in 10" odds honest, and can they be fixed?

The where-to-look model (exp61) gives P(part of case | error). Cards show the
top three parts as "about N in 10". A first look at exp65's cards: "9 in 10"
was right 57% (NY) to 71% (PA) of the time.

Pre-registered (this docstring, committed before the run):
  States PA, NY, ID (those with error-location labels and enough cases).
  Raw model: exp61's classifier trained on non-holdout error cases.
  Fix: temperature scaling. 5-fold out-of-fold probabilities on the training
  error cases; one temperature T fit by minimizing log loss on them
  (grid 0.5-4.0, step 0.05); p_cal = softmax(log p_raw / T). Ranking and
  the top three parts are unchanged (monotone).
  Test: flagged holdout errors (top 20% of the exp58 ranker), as exp61/62.
  Metric: expected calibration error (ECE) over every listed part (top 3),
  10 equal-width bins, and the same reliability table by "N in 10".
  Acceptance: the fix is adopted if ECE falls in all three states.

Usage: OMP_NUM_THREADS=8 python3 experiments/exp74_odds_calibration.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "experiments" / "eval_pilot"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402
import exp58_agency_rankers as E58  # noqa: E402
import exp61_ranker_reason_codes as E61  # noqa: E402


def wl_model(X, lab):
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(random_state=61, max_iter=200, learning_rate=0.05).fit(X, lab)


def temper(p, T):
    lp = np.log(np.clip(p, 1e-9, 1)) / T
    lp -= lp.max(axis=1, keepdims=True)
    e = np.exp(lp)
    return e / e.sum(axis=1, keepdims=True)


def ece_top3(P, classes, truth):
    pts = []
    for p, t in zip(P, truth):
        for j in np.argsort(-p)[:3]:
            pts.append((p[j], classes[j] == t))
    pts = np.array(pts, dtype=float)
    bins = np.minimum((pts[:, 0] * 10).astype(int), 9)
    ece = sum(abs(pts[bins == b, 0].mean() - pts[bins == b, 1].mean()) * (bins == b).sum()
              for b in range(10) if (bins == b).any()) / len(pts)
    table = defaultdict(lambda: [0, 0])
    for pr, hit in pts:
        n = min(9, max(1, int(round(pr * 10))))
        table[n][0] += 1; table[n][1] += hit
    return round(float(ece), 4), {k: (v[0], round(v[1] / v[0], 2)) for k, v in sorted(table.items())}


def main():
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import log_loss
    qc_dir = str(ROOT.parent / "snap-qc-data/raw")
    cfgs = {r["state"]: r["cfg"] for r in json.loads((ROOT / "experiments/exp58_results.json").read_text())}
    out = {}
    for st in ("PA", "NY", "ID"):
        code, hfile, _, _ = E56.STATES[st]
        real = E58.load_state(qc_dir, code)
        t3 = E61.t3_labels(qc_dir, code)
        hold = {tuple(k) for k in json.loads((ROOT / "experiments" / hfile).read_text())["holdout_keys"]}
        tr = [k for k in sorted(real) if k not in hold]; te = [k for k in sorted(real) if k in hold]
        X, y, a = E58.arrays(real, tr); Xh, yh, _ = E58.arrays(real, te)
        f, _ = E56.fit_two_part(X, y, a, cfgs[st]["clf"], cfgs[st]["reg"])
        s = f(Xh)
        ev = [i for i, k in enumerate(te) if s[i] >= np.quantile(s, 0.8) and yh[i] and t3[k]]
        truth = [t3[te[i]] for i in ev]
        pool = [i for i, k in enumerate(tr) if y[i] and t3[k]]
        lab = np.array([t3[tr[i]] for i in pool])
        Xp = X[pool]
        m = wl_model(Xp, lab)
        classes = m.classes_
        # out-of-fold probabilities for the temperature fit
        oof = np.zeros((len(pool), len(classes)))
        keep = np.isin(lab, [c for c in classes if (lab == c).sum() >= 5])
        skf = StratifiedKFold(5, shuffle=True, random_state=74)
        for a_i, b_i in skf.split(Xp[keep], lab[keep]):
            ia, ib = np.where(keep)[0][a_i], np.where(keep)[0][b_i]
            mm = wl_model(Xp[ia], lab[ia])
            pp = mm.predict_proba(Xp[ib])
            for j, c in enumerate(mm.classes_):
                oof[ib, list(classes).index(c)] = pp[:, j]
        oof = oof[keep] + 1e-6; oof /= oof.sum(axis=1, keepdims=True)
        grid = np.arange(0.5, 4.0001, 0.05)
        losses = [log_loss(lab[keep], temper(oof, T), labels=classes) for T in grid]
        T = float(grid[int(np.argmin(losses))])
        P = m.predict_proba(Xh[ev])
        raw = ece_top3(P, classes, truth); cal = ece_top3(temper(P, T), classes, truth)
        out[st] = {"n_flagged_errors": len(ev), "temperature": round(T, 2), "ece_raw": raw[0], "ece_calibrated": cal[0],
                   "table_raw": raw[1], "table_calibrated": cal[1]}
        print(f"{st}: n={len(ev)} T={T:.2f} ECE {raw[0]:.3f} -> {cal[0]:.3f}\n  raw  {raw[1]}\n  cal  {cal[1]}", flush=True)
    adopt = all(v["ece_calibrated"] < v["ece_raw"] for v in out.values())
    out["adopt"] = adopt
    print("adopt temperature scaling:", adopt)
    (ROOT / "experiments/exp74_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
