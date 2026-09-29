"""Exp 35 — discriminator diagnostic: where does the generator look synthetic?

A synthetic-vs-real classifier separates best on specific feature slices,
revealing generator blindspots that marginal checks miss (calibration gate).

Method: 20k synthetic cases (seed 7, current default persistent generator)
plus real FY2024 QC rows, shared v2 feature set (exp4/exp19 recipe). Labels:
synthetic=0, real=1. Stratified 70/30 split. HistGradientBoostingClassifier
(random_state=0) primary, logistic regression (scaled) secondary. Report test
AUC overall and sliced by element bucket, dollar-error band
(zero / small <=$56 / large), and household type (earner vs non-earner,
senior/disabled vs not). Top distinguishing features via permutation
importance (GBM) and standardized |coef| (LR).

Usage: python3 experiments/exp35_discriminator_diagnostic.py
Requires: scikit-learn, numpy
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QC = Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
SYNTH = Path("/tmp/exp35_synth.jsonl")

V2 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit",
      "gross", "net", "gap_to_max", "benefit_frac", "review_month",
      "n_elderly", "n_disabled", "has_earned", "has_unearned", "earned_share"]

SUA_YES = {"3", "4", "5", "6", "7", "8"}
DOLLAR_BAND_CUT = 56.0


def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def real_row_features(row):
    size = int(fnum(row["CERTHHSZ"]))
    earned = fnum(row["FSEARN"])
    unearned = fnum(row["FSUNEARN"])
    gross = fnum(row["FSGRINC"])
    net = fnum(row["FSNETINC"])
    issued = fnum(row["RAWBEN"])
    mallot = params.max_allotment(size)
    return {
        "hh_size": float(size), "earned": earned, "unearned": unearned,
        "shelter": fnum(row["SHELDED"]),
        "sua": 1.0 if row["SUA1"].strip() in SUA_YES else 0.0,
        "medical_exp": fnum(row["FSMEDEXP"]), "depcare": fnum(row["FSDEPDED"]),
        "senior_disabled": 1.0 if (fnum(row["FSNELDER"]) > 0 or fnum(row["FSNDIS"]) > 0) else 0.0,
        "issued_benefit": issued,
        "gross": gross, "net": net,
        "gap_to_max": mallot - issued,
        "benefit_frac": issued / mallot if mallot else 0.0,
        "review_month": float(row["YRMONTH"].strip()[-2:]),
        "n_elderly": fnum(row["FSNELDER"]), "n_disabled": fnum(row["FSNDIS"]),
        "has_earned": 1.0 if earned > 0 else 0.0,
        "has_unearned": 1.0 if fnum(row["FSUNEARN"]) > 0 else 0.0,
        "earned_share": earned / gross if gross > 0 else 0.0,
    }


def synth_case_features(case):
    f = case["issued_facts"]
    calc = benefit_mod.compute(f)
    size = f["hh_size"]
    mallot = params.max_allotment(size)
    issued = float(case["issued_benefit"])
    gross = calc["gross"]
    return {
        "hh_size": float(size), "earned": f["earned"], "unearned": f["unearned"],
        "shelter": f["shelter"], "sua": float(f["sua"]),
        "medical_exp": f["medical_exp"], "depcare": f["depcare"],
        "senior_disabled": float(f["senior_disabled"]),
        "issued_benefit": issued,
        "gross": gross, "net": calc["net"],
        "gap_to_max": mallot - issued,
        "benefit_frac": issued / mallot if mallot else 0.0,
        "review_month": float(f["review_month"]),
        "n_elderly": float(f["n_elderly"]), "n_disabled": float(f["n_disabled"]),
        "has_earned": 1.0 if f["earned"] > 0 else 0.0,
        "has_unearned": 1.0 if f["unearned"] > 0 else 0.0,
        "earned_share": f["earned"] / gross if gross > 0 else 0.0,
    }


def dollar_band(dollar):
    if dollar <= 0:
        return "zero"
    return "small" if dollar <= DOLLAR_BAND_CUT else "large"


def load_real():
    rows = []
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            status = row["STATUS"].strip()
            e1 = row.get("ELEMENT1", "").strip()
            feats = real_row_features(row)
            if status == "1":
                bucket = "correct"
                dollar = 0.0
            else:
                bucket = element_bucket(int(e1)) if e1 else "unknown"
                dollar = abs(fnum(row["AMTERR"]))
            rows.append({
                "feats": feats, "label": 1, "bucket": bucket,
                "dollar_band": dollar_band(dollar), "dollar": dollar,
                "earner": "earner" if feats["has_earned"] > 0 else "non-earner",
                "senior": "senior/disabled" if feats["senior_disabled"] > 0 else "neither",
            })
    return rows


def load_synth(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            feats = synth_case_features(c)
            if c["variances"]:
                bucket = c["variances"][0]["element_bucket"]
                dollar = abs(c.get("dollar_error", 0) or 0)
            else:
                bucket = "correct"
                dollar = 0.0
            rows.append({
                "feats": feats, "label": 0, "bucket": bucket,
                "dollar_band": dollar_band(dollar), "dollar": dollar,
                "earner": "earner" if feats["has_earned"] > 0 else "non-earner",
                "senior": "senior/disabled" if feats["senior_disabled"] > 0 else "neither",
            })
    return rows


def main():
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    print("git HEAD:", subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip())
    print("git status:", subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip().replace("\n", " | "))

    print("loading real FY2024...", flush=True)
    real = load_real()
    print(f"  real rows: {len(real)}", flush=True)
    print("loading synth...", flush=True)
    synth = load_synth(SYNTH)
    print(f"  synth rows: {len(synth)}", flush=True)

    rows = real + synth
    X = [[r["feats"][k] for k in V2] for r in rows]
    y = [r["label"] for r in rows]

    idx = list(range(len(rows)))
    tr, te = train_test_split(idx, test_size=0.30, random_state=0, stratify=y)
    Xtr, ytr = [X[i] for i in tr], [y[i] for i in tr]
    Xte, yte = [X[i] for i in te], [y[i] for i in te]
    te_rows = [rows[i] for i in te]
    print(f"train {len(Xtr)} / test {len(Xte)} "
          f"(train real rate={sum(ytr)/len(ytr):.3f}, test real rate={sum(yte)/len(yte):.3f})")

    gbm = HistGradientBoostingClassifier(random_state=0).fit(Xtr, ytr)
    lr = make_pipeline(StandardScaler(),
                       LogisticRegression(max_iter=5000)).fit(Xtr, ytr)
    pg = gbm.predict_proba(Xte)[:, 1]
    pl = lr.predict_proba(Xte)[:, 1]
    print(f"\noverall test AUC: GBM={roc_auc_score(yte, pg):.4f} "
          f"LR={roc_auc_score(yte, pl):.4f} (chance=0.5)")

    def slice_rows(key):
        groups = {}
        for i, r in enumerate(te_rows):
            groups.setdefault(r[key], []).append(i)
        return groups

    def report(key, min_n=10):
        print(f"\n== slice: {key} ==")
        print(f"{'slice':<18} {'n_syn':>6} {'n_real':>7} "
              f"{'GBM_AUC':>8} {'LR_AUC':>7} "
              f"{'P(real|syn)':>10} {'P(real|real)':>12}")
        out = []
        for name, ii in sorted(slice_rows(key).items()):
            ns = sum(1 for i in ii if yte[i] == 0)
            nr = len(ii) - ns
            if ns < min_n or nr < min_n:
                auc_g = auc_l = float("nan")
            else:
                auc_g = roc_auc_score([yte[i] for i in ii], [pg[i] for i in ii])
                auc_l = roc_auc_score([yte[i] for i in ii], [pl[i] for i in ii])
            pr_s = sum(pg[i] for i in ii if yte[i] == 0) / ns if ns else float("nan")
            pr_r = sum(pg[i] for i in ii if yte[i] == 1) / nr if nr else float("nan")
            out.append((name, ns, nr, auc_g, auc_l, pr_s, pr_r))
        for name, ns, nr, auc_g, auc_l, pr_s, pr_r in sorted(
                out, key=lambda t: (t[3] != t[3], -(t[3] if t[3] == t[3] else 0))):
            print(f"{name:<18} {ns:>6} {nr:>7} "
                  f"{auc_g:>8.3f} {auc_l:>7.3f} {pr_s:>10.3f} {pr_r:>12.3f}")
        return out

    slices = {}
    for key in ("bucket", "dollar_band", "earner", "senior"):
        slices[key] = report(key)

    # ---- top distinguishing features ----
    print("\n== GBM permutation importance (test AUC drop) ==")
    import numpy as np
    rng = np.random.RandomState(0)
    base = roc_auc_score(yte, pg)
    imp = []
    Xte_arr = np.array(Xte)
    for j, feat in enumerate(V2):
        drops = []
        for _ in range(5):
            Xp = Xte_arr.copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            drops.append(base - roc_auc_score(yte, gbm.predict_proba(Xp)[:, 1]))
        imp.append((feat, sum(drops) / len(drops)))
    for feat, d in sorted(imp, key=lambda t: -t[1])[:10]:
        print(f"  {feat:16s} {d:+.4f}")

    print("\n== LR standardized |coef| (top 10) ==")
    coef = lr.named_steps["logisticregression"].coef_[0]
    for feat, c in sorted(zip(V2, coef), key=lambda t: -abs(t[1]))[:10]:
        print(f"  {feat:16s} {c:+.4f}")

    Path("/tmp/exp35_slices.json").write_text(json.dumps(
        {k: [{"slice": n, "n_synth": ns, "n_real": nr,
              "gbm_auc": g, "lr_auc": l,
              "p_real_given_synth": ps, "p_real_given_real": pr}
             for n, ns, nr, g, l, ps, pr in v]
         for k, v in slices.items()}, indent=1))
    print("\nsaved /tmp/exp35_slices.json")


if __name__ == "__main__":
    main()
