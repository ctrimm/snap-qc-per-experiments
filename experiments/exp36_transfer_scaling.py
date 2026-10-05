"""Exp 36 — transfer scaling curve: element-classifier transfer vs synthetic N.

North-star gate: TRANSFER. The LM pretraining corpus has to be sized on
something; this experiment measures where synth-trained GBM transfer
saturates, as the best available proxy for where LM pretraining would
stop helping.

Hypothesis: element transfer (accuracy / macroF1 on real FY2024 QC)
saturates at some synthetic volume N* -- beyond N*, doubling N buys
<0.005 macroF1 -- and that N* sizes the LM pretraining corpus.

Method (exp25's closed recipe, exactly):
- generator: faithful persistent default (no --no-persistent-buckets),
  --max-attempts 12, current in-flight defaults, SEED 7 for every N so
  the curve is not seed noise.
- training rows: error rows only (c["variances"] non-empty), element task,
  v1 features, HistGradientBoostingClassifier(random_state=0),
  class_weight="balanced".
- test split: same real FY2024 QC split as exp19/exp22/exp25 (test set is
  never touched; keep-buckets fixed from the N=20000 faithful pool).
- N grid: 2000, 5000, 10000, 20000, 40000.

Usage: python3 experiments/exp36_transfer_scaling.py [--ns "2000 5000 ..."] [--seed 7]
Requires: scikit-learn
"""
import argparse
import csv
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

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
        "n_elderly": fnum(row["FSNELDER"]), "n_disabled": float(fnum(row["FSNDIS"])),
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


def case_row(c):
    return (synth_case_features(c),
            0 if c["finding"] == 1 else 1,
            c["finding"],
            c["variances"][0]["element_bucket"] if c["variances"] else None)


def gen_synth(n, seed):
    tf = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    path = tf.name
    tf.close()
    cmd = [sys.executable, "-m", "synth.generate", "--n", str(n),
           "--seed", str(seed), "--dist", str(ROOT / "experiments/dist.json"),
           "--max-attempts", "12", "--out", path]
    subprocess.run(cmd, cwd=ROOT / "src", check=True, capture_output=True)
    return path


def evaluate(s_rows, r_rows, feats):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score
    sX = [[r[0][k] for k in feats] for r in s_rows]
    sy = [r[3] for r in s_rows]
    rX = [[r[0][k] for k in feats] for r in r_rows]
    ry = [r[3] for r in r_rows]
    clf = HistGradientBoostingClassifier(
        random_state=0, class_weight="balanced").fit(sX, sy)
    pred = clf.predict(rX)
    acc = accuracy_score(ry, pred)
    macro = f1_score(ry, pred, average="macro", zero_division=0)
    per = f1_score(ry, pred, labels=BUCKETS, average=None, zero_division=0)
    return acc, macro, dict(zip(BUCKETS, per))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", default="2000,5000,10000,20000,40000")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    ns = [int(x) for x in args.ns.split(",")]

    # reproducibility stamp (generator is in-flight work)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--short"], cwd=ROOT,
                            capture_output=True, text=True).stdout
    print(f"git HEAD: {head}")
    print(f"git status --short:\n{status}")

    print("loading real QC file...", flush=True)
    real = load_real()

    # generate all pools first (so keep-buckets can be fixed from the
    # reference 20k pool, exactly like exp25)
    import json
    pools = {}
    ref_n = 20000 if 20000 in ns else max(ns)
    for n in sorted(set(ns + [ref_n]), reverse=True):
        print(f"generating faithful persistent pool ({n}, seed "
              f"{args.seed})...", flush=True)
        path = gen_synth(n, args.seed)
        with open(path) as fh:
            cases = [json.loads(line) for line in fh]
        Path(path).unlink(missing_ok=True)
        pools[n] = cases[:n]
        err_rows = [case_row(c) for c in cases if c["variances"]]
        cnt = Counter(r[3] for r in err_rows)
        print(f"  n={n}: {len(err_rows)} error rows, classes={sorted(set(r[3] for r in err_rows))}")
        print(f"    class counts: {dict(cnt)}")
        if n == ref_n:
            keep = sorted(set(r[3] for r in err_rows))
            print(f"  keep-buckets (fixed for all N): {keep}")

    r_rows = [r for r in real if r[3] in set(keep)]
    print(f"real test rows: {len(r_rows)} (of {len(real)}) "
          f"(exp25 seed7 split: 17,318 rows)")

    results = {}
    for n in ns:
        err_rows = [case_row(c) for c in pools[n] if c["variances"]]
        acc, macro, per = evaluate(err_rows, r_rows, V1)
        results[n] = (acc, macro, per, len(err_rows))
        print(f"N={n:6d}: acc={acc:.3f} macroF1={macro:.3f} "
              f"(train rows={len(err_rows)})")

    print("\n== transfer scaling curve (element, v1, balanced, seed 7) ==")
    print("N        acc     macroF1   d(acc)    d(macroF1)")
    prev = None
    for n in ns:
        acc, macro, _, _ = results[n]
        da = "" if prev is None else f"{acc - prev[0]:+.4f}"
        dm = "" if prev is None else f"{macro - prev[1]:+.4f}"
        print(f"{n:6d}   {acc:.3f}   {macro:.3f}   {da:>7}   {dm:>7}")
        prev = (acc, macro)

    print("\n== per-bucket F1 vs N (rare buckets marked *) ==")
    rare = {"hhcomp", "depcare", "sua", "arithmetic", "medical"}
    print("bucket      " + "".join(f"  N={n:<6d}" for n in ns))
    for b in BUCKETS:
        mark = "*" if b in rare else " "
        print(f"{b:10s}{mark} " + "".join(f"  {results[n][2][b]:.3f}   " for n in ns))

    print("\n== saturation knee: smallest N where doubling N buys <0.005 ==")
    for i, n in enumerate(ns[:-1]):
        n2 = ns[i + 1]
        gain = results[n2][1] - results[n][1]
        flag = " <-- knee" if gain < 0.005 else ""
        print(f"  {n:6d} -> {n2:6d}: macroF1 gain {gain:+.4f}{flag}")


if __name__ == "__main__":
    main()
