"""Experiment 18 - dollar-error mechanisms (calibration gate).

North-star gate: **calibration**. exp16 found the dollar-error marginal
drifted: synth p10 is 5.5x real, only 37% of synth errors are <= $56 vs
69% real, the over/under dollar asymmetry is inverted at every quantile,
and synth over p99 is $319 vs real $603 (no whole-unit ineligibility).

This experiment prototypes three generator mechanisms in-script (production
code in src/synth is NOT touched; if a mechanism verifies it can be merged
later):

  1. small-error mode: timing variances (nature 97 -- 44% of real error
     cases, median $15-20 in real QC) take small perturbations (+/- $2-30
     on the underlying amount, ~$1-9 on the benefit through the 30%
     pass-through) instead of the full coarse magnitudes the 97-resolution
     coin currently renders. Recorded under the same (element, nature)
     codes -- QC natures don't distinguish magnitude -- so the recorded
     taxonomy mix is unchanged. A small residual fraction for non-97
     natures is grid-searched.
  2. whole-unit ineligibility: a new over-error mode where the unit is
     ineligible, correct benefit $0, error = full issued benefit. Restores
     the extreme over tail (real over p99 $603 vs synth $319).
  3. asymmetry repair: whole-unit overs plus direction-specific small-error
     fractions flip the over/under gap back to real's sign
     (real: over > under at median/mean/p90/p99).

Usage:
    python3 experiments/exp18_dollar_mechanisms.py \
        --real ../snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv \
        --dist experiments/dist.json

Grid-searches mechanism knobs on 20k-case synth draws and reports the
dollar marginal (p10/p25/p50/p90/p99, share <= $56, over/under gaps) and
the finding-mix L1 against real FY2024 aggregates. Real microdata is
held-out validation: aggregates are read, nothing per-row is committed.
"""
import argparse
import copy
import csv
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from synth import benefit as benefit_mod
from synth import errors, household
from synth.distutil import load_dist

QUANTS = (0.10, 0.25, 0.50, 0.90, 0.99)

# --------------------------------------------------------------------------
# real aggregates (held-out; read only)
# --------------------------------------------------------------------------

def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def load_real(path):
    signed, overs, unders = [], [], []
    n = 0
    n_correct = 0
    n_full_unit = 0
    n_over = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            n += 1
            st = row["STATUS"].strip()
            if st == "1":
                n_correct += 1
                continue
            if st not in ("2", "3"):
                continue
            a = float(row["AMTERR"] or 0)
            if st == "2":
                signed.append(a)
                overs.append(a)
                n_over += 1
                if float(row["FSBEN"] or 0) == 0 and float(row["RAWBEN"] or 0) > 0:
                    n_full_unit += 1
            else:
                signed.append(-a)
                unders.append(a)
    return {
        "signed": signed, "overs": overs, "unders": unders,
        "n": n, "n_correct": n_correct,
        "full_unit_share_of_over": n_full_unit / n_over if n_over else 0.0,
        "n_over": n_over, "n_under": len(unders),
    }


def summarize(signed):
    ab = [abs(x) for x in signed]
    overs = [x for x in signed if x > 0]
    unders = [-x for x in signed if x < 0]
    s = {"n_error": len(signed), "n_over": len(overs), "n_under": len(unders)}
    for q in QUANTS:
        s[f"p{int(q*100)}"] = pct(ab, q)
    s["mean"] = statistics.fmean(ab) if ab else float("nan")
    s["share_le56"] = sum(1 for x in ab if x <= 56) / len(ab) if ab else float("nan")
    for tag, xs in (("over", overs), ("under", unders)):
        s[f"p10_{tag}"] = pct(xs, 0.10)
        s[f"p25_{tag}"] = pct(xs, 0.25)
        s[f"median_{tag}"] = pct(xs, 0.50)
        s[f"p90_{tag}"] = pct(xs, 0.90)
        s[f"p99_{tag}"] = pct(xs, 0.99)
        s[f"mean_{tag}"] = statistics.fmean(xs) if xs else float("nan")
        s[f"share_le56_{tag}"] = sum(1 for x in xs if x <= 56) / len(xs) if xs else float("nan")
    return s

# --------------------------------------------------------------------------
# mechanism prototypes (monkey-patches on errors, experiment-local)
# --------------------------------------------------------------------------

# (1) small-error mode, v3: conditioned on nature 97 (timing), not direction.
# Real FY2024: 44% of error cases carry a 97 variance and 97s are small
# (over p50 $20 / under p50 $15, p90 $49/$45) -- the generator instead
# renders 97s with full coarse magnitudes via the resolution coin. Timing
# variances now take the small perturbation; non-97 natures keep coarse
# magnitudes except for a small residual fraction (grid search).
SMALL_97 = True
SMALL_NON97 = {"over": 0.0, "under": 0.0}
SMALL_LO, SMALL_HI = 2.0, 30.0  # dollars on the underlying amount


def _small_perturb(base, direction, rng, invert=False):
    """Small mis-keying: +/- $2-30 on the amount. `direction` is the desired
    finding: 'over' means the agency should pay too much. For income that
    means under-counting (base - delta); for deductions it means
    over-counting (base + delta), hence `invert=True` on the deduction path."""
    delta = rng.uniform(SMALL_LO, SMALL_HI)
    if (direction == "over") != invert:
        return round(base - delta, 2)
    return round(base + delta, 2)


def _dir_of_income_nature(nature, base):
    # which finding does this nature produce?
    if nature == 44:
        return "under"
    return "over"


def _small_truth_income(rng):
    """Small unreported income: the truth had $20-150 the agency never saw."""
    return round(rng.uniform(20, 150), 2)


def _small_fabricated_income(rng):
    """Small phantom income: the agency counted $30-120 that was never there."""
    return round(rng.uniform(30, 120), 2)


def _small_truth_deduction(field, rng):
    """Small omitted deduction: the truth had a modest amount the agency
    missed (a utility bill slice, a small copay total, a few hours of care).
    Medical must clear the $35 threshold to move the benefit."""
    if field == "shelter":
        return round(rng.uniform(30, 150), 2)
    if field == "medical_exp":
        return round(rng.uniform(36, 90), 2)
    if field == "depcare":
        return round(rng.uniform(20, 100), 2)
    return round(rng.uniform(20, 100), 2)


def _small_fabricated_deduction(field, rng):
    """Small phantom deduction: the agency claimed $20-100 that doesn't exist."""
    return round(rng.uniform(20, 100), 2)


def _take_small(from_97, direction, rng):
    """v3: timing (97) variances always take the small mode; non-97 natures
    take it with the residual per-direction fraction."""
    if from_97 and SMALL_97:
        return True
    f = SMALL_NON97[direction]
    return f > 0 and rng.random() < f


def _patched_corrupt_income(agency, truth, nature, rng, field, bucket, dist,
                            _force_97_dir=None, _orig=None):
    base = truth[field]
    from_97 = nature == 97
    resolved = nature
    if from_97:
        resolved = 38 if errors._resolve_97_dir(bucket, dist, rng, _force_97_dir) else 44
    direction = _dir_of_income_nature(resolved, base)
    if _take_small(from_97, direction, rng):
        if base == 0:
            if resolved == 44:
                # small phantom income -> underissuance
                agency[field] = _small_fabricated_income(rng)
                return None, None
            # small unreported source -> overissuance; truth corrected up
            override = None if from_97 else (35 if resolved == 38 else resolved)
            return {field: _small_truth_income(rng)}, override
        # small mis-keying on a positive base (keeps the drawn nature label)
        agency[field] = max(0.0, _small_perturb(base, direction, rng))
        return None, None
    return _orig(agency, truth, nature, rng, field, bucket, dist,
                 _force_97_dir=_force_97_dir)


def _dir_of_ded_nature(nature):
    if nature in (57, 52):
        return "under"
    return "over"


def _patched_corrupt_deduction(agency, truth, nature, rng, field, bucket, dist,
                               _force_97_dir=None, _orig=None):
    base = truth[field]
    from_97 = nature == 97
    resolved = nature
    if from_97:
        # Timing nature on any base: resolve directionally for the small-mode
        # decision (the recorded nature stays 97).
        resolved = 56 if errors._resolve_97_dir(bucket, dist, rng, _force_97_dir) else 57
    direction = _dir_of_ded_nature(resolved)
    if _take_small(from_97, direction, rng):
        if field == "medical_exp" and not truth["senior_disabled"]:
            return _orig(agency, truth, nature, rng, field, bucket, dist,
                         _force_97_dir=_force_97_dir)
        if base == 0:
            if direction == "under":
                # small omitted deduction -> underissuance; truth corrected up
                return {field: _small_truth_deduction(field, rng)}, None
            # small phantom deduction -> overissuance
            agency[field] = _small_fabricated_deduction(field, rng)
            return None, None
        # small mis-keying on a positive base (keeps the drawn nature label)
        agency[field] = max(0.0, _small_perturb(base, direction, rng, invert=True))
        return None, None
    return _orig(agency, truth, nature, rng, field, bucket, dist,
                 _force_97_dir=_force_97_dir)


# (2) whole-unit ineligibility: with probability P_UNIT per case the unit is
# ineligible; the agency pays the computed benefit anyway. Correct benefit
# $0, dollar error = full issued benefit (an overissuance).
P_UNIT = 0.0
UNIT_ELEMENT = 150  # "Unit composition" (hhcomp bucket code)


def _unit_ineligible_case(facts, rng):
    issued = benefit_mod.compute(facts)["benefit"]
    return {
        "facts": facts,
        "issued_facts": copy.deepcopy(facts),
        "correct_benefit": 0,
        "issued_benefit": issued,
        "finding": 2,
        "dollar_error": issued,
        "reportable": issued > 56,
        "variances": [{
            "element": UNIT_ELEMENT,
            "element_bucket": "hhcomp",
            "nature": 99,
            "cause": 10,   # policy incorrectly applied
            "timing": "at_action",
        }],
    }


def generate(n, seed, dist, small_97, non97_over, non97_under, p_unit,
             coin_scale=1.0, under_boost=1.0):
    """Experiment-local generator: stock inject() with patched corruptors,
    plus a whole-unit-ineligibility draw layered on top.

    coin_scale recalibrates the injection coin: the small-error mode raises
    the attrition rate (more perturbations floor to $0 benefit change), so
    the exp7-calibrated coin under-realizes errors. Scaling it back up is
    the same recalibration calibrate_injection.py performs after any
    mechanism change; it is done here on an in-script copy of dist so the
    committed inject.json is untouched.

    under_boost scales the under-direction importance weights (dir_weight):
    small unders are absorbed by the $23 minimum-benefit floor / shelter-cap
    mechanics more often than small overs hit the max-allotment ceiling, so
    the realized over/under ratio skews over-heavy. Same importance-weight
    idea as exp13's nature-57 correction."""
    global P_UNIT, SMALL_97
    SMALL_97 = small_97
    SMALL_NON97["over"] = non97_over
    SMALL_NON97["under"] = non97_under
    P_UNIT = p_unit
    if coin_scale != 1.0 or under_boost != 1.0:
        dist = copy.deepcopy(dist)
        pc = dist["injection_rate"]["persistent"]
        pc["earner"] = min(0.99, pc["earner"] * coin_scale)
        pc["no_earner"] = min(0.99, pc["no_earner"] * coin_scale)
        for bw in dist["effectiveness"]["dir_weight"].values():
            bw["under"] = bw.get("under", 1.0) * under_boost
    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        facts = household.sample_household(rng)
        if p_unit > 0 and rng.random() < p_unit:
            cases.append(_unit_ineligible_case(facts, rng))
            continue
        cases.append(errors.inject(facts, rng, dist, persistent_buckets=True))
    return cases


def finding_mix_l1(cases, real):
    s_over = sum(1 for c in cases if c["finding"] == 2) / len(cases)
    s_under = sum(1 for c in cases if c["finding"] == 3) / len(cases)
    s_ok = 1 - s_over - s_under
    r_over = real["n_over"] / real["n"]
    r_under = real["n_under"] / real["n"]
    r_ok = real["n_correct"] / real["n"]
    return abs(s_over - r_over) + abs(s_under - r_under) + abs(s_ok - r_ok), \
        (s_ok, s_over, s_under)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--dist", required=True)
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--out", default="/tmp/exp18_results.json")
    args = ap.parse_args()

    real = load_real(args.real)
    r = summarize(real["signed"])
    print(f"real: {real['n']} rows, {r['n_error']} error cases "
          f"(over {r['n_over']}, under {r['n_under']}); "
          f"full-unit share of overs: {real['full_unit_share_of_over']:.3f}")
    print(f"real share<=56: overall {r['share_le56']:.3f} "
          f"over {r['share_le56_over']:.3f} under {r['share_le56_under']:.3f}")

    dist = load_dist(args.dist)

    # install patches
    orig_income = errors._corrupt_income
    orig_ded = errors._corrupt_deduction

    def patched_income(agency, truth, nature, rng, field, bucket, dist,
                       _force_97_dir=None):
        return _patched_corrupt_income(agency, truth, nature, rng, field, bucket,
                                       dist, _force_97_dir, _orig=orig_income)

    def patched_ded(agency, truth, nature, rng, field, bucket, dist,
                    _force_97_dir=None):
        return _patched_corrupt_deduction(agency, truth, nature, rng, field, bucket,
                                          dist, _force_97_dir, _orig=orig_ded)

    errors._corrupt_income = patched_income
    errors._corrupt_deduction = patched_ded
    # arithmetic is referenced as errors-internal only in _inject_persistent,
    # which calls the module-level helpers above -- patched in place.

    grid = [
        # (s97, non97_so, non97_su, pu, coin_scale, under_boost) -- v3: small
        # mode conditioned on nature 97 (timing), the real small-error mass,
        # plus a direction residual for the remaining small mass
        (False, 0.0, 0.0, 0.0, 1.00, 1.0),    # baseline: stock generator
        (True, 0.25, 0.35, 0.0125, 1.05, 1.25),
        (True, 0.35, 0.45, 0.0125, 1.05, 1.25),
        (True, 0.25, 0.35, 0.010, 1.00, 1.2),
    ]

    results = {"real": r, "configs": []}
    header_printed = False
    for i, (s97, so, su, pu, cs, ub) in enumerate(grid):
        cases = generate(args.n, 1000 + i, dist, s97, so, su, pu,
                         coin_scale=cs, under_boost=ub)
        signed = [c["issued_benefit"] - c["correct_benefit"]
                  for c in cases if c["finding"] in (2, 3)]
        s = summarize(signed)
        l1, mix = finding_mix_l1(cases, real)
        s.update({"small_97": s97, "small_non97_over": so, "small_non97_under": su,
                  "p_unit": pu, "coin_scale": cs, "under_boost": ub,
                  "finding_l1": l1, "finding_mix": mix})
        results["configs"].append(s)
        if not header_printed:
            print(f"\n{'cfg':>3} {'s97':>3} {'n97o':>4} {'n97u':>4} {'pu':>5} "
                  f"{'p10':>6} {'p25':>6} {'p50':>6} {'p90':>6} {'p99':>6} "
                  f"{'<=56':>6} {'medO':>6} {'medU':>6} {'mnO':>6} {'mnU':>6} "
                  f"{'p90O':>6} {'p90U':>6} {'p99O':>6} {'p99U':>6} {'L1':>6} "
                  f"{'ok/ov/un':>18}")
            print(f"{'':>3} {'':>4} {'':>4} {'':>5} "
                  f"{r['p10']:6.0f} {r['p25']:6.0f} {r['p50']:6.0f} "
                  f"{r['p90']:6.0f} {r['p99']:6.0f} {r['share_le56']:6.2f} "
                  f"{r['median_over']:6.0f} {r['median_under']:6.0f} "
                  f"{r['mean_over']:6.0f} {r['mean_under']:6.0f} "
                  f"{r['p90_over']:6.0f} {r['p90_under']:6.0f} "
                  f"{r['p99_over']:6.0f} {r['p99_under']:6.0f} {'':>6}  <- real")
            header_printed = True
        print(f"{i:>3} {int(s97):>3d} {so:4.2f} {su:4.2f} {pu:5.3f} "
              f"{s['p10']:6.0f} {s['p25']:6.0f} {s['p50']:6.0f} "
              f"{s['p90']:6.0f} {s['p99']:6.0f} {s['share_le56']:6.2f} "
              f"{s['median_over']:6.0f} {s['median_under']:6.0f} "
              f"{s['mean_over']:6.0f} {s['mean_under']:6.0f} "
              f"{s['p90_over']:6.0f} {s['p90_under']:6.0f} "
              f"{s['p99_over']:6.0f} {s['p99_under']:6.0f} {l1:6.3f} "
              f"mix={mix[0]:.3f}/{mix[1]:.3f}/{mix[2]:.3f} cs={cs:.2f} ub={ub:.1f}")

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nresults -> {args.out}")


if __name__ == "__main__":
    sys.exit(main())
