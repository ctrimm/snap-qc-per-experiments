"""Error injector: corrupts true household facts the way QC variances describe,
producing labeled (element, nature, cause, direction, dollar) training cases.

The (bucket, nature, cause) mix is sampled from the empirical distribution
built from the real FY2024 QC file (see experiments/build_dist.py). Each
corruption is mechanics-faithful: it changes the facts the agency *used*,
and the issued benefit is recomputed from the corrupted facts — so the
direction and dollar error emerge from the benefit math, not from labels.
"""
import copy
import random

from . import benefit as benefit_mod
from . import params

# most common real element code per bucket -> representative code we emit
REPRESENTATIVE_ELEMENT = {
    "earned": 311, "unearned": 331, "shelter": 363, "sua": 364,
    "medical": 365, "depcare": 323, "hhcomp": 150, "arithmetic": 520,
}

SUPPORTED_BUCKETS = list(REPRESENTATIVE_ELEMENT.keys())


def _u(rng, lo, hi):
    return rng.uniform(lo, hi)


def _corrupt_income(facts, nature, rng, field):
    f = copy.deepcopy(facts)
    base = f[field]
    if base == 0:
        # nothing reported: the only honest income variance is an unreported source
        f[field] = round(_u(rng, 200, 900), 2)
        return f, 35
    if nature == 44:      # less income than budgeted -> agency over-counted -> underissuance
        f[field] = round(base * (1 - _u(rng, 0.10, 0.40)), 2)
    elif nature == 37:    # known source not included -> agency under-counted -> overissuance
        f[field] = round(base * (1 - _u(rng, 0.30, 0.60)), 2)
    elif nature == 35:    # unreported source -> agency missed income -> overissuance
        f[field] = round(base + _u(rng, 200, 900), 2)
    else:                 # 38 default: more income than budgeted -> overissuance
        f[field] = round(base * (1 + _u(rng, 0.10, 0.50)), 2)
    return f, None


def _corrupt_deduction(facts, nature, rng, field):
    f = copy.deepcopy(facts)
    base = f[field]
    if nature == 57:      # budgeted too little -> underissuance
        f[field] = round(base * (1 - _u(rng, 0.15, 0.40)), 2)
    elif nature == 53:    # included but shouldn't be -> overissuance
        f[field] = round(base + _u(rng, 100, 300), 2)
    elif nature == 52:    # should have been included, wasn't -> underissuance
        f[field] = 0.0
    else:                 # 56 default: budgeted too much -> overissuance
        f[field] = round(base * (1 + _u(rng, 0.15, 0.50)), 2)
    return f, None


def _corrupt_hhcomp(facts, nature, rng):
    f = copy.deepcopy(facts)
    if nature == 7:       # ineligible person included -> overissuance
        f["hh_size"] = min(f["hh_size"] + 1, 8)
    else:                 # 6/13 default: eligible person excluded -> underissuance
        f["hh_size"] = max(f["hh_size"] - 1, 1)
    return f, None


def _apply_one(facts, bucket, nature, rng):
    if bucket in ("earned",):
        return _corrupt_income(facts, nature, rng, "earned")
    if bucket == "unearned":
        return _corrupt_income(facts, nature, rng, "unearned")
    if bucket in ("shelter", "sua"):
        return _corrupt_deduction(facts, nature, rng, "shelter")
    if bucket == "medical":
        return _corrupt_deduction(facts, nature, rng, "medical_exp")
    if bucket == "depcare":
        return _corrupt_deduction(facts, nature, rng, "depcare")
    if bucket == "hhcomp":
        return _corrupt_hhcomp(facts, nature, rng)
    return copy.deepcopy(facts), None  # arithmetic handled as direct benefit noise


# Measured from the FY2024 QC file: P(variance in bucket | base amount is zero)
# relative to P(variance | base > 0). Lets zero-base households draw income /
# deduction variances at the real (low) rate instead of never or always.
ZERO_BASE_WEIGHT = {
    "earned": 0.018,
    "unearned": 0.091,
    "shelter": 0.227,
    "medical": 0.036,
    "depcare": 0.008,
}

_BASE_FIELD = {
    "earned": "earned", "unearned": "unearned", "shelter": "shelter",
    "medical": "medical_exp", "depcare": "depcare", "sua": "sua",
}


def _applicable_buckets(facts: dict, dist: dict, rng: random.Random):
    """Buckets weighted by empirical probability, scaled down when the base
    amount is zero (a household with no earnings can still get an earned-
    income variance — an unreported source — but rarely does)."""
    cands = {}
    for bucket, p in dist["bucket_probs"].items():
        w = 1.0
        field = _BASE_FIELD.get(bucket)
        if field is not None:
            base = facts[field]
            base_pos = (base == 1) if bucket == "sua" else (base > 0)
            if not base_pos:
                w = ZERO_BASE_WEIGHT.get(bucket, 1.0)
        # hhcomp and arithmetic always fully applicable
        if w > 0:
            cands[bucket] = p * w
    if not cands:  # nothing to get wrong except raw arithmetic
        cands = {"arithmetic": 1.0} if "arithmetic" in dist["bucket_probs"] else {}
    return cands


def _sample(rng, probs: dict):
    keys, weights = zip(*probs.items())
    return rng.choices(keys, weights=weights)[0]


def _clean_case(facts, correct):
    return {
        "facts": facts,
        "issued_facts": copy.deepcopy(facts),
        "correct_benefit": correct,
        "issued_benefit": correct,
        "finding": 1,
        "dollar_error": 0,
        "reportable": False,
        "variances": [],
    }


def inject(facts: dict, rng: random.Random, dist: dict):
    """Returns (issued_facts, issued_benefit, variances, finding, dollar_error)."""
    correct = benefit_mod.compute(facts)["benefit"]

    if rng.random() >= dist["error_rate"]:
        return _clean_case(facts, correct)

    applicable = _applicable_buckets(facts, dist, rng)
    if not applicable:
        applicable = {"arithmetic": 1.0}
    # Correct for retry-filtering bias: buckets whose corruptions often no-op
    # (max-allotment ceiling, shelter cap absorption) are upweighted so the
    # post-retry mix matches the empirical mix. See experiments/eff.json.
    eff = dist.get("effectiveness")
    if eff:
        applicable = {b: p / max(eff.get(b, 1.0), 0.02) for b, p in applicable.items()}

    # A variance that doesn't move the benefit is a no-op: retry with a
    # different draw (real QC files carry ~zero variances on correct cases).
    for _ in range(3):
        corrupted = copy.deepcopy(facts)
        benefit_noise = 0.0
        variances = []
        n_var = 2 if rng.random() < 0.15 else 1
        for _ in range(n_var):
            bucket = _sample(rng, applicable)
            nature = int(_sample(rng, dist["nature_given_bucket"][bucket]))
            cause = int(_sample(rng, dist["cause_given_bucket"][bucket]))
            if bucket == "arithmetic":
                benefit_noise += rng.choice([-1, 1]) * _u(rng, 10, 60)
            else:
                corrupted, nature_override = _apply_one(corrupted, bucket, nature, rng)
                if nature_override is not None:
                    nature = nature_override
            variances.append({
                "element": REPRESENTATIVE_ELEMENT[bucket],
                "element_bucket": bucket,
                "nature": nature,
                "cause": cause,
                "timing": "after" if nature == 97 else "at_action",
            })
        issued = benefit_mod.compute(corrupted)["benefit"] + benefit_noise
        issued = max(0, int(round(issued)))
        if issued != correct:
            dollar = abs(correct - issued)
            return {
                "facts": facts,               # true facts (what QC found)
                "issued_facts": corrupted,    # facts the agency used
                "correct_benefit": correct,
                "issued_benefit": issued,
                "finding": 2 if issued > correct else 3,
                "dollar_error": dollar,
                "reportable": dollar > params.QC_ERROR_THRESHOLD,
                "variances": variances,
            }
    return _clean_case(facts, correct)
