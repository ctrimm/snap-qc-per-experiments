"""Exp 25 — re-derive the classifier-training recipe on the faithful generator.

Exp24 adopted the draw fix + re-measured materialization matrix as generator
defaults: calibration strictly better (finding L1 0.036 -> 0.025), but element
macroF1 dropped 0.007-0.031 because the faithful mix has ~35% fewer distinct
rare-bucket training examples (hhcomp 420 -> ~276, arithmetic 262 -> ~164).
The calibration win and the macroF1 loss are the same event, and macroF1 is
count-driven (exp9/exp19). Doctrine going in: keep the GENERATOR faithful (the
data product), fix the TRAINING recipe.

Hypothesis: on the faithful post-exp24 generator, generation-time rare-bucket
oversampling for the TRAINING mix only, optionally combined with hard-household
selection (a retry-style materialization screen selecting harder households),
recovers the lost macroF1 -- without reintroducing distortion into the
generator or the data product.

Arms (element task, v1 features, HistGradientBoostingClassifier(random_state=0),
class_weight="balanced" everywhere, same real FY2024 QC test split as
exp19/exp22 -- the test set is NEVER touched):
  (a) faithful persistent 20k + balanced            -- new baseline
  (b) (a) + generation-time rare-bucket extras (boosted rare-bucket draw,
      distinct cases, training mix only) + balanced
  (c) persistent injection on retry-selected households (exp22 arm-(j)
      pattern: retry-style materialization screen) + balanced
  (d) (c) rows + (b) extras + balanced              -- combined

Also verified: the unsampled 20k data-product pool still calibrates
(finding L1 ~= 0.025) -- the training recipe must not distort the product.

Generation-time oversampling here means generating EXTRA distinct cases with
a boosted rare-bucket draw (in-process dist copy; the generator's own files
and defaults are untouched), never row duplication, never touching the
product pool. Targets: restore each rare bucket to its pre-exp24 persistent
20k distinct count -- exactly the examples the calibration win cost.

Usage: python3 experiments/exp25_training_recipe.py [--seed 7]
Requires: scikit-learn
"""
import argparse
import copy
import csv
import json
import random
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import errors as errors_mod  # noqa: E402
from synth import household as household_mod  # noqa: E402
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]

# Rare buckets that get generation-time oversampling (exp19's list).
RARE = ["hhcomp", "depcare", "sua", "arithmetic", "medical"]

# Pre-exp24 persistent 20k distinct error counts (exp22 replication check;
# sua from exp19): the examples the draw fix removed. Restoring exactly
# these is the "recover what was lost" test.
TARGETS = {"hhcomp": 420, "arithmetic": 262, "medical": 310,
           "depcare": 72, "sua": 781}

BOOST = 4.0  # rare-bucket draw-weight multiplier for the extras run

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
        for row in csv.DictReader(fh):
            status = row["STATUS"].strip()
            e1 = row.get("ELEMENT1", "").strip()
            rows.append((real_row_features(row),
                         0 if status == "1" else 1,
                         int(status),
                         element_bucket(int(e1)) if e1 and status != "1" else None))
    return rows


def load_synth_cases(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh]


def case_row(c):
    return (synth_case_features(c),
            0 if c["finding"] == 1 else 1,
            c["finding"],
            c["variances"][0]["element_bucket"] if c["variances"] else None)


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


def evaluate(name, s_rows, r_rows, feats, class_weight="balanced"):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score
    sX, sy = as_Xy(s_rows, feats, 3)
    rX, ry = as_Xy(r_rows, feats, 3)
    clf = HistGradientBoostingClassifier(random_state=0,
                                         class_weight=class_weight).fit(sX, sy)
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


# ---- calibration helpers (mix L1 readings) ----
def finding_mix(rows):
    c = Counter(r[2] for r in rows)
    n = sum(c.values()) or 1
    return {k: c.get(k, 0) / n for k in (1, 2, 3)}


def element_mix(rows):
    c = Counter(r[3] for r in rows if r[3] in BUCKETS)
    n = sum(c.values()) or 1
    return {b: c.get(b, 0) / n for b in BUCKETS}


def l1(a, b):
    return sum(abs(a[k] - b.get(k, 0.0)) for k in a)


# ---- arm (b): boosted-draw rare-bucket extras (training mix only) ----
def boosted_dist(dist, boost, rare):
    """In-process copy of dist with rare-bucket draw weights scaled by
    `boost` in every bucket_probs* mix. The generator's files and defaults
    are untouched; the materialization machinery (matrix, nature mixes,
    phase-1 coins) is unchanged -- only the draw marginal moves, and only
    for the extras run."""
    d2 = copy.deepcopy(dist)
    for key in list(d2):
        if key.startswith("bucket_probs") and isinstance(d2[key], dict):
            for b in rare:
                if b in d2[key]:
                    d2[key][b] = d2[key][b] * boost
    return d2


def gen_boosted_extras(dist, seed, have_counts, targets, rare, boost,
                       budget):
    """Generate distinct extra error cases with the boosted rare-bucket
    draw until each rare bucket reaches targets[b]. Households come from a
    fresh rng stream, so extras are disjoint from the base pool. Returns
    (extras, need_left): fail-soft if the budget exhausts first."""
    d2 = boosted_dist(dist, boost, rare)
    rng = random.Random(seed)
    need = {b: max(0, targets[b] - have_counts.get(b, 0)) for b in rare}
    extras = []
    drawn = 0
    while drawn < budget and any(n > 0 for n in need.values()):
        drawn += 1
        facts = household_mod.sample_household(rng)
        case = errors_mod.inject(facts, rng, d2, max_attempts=12,
                                 persistent_buckets=True)
        if case["variances"]:
            b = case["variances"][0]["element_bucket"]
            if b in need and need[b] > 0:
                need[b] -= 1
                extras.append(case)
    short = {b: n for b, n in need.items() if n > 0}
    return extras, short, drawn


# ---- arm (c): persistent injection on retry-selected households ----
def build_dist_coin(dist):
    """dist copy with the shared phase-1 injection coin forced on, so only
    the materialization screen differentiates the arms (exp22's pattern)."""
    d2 = copy.deepcopy(dist)
    d2.get("injection_rate", {})["persistent"] = {"earner": 1.0,
                                                  "no_earner": 1.0}
    return d2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n-base", type=int, default=20000)
    ap.add_argument("--boost", type=float, default=BOOST)
    ap.add_argument("--extra-budget", type=int, default=300000,
                    help="max households drawn for the boosted extras run")
    ap.add_argument("--extra-seed", type=int, default=999,
                    help="rng seed for the boosted extras household stream")
    args = ap.parse_args()

    dist = load_dist(ROOT / "experiments/dist.json")

    print(f"generating faithful persistent pool ({args.n_base}, seed "
          f"{args.seed})...", flush=True)
    p_path = gen_synth(args.n_base, args.seed, persistent=True)
    print(f"generating retry-loop pool ({args.n_base}, seed {args.seed})...",
          flush=True)
    r_path = gen_synth(args.n_base, args.seed, persistent=False)

    print("loading real QC file...", flush=True)
    real = load_real()

    print("loading pools...", flush=True)
    cases_p = load_synth_cases(p_path)[:args.n_base]
    cases_r = load_synth_cases(r_path)[:args.n_base]
    Path(p_path).unlink(missing_ok=True)
    Path(r_path).unlink(missing_ok=True)

    # (a) base: faithful persistent error rows (also the data-product pool's
    # error rows; the product pool itself is the full 20k, unsampled).
    base_p = [case_row(c) for c in cases_p if c["variances"]]
    err_r = [c for c in cases_r if c["variances"]]

    cnt_p = Counter(r[3] for r in base_p)
    cnt_r = Counter(c["variances"][0]["element_bucket"] for c in err_r)
    print("faithful 20k error-class counts (persistent):", dict(cnt_p))
    print("faithful 20k error-class counts (retry-loop):", dict(cnt_r))
    # replication checks against exp24's post-rebaseline numbers (seed 7)
    for b, exp in [("hhcomp", 281), ("arithmetic", 166), ("sua", 669),
                   ("medical", 241)]:
        got = cnt_p.get(b, 0)
        if abs(got - exp) > 25:
            print(f"WARNING: replication drift on {b}: got {got}, "
                  f"exp24 seed-7 {exp}")
        else:
            print(f"  replication OK on {b}: {got} (exp24 seed-7 {exp})")

    # ---- (b) extras: boosted-draw rare-bucket cases, training mix only ----
    print(f"\ngenerating boosted-draw extras (boost={args.boost}, targets="
          f"{TARGETS})...", flush=True)
    extras, short, drawn = gen_boosted_extras(
        dist, args.extra_seed, cnt_p, TARGETS, RARE, args.boost,
        args.extra_budget)
    extra_rows = [case_row(c) for c in extras]
    print(f"  drew {drawn} households -> {len(extra_rows)} rare-bucket extras: "
          f"{dict(Counter(r[3] for r in extra_rows))}")
    if short:
        print(f"  WARNING: budget exhausted, still short: {short}")
    else:
        print("  all rare-bucket targets met")
    b_rows = base_p + extra_rows
    print(f"  (b) training rows: {len(b_rows)} "
          f"({dict(Counter(r[3] for r in b_rows))})")

    # ---- (c): persistent injection on retry-selected households ----
    # exp22's arm-(j) pattern on the current generator: the retry loop's
    # redraw-until-materialize screen selects "hard" households; run the
    # persistent generator on exactly those households (shared phase-1 coin
    # forced on) and keep the ones that yield a persistent error.
    dist_coin = build_dist_coin(dist)
    j_cases = []
    for idx, c in enumerate(err_r):
        cj = errors_mod.inject(copy.deepcopy(c["facts"]),
                               random.Random(71000 + idx), dist_coin,
                               max_attempts=12, persistent_buckets=True)
        if cj["variances"]:
            j_cases.append(cj)
    j_rows = [case_row(c) for c in j_cases]
    print(f"\n(c) persistent on retry-selected households: {len(j_rows)} rows "
          f"({len(j_rows) / max(len(err_r), 1):.2f} of retry error households "
          f"yielded a persistent error)")
    print(f"    class counts: {dict(Counter(r[3] for r in j_rows))}")

    # ---- (d): (c) rows + (b) extras (disjoint: different household streams)
    d_rows = j_rows + extra_rows
    print(f"(d) combined training rows: {len(d_rows)}")

    # test split: identical to exp9/exp19/exp22 (buckets in the persistent
    # baseline)
    keep = sorted(set(cnt_p))
    r_rows = [r for r in real if r[3] in set(keep)]
    print(f"\nreal test rows: {len(r_rows)} (of {len(real)})")

    results = {}
    print("\n== (a) faithful persistent + balanced [v1] "
          "(exp24 after-(b) seed7: 0.481/0.281) ==")
    results["a"] = evaluate("a", base_p, r_rows, V1)
    print("\n== (b) faithful + boosted-draw rare extras + balanced [v1] ==")
    results["b"] = evaluate("b", b_rows, r_rows, V1)
    print("\n== (c) persistent on retry-selected households + balanced [v1] ==")
    results["c"] = evaluate("c", j_rows, r_rows, V1)
    print("\n== (d) (c) + boosted extras + balanced [v1] ==")
    results["d"] = evaluate("d", d_rows, r_rows, V1)

    print("\n== summary ==")
    for k, (acc, macro, per) in results.items():
        print(f"  ({k}) acc={acc:.3f} macroF1={macro:.3f}")

    print("\n== per-bucket F1 across arms (rare buckets marked *) ==")
    print("bucket      " + "".join(f"   ({k}) " for k in results))
    for b in BUCKETS:
        mark = "*" if b in RARE else " "
        print(f"{b:10s}{mark} " + "".join(f" {results[k][2][b]:.3f}" for k in results))

    print("\n== arm deltas vs (a), macroF1 ==")
    for k in ("b", "c", "d"):
        d = results[k][1] - results["a"][1]
        print(f"  ({k})-(a): {d:+.4f}")

    # ---- product-pool calibration: the unsampled 20k must stay faithful ----
    # Per-case element ratios use exp24's definition: ALL recorded variances
    # (ELEMENT1..ELEMENT9 on the real side, every variances[] entry on the
    # synth side) per case -- not just the first variance.
    print("\n== product-pool calibration (unsampled faithful 20k) ==")
    pool_rows = [case_row(c) for c in cases_p]  # includes clean cases
    real_finding = finding_mix(real)
    pool_finding = finding_mix(pool_rows)
    print(f"  real finding mix (correct/over/under): "
          f"{real_finding[1]:.3f}/{real_finding[2]:.3f}/{real_finding[3]:.3f}")
    print(f"  pool finding mix (correct/over/under): "
          f"{pool_finding[1]:.3f}/{pool_finding[2]:.3f}/{pool_finding[3]:.3f}")
    print(f"  finding-mix L1: {l1(pool_finding, real_finding):.3f} "
          f"(exp24 after-persist: 0.025)")
    pool_pc = Counter()
    for c in cases_p:
        for v in c["variances"]:
            if v["element_bucket"] in BUCKETS:
                pool_pc[v["element_bucket"]] += 1
    real_pc = Counter()
    n_real = 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            n_real += 1
            for i in range(1, 10):
                e = (row[f"ELEMENT{i}"] or "").strip()
                if e:
                    b = element_bucket(int(e))
                    if b in BUCKETS:
                        real_pc[b] += 1
    print("  per-case element ratios, all variances (1.0x = matches real):")
    for b in BUCKETS:
        ratio = ((pool_pc[b] / len(cases_p)) / (real_pc[b] / n_real)
                 if real_pc[b] else 0.0)
        print(f"    {b:10s} {ratio:.2f}x")


if __name__ == "__main__":
    main()
