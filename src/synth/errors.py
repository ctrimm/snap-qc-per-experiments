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


def _typical_amount(field, rng):
    """Sampler-consistent magnitude for truth correction on omission-type
    variances (the truth had an amount the agency never saw)."""
    if field == "shelter":
        return round(rng.uniform(350, 1700), 2)
    if field == "medical_exp":
        return round(rng.uniform(20, 400), 2)
    if field == "depcare":
        return round(rng.uniform(100, 650), 2)
    return round(_u(rng, 200, 900), 2)  # earned / unearned


# Direction classes for retry-bias correction (see measure_effectiveness.py).
# Over/under group natures by their benefit effect; 97 resolves
# stochastically so it lives in "other" with its blended rate.
_OVER_NATURES = {35, 37, 38, 53, 56, 7}
_UNDER_NATURES = {44, 52, 57, 6, 13}


def _dirclass(nature):
    if nature in _OVER_NATURES:
        return "over"
    if nature in _UNDER_NATURES:
        return "under"
    return "other"


def _p_over_97(bucket, dist):
    """Resolution coin for timing-nature (97) variances.

    The empirical P(over | bucket, 97) is the *realized* target, but
    over-direction deduction corruptions materialize less often than
    under-direction ones (the excess-shelter cap absorbs increases), so the
    resolution coin is attrition-corrected (see calibrate_injection.py) to
    land the realized direction on the empirical target.
    """
    r = dist.get("injection_rate", {}).get("p_over_97_resolve", {})
    if bucket in r:
        return r[bucket]
    return dist.get("p_over_97_given_bucket", {}).get(bucket, 0.5)


def _resolve_97_dir(bucket, dist, rng, force=None):
    if force == "over":
        return True
    if force == "under":
        return False
    return rng.random() < _p_over_97(bucket, dist)


def _corrupt_income(agency, truth, nature, rng, field, bucket, dist,
                   _force_97_dir=None):
    """Corrupt agency-view income facts in place.

    Convention: `truth` holds the verified facts; `agency` is mutated toward
    what the agency used. issued > correct means the agency paid too much
    (overissuance): the agency *under*-counted income or *over*-counted
    deductions.

    Returns (truth_correction, nature_override). truth_correction is a
    {field: value} dict only for the unreported-source-on-zero-base case,
    where the sampled truth itself must gain the unreported income.
    """
    base = truth[field]
    from_97 = nature == 97
    if from_97:
        # Timing nature: resolve directionally; the recorded nature stays 97.
        nature = 38 if _resolve_97_dir(bucket, dist, rng, _force_97_dir) else 44
    if base == 0:
        if nature == 44:
            # Agency counted income that was never there -> underissuance.
            agency[field] = round(_u(rng, 200, 900), 2)
            return None, None
        # Omission family: the truth had income the agency never saw, so the
        # sampled truth (zero) is corrected upward; the agency view stays 0.
        # A reviewer would code a drawn 38 on a zero base as 35 (but a drawn
        # 97 stays 97).
        override = None if from_97 else (35 if nature == 38 else nature)
        return {field: round(_u(rng, 200, 900), 2)}, override
    if nature == 44:      # less income than budgeted -> agency over-counted -> underissuance
        agency[field] = round(base * (1 + _u(rng, 0.10, 0.40)), 2)
    elif nature == 37:    # known source not included -> agency under-counted -> overissuance
        agency[field] = round(base * (1 - _u(rng, 0.30, 0.60)), 2)
    elif nature == 35:    # unreported source -> agency missed part of income -> overissuance
        agency[field] = round(max(0.0, base - _u(rng, 200, 900)), 2)
    else:                 # 38 default: more income than budgeted -> agency under-counted -> overissuance
        agency[field] = round(base * (1 - _u(rng, 0.10, 0.50)), 2)
    return None, None


def _corrupt_deduction(agency, truth, nature, rng, field, bucket, dist,
                     _force_97_dir=None):
    base = truth[field]
    if base == 0:
        if nature == 97:
            # Timing nature on a zero base: resolve directionally.
            if _resolve_97_dir(bucket, dist, rng, _force_97_dir):
                agency[field] = round(_u(rng, 100, 300), 2)  # fabricated -> over
            else:
                if field == "medical_exp" and not truth["senior_disabled"]:
                    return None, None
                return {field: _typical_amount(field, rng)}, None  # omitted -> under
            return None, None
        if nature in (52, 57):
            # Omission: the truth had the deduction, the agency omitted it.
            # Correct the truth upward; the agency view stays 0 -> underissuance.
            # Medical is only coherent for elderly/disabled households.
            if field == "medical_exp" and not truth["senior_disabled"]:
                return None, None
            return {field: _typical_amount(field, rng)}, None
        if nature == 53:
            # Agency claimed a deduction that doesn't exist -> overissuance.
            agency[field] = round(_u(rng, 100, 300), 2)
            return None, None
        return None, None  # 56 on a zero base is incoherent; retry redraws
    if nature == 97:
        # Timing nature: resolve directionally; the recorded nature stays 97.
        nature = 56 if _resolve_97_dir(bucket, dist, rng, _force_97_dir) else 57
    if nature == 57:      # budgeted too little -> underissuance
        agency[field] = round(base * (1 - _u(rng, 0.15, 0.40)), 2)
    elif nature == 53:    # included but shouldn't be -> overissuance
        agency[field] = round(base + _u(rng, 100, 300), 2)
    elif nature == 52:    # should have been included, wasn't -> underissuance
        agency[field] = 0.0
    else:                 # 56 default: budgeted too much -> overissuance
        agency[field] = round(base * (1 + _u(rng, 0.15, 0.50)), 2)
    return None, None


def _corrupt_hhcomp(agency, truth, nature, rng, bucket, dist,
                  _force_97_dir=None):
    if nature == 97:
        # Timing nature: resolve directionally; the recorded nature stays 97.
        nature = 7 if _resolve_97_dir(bucket, dist, rng, _force_97_dir) else 6
    if nature == 7:       # ineligible person included -> overissuance
        agency["hh_size"] = min(truth["hh_size"] + 1, 8)
    else:                 # 6/13 default: eligible person excluded -> underissuance
        agency["hh_size"] = max(truth["hh_size"] - 1, 1)
    return None, None


def _apply_one(agency, truth, bucket, nature, rng, dist=None,
             _force_97_dir=None):
    """Corrupt agency-view facts in place. Returns (truth_correction,
    nature_override). dist is needed only to resolve timing-nature (97)
    direction; callers that lack it get the 0.5 fallback. _force_97_dir
    ("over"/"under") is a calibration hook, not for production draws."""
    dist = dist or {}
    if bucket == "earned":
        return _corrupt_income(agency, truth, nature, rng, "earned", bucket, dist,
                               _force_97_dir)
    if bucket == "unearned":
        return _corrupt_income(agency, truth, nature, rng, "unearned", bucket, dist,
                               _force_97_dir)
    if bucket in ("shelter", "sua"):
        return _corrupt_deduction(agency, truth, nature, rng, "shelter", bucket, dist,
                                  _force_97_dir)
    if bucket == "medical":
        return _corrupt_deduction(agency, truth, nature, rng, "medical_exp", bucket, dist,
                                  _force_97_dir)
    if bucket == "depcare":
        return _corrupt_deduction(agency, truth, nature, rng, "depcare", bucket, dist,
                                  _force_97_dir)
    if bucket == "hhcomp":
        return _corrupt_hhcomp(agency, truth, nature, rng, bucket, dist,
                               _force_97_dir)
    return None, None  # arithmetic handled as direct benefit noise


# Measured from the FY2024 QC file (all cases): P(case has a variance in
# bucket | base amount is zero) relative to P(variance | base > 0). Lets
# zero-base households draw income / deduction variances at the real (low)
# rate instead of never or always. Medical uses FSNELDER>0 as the base
# population (re-measured 2026-09-28; was 0.036 under an older cut).
ZERO_BASE_WEIGHT = {
    "earned": 0.018,
    "unearned": 0.091,
    "shelter": 0.227,
    # medical removed (exp11), depcare removed (exp12): the stratified
    # empirical mixes already capture the real base-rate relationships;
    # the extra suppression was double-counting.
}

_BASE_FIELD = {
    "earned": "earned", "unearned": "unearned", "shelter": "shelter",
    "medical": "medical_exp", "depcare": "depcare", "sua": "sua",
}


def _applicable_buckets(facts: dict, dist: dict, rng: random.Random):
    """Buckets weighted by empirical probability, scaled down when the base
    amount is zero (a household with no earnings can still get an earned-
    income variance — an unreported source — but rarely does).

    The bucket mix is conditional on earner status and senior/disabled status:
    real QC shows medical is 0.109 of variances on (no-earner, senior) but
    0.048 on (no-earner, non-senior) (exp11); a single marginal mix cannot
    reproduce both.
    """
    earner = "earner" if facts.get("earned", 0) > 0 else "no_earner"
    senior = "senior" if facts.get("senior_disabled") else "nonsenior"
    key = f"bucket_probs_given_{earner}_{senior}"
    if key not in dist:
        # fall back to the earner-only mix, then the marginal
        key = (f"bucket_probs_given_{earner}"
               if f"bucket_probs_given_{earner}" in dist else "bucket_probs")
    mix = dist.get(key, dist["bucket_probs"])
    cands = {}
    for bucket, p in mix.items():
        w = 1.0
        # depcare variances occur exclusively on kid households (exp12)
        if bucket == "depcare" and facts.get("n_kids", 0) == 0:
            continue
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


def _draw_nature(facts, bucket, dist, dir_w, rng):
    """Draw (nature, cause) for a bucket: empirical nature mix (earner-
    conditional) with direction-level retry-bias correction."""
    nkey = ("nature_given_bucket_earner" if facts.get("earned", 0) > 0
            else "nature_given_bucket_no_earner")
    nmix = dist.get(nkey, {}).get(bucket) or dist["nature_given_bucket"][bucket]
    bw = dir_w.get(bucket)
    if bw:
        nmix = {n: p * bw.get(_dirclass(int(n)), 1.0) for n, p in nmix.items()}
    # Exp13: importance weights for nature 57 ("budgeted too little").
    # Measured materialization m_{b,57} in the persistent flow is low
    # (medical 0.28, shelter 0.47); upweight the draw by 1/m so the
    # recorded rate matches the empirical mix.
    w57 = _NATURE_57_WEIGHT.get(bucket, 1.0)
    if w57 != 1.0:
        nmix = {n: (p * w57 if int(n) == 57 else p) for n, p in nmix.items()}
    nature = int(_sample(rng, nmix))
    cause = int(_sample(rng, dist["cause_given_bucket"][bucket]))
    return nature, cause


_NATURE_57_WEIGHT = {
    # 1 / materialization rate, measured in persistent flow (exp13),
    # scaled by 0.8 after the first pass overshot to 1.29x.
    "medical": 2.86,
    "shelter": 1.69,
    "earned": 1.60,
    "depcare": 1.00,
}


def _recorded_cause(nature, cause, rng):
    """Exp15: the real file leaves cause blank on 32% of nature-97 variances
    ('not required to be reported or acted upon' — no-fault timing). Mirror
    that labeling so pretraining labels stay faithful."""
    if nature == 97 and rng.random() < 0.32:
        return None
    return cause


def _inject_persistent(facts, rng, dist, applicable, dir_w, max_attempts,
                     stats=None):
    """Exp7: per-bucket persistence, single-draw-and-drop.

    Each variance's bucket is drawn ONCE from the empirical (conditional,
    zero-base-scaled) mix weighted by 1/eff_b^* (eff.json "bucket" section:
    the harmonic-mean per-bucket feasibility). The nature is drawn ONCE from
    the empirical mix with direction-level importance weights (1/m_d,
    eff.json "dir_weight") and applied ONCE: if it moves the benefit it is
    recorded, else the variance is dropped.

    Why this is exact where the retry loop was not: the old loop redrew the
    bucket on every failed attempt, so always-feasible buckets (hhcomp,
    arithmetic) won the retry lottery and were over-recorded ~3x. Fixing the
    bucket and dropping (instead of retrying) makes P(record b) = drawn_b x
    keep_b with keep_b = eff_b^*, so the 1/eff_b^* weight lands recorded_b
    exactly on empirical; likewise P(record n | b) lands on empirical by the
    1/m_d importance weights. No within-bucket race, so household-structural
    infeasibility (shelter at the cap, hhcomp-under on singles) cannot
    distort the nature mix — it just lowers keep_b, which the weight absorbs.
    max_attempts is unused (no retries); stats collects drawn/recorded counts
    for keep-rate measurement.
    """
    eff_b = (dist.get("effectiveness") or {}).get("bucket", {})
    if eff_b:
        applicable = {b: p / max(eff_b.get(b, 1.0), 0.02)
                      for b, p in applicable.items()}
    agency = copy.deepcopy(facts)
    truth = facts
    benefit_noise = 0.0
    variances = []
    n_var = 2 if rng.random() < 0.15 else 1

    def pair(a, t, noise):
        c = benefit_mod.compute(t)["benefit"]
        i = max(0, int(round(benefit_mod.compute(a)["benefit"] + noise)))
        return i, c

    for _ in range(n_var):
        bucket = _sample(rng, applicable)
        if stats is not None:
            stats["drawn"][bucket] += 1
        c_issued, c_correct = pair(agency, truth, benefit_noise)
        nature, cause = _draw_nature(facts, bucket, dist, dir_w, rng)
        trial_noise = 0.0
        if bucket == "arithmetic":
            # Direct benefit noise always materializes.
            trial_noise = rng.choice([-1, 1]) * _u(rng, 10, 60)
        else:
            trial_agency = copy.deepcopy(agency)
            trial_truth = truth
            truth_corr, nature_override = _apply_one(
                trial_agency, trial_truth, bucket, nature, rng, dist)
            if truth_corr:
                trial_truth = {**trial_truth, **truth_corr}
            if nature_override is not None:
                nature = nature_override
        t_issued, t_correct = pair(
            trial_agency if bucket != "arithmetic" else agency,
            trial_truth if bucket != "arithmetic" else truth,
            benefit_noise + trial_noise)
        if ((t_issued, t_correct) != (c_issued, c_correct)
                and t_issued != t_correct):
            if bucket != "arithmetic":
                agency, truth = trial_agency, trial_truth
            benefit_noise += trial_noise
            if stats is not None:
                stats["recorded"][bucket] += 1
            variances.append({
                "element": REPRESENTATIVE_ELEMENT[bucket],
                "element_bucket": bucket,
                "nature": nature,
                "cause": _recorded_cause(nature, cause, rng),
                "timing": "after" if nature == 97 else "at_action",
            })
        # Infeasible for this household: variance dropped (no retry — retrying
        # within the bucket is what distorts the nature mix).

    if not variances:
        return _clean_case(facts, benefit_mod.compute(facts)["benefit"])
    issued = max(0, int(round(benefit_mod.compute(agency)["benefit"] + benefit_noise)))
    correct = benefit_mod.compute(truth)["benefit"]
    dollar = abs(correct - issued)
    return {
        "facts": truth,
        "issued_facts": agency,
        "correct_benefit": correct,
        "issued_benefit": issued,
        "finding": 2 if issued > correct else 3,
        "dollar_error": dollar,
        "reportable": dollar > params.QC_ERROR_THRESHOLD,
        "variances": variances,
    }


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


def inject(facts: dict, rng: random.Random, dist: dict, max_attempts: int = 12,
           persistent_buckets: bool = False, _stats: dict = None):
    """Returns a case dict with true facts, agency-view facts, correct and
    issued benefits, finding, dollar error, and the variance list.

    A variance that doesn't move the benefit is a no-op: retry with a
    different draw (real QC files carry ~zero variances on correct cases).
    max_attempts bounds the retries; exhausted retries yield a clean case.

    Injection is earner-conditional: real QC shows P(error|earned>0) well
    above P(error|earned=0), and a flat coin flattens the earnings->error
    gradient the transfer classifier needs (exp4 diagnosis).

    persistent_buckets (exp7): draw each variance's bucket once from the
    empirical mix (weighted by 1/eff_b^*) and apply each drawn nature once,
    dropping infeasible ones instead of redrawing the bucket. Removes the
    cross-bucket retry lottery that over-records always-materializing
    buckets (hhcomp, arithmetic) while keeping the importance-weighting
    math exact.
    """
    p_inject: float
    inj = dist.get("injection_rate")
    if inj:
        # Attrition-corrected coin: realized P(error | status) then matches
        # the empirical FY2024 conditionals (see calibrate_injection.py).
        # Persistent mode has its own attrition profile -> own coins.
        if persistent_buckets and isinstance(inj.get("persistent"), dict):
            inj = inj["persistent"]
        p_inject = inj["earner"] if facts.get("earned", 0) > 0 else inj["no_earner"]
    else:
        # Fallback: raw empirical conditionals (uncorrected for retry loss).
        p_inject = (dist.get("error_rate_given_earner", dist["error_rate"])
                    if facts.get("earned", 0) > 0
                    else dist.get("error_rate_given_no_earner", dist["error_rate"]))
    if rng.random() >= p_inject:
        return _clean_case(facts, benefit_mod.compute(facts)["benefit"])

    applicable = _applicable_buckets(facts, dist, rng)
    if not applicable:
        applicable = {"arithmetic": 1.0}
    # Correct for retry-filtering bias: buckets whose corruptions often no-op
    # (shelter cap absorption, medical threshold) are upweighted so the
    # post-retry mix matches the empirical mix. See experiments/eff.json.
    # Skipped in persistent mode: the bucket is drawn once, so there is no
    # cross-bucket retry lottery to correct.
    eff = dist.get("effectiveness") or {}
    eff_b = eff.get("bucket", eff)  # eff.json is nested; tolerate the old flat shape
    dir_w = eff.get("dir_weight", {})
    if persistent_buckets:
        return _inject_persistent(facts, rng, dist, applicable, dir_w,
                                  max_attempts, stats=_stats)
    if eff_b:
        applicable = {b: p / max(eff_b.get(b, 1.0), 0.02) for b, p in applicable.items()}

    for _ in range(max_attempts):
        agency = copy.deepcopy(facts)
        truth = facts
        benefit_noise = 0.0
        variances = []
        n_var = 2 if rng.random() < 0.15 else 1
        for _ in range(n_var):
            bucket = _sample(rng, applicable)
            nature, cause = _draw_nature(facts, bucket, dist, dir_w, rng)
            if bucket == "arithmetic":
                benefit_noise += rng.choice([-1, 1]) * _u(rng, 10, 60)
                nature_override = None
            else:
                truth_corr, nature_override = _apply_one(agency, truth, bucket, nature, rng, dist)
                if truth_corr:
                    truth = {**truth, **truth_corr}
                if nature_override is not None:
                    nature = nature_override
            variances.append({
                "element": REPRESENTATIVE_ELEMENT[bucket],
                "element_bucket": bucket,
                "nature": nature,
                "cause": _recorded_cause(nature, cause, rng),
                "timing": "after" if nature == 97 else "at_action",
            })
        correct = benefit_mod.compute(truth)["benefit"]
        issued = benefit_mod.compute(agency)["benefit"] + benefit_noise
        issued = max(0, int(round(issued)))
        if issued != correct:
            dollar = abs(correct - issued)
            return {
                "facts": truth,               # true facts (what QC found)
                "issued_facts": agency,       # facts the agency used
                "correct_benefit": correct,
                "issued_benefit": issued,
                "finding": 2 if issued > correct else 3,
                "dollar_error": dollar,
                "reportable": dollar > params.QC_ERROR_THRESHOLD,
                "variances": variances,
            }
    return _clean_case(facts, benefit_mod.compute(facts)["benefit"])
