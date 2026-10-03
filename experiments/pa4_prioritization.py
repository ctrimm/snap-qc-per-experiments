"""PA4 — Prioritization simulation: the SECOND DECISION POINT of the PA POC track.

Simulates a reviewer's workflow on the SHARED PA2 holdout (817 real PA cases,
seed 20260929, 75/25 stratified): train PA2's best finding arm exactly per
the recipe (PA-conditioned synthetic n=20k seed 7 + GBM WITHOUT class_weight),
calibrate its P(error) (NOT hard classification — PA2 showed hard accuracy
0.388 < majority 0.573 while binary AUC 0.645), rank holdout cases by
calibrated P(error), and report precision@k / lift / errors-per-100-reviews
vs random review order, plus what the caught errors look like (over/under
split, median dollars).

Reproduction (exact commands, from repo root):
  1) cd src && python3 -m synth.pa_state --n 20000 --seed 7 \\
        --dist ../experiments/dist.json --out /tmp/pa4out/pa_synth.jsonl
  2) python3 experiments/pa4_prioritization.py \\
        --pa-synth /tmp/pa4out/pa_synth.jsonl \\
        --qc-dir ../snap-qc-data/raw \\
        --holdout-json experiments/pa2_holdout_idx.json

Calibration design (documented choice):
  The synth-trained 3-class GBM is error-eager on real PA (PA2). We take
  raw P(error) = 1 - P(correct) = P(over) + P(under) from the frozen
  synth-trained GBM and recalibrate it on the real-PA TRAIN split (2,451
  rows, the complement of the shared holdout — disjoint from everything
  reported). Choice between isotonic and Platt (logistic) is made by
  5-fold stratified cross-validation Brier score on that real-train split;
  the winner is refit on the full train split and applied once to the
  holdout. This mirrors PA2's recommended next step ("threshold tuning on a
  real-PA validation slice").

Method notes:
  - Finding labels: 1 = correct, 2 = over-issuance, 3 = under-issuance.
  - Features: v1 (9 raw agency-view features), per exp4_v3 verdict.
  - No model weights are written anywhere. Microdata is read-only.
  - AMTERR is used for dollar-error magnitudes among caught errors.
Requires: scikit-learn.
"""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

SUA_YES = {"3", "4", "5", "6", "7", "8"}
SPLIT_SEED = 20260929
TEST_SIZE = 0.25
FY_FILES = [2020, 2021, 2022, 2023, 2024]


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
        "issued_benefit": fnum(row["RAWBEN"]),
    }


def load_pa_real(qc_dir):
    """All PA rows. Key: (fy, pa-relative row idx).
    Value: (features, finding, amterr, fsben)."""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    rows = {}
    for fy in FY_FILES:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")), None)
        if path is None:
            raise FileNotFoundError(f"no csv under qcfy{fy}_csv")
        with open(path, newline="") as fh:
            pa_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != "42":
                    continue
                rows[(fy, pa_idx)] = (
                    real_row_features(row),
                    int(row["STATUS"].strip()),
                    fnum(row.get("AMTERR", 0)),
                    fnum(row.get("FSBEN", 0)),
                )
                pa_idx += 1
    return rows


def load_synth(path):
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from synth import benefit as benefit_mod  # noqa: E402
    rows = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            f = c["issued_facts"]
            calc = benefit_mod.compute(f)  # noqa: F841  (mirrors PA2 recipe)
            rows.append(({
                "hh_size": float(f["hh_size"]), "earned": float(f["earned"]),
                "unearned": float(f["unearned"]),
                "shelter": float(f["shelter"]), "sua": float(f["sua"]),
                "medical_exp": float(f["medical_exp"]),
                "depcare": float(f["depcare"]),
                "senior_disabled": float(f["senior_disabled"]),
                "issued_benefit": float(c["issued_benefit"]),
            }, int(c["finding"])))
    return rows


def as_Xy(rows):
    return [[r[0][k] for k in V1] for r in rows], [r[1] for r in rows]


def raw_p_error(clf, X):
    """P(error) = 1 - P(correct) from the 3-class GBM."""
    proba = clf.predict_proba(X)
    correct_col = list(clf.classes_).index(1)
    return 1.0 - proba[:, correct_col]


def choose_calibrator(scores, y, seed=SPLIT_SEED):
    """5-fold stratified CV Brier: isotonic vs Platt. Returns (name, fitted
    calibrator on ALL rows)."""
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    import numpy as np
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
    else:
        cal = LogisticRegression().fit(scores.reshape(-1, 1), y)

        def _platt_predict(s):
            return cal.predict_proba(s.reshape(-1, 1))[:, 1]
        cal.predict = _platt_predict
    return name, cal, {k: round(sum(v) / len(v), 5) for k, v in briers.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pa-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json", required=True)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score, brier_score_loss
    import numpy as np

    print("loading real PA microdata...", flush=True)
    real = load_pa_real(args.qc_dir)
    print(f"  PA rows: {len(real)}", flush=True)

    hj = json.loads(Path(args.holdout_json).read_text())
    assert hj["split_seed"] == SPLIT_SEED and hj["test_size"] == TEST_SIZE
    holdout_keys = [tuple(k) for k in hj["holdout_keys"]]
    holdout_set = set(holdout_keys)
    train_keys = [k for k in sorted(real.keys()) if k not in holdout_set]
    print(f"  shared holdout: {len(holdout_keys)} test rows; "
          f"real-PA train pool (calibration): {len(train_keys)}", flush=True)

    print("loading PA synthetic (arm b of PA2: seed 7, n=20000)...", flush=True)
    pa_synth = load_synth(args.pa_synth)
    print(f"  synth rows: {len(pa_synth)}", flush=True)

    # 1) Retrain PA2's best finding model exactly per the recipe.
    print("training 3-class GBM (no class_weight, random_state=0)...", flush=True)
    sX, sy = as_Xy(pa_synth)
    clf = HistGradientBoostingClassifier(random_state=0)
    clf.fit(sX, sy)

    # 2) Calibrate P(error) on the real-PA train split (disjoint from holdout).
    cal_keys = train_keys
    cX = np.array([[real[k][0][v] for v in V1] for k in cal_keys])
    cy = np.array([1 if real[k][1] != 1 else 0 for k in cal_keys])
    raw_cal = raw_p_error(clf, cX)
    auc_cal = roc_auc_score(cy, raw_cal)
    name, cal, briers = choose_calibrator(raw_cal, cy)
    cal_p = np.clip(np.asarray(cal.predict(raw_cal)), 1e-6, 1 - 1e-6)
    print(f"calibration on real-PA train split (n={len(cal_keys)}): "
          f"raw AUC={auc_cal:.4f}, CV Brier {briers}, chosen={name}, "
          f"in-sample Brier={brier_score_loss(cy, cal_p):.5f}", flush=True)

    # 3) Rank the holdout.
    tX = np.array([[real[k][0][v] for v in V1] for k in holdout_keys])
    ty = np.array([1 if real[k][1] != 1 else 0 for k in holdout_keys])
    tdir = np.array([real[k][1] for k in holdout_keys])   # 1/2/3
    tamt = np.array([real[k][2] for k in holdout_keys])   # AMTERR
    p_err = np.clip(np.asarray(cal.predict(raw_p_error(clf, tX))), 1e-6, 1 - 1e-6)

    auc_hold = roc_auc_score(ty, p_err)
    auc_hold_raw = roc_auc_score(ty, raw_p_error(clf, tX))
    print(f"holdout: n={len(ty)}, errors={int(ty.sum())}, "
          f"base error rate={ty.mean():.4f}, raw AUC={auc_hold_raw:.4f}, "
          f"calibrated AUC={auc_hold:.4f} (calibration is monotone: identical ranking)", flush=True)

    order = np.argsort(-p_err, kind="stable")
    n = len(ty)
    base = float(ty.mean())
    total_err = int(ty.sum())

    gains = []
    for pct in [10, 20, 30, 40, 50, 100]:
        k = int(round(n * pct / 100))
        idx = order[:k]
        prec = float(ty[idx].mean())
        caught = int(ty[idx].sum())
        gains.append({
            "top_pct": pct, "k": k,
            "precision": round(prec, 4),
            "lift": round(prec / base, 3),
            "caught_errors": caught,
            "caught_share": round(caught / total_err, 4),
            "errors_per_100_reviews": round(prec * 100, 1),
        })
    for g in gains:
        print(f"  top {g['top_pct']:>3d}% (n={g['k']:>3d}): precision={g['precision']:.3f} "
              f"lift={g['lift']:.2f} caught={g['caught_errors']:>3d}/{total_err} "
              f"({g['caught_share']:.1%}) -> {g['errors_per_100_reviews']:.1f} errors per 100 reviews "
              f"(baseline {base*100:.1f})", flush=True)

    # 4) What would a reviewer be finding? (top-20% budget, the reviewer cut)
    cut20 = order[:int(round(n * 20 / 100))]
    caught = cut20[ty[cut20] == 1]
    caught_dir = tdir[caught]
    caught_amt = tamt[caught]
    over = int((caught_dir == 2).sum()); under = int((caught_dir == 3).sum())
    anatomy = {
        "reviewer_cut": "top 20%",
        "n_reviewed": int(len(cut20)),
        "n_caught_errors": int(len(caught)),
        "over": over, "under": under,
        "over_share": round(over / max(len(caught), 1), 3),
        "under_share": round(under / max(len(caught), 1), 3),
        "median_amterr": round(float(np.median(caught_amt)), 2),
        "mean_amterr": round(float(np.mean(caught_amt)), 2),
        "p10_amterr": round(float(np.percentile(caught_amt, 10)), 2),
        "p90_amterr": round(float(np.percentile(caught_amt, 90)), 2),
    }
    # holdout-wide error anatomy for comparison
    err = ty == 1
    anatomy["holdout_error_over_share"] = round(float((tdir[err] == 2).mean()), 3)
    anatomy["holdout_error_under_share"] = round(float((tdir[err] == 3).mean()), 3)
    anatomy["holdout_error_median_amterr"] = round(float(np.median(tamt[err])), 2)
    print("caught-error anatomy (top 20%):", json.dumps(anatomy, indent=2), flush=True)

    out = {
        "base_error_rate": round(base, 4),
        "n_holdout": n, "n_errors": total_err,
        "raw_auc_real_train": round(float(auc_cal), 4),
        "raw_auc_holdout": round(float(auc_hold_raw), 4),
        "calibrated_auc_holdout": round(float(auc_hold), 4),
        "calibration": {"chosen": name, "cv_brier": briers,
                        "fit_on": "real-PA train split (disjoint from holdout)",
                        "n_fit": len(cal_keys)},
        "gains": gains,
        "caught_anatomy": anatomy,
        "recipe": {"synth": args.pa_synth, "n": len(pa_synth), "seed": 7,
                   "gbm": "HistGradientBoostingClassifier(random_state=0), "
                          "no class_weight, 3-class, P(error)=1-P(correct)",
                   "holdout": str(args.holdout_json)},
    }
    print("\n" + json.dumps(out, indent=2))
    out_path = args.out_json or "/tmp/pa4out/pa4_results.json"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=2))
    print(f"results -> {out_path}")


if __name__ == "__main__":
    main()
