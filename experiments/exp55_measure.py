"""Exp 55 — calibration check: dist.json vs dist_reportable.json.

Generates n cases with each distribution (persistent pool, the exp52/exp43
recipe) and compares against real FY2024 QC on:
  finding mix (correct / over / under) and its L1,
  primary-variance nature and bucket mix vs real reportable variances
    (largest AMOUNT > 0 variance on error cases — the eval's rule),
  dollar error: share <= $56 and median among error cases,
  share of error cases with 2+ reportable variances.

Usage: python3 experiments/exp55_measure.py [--n 30000] [--seed 7] [--extra-args "..."]
"""
import argparse
import csv
import json
import statistics
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth.codebook import element_bucket  # noqa: E402
from synth.errors import SUPPORTED_BUCKETS  # noqa: E402

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"


def real_targets():
    fm, nat, buck, dollars, multi, nerr = Counter(), Counter(), Counter(), [], 0, 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            st = row["STATUS"].strip()
            if st not in ("1", "2", "3"):
                continue
            fm[st] += 1
            if st == "1":
                continue
            nerr += 1
            try:
                dollars.append(abs(float(row["AMTERR"] or 0)))
            except ValueError:
                pass
            rep = []
            for i in range(1, 10):
                e = (row.get(f"ELEMENT{i}") or "").strip()
                if not e:
                    continue
                try:
                    a = float(row.get(f"AMOUNT{i}") or 0)
                except ValueError:
                    a = 0.0
                if a > 0:
                    rep.append((a, element_bucket(int(e)), (row.get(f"NATURE{i}") or "").strip()))
            multi += len(rep) >= 2
            rep = [r for r in rep if r[1] in SUPPORTED_BUCKETS]
            if rep:
                _, b, n = max(rep)
                buck[b] += 1
                nat[n] += 1
    n = sum(fm.values())
    return {"finding": {k: fm[k] / n for k in "123"},
            "nature": {k: v / sum(nat.values()) for k, v in nat.items()},
            "bucket": {k: v / sum(buck.values()) for k, v in buck.items()},
            "le56": sum(d <= 56 for d in dollars) / len(dollars),
            "p50": statistics.median(dollars), "multi": multi / nerr}


def synth_stats(dist, n, seed, extra):
    tf = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    tf.close()
    cmd = [sys.executable, "-m", "synth.generate", "--n", str(n), "--seed", str(seed),
           "--dist", str(dist), "--max-attempts", "12", "--out", tf.name] + extra
    subprocess.run(cmd, cwd=ROOT / "src", check=True, capture_output=True)
    cases = [json.loads(l) for l in open(tf.name)]
    Path(tf.name).unlink()
    fm = Counter(str(c["finding"]) for c in cases)
    err = [c for c in cases if c["finding"] != 1 and c.get("variances")]
    nat = Counter(str(c["variances"][0]["nature"]) for c in err)
    buck = Counter(c["variances"][0]["element_bucket"] for c in err)
    dol = [c["dollar_error"] for c in cases if c["finding"] != 1]
    return {"finding": {k: fm[k] / len(cases) for k in "123"},
            "nature": {k: v / len(err) for k, v in nat.items()},
            "bucket": {k: v / len(err) for k, v in buck.items()},
            "le56": sum(d <= 56 for d in dol) / len(dol), "p50": statistics.median(dol),
            "multi": sum(len(c["variances"]) >= 2 for c in err) / len(err)}


def l1(a, b):
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dists", default="dist.json,dist_reportable.json")
    ap.add_argument("--extra-args", default="")
    args = ap.parse_args()
    real = real_targets()
    rows = {"real FY2024": real}
    for d in args.dists.split(","):
        rows[d] = synth_stats(ROOT / "experiments" / d, args.n, args.seed, args.extra_args.split())
    print(f"{'':22s}{'correct':>8s}{'over':>7s}{'under':>7s}{'findL1':>8s}{'nat97':>7s}{'natL1':>7s}{'buckL1':>8s}{'<=$56':>7s}{'p50':>6s}{'multi':>7s}")
    for k, r in rows.items():
        f = r["finding"]
        print(f"{k:22s}{f['1']:>8.3f}{f['2']:>7.3f}{f['3']:>7.3f}{l1(f, real['finding']):>8.3f}"
              f"{r['nature'].get('97', 0):>7.2f}{l1(r['nature'], real['nature']):>7.2f}"
              f"{l1(r['bucket'], real['bucket']):>8.2f}{r['le56']:>7.2f}{r['p50']:>6.0f}{r['multi']:>7.2f}")


if __name__ == "__main__":
    main()
