"""Experiment 24: adopt the exp21 draw fix + re-measured materialization
matrix as generator defaults, and re-baseline both gates.

North-star gates: calibration AND transfer. Exp21 showed removing
earned/unearned/shelter from ZERO_BASE_WEIGHT plus the re-measured
per-(bucket,stratum) materialization matrix gives finding L1 0.025 (from
0.036); the stale exp20 matrix must NOT be reused (keep rates were
re-measured on the corrected draw).

Hypothesis: adopting the draw fix (delete the three ZERO_BASE_WEIGHT
entries, exp11 precedent) and the re-measured matrix as generator
defaults establishes a new, strictly better baseline on both the
calibration gate (finding mix L1, element ratios, cause mix, dollar
marginals) and the transfer gate (exp19's battery: element
accuracy/macroF1, persistent + balanced arm and one retry-loop arm).

Generator changes (already applied, verified below):
  src/synth/errors.py
    - ZERO_BASE_WEIGHT = {} (three entries deleted)
    - MATERIALIZATION_MATRIX: re-measured keep rates, exp20 guardrails
      (damp 0.8, mechanics-gap fallback < 0.10, 2.5x trust cap)
    - _inject_persistent: matrix by default; legacy_materialization=True
      restores the old scalar 1/eff_b path
    - inject(): legacy_materialization plumbed through; retry loop keeps
      its scalar correction either way (matrix measured in persistent flow)
  src/synth/generate.py
    - --legacy-materialization flag (default off)

Method (all in-process; only this script and its chronicle are written;
no commit):
  [0] SANITY: re-measure keep rates under the corrected draw (60k,
      seed 11, exp21's procedure) and assert the hard-coded
      MATERIALIZATION_MATRIX matches exactly.
  [1] BEFORE: 20k cases, seed 7, pre-change defaults reproduced
      in-process (old ZERO_BASE_WEIGHT restored + legacy scalar path),
      persistent and retry-loop (--no-persistent-buckets equivalent).
  [2] AFTER: 20k cases, seed 7, new generator defaults, persistent and
      retry-loop. Paired rng streams (same seeds -> same households).
  [3] CALIBRATION: finding mix L1, per-case element ratios + share ratios,
      nature-57 share, coarse cause mix (exp15's mapping), dollar
      marginals (exp18's stats). Real QC aggregates read from the held-out
      file, aggregate-only; never written to the repo.
  [4] TRANSFER: exp19's battery arms (a) persistent unbalanced,
      (b) persistent + class_weight="balanced", (c) retry-loop + balanced
      -- on BEFORE and AFTER. Element task, v1 features,
      HistGradientBoostingClassifier(random_state=0), same real FY2024 QC
      test split as exp4/exp9/exp19 (test set never touched).

Usage: python3 experiments/exp24_adopt_rebaseline.py
Requires: scikit-learn
"""
import csv
import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import errors, household  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

QC = Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

BUCKETS = ["earned", "unearned", "shelter", "sua", "medical", "depcare",
           "hhcomp", "arithmetic"]
STRATA = ["no_earner_nonsenior", "earner_nonsenior",
          "no_earner_senior", "earner_senior"]
N = 20000
SEED = 7

# Pre-change defaults, restored in-process for the BEFORE arms.
OLD_ZBW = {"earned": 0.018, "unearned": 0.091, "shelter": 0.227}

# exp15's coarse cause mapping.
AGENCY_CAUSE = {10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25}
CLIENT_CAUSE = {1, 2, 3, 4}


def coarse_cause(code):
    if code is None:
        return "unknown"
    if code in AGENCY_CAUSE:
        return "agency"
    if code in CLIENT_CAUSE:
        return "client"
    return "other"


def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


# ---------------- real aggregates (held-out; aggregate-only) ----------------

def real_aggregates():
    finding = Counter()
    bucket = Counter()
    per_case = Counter()
    n57 = 0
    cause = Counter()
    dollar_all, dollar_over, dollar_under = [], [], []
    n = 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            st = int(row["STATUS"])
            finding[st] += 1
            amt = fnum(row["AMTERR"])
            if st == 1:
                pass
            else:
                dollar_all.append(amt)
                (dollar_over if st == 2 else dollar_under).append(amt)
            for i in range(1, 10):
                e = (row[f"ELEMENT{i}"] or "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                bucket[b] += 1
                per_case[b] += 1
                ntr = (row[f"NATURE{i}"] or "").strip()
                if ntr == "57":
                    n57 += 1
                cau = (row[f"AGENCY{i}"] or "").strip()
                cause[coarse_cause(int(cau) if cau else None)] += 1
    v = sum(bucket.values())
    vc = sum(cause.values())
    return {
        "finding": {k: finding[k] / n for k in (1, 2, 3)},
        "elem_share": {b: bucket[b] / v for b in BUCKETS},
        "per_case": {b: per_case[b] / n for b in BUCKETS},
        "n57": n57 / v,
        "cause": {k: cause[k] / vc for k in
                  ("agency", "client", "other", "unknown")},
        "cause_known": {k: cause[k] / (vc - cause["unknown"]) for k in
                        ("agency", "client", "other")},
        "d_all": dollar_all, "d_over": dollar_over, "d_under": dollar_under,
        "n": n,
    }


def dollar_stats(vals):
    q = statistics.quantiles(vals, n=100) if len(vals) > 100 else []
    get = lambda p: (q[p - 1] if q else
                     sorted(vals)[min(len(vals) - 1, int(p / 100 * len(vals)))])
    return {"n": len(vals), "mean": statistics.fmean(vals),
            "p10": get(10), "p25": get(25), "p50": get(50),
            "p90": get(90), "p99": get(99),
            "le56": sum(1 for x in vals if x <= 56) / len(vals)}


# ---------------- generation ----------------

def gen_cases(n, seed, dist, persistent=True, legacy=False, zbw=None):
    """Replicates generate.py's loop; zbw swaps ZERO_BASE_WEIGHT in-process
    (restored afterwards); legacy toggles the old scalar correction."""
    old = errors.ZERO_BASE_WEIGHT
    if zbw is not None:
        errors.ZERO_BASE_WEIGHT = zbw
    rng = random.Random(seed)
    try:
        return [errors.inject(household.sample_household(rng), rng, dist,
                              max_attempts=12,
                              persistent_buckets=persistent,
                              legacy_materialization=legacy)
                for _ in range(n)]
    finally:
        errors.ZERO_BASE_WEIGHT = old


def mixes(cases):
    f = Counter(c["finding"] for c in cases)
    n = len(cases)
    b = Counter()
    n57 = 0
    cause = Counter()
    d_all, d_over, d_under = [], [], []
    for c in cases:
        if c["finding"] == 2:
            d_over.append(c["dollar_error"])
        elif c["finding"] == 3:
            d_under.append(c["dollar_error"])
        if c["variances"]:
            d_all.append(c["dollar_error"])
        for v in c["variances"]:
            b[v["element_bucket"]] += 1
            if v["nature"] == 57:
                n57 += 1
            cause[coarse_cause(v["cause"])] += 1
    v = sum(b.values())
    vc = sum(cause.values())
    return {
        "finding": {k: f[k] / n for k in (1, 2, 3)},
        "elem_share": {k: b[k] / v for k in BUCKETS},
        "per_case": {k: b[k] / n for k in BUCKETS},
        "n57": n57 / v if v else 0,
        "cause": {k: cause[k] / vc for k in
                  ("agency", "client", "other", "unknown")},
        "cause_known": {k: cause[k] / (vc - cause["unknown"]) for k in
                        ("agency", "client", "other")},
        "d_all": d_all, "d_over": d_over, "d_under": d_under,
    }


def l1(a, b):
    return sum(abs(a[k] - b.get(k, 0.0)) for k in a)


# ---------------- keep-rate measurement (exp21 procedure) ----------------

_ORIG_IP = errors._inject_persistent
_REC_DRAWN = Counter()
_RECORDED = Counter()


def _kr_measuring_ip(facts, rng, dist, applicable, dir_w, max_attempts,
                     stats=None, **kwargs):
    s = errors._stratum_key(facts)
    local = {"drawn": Counter(), "recorded": Counter()}
    # legacy_materialization=True: exp21's exact measurement setup (the
    # scalar-weighted draw). The keep rate P(materialize | drawn) is
    # weight-invariant in expectation, but the drawn *sample* (and the rng
    # stream) differs under the matrix weights, so the hard-coded matrix
    # must be checked against the scalar-draw measurement, not a new one.
    out = _ORIG_IP(facts, rng, dist, applicable, dir_w, max_attempts,
                   stats=local, legacy_materialization=True)
    for b, c in local["drawn"].items():
        _REC_DRAWN[(b, s)] += c
    for b, c in local["recorded"].items():
        _RECORDED[(b, s)] += c
    return out


def measure_matrix(dist):
    """Keep rates under the corrected draw (exp21 step [5] procedure):
    60k cases, seed 11, scalar-draw (legacy) measurement, clipped to
    [0.02, 1.0]. Must match MATERIALIZATION_MATRIX exactly."""
    eff_b = (dist.get("effectiveness") or {}).get("bucket", {})
    _REC_DRAWN.clear()
    _RECORDED.clear()
    old = errors.ZERO_BASE_WEIGHT
    errors.ZERO_BASE_WEIGHT = {}
    errors._inject_persistent = _kr_measuring_ip
    try:
        gen_cases(60000, 11, dist)
    finally:
        errors._inject_persistent = _ORIG_IP
        errors.ZERO_BASE_WEIGHT = old
    return {b: {s: min(1.0, max(0.02,
                _RECORDED[(b, s)] / _REC_DRAWN[(b, s)]
                if _REC_DRAWN[(b, s)] else eff_b.get(b, 1.0)))
                for s in STRATA} for b in BUCKETS}


# ---------------- transfer battery (exp19) ----------------

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]
EVAL_BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
                "hhcomp", "arithmetic", "depcare"]
SUA_YES = {"3", "4", "5", "6", "7", "8"}

sys.path.insert(0, str(ROOT / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import params  # noqa: E402


def synth_case_features(case):
    f = case["issued_facts"]
    calc = benefit_mod.compute(f)
    size = f["hh_size"]
    mallot = params.max_allotment(size)
    issued = float(case["issued_benefit"])
    gross = calc["gross"]
    return {"hh_size": float(size), "earned": f["earned"],
            "unearned": f["unearned"], "shelter": f["shelter"],
            "sua": float(f["sua"]), "medical_exp": f["medical_exp"],
            "depcare": f["depcare"],
            "senior_disabled": float(f["senior_disabled"]),
            "issued_benefit": issued}


def real_row_features(row):
    size = int(fnum(row["CERTHHSZ"]))
    earned = fnum(row["FSEARN"])
    return {"hh_size": float(size), "earned": earned,
            "unearned": fnum(row["FSUNEARN"]), "shelter": fnum(row["SHELDED"]),
            "sua": 1.0 if row["SUA1"].strip() in SUA_YES else 0.0,
            "medical_exp": fnum(row["FSMEDEXP"]),
            "depcare": fnum(row["FSDEPDED"]),
            "senior_disabled": 1.0 if (fnum(row["FSNELDER"]) > 0 or
                                       fnum(row["FSNDIS"]) > 0) else 0.0,
            "issued_benefit": fnum(row["RAWBEN"])}


def load_real():
    rows = []
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            status = row["STATUS"].strip()
            e1 = row.get("ELEMENT1", "").strip()
            rows.append((real_row_features(row),
                         element_bucket(int(e1))
                         if e1 and status != "1" else None))
    return rows


def synth_rows(cases):
    return [(synth_case_features(c),
             c["variances"][0]["element_bucket"] if c["variances"] else None)
            for c in cases]


def evaluate(name, s_rows, r_rows, class_weight=None):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score
    sX = [[r[0][k] for k in V1] for r in s_rows]
    sy = [r[1] for r in s_rows]
    rX = [[r[0][k] for k in V1] for r in r_rows]
    ry = [r[1] for r in r_rows]
    clf = HistGradientBoostingClassifier(
        random_state=0, class_weight=class_weight).fit(sX, sy)
    pred = clf.predict(rX)
    acc = accuracy_score(ry, pred)
    macro = f1_score(ry, pred, average="macro", zero_division=0)
    per = f1_score(ry, pred, labels=EVAL_BUCKETS, average=None,
                   zero_division=0)
    print(f"{name}: acc={acc:.3f} macroF1={macro:.3f} "
          f"(train n={len(sX)}, classes={len(set(sy))})")
    for b, f in zip(EVAL_BUCKETS, per):
        print(f"    F1 {b:10s} {f:.3f}")
    return acc, macro, dict(zip(EVAL_BUCKETS, per))


# ---------------- main ----------------

def main():
    dist = load_dist(ROOT / "experiments/dist.json")
    assert errors.ZERO_BASE_WEIGHT == {}, \
        "exp24 expects the adopted default ZERO_BASE_WEIGHT == {}"

    print("[0] SANITY: re-measuring keep rates under the corrected draw "
          "(60k, seed 11)...", flush=True)
    fresh = measure_matrix(dist)
    worst = max(abs(fresh[b][s] - errors.MATERIALIZATION_MATRIX[b][s])
                for b in BUCKETS for s in STRATA)
    print(f"    max |remeasured - hard-coded| = {worst:.6f}")
    assert worst < 1e-6, "adopted matrix does not match a fresh measurement"

    print("reading real QC aggregates (held-out; aggregate-only)...",
          flush=True)
    real = real_aggregates()
    print(f"    real finding mix: {real['finding'][1]:.3f}/"
          f"{real['finding'][2]:.3f}/{real['finding'][3]:.3f} "
          f"(n={real['n']})")

    # ---- [1] BEFORE (pre-change defaults, in-process reproduction) ----
    print(f"\n[1/4] BEFORE persistent: {N} cases, seed {SEED}...", flush=True)
    b_p = gen_cases(N, SEED, dist, persistent=True, legacy=True,
                    zbw=dict(OLD_ZBW))
    print(f"[1/4] BEFORE retry-loop: {N} cases, seed {SEED}...", flush=True)
    b_r = gen_cases(N, SEED, dist, persistent=False, legacy=True,
                    zbw=dict(OLD_ZBW))
    mb_p, mb_r = mixes(b_p), mixes(b_r)

    # ---- [2] AFTER (new generator defaults) ----
    print(f"\n[2/4] AFTER persistent: {N} cases, seed {SEED}...", flush=True)
    a_p = gen_cases(N, SEED, dist, persistent=True)
    print(f"[2/4] AFTER retry-loop: {N} cases, seed {SEED}...", flush=True)
    a_r = gen_cases(N, SEED, dist, persistent=False)
    ma_p, ma_r = mixes(a_p), mixes(a_r)

    arms = {"BEFORE-persist": mb_p, "AFTER-persist": ma_p,
            "BEFORE-retry": mb_r, "AFTER-retry": ma_r}

    # ---- [3] CALIBRATION ----
    print("\n== [3] CALIBRATION ==")
    print("finding mix (correct/over/under) and L1 vs real "
          f"{real['finding'][1]:.3f}/{real['finding'][2]:.3f}/"
          f"{real['finding'][3]:.3f}:")
    for k, m in arms.items():
        fm = m["finding"]
        print(f"  {k:14s} {fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f}  "
              f"L1={l1(fm, real['finding']):.3f}")

    print("\nper-case element ratios (1.0x = matches real):")
    print(f"  {'bucket':<10}" + "".join(f"{k:>14}" for k in arms))
    for b in BUCKETS:
        print(f"  {b:<10}" + "".join(
            f"{(m['per_case'][b] / real['per_case'][b]):>13.2f}x"
            for m in arms.values()))
    print("element share ratios:")
    for b in BUCKETS:
        print(f"  {b:<10}" + "".join(
            f"{(m['elem_share'][b] / real['elem_share'][b]):>13.2f}x"
            for m in arms.values()))
    print(f"nature-57 share ratio: " + "".join(
        f"  {k:12s}{(m['n57'] / real['n57']):.2f}x" for k, m in arms.items()))

    print("\ncoarse cause mix (real: "
          + "/".join(f"{real['cause'][k]:.3f}"
                     for k in ("agency", "client", "other", "unknown"))
          + "):")
    for k, m in arms.items():
        s = m["cause"]
        print(f"  {k:14s} " + "/".join(f"{s[c]:.3f}"
              for c in ("agency", "client", "other", "unknown"))
              + f"  L1={l1(s, real['cause']):.3f}")
    print("cause mix among known (real: "
          + "/".join(f"{real['cause_known'][k]:.3f}"
                     for k in ("agency", "client", "other")) + "):")
    for k, m in arms.items():
        s = m["cause_known"]
        print(f"  {k:14s} " + "/".join(f"{s[c]:.3f}"
              for c in ("agency", "client", "other"))
              + f"  L1={l1(s, real['cause_known']):.3f}")

    print("\ndollar marginals, error cases (absolute $, exp18 stats):")
    print(f"  {'stat':<8}{'real':>8}{'B-persist':>10}{'A-persist':>10}"
          f"{'B-retry':>10}{'A-retry':>10}")
    ds = [dollar_stats(x) for x in
          (real["d_all"], mb_p["d_all"], ma_p["d_all"],
           mb_r["d_all"], ma_r["d_all"])]
    for stat in ("mean", "p10", "p25", "p50", "p90", "p99", "le56"):
        fmt = (lambda v: f"{v:.2f}") if stat == "le56" else \
              (lambda v: f"{v:,.0f}")
        print(f"  {stat:<8}" + "".join(f"{fmt(d[stat]):>10}" for d in ds))
    print("\nover-vs-under medians/means (absolute $, sign match check):")
    for k, (do, du) in {"real": (real["d_over"], real["d_under"]),
                        "B-persist": (mb_p["d_over"], mb_p["d_under"]),
                        "A-persist": (ma_p["d_over"], ma_p["d_under"]),
                        "B-retry": (mb_r["d_over"], mb_r["d_under"]),
                        "A-retry": (ma_r["d_over"], ma_r["d_under"])}.items():
        print(f"  {k:10s} medO={statistics.median(do):6.0f} "
              f"medU={statistics.median(du):6.0f} "
              f"meanO={statistics.fmean(do):6.0f} "
              f"meanU={statistics.fmean(du):6.0f} "
              f"(nO={len(do)}, nU={len(du)})")

    # ---- [4] TRANSFER ----
    print("\n== [4] TRANSFER (exp19 battery: element, v1, HGB) ==")
    real_rows = load_real()
    bp_rows = [r for r in synth_rows(b_p) if r[1]]
    ap_rows = [r for r in synth_rows(a_p) if r[1]]
    br_rows = [r for r in synth_rows(b_r) if r[1]]
    ar_rows = [r for r in synth_rows(a_r) if r[1]]
    keep = sorted(set(r[1] for r in bp_rows) | set(r[1] for r in ap_rows))
    r_rows = [r for r in real_rows if r[1] in set(keep)]
    print(f"real test rows: {len(r_rows)} (buckets: {keep})")
    results = {}
    print("\n(a) persistent + unbalanced:")
    results["before-a"] = evaluate("before-a", bp_rows, r_rows)
    results["after-a"] = evaluate("after-a", ap_rows, r_rows)
    print("\n(b) persistent + class_weight=balanced:")
    results["before-b"] = evaluate("before-b", bp_rows, r_rows,
                                   class_weight="balanced")
    results["after-b"] = evaluate("after-b", ap_rows, r_rows,
                                  class_weight="balanced")
    print("\n(c) retry-loop + class_weight=balanced:")
    results["before-c"] = evaluate("before-c", br_rows, r_rows,
                                   class_weight="balanced")
    results["after-c"] = evaluate("after-c", ar_rows, r_rows,
                                  class_weight="balanced")

    print("\n== transfer summary ==")
    for k, (acc, macro, _) in results.items():
        print(f"  {k:10s} acc={acc:.3f} macroF1={macro:.3f}")
    print("\nper-bucket F1 across transfer arms:")
    hdr = "bucket     " + "".join(f" {k:>10s}" for k in results)
    print(hdr)
    for b in EVAL_BUCKETS:
        print(f"{b:10s} " + "".join(f" {results[k][2][b]:10.3f}"
                                   for k in results))


if __name__ == "__main__":
    main()
