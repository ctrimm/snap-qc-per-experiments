"""PA7 — feature sanity audit for the Pennsylvania POC track.

The "defend this to a CIO" check: does PA2's best element model key on
legitimate, certification-time process signals (income, deductions, household
facts a caseworker actually sees), or on post-decision / reviewer-coded
fields that would leak the label?

Steps:
  1) Retrain PA2's best arm EXACTLY per its recipe: PA-conditioned synthetic
     n=20000 seed 7 + sklearn HistGradientBoostingClassifier(random_state=0),
     NO class_weight; evaluate on the shared holdout
     (experiments/pa2_holdout_idx.json), element task on error cases.
  2) Feature importance two ways: GBM gain (sum of node split gains per
     feature across all trees) and permutation importance on the holdout.
  3) Explicit leakage audit: every feature touching a post-decision or
     reviewer-coded field (AMTERR, RAWBEN, FSBEN, STATUS, ELEMENT/NATURE/
     CAUSE label arrays, or anything unknowable at certification) is listed,
     removed, and the model retrained to measure the performance delta.

Reproduction (from repo root):
  1) cd src && python3 -m synth.pa_state --n 20000 --seed 7 \\
        --dist ../experiments/dist.json --out /tmp/pa7out/pa_synth.jsonl
  2) python3 experiments/pa7_feature_audit.py \\
        --pa-synth /tmp/pa7out/pa_synth.jsonl \\
        --qc-dir ~/workspace/snap-qc-data/raw \\
        --holdout-json experiments/pa2_holdout_idx.json

Requires: scikit-learn.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

# Field provenance: (feature -> (QC field(s), known at certification?, notes))
PROVENANCE = {
    "hh_size": ("CERTHHSZ", True, "certified household size — the caseworker budgets for this"),
    "earned": ("FSEARN", True, "monthly earned income (wages) on the case budget"),
    "unearned": ("FSUNEARN", True, "monthly unearned income (SSI/SSDI/VA/etc.) on the case budget"),
    "shelter": ("SHELDED", True, "shelter deduction amount allowed on the case"),
    "sua": ("SUA1", True, "standard utility allowance in use (codes 3-8); part of the shelter math"),
    "medical_exp": ("FSMEDEXP", True, "medical expense deduction claimed by elderly/disabled members"),
    "depcare": ("FSDEPDED", True, "dependent care deduction claimed"),
    "senior_disabled": ("FSNELDER/FSNDIS", True, "elderly or disabled member present"),
    "issued_benefit": ("RAWBEN", False, "benefit actually issued — the decision OUTCOME, post-certification"),
}

# Labels used (never features)
LABELS = {"STATUS": "finding label", "ELEMENT1": "element label (slot 1)",
          "AMTERR": "not used", "FSBEN": "not used"}

FY_FILES = [2020, 2021, 2022, 2023, 2024]
SUA_YES = {"3", "4", "5", "6", "7", "8"}


def fnum(v):
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def real_row_features(row):
    size = int(fnum(row["CERTHHSZ"]))
    earned = fnum(row["FSEARN"])
    unearned = fnum(row["FSUNEARN"])
    issued = fnum(row["RAWBEN"])
    return {
        "hh_size": float(size), "earned": earned, "unearned": unearned,
        "shelter": fnum(row["SHELDED"]),
        "sua": 1.0 if row["SUA1"].strip() in SUA_YES else 0.0,
        "medical_exp": fnum(row["FSMEDEXP"]), "depcare": fnum(row["FSDEPDED"]),
        "senior_disabled": 1.0 if (fnum(row["FSNELDER"]) > 0 or fnum(row["FSNDIS"]) > 0) else 0.0,
        "issued_benefit": issued,
    }


def synth_case_features(case):
    f = case["issued_facts"]
    issued = float(case["issued_benefit"])
    return {
        "hh_size": float(f["hh_size"]), "earned": float(f["earned"]),
        "unearned": float(f["unearned"]),
        "shelter": float(f["shelter"]), "sua": float(f["sua"]),
        "medical_exp": float(f["medical_exp"]), "depcare": float(f["depcare"]),
        "senior_disabled": float(f["senior_disabled"]),
        "issued_benefit": issued,
    }


def load_pa_real(qc_dir):
    rows = {}
    for fy in FY_FILES:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")), None)
        if path is None:
            raise FileNotFoundError(f"no csv under qcfy{fy}_csv")
        with open(path, newline="") as fh:
            pa_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != "42":
                    continue
                status = row["STATUS"].strip()
                e1 = row.get("ELEMENT1", "").strip()
                bucket = element_bucket(int(e1)) if (e1 and status != "1") else None
                rows[(fy, pa_idx)] = (real_row_features(row), int(status), bucket)
                pa_idx += 1
    return rows


def load_synth(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            rows.append((synth_case_features(c),
                         int(c["finding"]),
                         c["variances"][0]["element_bucket"] if c["variances"] else None))
    return rows


def as_Xy(rows, feats, y_idx):
    X = [[r[0][k] for k in feats] for r in rows]
    y = [r[y_idx] for r in rows]
    return X, y


def train_arm(train_rows, feats, test_rows):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score
    sX, sy = as_Xy(train_rows, feats, 2)
    rX, ry = as_Xy(test_rows, feats, 2)
    clf = HistGradientBoostingClassifier(random_state=0)
    clf.fit(sX, sy)
    pred = clf.predict(rX)
    acc = accuracy_score(ry, pred)
    macro = f1_score(ry, pred, average="macro", zero_division=0)
    return clf, {"acc": acc, "macroF1": macro}, (rX, ry)


def gbm_gain_importance(clf, feats):
    """Sum node split gains per feature over every tree of every iteration."""
    gains = {f: 0.0 for f in feats}
    feat_index = {f: i for i, f in enumerate(feats)}
    for ests in clf._predictors:
        for est in ests:
            nodes = est.nodes
            for n in nodes:
                if n["is_leaf"]:
                    continue
                gains[feats[n["feature_idx"]]] += float(n["gain"])
    total = sum(gains.values()) or 1.0
    return {f: gains[f] / total for f in feats}


def permutation_importance(clf, rX, ry, feats, n_repeats=20):
    from sklearn.inspection import permutation_importance
    res_acc = permutation_importance(clf, rX, ry, n_repeats=n_repeats,
                                     random_state=0, scoring="accuracy")
    res_f1 = permutation_importance(clf, rX, ry, n_repeats=n_repeats,
                                    random_state=0, scoring="f1_macro")
    return {f: (float(res_acc.importances_mean[i]), float(res_acc.importances_std[i]),
                float(res_f1.importances_mean[i]), float(res_f1.importances_std[i]))
            for i, f in enumerate(feats)}


def plain_meaning(feat):
    return {
        "hh_size": "household size (number of people on the case)",
        "earned": "monthly earned income — wages/salary on the case budget",
        "unearned": "monthly unearned income — SSI, Social Security, VA, etc.",
        "shelter": "shelter deduction amount (rent + utilities/SUA)",
        "sua": "whether the household gets the standard utility allowance",
        "medical_exp": "medical expense deduction (elderly/disabled members)",
        "depcare": "dependent care deduction (child/adult care costs)",
        "senior_disabled": "an elderly or disabled person is in the household",
        "issued_benefit": "benefit amount actually issued (RAWBEN)",
    }[feat]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pa-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json", required=True)
    ap.add_argument("--out-json", default="/tmp/pa7out/pa7_results.json")
    args = ap.parse_args()

    print("loading real PA microdata...", flush=True)
    real = load_pa_real(args.qc_dir)
    saved = json.loads(Path(args.holdout_json).read_text())
    holdout_keys = {tuple(k) for k in saved["holdout_keys"]}
    test_real = [real[k] for k in sorted(real.keys()) if k in holdout_keys]
    test_err = [r for r in test_real if r[2] is not None]
    print(f"  PA rows {len(real)}; holdout test {len(test_real)}; test error cases {len(test_err)}", flush=True)

    print("loading PA-conditioned synthetic...", flush=True)
    pa_synth = load_synth(args.pa_synth)
    train_err = [r for r in pa_synth if r[2] is not None]
    print(f"  synth {len(pa_synth)} total, {len(train_err)} error cases", flush=True)

    # --- 1) Retrain PA2's best arm exactly ---
    print("\n== arm b retrain (PA synth + GBM no-classweight, element task) ==", flush=True)
    clf, perf, (rX, ry) = train_arm(train_err, V1, test_err)
    print(f"  acc={perf['acc']:.4f} macroF1={perf['macroF1']:.4f} "
          f"(PA2 reported 0.567 / 0.208)", flush=True)

    # --- 2a) GBM gain importance ---
    gains = gbm_gain_importance(clf, V1)
    print("\n== GBM gain importance (share of total split gain) ==", flush=True)
    for f in sorted(V1, key=lambda f: -gains[f]):
        print(f"  {f:16s} {gains[f]:.4f}  ({plain_meaning(f)})", flush=True)

    # --- 2b) Permutation importance on the holdout ---
    perm = permutation_importance(clf, rX, ry, V1)
    print("\n== permutation importance on holdout (drop in accuracy / macroF1) ==", flush=True)
    for f in sorted(V1, key=lambda f: -perm[f][0]):
        da, sa, df1, sf1 = perm[f]
        print(f"  {f:16s} dAcc={da:+.4f}±{sa:.4f}  dF1={df1:+.4f}±{sf1:.4f}", flush=True)

    # --- 3) Leakage audit: features touching post-decision/reviewer fields ---
    print("\n== leakage audit: feature provenance ==", flush=True)
    leak_feats = []
    for f in V1:
        qcfield, known, note = PROVENANCE[f]
        flag = "" if known else "  <-- LEAKAGE SUSPECT (post-decision)"
        print(f"  {f:16s} <- {qcfield:16s} cert-time={str(known):5s} {note}{flag}", flush=True)
        if not known:
            leak_feats.append(f)
    print("  labels (never features): " +
          ", ".join(f"{k}={v}" for k, v in LABELS.items()), flush=True)

    # --- 4) Retrain without leakage features ---
    clean_feats = [f for f in V1 if f not in leak_feats]
    print(f"\n== retrain WITHOUT leakage features {leak_feats} ==", flush=True)
    clf2, perf2, (rX2, ry2) = train_arm(train_err, clean_feats, test_err)
    print(f"  acc={perf2['acc']:.4f} macroF1={perf2['macroF1']:.4f}", flush=True)
    print(f"  delta: acc {perf2['acc']-perf['acc']:+.4f}, macroF1 {perf2['macroF1']-perf['macroF1']:+.4f}", flush=True)
    gains2 = gbm_gain_importance(clf2, clean_feats)
    perm2 = permutation_importance(clf2, rX2, ry2, clean_feats)
    print("  clean-arm gain shares:", flush=True)
    for f in sorted(clean_feats, key=lambda f: -gains2[f]):
        print(f"    {f:16s} {gains2[f]:.4f}", flush=True)

    out = {
        "arm_b_retrain": {"feats": V1, "perf": perf},
        "gain_importance": gains,
        "perm_importance": {f: {"d_acc_mean": perm[f][0], "d_acc_std": perm[f][1],
                                                "d_f1_mean": perm[f][2], "d_f1_std": perm[f][3]}
                            for f in V1},
        "leakage_features": leak_feats,
        "clean_retrain": {"feats": clean_feats, "perf": perf2,
                          "gain_importance": gains2},
        "n_test_err": len(test_err), "n_train_err": len(train_err),
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2))
    print(f"\nresults -> {args.out_json}")


if __name__ == "__main__":
    main()
