"""Exp 79 — an underpayment-focused ranker, all 53 jurisdictions.

The triage ranker targets total error dollars, which are mostly overpayments
(national FY2025: 9.28% over vs 1.33% under). A state that wants to find
households being shorted could rank by expected underpayment instead.

Pre-registered (this docstring, committed before running):
  Per jurisdiction, exp68 holdout. Two rankers, agency-side features:
    total   the exp68 two-part ranker with its exp68 configuration
    under   two-part P(underpayment) x E[$ | underpayment] (STATUS 3 cases'
            AMTERR as the dollars), default configuration
  Readouts on the holdout, top 20%: (1) share of the holdout's underpayment
  dollars found, as lift over random, for each ranker; (2) total-error
  dollars lift for each (the cost of switching). Report the 53-jurisdiction
  median and how many jurisdictions the under ranker beats the total ranker
  on underpayment dollars.

Usage: python3 experiments/exp79_underpayment_ranker.py [--workers 8]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]


def run_one(job):
    ab, code, hold_keys, cfg, qc_dir = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    real = E58.load_state(qc_dir, code)
    hold = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(real) if k not in hold]; te = [k for k in sorted(real) if k in hold]
    X, y, a = E58.arrays(real, tr); Xh, yh, ah = E58.arrays(real, te)
    yu = np.array([real[k][1] == "3" for k in tr], int); au = np.where(yu == 1, a, 0.0)
    yhu = np.array([real[k][1] == "3" for k in te], int); ahu = np.where(yhu == 1, ah, 0.0)
    f_tot, _ = E56.fit_two_part(X, y, a, cfg["clf"], cfg["reg"])
    res = {"state": ab, "under_share_of_error_dollars": round(float(ahu.sum() / max(ah.sum(), 1)), 3)}
    if yu.sum() < 20 or (au > 0).sum() < 10:
        res["skipped"] = "too few underpayment cases"
        return res
    f_und, _ = E56.fit_two_part(X, yu, au, E56.DEFAULT, E56.DEFAULT)
    k = int(round(0.2 * len(te)))
    for name, f in (("total", f_tot), ("under", f_und)):
        idx = np.argsort(-f(Xh), kind="stable")[:k]
        res[name] = {"under_lift": round(float(ahu[idx].sum() / max(ahu.sum() * 0.2, 1e-9)), 3),
                     "total_lift": round(float(ah[idx].sum() / max(ah.sum() * 0.2, 1e-9)), 3)}
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8); args = ap.parse_args()
    qc_dir = str(ROOT.parent / "snap-qc-data/raw")
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    cfg = {r["state"]: r["cfg"] for r in json.loads((ROOT / "experiments/exp68_results.json").read_text())}
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    with get_context("spawn").Pool(args.workers) as pool:
        res = sorted(pool.map(run_one, [(ab, h["code"], h["keys"], cfg[ab], qc_dir) for ab, h in hold.items()]),
                     key=lambda r: r["state"])
    (ROOT / "experiments/exp79_results.json").write_text(json.dumps(res, indent=1))
    ok = [r for r in res if "skipped" not in r]
    med = lambda v: float(np.median(v))
    print(f"jurisdictions scored: {len(ok)} of {len(res)} (skipped: {[r['state'] for r in res if 'skipped' in r]})")
    print(f"underpayment dollars, top-20% lift: total ranker median {med([r['total']['under_lift'] for r in ok]):.2f}x | "
          f"under ranker median {med([r['under']['under_lift'] for r in ok]):.2f}x | under ranker better in "
          f"{sum(r['under']['under_lift'] > r['total']['under_lift'] for r in ok)} of {len(ok)}")
    print(f"total error dollars, top-20% lift: total ranker median {med([r['total']['total_lift'] for r in ok]):.2f}x | "
          f"under ranker median {med([r['under']['total_lift'] for r in ok]):.2f}x")
    print(f"underpayments' share of error dollars: median {med([r['under_share_of_error_dollars'] for r in res]):.0%}")


if __name__ == "__main__":
    main()
