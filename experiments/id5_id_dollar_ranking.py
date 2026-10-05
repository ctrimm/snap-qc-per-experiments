"""ID5 — dollar-impact ranking for the Idaho POC track.

A CIO cares about recovery per review hour, not classification accuracy. This
experiment ranks held-out real ID cases by expected error dollars and compares
three ranking rules:

  (a) P(error)-only: calibrated P(error) from ID2's best classifier
      (ID-conditioned synthetic n=20k seed 7, HistGradientBoostingClassifier
      with class_weight='balanced' — ID2: balanced wins finding AUC 3/3),
      calibrated on the real ID train split.
  (b) two-part: calibrated P(error) x E[AMTERR|features], where the dollar
      regressor is trained on ID-synth error cases (log1p target).
  (c) direct: a single expected-dollar regressor trained on all ID-synth
      cases (AMTERR target, 0 for correct cases).

Headroom arms (real-ID-trained, 5-fold, never touching the holdout):
  (b-r) real two-part: P(error) x E[AMTERR|features] both trained on the real
        ID train split.
  (c-r) real direct expected-dollar regressor trained on the real ID train.

FEATURE SET (per ID7): ID7's leakage audit found issued_benefit (RAWBEN,
the post-decision issued amount) is a leakage feature with an immaterial
delta. All ID5 arms use the CLEAN 8-feature set (drop issued_benefit).

Metric: dollars recovered per review hour at top-k (10/20/30% of the 960-case
holdout), vs a random-review-order baseline. REVIEW-COST ASSUMPTION: 30
minutes per case review (documented assumption, not measured); sensitivity
shown at 15 and 60 minutes. Recovered dollars are actual AMTERR of reviewed
cases (retrospective on QC-labeled cases). Over/under split reported:
over-issuance dollars are program savings; under-issuance dollars found mean
households were underpaid (outreach, not recovery).

AMTERR is reviewer-verified and includes the +/-$1 rounding tolerance; it is
never used as an input feature. No FYWGT is used (PA5 did not use it either).
Microdata is read-only.

Reproduction (exact commands, from repo root):
  1) python3 -m src.synth.id_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out /tmp/id45out/id_synth.jsonl
  2) python3 experiments/id5_dollar_ranking.py \\
        --id-synth /tmp/id45out/id_synth.jsonl \\
        --qc-dir ../snap-qc-data/raw \\
        --holdout-json experiments/id2_holdout_idx.json

Requires: scikit-learn, numpy.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth.codebook import element_bucket  # noqa: E402

# Clean v1: ID7's 8-feature set (issued_benefit dropped as leakage).
CLEAN8 = ["hh_size", "earned", "unearned", "shelter", "sua",
          "medical_exp", "depcare", "senior_disabled"]
ID_STATE = "16"
SUA_YES = {"3", "4", "5", "6", "7", "8"}
FY_FILES = [2020, 2021, 2022, 2023, 2024]
TOPK_FRACS = (0.10, 0.20, 0.30)
REVIEW_MINUTES = (15, 30, 60)  # base assumption is 30; 15/60 are sensitivity
BASE_REVIEW_MIN = 30


def fnum(v):
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def real_row_features(row):
    return {
        "hh_size": float(int(fnum(row["CERTHHSZ"]))),
        "earned": fnum(row["FSEARN"]),
        "unearned": fnum(row["FSUNEARN"]),
        "shelter": fnum(row["SHELDED"]),
        "sua": 1.0 if row["SUA1"].strip() in SUA_YES else 0.0,
        "medical_exp": fnum(row["FSMEDEXP"]),
        "depcare": fnum(row["FSDEPDED"]),
        "senior_disabled": 1.0 if (fnum(row["FSNELDER"]) > 0
                                   or fnum(row["FSNDIS"]) > 0) else 0.0,
    }


def load_id_real(qc_dir):
    """key -> (features, status, amterr, element_bucket|None). Same key
    convention as id2_id_transfer.load_id_real: (fy, id-relative row idx)."""
    rows = {}
    for fy in FY_FILES:
        path = Path(qc_dir) / f"qcfy{fy}_csv" / f"qc_pub_fy{fy}.csv"
        if not path.exists():
            raise FileNotFoundError(f"no csv at {path}")
        with open(path, newline="") as fh:
            id_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != ID_STATE:
                    continue
                status = row["STATUS"].strip()
                e1 = row.get("ELEMENT1", "").strip()
                bucket = element_bucket(int(e1)) if (e1 and status != "1") else None
                rows[(fy, id_idx)] = (
                    real_row_features(row),
                    status,
                    fnum(row["AMTERR"]),
                    bucket,
                )
                id_idx += 1
    return rows


def load_synth(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            # case-level dollar error: abs(correct_benefit - issued_benefit),
            # 0 for correct cases.
            dollar = float(c.get("dollar_error") or 0.0)
            f = c["issued_facts"]
            feats = {
                "hh_size": float(f["hh_size"]), "earned": float(f["earned"]),
                "unearned": float(f["unearned"]),
                "shelter": float(f["shelter"]), "sua": float(f["sua"]),
                "medical_exp": float(f["medical_exp"]),
                "depcare": float(f["depcare"]),
                "senior_disabled": float(f["senior_disabled"]),
            }
            rows.append((feats, int(c["finding"]) != 1, float(dollar)))
    return rows


def X(rows):
    return [[r[0][k] for k in CLEAN8] for r in rows]


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n else 0.0


def choose_calibrator(scores, y, seed=20260929):
    """5-fold stratified CV Brier: isotonic vs Platt (same protocol as ID4).
    Returns calibrated scores on `scores` itself (refit on all of y)."""
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    import numpy as np
    scores = np.asarray(scores)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    briers = {"isotonic": [], "platt": []}
    for tri, vai in skf.split(scores, y):
        ir = IsotonicRegression(out_of_bounds="clip").fit(scores[tri], y[tri])
        pi = np.clip(ir.predict(scores[vai]), 1e-6, 1 - 1e-6)
        briers["isotonic"].append(float(np.mean((pi - y[vai]) ** 2)))
        lr = LogisticRegression().fit(scores[tri].reshape(-1, 1), y[tri])
        pp = lr.predict_proba(scores[vai].reshape(-1, 1))[:, 1]
        briers["platt"].append(float(np.mean((pp - y[vai]) ** 2)))
    name = min(briers, key=lambda k: sum(briers[k]) / len(briers[k]))
    if name == "isotonic":
        cal = IsotonicRegression(out_of_bounds="clip").fit(scores, y)
        p = np.clip(cal.predict(scores), 1e-6, 1 - 1e-6)
    else:
        cal = LogisticRegression().fit(scores.reshape(-1, 1), y)
        p = cal.predict_proba(scores.reshape(-1, 1))[:, 1]
    briers = {k: round(sum(v) / len(v), 5) for k, v in briers.items()}
    return name, briers, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json", required=True)
    args = ap.parse_args()

    import numpy as np
    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  HistGradientBoostingRegressor)
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold

    print("loading real ID microdata...", flush=True)
    real = load_id_real(args.qc_dir)
    hj = json.loads(Path(args.holdout_json).read_text())
    holdout_keys = {tuple(k) for k in hj["holdout_keys"]}
    train_keys = [k for k in sorted(real.keys()) if k not in holdout_keys]
    test_keys = [k for k in sorted(real.keys()) if k in holdout_keys]
    train_real = [real[k] for k in train_keys]
    test_real = [real[k] for k in test_keys]
    print(f"  train {len(train_real)} / test {len(test_real)}", flush=True)

    # sanity: AMTERR semantics on the train split (never a model input)
    am_over = [r[2] for r in train_real if r[1] == "2"]
    am_under = [r[2] for r in train_real if r[1] == "3"]
    am_corr = [r[2] for r in train_real if r[1] == "1"]
    print(f"  AMTERR medians: over={median(am_over):.0f} under={median(am_under):.0f} "
          f"correct_max={max(am_corr):.0f} (n_over={len(am_over)} n_under={len(am_under)})",
          flush=True)
    assert max(am_corr) == 0.0, "correct cases must carry $0 AMTERR"

    print("loading ID-conditioned synthetic...", flush=True)
    synth = load_synth(args.id_synth)
    synth_err = [r for r in synth if r[1]]
    synth_corr_dollar = sum(r[2] for r in synth if not r[1])
    assert synth_corr_dollar == 0.0, "synth correct cases must carry $0 dollar_error"
    print(f"  synth {len(synth)} cases, {len(synth_err)} errors", flush=True)

    sX, sy = X(synth), [1 if r[1] else 0 for r in synth]
    tX, ty = X(train_real), [1 if r[1] != "1" else 0 for r in train_real]
    hX = X(test_real)
    y_hold = np.array([1 if r[1] != "1" else 0 for r in test_real])
    amt_hold = np.array([r[2] for r in test_real])
    over_hold = np.array([1 if r[1] == "2" else 0 for r in test_real])
    under_hold = np.array([1 if r[1] == "3" else 0 for r in test_real])
    bucket_hold = [r[3] for r in test_real]

    # ---- (a) P(error) classifier: ID2's best recipe, calibrated on real train
    print("training (a) P(error) classifier + calibration...", flush=True)
    clf = HistGradientBoostingClassifier(random_state=0, class_weight="balanced")
    clf.fit(sX, sy)
    raw_train = clf.predict_proba(tX)[:, 1]
    raw_hold = clf.predict_proba(hX)[:, 1]
    cal_name, cal_briers, _ = choose_calibrator(raw_train, np.array(ty))
    # apply the chosen calibrator (refit on all of train) to the holdout
    if cal_name == "isotonic":
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(raw_train, np.array(ty))
        p_err = np.clip(iso.predict(raw_hold), 1e-6, 1 - 1e-6)
    else:
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression().fit(raw_train.reshape(-1, 1), np.array(ty))
        p_err = lr.predict_proba(raw_hold.reshape(-1, 1))[:, 1]
    auc = roc_auc_score(y_hold, p_err)
    mean_train_amt = float(np.mean([r[2] for r in train_real if r[1] != "1"]))
    print(f"  calibration: {cal_name} (CV Brier {cal_briers}); "
          f"calibrated P(error) AUC on holdout: {auc:.4f} "
          f"(train error mean AMTERR=${mean_train_amt:.2f})", flush=True)

    # ---- (b) dollar regressor on synth error cases (log1p target)
    print("training (b) synth dollar regressor on error cases...", flush=True)
    seX = X(synth_err)
    se_dollar = np.array([r[2] for r in synth_err])
    reg_err = HistGradientBoostingRegressor(random_state=0)
    reg_err.fit(seX, np.log1p(se_dollar))
    e_amt_synth = np.clip(np.expm1(reg_err.predict(hX)), 0, None)
    score_b = p_err * e_amt_synth

    # ---- (c) direct expected-dollar regressor on all synth cases
    print("training (c) direct synth expected-dollar regressor...", flush=True)
    reg_all = HistGradientBoostingRegressor(random_state=0)
    reg_all.fit(sX, np.log1p(np.array([r[2] for r in synth])))
    score_c = np.clip(np.expm1(reg_all.predict(hX)), 0, None)

    # ---- headroom: real-trained arms via 5-fold OOF-style ensembling
    print("training headroom arms on real ID train (5-fold)...", flush=True)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    p_real_folds = np.zeros(len(hX))
    amt_real_folds = np.zeros(len(hX))
    amt_direct_folds = np.zeros(len(hX))
    tXa, tya = np.array(tX), np.array(ty)
    t_amt = np.array([r[2] for r in train_real])
    for tri, _ in skf.split(tXa, tya):
        c = HistGradientBoostingClassifier(random_state=0, class_weight="balanced")
        c.fit(tXa[tri].tolist(), tya[tri].tolist())
        p_real_folds += c.predict_proba(hX)[:, 1] / 5
        err_idx = tri[t_amt[tri] > 0]
        r1 = HistGradientBoostingRegressor(random_state=0)
        r1.fit(tXa[err_idx].tolist(), np.log1p(t_amt[err_idx]))
        amt_real_folds += np.clip(np.expm1(r1.predict(hX)), 0, None) / 5
        r2 = HistGradientBoostingRegressor(random_state=0)
        r2.fit(tXa[tri].tolist(), np.log1p(t_amt[tri]))
        amt_direct_folds += np.clip(np.expm1(r2.predict(hX)), 0, None) / 5
    score_br = p_real_folds * amt_real_folds   # (b-r) real two-part
    score_cr = amt_direct_folds               # (c-r) real direct
    auc_real = roc_auc_score(y_hold, p_real_folds)
    print(f"  real-trained P(error) AUC on holdout: {auc_real:.4f}", flush=True)

    rules = {
        "(a) P(error)-only": p_err,
        "(b) P(err) x synth-$": score_b,
        "(c) direct synth-$": score_c,
        "(b-r) real two-part [headroom]": score_br,
        "(c-r) real direct-$ [headroom]": score_cr,
    }
    # expected-dollar estimates per rule (for expected-vs-actual calibration check)
    exp_est = {
        "(a) P(error)-only": p_err * mean_train_amt,
        "(b) P(err) x synth-$": score_b,
        "(c) direct synth-$": score_c,
        "(b-r) real two-part [headroom]": score_br,
        "(c-r) real direct-$ [headroom]": score_cr,
    }

    n = len(hX)
    total_amt = float(amt_hold.sum())
    print(f"\nholdout total AMTERR: ${total_amt:,.0f} "
          f"(mean ${total_amt/n:.2f}/case, errors {int(y_hold.sum())}/{n})", flush=True)

    results = {"n_holdout": n, "total_holdout_error_$": round(total_amt, 2),
               "auc_a": round(float(auc), 4), "auc_real": round(float(auc_real), 4),
               "calibration": {"chosen": cal_name, "cv_brier": cal_briers},
               "topk": {}}
    for frac in TOPK_FRACS:
        k = int(round(n * frac))
        hours = {m: k * m / 60.0 for m in REVIEW_MINUTES}
        blk = {"k": k, "rules": {}, "random": {}}
        # random baseline (expectation over random order)
        mean_amt = total_amt / n
        rec_rand = k * mean_amt
        over_share = float(amt_hold[over_hold == 1].sum() / total_amt)
        blk["random"] = {
            "expected_recovered_$": round(rec_rand, 2),
            "over_$_share": round(over_share, 4),
            "per_hour_$": {str(m): round(rec_rand / hours[m], 2) for m in REVIEW_MINUTES},
        }
        for name, s in rules.items():
            order = np.argsort(-s, kind="stable")[:k]
            rec = float(amt_hold[order].sum())
            rec_over = float(amt_hold[order][over_hold[order] == 1].sum())
            rec_under = float(amt_hold[order][under_hold[order] == 1].sum())
            expd = float(exp_est[name][order].sum())
            n_err = int(y_hold[order].sum())
            blk["rules"][name] = {
                "recovered_$": round(rec, 2),
                "expected_$": round(expd, 2),
                "over_$": round(rec_over, 2),
                "under_$": round(rec_under, 2),
                "error_cases_in_topk": n_err,
                "share_of_total_$": round(rec / total_amt, 4) if total_amt else 0,
                "lift_vs_random": round(rec / rec_rand, 3) if rec_rand else 0,
                "per_hour_$": {str(m): round(rec / hours[m], 2) for m in REVIEW_MINUTES},
                "over_per_hour_$": {str(m): round(rec_over / hours[m], 2) for m in REVIEW_MINUTES},
            }
        results["topk"][f"{int(frac*100)}pct"] = blk
        print(f"\n== top-{int(frac*100)}% (k={k}) ==", flush=True)
        print(f"  random baseline: ${rec_rand:,.0f} recovered "
              f"(${rec_rand / hours[BASE_REVIEW_MIN]:,.0f}/hr at {BASE_REVIEW_MIN}min/case)", flush=True)
        for name in rules:
            r = blk["rules"][name]
            print(f"  {name}: recovered ${r['recovered_$']:,.0f} "
                  f"(expected ${r['expected_$']:,.0f}) lift {r['lift_vs_random']:.2f}x | "
                  f"over ${r['over_$']:,.0f} under ${r['under_$']:,.0f} | "
                  f"${r['per_hour_$'][str(BASE_REVIEW_MIN)]:,.0f}/hr "
                  f"({r['error_cases_in_topk']}/{k} error cases)", flush=True)

    # ---- oracle: where do ID's dollars actually live? (rank by actual AMTERR)
    print("\noracle — rank holdout by ACTUAL AMTERR (where the dollars live):", flush=True)
    oracle = np.argsort(-amt_hold, kind="stable")
    oracle_info = {}
    for frac in TOPK_FRACS:
        k = int(round(n * frac))
        idx = oracle[:k]
        share = float(amt_hold[idx].sum() / total_amt)
        from collections import Counter
        bmix = Counter(b if b is not None else "correct" for b in
                       [bucket_hold[i] for i in idx if y_hold[i] == 1])
        od = int(over_hold[idx].sum())
        oracle_info[f"{int(frac*100)}pct"] = {
            "share_of_total_$": round(share, 4),
            "top_buckets": [[b, c] for b, c in bmix.most_common(6)],
            "over_cases": od, "under_cases": k - od - int((y_hold[idx] == 0).sum()),
        }
        print(f"  top-{int(frac*100)}%: {share:.1%} of all error dollars | "
              f"top buckets {bmix.most_common(6)} | over {od} cases", flush=True)
    results["oracle"] = oracle_info

    out_path = "/tmp/id45out/id5_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nresults -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
