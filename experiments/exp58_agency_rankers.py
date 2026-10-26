"""Exp 58 — triage rankers on agency-side features only, packaged per state.

exp56/exp57's rankers (and the PA2-PA8 lineage before them) used FSEARN,
FSUNEARN, FSNELDER and FSNDIS. In the QC public-use file those are
QC-verified values (labels.FIELD_SPEC puts them in the verification view):
for an income error, FSEARN already holds the corrected income. A triage
tool runs before review, so it can only use what the agency had. This
experiment rebuilds the ranker on agency-side fields only, re-tunes and
re-calibrates it per state with the exp56 / exp57 procedures, and packages
the result as the POC deliverable.

Agency-side features (one row = one sampled case):
  CERTHHSZ, RAWHSIZE, RAWGROSS, RAWNET, RAWERND (20% earned-income deduction;
  earned ~= 5 x RAWERND), derived earned / unearned split, SHELDED, RENT, UTIL,
  SUA1 (standard utility allowance used), FSMEDEXP, FSDEPDED, FSCSEXP (claimed
  deductions), HOMEDED, RAWBEN (issued benefit), plus ratios.
Never inputs: AMTERR, STATUS, ELEMENT*/NATURE*/AGENCY*/AMOUNT*, FS* verified
fields other than the three claimed-deduction fields above.

Per state: nested-CV top-20% dollar lift (untuned vs tuned), time split
(FY2020-22 -> FY2023-24), holdout (state's existing split), and the exp57
dollar calibration (isotonic of actual dollars on the out-of-fold score).
--package then refits on all of the state's labeled rows and writes
deliverables/state_rankers/<ST>/{model.joblib, model_card.json}.

Usage (repo root):
  OMP_NUM_THREADS=2 python3 experiments/exp58_agency_rankers.py [--states PA,NY,...] [--package]
"""
import argparse
import csv
import datetime
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402

FY_FILES = [2020, 2021, 2022, 2023, 2024]
SUA_YES = {"3", "4", "5", "6", "7", "8"}
FEATURES = ["hh_size_cert", "hh_size_reported", "gross_income", "net_income", "earned_deduction",
            "earned_est", "unearned_est", "shelter_deduction", "rent", "utilities", "sua_used",
            "medical_claimed", "depcare_claimed", "child_support_claimed", "homeless",
            "issued_benefit", "income_per_person", "earned_share", "shelter_to_income", "net_to_gross"]
# exp107: SNAPQC_FEATURES=leakfree drops the issued benefit. The QC file's RAW* income, deduction and size fields are
# the QC reviewer's recorded values (exp106), so pairing them with RAWBEN (what the agency issued) leaks the error.
LEAKFREE = os.environ.get("SNAPQC_FEATURES") == "leakfree"
if LEAKFREE:
    FEATURES = [f for f in FEATURES if f != "issued_benefit"]


def results_path(name):
    """experiments/<name>, or its *_leakfree_results.json twin under SNAPQC_FEATURES=leakfree (exp107)."""
    return ROOT / "experiments" / (name.replace("_results.json", "_leakfree_results.json") if LEAKFREE else name)
DELIVER = ROOT / "deliverables" / "state_rankers"


def fnum(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def agency_features(row):
    """Agency-side feature vector from one QC public-use row (or a CSV row with
    the same column names). Order = FEATURES."""
    gross, net, ernd = fnum(row.get("RAWGROSS")), fnum(row.get("RAWNET")), fnum(row.get("RAWERND"))
    earned = 5.0 * ernd
    unearned = max(gross - earned, 0.0)
    size = fnum(row.get("CERTHHSZ"))
    shelter = fnum(row.get("SHELDED"))
    v = [size, fnum(row.get("RAWHSIZE")), gross, net, ernd, earned, unearned, shelter,
         fnum(row.get("RENT")), fnum(row.get("UTIL")),
         1.0 if (row.get("SUA1") or "").strip() in SUA_YES else 0.0,
         fnum(row.get("FSMEDEXP")), fnum(row.get("FSDEPDED")), fnum(row.get("FSCSEXP")),
         1.0 if (row.get("HOMEDED") or "").strip() == "1" else 0.0,
         fnum(row.get("RAWBEN")),
         gross / max(size, 1.0), earned / gross if gross > 0 else 0.0,
         shelter / gross if gross > 0 else shelter, net / gross if gross > 0 else 0.0]
    if LEAKFREE:
        del v[15]  # issued_benefit
    return v


def load_state(qc_dir, code):
    rows = {}
    for fy in FY_FILES:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")))
        idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != code:
                    continue
                rows[(fy, idx)] = (agency_features(row), row["STATUS"].strip(), fnum(row["AMTERR"]))
                idx += 1
    return rows


def arrays(real, keys):
    X = np.array([real[k][0] for k in keys])
    y = np.array([real[k][1] != "1" for k in keys], int)
    a = np.array([real[k][2] for k in keys])
    return X, y, a


def dollar_calibrator(X, y, a, cfg_c, cfg_r, seed=58):
    """exp57 variant 3: isotonic of actual dollars on the out-of-fold raw score."""
    from sklearn.isotonic import IsotonicRegression
    from sklearn.model_selection import StratifiedKFold
    s_oof = np.zeros(len(y))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y):
        f, _ = E56.fit_two_part(X[tr], y[tr], a[tr], cfg_c, cfg_r)
        s_oof[te] = f(X[te])
    return IsotonicRegression(out_of_bounds="clip", y_min=0).fit(s_oof, a)


def evaluate(st, qc_dir, n_search):
    from sklearn.model_selection import StratifiedKFold
    code, hfile, _, _ = E56.STATES[st]
    real = load_state(qc_dir, code)
    hold = {tuple(k) for k in json.loads((ROOT / "experiments" / hfile).read_text())["holdout_keys"]}
    tr = [k for k in sorted(real) if k not in hold]
    te = [k for k in sorted(real) if k in hold]
    X, y, a = arrays(real, tr)
    Xh, yh, ah = arrays(real, te)
    D = E56.DEFAULT
    outer = list(StratifiedKFold(5, shuffle=True, random_state=56).split(X, y))
    cv = {"untuned": 0.0, "tuned": 0.0}
    for i, (p, q) in enumerate(outer):
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
        ts[name] = E56.dollars_at(f(X[late]), a[late], 0.20) / (float(a[late].sum()) * 0.20)
    use_tuned = cv["tuned"] > cv["untuned"]
    if use_tuned:
        cc, cr, _ = E56.search(X, y, a, n_search, seed=400)
    else:
        cc, cr = D, D
    f, _ = E56.fit_two_part(X, y, a, cc, cr)
    iso = dollar_calibrator(X, y, a, cc, cr)
    raw = f(Xh); cal = iso.predict(raw)
    hold_res = {}
    for frac in (0.10, 0.20, 0.30):
        k = int(round(len(raw) * frac)); idx = np.argsort(-raw, kind="stable")[:k]
        rec = float(ah[idx].sum())
        hold_res[f"top{int(frac * 100)}"] = {
            "lift": round(rec / (float(ah.sum()) * frac), 3),
            "per_hour_$": round(rec / (k * E56.REVIEW_MIN / 60), 1),
            "random_per_hour_$": round(float(ah.sum()) * frac / (k * E56.REVIEW_MIN / 60), 1),
            "expected_over_actual": round(float(cal[idx].sum()) / max(rec, 1.0), 3)}
    return {"state": st, "n_train": len(tr), "n_holdout": len(te), "n_errors_train": int(y.sum()),
            "nested_cv_top20_lift": {k: round(v / rand, 3) for k, v in cv.items()},
            "time_split_top20_lift": {k: round(v, 3) for k, v in ts.items()},
            "chosen": "tuned" if use_tuned else "untuned", "cfg": {"clf": cc, "reg": cr},
            "holdout": hold_res}


def package(st, qc_dir, ev):
    """Refit on all of the state's labeled rows; write model + card."""
    import joblib
    import sklearn
    code = E56.STATES[st][0]
    real = load_state(qc_dir, code)
    keys = sorted(real)
    X, y, a = arrays(real, keys)
    cc, cr = ev["cfg"]["clf"], ev["cfg"]["reg"]
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    clf = HistGradientBoostingClassifier(random_state=0, **cc).fit(X, y)
    reg = HistGradientBoostingRegressor(random_state=0, **cr).fit(X[a > 0], np.log1p(a[a > 0]))
    iso = dollar_calibrator(X, y, a, cc, cr)
    out = DELIVER / st
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"features": FEATURES, "classifier": clf, "dollar_regressor": reg,
                 "dollar_calibrator": iso, "state": st}, out / "model.joblib")
    card = {"state": st, "state_code": code, "built": datetime.date.today().isoformat(),
            "training_rows": len(keys), "training_years": "FY2020-2024 QC public-use",
            "error_rows": int(y.sum()), "features": FEATURES,
            "feature_note": "agency-side fields only (what the agency had before QC review)",
            "model": "P(error) x E[dollars | error], HistGradientBoosting; expected dollars "
                     "calibrated by isotonic regression on out-of-fold scores (exp57)",
            "config": ev["cfg"], "chosen": ev["chosen"],
            "evaluation": {k: ev[k] for k in ("nested_cv_top20_lift", "time_split_top20_lift", "holdout",
                                               "n_train", "n_holdout")},
            "review_minutes_assumed": E56.REVIEW_MIN, "sklearn_version": sklearn.__version__,
            "source": "snap-qc-per-experiments exp58 (experiments/exp58_agency_rankers.py)"}
    (out / "model_card.json").write_text(json.dumps(card, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-dir", default=str(ROOT.parent / "snap-qc-data/raw"))
    ap.add_argument("--states", default="PA,NY,TX,SD,UT,ID")
    ap.add_argument("--n-search", type=int, default=30)
    ap.add_argument("--package", action="store_true")
    args = ap.parse_args()
    results = []
    for st in args.states.split(","):
        ev = evaluate(st, args.qc_dir, args.n_search)
        results.append(ev)
        h = ev["holdout"]["top20"]
        print(f"{st}: nested CV {ev['nested_cv_top20_lift']['untuned']:.2f}x -> {ev['nested_cv_top20_lift']['tuned']:.2f}x "
              f"| time split {ev['time_split_top20_lift']['untuned']:.2f}x -> {ev['time_split_top20_lift']['tuned']:.2f}x "
              f"| holdout top10 {ev['holdout']['top10']['lift']:.2f}x top20 {h['lift']:.2f}x "
              f"(${h['per_hour_$']:.0f}/hr vs ${h['random_per_hour_$']:.0f}) exp/act {h['expected_over_actual']:.2f} "
              f"| chosen {ev['chosen']}", flush=True)
        if args.package:
            print(f"  packaged -> {package(st, args.qc_dir, ev)}", flush=True)
    (ROOT / "experiments" / "exp58_results.json").write_text(json.dumps(results, indent=1, default=float))
    print("wrote experiments/exp58_results.json")


if __name__ == "__main__":
    main()
