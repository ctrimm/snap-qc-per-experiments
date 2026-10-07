"""Exp 55 — reportable-variance distribution for the generator.

dist.json (build_dist.py + exp11 strata) counts every recorded variance in the
FY2024 file. 52% of those carry AMOUNT = 0 (no dollar effect), and 59% of the
zero-amount ones are timing (nature 97), so the generator — which only records
variances that change the benefit — over-draws nature 97 (~47% of synthetic
primaries vs 19% of real reportable variances). The exp30 eval labels T3–T5
from the largest *reportable* variance, so synthetic labels drift from what
the eval scores (exp54).

This builds experiments/dist_reportable.json: a copy of dist.json whose
variance-level tables are recomputed from variances with AMOUNT > 0 on error
cases (STATUS 2/3):
  bucket_probs (+ _given_earner / _given_no_earner / the four exp11 strata),
  nature_given_bucket (+ _earner / _no_earner), cause_given_bucket,
  p_over_97_given_bucket (single-reportable-variance cases), _n_97.
Case-level rates (error_rate*, direction_given_error) are copied unchanged.
dist.json is not touched; generate.py --dist experiments/dist_reportable.json
opts in.

Usage: python3 experiments/exp55_build_dist_reportable.py
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
from synth.codebook import cause_bucket, element_bucket  # noqa: E402
from synth.errors import SUPPORTED_BUCKETS  # noqa: E402
from exp11_senior_bucket_mix import SSI_COLS  # noqa: E402

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
SRC = ROOT / "experiments" / "dist.json"
OUT = ROOT / "experiments" / "dist_reportable.json"


def norm(c):
    t = sum(c.values())
    return {str(k): v / t for k, v in c.items()} if t else {}


def main():
    bucket, b_earn, b_noearn = Counter(), Counter(), Counter()
    strata = defaultdict(Counter)
    nat, nat_e, nat_ne = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    cau = defaultdict(Counter)
    over_97, tot_97 = Counter(), Counter()
    n_var = n_all = 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            st = row["STATUS"].strip()
            earner = float(row["FSEARN"] or 0) > 0
            senior = int(row["FSNELDER"] or 0) > 0 or any(int(row[c] or 0) > 0 for c in SSI_COLS)
            skey = f"{'earner' if earner else 'no_earner'}_{'senior' if senior else 'nonsenior'}"
            rep = []
            for i in range(1, 10):
                e = (row.get(f"ELEMENT{i}") or "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                if b not in SUPPORTED_BUCKETS:
                    continue
                n_all += 1
                try:
                    amt = float(row.get(f"AMOUNT{i}") or 0)
                except ValueError:
                    amt = 0.0
                if st not in ("2", "3") or amt <= 0:
                    continue
                n_var += 1
                bucket[b] += 1
                (b_earn if earner else b_noearn)[b] += 1
                strata[skey][b] += 1
                ntr = (row.get(f"NATURE{i}") or "").strip()
                if ntr:
                    nat[b][int(ntr)] += 1
                    (nat_e if earner else nat_ne)[b][int(ntr)] += 1
                    rep.append((b, int(ntr)))
                c = (row.get(f"AGENCY{i}") or "").strip()
                if c:
                    cau[b][cause_bucket(int(c)) and int(c)] += 1
            if len(rep) == 1 and rep[0][1] == 97:
                tot_97[rep[0][0]] += 1
                over_97[rep[0][0]] += (st == "2")
    dist = json.loads(SRC.read_text())
    dist.update({
        "bucket_probs": {k: v for k, v in norm(bucket).items()},
        "bucket_probs_given_earner": norm(b_earn),
        "bucket_probs_given_no_earner": norm(b_noearn),
        "nature_given_bucket": {b: norm(c) for b, c in nat.items()},
        "nature_given_bucket_earner": {b: norm(c) for b, c in nat_e.items()},
        "nature_given_bucket_no_earner": {b: norm(c) for b, c in nat_ne.items()},
        "cause_given_bucket": {b: norm(c) for b, c in cau.items()},
        "p_over_97_given_bucket": {b: over_97[b] / tot_97[b] for b in tot_97},
        "_n_97": dict(tot_97),
    })
    for skey, c in strata.items():
        dist[f"bucket_probs_given_{skey}"] = norm(c)
    dist["meta"] = {**dist.get("meta", {}), "exp55_reportable_only": True,
                    "n_variances_all_supported": n_all, "n_variances_reportable": n_var}
    OUT.write_text(json.dumps(dist, indent=1))
    mix = Counter()
    for b, pb in dist["bucket_probs"].items():
        for k, p in dist["nature_given_bucket"].get(b, {}).items():
            mix[k] += pb * p
    print(f"reportable variances {n_var} of {n_all} ({n_var / n_all:.0%})")
    print("implied nature mix:", {k: round(v, 3) for k, v in sorted(mix.items(), key=lambda x: -x[1])[:8]})
    print("bucket_probs:", {k: round(v, 3) for k, v in sorted(dist["bucket_probs"].items(), key=lambda x: -x[1])})
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
