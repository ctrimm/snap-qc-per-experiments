"""SD2 — SD-filtered transfer: the first DECISION POINT of the SD POC track.

Train classifiers on synthetic data (SD-conditioned vs national), evaluate
on HELD-OUT REAL SD cases. Arms:

  a) SD-conditioned synthetic + GBM + class_weight="balanced"
  b) SD-conditioned synthetic + GBM without class_weight
  c) national synthetic + GBM + balanced
  d) national synthetic + GBM without class_weight
  e) REAL->REAL SD ceiling (GBM balanced on the SD train split) — headroom
     reference, not a product
  f) majority-class baseline (DummyClassifier most_frequent on SD train)

Two tasks:
  - element classification (error cases only): which benefit element is in
    error. The transfer gate's currency: accuracy + macroF1.
  - finding classification (all cases): correct vs over vs under.

HOLDOUT: stratified 75/25 split of SD's 2,365 QC rows (FY2020-2024 pooled),
stratified on a key where correct cases form one stratum and error cases are
stratified on finding x element-bucket-of-slot-1, with ultra-rare buckets
merged into "rare" so every stratum can be split. Seed 20260929, same
convention as PA2/NY2. The same holdout serves every arm (and SD7/SD8). Saved at
experiments/sd_holdout_idx.json: {"split_seed": 20260929, "test_size": 0.25,
"n_sd_rows": 2365, "holdout_keys": [...]} — train = complement. A row key is
(fy, 0-based index of the row within that FY's CSV among SD rows).

Reproduction (exact commands, from repo root):
  1) python3 -m src.synth.sd_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out /tmp/sd2out/sd_synth.jsonl
  2) cd src && python3 -m synth.generate --n 20000 --seed 7 \\
        --dist ../experiments/dist.json --max-attempts 12 \\
        --out /tmp/sd2out/nat_synth.jsonl
     (seed-robustness extras: repeat both with --seed 8 and --seed 9 into
      /tmp/sd2out/sd_synth_s8.jsonl, sd_synth_s9.jsonl,
      nat_synth_s8.jsonl, nat_synth_s9.jsonl)
  3) python3 experiments/sd2_sd_transfer.py \\
        --sd-synth /tmp/sd2out/sd_synth.jsonl \\
        --nat-synth /tmp/sd2out/nat_synth.jsonl \\
        --qc-dir ../snap-qc-data/raw \\
        --holdout-json experiments/sd_holdout_idx.json \\
        [--sd-synth-s8 ... --sd-synth-s9 ... --nat-synth-s8 ... --nat-synth-s9 ...]

Generator notes: dollar mechanisms ON and persistent buckets are the
generator defaults since exp31; both synth sets are generated with the same
n=20000 and seed=7 so the only difference is SD conditioning (the national
path is byte-identical with or without sd_state imported, per SD1).

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

SD_STATE = "46"
SUA_YES = {"3", "4", "5", "6", "7", "8"}
SPLIT_SEED = 20260929
TEST_SIZE = 0.25
SYNTH_SEED = 7
N_SYNTH = 20000
FY_FILES = [2020, 2021, 2022, 2023, 2024]

# SD's distinctive element buckets per SD1 (used for per-bucket F1 reporting):
# earned (1.32x national share) and medical (1.41x) run above national;
# sua (0.67x) runs below; shelter/unearned near national. hhcomp is
# reported too since SD1 flags it as a national-tail over-recording cell.
BUCKETS_OF_INTEREST = ["earned", "medical", "shelter", "sua", "unearned",
                       "hhcomp"]


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


def load_sd_real(qc_dir):
    """All SD rows across the five FY files. Key: (fy, sd-relative row idx).

    SD indexing matches sd1_sd_generator.fit_sd_targets (STATE stripped,
    SD rows counted in CSV order per FY). SD1 used `row["STATE"] == "46"`
    without strip; verified on 2026-10-03 that no SD rows carry STATE
    whitespace, so the two conventions count identically (2,365 rows).
    """
    rows = {}   # key -> (features, finding, element_bucket|None)
    for fy in FY_FILES:
        path = Path(qc_dir) / f"qcfy{fy}_csv" / f"qc_pub_fy{fy}.csv"
        if not path.exists():
            raise FileNotFoundError(f"no csv at {path}")
        with open(path, newline="") as fh:
            sd_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != SD_STATE:
                    continue
                status = row["STATUS"].strip()
                e1 = row.get("ELEMENT1", "").strip()
                bucket = element_bucket(int(e1)) if (e1 and status != "1") else None
                rows[(fy, sd_idx)] = (
                    real_row_features(row),
                    int(status),
                    bucket,
                )
                sd_idx += 1
    return rows


# SD's ultra-rare (finding, bucket) cells (unweighted n, pooled FY2020-24):
# over side — depcare 3, childsupport 4, hhcomp 1, assets 1, other 8,
# missing-bucket 1; under side — depcare 1, hhcomp 4, other 4, missing 1.
# Merged: 2|rare n=22, 3|rare n=10 (both >= 2, splitter satisfied).
# sua (6/14) and medical (13/20) stay as their own thin strata.
RARE_BUCKETS = {None, "assets", "childsupport", "depcare", "hhcomp", "other",
                "arithmetic", "standard", "standard_deduction",
                "income_total", "reporting"}


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
    ap.add_argument("--sd-synth", required=True)
    ap.add_argument("--nat-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json", required=True)
    ap.add_argument("--out-json", default="/tmp/sd2out/sd2_results.json")
    for extra in ("sd-synth-s8", "sd-synth-s9", "nat-synth-s8", "nat-synth-s9"):
        ap.add_argument("--" + extra, default=None,
                        help="seed-robustness synth file for arms a-d")
    args = ap.parse_args()

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.dummy import DummyClassifier

    print("loading real SD microdata...", flush=True)
    real = load_sd_real(args.qc_dir)
    print(f"  SD rows: {len(real)}", flush=True)

    hj = Path(args.holdout_json)
    if hj.exists():
        saved = json.loads(hj.read_text())
        holdout_keys = [tuple(k) for k in saved["holdout_keys"]]
        train_keys = [k for k in sorted(real.keys()) if k not in set(holdout_keys)]
        print(f"  loaded holdout from {hj} ({len(holdout_keys)} test rows)", flush=True)
        assert saved["split_seed"] == SPLIT_SEED and saved["test_size"] == TEST_SIZE
        assert saved["n_sd_rows"] == len(real), "microdata row count changed"
    else:
        train_keys, holdout_keys = build_holdout(real)
        saved = {
            "split_seed": SPLIT_SEED, "test_size": TEST_SIZE,
            "n_sd_rows": len(real),
            "holdout_keys": [[fy, i] for (fy, i) in sorted(holdout_keys)],
            "note": ("75/25 stratified split of SD's pooled FY2020-2024 QC rows "
                     "(seed 20260929); correct cases form one stratum, error "
                     "cases stratified on finding x element bucket with "
                     "ultra-rare buckets (assets/childsupport/depcare/hhcomp/"
                     "other/missing, plus never-occurring arithmetic/standard/"
                     "standard_deduction/income_total/reporting) merged into "
                     "'rare' (2|rare n=22, 3|rare n=10); "
                     "row key = [fy, 0-based index among SD rows in that FY's CSV]; "
                     "train = all SD rows not in holdout_keys."),
        }
        hj.write_text(json.dumps(saved, indent=2))
        print(f"  wrote holdout index -> {hj} ({len(holdout_keys)} test rows)", flush=True)

    train_real = [real[k] for k in train_keys]
    test_real = [real[k] for k in holdout_keys]
    n_test_err = sum(1 for r in test_real if r[1] != 1)
    print(f"  train {len(train_real)} / test {len(test_real)} (test errors: {n_test_err})", flush=True)

    print("loading synthetic sets...", flush=True)
    sd_synth = load_synth(args.sd_synth)
    nat_synth = load_synth(args.nat_synth)
    print(f"  SD synth {len(sd_synth)}, national synth {len(nat_synth)}", flush=True)

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

    def run_arms(sd_pool, nat_pool, tag=""):
        arms = {
            "a) SD synth + GBM balanced":       (sd_pool,  lambda: gbm(True)),
            "b) SD synth + GBM no-classweight": (sd_pool,  lambda: gbm(False)),
            "c) national synth + GBM balanced": (nat_pool, lambda: gbm(True)),
            "d) national synth + GBM no-classweight": (nat_pool, lambda: gbm(False)),
            "e) REAL->REAL SD ceiling (GBM balanced)": (train_real, lambda: gbm(True)),
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

    results = {"seed7": run_arms(sd_synth, nat_synth)}

    # --- seed robustness: arms a-d at generation seeds 8, 9 ---
    robust = {}
    extra_map = {"8": (args.sd_synth_s8, args.nat_synth_s8),
                 "9": (args.sd_synth_s9, args.nat_synth_s9)}
    for seedtag, (sdp, natp) in extra_map.items():
        if not (sdp and natp):
            continue
        print(f"\n######## seed robustness: generation seed {seedtag} ########", flush=True)
        sds = load_synth(sdp)
        nats = load_synth(natp)
        res = run_arms(sds, nats, tag=f"(gen seed {seedtag}) ")
        robust[seedtag] = {k: v for k, v in res.items()
                           if k.split(")")[0] in ("a", "b", "c", "d")}
    if robust:
        results["robustness"] = robust

    out = {"arms": results, "holdout": str(hj),
           "synth": {"ny": args.sd_synth, "nat": args.nat_synth,
                     "n": N_SYNTH, "seed": SYNTH_SEED}}
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2))
    print(f"\nresults -> {args.out_json}")


if __name__ == "__main__":
    main()
