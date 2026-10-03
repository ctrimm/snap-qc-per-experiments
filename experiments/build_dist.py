"""Build the empirical variance distribution from the real FY2024 QC file.

Output (experiments/dist.json):
  error_rate: share of cases with any error (STATUS 2/3)
  error_rate_given_earner / _given_no_earner: P(error | FSEARN>0 / =0).
    Real QC shows a steep earnings->error gradient (exp4 diagnosis); a flat
    injection coin flattens it in the synthetic frame.
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
    earner_n = earner_err = 0
    noearner_n = noearner_err = 0
    direction = Counter()
    bucket_counts = Counter()
    nature_given = defaultdict(Counter)
    cause_given = defaultdict(Counter)
    # Conditional on earner status (exp6 diagnosis: the bucket mix differs
    # sharply — earned is 53% of variances on earner cases, ~0% otherwise).
    bucket_earner = Counter()
    bucket_noearner = Counter()
    nature_earner = defaultdict(Counter)
    nature_noearner = defaultdict(Counter)
    # Direction of timing-nature (97) variances: 97 is direction-ambiguous
    # (earned-97 is 60% over, shelter-97 is 37% over). Measured on
    # single-variance cases for clean direction attribution.
    over_97 = Counter()
    tot_97 = Counter()

    with open(QC, newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            n_cases += 1
            status = row["STATUS"].strip()
            is_err = status in ("2", "3")
            if is_err:
                n_err_cases += 1
                direction[status] += 1
            try:
                earner = float(row["FSEARN"] or 0) > 0
            except ValueError:
                earner = False
            if earner:
                earner_n += 1
                earner_err += is_err
            else:
                noearner_n += 1
                noearner_err += is_err
            case_vars = []
            for i in range(1, 10):
                e = row.get(f"ELEMENT{i}", "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                if b not in SUPPORTED_BUCKETS:
                    continue
                bucket_counts[b] += 1
                (bucket_earner if earner else bucket_noearner)[b] += 1
                ntr = row.get(f"NATURE{i}", "").strip()
                cau = row.get(f"AGENCY{i}", "").strip()
                if ntr:
                    nature_given[b][int(ntr)] += 1
                    (nature_earner if earner else nature_noearner)[b][int(ntr)] += 1
                    case_vars.append((b, int(ntr)))
                if cau:
                    cause_given[b][cause_bucket(int(cau)) and int(cau)] += 1
            if len(case_vars) == 1 and case_vars[0][1] == 97 and is_err:
                b = case_vars[0][0]
                tot_97[b] += 1
                over_97[b] += (status == "2")

    total_var = sum(bucket_counts.values())
    dist = {
        "error_rate": n_err_cases / n_cases,
        "error_rate_given_earner": earner_err / earner_n,
        "error_rate_given_no_earner": noearner_err / noearner_n,
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
        "bucket_probs_given_earner": {
            b: c / sum(bucket_earner.values()) for b, c in bucket_earner.items()
        },
        "bucket_probs_given_no_earner": {
            b: c / sum(bucket_noearner.values()) for b, c in bucket_noearner.items()
        },
        "nature_given_bucket_earner": {
            b: {str(k): v / sum(c.values()) for k, v in c.items()}
            for b, c in nature_earner.items()
        },
        "nature_given_bucket_no_earner": {
            b: {str(k): v / sum(c.values()) for k, v in c.items()}
            for b, c in nature_noearner.items()
        },
        # P(over-issuance | bucket, nature=97), single-variance cases.
        # Buckets with <50 observations fall back to 0.5 at load time.
        "p_over_97_given_bucket": {
            b: over_97[b] / tot_97[b] for b in tot_97
        },
        "_n_97": {b: tot_97[b] for b in tot_97},
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
