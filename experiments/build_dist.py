"""Build the empirical variance distribution from the real FY2024 QC file.

Output (experiments/dist.json):
  error_rate: share of cases with any error (STATUS 2/3)
  direction_given_error: {2: p_over, 3: p_under}
  bucket_probs: variance-level P(bucket), restricted to generator-supported buckets
  nature_given_bucket / cause_given_bucket: conditional categorical distributions

Usage: python experiments/build_dist.py
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth.codebook import element_bucket, cause_bucket  # noqa: E402
from synth.errors import SUPPORTED_BUCKETS  # noqa: E402

QC = Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
OUT = Path(__file__).resolve().parent / "dist.json"


def main():
    n_cases = 0
    n_err_cases = 0
    direction = Counter()
    bucket_counts = Counter()
    nature_given = defaultdict(Counter)
    cause_given = defaultdict(Counter)

    with open(QC, newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            n_cases += 1
            status = row["STATUS"].strip()
            if status in ("2", "3"):
                n_err_cases += 1
                direction[status] += 1
            for i in range(1, 10):
                e = row.get(f"ELEMENT{i}", "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                if b not in SUPPORTED_BUCKETS:
                    continue
                bucket_counts[b] += 1
                ntr = row.get(f"NATURE{i}", "").strip()
                cau = row.get(f"AGENCY{i}", "").strip()
                if ntr:
                    nature_given[b][int(ntr)] += 1
                if cau:
                    cause_given[b][cause_bucket(int(cau)) and int(cau)] += 1

    total_var = sum(bucket_counts.values())
    dist = {
        "error_rate": n_err_cases / n_cases,
        "direction_given_error": {k: v / n_err_cases for k, v in direction.items()},
        "bucket_probs": {b: c / total_var for b, c in bucket_counts.items()},
        "nature_given_bucket": {
            b: {str(k): v / sum(c.values()) for k, v in c.items()}
            for b, c in nature_given.items()
        },
        "cause_given_bucket": {
            b: {str(k): v / sum(c.values()) for k, v in c.items()}
            for b, c in cause_given.items()
        },
        "meta": {
            "n_cases": n_cases, "n_err_cases": n_err_cases,
            "n_variances_supported": total_var,
        },
    }
    with open(OUT, "w") as fh:
        json.dump(dist, fh, indent=1)
    print(json.dumps(dist["meta"], indent=1))
    print("bucket_probs:", json.dumps(dist["bucket_probs"], indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
