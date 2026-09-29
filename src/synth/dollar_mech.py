"""Dollar-error mechanisms (exp18 verified, exp23 merged) — flag-gated.

Formalizes the mechanisms exp18 prototyped as in-script monkey-patches so
they can be enabled, calibrated, and evaluated as a unit WITHOUT editing
src/synth/errors.py (a parallel worker may be touching nearby code; this
module is purely additive).

Mechanisms (ALL default OFF — importing this module changes nothing):
  1. small-error mode: timing variances (nature 97, 44% of real error
     cases) take small perturbations (+/- $2-30 on the underlying amount)
     instead of the coarse magnitudes the 97-resolution coin renders; a
     residual per-direction fraction of non-97 natures does too.
     (exp18: HELD — fixed the low tail of the dollar marginal:
     p10/p25/p50 22/41/72 -> 3/5/29 vs real 4/11/31.)
  2. whole-unit ineligibility: per-case probability p_unit that the unit is
     ineligible (correct benefit $0; dollar error = full issued benefit),
     restoring the extreme over tail. Layered in inject_case(), which
     wraps errors.inject().
     (exp18: HELD — p_unit=0.0125 reproduces the real 4.9%
     near-full-benefit over share; over p99 301 -> ~535 vs real 603.)
  4. coarse under rescale: multiply the benefit-relevant delta of coarse
     (non-small-mode) under-direction corruptions by a per-nature scale so
     the realized per-nature medians land on the real QC medians
     (exp23; repairs the p90 over/under asymmetry inversion exp18 left:
     synth under p90 was $216 vs real $128 because coarse under
     magnitudes are oversized).

Usage:
    from synth import dollar_mech
    dollar_mech.enable()  # install patches (exp18 best config by default)
    case = dollar_mech.inject_case(facts, rng, dist, persistent_buckets=True)
    ...
    dollar_mech.disable()  # restore stock behavior

enable() is idempotent (re-calling only updates the config); disable()
restores the original corruptors. The recorded (element, nature) codes are
unchanged by every mechanism — QC natures don't distinguish magnitude —
so the taxonomy mix is preserved by construction.
"""
import copy

from . import benefit as benefit_mod
from . import errors

_SMALL_LO, _SMALL_HI = 2.0, 30.0  # dollars on the underlying amount

# exp18's best config (grid-verified on 3 seeds)
SMALL_97_DEFAULT = True
NON97_RESIDUAL_DEFAULT = {"over": 0.25, "under": 0.35}
P_UNIT_DEFAULT = 0.0125

UNIT_ELEMENT = 150  # "Unit composition" (hhcomp bucket code)

_orig_income = None
_orig_deduction = None
_small_97 = SMALL_97_DEFAULT
_non97_residual = dict(NON97_RESIDUAL_DEFAULT)
_under_scale = {}  # nature -> scale; empty means mechanism 4 is off


# --------------------------------------------------------------------------
# mechanism 1: small-error mode (ported from exp18, unchanged semantics)
# --------------------------------------------------------------------------

def _small_perturb(base, direction, rng, invert=False):
    """Small mis-keying: +/- $2-30 on the amount. `direction` is the desired
    finding: 'over' means the agency should pay too much. For income that
    means under-counting (base - delta); for deductions it means
    over-counting (base + delta), hence `invert=True` on the deduction path."""
    delta = rng.uniform(_SMALL_LO, _SMALL_HI)
    if (direction == "over") != invert:
        return round(base - delta, 2)
    return round(base + delta, 2)


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
    """Timing (97) variances take the small mode; non-97 natures take it with
    the residual per-direction fraction."""
    if from_97 and _small_97:
        return True
    f = _non97_residual.get(direction, 0.0)
    return f > 0 and rng.random() < f


def _small_income_branch(agency, truth, nature, from_97, resolved, direction,
                         rng, field, bucket, dist, _force_97_dir):
    base = truth[field]
    if base == 0:
        if resolved == 44:
            # small phantom income -> underissuance
            agency[field] = _small_fabricated_income(rng)
            return None, None
        # small unreported source -> overissuance; truth corrected up.
        # A reviewer would code a drawn 38 on a zero base as 35 (but a
        # drawn 97 stays 97).
        override = None if from_97 else (35 if resolved == 38 else resolved)
        return {field: _small_truth_income(rng)}, override
    # small mis-keying on a positive base (keeps the drawn nature label)
    agency[field] = max(0.0, _small_perturb(base, direction, rng))
    return None, None


def _small_deduction_branch(agency, truth, nature, from_97, resolved, direction,
                            rng, field, bucket, dist, _force_97_dir):
    base = truth[field]
    if field == "medical_exp" and not truth["senior_disabled"]:
        return _orig_deduction(agency, truth, nature, rng, field, bucket, dist,
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


# --------------------------------------------------------------------------
# mechanism 4: coarse under rescale (exp23)
# --------------------------------------------------------------------------

def _rescale_under(nature, base, snap, agency, truth_corr, field):
    """Shrink the benefit-relevant delta of a coarse under-direction
    corruption toward the real per-nature median (mechanism 4).

    Works post-hoc on the stock corruption: the agency-side delta is scaled
    in place, and omission-type truth corrections (the truth had an amount
    the agency never saw) are scaled before they are merged. Only reached
    on the coarse path — the small mode returns earlier — and only for
    natures present in the scale map (44/57/52, the under natures exp18
    found oversized).
    """
    s = _under_scale.get(nature)
    if not s or s == 1.0:
        return
    if truth_corr is not None and field in truth_corr:
        truth_corr[field] = round(truth_corr[field] * s, 2)
        return
    agency[field] = round(base + s * (agency[field] - base), 2)


# --------------------------------------------------------------------------
# patched corruptors (installed by enable())
# --------------------------------------------------------------------------

def _patched_corrupt_income(agency, truth, nature, rng, field, bucket, dist,
                            _force_97_dir=None):
    base = truth[field]
    from_97 = nature == 97
    resolved = nature
    if from_97:
        resolved = 38 if errors._resolve_97_dir(bucket, dist, rng, _force_97_dir) else 44
    direction = "under" if resolved == 44 else "over"
    if _take_small(from_97, direction, rng):
        return _small_income_branch(agency, truth, nature, from_97, resolved,
                                    direction, rng, field, bucket, dist,
                                    _force_97_dir)
    # coarse path: stock corruption, then mechanism-4 rescale of the delta
    snap = agency[field]
    truth_corr, override = _orig_income(agency, truth, nature, rng, field,
                                        bucket, dist, _force_97_dir=_force_97_dir)
    _rescale_under(nature, base, snap, agency, truth_corr, field)
    return truth_corr, override


def _patched_corrupt_deduction(agency, truth, nature, rng, field, bucket, dist,
                               _force_97_dir=None):
    base = truth[field]
    from_97 = nature == 97
    resolved = nature
    if from_97:
        # Timing nature: resolve directionally for the small-mode decision
        # (the recorded nature stays 97).
        resolved = 56 if errors._resolve_97_dir(bucket, dist, rng, _force_97_dir) else 57
    direction = "under" if resolved in (57, 52) else "over"
    if _take_small(from_97, direction, rng):
        return _small_deduction_branch(agency, truth, nature, from_97, resolved,
                                       direction, rng, field, bucket, dist,
                                       _force_97_dir)
    # coarse path: stock corruption, then mechanism-4 rescale of the delta
    snap = agency[field]
    truth_corr, override = _orig_deduction(agency, truth, nature, rng, field,
                                           bucket, dist, _force_97_dir=_force_97_dir)
    _rescale_under(nature, base, snap, agency, truth_corr, field)
    return truth_corr, override


# --------------------------------------------------------------------------
# mechanism 2: whole-unit ineligibility (ported from exp18)
# --------------------------------------------------------------------------

def _unit_ineligible_case(facts):
    issued = benefit_mod.compute(facts)["benefit"]
    return {
        "facts": facts,
        "issued_facts": copy.deepcopy(facts),
        "correct_benefit": 0,
        "issued_benefit": issued,
        "finding": 2,
        "dollar_error": issued,
        "reportable": issued > 56,
        # Marker distinguishing mechanism-2 cases from genuine nature-99
        # variances: 99 is a real QC nature code already present in the
        # empirical mix (all buckets carry it), so the nature code alone
        # cannot identify a whole-unit case.
        "unit_ineligible": True,
        "variances": [{
            "element": UNIT_ELEMENT,
            "element_bucket": "hhcomp",
            "nature": 99,
            "cause": 10,   # policy incorrectly applied
            "timing": "at_action",
        }],
    }


def inject_case(facts, rng, dist, p_unit=P_UNIT_DEFAULT, **inject_kwargs):
    """errors.inject() with the whole-unit-ineligibility draw layered on top
    (mechanism 2). The unit draw happens first, exactly as in exp18: with
    probability p_unit the unit is ineligible, the correct benefit is $0,
    and the dollar error is the full issued benefit (an overissuance)."""
    if p_unit and rng.random() < p_unit:
        return _unit_ineligible_case(facts)
    return errors.inject(facts, rng, dist, **inject_kwargs)


# --------------------------------------------------------------------------
# flag: install / remove the patches (default: off)
# --------------------------------------------------------------------------

def enable(small_97=True, non97_residual=None, under_scale=None):
    """Install the mechanism patches on src/synth/errors.py.

    small_97: timing (97) variances take the small-error mode (mechanism 1).
    non97_residual: {"over": f, "under": f} fraction of non-97 variances
        taking the small mode; None selects exp18's best (0.25 / 0.35).
    under_scale: {nature: scale} for mechanism 4 (coarse under rescale);
        None or {} disables mechanism 4.

    Idempotent: re-calling updates the config without re-wrapping.
    """
    global _orig_income, _orig_deduction, _small_97, _non97_residual, _under_scale
    if _orig_income is None:
        _orig_income = errors._corrupt_income
        _orig_deduction = errors._corrupt_deduction
    _small_97 = small_97
    _non97_residual = (dict(non97_residual) if non97_residual is not None
                       else dict(NON97_RESIDUAL_DEFAULT))
    _under_scale = {int(k): float(v) for k, v in (under_scale or {}).items()}
    errors._corrupt_income = _patched_corrupt_income
    errors._corrupt_deduction = _patched_corrupt_deduction


def disable():
    """Restore the stock corruptors (mechanisms off)."""
    global _orig_income, _orig_deduction
    if _orig_income is not None:
        errors._corrupt_income = _orig_income
        errors._corrupt_deduction = _orig_deduction
        _orig_income = None
        _orig_deduction = None


def is_enabled():
    """True if the mechanism patches are currently installed."""
    return _orig_income is not None
