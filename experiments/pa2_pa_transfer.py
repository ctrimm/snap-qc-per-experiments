"""PA2 — PA-filtered transfer: the first DECISION POINT of the PA POC track.

Train classifiers on synthetic data (PA-conditioned vs national), evaluate
on HELD-OUT REAL PA cases. Arms:

  a) PA-conditioned synthetic + GBM + class_weight="balanced"
  b) PA-conditioned synthetic + GBM without class_weight
  c) national synthetic + GBM + balanced
  d) national synthetic + GBM without class_weight
  e) REAL->REAL PA ceiling (GBM balanced on the PA train split) — headroom
     reference, not a product
  f) majority-class baseline (DummyClassifier most_frequent on PA train)

Two tasks:
  - element classification (error cases only): which benefit element is in
    error. The transfer gate's currency: accuracy + macroF1.
  - finding classification (all cases): correct vs over vs under.
    (PA4 will need P(error) from this.)

HOLDOUT: stratified 75/25 split of PA's 3,268 QC rows (FY2020-2024 pooled),
stratified on (finding, element-bucket-of-slot-1), seed 20260929. The same
holdout serves every arm. Saved at experiments/pa2_holdout_idx.json:
{"split_seed": 20260929, "test_size": 0.25, "rows": [{"fy":..,"idx":..}, ...],
 "holdout_keys": [...]} — train = complement. A row key is (fy, 0-based
index of the row within that FY's CSV among PA rows).

Reproduction (exact commands, from repo root):
  1) python3 -m synth.pa_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out /tmp/pa2out/pa_synth.jsonl
     (cwd = src/, i.e. `cd src && python3 -m synth.pa_state ...`)
  2) cd src && python3 -m synth.generate --n 20000 --seed 7 \\
        --dist ../experiments/dist.json --max-attempts 12 \\
        --out /tmp/pa2out/nat_synth.jsonl
  3) python3 experiments/pa2_pa_transfer.py \\
        --pa-synth /tmp/pa2out/pa_synth.jsonl \\
        --nat-synth /tmp/pa2out/nat_synth.jsonl \\
        --qc-dir ../snap-qc-data/raw \\
        --holdout-json experiments/pa2_holdout_idx.json

Generator notes: dollar mechanisms ON and persistent buckets are the
generator defaults since exp31; both synth sets are generated with the same
n=20000 and seed=7 so the only difference is PA conditioning (the national
path is byte-identical with or without pa_state imported, per PA1).

GBM: sklearn HistGradientBoostingClassifier(random_state=0), default
hyperparameters; class_weight either "balanced" or None.

No model weights are written anywhere. Microdata is read-only.
Requires: scikit-learn.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

SUA_YES = {"3", "4", "5", "6", "7", "8"}
SPLIT_SEED = 20260929
TEST_SIZE = 0.25
SYNTH_SEED = 7
N_SYNTH = 20000
FY_FILES = [2020, 2021, 2022, 2023, 2024]


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
    f = case["issued_facts"]  # agency-view facts, like the caseworker saw
    calc = benefit_mod.compute(f)
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
    """All PA rows across the five FY files. Key: (fy, pa-relative row idx)."""
    rows = {}   # key -> (features, finding, element_bucket|None)
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
                rows[(fy, pa_idx)] = (
                    real_row_features(row),
                    int(status),
                    bucket,
                )
                pa_idx += 1
    return rows


RARE_BUCKETS = {None, "arithmetic", "depcare", "childsupport",
                "standard_deduction"}


def _stratum(finding, bucket):
    """Stratification key for the holdout. Correct cases form one stratum;
    error cases are stratified by finding x element bucket, with ultra-rare
    buckets (which can have a single member in PA) merged into 'rare' so
    every stratum can be split."""
    if finding == 1:
        return "1"
    b = "rare" if bucket in RARE_BUCKETS else bucket
    return f"{finding}|{b}"


def build_holdout(rows):
    """Stratified 75/25 split on the stratification key above. Returns
    (train_keys, holdout_keys)."""
    from sklearn.model_selection import StratifiedShuffleSplit
    keys = sorted(rows.keys())
    strata = [_stratum(rows[k][1], rows[k][2]) for k in keys]
    sss = StratifiedShuffleSplit(n_splits=1, test_size=TEST_SIZE,
                                 random_state=SPLIT_SEED)
    train_i, test_i = next(sss.split(keys, strata))
    train_keys = [keys[i] for i in train_i]
    holdout_keys = [keys[i] for i in test_i]
    return train_keys, holdout_keys


def load_synth(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            rows.append((synth_case_features(c),
                         int(c["finding"]),
                         c["variances"][0]["element_bucket"] if c["variances"] else None))
    return rows


def as_Xy(rows, y_idx, classes=None):
    X = [[r[0][k] for k in V1] for r in rows]
    y = [r[y_idx] for r in rows]
    return X, y


def metrics(y_true, y_pred, buckets_of_interest):
    from sklearn.metrics import accuracy_score, f1_score
    acc = accuracy_score(y_true, y_pred)
    macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
    per = f1_score(y_true, y_pred, average=None, zero_division=0,
                   labels=sorted(set(y_true)))
    per = dict(zip(sorted(set(y_true)), per))
    return {
        "acc": round(acc, 4), "macroF1": round(macro, 4),
        "per_bucket_F1": {b: round(per.get(b, 0.0), 4) for b in buckets_of_interest},
        "n_test": len(y_true),
    }


def run_arm(clf, train_rows, test_rows, y_idx, buckets):
    from sklearn.metrics import accuracy_score, f1_score
    sX, sy = as_Xy(train_rows, y_idx)
    rX, ry = as_Xy(test_rows, y_idx)
    clf.fit(sX, sy)
    pred = clf.predict(rX)
    return metrics(ry, pred, buckets), clf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pa-synth", required=True)
    ap.add_argument("--nat-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json", required=True)
    args = ap.parse_args()

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.dummy import DummyClassifier

    print("loading real PA microdata...", flush=True)
    real = load_pa_real(args.qc_dir)
    print(f"  PA rows: {len(real)}", flush=True)

    hj = Path(args.holdout_json)
    if hj.exists():
        saved = json.loads(hj.read_text())
        holdout_keys = [tuple(k) for k in saved["holdout_keys"]]
        train_keys = [k for k in sorted(real.keys()) if k not in set(holdout_keys)]
        print(f"  loaded holdout from {hj} ({len(holdout_keys)} test rows)", flush=True)
        assert saved["split_seed"] == SPLIT_SEED and saved["test_size"] == TEST_SIZE
    else:
        train_keys, holdout_keys = build_holdout(real)
        saved = {
            "split_seed": SPLIT_SEED, "test_size": TEST_SIZE,
            "n_pa_rows": len(real),
            "holdout_keys": [[fy, i] for (fy, i) in sorted(holdout_keys)],
            "note": ("75/25 stratified split of PA's pooled FY2020-2024 QC rows "
                     "(seed 20260929); correct cases form one stratum, error "
                     "cases stratified on finding x element bucket with "
                     "ultra-rare buckets (arithmetic/depcare/childsupport/"
                     "standard_deduction/missing) merged into 'rare'; "
                     "row key = [fy, 0-based index among PA rows in that FY's CSV]; "
                     "train = all PA rows not in holdout_keys."),
        }
        hj.write_text(json.dumps(saved, indent=2))
        print(f"  wrote holdout index -> {hj} ({len(holdout_keys)} test rows)", flush=True)

    train_real = [real[k] for k in train_keys]
    test_real = [real[k] for k in holdout_keys]
    n_test_err = sum(1 for r in test_real if r[1] != 1)
    print(f"  train {len(train_real)} / test {len(test_real)} (test errors: {n_test_err})", flush=True)

    print("loading synthetic sets...", flush=True)
    pa_synth = load_synth(args.pa_synth)
    nat_synth = load_synth(args.nat_synth)
    print(f"  PA synth {len(pa_synth)}, national synth {len(nat_synth)}", flush=True)

    tasks = {
        "element": 2,   # error cases only
        "finding": 1,   # all cases
    }
    buckets_of_interest = ["shelter", "medical", "earned"]  # PA's distinctive buckets (PA3)

    def subset(rows, y_idx):
        if y_idx == 2:  # element: error cases with a labeled bucket
            return [r for r in rows if r[2] is not None]
        return rows

    test_element = subset(test_real, 2)
    test_finding = subset(test_real, 1)
    print("test label distributions:",
          {b: sum(1 for r in test_element if r[2] == b)
           for b in sorted({r[2] for r in test_element})},
          {s: sum(1 for r in test_finding if r[1] == s) for s in (1, 2, 3)}, flush=True)

    def gbm(balanced):
        kw = {"random_state": 0}
        if balanced:
            kw["class_weight"] = "balanced"
        return HistGradientBoostingClassifier(**kw)

    arms = {
        "a) PA synth + GBM balanced":      (pa_synth,  lambda: gbm(True)),
        "b) PA synth + GBM no-classweight": (pa_synth, lambda: gbm(False)),
        "c) national synth + GBM balanced":  (nat_synth, lambda: gbm(True)),
        "d) national synth + GBM no-classweight": (nat_synth, lambda: gbm(False)),
        "e) REAL->REAL PA ceiling (GBM balanced)": (train_real, lambda: gbm(True)),
        "f) majority baseline":            (train_real, lambda: DummyClassifier(strategy="most_frequent")),
    }

    results = {}
    for arm, (train_pool, clf_factory) in arms.items():
        results[arm] = {}
        print(f"\n== {arm} ==", flush=True)
        for tname, y_idx in tasks.items():
            test_rows = test_element if y_idx == 2 else test_finding
            tr = subset(train_pool, y_idx)
            clf = clf_factory()
            sX, sy = as_Xy(tr, y_idx)
            rX, ry = as_Xy(test_rows, y_idx)
            clf.fit(sX, sy)
            pred = clf.predict(rX)
            m = metrics(ry, pred, buckets_of_interest if y_idx == 2 else [])
            results[arm][tname] = m
            line = (f"  {tname:8s}: acc={m['acc']:.4f} macroF1={m['macroF1']:.4f} "
                    f"(n_test={m['n_test']}, n_train={len(tr)})")
            if y_idx == 2:
                pb = m["per_bucket_F1"]
                line += (f" | shelter F1={pb['shelter']:.3f} "
                         f"medical F1={pb['medical']:.3f} earned F1={pb['earned']:.3f}")
            print(line, flush=True)

    out = {"arms": results, "holdout": str(hj),
           "synth": {"pa": args.pa_synth, "nat": args.nat_synth,
                     "n": N_SYNTH, "seed": SYNTH_SEED}}
    print("\n" + json.dumps(out, indent=2))
    with open("/tmp/pa2out/pa2_results.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("results -> /tmp/pa2out/pa2_results.json")


if __name__ == "__main__":
    main()
