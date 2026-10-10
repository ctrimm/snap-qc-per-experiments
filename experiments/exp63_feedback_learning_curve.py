"""Exp 63 — how much caseworker feedback does a where-to-look model need?

exp62's flag cards rely on a per-state where-to-look model trained on error
cases with a known location (T3). States that don't record error locations
(TX) would have to build that label set from reviewer feedback. This
simulates it on PA, NY and ID: train the exp61 where-to-look classifier on
random subsets of n labelled training error cases, and score top-2 coverage
on the same flagged holdout errors as exp61/62. Baseline per subset: the two
most common locations in that subset (generic advice from the same labels).

--flagged-only: the label pool is restricted to training error cases the
ranker would have flagged (top 20% of training rows by its score), which is
all a pilot's reviewer feedback would cover.

Usage: OMP_NUM_THREADS=8 python3 experiments/exp63_feedback_learning_curve.py [--flagged-only]
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "experiments" / "eval_pilot"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402
import exp58_agency_rankers as E58  # noqa: E402
import exp61_ranker_reason_codes as E61  # noqa: E402

SIZES = [25, 50, 100, 200, 400, 800]
REPEATS = 10


def main():
    import argparse
    from sklearn.ensemble import HistGradientBoostingClassifier
    ap = argparse.ArgumentParser(); ap.add_argument("--flagged-only", action="store_true"); args = ap.parse_args()
    qc_dir = str(ROOT.parent / "snap-qc-data/raw")
    cfgs = {r["state"]: r["cfg"] for r in json.loads((ROOT / "experiments" / "exp58_results.json").read_text())}
    out = {}
    for st in ("PA", "NY", "ID"):
        code, hfile, _, _ = E56.STATES[st]
        real = E58.load_state(qc_dir, code)
        t3 = E61.t3_labels(qc_dir, code)
        hold = {tuple(k) for k in json.loads((ROOT / "experiments" / hfile).read_text())["holdout_keys"]}
        tr = [k for k in sorted(real) if k not in hold]
        te = [k for k in sorted(real) if k in hold]
        X, y, a = E58.arrays(real, tr)
        Xh, yh, _ = E58.arrays(real, te)
        f, _ = E56.fit_two_part(X, y, a, cfgs[st]["clf"], cfgs[st]["reg"])
        s = f(Xh)
        ev = [i for i, k in enumerate(te) if s[i] >= np.quantile(s, 0.8) and yh[i] and t3[k]]
        truth = [t3[te[i]] for i in ev]
        pool = [i for i, k in enumerate(tr) if y[i] and t3[k]]
        if args.flagged_only:
            s_tr = f(X)
            pool = [i for i in pool if s_tr[i] >= np.quantile(s_tr, 0.8)]
        rows = {}
        for n in [m for m in SIZES if m < len(pool)] + [len(pool)]:
            model_hits, base_hits = [], []
            for r in range(REPEATS if n < len(pool) else 1):
                sub = random.Random(1000 * n + r).sample(pool, n)
                lab = [t3[tr[i]] for i in sub]
                base = [b for b, _ in Counter(lab).most_common(2)]
                base_hits.append(np.mean([t in base for t in truth]))
                if len(set(lab)) < 2:
                    model_hits.append(base_hits[-1]); continue
                m = HistGradientBoostingClassifier(random_state=61, max_iter=200, learning_rate=0.05).fit(X[sub], lab)
                top = m.classes_[np.argsort(-m.predict_proba(Xh[ev]), axis=1)[:, :2]]
                model_hits.append(np.mean([t in set(tp) for t, tp in zip(truth, top)]))
            rows[n] = {"model_top2": round(float(np.mean(model_hits)), 3), "model_sd": round(float(np.std(model_hits)), 3),
                       "generic_top2": round(float(np.mean(base_hits)), 3)}
            print(f"{st} n={n:4d}: where-to-look {rows[n]['model_top2']:.0%} (±{rows[n]['model_sd']:.0%}) "
                  f"vs generic {rows[n]['generic_top2']:.0%}", flush=True)
        out[st] = {"flagged_eval_errors": len(ev), "label_pool": len(pool), "curve": rows}
    name = "exp63_results_flagged_only.json" if args.flagged_only else "exp63_results.json"
    (ROOT / "experiments" / name).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
