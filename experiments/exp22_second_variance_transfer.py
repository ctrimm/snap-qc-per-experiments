"""Exp 22 — second-variance structure and the residual transfer edge.

Exp 19 falsified exp9's distinct-count mechanism: at count parity the retry
loop still wins element macroF1 (0.304 vs 0.287), and the persistent
generator had MORE distinct medical (310 vs 264) and sua (781 vs 738) cases
yet worse F1. The live candidates for the residual edge:

  (1) multi-variance structure — retry-loop error cases carry far more
      second variances (a drawn second variance is recorded unconditionally
      whenever the draw set materializes), while the persistent flow keeps a
      second variance only if it individually moves the benefit;
  (2) household selection — the retry loop redraws variance draws until one
      materializes (up to --max-attempts), which filters households: only
      households where *some* corruption moves the benefit become error
      cases, and the selected subpopulation may carry error signatures that
      are more prototypical of real errors.

This experiment attributes the gap: (h) gives persistent cases retry-rate
second variances (matched per bucket); (i) removes multi-variance cases
from the retry loop; (j) runs the persistent generator on the retry loop's
selected households.

Element task only (y_idx=3), v1 features (9 raw), HistGradientBoosting
Classifier(random_state=0), 20k synth baselines (seed 7), the same real
FY2024 QC test split as exp9/exp19 (test set NEVER touched).

Arms:
  (b) persistent + class_weight="balanced"            -- exp19 replication
  (c) retry-loop + class_weight="balanced"            -- exp19 replication (bar)
  (h) persistent + 2nd variances at retry rates + balanced   -- key test
  (i) retry-loop, single-variance cases only + balanced       -- ablation
  (j) persistent generator on retry-selected households + balanced
      -- selection: the retry loop's screen admits "hard" households the
      persistent keep-rule would leave clean; running the persistent
      generator on exactly those households isolates the household-
      composition effect from the case-structure effect.

Usage: python3 experiments/exp22_second_variance_transfer.py
       [--synth-src /tmp/pristine/src] [--n-pool N] [--n-base N] [--seed S]
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

# --synth-src must be honored before `from synth import ...` runs, so it is
# pre-parsed here. Default: this repo's src/. Point it at a pristine
# `git archive HEAD src` tree to run the battery against the pre-exp24
# generator (exp24's uncommitted rebaseline changed the persistent
# generator's materialization correction and emptied ZERO_BASE_WEIGHT).
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--synth-src", default=None,
                  help="override the synth package dir (reproducibility)")
_pre_args, _ = _pre.parse_known_args()
ROOT = Path(__file__).resolve().parent.parent
SYNTH_SRC = Path(_pre_args.synth_src) if _pre_args.synth_src else ROOT / "src"
sys.path.insert(0, str(SYNTH_SRC))
from synth import benefit as benefit_mod  # noqa: E402
from synth import errors as errors_mod  # noqa: E402
from synth import params  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

V1 = ["hh_size", "earned", "unearned", "shelter", "sua",
      "medical_exp", "depcare", "senior_disabled", "issued_benefit"]

BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]

SUA_YES = {"3", "4", "5", "6", "7", "8"}

# Observables for the household-selection comparison (truth facts).
OBS = ["hh_size", "earned", "unearned", "shelter", "sua", "medical_exp",
       "depcare", "senior_disabled", "n_elderly", "n_disabled"]


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


def load_synth_cases(path):
    """Raw case dicts (needed: variance lists, truth facts for injection)."""
    with open(path) as fh:
        return [json.loads(line) for line in fh]


def case_row(c):
    """Feature row from a case dict: (feats, binary, finding, bucket, n_var)."""
    return (synth_case_features(c),
            0 if c["finding"] == 1 else 1,
            c["finding"],
            c["variances"][0]["element_bucket"] if c["variances"] else None,
            len(c["variances"]))


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
    subprocess.run(cmd, cwd=str(SYNTH_SRC), check=True, capture_output=True)
    return path


# ---- second-variance rates ----
def second_var_rates(rows):
    """Per-bucket fraction of error rows carrying >= 2 variances."""
    by = {}
    for r in rows:
        by.setdefault(r[3], []).append(r)
    return {b: sum(1 for r in rs if r[4] >= 2) / len(rs)
            for b, rs in sorted(by.items())}


def real_multivar_rates():
    """Real QC reference: per-ELEMENT1-bucket fraction of error cases with
    >= 2 recorded variances (ELEMENT1..ELEMENT9 arrays)."""
    by = {}
    total_err = total_multi = 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            if row["STATUS"].strip() not in ("2", "3"):
                continue
            e1 = row.get("ELEMENT1", "").strip()
            n_var = sum(1 for i in range(1, 10)
                        if row.get(f"ELEMENT{i}", "").strip())
            total_err += 1
            total_multi += (n_var >= 2)
            if e1:
                b = element_bucket(int(e1))
                by.setdefault(b, []).append(n_var >= 2)
    per = {b: sum(v) / len(v) for b, v in sorted(by.items()) if b in BUCKETS}
    return total_multi / total_err, per, {b: len(v) for b, v in by.items()
                                          if b in BUCKETS}


# ---- arm (h): inject retry-style second variances into persistent cases ----
def inject_second_variance(case, dist, rng):
    """Append one retry-loop-style second variance to a persistent error
    case: drawn from the retry loop's applicable mix (1/eff weighted),
    applied to the agency facts, recorded unconditionally like the retry
    loop does. Redraws (<=5) if it exactly offsets variance 1 (the retry
    loop would reject that draw set); returns the original case if no
    non-offsetting draw is found. The label (variances[0]) never changes.
    """
    truth = copy.deepcopy(case["facts"])
    agency = copy.deepcopy(case["issued_facts"])
    applicable = errors_mod._applicable_buckets(truth, dist, rng)
    eff = dist.get("effectiveness") or {}
    eff_b = eff.get("bucket", eff)
    if eff_b:
        applicable = {b: p / max(eff_b.get(b, 1.0), 0.02)
                      for b, p in applicable.items()}
    dir_w = eff.get("dir_weight", {})
    old_agency_benefit = benefit_mod.compute(agency)["benefit"]
    for _ in range(5):
        a2 = copy.deepcopy(agency)
        t2 = truth
        b2 = errors_mod._sample(rng, applicable)
        n2, c2 = errors_mod._draw_nature(truth, b2, dist, dir_w, rng)
        noise2 = 0.0
        if b2 == "arithmetic":
            noise2 = rng.choice([-1, 1]) * rng.uniform(10, 60)
        else:
            corr, override = errors_mod._apply_one(a2, t2, b2, n2, rng, dist)
            if corr:
                t2 = {**t2, **corr}
            if override is not None:
                n2 = override  # recorded nature, like inject()
        new_correct = benefit_mod.compute(t2)["benefit"]
        if b2 == "arithmetic":
            new_issued = case["issued_benefit"] + noise2
        else:
            new_issued = (case["issued_benefit"]
                          + benefit_mod.compute(a2)["benefit"]
                          - old_agency_benefit)
        new_issued = max(0, int(round(new_issued)))
        if new_issued != new_correct:
            new = copy.deepcopy(case)
            new["facts"] = t2
            new["issued_facts"] = a2
            new["issued_benefit"] = new_issued
            new["correct_benefit"] = new_correct
            new["finding"] = 2 if new_issued > new_correct else 3
            new["dollar_error"] = abs(new_correct - new_issued)
            new["reportable"] = new["dollar_error"] > params.QC_ERROR_THRESHOLD
            new["variances"] = list(case["variances"]) + [{
                "element": errors_mod.REPRESENTATIVE_ELEMENT[b2],
                "element_bucket": b2,
                "nature": n2,
                "cause": errors_mod._recorded_cause(n2, c2, rng),
                "timing": "after" if n2 == 97 else "at_action",
            }]
            return new
    return case


# ---- arm (j): the retry loop's materialization screen, coin forced on ----
def retry_materializable(facts, dist, rng, max_attempts=12):
    """True iff some variance draw-set moves the benefit within the retry
    budget. Mirrors errors.inject's retry loop exactly (same helpers, same
    draw order) but skips the phase-1 injection coin — the coin is shared by
    both generators, so only the materialization screen can explain the
    cross-generator gap."""
    applicable = errors_mod._applicable_buckets(facts, dist, rng)
    eff = dist.get("effectiveness") or {}
    eff_b = eff.get("bucket", eff)
    dir_w = eff.get("dir_weight", {})
    if eff_b:
        applicable = {b: p / max(eff_b.get(b, 1.0), 0.02)
                      for b, p in applicable.items()}
    for _ in range(max_attempts):
        agency = copy.deepcopy(facts)
        truth = facts
        benefit_noise = 0.0
        n_var = 2 if rng.random() < 0.15 else 1
        for _ in range(n_var):
            bucket = errors_mod._sample(rng, applicable)
            nature, _cause = errors_mod._draw_nature(facts, bucket, dist,
                                                    dir_w, rng)
            if bucket == "arithmetic":
                benefit_noise += rng.choice([-1, 1]) * rng.uniform(10, 60)
            else:
                corr, _ov = errors_mod._apply_one(agency, truth, bucket,
                                                 nature, rng, dist)
                if corr:
                    truth = {**truth, **corr}
        correct = benefit_mod.compute(truth)["benefit"]
        issued = max(0, int(round(
            benefit_mod.compute(agency)["benefit"] + benefit_noise)))
        if issued != correct:
            return True
    return False


def evaluate(name, s_rows, r_rows, feats, class_weight=None):
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


def direction_mix(rows):
    errs = [r for r in rows if r[2] in (2, 3)]
    n = len(errs) or 1
    return {2: sum(1 for r in errs if r[2] == 2) / n,
            3: sum(1 for r in errs if r[2] == 3) / n}


def l1(a, b):
    return sum(abs(a[k] - b.get(k, 0.0)) for k in a)


# ---- household-selection comparison ----
def smd(a_vals, b_vals):
    """Standardized mean difference between two samples."""
    import statistics
    ma, mb = statistics.fmean(a_vals), statistics.fmean(b_vals)
    va = statistics.pvariance(a_vals) if len(a_vals) > 1 else 0.0
    vb = statistics.pvariance(b_vals) if len(b_vals) > 1 else 0.0
    pooled = ((va + vb) / 2) ** 0.5
    return (ma - mb) / pooled if pooled > 0 else 0.0


def selection_table(label, cases_a, cases_b, cases_pop):
    """SMD of truth-household observables: A vs B, and each vs population."""
    print(f"\n== household selection: {label} ==")
    print(f"{'observable':16s} {'mean_A':>8s} {'mean_B':>8s} "
          f"{'SMD(A-B)':>9s} {'SMD(A-pop)':>11s} {'SMD(B-pop)':>11s}")
    import statistics
    for ob in OBS:
        fa = [float(c["facts"][ob]) for c in cases_a]
        fb = [float(c["facts"][ob]) for c in cases_b]
        fp = [float(c["facts"][ob]) for c in cases_pop]
        print(f"{ob:16s} {statistics.fmean(fa):8.3f} {statistics.fmean(fb):8.3f} "
              f"{smd(fa, fb):9.3f} {smd(fa, fp):11.3f} {smd(fb, fp):11.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth-src", default=None,
                    help="override the synth package dir (pre-parsed; see top of file)")
    ap.add_argument("--n-pool", type=int, default=100000)
    ap.add_argument("--n-base", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    dist = load_dist(ROOT / "experiments/dist.json")

    print(f"generating pools ({args.n_pool} persistent + {args.n_pool} "
          f"retry-loop, seed {args.seed})...", flush=True)
    p_path = gen_synth(args.n_pool, args.seed, persistent=True)
    r_path = gen_synth(args.n_pool, args.seed, persistent=False)

    print("loading real QC file...", flush=True)
    real = load_real()

    print("loading pools...", flush=True)
    cases_p = load_synth_cases(p_path)[:args.n_base]
    cases_r = load_synth_cases(r_path)[:args.n_base]
    Path(p_path).unlink(missing_ok=True)
    Path(r_path).unlink(missing_ok=True)

    base_p = [case_row(c) for c in cases_p if c["variances"]]
    base_r = [case_row(c) for c in cases_r if c["variances"]]
    err_p = [c for c in cases_p if c["variances"]]
    err_r = [c for c in cases_r if c["variances"]]

    cnt_p = Counter(r[3] for r in base_p)
    cnt_r = Counter(r[3] for r in base_r)
    print("baseline 20k error-class counts (persistent):", dict(cnt_p))
    print("baseline 20k error-class counts (retry-loop):", dict(cnt_r))
    # exp19 replication check: same seed and command must reproduce its
    # counts (scaled when --n-base != 20000).
    scale = args.n_base / 20000
    for b, ep, er in [("hhcomp", 420, 735), ("arithmetic", 262, 508),
                      ("medical", 310, 264), ("depcare", 72, 82)]:
        xp, xr = round(ep * scale), round(er * scale)
        if cnt_p.get(b) != xp or cnt_r.get(b) != xr:
            print(f"WARNING: replication drift on {b}: persistent "
                  f"{cnt_p.get(b)} (exp19-scaled {xp}), retry "
                  f"{cnt_r.get(b)} (exp19-scaled {xr})")
        else:
            print(f"  replication OK on {b}: {cnt_p.get(b)}/{cnt_r.get(b)}")

    # ---- (1) second-variance rates: both generators + real QC reference ----
    p2_p = second_var_rates(base_p)
    p2_r = second_var_rates(base_r)
    print("\n== second-variance rates: fraction of error cases with >=2 "
          "variances, by label bucket ==")
    print(f"{'bucket':10s} {'persistent':>10s} {'retry-loop':>10s} "
          f"{'real QC':>8s} {'(real n)':>8s}")
    real_overall, real_per, real_n = real_multivar_rates()
    for b in BUCKETS:
        print(f"{b:10s} {p2_p.get(b, 0):10.3f} {p2_r.get(b, 0):10.3f} "
              f"{real_per.get(b, 0):8.3f} {real_n.get(b, 0):8d}")
    print(f"overall: persistent "
          f"{sum(1 for r in base_p if r[4] >= 2) / len(base_p):.3f}, "
          f"retry {sum(1 for r in base_r if r[4] >= 2) / len(base_r):.3f}, "
          f"real QC {real_overall:.3f}")

    # ---- (3a) household selection: observable distributions ----
    selection_table("retry-error households (A) vs persistent-error (B), "
                    "vs all pooled households (pop)",
                    err_r, err_p, cases_p + cases_r)

    # Screen asymmetry: with the shared phase-1 coin forced on, which
    # households does each generator's materialization screen admit?
    dist_coin = copy.deepcopy(dist)
    dist_coin.get("injection_rate", {})["persistent"] = {
        "earner": 1.0, "no_earner": 1.0}

    def persistent_screen_pass(facts, seed):
        c = errors_mod.inject(copy.deepcopy(facts), random.Random(seed),
                              dist_coin, max_attempts=12,
                              persistent_buckets=True)
        return bool(c["variances"])

    n_samp = min(3000, len(err_p), len(err_r))
    r_given_p = sum(retry_materializable(c["facts"], dist,
                                        random.Random(3000 + i))
                    for i, c in enumerate(err_p[:n_samp])) / n_samp
    p_given_r = sum(persistent_screen_pass(c["facts"], 4000 + i)
                    for i, c in enumerate(err_r[:n_samp])) / n_samp
    print(f"\nscreen asymmetry (coin forced on, n={n_samp} each):")
    print(f"  P(retry screen passes | persistent error household) = {r_given_p:.3f}")
    print(f"  P(persistent screen passes | retry error household) = {p_given_r:.3f}")

    # ---- build arms ----
    # (h): persistent + second variances injected at retry per-bucket rates.
    # Only single-variance cases are eligible; the coin is sized so the
    # final per-bucket rate lands on the retry rate.
    rng_h = random.Random(20260929)
    h_cases = []
    for c in err_p:
        b = c["variances"][0]["element_bucket"]
        if len(c["variances"]) == 1:
            q = (p2_r.get(b, 0) - p2_p.get(b, 0)) / max(1 - p2_p.get(b, 0), 1e-9)
            if rng_h.random() < max(q, 0.0):
                c = inject_second_variance(c, dist, rng_h)
        h_cases.append(c)
    h_rows = [case_row(c) for c in h_cases]
    p2_h = second_var_rates(h_rows)
    print("\n(h) achieved second-variance rates vs retry targets:")
    for b in BUCKETS:
        print(f"    {b:10s} achieved {p2_h.get(b, 0):.3f} "
              f"(target {p2_r.get(b, 0):.3f}, persistent was {p2_p.get(b, 0):.3f})")

    # (i): retry-loop, single-variance cases only.
    i_cases = [c for c in err_r if len(c["variances"]) == 1]
    i_rows = [case_row(c) for c in i_cases]
    print(f"\n(i) retry single-variance-only: {len(i_rows)} rows "
          f"(dropped {len(err_r) - len(i_rows)} multi-variance)")

    # ---- (j): persistent generator on retry-selected households ----
    # The retry loop's screen is one-directional: nearly every persistent
    # error household also passes the retry screen, but not vice versa (the
    # retry loop admits "hard" households the persistent keep-rule leaves
    # clean). So instead of filtering persistent cases through the retry
    # screen (vacuous), run the persistent generator on the retry pool's
    # error households with the shared phase-1 coin forced on — the only
    # difference from (b) is the household population. (dist_coin, with
    # the shared phase-1 coin forced on, was built in the selection
    # section above.)
    j_cases = []
    for idx, c in enumerate(err_r):
        cj = errors_mod.inject(copy.deepcopy(c["facts"]),
                               random.Random(2000 + idx), dist_coin,
                               max_attempts=12, persistent_buckets=True)
        if cj["variances"]:
            j_cases.append(cj)
    j_rows = [case_row(c) for c in j_cases]
    print(f"(j) persistent on retry-selected households: {len(j_rows)} rows "
          f"({len(j_rows) / len(err_r):.2f} of retry error households "
          f"yielded a persistent error)")

    # test split: identical to exp9/exp19 (buckets in the persistent baseline)
    keep = sorted(set(cnt_p))
    r_rows = [r for r in real if r[3] in set(keep)]
    print(f"\nreal test rows: {len(r_rows)} (of {len(real)})")

    results = {}
    print("\n== (b) persistent + class_weight=balanced [v1] (exp19: 0.478/0.288) ==")
    results["b"] = evaluate("b", base_p, r_rows, V1, class_weight="balanced")
    print("\n== (c) retry-loop + class_weight=balanced [v1] (exp19: 0.437/0.304) ==")
    results["c"] = evaluate("c", base_r, r_rows, V1, class_weight="balanced")
    print("\n== (h) persistent + 2nd variances at retry rates + balanced [v1] ==")
    results["h"] = evaluate("h", h_rows, r_rows, V1, class_weight="balanced")
    print("\n== (i) retry-loop single-variance-only + balanced [v1] ==")
    results["i"] = evaluate("i", i_rows, r_rows, V1, class_weight="balanced")
    print("\n== (j) persistent generator on retry-selected households + balanced [v1] ==")
    results["j"] = evaluate("j", j_rows, r_rows, V1, class_weight="balanced")

    print("\n== summary ==")
    for k, (acc, macro, per) in results.items():
        print(f"  ({k}) acc={acc:.3f} macroF1={macro:.3f}")

    print("\n== per-bucket F1 across arms ==")
    print("bucket     " + "".join(f"  ({k})" for k in results))
    for b in BUCKETS:
        print(f"{b:10s} " + "".join(f" {results[k][2][b]:.3f}" for k in results))

    # ---- attribution of the (c)-(b) gap ----
    gap = results["c"][1] - results["b"][1]
    print("\n== gap attribution (macroF1; gap = (c)-(b)) ==")
    print(f"  gap = {gap:.4f}")
    for name, num, den_desc in [
            ("(h)-(b) 2nd-variance injection", results["h"][1] - results["b"][1], "gap"),
            ("(c)-(i) removing retry multi-var", results["c"][1] - results["i"][1], "gap"),
            ("(j)-(b) retry household population", results["j"][1] - results["b"][1], "gap")]:
        share = num / gap if gap else float("nan")
        print(f"  {name}: {num:+.4f}  ({share:+.1%} of {den_desc})")

    # ---- calibration: what the arms cost in fidelity ----
    print("\n== calibration readings ==")
    real_finding = finding_mix(real)
    print(f"real finding mix (correct/over/under): "
          f"{real_finding[1]:.3f}/{real_finding[2]:.3f}/{real_finding[3]:.3f}")
    for name, rows in [("b (persistent 20k err rows)", base_p),
                       ("c (retry 20k err rows)", base_r),
                       ("h (persistent + 2nd var)", h_rows),
                       ("i (retry single-var)", i_rows),
                       ("j (persistent on retry households)", j_rows)]:
        em, dm = element_mix(rows), direction_mix(rows)
        print(f"  training-subset {name}: element-mix L1={l1(em, element_mix(r_rows)):.3f} "
              f"direction-mix L1={l1(dm, direction_mix(real)):.3f}")


if __name__ == "__main__":
    main()
