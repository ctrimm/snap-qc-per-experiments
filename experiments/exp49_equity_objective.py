"""Exp49 — prototype equity fixes for the dollar-ranker household-type tilt (exp47).

exp47 found the PA/NY dollar rankers systematically under-review elderly and
disabled households relative to their error risk (PA review-to-risk ratios
0.22/0.33, NY 0.34/0.35; childless adults 1.41/1.45) because the dollar
objective deprioritizes frequent small-dollar errors. This experiment
prototypes two simple fixes and measures what they cost in headline $/hr.

Variant A (per-type floors): reserve a fraction f of the review budget and
allocate it across household types proportional to each type's share of
holdout errors (floor_t = k*f*err_share_t, within-type top by dollar
score); fill the rest of the budget by pure dollar rank. Floor strengths
f in {0.25, 0.5, 1.0} (f=1.0 = entire budget allocated proportional to
errors, the full-equity endpoint where rev/base ratios are constant).

Variant B (equity-weighted ranker): rank by expected_$ x w_t, upweighting
elderly and disabled_nonelderly. Sweep w in {1.0, 1.5, 2.5, 4.0}
(1.0 = pure-dollar baseline).

Rankers, holdouts, and taxonomy reproduced exactly from exp47 (pooled
seed-7 synthetic; pa2/ny2 shared holdouts 817/815; MIN_TYPE_N=25 merges).

Reproduction (from repo root), synth files already built by exp47:
  python3 experiments/exp49_equity_objective.py \\
      --pa-synth /tmp/exp47out/pa_synth.jsonl \\
      --ny-synth /tmp/exp47out/ny_synth.jsonl \\
      --qc-dir ~/workspace/snap-qc-data/raw

CPU only. Microdata read-only. Raw tables -> /tmp/exp49out/exp49_results.json
(scratch, not committed).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # experiments/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pa5_dollar_ranking as pa5  # noqa: E402
import ny5_dollar_ranking as ny5  # noqa: E402
import exp47_household_type_burden as e47  # noqa: E402

FRAC = 0.20  # top-20% budget, like the pilot headline
REVIEW_HOURS = 0.5  # 30-min review assumption
FLOOR_FRACS = (0.50, 0.75, 1.00)
EQUITY_WEIGHTS = (1.0, 1.5, 2.5, 4.0)
VULNERABLE = ("elderly", "disabled_nonelderly")


def train_rankers(pa_synth_path, ny_synth_path, pa_train, ny_train,
                  pa_test, ny_test):
    import numpy as np
    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  HistGradientBoostingRegressor)
    from sklearn.isotonic import IsotonicRegression

    print("training PA two-part ranker (pa5 recipe, V1)...", flush=True)
    pa_synth = pa5.load_synth(pa_synth_path)
    pa_synth_err = [r for r in pa_synth if r[1]]
    sX = pa5.X(pa_synth)
    sy = [1 if r[1] else 0 for r in pa_synth]
    tX = pa5.X(pa_train)
    ty = [1 if r[1] != "1" else 0 for r in pa_train]
    hX_pa = pa5.X(pa_test)
    clf = HistGradientBoostingClassifier(random_state=0)
    clf.fit(sX, sy)
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(clf.predict_proba(tX)[:, 1], ty)
    p_err = np.clip(iso.predict(clf.predict_proba(hX_pa)[:, 1]),
                    1e-6, 1 - 1e-6)
    reg_err = HistGradientBoostingRegressor(random_state=0)
    reg_err.fit(pa5.X(pa_synth_err),
                np.log1p(np.array([r[2] for r in pa_synth_err])))
    score_pa = p_err * np.clip(np.expm1(reg_err.predict(hX_pa)), 0, None)

    print("training NY direct expected-dollar ranker (ny5 CLEAN8)...", flush=True)
    ny_synth = ny5.load_synth(ny_synth_path)
    reg_all = HistGradientBoostingRegressor(random_state=0)
    reg_all.fit(ny5.X(ny_synth),
                np.log1p(np.array([r[2] for r in ny_synth])))
    score_ny = np.clip(np.expm1(reg_all.predict(ny5.X(ny_test))), 0, None)
    return score_pa, score_ny


def largest_remainder(quotas, total):
    """Integer allocation of `total` to keys by largest remainder."""
    base = {t: int(q) for t, q in quotas.items()}
    rem = total - sum(base.values())
    fracs = sorted(((quotas[t] - base[t], t) for t in quotas), reverse=True)
    i = 0
    while rem > 0 and fracs:
        base[fracs[i % len(fracs)][1]] += 1
        rem -= 1
        i += 1
    return base


def variant_a_selection(score, types, tlist, k, floor_frac, err_share, counts):
    """Reserve floor_frac of budget as per-type floors proportional to
    error share; fill the remainder by global dollar rank."""
    import numpy as np
    target = int(round(k * floor_frac))
    quotas = {t: target * err_share[t] for t in tlist}
    floors = largest_remainder(quotas, target)
    floors = {t: min(floors[t], counts[t]) for t in tlist}
    sel = set()
    for t in tlist:
        idx = np.array([i for i, tt in enumerate(types) if tt == t])
        top = idx[np.argsort(-score[idx], kind="stable")[:floors[t]]]
        sel.update(int(i) for i in top)
    rest = k - len(sel)
    glob = np.argsort(-score, kind="stable")
    for i in glob:
        if rest <= 0:
            break
        i = int(i)
        if i not in sel:
            sel.add(i)
            rest -= 1
    return np.array(sorted(sel))


def evaluate(sel, score, y, amt, types, tlist, k):
    import numpy as np
    n = len(y)
    total_amt = float(amt.sum())
    selset = set(int(i) for i in sel)
    rec = float(amt[list(selset)].sum())
    prec = float(y[list(selset)].sum() / k)
    per_type = {}
    ratios = []
    for t in tlist:
        idx = np.array([i for i, tt in enumerate(types) if tt == t])
        nt = len(idx)
        base_err = float(y[idx].sum() / nt)
        rev_rate = float(sum(1 for i in idx if int(i) in selset) / nt)
        ratio = rev_rate / base_err if base_err else 0.0
        ratios.append(ratio)
        type_sel = [int(i) for i in idx if int(i) in selset]
        prec_t = float(y[type_sel].sum() / len(type_sel)) if type_sel else 0.0
        per_type[t] = {
            "n": nt,
            "base_error_rate": round(base_err, 4),
            "review_rate": round(rev_rate, 4),
            "precision_in_type": round(prec_t, 4),
            "review_rate_over_base_error_rate": round(ratio, 3),
            "share_of_type_error_$_recovered": round(
                float(amt[type_sel].sum() / amt[idx].sum()), 4)
            if amt[idx].sum() else 0.0,
        }
    ratios = np.array(ratios)
    return {
        "k": k,
        "selected_idx": sorted(int(i) for i in selset),
        "recovered_$": round(rec, 2),
        "share_of_total_$": round(rec / total_amt, 4),
        "precision": round(prec, 4),
        "$_per_hour": round(rec / (k * REVIEW_HOURS), 2),
        "per_type": per_type,
        "equity": {
            "min_review_to_risk_ratio": round(float(ratios.min()), 3),
            "max_review_to_risk_ratio": round(float(ratios.max()), 3),
            "cv_review_to_risk_ratio": round(
                float(ratios.std() / ratios.mean()), 3)
            if ratios.mean() else 0.0,
            "elderly_review_rate": per_type.get("elderly", {}).get(
                "review_rate"),
            "disabled_review_rate": per_type.get("disabled_nonelderly", {}).get(
                "review_rate"),
        },
    }


def random_baseline(y, amt, types, tlist, k):
    """Analytic expectations for uniform random review."""
    import numpy as np
    n = len(y)
    total_amt = float(amt.sum())
    total_err = int(y.sum())
    rec = (k / n) * total_amt
    per_type = {}
    ratios = []
    for t in tlist:
        idx = np.array([i for i, tt in enumerate(types) if tt == t])
        nt = len(idx)
        base_err = float(y[idx].sum() / nt)
        rev_rate = k / n
        ratio = rev_rate / base_err if base_err else 0.0
        ratios.append(ratio)
        per_type[t] = {
            "n": nt,
            "base_error_rate": round(base_err, 4),
            "review_rate": round(rev_rate, 4),
            "precision_in_type": round(base_err, 4),
            "review_rate_over_base_error_rate": round(ratio, 3),
            "share_of_type_error_$_recovered": round(k / n, 4),
        }
    ratios = np.array(ratios)
    return {
        "k": k, "recovered_$": round(rec, 2),
        "share_of_total_$": round(rec / total_amt, 4),
        "precision": round(total_err / n, 4),
        "$_per_hour": round(rec / (k * REVIEW_HOURS), 2),
        "per_type": per_type,
        "equity": {
            "min_review_to_risk_ratio": round(float(ratios.min()), 3),
            "max_review_to_risk_ratio": round(float(ratios.max()), 3),
            "cv_review_to_risk_ratio": round(
                float(ratios.std() / ratios.mean()), 3)
            if ratios.mean() else 0.0,
            "elderly_review_rate": per_type.get("elderly", {}).get(
                "review_rate"),
            "disabled_review_rate": per_type.get("disabled_nonelderly", {}).get(
                "review_rate"),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pa-synth", required=True)
    ap.add_argument("--ny-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    args = ap.parse_args()
    import numpy as np

    out = Path("/tmp/exp49out")
    out.mkdir(parents=True, exist_ok=True)
    results = {"budget_frac": FRAC, "review_hours_per_case": REVIEW_HOURS,
               "floor_fracs": list(FLOOR_FRACS),
               "equity_weights": list(EQUITY_WEIGHTS)}

    print("loading real microdata...", flush=True)
    pa_real = e47.load_state_real(args.qc_dir, "42", pa5.real_row_features)
    ny_real = e47.load_state_real(args.qc_dir, "36", ny5.real_row_features)
    pa_hj = json.loads(Path("experiments/pa2_holdout_idx.json").read_text())
    ny_hj = json.loads(Path("experiments/ny2_holdout_idx.json").read_text())
    pa_hold = {tuple(k) for k in pa_hj["holdout_keys"]}
    ny_hold = {tuple(k) for k in ny_hj["holdout_keys"]}

    def split(real, hold):
        keys = sorted(real.keys())
        return ([real[k] for k in keys if k not in hold],
                [real[k] for k in keys if k in hold])

    pa_train, pa_test = split(pa_real, pa_hold)
    ny_train, ny_test = split(ny_real, ny_hold)
    assert len(pa_test) == 817 and len(ny_test) == 815

    score_pa, score_ny = train_rankers(args.pa_synth, args.ny_synth,
                                      pa_train, ny_train, pa_test, ny_test)

    for st, test, train, score in (("PA", pa_test, pa_train, score_pa),
                                   ("NY", ny_test, ny_train, score_ny)):
        n = len(test)
        k = int(round(n * FRAC))
        y = np.array([1 if r[1] != "1" else 0 for r in test])
        amt = np.array([r[2] for r in test])
        raw_types = [e47.household_type(r[3]) for r in test]
        counts = {t: raw_types.count(t) for t in set(raw_types)}
        small = {t for t in set(raw_types) if counts[t] < e47.MIN_TYPE_N}

        def merge_holdout(t):
            return "other_small" if t in small else t

        types = [merge_holdout(t) for t in raw_types]
        counts = {t: types.count(t) for t in set(types)}
        tlist = [t for t in e47.TYPE_ORDER if t in counts]
        # Floor weights MUST come from the train split (known at ranker-build
        # time), never from holdout labels: err_share_t = train errors in
        # type t / total train errors, with the holdout's merge rule applied.
        tr_types = [merge_holdout(e47.household_type(r[3])) for r in train]
        tr_y = np.array([1 if r[1] != "1" else 0 for r in train])
        tr_total_err = int(tr_y.sum())
        err_share = {}
        for t in tlist:
            idx = [i for i, tt in enumerate(tr_types) if tt == t]
            err_share[t] = float(tr_y[idx].sum() / tr_total_err)
        s = sum(err_share.values())  # ~1; guards rounding
        err_share = {t: err_share[t] / s for t in tlist}

        variants = {}
        # baseline: pure dollar rank
        order = np.argsort(-score, kind="stable")[:k]
        variants["baseline_dollar"] = evaluate(
            order, score, y, amt, types, tlist, k)
        # random (analytic)
        variants["random"] = random_baseline(y, amt, types, tlist, k)
        # Variant A: per-type floors
        for f in FLOOR_FRACS:
            sel = variant_a_selection(score, types, tlist, k, f,
                                      err_share, counts)
            variants[f"floor_f{f}"] = evaluate(sel, score, y, amt,
                                               types, tlist, k)
        # Variant B: equity-weighted score
        for w in EQUITY_WEIGHTS:
            wvec = np.array([w if t in VULNERABLE else 1.0 for t in types])
            wscore = score * wvec
            border = np.argsort(-wscore, kind="stable")[:k]
            variants[f"weight_w{w}"] = evaluate(border, score, y, amt,
                                                types, tlist, k)
        results[st] = {"n": n, "k": k, "variants": variants}

        print(f"\n===== {st} top-20% (k={k}) tradeoff =====", flush=True)
        print("  variant          |  $/hr | share$ | prec | min_r | CV_r  | "
              "eld_rr | dis_rr", flush=True)
        for name, v in variants.items():
            e = v["equity"]
            print(f"  {name:16s} | {v['$_per_hour']:5.1f} | "
                  f"{v['share_of_total_$']:.3f} | {v['precision']:.3f} | "
                  f"{e['min_review_to_risk_ratio']:.3f} | "
                  f"{e['cv_review_to_risk_ratio']:.3f} | "
                  f"{e['elderly_review_rate']:.3f} | "
                  f"{e['disabled_review_rate']:.3f}", flush=True)

        print(f"\n  -- {st} per-type detail (rev_rate | ratio) --", flush=True)
        for name in ("baseline_dollar", "floor_f1.0", "weight_w2.5",
                     "weight_w4.0"):
            v = variants[name]
            cells = " ".join(
                f"{t[:6]}:{v['per_type'][t]['review_rate']:.2f}/"
                f"{v['per_type'][t]['review_rate_over_base_error_rate']:.2f}"
                for t in tlist)
            print(f"  {name:16s} {cells}", flush=True)

    with open(out / "exp49_results.json", "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nresults -> {out / 'exp49_results.json'}", flush=True)


if __name__ == "__main__":
    main()
