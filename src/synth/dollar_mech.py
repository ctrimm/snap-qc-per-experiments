"""Dollar-error mechanisms (exp18 verified, exp23 merged, exp26 fixed) — flag-gated.

Formalizes the mechanisms exp18 prototyped as in-script monkey-patches so
they can be enabled, calibrated, and evaluated as a unit WITHOUT editing
src/synth/errors.py (a parallel worker may be touching nearby code; this
module is purely additive).

Mechanisms (ALL default OFF — importing this module changes nothing):
  1. small-error mode: timing variances (nature 97, 44% of real error
     cases) take small perturbations instead of the coarse magnitudes the
     97-resolution coin renders; a residual per-direction fraction of
     non-97 natures does too. (exp18: HELD — fixed the low tail of the
     dollar marginal.) exp26: the perturbation magnitude is now
     direction-aware — under-direction small variances draw larger
     amount deltas (U($20,$80) on both paths -> ~$5-24 benefit at the
     ~30% pass-through)
     so the benefit deltas center near the real 97-under median ($15)
     instead of dying at the $23 minimum-benefit floor ($1-9 benefit
     deltas in exp23, under median collapsed to $8 vs $23 real).
  2. whole-unit ineligibility: per-case probability p_unit that the unit is
     ineligible (correct benefit $0; dollar error = full issued benefit),
     restoring the extreme over tail. Recorded as an earned-income
     variance (element 311, nature 35) — exp26 recode: the real file codes
     near-full-benefit overs as earned income (311 / natures 35/38/39/37),
     NOT as hhcomp/99, which is how exp18/exp23 recorded them (and the
     miscoding drove exp23's element-L1 regression 0.068 -> 0.149).
     Because the real whole-unit mass already lives in the empirical
     earned mix, enabling this mechanism MUST be paired with
     apply_unit_bucket_correction(), which subtracts the unit mass from
     the empirical earned draw weight first (the recurring double-counting
     bug class: any mass the mechanisms add that the empirical mix
     already contains must be subtracted from the empirical targets).
     Layered in inject_case(), which wraps errors.inject().
     (exp18: HELD — p_unit=0.0125 reproduces the real 4.9%
     near-full-benefit over share; over p99 301 -> ~535 vs real 603.)
  4. coarse under rescale: multiply the benefit-relevant delta of coarse
     (non-small-mode) under-direction corruptions by a per-nature scale so
     the realized per-nature medians land on the real QC medians
     (exp23; repairs the p90 over/under asymmetry inversion exp18 left).

Helpers for the direction-aware recalibration (exp26):
  apply_unit_bucket_correction(dist, p_unit, variances_per_case) -> dist
      copy with the earned draw weight reduced by the whole-unit mass.
  apply_direction_balance(dist, boost_over, boost_under) -> dist copy
      with the over/under draw multipliers folded into dir_weight, so the
      phase-1 calibration can target separate over/under residual rates
      and offset mechanism 2's mechanical over-contribution.

Usage:
    from synth import dollar_mech
    dollar_mech.enable()  # install patches (exp18 best config by default)
    case = dollar_mech.inject_case(facts, rng, dist, persistent_buckets=True)
    ...
    dollar_mech.disable()  # restore stock behavior

enable() is idempotent (re-calling only updates the config); disable()
restores the original corruptors. The recorded (element, nature) codes are
unchanged by mechanisms 1 and 4 — QC natures don't distinguish magnitude —
so the taxonomy mix is preserved by construction; mechanism 2's (311, 35)
code is the exp26 fix for exp23's miscoding.
"""
import copy

from . import benefit as benefit_mod
from . import errors

# Small-mode perturbation ranges on the underlying amount (dollars).
# Overs keep exp18's range. Unders are direction-aware (exp26): the benefit
# moves at ~30% of the amount delta on BOTH the income path (20% earnings
# disregard: 0.8 * 0.3 = 0.24) and the deduction path (0.3 when the
# deduction bites; 0 at the shelter cap), so under perturbations draw
# U($20,$80) -> ~$5-24 benefit deltas, centering near the real 97-under
# median ($15). exp18/exp23 used $2-30 for both, whose $1-9 benefit deltas
# died at the $23 minimum-benefit floor and collapsed the under median to
# $8 vs $23 real. (An earlier draft used a smaller deduction range on a
# mistaken ~1:1 pass-through assumption; the benefit formula is
# max_allotment - 0.3 * net_income either way.)
_SMALL_OVER_LO, _SMALL_OVER_HI = 2.0, 30.0
_SMALL_UNDER_INCOME_DEFAULT = (20.0, 80.0)
_SMALL_UNDER_DEDUCT_DEFAULT = (20.0, 80.0)

# exp18's best config (grid-verified on 3 seeds)
SMALL_97_DEFAULT = True
NON97_RESIDUAL_DEFAULT = {"over": 0.25, "under": 0.35}
P_UNIT_DEFAULT = 0.0125

# exp26 recode (exp23 diagnosis #3): real near-full-benefit overs are coded
# as earned-income variances (element 311, natures 35/38/39/37) — not as
# household-composition / nature 99. Recording the whole-unit mechanism as
# (311, 35) matches the real file and repairs exp23's element-L1
# regression (0.068 -> 0.149 from the hhcomp/99 miscoding).
UNIT_ELEMENT = 311
UNIT_NATURE = 35
UNIT_BUCKET = "earned"

_orig_income = None
_orig_deduction = None
_small_97 = SMALL_97_DEFAULT
_non97_residual = dict(NON97_RESIDUAL_DEFAULT)
_small_under_income = _SMALL_UNDER_INCOME_DEFAULT
_small_under_deduct = _SMALL_UNDER_DEDUCT_DEFAULT
_under_scale = {}  # nature -> scale; empty means mechanism 4 is off


# --------------------------------------------------------------------------
# mechanism 1: small-error mode (ported from exp18, unchanged semantics)
# --------------------------------------------------------------------------

def _small_perturb(base, direction, rng, invert=False):
    """Small mis-keying on the amount. `direction` is the desired finding:
    'over' means the agency should pay too much. For income that means
    under-counting (base - delta); for deductions it means over-counting
    (base + delta), hence `invert=True` on the deduction path.

    exp26: the range is direction-aware. Over keeps exp18's +/- $2-30.
    Under draws larger amount deltas (U($20,$80) on both paths — the
    benefit moves at ~30% of the amount delta on both paths), so the
    benefit delta centers near the real 97-under median ($15) instead of
    the $1-9 that died at the $23 minimum-benefit floor."""
    if direction == "under":
        lo, hi = (_small_under_deduct if invert else _small_under_income)
    else:
        lo, hi = _SMALL_OVER_LO, _SMALL_OVER_HI
    delta = rng.uniform(lo, hi)
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
        # exp26 recode: the real file codes near-full-benefit overs as
        # earned-income variances (element 311, natures 35/38/39/37) — not
        # as hhcomp/99, which is how exp18/exp23 recorded them (the
        # miscoding drove exp23's element-L1 regression 0.068 -> 0.149).
        # Marker distinguishing mechanism-2 cases from genuine earned/35
        # variances: 35 is a real QC nature code already present in the
        # empirical mix, so the nature code alone cannot identify a
        # whole-unit case.
        "unit_ineligible": True,
        "variances": [{
            "element": UNIT_ELEMENT,
            "element_bucket": UNIT_BUCKET,
            "nature": UNIT_NATURE,
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
# exp26 calibration helpers: keep the empirical targets honest when
# mechanism 2 is on (the double-counting bug class)
# --------------------------------------------------------------------------

def apply_unit_bucket_correction(dist, p_unit, variances_per_case):
    """Subtract the whole-unit mass from the empirical bucket targets.

    Mechanism 2 records each whole-unit case as one earned / nature-35
    variance, and the real whole-unit mass already lives in the empirical
    earned mix (exp23 diagnosis #3) — so drawing the full empirical earned
    weight on top double-counts it. Returns a dist copy with the earned
    weight scaled by (1 - unit_share / earned_share) in every bucket mix,
    where unit_share = p_unit / variances_per_case (unit variances as a
    share of all recorded variances) and earned_share is the empirical
    earned share. The factor is clipped to [0.5, 1.0]; the persistent
    injector's materialization correction then lands recorded earned on
    (empirical - unit mass), and mechanism 2 adds the unit mass back.
    """
    d = copy.deepcopy(dist)
    e_earned = d["bucket_probs"][UNIT_BUCKET]
    unit_share = p_unit / max(variances_per_case, 1e-9)
    f = 1.0 - unit_share / e_earned
    f = min(1.0, max(0.5, f))
    for key in d:
        if (key.startswith("bucket_probs") and isinstance(d[key], dict)
                and UNIT_BUCKET in d[key]):
            d[key][UNIT_BUCKET] = d[key][UNIT_BUCKET] * f
    d.setdefault("_exp26", {})["unit_bucket_factor"] = round(f, 4)
    return d


def apply_direction_balance(dist, boost_over=1.0, boost_under=1.0):
    """Fold direction-balance multipliers into dir_weight.

    The phase-1 calibration is direction-aware (exp26): it targets separate
    over/under residual rates — the empirical direction targets with the
    whole-unit mass subtracted — so mechanism 2's mechanical over
    contribution can be offset instead of baked in. These multipliers are
    the draw-side instrument: they scale the over/under nature-draw weights
    inside each bucket. The "other" class (timing-97) is untouched — 97
    direction is owned by the phase-2 resolution coin. Returns a dist copy;
    the committed eff.json/inject.json are never rewritten.
    """
    d = copy.deepcopy(dist)
    eff = d.get("effectiveness") or {}
    dw = eff.get("dir_weight") or {}
    for b, w in dw.items():
        w = dict(w)
        if "over" in w:
            w["over"] = round(w["over"] * boost_over, 4)
        if "under" in w:
            w["under"] = round(w["under"] * boost_under, 4)
        dw[b] = w
    eff["dir_weight"] = dw
    d["effectiveness"] = eff
    return d


# --------------------------------------------------------------------------
# flag: install / remove the patches (default: off)
# --------------------------------------------------------------------------

def enable(small_97=True, non97_residual=None, under_scale=None,
           small_under=None):
    """Install the mechanism patches on src/synth/errors.py.

    small_97: timing (97) variances take the small-error mode (mechanism 1).
    non97_residual: {"over": f, "under": f} fraction of non-97 variances
        taking the small mode; None selects exp18's best (0.25 / 0.35).
    under_scale: {nature: scale} for mechanism 4 (coarse under rescale);
        None or {} disables mechanism 4.
    small_under: ((income_lo, income_hi), (deduct_lo, deduct_hi)) amount
        ranges for under-direction small perturbations; None selects the
        exp26 defaults ((20, 80) both paths), which center the benefit
        delta near the real 97-under median ($15) given the ~30%
        benefit pass-through on both paths.

    Idempotent: re-calling updates the config without re-wrapping.
    """
    global _orig_income, _orig_deduction, _small_97, _non97_residual
    global _under_scale, _small_under_income, _small_under_deduct
    if _orig_income is None:
        _orig_income = errors._corrupt_income
        _orig_deduction = errors._corrupt_deduction
    _small_97 = small_97
    _non97_residual = (dict(non97_residual) if non97_residual is not None
                       else dict(NON97_RESIDUAL_DEFAULT))
    _under_scale = {int(k): float(v) for k, v in (under_scale or {}).items()}
    if small_under is not None:
        _small_under_income = tuple(small_under[0])
        _small_under_deduct = tuple(small_under[1])
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


# --------------------------------------------------------------------------
# exp31: adopted calibration -- the exp26 recalibration as module defaults
# --------------------------------------------------------------------------
# The mechanisms collapse without the recalibration: enable() alone (no
# fitted coins / scales / effectiveness) gives finding L1 0.103 (exp31
# measured). These constants are the exp26 recalibration re-fitted on the
# CURRENT generator state -- exp24 draw defaults (ZERO_BASE_WEIGHT={} +
# exp29 re-measured MATERIALIZATION_MATRIX), exp29 sampler (BASE_POSITIVITY),
# exp29 97-coins, exp28 kid-weight/57-weights -- seed set A (exp26's exact
# seeds: pre-pass 5000, eff 11, 97-cal 21, boost 31). A re-fit on seed set
# B (5001/13/23/33) agrees within tolerance: boosts +/-0.01, phase-1 coins
# +/-0.025, 97 coins +/-0.011, unit-bucket factor +/-0.002, V +/-1.2%; the
# noisiest fitted values are the nature-44 under scale (0.641 vs 0.759) and
# rare-bucket dir_weight cells (medical/depcare/sua, up to 0.141). Full
# comparison: experiments/exp31_adopt_dollar.md.
#
# BRITTLENESS (measured): these are fitted to one generator state. Exp26's
# published values (fitted before exp29's matrix re-measurement) differ from
# the re-fit above (boosts 0.686->0.664, phase-1 coins ~0.02), so if the draw
# defaults, the materialization matrix, or the sampler change, re-run
# `python3 experiments/exp31_adopt_dollar.py capture` and re-render this
# section with experiments/exp31_render_constants.py. Design (b) -- persisted
# fitted values -- was chosen over adaptive re-fitting inside enable() on
# measured evidence: the recalibration needs ~150k case-generations per
# invocation, and its measurement noise would make seeded runs
# non-reproducible.
# mechanism-4 coarse-under scales (real_median / synth_median, clipped [0.25, 1.0])
EXP31_UNDER_SCALE = {44: 0.641, 57: 0.301, 52: 0.587}

# recorded variances per case in the mechanism-on pre-pass; feeds the
# unit-bucket double-counting correction via apply_unit_bucket_correction
# (re-derives the factor 0.8732 on the current dist)
EXP31_VARIANCES_PER_CASE = 0.39

# per-bucket effectiveness re-measured AFTER mechanisms 1+4 were installed
# (the rescale changes materialization rates -- exp23's subtlety), with the
# direction-balance boosts (over 0.663816, under 0.989421) folded into dir_weight
EXP31_EFFECTIVENESS = {
 "bucket": {
  "arithmetic": 1.0,
  "earned": 0.723,
  "unearned": 0.558,
  "shelter": 0.33,
  "medical": 0.423,
  "hhcomp": 0.713,
  "depcare": 0.633,
  "sua": 0.307
 },
 "dir_materialization": {
  "arithmetic": {
   "over": 1.0,
   "under": 1.0,
   "other": 1.0
  },
  "earned": {
   "over": 0.768,
   "under": 0.752,
   "other": 0.7
  },
  "unearned": {
   "over": 0.624,
   "under": 0.596,
   "other": 0.506
  },
  "shelter": {
   "over": 0.323,
   "under": 0.468,
   "other": 0.305
  },
  "medical": {
   "over": 0.41,
   "under": 0.456,
   "other": 0.417
  },
  "hhcomp": {
   "over": 1.0,
   "under": 0.629,
   "other": 0.661
  },
  "depcare": {
   "over": 0.481,
   "under": 0.791,
   "other": 0.831
  },
  "sua": {
   "over": 0.317,
   "under": 0.501,
   "other": 0.252
  }
 },
 "dir_weight": {
  "arithmetic": {
   "over": 0.6638,
   "under": 0.9894,
   "other": 1.0
  },
  "earned": {
   "over": 0.6247,
   "under": 0.9508,
   "other": 1.033
  },
  "unearned": {
   "over": 0.5941,
   "under": 0.9251,
   "other": 1.102
  },
  "shelter": {
   "over": 0.6791,
   "under": 0.6975,
   "other": 1.083
  },
  "medical": {
   "over": 0.6857,
   "under": 0.9182,
   "other": 1.016
  },
  "hhcomp": {
   "over": 0.4733,
   "under": 1.123,
   "other": 1.08
  },
  "depcare": {
   "over": 0.8736,
   "under": 0.7925,
   "other": 0.762
  },
  "sua": {
   "over": 0.6426,
   "under": 0.6055,
   "other": 1.216
  }
 }
}

# 97-resolution coins per bucket (phase-2 refit under the mechanisms)
EXP31_P97_COINS = {'arithmetic': 0.4857, 'depcare': 0.5314, 'earned': 0.6142, 'hhcomp': 0.3852, 'medical': 0.5978, 'shelter': 0.3944, 'sua': 0.5302, 'unearned': 0.6862}

# direction-aware phase-1 coins per stratum (empirical minus the unit mass,
# renormalized to the residual pool, over per-stratum P(materialize|inject))
EXP31_PHASE1_COINS = {'earner': 0.9131, 'no_earner': 0.8573}

def adopted_dist(dist):
    """Return a dist copy with the exp31 adopted calibration baked in.

    In-memory only -- the committed dist.json/eff.json/inject.json are never
    rewritten. Applies: the re-measured effectiveness (direction-balance
    boosts already folded into dir_weight), the unit-bucket double-counting
    correction (the whole-unit mass already lives in the empirical earned
    mix, so it is subtracted from the earned draw weight first), the refit
    97-resolution coins, and the direction-aware phase-1 coins.
    """
    d = copy.deepcopy(dist)
    d["effectiveness"] = copy.deepcopy(EXP31_EFFECTIVENESS)
    d = apply_unit_bucket_correction(
        d, P_UNIT_DEFAULT, EXP31_VARIANCES_PER_CASE)
    inj = dict(d["injection_rate"])
    inj["p_over_97_resolve"] = dict(EXP31_P97_COINS)
    inj["persistent"] = dict(EXP31_PHASE1_COINS)
    d["injection_rate"] = inj
    return d


def enable_adopted(dist):
    """Install the mechanism patches with the exp31 adopted config and return
    the calibrated dist copy -- the single entry point for the
    --dollar-mechanisms generator default. No separate fitting step: the
    exp26 recalibration is baked in as module defaults (see above).
    Idempotent like enable(); pair with disable() to restore stock behavior.
    """
    enable(under_scale=EXP31_UNDER_SCALE)
    return adopted_dist(dist)
