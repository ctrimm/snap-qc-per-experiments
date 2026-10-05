"""Exp 2 — transfer: does a model trained ONLY on synthetic cases predict
real QC findings? This is the core thesis test for synthetic pretraining data.

Features are computable from both worlds (agency-view facts + issued benefit).
Targets: (a) binary error vs correct, (b) 3-class finding, (c) element bucket
given error.

Compares train-on-synthetic -> test-on-real against train-on-real (upper
bound, 5-fold CV) and a dummy majority baseline.

Usage: python experiments/exp2_transfer.py [--n-synth 20000] [--seed 7]
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
from synth.codebook import element_bucket  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

FEATURES = ["hh_size", "earned", "unearned", "shelter", "sua",
            "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

SUA_YES = {"3", "4", "5", "6", "7", "8"}


def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def load_real():
    X, y_bin, y_find, y_elem = [], [], [], []
    with open(QC, newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            x = [
                fnum(row["CERTHHSZ"]), fnum(row["FSEARN"]), fnum(row["FSUNEARN"]),
                fnum(row["SHELDED"]), 1.0 if row["SUA1"].strip() in SUA_YES else 0.0,
                fnum(row["FSMEDEXP"]), fnum(row["FSDEPDED"]),
                1.0 if (fnum(row["FSNELDER"]) > 0 or fnum(row["FSNDIS"]) > 0) else 0.0,
                fnum(row["RAWBEN"]),
            ]
            status = row["STATUS"].strip()
            X.append(x)
            y_bin.append(0 if status == "1" else 1)
            y_find.append(int(status))
            e1 = row.get("ELEMENT1", "").strip()
            y_elem.append(element_bucket(int(e1)) if e1 and status != "1" else None)
    return X, y_bin, y_find, y_elem


def load_synth(path):
    X, y_bin, y_find, y_elem = [], [], [], []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            f = c["issued_facts"]  # agency-view facts, like the caseworker saw
            X.append([f["hh_size"], f["earned"], f["unearned"], f["shelter"],
                      float(f["sua"]), f["medical_exp"], f["depcare"],
                      float(f["senior_disabled"]), float(c["issued_benefit"])])
            y_bin.append(0 if c["finding"] == 1 else 1)
            y_find.append(c["finding"])
            y_elem.append(c["variances"][0]["element_bucket"] if c["variances"] else None)
    return X, y_bin, y_find, y_elem


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
         "--out", synth_path],
        cwd=ROOT / "src", check=True, capture_output=True,
    )

    print("loading data...", flush=True)
    sX, s_bin, s_find, s_elem = load_synth(synth_path)
    rX, r_bin, r_find, r_elem = load_real()

    tasks = {
        "binary error vs correct": (s_bin, r_bin, r_bin),
        "finding 1/2/3": (s_find, r_find, r_find),
    }
    # element bucket given error: restrict to buckets the generator covers
    keep = [b for b in set(s_elem) if b]
    sXe = [x for x, e in zip(sX, s_elem) if e in keep]
    s_ee = [e for e in s_elem if e in keep]
    rXe = [x for x, e in zip(rX, r_elem) if e in keep]
    r_ee = [e for e in r_elem if e in keep]
    tasks["element bucket | error"] = (s_ee, r_ee, r_ee)
    task_X = {"binary error vs correct": (sX, rX),
              "finding 1/2/3": (sX, rX),
              "element bucket | error": (sXe, rXe)}

    for name, (s_y, r_y, _) in tasks.items():
        s_X, r_X = task_X[name]
        print(f"\n== {name} ==")
        # transfer: train on synthetic, test on real
        clf = HistGradientBoostingClassifier(random_state=0)
        clf.fit(s_X, s_y)
        pred = clf.predict(r_X)
        acc = accuracy_score(r_y, pred)
        f1 = f1_score(r_y, pred, average="macro", zero_division=0)
        line = f"  synth->real: acc={acc:.3f} macroF1={f1:.3f}"
        if len(set(r_y)) == 2:
            line += f" AUC={roc_auc_score(r_y, clf.predict_proba(r_X)[:, 1]):.3f}"
        print(line)
        # upper bound: train on real (5-fold CV)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
        pred_r = cross_val_predict(HistGradientBoostingClassifier(random_state=0),
                                   r_X, r_y, cv=cv)
        f1r = f1_score(r_y, pred_r, average="macro", zero_division=0)
        print(f"  real->real (5fold CV): acc={accuracy_score(r_y, pred_r):.3f} "
              f"macroF1={f1r:.3f}")
        # floor: dummy
        dummy = DummyClassifier(strategy="most_frequent").fit(s_X, s_y)
        pred_d = dummy.predict(r_X)
        print(f"  dummy: acc={accuracy_score(r_y, pred_d):.3f} "
              f"macroF1={f1_score(r_y, pred_d, average='macro', zero_division=0):.3f}")


if __name__ == "__main__":
    main()
