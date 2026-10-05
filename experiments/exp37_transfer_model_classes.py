"""Exp 37 — does the faithful-persistent + class-balanced training recipe hold
across model classes?

Hypothesis: the exp25 recipe (faithful persistent-buckets generator,
class_weight="balanced") is a property of the data, not of the model class.
If the same transfer advantage shows up for logistic regression and an MLP
as for gradient-boosted trees, the recipe generalizes; a transformer (a third
model class entirely) is then a safer bet for the LM plan.

Arms (element task, v1 features, 20k synthetic, seed 7, same real-QC eval
split as exp19/exp22/exp25: all FY2024 QC rows whose ELEMENT1 bucket appears
in the persistent baseline; test set is NEVER trained on):
  persistent pool: --max-attempts 12, persistent-buckets ON (default)
  retry pool:      --max-attempts 12, --no-persistent-buckets
  classifiers:
    (a) HistGradientBoostingClassifier(random_state=0, class_weight="balanced")
    (b) LogisticRegression(class_weight="balanced") on standardized features
    (c) MLPClassifier(hidden_layer_sizes=(100,), max_iter=300, random_state=0)
        with class_weight="balanced" emulated via sample_weight

Each classifier is trained twice: on persistent error rows and on retry-loop
error rows, and scored element accuracy + macroF1 on the real-QC eval set.
Also reports the persistent-vs-retry ranking per model class.

Usage: python3 experiments/exp37_transfer_model_classes.py [--seed 7]
Requires: scikit-learn
"""
import argparse
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import errors as errors_mod  # noqa: E402  (unused, kept for lineage)
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]

SUA_YES = {"3", "4", "5", "6", "7", "8"}


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
        "n_elderly": fnum(row["FSNELDER"]), "n_disabled": float(fnum(row["FSNDIS"])),
        "has_earned": 1.0 if earned > 0 else 0.0,
        "has_unearned": 1.0 if unearned > 0 else 0.0,
        "earned_share": earned / gross if gross > 0 else 0.0,
    }


def synth_case_features(case):
    f = case["issued_facts"]  # agency-view facts, like the caseworker saw
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


def load_real():
    rows = []
    with open(QC, newline="") as fh:
        import csv
        for row in csv.DictReader(fh):
            status = row["STATUS"].strip()
            e1 = row.get("ELEMENT1", "").strip()
            rows.append((real_row_features(row),
                         element_bucket(int(e1)) if e1 and status != "1" else None))
    return rows


def case_row(c):
    return (synth_case_features(c),
            c["variances"][0]["element_bucket"] if c["variances"] else None)


def as_Xy(rows, feats):
    X = [[r[0][k] for k in feats] for r in rows]
    y = [r[1] for r in rows]
    return X, y


def gen_synth(n, seed, persistent):
    tf = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    path = tf.name
    tf.close()
    cmd = [sys.executable, "-m", "synth.generate", "--n", str(n),
           "--seed", str(seed), "--dist", str(ROOT / "experiments/dist.json"),
           "--max-attempts", "12", "--out", path]
    if not persistent:
        cmd.append("--no-persistent-buckets")  # explicit opt-out, not default
    subprocess.run(cmd, cwd=ROOT / "src", check=True, capture_output=True)
    return path


def balanced_sample_weights(y):
    """Emulate class_weight='balanced' for estimators that lack it
    (MLPClassifier): weight_i = n / (n_classes * n_class_of_i)."""
    cnt = Counter(y)
    n = len(y)
    k = len(cnt)
    return [n / (k * cnt[c]) for c in y]


def make_clfs():
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    return {
        "gbm": HistGradientBoostingClassifier(random_state=0,
                                              class_weight="balanced"),
        "logreg": LogisticRegression(class_weight="balanced",
                                     max_iter=5000, random_state=0),
        "mlp": MLPClassifier(hidden_layer_sizes=(100,), max_iter=300,
                             random_state=0),
    }


def evaluate(name, train_rows, test_rows, feats, clf, scale, sample_w):
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.preprocessing import StandardScaler
    sX, sy = as_Xy(train_rows, feats)
    rX, ry = as_Xy(test_rows, feats)
    if scale:
        scaler = StandardScaler().fit(sX)
        sX = scaler.transform(sX)
        rX = scaler.transform(rX)
    fit_kw = {"sample_weight": balanced_sample_weights(sy)} if sample_w else {}
    clf.fit(sX, sy, **fit_kw)
    pred = clf.predict(rX)
    acc = accuracy_score(ry, pred)
    macro = f1_score(ry, pred, average="macro", zero_division=0)
    per = f1_score(ry, pred, labels=BUCKETS, average=None, zero_division=0)
    print(f"{name}: acc={acc:.3f} macroF1={macro:.3f} "
          f"(train n={len(sy)}, classes={len(set(sy))})")
    for b, f in zip(BUCKETS, per):
        print(f"    F1 {b:10s} {f:.3f}")
    print(f"    train class counts: {dict(Counter(sy))}")
    return acc, macro, dict(zip(BUCKETS, per))


def diagnose_logreg(seed, n_base):
    """Sweep C and class_weight for logreg on the persistent pool.

    Tests whether exp37's logreg/persistent collapse (acc 0.175,
    macroF1 0.158 vs retry 0.374/0.242) is a fitting artifact
    (underfit / bad convergence) or a data property (retry pool more
    linearly separable). Prints n_iter_ (convergence check) per fit.
    """
    import json
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.preprocessing import StandardScaler

    print(f"generating persistent pool ({n_base}, seed {seed})...", flush=True)
    p_path = gen_synth(n_base, seed, persistent=True)
    print(f"generating retry-loop pool ({n_base}, seed {seed})...", flush=True)
    r_path = gen_synth(n_base, seed, persistent=False)
    with open(p_path) as fh:
        cases_p = [json.loads(line) for line in fh][:n_base]
    with open(r_path) as fh:
        cases_r = [json.loads(line) for line in fh][:n_base]
    Path(p_path).unlink(missing_ok=True)
    Path(r_path).unlink(missing_ok=True)
    base_p = [case_row(c) for c in cases_p if c["variances"]]
    retry_p = [case_row(c) for c in cases_r if c["variances"]]
    real = load_real()
    keep = sorted(set(r[1] for r in base_p))
    test_rows = [r for r in real if r[1] in set(keep)]
    for pool_name, pool_rows in (("persistent", base_p), ("retry", retry_p)):
        sX, sy = as_Xy(pool_rows, V1)
        rX, ry = as_Xy(test_rows, V1)
        scaler = StandardScaler().fit(sX)
        sX, rX = scaler.transform(sX), scaler.transform(rX)
        print(f"{pool_name}: train n={len(sy)}, test n={len(ry)}", flush=True)
        for C, cw in [(0.1, "balanced"), (1.0, "balanced"), (10.0, "balanced"),
                      (100.0, "balanced"), (1.0, None)]:
            clf = LogisticRegression(C=C, class_weight=cw, max_iter=5000,
                                     random_state=0)
            clf.fit(sX, sy)
            pred = clf.predict(rX)
            acc = accuracy_score(ry, pred)
            macro = f1_score(ry, pred, average="macro", zero_division=0)
            niter = getattr(clf, "n_iter_", "?")
            niter = max(niter) if hasattr(niter, "__iter__") else niter
            print(f"  {pool_name} C={C:<6} class_weight={str(cw):>8s}: "
                  f"acc={acc:.3f} macroF1={macro:.3f} n_iter={niter}",
                  flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n-base", type=int, default=20000)
    ap.add_argument("--diagnose-logreg", action="store_true",
                    help="post-hoc: sweep logreg C / class_weight on the "
                         "persistent pool to test whether the exp37 logreg "
                         "collapse is a fitting artifact")
    args = ap.parse_args()

    if args.diagnose_logreg:
        return diagnose_logreg(args.seed, args.n_base)

    print(f"generating persistent pool ({args.n_base}, seed {args.seed})...",
          flush=True)
    p_path = gen_synth(args.n_base, args.seed, persistent=True)
    print(f"generating retry-loop pool ({args.n_base}, seed {args.seed})...",
          flush=True)
    r_path = gen_synth(args.n_base, args.seed, persistent=False)

    print("loading real QC file...", flush=True)
    real = load_real()

    print("loading pools...", flush=True)
    import json
    with open(p_path) as fh:
        cases_p = [json.loads(line) for line in fh][:args.n_base]
    with open(r_path) as fh:
        cases_r = [json.loads(line) for line in fh][:args.n_base]
    Path(p_path).unlink(missing_ok=True)
    Path(r_path).unlink(missing_ok=True)

    base_p = [case_row(c) for c in cases_p if c["variances"]]
    err_r = [case_row(c) for c in cases_r if c["variances"]]
    cnt_p = Counter(r[1] for r in base_p)
    cnt_r = Counter(r[1] for r in err_r)
    print("persistent 20k error-class counts:", dict(cnt_p))
    print("retry-loop 20k error-class counts:", dict(cnt_r))

    # replication check: must reproduce exp24/exp25 post-rebaseline seed-7
    # counts (persistent-buckets default, --max-attempts 12)
    for b, exp in [("hhcomp", 281), ("arithmetic", 166), ("sua", 669),
                   ("medical", 241)]:
        got = cnt_p.get(b, 0)
        tag = "OK" if abs(got - exp) <= 25 else "DRIFT"
        print(f"  replication {tag} on {b}: got {got}, exp24 seed-7 {exp}")

    # eval split: identical to exp9/exp19/exp22/exp25 -- real rows whose
    # ELEMENT1 bucket appears in the persistent baseline
    keep = sorted(set(cnt_p))
    test_rows = [r for r in real if r[1] in set(keep)]
    print(f"\nreal eval rows: {len(test_rows)} (of {len(real)}); "
          f"buckets: {keep}")

    # model classes; linear models get standardized features; MLP gets
    # sample_weight-emulated balanced class weights
    config = {
        "gbm": dict(scale=False, sample_w=False),
        "logreg": dict(scale=True, sample_w=False),
        "mlp": dict(scale=True, sample_w=True),
    }
    results = {}
    for mname in ("gbm", "logreg", "mlp"):
        clfs = make_clfs()
        cfg = config[mname]
        print(f"\n== {mname}: persistent pool ==")
        p_res = evaluate(f"{mname}/persistent", base_p, test_rows, V1,
                         clfs[mname], cfg["scale"], cfg["sample_w"])
        print(f"\n== {mname}: retry-loop pool ==")
        r_res = evaluate(f"{mname}/retry", err_r, test_rows, V1,
                         make_clfs()[mname], cfg["scale"], cfg["sample_w"])
        results[mname] = {"persistent": p_res, "retry": r_res}

    print("\n== summary (element accuracy / macroF1 on real FY2024 QC) ==")
    print(f"{'model':8s} {'pool':10s} {'acc':>6s} {'macroF1':>8s}")
    for m in ("gbm", "logreg", "mlp"):
        for pool in ("persistent", "retry"):
            acc, macro, _ = results[m][pool]
            print(f"{m:8s} {pool:10s} {acc:6.3f} {macro:8.3f}")

    print("\n== persistent-vs-retry ranking per model class (macroF1 delta) ==")
    for m in ("gbm", "logreg", "mlp"):
        d_acc = results[m]["persistent"][0] - results[m]["retry"][0]
        d_mac = results[m]["persistent"][1] - results[m]["retry"][1]
        winner = "persistent" if d_mac > 0 else ("retry" if d_mac < 0 else "tie")
        print(f"  {m:8s}: acc delta {d_acc:+.4f}, macroF1 delta {d_mac:+.4f} "
              f"-> {winner} wins")

    print("\n== per-bucket F1, persistent pool, by model class ==")
    print("bucket      " + "".join(f" {m:>8s}" for m in ("gbm", "logreg", "mlp")))
    for b in BUCKETS:
        print(f"{b:10s}  " + "".join(
            f" {results[m]['persistent'][2].get(b, 0.0):8.3f}"
            for m in ("gbm", "logreg", "mlp")))

    print("\n== GBM replication vs exp25 arm-(a) [v1, seed 7]: "
          "exp25 reported acc=0.481 macroF1=0.281 ==")


if __name__ == "__main__":
    main()
