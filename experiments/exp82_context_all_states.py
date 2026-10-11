"""Exp 82 — context-aware pooled models for every other jurisdiction.

exp80: pooling with state-context features (BENMAX, RAWBEN/BENMAX) beat the
deployed model on both readouts in all 12 small jurisdictions. Does it also
help the 41 larger ones, which currently use their own cases only (exp68)?

Pre-registered (this docstring, committed before running):
  Targets: the 41 jurisdictions not in exp80. Variants and readouts exactly
  as exp80 (B_ctx pooled, C_ctx pooled with own rows x10; default
  configuration; exp68 holdout top-20% lift and FY2020-22 -> FY2023-24
  time split). Comparison: the deployed exp68 model on the same readouts
  (its exp68 holdout lift; its time split recomputed here with its own
  exp68 configuration, as exp75 did for variant A).
  Adoption: a context variant replaces the deployed model only if it beats
  it on both readouts (both qualify: the higher holdout lift).
  Packaging of adopted models as exp80.

Usage: python3 experiments/exp82_context_all_states.py [--workers 8] [--package]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
_G = {}


def init():
    import exp80_state_context as X80
    _G["data"] = X80.load_all(str(ROOT.parent / "snap-qc-data/raw"))


def run_one(job):
    ab, code, hold_keys, cfg = job
    import exp56_pa_tuned_classifier as E56
    import exp58_agency_rankers as E58
    from exp75_small_state_pooling import fit_w, lift
    data = _G["data"]; own = data[code]
    ho = {tuple(k) for k in hold_keys}
    tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
    X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
    late = [k for k in sorted(own) if k[0] >= 2023]; Xl, yl, al = E58.arrays(own, late)
    e = np.array([k[0] <= 2022 for k in tr])
    nb = len(E58.FEATURES)  # deployed model uses the agency-side features only
    fA = fit_w(X[:, :nb], y, a, np.ones(len(y)), cfg["clf"], cfg["reg"])
    fA2 = fit_w(X[e][:, :nb], y[e], a[e], np.ones(e.sum()), cfg["clf"], cfg["reg"])
    res = {"deployed": {"holdout": round(lift(fA(Xh[:, :nb]), ah), 3), "time_split": round(lift(fA2(Xl[:, :nb]), al), 3)}}
    others = [(c, k) for c in data if c != code for k in data[c]]
    Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
    ao = np.array([data[c][k][2] for c, k in others]); eo = np.array([k[0] <= 2022 for c, k in others])
    D = E56.DEFAULT
    for name, wown in (("B_ctx", 1.0), ("C_ctx", 10.0)):
        f = fit_w(np.vstack([X, Xo]), np.concatenate([y, yo]), np.concatenate([a, ao]),
                  np.concatenate([np.full(len(y), wown), np.ones(len(yo))]), D, D)
        f2 = fit_w(np.vstack([X[e], Xo[eo]]), np.concatenate([y[e], yo[eo]]), np.concatenate([a[e], ao[eo]]),
                   np.concatenate([np.full(e.sum(), wown), np.ones(eo.sum())]), D, D)
        res[name] = {"holdout": round(lift(f(Xh), ah), 3), "time_split": round(lift(f2(Xl), al), 3)}
    dep = res["deployed"]
    ok = [v for v in ("B_ctx", "C_ctx") if res[v]["holdout"] > dep["holdout"] and res[v]["time_split"] > dep["time_split"]]
    res["adopted"] = max(ok, key=lambda v: res[v]["holdout"]) if ok else "keep"
    res["state"] = ab; res["n_rows"] = len(own)
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8); ap.add_argument("--package", action="store_true")
    args = ap.parse_args()
    if args.package:
        import exp80_state_context as X80
        X80_res = ROOT / "experiments/exp80_results.json"
        saved = X80_res.read_text()
        try:  # reuse exp80's packager on exp82's adopted list
            r82 = json.loads((ROOT / "experiments/exp82_results.json").read_text())
            X80_res.write_text(json.dumps({k: v for k, v in r82.items() if v["adopted"] != "keep"}))
            X80.package_adopted()
        finally:
            X80_res.write_text(saved)
        return
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    r80 = json.loads((ROOT / "experiments/exp80_results.json").read_text())
    cfg = {r["state"]: r["cfg"] for r in json.loads((ROOT / "experiments/exp68_results.json").read_text())}
    jobs = [(ab, h["code"], h["keys"], cfg[ab]) for ab, h in hold.items() if ab not in r80]
    os.environ["OMP_NUM_THREADS"] = "3"
    from multiprocessing import get_context
    out = {}
    with get_context("spawn").Pool(args.workers, initializer=init) as pool:
        for r in pool.imap_unordered(run_one, jobs):
            out[r["state"]] = r
            d = r["deployed"]
            print(f"{r['state']}: deployed {d['holdout']:.2f}x / {d['time_split']:.2f}x | B_ctx {r['B_ctx']['holdout']:.2f}x / "
                  f"{r['B_ctx']['time_split']:.2f}x | C_ctx {r['C_ctx']['holdout']:.2f}x / {r['C_ctx']['time_split']:.2f}x | {r['adopted']}",
                  flush=True)
            (ROOT / "experiments/exp82_results.json").write_text(json.dumps(dict(sorted(out.items())), indent=1))
    n = sum(r["adopted"] != "keep" for r in out.values())
    print(f"adopted in {n} of {len(out)}")


if __name__ == "__main__":
    main()
