"""Experiment 29: close the household-sampler base-positivity gaps.

North-star gate: calibration. Exp21 measured per-stratum base-positivity
gaps between the real QC file and the household sampler that are
independent of the variance-injection draw (the draw target is the
marginal empirical mix either way): unearned too low on senior strata
(real 0.95/0.81), shelter too low on earner/senior strata (real
0.88/0.91/0.95), and sua flat 0.72 in the sampler vs a real 0.46-0.88
per-stratum spread. Exp24's next step 6 staged this sampler follow-up.

Hypothesis: stratum-conditioning the sampler's P(unearned>0),
P(shelter>0), P(sua>0) to the real per-stratum aggregates closes all
three gaps to within 0.05 absolute per stratum, keeps finding L1 <=
0.030, and does not regress any per-case element ratio by more than
0.10x -- without touching benefit math or the corruption mechanics.

Method: the generator edit is src/synth/household.py's BASE_POSITIVITY
tables (pre-screen draw probabilities tuned so post-screen P(base>0)
matches the real aggregates). Two dependent calibrations were
re-derived under the new sampler, per their documented maintenance
rules ("re-run whenever the sampler changes"): the per-(bucket,
stratum) materialization matrix in src/synth/errors.py (exp21's
procedure, 150k cases, seed 11; >=200-draw cells take the new value, 8
tiny-sample cells pool the exp24 value) and the 97-resolution direction
coins in experiments/inject.json (calibrate_injection.py phase 2).
Phase-1 persistent coins untouched (realized P(err|status) still on
target). Only this script and its chronicle are written besides those
adoptions; nothing committed.

Arms (20k cases, seed 7; the legacy arms patch in-process with identical
rng call order, so they are paired with AFTER):
  [0] REAL targets: aggregate-only read of the FY2024 QC file --
      exp21's real_aggregates for the per-stratum table (share, base
      positivity), exp24's real_aggregates for the finding mix, per-case
      element rates, and dollar marginals.
  [1] BEFORE: legacy sampler + exp24 matrix + old 97 coins (=
      exp24 defaults exactly).
  [2] MID (attribution): new sampler + OLD matrix + OLD 97 coins --
      isolates the dependent-calibration interaction.
  [3] AFTER: new defaults (new sampler + re-measured matrix + new 97
      coins).
  [4] VALIDATION: base-positivity gaps per stratum; finding L1; per-case
      element ratios; stratum share drift; dollar marginals spot-check
      (exp18's stats).
  [5] VERDICT: gaps <= 0.05 absolute per stratum; finding L1 <= 0.030;
      no per-case element ratio |r-1| worsens by > 0.10x.

Note (2026-09-29): a concurrent worker (exp28) landed _DEPCARE_KID_WEIGHT
and new _NATURE_57_WEIGHT in src/synth/errors.py while this experiment
was running, and temporarily overwrote the re-measured matrix (restored
from experiments/exp28_exp29_matrix_backup.json). Those two mechanisms
are orthogonal to exp29's hypothesis, so all three arms neutralize them
in-process (kid-weight 1.0, exp13 57-weights); the AFTER arm thus
measures exp29's changes only. The live repo combines both experiments'
adoptions; the coordinator merges.

Usage: python3 experiments/exp29_sampler_positivity.py [--n 20000]
"""
import argparse
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
from synth import errors, household  # noqa: E402
from synth.distutil import load_dist  # noqa: E402
import exp21_zerobase_audit as e21  # noqa: E402
import exp24_adopt_rebaseline as e24  # noqa: E402

STRATA = e21.STRATA
BUCKETS = e21.BUCKETS

# Pre-exp29 flat sampler rates, transcribed from the old _sample_unscreened:
# p_une = 0.85 if senior_or_disabled else 0.50; shelter zeroed w.p. 0.37;
# sua drawn w.p. 0.72. Patching BASE_POSITIVITY reproduces the old sampler
# exactly (same rng call order as the new table code).
LEGACY_BASE_POSITIVITY = {
    "unearned": {"no_earner_nonsenior": 0.50, "earner_nonsenior": 0.50,
                 "no_earner_senior": 0.85, "earner_senior": 0.85},
    "shelter": {s: 0.63 for s in STRATA},
    "sua": {s: 0.72 for s in STRATA},
}

# Exp24's MATERIALIZATION_MATRIX (pre-exp29), transcribed from git HEAD
# for the in-process BEFORE/MID arms.
OLD_MATRIX = {
    "earned":     {"no_earner_nonsenior": 0.665037, "earner_nonsenior": 0.819570,
                   "no_earner_senior": 0.723077, "earner_senior": 0.764706},
    "unearned":   {"no_earner_nonsenior": 0.648397, "earner_nonsenior": 0.938224,
                   "no_earner_senior": 0.667449, "earner_senior": 0.788136},
    "shelter":    {"no_earner_nonsenior": 0.228657, "earner_nonsenior": 0.422714,
                   "no_earner_senior": 0.426030, "earner_senior": 0.590444},
    "sua":        {"no_earner_nonsenior": 0.197137, "earner_nonsenior": 0.455617,
                   "no_earner_senior": 0.379898, "earner_senior": 0.525000},
    "medical":    {"no_earner_nonsenior": 0.020000, "earner_nonsenior": 0.020000,
                   "no_earner_senior": 0.522399, "earner_senior": 0.860465},
    "depcare":    {"no_earner_nonsenior": 0.326923, "earner_nonsenior": 0.710247,
                   "no_earner_senior": 0.666667, "earner_senior": 0.500000},
    "hhcomp":     {"no_earner_nonsenior": 0.666667, "earner_nonsenior": 0.648968,
                   "no_earner_senior": 0.545455, "earner_senior": 0.272727},
    "arithmetic": {"no_earner_nonsenior": 1.000000, "earner_nonsenior": 1.000000,
                   "no_earner_senior": 1.000000, "earner_senior": 1.000000},
}

# Pre-exp29 p_over_97_resolve coins, transcribed from inject.json @ git HEAD.
OLD_COINS = {'arithmetic': 0.4857, 'depcare': 0.5412, 'earned': 0.6099,
             'hhcomp': 0.3815, 'medical': 0.5449, 'shelter': 0.5347,
             'sua': 0.6845, 'unearned': 0.6788}


# Pre-exp29 _NATURE_57_WEIGHT (exp13 values), transcribed from git HEAD.
# exp28 changed these in the working tree; the arms below patch them back
# in-process so the comparison isolates exp29's changes.
OLD_57_WEIGHTS = {"medical": 2.86, "shelter": 1.69, "earned": 1.60,
                  "depcare": 1.00}

# exp28's _DEPCARE_KID_WEIGHT is a new mechanism (not in exp24 defaults);
# neutralized in-process (1.0) for the same reason.
NEUTRAL_KID_WEIGHT = {"no_earner_nonsenior": 1.0, "earner_nonsenior": 1.0,
                      "no_earner_senior": 1.0, "earner_senior": 1.0}


@contextmanager
def _patch_exp28_neutral():
    """Neutralize exp28's orthogonal mechanisms in-process (they postdate
    exp24 and are not part of exp29's hypothesis)."""
    old_kw = errors._DEPCARE_KID_WEIGHT
    old_57 = errors._NATURE_57_WEIGHT
    errors._DEPCARE_KID_WEIGHT = NEUTRAL_KID_WEIGHT
    errors._NATURE_57_WEIGHT = dict(OLD_57_WEIGHTS)
    try:
        yield
    finally:
        errors._DEPCARE_KID_WEIGHT = old_kw
        errors._NATURE_57_WEIGHT = old_57


@contextmanager
def legacy_stack(dist):
    """BEFORE arm: legacy sampler + old matrix + old 97 coins
    (= exp24 defaults exactly)."""
    old_bp = household.BASE_POSITIVITY
    old_mx = errors.MATERIALIZATION_MATRIX
    old_coins = dict(dist["injection_rate"]["p_over_97_resolve"])
    household.BASE_POSITIVITY = LEGACY_BASE_POSITIVITY
    errors.MATERIALIZATION_MATRIX = OLD_MATRIX
    dist["injection_rate"]["p_over_97_resolve"] = dict(OLD_COINS)
    with _patch_exp28_neutral():
        try:
            yield
        finally:
            household.BASE_POSITIVITY = old_bp
            errors.MATERIALIZATION_MATRIX = old_mx
            dist["injection_rate"]["p_over_97_resolve"] = old_coins


@contextmanager
def mid_stack(dist):
    """MID arm: new sampler + OLD matrix + OLD 97 coins."""
    old_mx = errors.MATERIALIZATION_MATRIX
    old_coins = dict(dist["injection_rate"]["p_over_97_resolve"])
    errors.MATERIALIZATION_MATRIX = OLD_MATRIX
    dist["injection_rate"]["p_over_97_resolve"] = dict(OLD_COINS)
    with _patch_exp28_neutral():
        try:
            yield
        finally:
            errors.MATERIALIZATION_MATRIX = old_mx
            dist["injection_rate"]["p_over_97_resolve"] = old_coins


@contextmanager
def after_stack():
    """AFTER arm: live sampler/matrix/coins (= exp29's new defaults),
    with exp28's orthogonal mechanisms neutralized in-process so the
    arm measures exp29's changes only."""
    with _patch_exp28_neutral():
        yield


def stratum_shares(cases):
    c = Counter(e21.stratum_of(case["facts"]) for case in cases)
    n = len(cases)
    return {s: c[s] / n for s in STRATA}


def show_base(label, sb, stab):
    print(f"\n== {label}: sampler P(base>0) vs real ==")
    keys = {"unearned": "p_une_base", "shelter": "p_shelter_base",
            "sua": "p_sua_base"}
    worst = 0.0
    print(f"  {'stratum':<22}" + "".join(f"{b:>16}" for b in
                                        ("unearned", "shelter", "sua")))
    for s in STRATA:
        row = f"  {s:<22}"
        for b in ("unearned", "shelter", "sua"):
            gap = abs(sb[s][b] - stab[s][keys[b]])
            worst = max(worst, gap)
            row += f"{sb[s][b]:>7.3f} (d{gap:+.3f})".rjust(16)
        print(row)
    print(f"  worst |gap| = {worst:.3f} (verdict bar 0.05)")
    return worst


def show_cal(label, m, real, before_ratios=None):
    fm, pc = m["finding"], m["per_case"]
    l1 = e24.l1(fm, real["finding"])
    print(f"\n== {label} ==")
    print(f"  finding mix: {fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f}  L1={l1:.3f}")
    print(f"  {'bucket':<10}{'per-case':>9}{'regress':>9}")
    worst_reg = 0.0
    ratios = {}
    for b in BUCKETS:
        r = pc[b] / real["per_case"][b] if real["per_case"][b] else 0
        ratios[b] = r
        reg = ""
        if before_ratios is not None:
            reg_amt = abs(r - 1.0) - abs(before_ratios[b] - 1.0)
            worst_reg = max(worst_reg, reg_amt)
            reg = f"{reg_amt:+.2f}"
        print(f"  {b:<10}{r:>8.2f}x{reg:>9}")
    if before_ratios is not None:
        print(f"  worst |r-1| regression vs BEFORE: {worst_reg:+.3f} "
              f"(bar +0.10)")
    return ratios, worst_reg, l1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    args = ap.parse_args()

    dist = load_dist(ROOT / "experiments/dist.json")

    print("[0] REAL aggregates (FY2024, aggregate-only read)...", flush=True)
    real = e24.real_aggregates()
    _, _, _, _, real_stab = e21.real_aggregates()
    print(f"  real finding mix: {real['finding'][1]:.3f}/"
          f"{real['finding'][2]:.3f}/{real['finding'][3]:.3f}")
    print(f"  {'stratum':<22}{'share':>7}{'P(une>0)':>9}{'P(sh>0)':>9}"
          f"{'P(sua)':>8}")
    for s in STRATA:
        t = real_stab[s]
        print(f"  {s:<22}{t['share']:>7.3f}{t['p_une_base']:>9.3f}"
              f"{t['p_shelter_base']:>9.3f}{t['p_sua_base']:>8.3f}")

    with legacy_stack(dist):
        print("\n[1] BEFORE (= exp24 defaults): sampler base rates "
              "(100k hh, seed 5)...", flush=True)
        sb_before = e21.synth_base_rates(100000, 5)
        w_before = show_base("BEFORE sampler", sb_before, real_stab)
        print(f"[1] BEFORE: generating {args.n} cases (seed 7)...",
              flush=True)
        m_before = e24.mixes(e24.gen_cases(args.n, 7, dist))

    with mid_stack(dist):
        print(f"\n[2] MID (new sampler, OLD matrix+coins): generating "
              f"{args.n} cases (seed 7)...", flush=True)
        m_mid = e24.mixes(e24.gen_cases(args.n, 7, dist))

    print("\n[3] AFTER (new defaults): sampler base rates (100k hh, "
          "seed 5)...", flush=True)
    sb_after = e21.synth_base_rates(100000, 5)
    w_after = show_base("AFTER sampler", sb_after, real_stab)
    print(f"[3] AFTER: generating {args.n} cases (seed 7, paired)...",
          flush=True)
    with after_stack():
        cases_after = e24.gen_cases(args.n, 7, dist)
    m_after = e24.mixes(cases_after)
    sh_after = stratum_shares(cases_after)

    print("\n[4] CALIBRATION: finding mix + per-case element ratios")
    rb, _, l1_before = show_cal("BEFORE (= exp24 defaults)", m_before, real)
    _, _, l1_mid = show_cal("MID (new sampler, stale matrix+coins)",
                            m_mid, real)
    ra, worst_reg, l1_after = show_cal("AFTER (new defaults)", m_after,
                                       real, rb)
    print(f"\n  finding L1: before {l1_before:.3f} -> mid {l1_mid:.3f} -> "
          f"after {l1_after:.3f} (bar 0.030)")

    print("\n[4] stratum shares: real vs AFTER (matrix-interaction check)")
    print(f"  {'stratum':<22}{'real':>7}{'after':>8}")
    for s in STRATA:
        print(f"  {s:<22}{real_stab[s]['share']:>7.3f}"
              f"{sh_after[s]:>8.3f}")

    print("\n[4] dollar marginals spot-check (error cases, absolute $)")
    for name, vals in (("real", real["d_all"]),
                       ("before", m_before["d_all"]),
                       ("after", m_after["d_all"])):
        st = e24.dollar_stats(vals)
        print(f"  {name:<7} n={st['n']:>5} mean={st['mean']:>6.1f} "
              f"p10={st['p10']:>6.1f} p25={st['p25']:>6.1f} "
              f"p50={st['p50']:>6.1f} p90={st['p90']:>6.1f} "
              f"p99={st['p99']:>7.1f} le56={st['le56']:.2f}")
    print("  over/under medians (real vs synth asymmetry check):")
    for name, mo, mu in (("real", real["d_over"], real["d_under"]),
                         ("before", m_before["d_over"], m_before["d_under"]),
                         ("after", m_after["d_over"], m_after["d_under"])):
        so = e24.dollar_stats(mo)["p50"] if mo else float("nan")
        su = e24.dollar_stats(mu)["p50"] if mu else float("nan")
        print(f"  {name:<7} med_over={so:>6.1f} med_under={su:>6.1f}")

    print("\n[5] VERDICT")
    checks = [
        ("base-positivity gaps <= 0.05 per stratum", w_after <= 0.05,
         f"worst {w_after:.3f}"),
        ("finding L1 <= 0.030", l1_after <= 0.030, f"L1 {l1_after:.3f}"),
        ("no element ratio regresses > 0.10x", worst_reg <= 0.10,
         f"worst {worst_reg:+.3f}"),
    ]
    held = True
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})")
        held = held and ok
    print(f"  => {'HOLDS' if held else 'DOES NOT HOLD'}")


if __name__ == "__main__":
    main()
