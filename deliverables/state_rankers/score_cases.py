"""Rank SNAP cases for QC review with a packaged state triage model.

Input: a CSV with QC public-use column names for the agency-side fields
(CERTHHSZ, RAWHSIZE, RAWGROSS, RAWNET, RAWERND, SHELDED, RENT, UTIL, SUA1,
FSMEDEXP, FSDEPDED, FSCSEXP, HOMEDED, RAWBEN; plus BENMAX, the case's maximum
allotment, for models whose card lists benefit_max), one row per case, plus any
ID column you want carried through. Missing numeric values count as 0.

Output: the same rows, ranked, with
  p_error            calibrated-enough probability the case has a payment error
  expected_dollars   expected error dollars (P(error) x E[$|error], calibrated
                     against actual dollars on held-out data; quote totals with
                     a +-15-20% band for one state's top-of-queue figure)
  rank, in_top_pct   queue position and the top-k% bucket it falls in

Usage:
  python3 score_cases.py --state PA --input cases.csv --output ranked.csv [--id-col CASE_ID]

Requires: numpy, scikit-learn (same major.minor as model_card.json), joblib.
"""
import argparse
import csv
from pathlib import Path

import joblib
import numpy as np

HERE = Path(__file__).resolve().parent
SUA_YES = {"3", "4", "5", "6", "7", "8"}


def fnum(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def agency_features(row):
    """Must match experiments/exp58_agency_rankers.py:agency_features."""
    gross, net, ernd = fnum(row.get("RAWGROSS")), fnum(row.get("RAWNET")), fnum(row.get("RAWERND"))
    earned = 5.0 * ernd
    unearned = max(gross - earned, 0.0)
    size = fnum(row.get("CERTHHSZ"))
    shelter = fnum(row.get("SHELDED"))
    return [size, fnum(row.get("RAWHSIZE")), gross, net, ernd, earned, unearned, shelter,
            fnum(row.get("RENT")), fnum(row.get("UTIL")),
            1.0 if (row.get("SUA1") or "").strip() in SUA_YES else 0.0,
            fnum(row.get("FSMEDEXP")), fnum(row.get("FSDEPDED")), fnum(row.get("FSCSEXP")),
            1.0 if (row.get("HOMEDED") or "").strip() == "1" else 0.0,
            fnum(row.get("RAWBEN")),
            gross / max(size, 1.0), earned / gross if gross > 0 else 0.0,
            shelter / gross if gross > 0 else shelter, net / gross if gross > 0 else 0.0]


def context_features(row):
    """Two extra inputs for models trained with state context (exp80): the case's maximum
    allotment (BENMAX) and the issued benefit as a share of it."""
    bm, rb = fnum(row.get("BENMAX")), fnum(row.get("RAWBEN"))
    return agency_features(row) + [bm, rb / bm if bm > 0 else 0.0]


def score(state, rows):
    m = joblib.load(HERE / state / "model.joblib")
    feat = context_features if len(m["features"]) > 20 else agency_features
    X = np.array([feat(r) for r in rows])
    p = m["classifier"].predict_proba(X)[:, 1]
    raw = p * np.clip(np.expm1(m["dollar_regressor"].predict(X)), 0, None)
    return p, m["dollar_calibrator"].predict(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, help="USPS code of a packaged model (any of the 53 folders here, e.g. PA, NY, WY)")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--id-col", default=None)
    args = ap.parse_args()
    rows = list(csv.DictReader(open(args.input, newline="")))
    p, exp_d = score(args.state, rows)
    order = np.argsort(-exp_d, kind="stable")
    n = len(rows)
    keep = [args.id_col] if args.id_col else list(rows[0].keys())
    with open(args.output, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(keep + ["p_error", "expected_dollars", "rank", "in_top_pct"])
        for rank, i in enumerate(order, 1):
            pct = next(t for t in (10, 20, 30, 50, 100) if rank <= n * t / 100)
            w.writerow([rows[i].get(c, "") for c in keep] +
                       [f"{p[i]:.3f}", f"{exp_d[i]:.2f}", rank, pct])
    k = max(1, int(round(n * 0.2)))
    print(f"scored {n} cases with the {args.state} model; top 20% ({k} cases) "
          f"expected error dollars ${exp_d[order[:k]].sum():,.0f}; wrote {args.output}")


if __name__ == "__main__":
    main()
