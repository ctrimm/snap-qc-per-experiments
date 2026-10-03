"""Exp 4 — transfer v2: richer shared features.

Exp 2's residual: synth->real element-bucket accuracy 0.422 vs 0.614
real->real — how much of the gap is features vs generator fidelity? This
reruns transfer on the exp6 generator with an enriched shared feature set,
ablating v1 (original 9) vs v2 (19 features), to isolate the feature
contribution. Generator contribution is read off exp2 (0.422, old generator
+ v1) vs this run's v1 number (new generator + v1).

v2 adds, all computable in both worlds from agency-view facts:
  gross/net income, gap to max allotment, benefit as fraction of max,
  review month, elderly/disabled counts, earned/unearned indicators,
  earned share of gross.

Usage: python experiments/exp4_transfer_v2.py [--n-synth 20000] [--seed 7]
Requires: scikit-learn
"""
import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QC = Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]
V2_EXTRA = ["gross", "net", "gap_to_max", "benefit_frac", "review_month",
            "n_elderly", "n_disabled", "has_earned", "has_unearned", "earned_share"]
V2 = V1 + V2_EXTRA

SUA_YES = {"3", "4", "5", "6", "7", "8"}


def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def real_row_features(row):
    size = int(fnum(row["CERTHHSZ"]))
    earned = fnum(row["FSEARN"])
    unearned = fnum(row["FSUNEARN"])
    gross = fnum(row["FSGRINC"])
    net = fnum(row["FSNETINC"])
    issued = fnum(row["RAWBEN"])
    mallot = params.max_allotment(size)
    return {
        "hh_size": float(size), "earned": earned, "unearned": unearned,
        "shelter": fnum(row["SHELDED"]),
        "sua": 1.0 if row["SUA1"].strip() in SUA_YES else 0.0,
        "medical_exp": fnum(row["FSMEDEXP"]), "depcare": fnum(row["FSDEPDED"]),
        "senior_disabled": 1.0 if (fnum(row["FSNELDER"]) > 0 or fnum(row["FSNDIS"]) > 0) else 0.0,
        "issued_benefit": issued,
        "gross": gross, "net": net,
        "gap_to_max": mallot - issued,
        "benefit_frac": issued / mallot if mallot else 0.0,
        "review_month": float(row["YRMONTH"].strip()[-2:]),
        "n_elderly": fnum(row["FSNELDER"]), "n_disabled": fnum(row["FSNDIS"]),
        "has_earned": 1.0 if earned > 0 else 0.0,
        "has_unearned": 1.0 if unearned > 0 else 0.0,
        "earned_share": earned / gross if gross > 0 else 0.0,
    }


def synth_case_features(case):
    f = case["issued_facts"]  # agency-view facts, like the caseworker saw
    calc = benefit_mod.compute(f)
    size = f["hh_size"]
    mallot = params.max_allotment(size)
    issued = float(case["issued_benefit"])
    gross = calc["gross"]
    return {
        "hh_size": float(size), "earned": f["earned"], "unearned": f["unearned"],
        "shelter": f["shelter"], "sua": float(f["sua"]),
        "medical_exp": f["medical_exp"], "depcare": f["depcare"],
        "senior_disabled": float(f["senior_disabled"]),
        "issued_benefit": issued,
        "gross": gross, "net": calc["net"],
        "gap_to_max": mallot - issued,
        "benefit_frac": issued / mallot if mallot else 0.0,
        "review_month": float(f["review_month"]),
        "n_elderly": float(f["n_elderly"]), "n_disabled": float(f["n_disabled"]),
        "has_earned": 1.0 if f["earned"] > 0 else 0.0,
        "has_unearned": 1.0 if f["unearned"] > 0 else 0.0,
        "earned_share": f["earned"] / gross if gross > 0 else 0.0,
    }


def load_real():
    rows = []
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            status = row["STATUS"].strip()
            e1 = row.get("ELEMENT1", "").strip()
            rows.append((real_row_features(row),
                         0 if status == "1" else 1,
                         int(status),
                         element_bucket(int(e1)) if e1 and status != "1" else None))
    return rows


def load_synth(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            rows.append((synth_case_features(c),
                         0 if c["finding"] == 1 else 1,
                         c["finding"],
                         c["variances"][0]["element_bucket"] if c["variances"] else None))
    return rows


def as_Xy(rows, feats, y_idx):
    X = [[r[0][k] for k in feats] for r in rows]
    y = [r[y_idx] for r in rows]
    return X, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-synth", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.dummy import DummyClassifier
    from sklearn.model_selection import cross_val_predict, StratifiedKFold
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        synth_path = tf.name
    subprocess.run(
        [sys.executable, "-m", "synth.generate", "--n", str(args.n_synth),
         "--seed", str(args.seed), "--dist", str(ROOT / "experiments/dist.json"),
         "--max-attempts", "12", "--out", synth_path],
        cwd=ROOT / "src", check=True, capture_output=True,
    )

    print("loading data...", flush=True)
    synth = load_synth(synth_path)
    real = load_real()

    tasks = {
        "binary error vs correct": 1,
        "finding 1/2/3": 2,
        "element bucket | error": 3,
    }
    print("exp2 reference (old generator + v1): binary AUC=0.656 macroF1=0.567; "
          "finding acc=0.510 macroF1=0.366; element acc=0.422 macroF1=0.264; "
          "real->real element acc=0.614")

    for name, y_idx in tasks.items():
        if y_idx == 3:
            keep = {r[3] for r in synth if r[3]}
            s_rows = [r for r in synth if r[3] in keep]
            r_rows = [r for r in real if r[3] in keep]
        else:
            s_rows, r_rows = synth, real
        print(f"\n== {name} ==")
        for feats, tag in ((V1, "v1 (9 feats)"), (V2, "v2 (19 feats)")):
            sX, sy = as_Xy(s_rows, feats, y_idx)
            rX, ry = as_Xy(r_rows, feats, y_idx)
            clf = HistGradientBoostingClassifier(random_state=0).fit(sX, sy)
            pred = clf.predict(rX)
            line = (f"  synth->real [{tag}]: acc={accuracy_score(ry, pred):.3f} "
                    f"macroF1={f1_score(ry, pred, average='macro', zero_division=0):.3f}")
            if len(set(ry)) == 2:
                line += f" AUC={roc_auc_score(ry, clf.predict_proba(rX)[:, 1]):.3f}"
            print(line)
        # upper bound with v2, and dummy floor
        rX, ry = as_Xy(r_rows, V2, y_idx)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
        pred_r = cross_val_predict(HistGradientBoostingClassifier(random_state=0),
                                   rX, ry, cv=cv)
        print(f"  real->real 5fold [v2]: acc={accuracy_score(ry, pred_r):.3f} "
              f"macroF1={f1_score(ry, pred_r, average='macro', zero_division=0):.3f}")
        sX, sy = as_Xy(s_rows, V2, y_idx)
        dummy = DummyClassifier(strategy="most_frequent").fit(sX, sy)
        pred_d = dummy.predict(rX)
        print(f"  dummy [v2]: acc={accuracy_score(ry, pred_d):.3f} "
              f"macroF1={f1_score(ry, pred_d, average='macro', zero_division=0):.3f}")


if __name__ == "__main__":
    main()
