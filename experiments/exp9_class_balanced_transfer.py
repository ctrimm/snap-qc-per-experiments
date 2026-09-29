"""Exp 9 — class-balanced element transfer.

Exp 4 v3's surprise: the more faithful persistent generator LOWERED
element-bucket transfer accuracy 0.493 -> 0.442 (macroF1 0.276 -> 0.214)
because rare buckets (hhcomp F1 0.20 -> 0.032) are starved of training
examples. Verdict: calibration fidelity != transfer utility; classifiers
need class rebalancing.

This experiment removes starvation four ways and asks whether the
persistent generator's cleaner feature->bucket mapping then beats the old
retry-loop generator. Element task only (y_idx=3), v1 features (9 raw;
exp4 v3 confirmed v1 beats v2 for element). All configs: 20k synth,
seed 7, same real FY2024 test set (test set NEVER touched).

Configs:
  (a) persistent generator (default), unbalanced -- reproduces v3 reference
      (expect acc~0.442 / macroF1~0.214)
  (b) persistent generator + class_weight="balanced"
  (c) old retry-loop generator (--no-persistent-buckets) + class_weight="balanced"
  (d) persistent generator + explicit oversampling of rare buckets to
      uniform counts in the TRAINING set (resample with replacement)
Also, time permitting: (b) with v2 features.

KEY comparison: (b) vs (c) -- once starvation is removed by balancing,
does the persistent generator's cleaner feature->bucket mapping win?

Usage: python experiments/exp9_class_balanced_transfer.py [--n-synth 20000] [--seed 7]
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

BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]

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


def gen_synth(n, seed, persistent):
    tf = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    path = tf.name
    tf.close()
    cmd = [sys.executable, "-m", "synth.generate", "--n", str(n),
           "--seed", str(seed), "--dist", str(ROOT / "experiments/dist.json"),
           "--max-attempts", "12", "--out", path]
    if not persistent:
        cmd.append("--no-persistent-buckets")
    subprocess.run(cmd, cwd=ROOT / "src", check=True, capture_output=True)
    return path


def oversample_uniform(X, y, random_state=0):
    """Resample each present class (with replacement) up to the max
    class count, so rare buckets are no longer starved."""
    from sklearn.utils import resample
    from collections import Counter
    counts = Counter(y)
    target = max(counts.values())
    Xn, yn = [], []
    for cls in sorted(counts):
        idx = [i for i, v in enumerate(y) if v == cls]
        Xi = [X[i] for i in idx]
        ni = len(idx)
        if ni < target:
            Xi, yi = resample([Xi[i] for i in range(ni)], [cls] * ni,
                              replace=True, n_samples=target,
                              random_state=random_state)
        else:
            yi = [cls] * ni
        Xn.extend(Xi)
        yn.extend(yi)
    return Xn, yn


def evaluate(name, s_rows, r_rows, feats, class_weight=None, oversample=False):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score
    sX, sy = as_Xy(s_rows, feats, 3)
    rX, ry = as_Xy(r_rows, feats, 3)
    train_n = len(sX)
    if oversample:
        sX, sy = oversample_uniform(sX, sy)
    clf = HistGradientBoostingClassifier(random_state=0,
                                         class_weight=class_weight).fit(sX, sy)
    pred = clf.predict(rX)
    acc = accuracy_score(ry, pred)
    macro = f1_score(ry, pred, average="macro", zero_division=0)
    per = f1_score(ry, pred, labels=BUCKETS, average=None, zero_division=0)
    train_classes = sorted(set(sy))
    train_counts = {c: list(sy).count(c) for c in train_classes}
    print(f"{name}: acc={acc:.3f} macroF1={macro:.3f} "
          f"(train n={train_n}->{len(sy)}, classes={len(train_classes)})")
    for b, f in zip(BUCKETS, per):
        print(f"    F1 {b:10s} {f:.3f}")
    print(f"    train class counts: {train_counts}")
    return acc, macro, dict(zip(BUCKETS, per))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-synth", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    print("generating synth (persistent, seed 7)...", flush=True)
    persist_path = gen_synth(args.n_synth, args.seed, persistent=True)
    print("generating synth (retry-loop, seed 7)...", flush=True)
    retry_path = gen_synth(args.n_synth, args.seed, persistent=False)

    print("loading data...", flush=True)
    synth_persist = [r for r in load_synth(persist_path) if r[3]]
    synth_retry = [r for r in load_synth(retry_path) if r[3]]
    real = load_real()

    print("exp4 v3 reference (persistent, unbalanced, v1): acc=0.442 macroF1=0.214")
    print("per-bucket v3: earned 0.616, shelter 0.549, unearned 0.343, sua 0.090, "
          "medical 0.062, hhcomp 0.032, arithmetic 0.025, depcare 0.000")

    results = {}

    # (a) persistent, unbalanced — v3 reference reproduction
    keep = sorted({r[3] for r in synth_persist})
    r_rows = [r for r in real if r[3] in set(keep)]
    print(f"\n== (a) persistent + unbalanced [v1] (classes: {keep}) ==")
    results["a"] = evaluate("a", synth_persist, r_rows, V1)

    # (b) persistent + class_weight="balanced"
    print("\n== (b) persistent + class_weight=balanced [v1] ==")
    results["b"] = evaluate("b", synth_persist, r_rows, V1,
                            class_weight="balanced")

    # (c) old retry-loop generator + class_weight="balanced"
    synth_retry_sub = [r for r in synth_retry if r[3] in set(keep)]
    print("\n== (c) retry-loop + class_weight=balanced [v1] ==")
    results["c"] = evaluate("c", synth_retry_sub, r_rows, V1,
                            class_weight="balanced")

    # (d) persistent + explicit oversampling to uniform training counts
    print("\n== (d) persistent + oversample-to-uniform [v1] ==")
    results["d"] = evaluate("d", synth_persist, r_rows, V1, oversample=True)

    # secondary: (b) with v2 features
    print("\n== (b-v2) persistent + class_weight=balanced [v2] ==")
    results["b-v2"] = evaluate("b-v2", synth_persist, r_rows, V2,
                               class_weight="balanced")

    print("\n== summary ==")
    for k, (acc, macro, per) in results.items():
        print(f"  ({k}) acc={acc:.3f} macroF1={macro:.3f}")


if __name__ == "__main__":
    main()
