"""Exp 1 — calibration: how close are the synthetic marginals to the real FY2024
QC file? Compares finding mix, element-bucket mix, nature mix, cause mix,
and the dollar-error distribution. Iterate on src/synth until close.

Usage: python experiments/exp1_calibration.py [--n 20000] [--seed 7]
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth.codebook import cause_bucket, element_bucket  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QC = Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"


def real_marginals():
    finding = Counter()
    bucket = Counter()
    nature = Counter()
    cause = Counter()
    amterr = []
    n = 0
    with open(QC, newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            n += 1
            finding[row["STATUS"].strip()] += 1
            amterr.append(abs(float(row["AMTERR"] or 0)))
            for i in range(1, 10):
                e = row.get(f"ELEMENT{i}", "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                bucket[b] += 1
                ntr = row.get(f"NATURE{i}", "").strip()
                cau = row.get(f"AGENCY{i}", "").strip()
                if ntr:
                    nature[ntr] += 1
                if cau:
                    cause[cause_bucket(int(cau))] += 1
    return finding, bucket, nature, cause, amterr, n


def synth_marginals(path):
    finding = Counter()
    bucket = Counter()
    nature = Counter()
    cause = Counter()
    amterr = []
    n = 0
    with open(path) as fh:
        for line in fh:
            n += 1
            c = json.loads(line)
            finding[str(c["finding"])] += 1
            amterr.append(c["dollar_error"])
            for v in c["variances"]:
                bucket[v["element_bucket"]] += 1
                nature[str(v["nature"])] += 1
                cause[cause_bucket(v["cause"])] += 1
    return finding, bucket, nature, cause, amterr, n


def show(name, real_c, synth_c, real_n, synth_n, top=10):
    print(f"\n== {name} (share of cases/variances) ==")
    print(f"  {'category':<28}{'real':>8}{'synth':>8}{'ratio':>8}")
    keys = [k for k, _ in real_c.most_common(top)]
    for k in keys:
        r, s = real_c[k] / real_n, synth_c[k] / synth_n
        print(f"  {str(k):<28}{r:>8.3f}{s:>8.3f}{(s / r if r else 0):>8.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        synth_path = tf.name
    subprocess.run(
        [sys.executable, "-m", "synth.generate", "--n", str(args.n),
         "--seed", str(args.seed), "--dist", str(ROOT / "experiments/dist.json"),
         "--out", synth_path],
        cwd=ROOT / "src", check=True, capture_output=True,
    )

    rf, rb, rn, rc, ra, r_n = real_marginals()
    sf, sb, sn, sc, sa, s_n = synth_marginals(synth_path)

    show("finding (1=correct 2=over 3=under)", rf, sf, r_n, s_n, top=3)
    r_var, s_var = sum(rb.values()), sum(sb.values())
    show("element bucket", rb, sb, r_var, s_var, top=10)
    show("nature", rn, sn, r_var, s_var, top=10)
    show("cause bucket", rc, sc, r_var, s_var, top=6)

    print("\n== dollar error |AMTERR| ==")
    for label, arr in (("real", ra), ("synth", sa)):
        q = statistics.quantiles(sorted(arr), n=100)
        print(f"  {label:<6} mean={statistics.mean(arr):7.1f} "
              f"median={statistics.median(arr):6.1f} p90={q[89]:7.1f} "
              f"p99={q[98]:7.1f} max={max(arr):7.0f}")
    print("   ... conditional on error cases only:")
    for label, arr in (("real", [a for a in ra if a > 0]), ("synth", [a for a in sa if a > 0])):
        q = statistics.quantiles(sorted(arr), n=100)
        print(f"  {label:<6} mean={statistics.mean(arr):7.1f} "
              f"median={statistics.median(arr):6.1f} p90={q[89]:7.1f} "
              f"p99={q[98]:7.1f}")


if __name__ == "__main__":
    main()
