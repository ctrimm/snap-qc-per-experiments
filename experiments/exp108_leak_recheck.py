"""Exp 108 — recheck the flag-card coverage (item 1) and the household-type detail (item 4) under the current
SNAPQC_FEATURES (pre-registered in exp108_leak_recheck.md). Run once under legacy (gates) and once leak-free (default):

    SNAPQC_FEATURES=legacy python3 experiments/exp108_leak_recheck.py    # -> exp108_results.json (must reproduce)
    python3 experiments/exp108_leak_recheck.py                           # -> exp108_leakfree_results.json

Item 1 replicates exp62.make_cards' ranking and where-to-look model (exp65: --top-k 3): state-only two-part ranker
(exp58 configuration), cards for the top 20% of the holdout by score, where-to-look classifier
(HistGradientBoosting, random_state 61, 200 iterations, learning rate 0.05) on training error cases with a location
label. Coverage = share of flagged holdout errors with a location label whose real location is among the top-k parts.
Item 4: the deployed pooled models (exp83 design, adopted variant, exp68 holdout, top 20%) for PA and NY: per
household type n, error rate, review rate, exp47 ratio (review rate / error rate), exp72 ratio, precision among
reviewed cases; the same with the exp72 floor; lift and precision overall.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "experiments" / "eval_pilot"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402
import exp58_agency_rankers as E58  # noqa: E402
import exp62_flag_cards as X62  # noqa: E402

QC = str(ROOT.parent / "snap-qc-data/raw")


def coverage(st, cfg):
    from sklearn.ensemble import HistGradientBoostingClassifier
    real, lab, tr, te = X62.load_labels(st, QC)
    X, y, a = E58.arrays(real, tr); Xh, yh, ah = E58.arrays(real, te)
    f, _ = E56.fit_two_part(X, y, a, cfg["clf"], cfg["reg"])
    tr_e = [i for i, k in enumerate(tr) if y[i] and lab[k][0]]
    wl = HistGradientBoostingClassifier(random_state=61, max_iter=200, learning_rate=0.05).fit(
        X[tr_e], [lab[tr[i]][0] for i in tr_e])
    score = f(Xh); q80 = np.quantile(score, 0.80)
    proba = wl.predict_proba(Xh)
    ev = [i for i, k in enumerate(te) if score[i] >= q80 and yh[i] and lab[k][0]]
    out = {"n_flagged_errors_with_location": len(ev)}
    for kk in (1, 2, 3):
        hits = sum(lab[te[i]][0] in [str(c) for c in wl.classes_[np.argsort(-proba[i])[:kk]]] for i in ev)
        out[f"top{kk}"] = round(hits / max(len(ev), 1), 3)
    # how informative is the location model beyond the base rate? (always guessing the most common parts)
    common = [c for c, _ in Counter(lab[tr[i]][0] for i in tr_e).most_common(3)]
    out["base_top3_most_common_parts"] = round(sum(lab[te[i]][0] in common for i in ev) / max(len(ev), 1), 3)
    return out


def households(st):
    import exp72_fairness_all_states as F
    import exp80_state_context as X80
    from exp75_small_state_pooling import fit_w
    from exp93_cost_share_current_models import floor_select
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())[st]
    adopted = {**json.loads((ROOT / "experiments/exp80_results.json").read_text()),
               **json.loads((ROOT / "experiments/exp82_results.json").read_text())}[st]["adopted"]
    data = X80.load_all(QC); code = hold["code"]; own = data[code]
    ho = {tuple(k) for k in hold["keys"]}
    tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
    X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
    others = [(c, k) for c in data if c != code for k in data[c]]
    Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
    ao = np.array([data[c][k][2] for c, k in others])
    wown = 10.0 if adopted == "C_ctx" else 1.0
    s = fit_w(np.vstack([X, Xo]), np.concatenate([y, yo]), np.concatenate([a, ao]),
              np.concatenate([np.full(len(y), wown), np.ones(len(yo))]), E56.DEFAULT, E56.DEFAULT)(Xh)
    tmap = F.types_for(QC, code)
    ht_raw = np.array([tmap[k] for k in te]); cnt = Counter(ht_raw)
    ht = np.array([t if cnt[t] >= 25 and t in F.TYPES else "other" for t in ht_raw])
    tlist = [t for t in F.TYPES + ["other"] if (ht == t).any()]
    ht_tr = np.array([t if t in tlist else "other" for t in (tmap[k] for k in tr)])
    k20 = int(round(0.2 * len(te)))
    base = np.argsort(-s, kind="stable")[:k20]
    fl = floor_select(s, yh, ht, ht_tr, y, tlist, k20)

    def detail(sel):
        sel = np.asarray(sel); rev = np.isin(np.arange(len(te)), sel)
        overall = len(sel) / len(te) / yh.mean()
        types = {}
        for t in tlist:
            m = ht == t
            err = yh[m].mean(); rr = rev[m].mean()
            types[t] = {"n": int(m.sum()), "error_rate": round(float(err), 3), "review_rate": round(float(rr), 3),
                        "ratio_exp47": round(float(rr / err), 3) if err else None,
                        "ratio_exp72": round(float(rr / err / overall), 3) if err else None,
                        "precision_reviewed": round(float(yh[m & rev].mean()), 3) if (m & rev).any() else None}
        return {"lift": round(float(ah[sel].sum() / (ah.sum() * 0.2)), 3), "precision": round(float(yh[sel].mean()), 3),
                "types": types}
    return {"variant": adopted, "n_holdout": len(te), "random_precision": round(float(yh.mean()), 3),
            "dollar_only": detail(base), "floor": detail(fl)}


def main():
    cfgs = {r["state"]: r["cfg"] for r in json.loads((ROOT / "experiments/exp58_results.json").read_text())}
    out = {"feature_set": E58.SNAPQC_FEATURES, "coverage": {}, "households": {}}
    for st in ("PA", "NY", "ID", "UT", "SD"):
        out["coverage"][st] = coverage(st, cfgs[st])
        print(st, "coverage", out["coverage"][st], flush=True)
    for st in ("PA", "NY"):
        out["households"][st] = households(st)
        h = out["households"][st]
        print(st, "elderly ratio_exp72", h["dollar_only"]["types"]["elderly"]["ratio_exp72"], "prec reviewed",
              h["dollar_only"]["types"]["elderly"]["precision_reviewed"], "| floor lift", h["floor"]["lift"], "vs", h["dollar_only"]["lift"], flush=True)
    E58.results_path("exp108_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
