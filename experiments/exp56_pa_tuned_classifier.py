"""Exp 56 — tuned PA triage classifier (two-part dollar ranker).

PA5 found the production path for Pennsylvania: rank cases for review by
P(error) x E[dollars | error], trained on real PA QC features (its untuned
"(b-r)" headroom arm: 5.00x top-10% / 3.15x top-20% lift on the PA holdout),
with PA-conditioned synthetic as a cold start. This experiment tunes that
ranker for the job it does: dollars recovered per review hour.

Design (budget-time features only; AMTERR and reviewer fields never inputs):
  features  clean-8 (PA7: issued_benefit dropped) + derived ratios
            (total income, income per person, earned share, shelter / income,
            medical and depcare presence)
  objective dollars recovered in the top 20% of the ranking (PA5's metric)
  search    random search over HistGradientBoosting settings for the
            P(error) classifier and the log-dollar regressor, scored by
            3-fold CV inside the training data
  estimate  nested CV: 5 outer folds on the 2,451 non-holdout PA cases, each
            running its own inner search, vs the untuned recipe on the same
            folds (unbiased estimate of what tuning buys)
  arms      untuned clean-8 (PA5 b-r, minus issued_benefit) | tuned real |
            tuned real + PA-synthetic rows (weight searched)
  checks    time split (tune FY2020-22, test FY2023-24, non-holdout rows);
            the PA2/PA8 817-case holdout scored once, at the end

Usage (repo root):
  python3 experiments/exp56_pa_tuned_classifier.py --qc-dir ../snap-qc-data/raw \\
      --holdout-json experiments/pa2_holdout_idx.json [--n-search 30]
"""
import argparse
import json
import random
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import pa5_dollar_ranking as pa5  # noqa: E402

CLEAN8 = ["hh_size", "earned", "unearned", "shelter", "sua", "medical_exp", "depcare", "senior_disabled"]
TOPK = (0.10, 0.20, 0.30)
REVIEW_MIN = 30


WITH_ISSUED = False  # --with-issued: add issued_benefit (known at triage time)


def feats(f, derived=True):
    x = [f[k] for k in CLEAN8] + ([f["issued_benefit"]] if WITH_ISSUED else [])
    if derived:
        inc = f["earned"] + f["unearned"]
        x += [inc, inc / max(f["hh_size"], 1.0), f["earned"] / inc if inc > 0 else 0.0,
              f["shelter"] / inc if inc > 0 else f["shelter"],
              float(f["medical_exp"] > 0), float(f["depcare"] > 0)]
    return x


def dollars_at(score, amt, frac):
    k = int(round(len(score) * frac))
    return float(amt[np.argsort(-score, kind="stable")[:k]].sum())


def sample_cfg(rng):
    return {"learning_rate": rng.choice([0.03, 0.05, 0.1]),
            "max_leaf_nodes": rng.choice([7, 15, 31]),
            "min_samples_leaf": rng.choice([10, 20, 40, 80]),
            "l2_regularization": rng.choice([0.0, 0.1, 1.0]),
            "max_iter": rng.choice([100, 200, 400])}


DEFAULT = {"learning_rate": 0.1, "max_leaf_nodes": 31, "min_samples_leaf": 20,
           "l2_regularization": 0.0, "max_iter": 100}


def fit_two_part(X, y, amt, cfg_c, cfg_r, sX=None, sy=None, samt=None, w_synth=0.0):
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    Xc, yc, wc = X, y, np.ones(len(y))
    if sX is not None and w_synth > 0:
        Xc = np.vstack([X, sX]); yc = np.concatenate([y, sy])
        wc = np.concatenate([wc, np.full(len(sy), w_synth)])
    clf = HistGradientBoostingClassifier(random_state=0, **cfg_c).fit(Xc, yc, sample_weight=wc)
    err = amt > 0
    Xr, tr, wr = X[err], np.log1p(amt[err]), np.ones(err.sum())
    if sX is not None and w_synth > 0:
        se = samt > 0
        Xr = np.vstack([Xr, sX[se]]); tr = np.concatenate([tr, np.log1p(samt[se])])
        wr = np.concatenate([wr, np.full(se.sum(), w_synth)])
    reg = HistGradientBoostingRegressor(random_state=0, **cfg_r).fit(Xr, tr, sample_weight=wr)
    return lambda Z: clf.predict_proba(Z)[:, 1] * np.clip(np.expm1(reg.predict(Z)), 0, None), clf


def cv_dollars(X, y, amt, cfg_c, cfg_r, folds, synth=None, w_synth=0.0):
    tot = 0.0
    for tr, te in folds:
        f, _ = fit_two_part(X[tr], y[tr], amt[tr], cfg_c, cfg_r,
                            *(synth or (None, None, None)), w_synth=w_synth)
        tot += dollars_at(f(X[te]), amt[te], 0.20)
    return tot


def search(X, y, amt, n_search, seed, synth=None):
    from sklearn.model_selection import StratifiedKFold
    folds = list(StratifiedKFold(3, shuffle=True, random_state=seed).split(X, y))
    rng = random.Random(seed)
    best = (cv_dollars(X, y, amt, DEFAULT, DEFAULT, folds), DEFAULT, DEFAULT, 0.0)
    for _ in range(n_search):
        cc, cr = sample_cfg(rng), sample_cfg(rng)
        w = rng.choice([0.0, 0.05, 0.1, 0.3]) if synth else 0.0
        s = cv_dollars(X, y, amt, cc, cr, folds, synth, w)
        if s > best[0]:
            best = (s, cc, cr, w)
    return best[1:]


def report(name, score, amt, y, over):
    from sklearn.metrics import roc_auc_score
    n, tot = len(score), float(amt.sum())
    out = {"auc_p_error_proxy": None}
    line = [f"{name:34s}"]
    for frac in TOPK:
        k = int(round(n * frac))
        rec = dollars_at(score, amt, frac)
        rand = tot * frac
        out[f"top{int(frac * 100)}"] = {"recovered_$": round(rec, 2), "lift": round(rec / rand, 3),
                                         "per_hour_$": round(rec / (k * REVIEW_MIN / 60), 2)}
        line.append(f"top{int(frac * 100)}% ${rec:>8,.0f} {rec / rand:4.2f}x ${rec / (k * REVIEW_MIN / 60):>4,.0f}/hr")
    print("  ".join(line), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json", required=True)
    ap.add_argument("--n-search", type=int, default=30)
    ap.add_argument("--synth-n", type=int, default=20000)
    ap.add_argument("--out", default=str(ROOT / "experiments" / "exp56_results.json"))
    ap.add_argument("--with-issued", action="store_true",
                    help="add issued_benefit: PA7 dropped it for element classification, "
                         "but the agency's issued amount is known before QC review")
    args = ap.parse_args()
    global WITH_ISSUED
    WITH_ISSUED = args.with_issued
    from sklearn.model_selection import StratifiedKFold
    from synth.pa_state import generate_pa

    real = pa5.load_pa_real(args.qc_dir)
    hold = {tuple(k) for k in json.loads(Path(args.holdout_json).read_text())["holdout_keys"]}
    tr_keys = [k for k in sorted(real) if k not in hold]
    te_keys = [k for k in sorted(real) if k in hold]

    def arrays(keys, derived=True):
        X = np.array([feats(real[k][0], derived) for k in keys])
        y = np.array([real[k][1] != "1" for k in keys], dtype=int)
        amt = np.array([real[k][2] for k in keys])
        over = np.array([real[k][1] == "2" for k in keys], dtype=int)
        return X, y, amt, over

    Xtr, ytr, atr, _ = arrays(tr_keys)
    Xte, yte, ate, ote = arrays(te_keys)
    Xtr8, _, _, _ = arrays(tr_keys, derived=False)
    Xte8, _, _, _ = arrays(te_keys, derived=False)
    print(f"PA real: train {len(tr_keys)} (errors {ytr.sum()}), holdout {len(te_keys)}", flush=True)

    tf = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False); tf.close()
    generate_pa(n=args.synth_n, seed=7, dist=str(ROOT / "experiments/dist.json"), out=tf.name)
    srows = pa5.load_synth(tf.name)
    sX = np.array([feats(r[0]) for r in srows])
    sy = np.array([int(r[1]) for r in srows]); samt = np.array([r[2] for r in srows])
    synth = (sX, sy, samt)
    print(f"PA synthetic: {len(srows)} cases (errors {sy.sum()})", flush=True)

    # ---- nested CV estimate on the non-holdout rows
    outer = list(StratifiedKFold(5, shuffle=True, random_state=56).split(Xtr, ytr))
    est = {"untuned_clean8": 0.0, "tuned_real": 0.0, "tuned_real_synth": 0.0}
    picks = []
    for i, (a, b) in enumerate(outer):
        f_u, _ = fit_two_part(Xtr8[a], ytr[a], atr[a], DEFAULT, DEFAULT)
        est["untuned_clean8"] += dollars_at(f_u(Xtr8[b]), atr[b], 0.20)
        cc, cr, _ = search(Xtr[a], ytr[a], atr[a], args.n_search, seed=100 + i)
        f_t, _ = fit_two_part(Xtr[a], ytr[a], atr[a], cc, cr)
        est["tuned_real"] += dollars_at(f_t(Xtr[b]), atr[b], 0.20)
        cc2, cr2, w = search(Xtr[a], ytr[a], atr[a], args.n_search, seed=200 + i, synth=synth)
        f_s, _ = fit_two_part(Xtr[a], ytr[a], atr[a], cc2, cr2, *synth, w_synth=w)
        est["tuned_real_synth"] += dollars_at(f_s(Xtr[b]), atr[b], 0.20)
        picks.append({"real": [cc, cr], "real_synth": [cc2, cr2, w]})
        print(f"outer fold {i + 1}/5 done (synth weight picked {w})", flush=True)
    rand = float(atr.sum()) * 0.20
    print("\nnested-CV top-20% dollars (sum over outer folds; random = "
          f"${rand:,.0f}):", flush=True)
    for k, v in est.items():
        print(f"  {k:20s} ${v:>9,.0f}  lift {v / rand:.2f}x", flush=True)

    # ---- time-split check (non-holdout rows): tune FY2020-22, test FY2023-24
    early = np.array([k[0] <= 2022 for k in tr_keys])
    cc_t, cr_t, _ = search(Xtr[early], ytr[early], atr[early], args.n_search, seed=300)
    f_tt, _ = fit_two_part(Xtr[early], ytr[early], atr[early], cc_t, cr_t)
    f_tu, _ = fit_two_part(Xtr8[early], ytr[early], atr[early], DEFAULT, DEFAULT)
    late = ~early
    t_rand = float(atr[late].sum()) * 0.20
    t_tuned = dollars_at(f_tt(Xtr[late]), atr[late], 0.20)
    t_untuned = dollars_at(f_tu(Xtr8[late]), atr[late], 0.20)
    print(f"\ntime split (FY23-24, n={late.sum()}): untuned {t_untuned / t_rand:.2f}x, "
          f"tuned {t_tuned / t_rand:.2f}x", flush=True)

    # ---- final: search on all non-holdout rows, score the holdout once
    best_arm = max(("tuned_real", "tuned_real_synth"), key=lambda k: est[k])
    syn = synth if best_arm == "tuned_real_synth" else None
    cc, cr, w = search(Xtr, ytr, atr, args.n_search, seed=400, synth=syn)
    f_final, _ = fit_two_part(Xtr, ytr, atr, cc, cr, *(syn or (None, None, None)), w_synth=w)
    f_base, _ = fit_two_part(Xtr8, ytr, atr, DEFAULT, DEFAULT)
    print(f"\nHOLDOUT (n={len(te_keys)}, scored once) — final arm: {best_arm}", flush=True)
    res_hold = {"untuned_clean8": report("untuned clean-8 (PA5 b-r style)", f_base(Xte8), ate, yte, ote),
                "final": report(f"tuned ({best_arm})", f_final(Xte), ate, yte, ote)}
    out = {"nested_cv_top20_$": est, "nested_cv_random_top20_$": rand,
           "time_split": {"untuned_lift": t_untuned / t_rand, "tuned_lift": t_tuned / t_rand},
           "final_arm": best_arm, "final_cfg": {"clf": cc, "reg": cr, "w_synth": w},
           "holdout": res_hold, "outer_picks": picks}
    Path(args.out).write_text(json.dumps(out, indent=1, default=float))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
