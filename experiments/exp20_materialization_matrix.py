"""Experiment 20: per-(bucket, stratum) materialization matrix.

North-star gate: calibration. Exp14 re-measured the scalar per-bucket
effectiveness eff_b under the exp11 4-stratum mixes: finding L1 improved
(0.042 -> 0.036) but hhcomp/arithmetic stayed ~1.5x over. The scalar
mis-estimates the true keep rate because keep rates vary by household
stratum (exp14 verdict). Hypothesis: replacing the scalar 1/eff_b draw
weight with a per-(bucket, stratum) matrix 1/m[b][s] -- measured from the
generator's own draw-vs-materialize behavior, damped 0.8 toward the scalar
baseline (exp13's damping rule; exp7 documents why naive IPF oscillates) --
moves hhcomp/arithmetic toward 1.0x and finding L1 below 0.036 without
breaking the fixed buckets (medical, depcare, nature 57).

Method (all in-process; only this script and its chronicle are written):
  1. BEFORE: 20k cases, seed 7, current persistent generator.
  2. MEASURE: hook _inject_persistent to attribute drawn/recorded counts to
     the household's (earner x senior) stratum; 60k cases, seed 11.
  3. AFTER: 20k cases, seed 7 (same rng stream as BEFORE -> paired), with
     the damped matrix draw weights patched in via monkeypatch.
  4. Compare element ratios and finding L1; the measured matrix is printed
     as a diagnostic either way.

Real QC microdata is read for aggregate comparison only; no per-row data
is written anywhere.

Usage: python3 experiments/exp20_materialization_matrix.py [--n 20000] [--m 60000]
"""
import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import errors, household  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
EL_COLS = [f"ELEMENT{i}" for i in range(1, 10)]
NTR_COLS = [f"NATURE{i}" for i in range(1, 10)]
BUCKETS = ["earned", "unearned", "shelter", "sua", "medical", "depcare",
           "hhcomp", "arithmetic"]
STRATA = ["no_earner_nonsenior", "earner_nonsenior",
          "no_earner_senior", "earner_senior"]
DAMP = 0.8  # exp13's damping rule: scale the 1/m correction 0.8 toward baseline
MIN_M = 0.10  # below this a cell is a mechanics gap (the corruptor cannot
# materialize there at all): fall back to the scalar rather than letting
# 1/m blow up and steal draw mass from buckets that can materialize.
WCAP = 2.5  # trust region: a matrix weight may not exceed 2.5x the scalar


def stratum_of(facts):
    """Must match the stratum key logic in errors._applicable_buckets."""
    earner = "earner" if facts.get("earned", 0) > 0 else "no_earner"
    senior = "senior" if facts.get("senior_disabled") else "nonsenior"
    return f"{earner}_{senior}"


def real_aggregates():
    """Aggregate-only read of the held-out QC file: finding mix, element
    mix, nature-57 share, and per-case element rates (the chronicle
    convention since exp7: synth count/cases over real count/cases)."""
    finding = Counter()
    bucket = Counter()
    per_case = Counter()
    n57 = 0
    n = 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            finding[int(row["STATUS"])] += 1
            for ec, nc in zip(EL_COLS, NTR_COLS):
                e = (row[ec] or "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                bucket[b] += 1
                per_case[b] += 1
                if (row[nc] or "").strip() == "57":
                    n57 += 1
    v = sum(bucket.values())
    return ({k: finding[k] / n for k in (1, 2, 3)},
            {b: bucket[b] / v for b in BUCKETS},
            n57 / v,
            {b: per_case[b] / n for b in BUCKETS})


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


_ORIG_IP = errors._inject_persistent
DRAWN = Counter()     # (bucket, stratum) -> drawn variances
RECORDED = Counter()  # (bucket, stratum) -> materialized variances


def _measuring_ip(facts, rng, dist, applicable, dir_w, max_attempts,
                  stats=None):
    s = stratum_of(facts)
    local = {"drawn": Counter(), "recorded": Counter()}
    out = _ORIG_IP(facts, rng, dist, applicable, dir_w, max_attempts,
                   stats=local)
    for b, c in local["drawn"].items():
        DRAWN[(b, s)] += c
    for b, c in local["recorded"].items():
        RECORDED[(b, s)] += c
    return out


def build_matrix(dist):
    eff_b = (dist.get("effectiveness") or {}).get("bucket", {})
    mat = {}
    for b in BUCKETS:
        mat[b] = {}
        for s in STRATA:
            d = DRAWN[(b, s)]
            r = RECORDED[(b, s)]
            m = r / d if d else eff_b.get(b, 1.0)
            mat[b][s] = min(1.0, max(0.02, m))
    return mat


def matrix_weight(b, s, matrix, eff_b):
    """Damped per-(bucket, stratum) draw weight. Falls back to the scalar
    in mechanics-gap cells (m < MIN_M: the importance-weight identity
    recorded = drawn x w x m breaks down there -- no weight can make a
    never-materializing cell record, it only steals draw mass). Capped at
    WCAP x the scalar as a trust region."""
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
                    help="cases for the matrix measurement run")
    args = ap.parse_args()

    dist = load_dist(ROOT / "experiments/dist.json")
    real_fm, real_em, real_57, real_pc = real_aggregates()
    print(f"real finding mix: {real_fm[1]:.3f}/{real_fm[2]:.3f}/{real_fm[3]:.3f}")

    print(f"\n[1/3] BEFORE: generating {args.n} cases (seed 7)...", flush=True)
    before = gen_cases(args.n, 7, dist)
    bfm, bem, bs57, bpc = mixes(before)
    show_ratios("BEFORE (current scalar eff_b)", bfm, bem, bs57, bpc,
                real_fm, real_em, real_57, real_pc)

    print(f"\n[2/3] MEASURE: {args.m} cases (seed 11), per-(bucket, stratum) "
          f"draw/record counts...", flush=True)
    errors._inject_persistent = _measuring_ip
    try:
        gen_cases(args.m, 11, dist)
    finally:
        errors._inject_persistent = _ORIG_IP
    matrix = build_matrix(dist)
    print("\nmeasured materialization matrix m[b][s] "
          "(drawn/recorded counts in parens):")
    print(f"  {'bucket':<10}" + "".join(f"{s:>22}" for s in STRATA))
    eff_b = (dist.get("effectiveness") or {}).get("bucket", {})
    for b in BUCKETS:
        row = f"  {b:<10}"
        for s in STRATA:
            d, r = DRAWN[(b, s)], RECORDED[(b, s)]
            row += f"{matrix[b][s]:>10.3f} ({r:>4}/{d:<4})"
        row += f"   scalar={eff_b.get(b, 1.0):.3f}"
        print(row)

    print("\napplied weight ratio (matrix weight / scalar weight), "
          "damped 0.8, gap cells fall back to 1.00:")
    print(f"  {'bucket':<10}" + "".join(f"{s:>22}" for s in STRATA))
    for b in BUCKETS:
        sc = eff_b.get(b, 1.0)
        row = f"  {b:<10}"
        for s in STRATA:
            row += f"{matrix_weight(b, s, matrix, eff_b) * sc:>22.2f}"
        print(row)

    print(f"\n[3/3] AFTER: generating {args.n} cases (seed 7) with the damped "
          f"(0.8) matrix weights...", flush=True)
    errors._inject_persistent = matrix_ip_factory(matrix, dist)
    try:
        after = gen_cases(args.n, 7, dist)
    finally:
        errors._inject_persistent = _ORIG_IP
    afm, aem, as57, apc = mixes(after)
    show_ratios("AFTER (damped per-(bucket, stratum) matrix)", afm, aem, as57,
                apc, real_fm, real_em, real_57, real_pc)

    print("\n== delta (after - before), per-case element ratios ==")
    for b in BUCKETS:
        rb = bpc[b] / real_pc[b] if real_pc[b] else 0
        ra = apc[b] / real_pc[b] if real_pc[b] else 0
        print(f"  {b:<10} {rb:5.2f}x -> {ra:5.2f}x   ({ra - rb:+.2f}x)")
    print(f"  finding L1: {finding_l1(bfm, real_fm):.3f} -> "
          f"{finding_l1(afm, real_fm):.3f}")
    print(f"  nature-57 share ratio: {bs57 / real_57:.2f}x -> "
          f"{as57 / real_57:.2f}x")


if __name__ == "__main__":
    main()
