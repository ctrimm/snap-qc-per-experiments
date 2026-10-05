"""SD4 — Prioritization simulation: the SECOND DECISION POINT of the UT POC track.

Simulates a reviewer's workflow on the SHARED UT holdout (592 real UT
cases, seed 20260929, 75/25 stratified): train UT2's best RANKING arm exactly
per the recipe (UT-conditioned synthetic n=20k seed 7 + GBM WITHOUT
class_weight="balanced"), calibrate its P(error) (NOT hard classification — UT2
  showed
hard accuracy 0.654 < majority 0.743 while binary AUC 0.728 seed 7),
rank holdout cases by calibrated P(error), and report precision@k / lift /
errors-per-100-reviews vs random review order, plus what the caught errors
look like (over/under split, median dollars).

FEATURE SET (per UT7): UT7's leakage audit found issued_benefit (RAWBEN,
the post-decision issued amount) is a leakage feature with an immaterial
delta (+0.013 acc / -0.000 macroF1 on removal). SD4/SD5 use the CLEAN
8-feature set (drop issued_benefit) from the start, adopted by SD7 before
SD4 ran (runbook ordering for new states).

Reproduction (exact commands, from repo root):
  1) python3 -m src.synth.ut_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out /tmp/ut45out/ut_synth.jsonl
  2) python3 experiments/sd4_prioritization.py \\
        --ut-synth /tmp/ut45out/ut_synth.jsonl \\
        --qc-dir ../snap-qc-data/raw \\
        --holdout-json experiments/ut2_holdout_idx.json

Calibration design (documented choice):
  The synth-trained 3-class GBM is error-eager on real UT (UT2). We take
  raw P(error) = 1 - P(correct) = P(over) + P(under) from the frozen
  synth-trained GBM and recalibrate it on the real-UT TRAIN split (1,773
  rows, the complement of the shared holdout — disjoint from everything
  reported). Choice between isotonic and Platt (logistic) is made by
  5-fold stratified cross-validation Brier score on that real-train split;
  the winner is refit on the full train split and applied once to the
  holdout. This mirrors UT2's recommended next step ("threshold calibration
  on a real-UT validation slice").

Method notes:
  - Finding labels: 1 = correct, 2 = over-issuance, 3 = under-issuance.
  - Features: clean v1 (8 agency-view features), per NY7's verdict.
  - No model weights are written anywhere. Microdata is read-only.
  - AMTERR is used for dollar-error magnitudes among caught errors.
  - UT8 fairness context: UT1's generator offsets were fit on pooled
    FY2020-2024 UT microdata *including the holdout rows* (pooled marginals
    only, not test labels). UT8's pristine refit (not yet run when UT4 ran)
    will quantify the contamination premium; the numbers below are very
    slightly flattered, not pristine. SD4's caveat section will be updated
    with UT8's reference once available.
Requires: scikit-learn.
"""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Clean v1: SD7's 8-feature set (issued_benefit dropped as leakage).
CLEAN8 = ["hh_size", "earned", "unearned", "shelter", "sua",
          "medical_exp", "depcare", "senior_disabled"]

UT_STATE = "49"
SUA_YES = {"3", "4", "5", "6", "7", "8"}
SPLIT_SEED = 20260929
TEST_SIZE = 0.25
FY_FILES = [2020, 2021, 2022, 2023, 2024]
UT8_PRISTINE_REF_AUC = 0.723  # PROVISIONAL: UT2 seed-7 finding binary AUC, arm (a) balanced (v1 9-feat). Updated with UT8's pristine reference once UT8 runs.


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


def load_ut_real(qc_dir):
    """All UT rows. Key: (fy, ut-relative row idx) — same convention as
    sd2_ut_transfer.load_ut_real. Value: (features, finding, amterr, fsben)."""
    rows = {}
    for fy in FY_FILES:
        path = Path(qc_dir) / f"qcfy{fy}_csv" / f"qc_pub_fy{fy}.csv"
        if not path.exists():
            raise FileNotFoundError(f"no csv at {path}")
        with open(path, newline="") as fh:
            ut_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != UT_STATE:
                    continue
                rows[(fy, ut_idx)] = (
                    real_row_features(row),
                    int(row["STATUS"].strip()),
                    fnum(row.get("AMTERR", 0)),
                    fnum(row.get("FSBEN", 0)),
                )
                ut_idx += 1
    return rows


def load_synth(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            f = c["issued_facts"]
            rows.append(({
                "hh_size": float(f["hh_size"]), "earned": float(f["earned"]),
                "unearned": float(f["unearned"]),
                "shelter": float(f["shelter"]), "sua": float(f["sua"]),
                "medical_exp": float(f["medical_exp"]),
                "depcare": float(f["depcare"]),
                "senior_disabled": float(f["senior_disabled"]),
            }, int(c["finding"])))
    return rows


def as_Xy(rows):
    return [[r[0][k] for k in CLEAN8] for r in rows], [r[1] for r in rows]


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
    ap.add_argument("--ut-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json", required=True)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score, brier_score_loss
    import numpy as np

    print("loading real UT microdata...", flush=True)
    real = load_ut_real(args.qc_dir)
    print(f"  UT rows: {len(real)}", flush=True)

    hj = json.loads(Path(args.holdout_json).read_text())
    assert hj["split_seed"] == SPLIT_SEED and hj["test_size"] == TEST_SIZE
    holdout_keys = [tuple(k) for k in hj["holdout_keys"]]
    holdout_set = set(holdout_keys)
    train_keys = [k for k in sorted(real.keys()) if k not in holdout_set]
    print(f"  shared holdout: {len(holdout_keys)} test rows; "
          f"real-UT train pool (calibration): {len(train_keys)}", flush=True)

    print("loading UT synthetic (arm (a) of UT2: balanced, seed 7, n=20000)...", flush=True)
    ut_synth = load_synth(args.ut_synth)
    print(f"  synth rows: {len(ut_synth)}", flush=True)

    # 1) Retrain UT2's best RANKING arm per the recipe (clean 8 features).
    # UT2: class_weight='balanced' wins finding binary AUC 3/3 seeds
    # (0.724 vs 0.697 avg) — ranking is this stage's currency, so the
    # P(error) model uses balanced (documented deviation from NY4/SD4's
    # no-cw recipe, where no-cw won AUC too).
    print("training 3-class GBM (class_weight=balanced, random_state=0, clean 8)...", flush=True)
    sX, sy = as_Xy(ut_synth)
    clf = HistGradientBoostingClassifier(random_state=0, class_weight="balanced")
    clf.fit(sX, sy)

    # 2) Calibrate P(error) on the real-UT train split (disjoint from holdout).
    cal_keys = train_keys
    cX = np.array([[real[k][0][v] for v in CLEAN8] for k in cal_keys])
    cy = np.array([1 if real[k][1] != 1 else 0 for k in cal_keys])
    raw_cal = raw_p_error(clf, cX)
    auc_cal = roc_auc_score(cy, raw_cal)
    name, cal, briers = choose_calibrator(raw_cal, cy)
    cal_p = np.clip(np.asarray(cal.predict(raw_cal)), 1e-6, 1 - 1e-6)
    print(f"calibration on real-UT train split (n={len(cal_keys)}): "
          f"raw AUC={auc_cal:.4f}, CV Brier {briers}, chosen={name}, "
          f"in-sample Brier={brier_score_loss(cy, cal_p):.5f}", flush=True)

    # 3) Rank the holdout.
    tX = np.array([[real[k][0][v] for v in CLEAN8] for k in holdout_keys])
    ty = np.array([1 if real[k][1] != 1 else 0 for k in holdout_keys])
    tdir = np.array([real[k][1] for k in holdout_keys])   # 1/2/3
    tamt = np.array([real[k][2] for k in holdout_keys])   # AMTERR
    p_err = np.clip(np.asarray(cal.predict(raw_p_error(clf, tX))), 1e-6, 1 - 1e-6)

    auc_hold = roc_auc_score(ty, p_err)
    auc_hold_raw = roc_auc_score(ty, raw_p_error(clf, tX))
    print(f"holdout: n={len(ty)}, errors={int(ty.sum())}, "
          f"base error rate={ty.mean():.4f}, raw AUC={auc_hold_raw:.4f}, "
          f"calibrated AUC={auc_hold:.4f} (calibration is monotone: identical ranking)", flush=True)
    print(f"UT8 pristine reference (provisional: UT2 seed-7 AUC arm (a); UT7 clean-8 delta immaterial): {UT8_PRISTINE_REF_AUC}", flush=True)

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
        "ut8_pristine_reference_auc": UT8_PRISTINE_REF_AUC,
        "calibration": {"chosen": name, "cv_brier": briers,
                        "fit_on": "real-UT train split (disjoint from holdout)",
                        "n_fit": len(cal_keys)},
        "gains": gains,
        "caught_anatomy": anatomy,
        "recipe": {"synth": args.ut_synth, "n": len(ut_synth), "seed": 7,
                   "gbm": "HistGradientBoostingClassifier(random_state=0), "
                          "class_weight=balanced, 3-class, P(error)=1-P(correct)",
                   "features": "clean8 (no issued_benefit, per UT7)",
                   "holdout": str(args.holdout_json)},
    }
    print("\n" + json.dumps(out, indent=2))
    out_path = args.out_json or "/tmp/ut45out/ut4_results.json"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=2))
    print(f"results -> {out_path}")


if __name__ == "__main__":
    main()
