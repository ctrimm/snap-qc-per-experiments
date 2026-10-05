"""NY2 — NY-filtered transfer: the first DECISION POINT of the NY POC track.

Train classifiers on synthetic data (NY-conditioned vs national), evaluate
on HELD-OUT REAL NY cases. Arms:

  a) NY-conditioned synthetic + GBM + class_weight="balanced"
  b) NY-conditioned synthetic + GBM without class_weight
  c) national synthetic + GBM + balanced
  d) national synthetic + GBM without class_weight
  e) REAL->REAL NY ceiling (GBM balanced on the NY train split) — headroom
     reference, not a product
  f) majority-class baseline (DummyClassifier most_frequent on NY train)

Two tasks:
  - element classification (error cases only): which benefit element is in
    error. The transfer gate's currency: accuracy + macroF1.
  - finding classification (all cases): correct vs over vs under.

HOLDOUT: stratified 75/25 split of NY's 3,257 QC rows (FY2020-2024 pooled),
stratified on a key where correct cases form one stratum and error cases are
stratified on finding x element-bucket-of-slot-1, with ultra-rare buckets
merged into "rare" so every stratum can be split. Seed 20260929, same
convention as PA2. The same holdout serves every arm (and NY7/NY8). Saved at
experiments/ny2_holdout_idx.json: {"split_seed": 20260929, "test_size": 0.25,
"n_ny_rows": 3257, "holdout_keys": [...]} — train = complement. A row key is
(fy, 0-based index of the row within that FY's CSV among NY rows).

Reproduction (exact commands, from repo root):
  1) python3 -m src.synth.ny_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out /tmp/ny2out/ny_synth.jsonl
  2) cd src && python3 -m synth.generate --n 20000 --seed 7 \\
        --dist ../experiments/dist.json --max-attempts 12 \\
        --out /tmp/ny2out/nat_synth.jsonl
     (seed-robustness extras: repeat both with --seed 8 and --seed 9 into
      /tmp/ny2out/ny_synth_s8.jsonl, ny_synth_s9.jsonl,
      nat_synth_s8.jsonl, nat_synth_s9.jsonl)
  3) python3 experiments/ny2_ny_transfer.py \\
        --ny-synth /tmp/ny2out/ny_synth.jsonl \\
        --nat-synth /tmp/ny2out/nat_synth.jsonl \\
        --qc-dir ../snap-qc-data/raw \\
        --holdout-json experiments/ny2_holdout_idx.json \\
        [--ny-synth-s8 ... --ny-synth-s9 ... --nat-synth-s8 ... --nat-synth-s9 ...]

Generator notes: dollar mechanisms ON and persistent buckets are the
generator defaults since exp31; both synth sets are generated with the same
n=20000 and seed=7 so the only difference is NY conditioning (the national
path is byte-identical with or without ny_state imported, per NY1).

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
from synth.codebook import element_bucket  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

NY_STATE = "36"
SUA_YES = {"3", "4", "5", "6", "7", "8"}
SPLIT_SEED = 20260929
TEST_SIZE = 0.25
SYNTH_SEED = 7
N_SYNTH = 20000
FY_FILES = [2020, 2021, 2022, 2023, 2024]

# NY's distinctive element buckets per NY3 (used for per-bucket F1 reporting):
# medical/sua/hhcomp run above national; shelter/earned below. hhcomp is
# reported too since it is one of NY3's three above-national buckets.
BUCKETS_OF_INTEREST = ["medical", "sua", "hhcomp", "earned", "shelter",
                       "unearned"]


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
    issued = float(case["issued_benefit"])
    return {
        "hh_size": float(f["hh_size"]), "earned": float(f["earned"]),
        "unearned": float(f["unearned"]),
        "shelter": float(f["shelter"]), "sua": float(f["sua"]),
        "medical_exp": float(f["medical_exp"]), "depcare": float(f["depcare"]),
        "senior_disabled": float(f["senior_disabled"]),
        "issued_benefit": issued,
    }


def load_ny_real(qc_dir):
    """All NY rows across the five FY files. Key: (fy, ny-relative row idx).

    NY indexing matches ny1_ny_generator.fit_ny_targets (STATE stripped,
    NY rows counted in CSV order per FY). NY1 used `row["STATE"] == "36"`
    without strip; verified on 2026-09-29 that no NY rows carry STATE
    whitespace, so the two conventions count identically (3,257 rows).
    """
    rows = {}   # key -> (features, finding, element_bucket|None)
    for fy in FY_FILES:
        path = Path(qc_dir) / f"qcfy{fy}_csv" / f"qc_pub_fy{fy}.csv"
        if not path.exists():
            raise FileNotFoundError(f"no csv at {path}")
        with open(path, newline="") as fh:
            ny_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != NY_STATE:
                    continue
                status = row["STATUS"].strip()
                e1 = row.get("ELEMENT1", "").strip()
                bucket = element_bucket(int(e1)) if (e1 and status != "1") else None
                rows[(fy, ny_idx)] = (
                    real_row_features(row),
                    int(status),
                    bucket,
                )
                ny_idx += 1
    return rows


# NY's ultra-rare (finding, bucket) cells (unweighted n): over side —
# arithmetic 2, depcare 6, other 5, reporting 2; under side — arithmetic 10,
# childsupport 3, depcare 4, income_total 1, other 6, reporting 1,
# standard 6. Anything not a supported bucket lands in "rare" so every
# stratum has >= 2 members and sklearn's splitter is satisfied.
RARE_BUCKETS = {None, "arithmetic", "depcare", "childsupport", "standard",
                "standard_deduction", "income_total", "other", "reporting"}


def _stratum(finding, bucket):
    """Stratification key for the holdout. Correct cases form one stratum;
    error cases are stratified by finding x element bucket, with ultra-rare
    buckets merged into 'rare' so every stratum can be split."""
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


def as_Xy(rows, y_idx):
    X = [[r[0][k] for k in V1] for r in rows]
    y = [r[y_idx] for r in rows]
    return X, y


def run_task(clf, train_rows, test_rows, y_idx, buckets):
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    sX, sy = as_Xy(train_rows, y_idx)
    rX, ry = as_Xy(test_rows, y_idx)
    clf.fit(sX, sy)
    pred = clf.predict(rX)
    acc = accuracy_score(ry, pred)
    macro = f1_score(ry, pred, average="macro", zero_division=0)
    per = f1_score(ry, pred, average=None, zero_division=0,
                   labels=sorted(set(ry)))
    per = dict(zip(sorted(set(ry)), per))
    m = {
        "acc": round(acc, 4), "macroF1": round(macro, 4),
        "per_bucket_F1": {b: round(per.get(b, 0.0), 4) for b in buckets},
        "n_test": len(ry), "n_train": len(train_rows),
    }
    if y_idx == 1:  # finding task: binary AUC from P(over)+P(under)
        proba = clf.predict_proba(rX)
        cls = list(clf.classes_)
        p_err = sum(proba[:, cls.index(c)] for c in (2, 3))
        y_bin = [0 if y == 1 else 1 for y in ry]
        m["binary_AUC"] = round(float(roc_auc_score(y_bin, p_err)), 4)
    return m, clf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ny-synth", required=True)
    ap.add_argument("--nat-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json", required=True)
    ap.add_argument("--out-json", default="/tmp/ny2out/ny2_results.json")
    for extra in ("ny-synth-s8", "ny-synth-s9", "nat-synth-s8", "nat-synth-s9"):
        ap.add_argument("--" + extra, default=None,
                        help="seed-robustness synth file for arms a-d")
    args = ap.parse_args()

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.dummy import DummyClassifier

    print("loading real NY microdata...", flush=True)
    real = load_ny_real(args.qc_dir)
    print(f"  NY rows: {len(real)}", flush=True)

    hj = Path(args.holdout_json)
    if hj.exists():
        saved = json.loads(hj.read_text())
        holdout_keys = [tuple(k) for k in saved["holdout_keys"]]
        train_keys = [k for k in sorted(real.keys()) if k not in set(holdout_keys)]
        print(f"  loaded holdout from {hj} ({len(holdout_keys)} test rows)", flush=True)
        assert saved["split_seed"] == SPLIT_SEED and saved["test_size"] == TEST_SIZE
        assert saved["n_ny_rows"] == len(real), "microdata row count changed"
    else:
        train_keys, holdout_keys = build_holdout(real)
        saved = {
            "split_seed": SPLIT_SEED, "test_size": TEST_SIZE,
            "n_ny_rows": len(real),
            "holdout_keys": [[fy, i] for (fy, i) in sorted(holdout_keys)],
            "note": ("75/25 stratified split of NY's pooled FY2020-2024 QC rows "
                     "(seed 20260929); correct cases form one stratum, error "
                     "cases stratified on finding x element bucket with "
                     "ultra-rare buckets (arithmetic/depcare/childsupport/"
                     "standard/standard_deduction/income_total/other/reporting/"
                     "missing) merged into 'rare'; "
                     "row key = [fy, 0-based index among NY rows in that FY's CSV]; "
                     "train = all NY rows not in holdout_keys."),
        }
        hj.write_text(json.dumps(saved, indent=2))
        print(f"  wrote holdout index -> {hj} ({len(holdout_keys)} test rows)", flush=True)

    train_real = [real[k] for k in train_keys]
    test_real = [real[k] for k in holdout_keys]
    n_test_err = sum(1 for r in test_real if r[1] != 1)
    print(f"  train {len(train_real)} / test {len(test_real)} (test errors: {n_test_err})", flush=True)

    print("loading synthetic sets...", flush=True)
    ny_synth = load_synth(args.ny_synth)
    nat_synth = load_synth(args.nat_synth)
    print(f"  NY synth {len(ny_synth)}, national synth {len(nat_synth)}", flush=True)

    tasks = {
        "element": 2,   # error cases only
        "finding": 1,   # all cases
    }

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

    def run_arms(ny_pool, nat_pool, tag=""):
        arms = {
            "a) NY synth + GBM balanced":       (ny_pool,  lambda: gbm(True)),
            "b) NY synth + GBM no-classweight": (ny_pool,  lambda: gbm(False)),
            "c) national synth + GBM balanced": (nat_pool, lambda: gbm(True)),
            "d) national synth + GBM no-classweight": (nat_pool, lambda: gbm(False)),
            "e) REAL->REAL NY ceiling (GBM balanced)": (train_real, lambda: gbm(True)),
            "f) majority baseline":             (train_real, lambda: DummyClassifier(strategy="most_frequent")),
        }
        res = {}
        for arm, (train_pool, clf_factory) in arms.items():
            res[arm] = {}
            print(f"\n== {tag}{arm} ==", flush=True)
            for tname, y_idx in tasks.items():
                test_rows = test_element if y_idx == 2 else test_finding
                tr = subset(train_pool, y_idx)
                m, _ = run_task(clf_factory(), tr, test_rows, y_idx,
                                BUCKETS_OF_INTEREST if y_idx == 2 else [])
                res[arm][tname] = m
                line = (f"  {tname:8s}: acc={m['acc']:.4f} macroF1={m['macroF1']:.4f} "
                        f"(n_test={m['n_test']}, n_train={len(tr)})")
                if y_idx == 2:
                    pb = m["per_bucket_F1"]
                    line += " | " + " ".join(f"{b} F1={pb[b]:.3f}" for b in BUCKETS_OF_INTEREST)
                else:
                    line += f" binary_AUC={m.get('binary_AUC', float('nan')):.3f}"
                print(line, flush=True)
        return res

    results = {"seed7": run_arms(ny_synth, nat_synth)}

    # --- seed robustness: arms a-d at generation seeds 8, 9 ---
    robust = {}
    extra_map = {"8": (args.ny_synth_s8, args.nat_synth_s8),
                 "9": (args.ny_synth_s9, args.nat_synth_s9)}
    for seedtag, (nyp, natp) in extra_map.items():
        if not (nyp and natp):
            continue
        print(f"\n######## seed robustness: generation seed {seedtag} ########", flush=True)
        nys = load_synth(nyp)
        nats = load_synth(natp)
        res = run_arms(nys, nats, tag=f"(gen seed {seedtag}) ")
        robust[seedtag] = {k: v for k, v in res.items()
                           if k.split(")")[0] in ("a", "b", "c", "d")}
    if robust:
        results["robustness"] = robust

    out = {"arms": results, "holdout": str(hj),
           "synth": {"ny": args.ny_synth, "nat": args.nat_synth,
                     "n": N_SYNTH, "seed": SYNTH_SEED}}
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2))
    print(f"\nresults -> {args.out_json}")


if __name__ == "__main__":
    main()
