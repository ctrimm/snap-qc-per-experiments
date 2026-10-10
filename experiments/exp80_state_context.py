"""Exp 80 — state-context features for pooled small-jurisdiction models.

exp75's pooled models helped five small jurisdictions but not Hawaii, Guam
or Alaska's later years, plausibly because their benefit levels differ from
the mainland's. The QC files carry each case's maximum allotment (BENMAX),
which differs by state, region and year.

Pre-registered (this docstring, committed before running):
  Features: exp58 agency-side features + BENMAX + RAWBEN / BENMAX (issued
  benefit as a share of the maximum).
  Targets and variants as exp75 (the 12 jurisdictions under 2,500 QC
  cases; B pooled, C pooled with own rows x10; default configuration), same
  holdouts and time split.
  Comparison: each target's currently deployed model (exp75's adopted variant,
  or own-only A) on the same two readouts.
  Adoption: a context variant replaces the deployed model only if it beats it
  on both the holdout lift and the time split (if both B and C qualify, the
  higher holdout lift). Adopted variants are repackaged (with the two extra
  inputs recorded in the model card and in score_cases.py).

Usage: OMP_NUM_THREADS=16 python3 experiments/exp80_state_context.py [--package]
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402
import exp58_agency_rankers as E58  # noqa: E402
from exp75_small_state_pooling import fit_w, lift  # noqa: E402

CONTEXT = ["benefit_max", "benefit_share_of_max"]


def context_features(row):
    bm = E58.fnum(row.get("BENMAX")); rb = E58.fnum(row.get("RAWBEN"))
    return E58.agency_features(row) + [bm, rb / bm if bm > 0 else 0.0]


def load_all(qc_dir):
    out = {}
    for fy in E58.FY_FILES:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")))
        idx = {}
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                c = row["STATE"].strip(); i = idx.get(c, 0); idx[c] = i + 1
                out.setdefault(c, {})[(fy, i)] = (context_features(row), row["STATUS"].strip(), E58.fnum(row["AMTERR"]))
    return out


def main():
    qc_dir = str(ROOT.parent / "snap-qc-data/raw")
    data = load_all(qc_dir)
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    r75 = json.loads((ROOT / "experiments/exp75_results.json").read_text())
    D = E56.DEFAULT
    out = {}
    for ab, prev in sorted(r75.items(), key=lambda kv: kv[1]["n_rows"]):
        dep = prev[prev["adopted"]]
        code = hold[ab]["code"]; own = data[code]
        ho = {tuple(k) for k in hold[ab]["keys"]}
        tr = [k for k in sorted(own) if k not in ho]; te = [k for k in sorted(own) if k in ho]
        X, y, a = E58.arrays(own, tr); Xh, yh, ah = E58.arrays(own, te)
        late = [k for k in sorted(own) if k[0] >= 2023]; Xl, yl, al = E58.arrays(own, late)
        e = np.array([k[0] <= 2022 for k in tr])
        others = [(c, k) for c in data if c != code for k in data[c]]
        Xo = np.array([data[c][k][0] for c, k in others]); yo = np.array([data[c][k][1] != "1" for c, k in others], int)
        ao = np.array([data[c][k][2] for c, k in others]); eo = np.array([k[0] <= 2022 for c, k in others])
        res = {"deployed": {"variant": prev["adopted"], **dep}}
        for name, wown in (("B_ctx", 1.0), ("C_ctx", 10.0)):
            f = fit_w(np.vstack([X, Xo]), np.concatenate([y, yo]), np.concatenate([a, ao]),
                      np.concatenate([np.full(len(y), wown), np.ones(len(yo))]), D, D)
            f2 = fit_w(np.vstack([X[e], Xo[eo]]), np.concatenate([y[e], yo[eo]]), np.concatenate([a[e], ao[eo]]),
                       np.concatenate([np.full(e.sum(), wown), np.ones(eo.sum())]), D, D)
            res[name] = {"holdout": round(lift(f(Xh), ah), 3), "time_split": round(lift(f2(Xl), al), 3)}
        ok = [v for v in ("B_ctx", "C_ctx") if res[v]["holdout"] > dep["holdout"] and res[v]["time_split"] > dep["time_split"]]
        res["adopted"] = max(ok, key=lambda v: res[v]["holdout"]) if ok else "keep"
        out[ab] = res
        print(f"{ab}: deployed {prev['adopted']} {dep['holdout']:.2f}x / {dep['time_split']:.2f}x | "
              f"B_ctx {res['B_ctx']['holdout']:.2f}x / {res['B_ctx']['time_split']:.2f}x | "
              f"C_ctx {res['C_ctx']['holdout']:.2f}x / {res['C_ctx']['time_split']:.2f}x | {res['adopted']}", flush=True)
    (ROOT / "experiments/exp80_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
