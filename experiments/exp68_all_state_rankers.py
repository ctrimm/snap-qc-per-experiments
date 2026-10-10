"""Exp 68 — the exp58 agency-side triage ranker for every state.

Same pipeline as exp58 (agency-side features, nested-CV untuned vs tuned,
time split FY2020-22 -> FY2023-24, holdout, exp57 isotonic dollar calibration,
refit on all rows and package) for all 53 jurisdictions in the QC files
(50 states, DC, Guam, Virgin Islands).

Holdouts: the six POC states keep their existing holdout files (so their
numbers match exp58). Every other jurisdiction gets a fixed 25% holdout,
stratified by error status, seed 68 + state code, saved to
exp68_holdouts.json before any model is fit.

Packages go to deliverables/state_rankers/<USPS>/ (model.joblib,
model_card.json); results to exp68_results.json. Runs states in parallel
(--workers, each with OMP_NUM_THREADS threads).

Usage: python3 experiments/exp68_all_state_rankers.py [--workers 8] [--states NY,PA] [--package]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]

USPS = {1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT", 10: "DE", 11: "DC", 12: "FL", 13: "GA",
        15: "HI", 16: "ID", 17: "IL", 18: "IN", 19: "IA", 20: "KS", 21: "KY", 22: "LA", 23: "ME", 24: "MD",
        25: "MA", 26: "MI", 27: "MN", 28: "MS", 29: "MO", 30: "MT", 31: "NE", 32: "NV", 33: "NH", 34: "NJ",
        35: "NM", 36: "NY", 37: "NC", 38: "ND", 39: "OH", 40: "OK", 41: "OR", 42: "PA", 44: "RI", 45: "SC",
        46: "SD", 47: "TN", 48: "TX", 49: "UT", 50: "VT", 51: "VA", 53: "WA", 54: "WV", 55: "WI", 56: "WY",
        66: "GU", 78: "VI"}
HOLDOUTS = ROOT / "experiments" / "exp68_holdouts.json"


def make_holdouts(qc_dir):
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    poc = {E56.STATES[s][0]: s for s in E56.STATES}
    out = {}
    for code, ab in USPS.items():
        c = str(code)
        if c in poc:
            hf = E56.STATES[poc[c]][1]
            out[ab] = {"code": c, "source": hf,
                       "keys": json.loads((ROOT / "experiments" / hf).read_text())["holdout_keys"]}
            continue
        real = E58.load_state(qc_dir, c)
        keys = sorted(real)
        rng = np.random.RandomState(68 + code)
        hold = []
        for err in (True, False):
            grp = [k for k in keys if (real[k][1] != "1") == err]
            rng.shuffle(grp)
            hold += grp[: int(round(0.25 * len(grp)))]
        out[ab] = {"code": c, "source": "exp68 stratified 25%, seed 68+code", "keys": sorted(map(list, hold))}
    HOLDOUTS.write_text(json.dumps(out))
    return out


def run_one(job):
    ab, code, hold_keys, qc_dir, n_search, package = job
    os.environ.setdefault("OMP_NUM_THREADS", "3")
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    from sklearn.model_selection import StratifiedKFold
    real = E58.load_state(qc_dir, code)
    hold = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(real) if k not in hold]
    te = [k for k in sorted(real) if k in hold]
    X, y, a = E58.arrays(real, tr)
    Xh, yh, ah = E58.arrays(real, te)
    D = E56.DEFAULT
    cv = {"untuned": 0.0, "tuned": 0.0}
    for i, (p, q) in enumerate(StratifiedKFold(5, shuffle=True, random_state=56).split(X, y)):
        f, _ = E56.fit_two_part(X[p], y[p], a[p], D, D)
        cv["untuned"] += E56.dollars_at(f(X[q]), a[q], 0.20)
        cc, cr, _ = E56.search(X[p], y[p], a[p], n_search, seed=100 + i)
        f, _ = E56.fit_two_part(X[p], y[p], a[p], cc, cr)
        cv["tuned"] += E56.dollars_at(f(X[q]), a[q], 0.20)
    rand = float(a.sum()) * 0.20
    early = np.array([k[0] <= 2022 for k in tr]); late = ~early
    cct, crt, _ = E56.search(X[early], y[early], a[early], n_search, seed=300)
    ts = {}
    for name, (c1, c2) in {"untuned": (D, D), "tuned": (cct, crt)}.items():
        f, _ = E56.fit_two_part(X[early], y[early], a[early], c1, c2)
        ts[name] = E56.dollars_at(f(X[late]), a[late], 0.20) / max(float(a[late].sum()) * 0.20, 1.0)
    use_tuned = cv["tuned"] > cv["untuned"]
    cc, cr = (E56.search(X, y, a, n_search, seed=400)[:2]) if use_tuned else (D, D)
    f, _ = E56.fit_two_part(X, y, a, cc, cr)
    iso = E58.dollar_calibrator(X, y, a, cc, cr)
    raw = f(Xh); cal = iso.predict(raw)
    hold_res = {}
    for frac in (0.10, 0.20, 0.30):
        k = int(round(len(raw) * frac)); idx = np.argsort(-raw, kind="stable")[:k]
        rec = float(ah[idx].sum())
        hold_res[f"top{int(frac * 100)}"] = {
            "lift": round(rec / max(float(ah.sum()) * frac, 1.0), 3),
            "per_hour_$": round(rec / (k * E56.REVIEW_MIN / 60), 1),
            "random_per_hour_$": round(float(ah.sum()) * frac / (k * E56.REVIEW_MIN / 60), 1),
            "expected_over_actual": round(float(cal[idx].sum()) / max(rec, 1.0), 3)}
    ev = {"state": ab, "state_code": code, "n_rows": len(real), "n_train": len(tr), "n_holdout": len(te),
          "n_errors_train": int(y.sum()), "error_rate": round(float(np.mean([real[k][1] != "1" for k in real])), 3),
          "nested_cv_top20_lift": {k: round(v / rand, 3) for k, v in cv.items()},
          "time_split_top20_lift": {k: round(v, 3) for k, v in ts.items()},
          "chosen": "tuned" if use_tuned else "untuned", "cfg": {"clf": cc, "reg": cr}, "holdout": hold_res,
          "low_sample": len(real) < 1500}
    if package:
        E56.STATES.setdefault(ab, (code, None, None, None))  # E58.package reads the code from here
        E58.package(ab, qc_dir, ev)
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-dir", default=str(ROOT.parent / "snap-qc-data/raw"))
    ap.add_argument("--states", default=None, help="comma-separated USPS codes (default: all 53)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-search", type=int, default=30)
    ap.add_argument("--package", action="store_true")
    args = ap.parse_args()
    hold = json.loads(HOLDOUTS.read_text()) if HOLDOUTS.exists() else make_holdouts(args.qc_dir)
    todo = args.states.split(",") if args.states else list(hold)
    out_path = ROOT / "experiments" / "exp68_results.json"
    done = {r["state"]: r for r in json.loads(out_path.read_text())} if out_path.exists() else {}
    jobs = [(ab, hold[ab]["code"], hold[ab]["keys"], args.qc_dir, args.n_search, args.package)
            for ab in todo if ab not in done]
    print(f"{len(jobs)} jurisdictions to run ({len(done)} already done), {args.workers} workers", flush=True)
    os.environ["OMP_NUM_THREADS"] = os.environ.get("OMP_NUM_THREADS", "3")  # inherited by spawned workers
    from multiprocessing import get_context
    with get_context("spawn").Pool(args.workers) as pool:
        for ev in pool.imap_unordered(run_one, jobs):
            done[ev["state"]] = ev
            h = ev["holdout"]["top20"]
            print(f"{ev['state']}: n={ev['n_rows']} holdout top20 {h['lift']:.2f}x (${h['per_hour_$']:.0f}/hr vs "
                  f"${h['random_per_hour_$']:.0f}) exp/act {h['expected_over_actual']:.2f} | nestedCV "
                  f"{max(ev['nested_cv_top20_lift'].values()):.2f}x | time split {ev['time_split_top20_lift'][ev['chosen']]:.2f}x"
                  f"{' | LOW SAMPLE' if ev['low_sample'] else ''}", flush=True)
            out_path.write_text(json.dumps(sorted(done.values(), key=lambda r: r["state"]), indent=1, default=float))


if __name__ == "__main__":
    main()
