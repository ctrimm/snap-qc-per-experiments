"""Experiment 21: ZERO_BASE_WEIGHT double-counting audit.

North-star gate: calibration. Exp20 found the scalar per-bucket
effectiveness was masking a draw-side distortion: `_applicable_buckets`
multiplies the empirical stratum mix by ZERO_BASE_WEIGHT (earned x0.018,
unearned x0.091, shelter x0.227 on zero bases), but the empirical stratum
mixes already reflect real zero-base households -- the same double-counting
exp11 diagnosed and fixed for medical (medical 0.11x -> 0.67x). The
suppression deflates earned/unearned/shelter draws and relatively inflates
sua (never scaled) and arithmetic (always fully applicable); the scalar's
under-correction of sua happened to offset its draw-side inflation (two
wrongs making a right).

Hypothesis: removing earned/unearned/shelter from ZERO_BASE_WEIGHT fixes
the draw-side distortion (earned/unearned/shelter -> 1.0x, sua deflates ->
1.0x), and re-applying the exp20 per-(bucket, stratum) materialization
matrix on the corrected draw moves hhcomp/arithmetic -> 1.0x and finding
L1 below 0.036.

Method (all in-process; only this script and its chronicle are written,
no repo files touched, nothing committed):
  [0] AUDIT: quantify the double-count analytically (synth base positivity
      per stratum -> implied draw multipliers) and by simulation (drawn
      mix vs empirical mix under the current weights).
  [1] BEFORE: 20k cases, seed 7, current generator (replicates exp20).
  [2] DAMPED: ZERO_BASE_WEIGHT entries square-rooted (partial-removal
      probe, exp13-style damping toward 1.0), 20k seed 7, paired.
  [3] REMOVED: ZERO_BASE_WEIGHT = {} (the exp11 medical precedent),
      20k seed 7, paired.
  [4] REMOVED + exp20's original matrix (transcribed from the exp20
      chronicle): tests whether the measured matrix transfers across the
      draw fix.
  [5] REMOVED + re-measured matrix: keep rates re-measured under the
      corrected draw (60k, seed 11), then the damped matrix applied,
      20k seed 7, paired.
Real QC microdata is read for aggregate comparison only; no per-row data
is written anywhere.

Usage: python3 experiments/exp21_zerobase_audit.py [--n 20000] [--m 60000]
"""
import argparse
import csv
import math
import random
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import errors, household  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

QC = Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
EL_COLS = [f"ELEMENT{i}" for i in range(1, 10)]
NTR_COLS = [f"NATURE{i}" for i in range(1, 10)]
BUCKETS = ["earned", "unearned", "shelter", "sua", "medical", "depcare",
           "hhcomp", "arithmetic"]
STRATA = ["no_earner_nonsenior", "earner_nonsenior",
          "no_earner_senior", "earner_senior"]
BASE_BUCKETS = ("earned", "unearned", "shelter", "sua")
CURRENT_ZBW = dict(errors.ZERO_BASE_WEIGHT)  # {"earned": .018, ...}

# exp20's measured per-(bucket, stratum) keep-rate matrix, transcribed from
# experiments/exp20_materialization_matrix.md (clipped to [0.02, 1.0] as in
# exp20's build_matrix; cells < 0.10 fall back to the scalar in the weight).
EXP20_MATRIX = {
    "earned":     {"no_earner_nonsenior": 0.70, "earner_nonsenior": 0.82,
                   "no_earner_senior": 0.02, "earner_senior": 0.75},
    "unearned":   {"no_earner_nonsenior": 0.81, "earner_nonsenior": 0.95,
                   "no_earner_senior": 0.76, "earner_senior": 0.83},
    "shelter":    {"no_earner_nonsenior": 0.21, "earner_nonsenior": 0.47,
                   "no_earner_senior": 0.44, "earner_senior": 0.68},
    "sua":        {"no_earner_nonsenior": 0.15, "earner_nonsenior": 0.43,
                   "no_earner_senior": 0.33, "earner_senior": 0.55},
    "medical":    {"no_earner_nonsenior": 0.02, "earner_nonsenior": 0.02,
                   "no_earner_senior": 0.53, "earner_senior": 0.77},
    "depcare":    {"no_earner_nonsenior": 0.31, "earner_nonsenior": 0.71,
                   "no_earner_senior": 0.33, "earner_senior": 1.00},
    "hhcomp":     {"no_earner_nonsenior": 0.70, "earner_nonsenior": 0.61,
                   "no_earner_senior": 0.55, "earner_senior": 0.41},
    "arithmetic": {"no_earner_nonsenior": 1.00, "earner_nonsenior": 1.00,
                   "no_earner_senior": 1.00, "earner_senior": 1.00},
}
DAMP = 0.8   # exp13's damping rule
MIN_M = 0.10  # mechanics-gap cells fall back to the scalar (exp20)
WCAP = 2.5   # trust region vs the scalar (exp20)


def stratum_of(facts):
    """Must match the stratum key logic in errors._applicable_buckets."""
    earner = "earner" if facts.get("earned", 0) > 0 else "no_earner"
    senior = "senior" if facts.get("senior_disabled") else "nonsenior"
    return f"{earner}_{senior}"


@contextmanager
def patched_zbw(new):
    """Swap errors.ZERO_BASE_WEIGHT in-process; the generator default is
    untouched (same explicit-flag spirit as --no-persistent-buckets)."""
    old = errors.ZERO_BASE_WEIGHT
    errors.ZERO_BASE_WEIGHT = new
    try:
        yield
    finally:
        errors.ZERO_BASE_WEIGHT = old


def real_aggregates():
    """Aggregate-only read of the held-out QC file: finding mix, element
    mix, nature-57 share, per-case element rates, plus a per-stratum table
    (case share, base positivity for unearned/shelter/sua, arithmetic
    per-case rate) for the audit and the arithmetic-fallback diagnosis."""
    finding = Counter()
    bucket = Counter()
    per_case = Counter()
    n57 = 0
    n = 0
    s_n = Counter()
    s_une = Counter()
    s_sh = Counter()
    s_sua = Counter()
    s_arith = Counter()
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            finding[int(row["STATUS"])] += 1
            earner = float(row["FSEARN"] or 0) > 0
            senior = (float(row["FSNELDER"] or 0) > 0 or
                      any(float(row[f"SSI{i}"] or 0) > 0 for i in range(1, 19)))
            s = ("earner" if earner else "no_earner") + "_" + \
                ("senior" if senior else "nonsenior")
            s_n[s] += 1
            if float(row["FSUNEARN"] or 0) > 0:
                s_une[s] += 1
            if float(row["FSSLTEXP"] or 0) > 0:
                s_sh[s] += 1
            if float(row["UTIL"] or 0) > 0:
                s_sua[s] += 1
            for ec, nc in zip(EL_COLS, NTR_COLS):
                e = (row[ec] or "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                bucket[b] += 1
                per_case[b] += 1
                if b == "arithmetic":
                    s_arith[s] += 1
                if (row[nc] or "").strip() == "57":
                    n57 += 1
    v = sum(bucket.values())
    stab = {s: {"share": s_n[s] / n,
                "p_une_base": s_une[s] / s_n[s],
                "p_shelter_base": s_sh[s] / s_n[s],
                "p_sua_base": s_sua[s] / s_n[s],
                "arith_per_case": s_arith[s] / s_n[s]}
            for s in STRATA}
    return ({k: finding[k] / n for k in (1, 2, 3)},
            {b: bucket[b] / v for b in BUCKETS},
            n57 / v,
            {b: per_case[b] / n for b in BUCKETS},
            stab)


def gen_cases(n, seed, dist):
    """Replicates generate.py's loop (persistent mode, max_attempts=12)."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        facts = household.sample_household(rng)
        out.append(errors.inject(facts, rng, dist, max_attempts=12,
                                 persistent_buckets=True))
    return out


def mixes(cases):
    f = Counter(c["finding"] for c in cases)
    n = len(cases)
    fm = {k: f[k] / n for k in (1, 2, 3)}
    b = Counter()
    n57 = 0
    for c in cases:
        for v in c["variances"]:
            b[v["element_bucket"]] += 1
            if v["nature"] == 57:
                n57 += 1
    v = sum(b.values())
    return (fm,
            {k: b[k] / v for k in BUCKETS},
            (n57 / v if v else 0),
            {k: b[k] / n for k in BUCKETS})  # per-case rates


def finding_l1(fm, real_fm):
    return sum(abs(fm[k] - real_fm[k]) for k in (1, 2, 3))


def synth_base_rates(n, seed):
    """P(base > 0) per stratum for the gated base fields, from the
    household sampler alone (no injection)."""
    rng = random.Random(seed)
    pos = Counter()
    tot = Counter()
    for _ in range(n):
        facts = household.sample_household(rng)
        s = stratum_of(facts)
        tot[s] += 1
        if facts.get("earned", 0) > 0:
            pos[(s, "earned")] += 1
        if facts.get("unearned", 0) > 0:
            pos[(s, "unearned")] += 1
        if facts.get("shelter", 0) > 0:
            pos[(s, "shelter")] += 1
        if facts.get("sua", 0) == 1:
            pos[(s, "sua")] += 1
    return {s: {b: pos[(s, b)] / tot[s] for b in BASE_BUCKETS}
            for s in STRATA}


_ORIG_IP = errors._inject_persistent
_DRAWN = Counter()  # (bucket, stratum) -> drawn variances (post-1/eff_b)


def _draw_measuring_ip(facts, rng, dist, applicable, dir_w, max_attempts,
                       stats=None):
    s = stratum_of(facts)
    local = {"drawn": Counter(), "recorded": Counter()}
    out = _ORIG_IP(facts, rng, dist, applicable, dir_w, max_attempts,
                   stats=local)
    for b, c in local["drawn"].items():
        _DRAWN[(b, s)] += c
    return out


def measure_drawn_mix(n, seed, dist):
    """Drawn bucket mix per stratum under the *current* generator weights
    (zero-base scaling + 1/eff_b), by simulation."""
    _DRAWN.clear()
    errors._inject_persistent = _draw_measuring_ip
    try:
        gen_cases(n, seed, dist)
    finally:
        errors._inject_persistent = _ORIG_IP
    out = {}
    for s in STRATA:
        tot = sum(_DRAWN[(b, s)] for b in BUCKETS)
        out[s] = {b: _DRAWN[(b, s)] / tot for b in BUCKETS}
    return out


_REC_DRAWN = Counter()
_RECORDED = Counter()


def _kr_measuring_ip(facts, rng, dist, applicable, dir_w, max_attempts,
                     stats=None):
    s = stratum_of(facts)
    local = {"drawn": Counter(), "recorded": Counter()}
    out = _ORIG_IP(facts, rng, dist, applicable, dir_w, max_attempts,
                   stats=local)
    for b, c in local["drawn"].items():
        _REC_DRAWN[(b, s)] += c
    for b, c in local["recorded"].items():
        _RECORDED[(b, s)] += c
    return out


def build_matrix(dist):
    eff_b = (dist.get("effectiveness") or {}).get("bucket", {})
    mat = {}
    for b in BUCKETS:
        mat[b] = {}
        for s in STRATA:
            d = _REC_DRAWN[(b, s)]
            r = _RECORDED[(b, s)]
            m = r / d if d else eff_b.get(b, 1.0)
            mat[b][s] = min(1.0, max(0.02, m))
    return mat


def matrix_weight(b, s, matrix, eff_b):
    m = matrix[b][s]
    sc = eff_b.get(b, 1.0)
    if m < MIN_M:
        m = sc
    w = DAMP / max(m, 0.02) + (1.0 - DAMP) / max(sc, 0.02)
    return min(w, WCAP / max(sc, 0.02))


def matrix_ip_factory(matrix, dist):
    eff_b = (dist.get("effectiveness") or {}).get("bucket", {})

    def _matrix_ip(facts, rng, dist_arg, applicable, dir_w, max_attempts,
                   stats=None):
        s = stratum_of(facts)
        weighted = {b: p * matrix_weight(b, s, matrix, eff_b)
                    for b, p in applicable.items()}
        # Neutralize the scalar so it is not applied on top of the matrix.
        dist2 = dict(dist_arg)
        dist2["effectiveness"] = {"bucket": {}, "dir_weight": dir_w}
        return _ORIG_IP(facts, rng, dist2, weighted, dir_w, max_attempts,
                        stats=stats)

    return _matrix_ip


def show_ratios(label, fm, em, s57, pc, real_fm, real_em, real_57, real_pc):
    print(f"\n== {label} ==")
    print(f"  finding mix: {fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f}  "
          f"L1={finding_l1(fm, real_fm):.3f}")
    print(f"  {'bucket':<10}{'per-case':>9}{'share':>7}")
    for b in BUCKETS:
        rpc = pc[b] / real_pc[b] if real_pc[b] else 0
        rsh = em[b] / real_em[b] if real_em[b] else 0
        print(f"  {b:<10}{rpc:>8.2f}x{rsh:>6.2f}x")
    print(f"  nature-57 share ratio: "
          f"{(s57 / real_57 if real_57 else 0):.2f}x")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--m", type=int, default=60000,
                    help="cases for the keep-rate measurement run")
    args = ap.parse_args()

    dist = load_dist(ROOT / "experiments/dist.json")
    eff_b = (dist.get("effectiveness") or {}).get("bucket", {})
    strat_mix = {s: dist[f"bucket_probs_given_{s}"] for s in STRATA}

    real_fm, real_em, real_57, real_pc, real_stab = real_aggregates()
    print(f"real finding mix: {real_fm[1]:.3f}/{real_fm[2]:.3f}/{real_fm[3]:.3f}")

    # ---- [0] AUDIT: quantify the double-count ----
    print("\n[0] AUDIT: real per-stratum base positivity (aggregates only):")
    print(f"  {'stratum':<22}{'share':>7}{'P(une>0)':>9}{'P(sh>0)':>9}"
          f"{'P(sua)':>8}{'arith/case':>11}")
    for s in STRATA:
        t = real_stab[s]
        print(f"  {s:<22}{t['share']:>7.3f}{t['p_une_base']:>9.3f}"
              f"{t['p_shelter_base']:>9.3f}{t['p_sua_base']:>8.3f}"
              f"{t['arith_per_case']:>11.4f}")

    print("\n[0] AUDIT: synth household base positivity per stratum "
          "(100k households, seed 5):")
    sb = synth_base_rates(100000, 5)
    print(f"  {'stratum':<22}" + "".join(f"{b:>10}" for b in BASE_BUCKETS))
    for s in STRATA:
        print(f"  {s:<22}" + "".join(f"{sb[s][b]:>10.3f}" for b in BASE_BUCKETS))

    print("\n[0] AUDIT: implied average draw multiplier M[b][s] = "
          "P(base>0) + P(base=0)*w_b  (1.0 = no distortion):")
    print(f"  {'stratum':<22}" + "".join(f"{b:>10}" for b in
                                        ("earned", "unearned", "shelter")))
    M = {}
    for s in STRATA:
        M[s] = {}
        row = f"  {s:<22}"
        for b in ("earned", "unearned", "shelter"):
            w = CURRENT_ZBW[b]
            m = sb[s][b] + (1 - sb[s][b]) * w
            M[s][b] = m
            row += f"{m:>10.3f}"
        print(row)

    print("\n[0] AUDIT: analytic drawn/empirical share ratio per stratum "
          "(mix * M / eff_b, renormalized; <1 = suppressed, >1 = inflated):")
    print(f"  {'stratum':<22}" + "".join(f"{b:>10}" for b in BUCKETS))
    for s in STRATA:
        num = {b: strat_mix[s][b] * M[s].get(b, 1.0) / max(eff_b.get(b, 1.0), 0.02)
               for b in BUCKETS}
        tot = sum(num.values())
        row = f"  {s:<22}"
        for b in BUCKETS:
            row += f"{(num[b] / tot) / strat_mix[s][b]:>10.2f}"
        print(row)

    print("\n[0] AUDIT: simulated drawn/empirical share ratio (40k cases, "
          "seed 13, current weights):")
    drawn = measure_drawn_mix(40000, 13, dist)
    print(f"  {'stratum':<22}" + "".join(f"{b:>10}" for b in BUCKETS))
    for s in STRATA:
        row = f"  {s:<22}"
        for b in BUCKETS:
            row += f"{drawn[s][b] / strat_mix[s][b]:>10.2f}"
        print(row)

    # ---- [1] BEFORE ----
    print(f"\n[1/5] BEFORE: generating {args.n} cases (seed 7)...", flush=True)
    before = gen_cases(args.n, 7, dist)
    res = {"BEFORE": mixes(before)}
    show_ratios("BEFORE (current ZERO_BASE_WEIGHT)", *res["BEFORE"],
                real_fm, real_em, real_57, real_pc)

    # ---- [2] DAMPED (sqrt weights: partial-removal probe) ----
    damped_zbw = {b: math.sqrt(w) for b, w in CURRENT_ZBW.items()}
    print(f"\n[2/5] DAMPED (sqrt weights {damped_zbw}): {args.n} cases, "
          f"seed 7...", flush=True)
    with patched_zbw(damped_zbw):
        res["DAMPED"] = mixes(gen_cases(args.n, 7, dist))
    show_ratios("DAMPED (sqrt ZERO_BASE_WEIGHT)", *res["DAMPED"],
                real_fm, real_em, real_57, real_pc)

    # ---- [3] REMOVED ----
    print(f"\n[3/5] REMOVED (ZERO_BASE_WEIGHT={{}}): {args.n} cases, seed 7...",
          flush=True)
    with patched_zbw({}):
        res["REMOVED"] = mixes(gen_cases(args.n, 7, dist))
    show_ratios("REMOVED (no zero-base scaling)", *res["REMOVED"],
                real_fm, real_em, real_57, real_pc)

    # ---- [4] REMOVED + exp20's original matrix ----
    print(f"\n[4/5] REMOVED + exp20 original matrix: {args.n} cases, seed 7...",
          flush=True)
    with patched_zbw({}):
        errors._inject_persistent = matrix_ip_factory(EXP20_MATRIX, dist)
        try:
            res["REMOVED+EXP20MAT"] = mixes(gen_cases(args.n, 7, dist))
        finally:
            errors._inject_persistent = _ORIG_IP
    show_ratios("REMOVED + exp20 matrix", *res["REMOVED+EXP20MAT"],
                real_fm, real_em, real_57, real_pc)

    # ---- [5] re-measure keep rates under the corrected draw, then apply ----
    print(f"\n[5/5] MEASURE keep rates under the corrected draw: {args.m} "
          f"cases (seed 11)...", flush=True)
    _REC_DRAWN.clear()
    _RECORDED.clear()
    with patched_zbw({}):
        errors._inject_persistent = _kr_measuring_ip
        try:
            gen_cases(args.m, 11, dist)
        finally:
            errors._inject_persistent = _ORIG_IP
    new_matrix = build_matrix(dist)
    print("\nre-measured keep rates under the corrected draw "
          "(delta vs exp20 in parens):")
    print(f"  {'bucket':<10}" + "".join(f"{s:>22}" for s in STRATA))
    for b in BUCKETS:
        row = f"  {b:<10}"
        for s in STRATA:
            d = EXP20_MATRIX[b][s] - new_matrix[b][s]
            row += f"{new_matrix[b][s]:>10.3f} ({d:>+5.2f})"
        print(row)

    print(f"\n[5/5] REMOVED + re-measured matrix: {args.n} cases, seed 7...",
          flush=True)
    with patched_zbw({}):
        errors._inject_persistent = matrix_ip_factory(new_matrix, dist)
        try:
            res["REMOVED+NEWMAT"] = mixes(gen_cases(args.n, 7, dist))
        finally:
            errors._inject_persistent = _ORIG_IP
    show_ratios("REMOVED + re-measured matrix", *res["REMOVED+NEWMAT"],
                real_fm, real_em, real_57, real_pc)

    print("\n== comparison: per-case element ratios and finding L1 ==")
    print(f"  {'bucket':<10}" + "".join(f"{k:>16}" for k in res))
    for b in BUCKETS:
        row = f"  {b:<10}"
        for k in res:
            pc = res[k][3]
            row += f"{(pc[b] / real_pc[b] if real_pc[b] else 0):>15.2f}x"
        print(row)
    row = f"  {'finding L1':<10}"
    for k in res:
        row += f"{finding_l1(res[k][0], real_fm):>16.3f}"
    print(row)
    row = f"  {'nature57':<10}"
    for k in res:
        row += f"{(res[k][2] / real_57 if real_57 else 0):>15.2f}x"
    print(row)


if __name__ == "__main__":
    main()
