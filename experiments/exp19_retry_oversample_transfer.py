"""Exp 19 — retry-loop + generation-time oversampling on the transfer gate.

Exp 9's verdict: class_weight="balanced" cannot fix class starvation. The
retry loop's transfer edge over the persistent generator (element acc
0.458 vs 0.443, macroF1 0.274 vs 0.252) comes from ~2x more DISTINCT
rare-bucket cases in its training data (hhcomp 672 vs 328, arithmetic
553 vs 238) — decision boundaries are learned from distinct examples,
not from upweighted or duplicated copies.

This experiment asks whether the edge SURVIVES when the persistent
generator explicitly oversamples rare buckets at GENERATION time (more
distinct cases, never row duplication): is the edge really about
distinct-example count, or is there something else in the retry loop's
distortion that helps?

Element task only (y_idx=3), v1 features (9 raw; exp4 v3 confirmed v1
beats v2 for element), HistGradientBoostingClassifier(random_state=0),
20k synth baseline (seed 7), same real FY2024 QC test split as exp4/exp9
(test set NEVER touched).

Arms:
  (a) persistent, unbalanced                         -- v3 reference
  (b) persistent + class_weight="balanced"            -- exp9 reference
  (c) retry-loop + class_weight="balanced"            -- exp9 headline (the bar)
  (d) persistent + row-duplication to uniform         -- exp9 reference
  (e) persistent + GENERATION-TIME oversample to match the retry loop's
      distinct per-bucket counts + balanced           -- the key test
  (f) retry-loop + GENERATION-TIME oversample to 2x those counts + balanced
  (g) persistent + GENERATION-TIME oversample to 2x those counts + balanced

Key comparisons:
  (e) vs (c): does distinct-count parity close the gap? Same distinct
      rare-bucket counts, both balanced -- if the gap survives, the retry
      loop's distortion has something beyond count.
  (g) vs (f): the same cross-generator comparison at 2x counts.
  (f) vs (c) and (g) vs (e): dose response -- do MORE distinct rare
      examples keep helping?
  (e) vs (d): distinct generation vs row duplication, same generator.

Generation-time oversampling: generate a 100k-case pool per generator
(seed 7, so the first 20k rows are exactly the exp9 baselines), then
extend each rare bucket with distinct extra cases from the remainder of
the pool until it reaches the target count. No row is ever duplicated.

Calibration: finding-mix L1 (correct/over/under) for the four generator
pools vs the real finding mix; element-mix and direction-mix L1 for the
oversampled training subsets vs the real mixes -- what the oversampling
costs in fidelity.

Usage: python3 experiments/exp19_retry_oversample_transfer.py
Requires: scikit-learn
"""
import argparse
import csv
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QC = Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]

# Rare buckets that get generation-time oversampling (exp9's list).
RARE = ["hhcomp", "depcare", "sua", "arithmetic", "medical"]

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
        "n_elderly": fnum(row["FSNELDER"]), "n_disabled": fnum(row["FSNDIS"]),
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
        for row in csv.DictReader(fh):
            status = row["STATUS"].strip()
            e1 = row.get("ELEMENT1", "").strip()
            rows.append((real_row_features(row),
                         0 if status == "1" else 1,
                         int(status),
                         element_bucket(int(e1)) if e1 and status != "1" else None))
    return rows


def load_synth(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            rows.append((synth_case_features(c),
                         0 if c["finding"] == 1 else 1,
                         c["finding"],
                         c["variances"][0]["element_bucket"] if c["variances"] else None))
    return rows


def as_Xy(rows, feats, y_idx):
    X = [[r[0][k] for k in feats] for r in rows]
    y = [r[y_idx] for r in rows]
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


def oversample_uniform(X, y, random_state=0):
    """Resample each present class (with replacement) up to the max
    class count, so rare buckets are no longer starved."""
    from sklearn.utils import resample
    from collections import Counter
    counts = Counter(y)
    target = max(counts.values())
    Xn, yn = [], []
    for cls in sorted(counts):
        idx = [i for i, v in enumerate(y) if v == cls]
        Xi = [X[i] for i in idx]
        ni = len(idx)
        if ni < target:
            Xi, yi = resample([Xi[i] for i in range(ni)], [cls] * ni,
                              replace=True, n_samples=target,
                              random_state=random_state)
        else:
            yi = [cls] * ni
        Xn.extend(Xi)
        yn.extend(yi)
    return Xn, yn


def build_gen_oversampled(base_rows, extra_rows, targets, rare, mult):
    """Extend each rare bucket with DISTINCT extra generated cases until it
    reaches mult * targets[b]. base_rows and extra_rows are disjoint slices
    of one seeded pool, so no case is ever duplicated.

    Returns (rows, need, short): the training rows, the requested
    additions, and any bucket where the pool ran out of distinct cases.
    """
    counts = Counter(r[3] for r in base_rows)
    need = {b: max(0, int(round(mult * targets[b])) - counts.get(b, 0))
            for b in rare}
    by_bucket = {}
    for r in extra_rows:
        if r[3] in rare:
            by_bucket.setdefault(r[3], []).append(r)
    added, short = [], {}
    for b, n in need.items():
        avail = by_bucket.get(b, [])
        take = min(n, len(avail))
        added.extend(avail[:take])
        if take < n:
            short[b] = (n, take)
    return base_rows + added, need, short


def evaluate(name, s_rows, r_rows, feats, class_weight=None, oversample=False):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score
    sX, sy = as_Xy(s_rows, feats, 3)
    rX, ry = as_Xy(r_rows, feats, 3)
    train_n = len(sX)
    if oversample:
        sX, sy = oversample_uniform(sX, sy)
    clf = HistGradientBoostingClassifier(random_state=0,
                                         class_weight=class_weight).fit(sX, sy)
    pred = clf.predict(rX)
    acc = accuracy_score(ry, pred)
    macro = f1_score(ry, pred, average="macro", zero_division=0)
    per = f1_score(ry, pred, labels=BUCKETS, average=None, zero_division=0)
    train_counts = dict(Counter(sy))
    print(f"{name}: acc={acc:.3f} macroF1={macro:.3f} "
          f"(train n={train_n}->{len(sy)}, classes={len(train_counts)})")
    for b, f in zip(BUCKETS, per):
        print(f"    F1 {b:10s} {f:.3f}")
    print(f"    train class counts: {train_counts}")
    return acc, macro, dict(zip(BUCKETS, per))


# ---- calibration helpers (mix L1 readings) ----
def finding_mix(rows):
    c = Counter(r[2] for r in rows)
    n = sum(c.values()) or 1
    return {k: c.get(k, 0) / n for k in (1, 2, 3)}


def element_mix(rows):
    c = Counter(r[3] for r in rows if r[3] in BUCKETS)
    n = sum(c.values()) or 1
    return {b: c.get(b, 0) / n for b in BUCKETS}


def direction_mix(rows):
    errs = [r for r in rows if r[2] in (2, 3)]
    n = len(errs) or 1
    return {2: sum(1 for r in errs if r[2] == 2) / n,
            3: sum(1 for r in errs if r[2] == 3) / n}


def l1(a, b):
    return sum(abs(a[k] - b.get(k, 0.0)) for k in a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-pool", type=int, default=100000,
                    help="cases generated per generator pool")
    ap.add_argument("--n-base", type=int, default=20000,
                    help="baseline slice size (first n rows of each pool)")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    print(f"generating pools ({args.n_pool} persistent + {args.n_pool} "
          f"retry-loop, seed {args.seed})...", flush=True)
    p_path = gen_synth(args.n_pool, args.seed, persistent=True)
    r_path = gen_synth(args.n_pool, args.seed, persistent=False)

    print("loading real QC file...", flush=True)
    real = load_real()

    print("loading persistent pool...", flush=True)
    rows_p_all = load_synth(p_path)
    base_p = [r for r in rows_p_all[:args.n_base] if r[3]]
    extra_p = [r for r in rows_p_all[args.n_base:] if r[3]]
    mix_p_20k = finding_mix(rows_p_all[:args.n_base])
    mix_p_pool = finding_mix(rows_p_all)
    del rows_p_all

    print("loading retry-loop pool...", flush=True)
    rows_r_all = load_synth(r_path)
    base_r = [r for r in rows_r_all[:args.n_base] if r[3]]
    extra_r = [r for r in rows_r_all[args.n_base:] if r[3]]
    mix_r_20k = finding_mix(rows_r_all[:args.n_base])
    mix_r_pool = finding_mix(rows_r_all)
    del rows_r_all

    cnt_p = Counter(r[3] for r in base_p)
    cnt_r = Counter(r[3] for r in base_r)
    print("baseline 20k class counts (persistent):", dict(cnt_p))
    print("baseline 20k class counts (retry-loop):", dict(cnt_r))
    # exp9 replication check: same seed and command must reproduce its counts
    for b, ep, er in [("hhcomp", 328, 672), ("arithmetic", 238, 553),
                      ("medical", 47, 57), ("depcare", 4, 2)]:
        if cnt_p.get(b) != ep or cnt_r.get(b) != er:
            print(f"WARNING: replication drift on {b}: persistent "
                  f"{cnt_p.get(b)} (exp9 {ep}), retry {cnt_r.get(b)} (exp9 {er})")

    targets = {b: max(cnt_p.get(b, 0), cnt_r.get(b, 0)) for b in RARE}
    print("generation-time oversample targets (retry-loop distinct counts):",
          targets)

    # (e) persistent matched to retry-loop counts; (f)/(g) doubled counts
    e_rows, need_e, short_e = build_gen_oversampled(base_p, extra_p, targets, RARE, 1)
    g_rows, need_g, short_g = build_gen_oversampled(base_p, extra_p, targets, RARE, 2)
    f_rows, need_f, short_f = build_gen_oversampled(base_r, extra_r, targets, RARE, 2)
    for name, need, short in [("e", need_e, short_e), ("g", need_g, short_g),
                              ("f", need_f, short_f)]:
        print(f"({name}) distinct extras requested: {need}")
        if short:
            print(f"    WARNING: pool ran short: {short}")

    # test split: identical to exp9 (buckets present in the persistent baseline)
    keep = sorted(set(cnt_p))
    r_rows = [r for r in real if r[3] in set(keep)]
    print(f"real test rows: {len(r_rows)} (of {len(real)})")

    results = {}
    print("\n== (a) persistent + unbalanced [v1] (exp9: 0.442/0.214) ==")
    results["a"] = evaluate("a", base_p, r_rows, V1)
    print("\n== (b) persistent + class_weight=balanced [v1] (exp9: 0.443/0.252) ==")
    results["b"] = evaluate("b", base_p, r_rows, V1, class_weight="balanced")
    print("\n== (c) retry-loop + class_weight=balanced [v1] (exp9: 0.458/0.274) ==")
    results["c"] = evaluate("c", base_r, r_rows, V1, class_weight="balanced")
    print("\n== (d) persistent + row-duplication oversample-to-uniform [v1] (exp9: 0.430/0.262) ==")
    results["d"] = evaluate("d", base_p, r_rows, V1, oversample=True)
    print("\n== (e) persistent + GENERATION-TIME oversample to retry counts + balanced [v1] ==")
    results["e"] = evaluate("e", e_rows, r_rows, V1, class_weight="balanced")
    print("\n== (f) retry-loop + GENERATION-TIME oversample to 2x retry counts + balanced [v1] ==")
    results["f"] = evaluate("f", f_rows, r_rows, V1, class_weight="balanced")
    print("\n== (g) persistent + GENERATION-TIME oversample to 2x retry counts + balanced [v1] ==")
    results["g"] = evaluate("g", g_rows, r_rows, V1, class_weight="balanced")

    print("\n== summary ==")
    for k, (acc, macro, per) in results.items():
        print(f"  ({k}) acc={acc:.3f} macroF1={macro:.3f}")

    print("\n== per-bucket F1 across arms ==")
    hdr = "bucket     " + "".join(f"  ({k})" for k in results)
    print(hdr)
    for b in BUCKETS:
        print(f"{b:10s} " + "".join(f" {results[k][2][b]:.3f}" for k in results))

    # ---- calibration: what does the oversampling cost in fidelity? ----
    print("\n== calibration readings ==")
    real_finding = finding_mix(real)
    print(f"real finding mix (correct/over/under): "
          f"{real_finding[1]:.3f}/{real_finding[2]:.3f}/{real_finding[3]:.3f}")
    for name, m in [(f"persistent {args.n_base//1000}k", mix_p_20k),
                    (f"retry {args.n_base//1000}k", mix_r_20k),
                    (f"persistent {args.n_pool//1000}k pool", mix_p_pool),
                    (f"retry {args.n_pool//1000}k pool", mix_r_pool)]:
        print(f"  finding-mix L1 {name}: {l1(m, real_finding):.3f} "
              f"({m[1]:.3f}/{m[2]:.3f}/{m[3]:.3f})")
    real_elem = element_mix(r_rows)
    real_dir = direction_mix(real)
    print(f"real direction mix | error (over/under): {real_dir[2]:.3f}/{real_dir[3]:.3f}")
    subsets = [(f"a/b (persist {args.n_base//1000}k err rows)", base_p),
               (f"c (retry {args.n_base//1000}k err rows)", base_r),
               ("e (persist, gen-oversampled 1x)", e_rows),
               ("f (retry, gen-oversampled 2x)", f_rows),
               ("g (persist, gen-oversampled 2x)", g_rows)]
    for name, rows in subsets:
        print(f"  training-subset {name}: element-mix L1={l1(element_mix(rows), real_elem):.3f} "
              f"direction-mix L1={l1(direction_mix(rows), real_dir):.3f}")

    Path(p_path).unlink(missing_ok=True)
    Path(r_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
