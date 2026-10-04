"""UT-conditioned synthetic QC generation (UT1).

Utah offsets for the SNAP QC synthetic generator. Fit from FY2022-2024 QC
public-use microdata (STATE='49', n=3,127; FYWGT-weighted; microdata-implied
rates, NOT FNS-published rates) — partial-year FY2020-21 excluded per the
NY6 lesson. See experiments/ut1_ut_generator.md and `python3
experiments/ut1_ut_generator.py fit` for the provenance of every constant
below.

Design: UT conditioning is a set of *relative offsets* applied to the
national (adopted-default) generator's dist, in-memory only. The national
path is untouched: importing this module installs nothing, and
`generate_ut()` restores every patch it installs. National (default)
generation behavior is byte-identical with or without this module.

What UT looks like vs national (FY2022-2024, FYWGT-weighted):
- errs less often (case-weighted 33.2% vs 40.1%) with a near-national over
  share (57.8% vs 61.3% of errors are overissuances); the dollar rate is
  much lower (0.0390 vs 0.0873) and errors are much smaller (p50 $22 vs
  $31, p90 $99 vs $202, mean $42 vs $70; medO $25/$37, medU $18/$23;
  85.5% of errors <=$56).
- error mix is earned-heavy (1.27x national share); sua-light (0.79x);
  medical near national (1.03x).
- timing-97 mix is split: MORE 97s than national on earned (1.52x),
  unearned (1.45x), medical (1.30x); FEWER on shelter (0.76x), sua (0.79x).
- direction: UT skews UNDER on earned/medical non-97 variances (earned
  over 0.87x/under 1.96x, medical over 0.61x/under 2.02x) and OVER on
  shelter (over 1.56x/under 0.90x) — the mirror of SD's under-skew.
- UT blanks cause on 84.0% of timing-97 variances (national 58.4%
  FY2022-24) — the recorded remainder is mostly cause 26 (no-fault), with
  client-coded 1s on earned/shelter.
- on substantive (non-97) variances UT codes NO no-fault (no_fault 0.0 on
  every bucket, NY-like): client-coded on unearned/shelter/sua
  (2.1x/1.6x/2.1x), agency-coded on earned/medical near national.
- near-full|over 0.0033 vs 0.0574 national — whole-unit ineligibility is
  near-absent in UT, so p_unit is scaled down to 0.0007
  (P_UNIT_DEFAULT x 0.0033/0.0574).

API for UT2 (copy-paste):
    from src.synth.ut_state import generate_ut
    generate_ut(n=20000, seed=7, dist="experiments/dist.json",
               out="data/ut_synth.jsonl")

Shell:
    python3 -m src.synth.ut_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out data/ut_synth.jsonl

Requires the adopted generator path (dollar mechanisms ON, persistent
buckets) — that is the generator default since exp31.
"""
import argparse
import copy
import json
import random

from . import errors
from .codebook import cause_bucket

# ---------------------------------------------------------------------------
# UT empirical targets (FY2022-2024 QC, STATE='49', n=3,127, FYWGT-weighted;
# partial-year FY2020-21 excluded per the NY6 lesson). National reference is
# FY2022-2024 microdata-implied (same basis, excluding UT rows).
# ---------------------------------------------------------------------------
UT_OFFSETS = {
    "finding_mix": {"1": 0.6677, "2": 0.1920, "3": 0.1403},
    "case_err_rate": 0.3323,
    "dollar_rate": 0.0390,
    "p_err_earner": 0.5751,
    "p_err_no_earner": 0.2376,
    "p_over_given_err": 0.5778,
    "near_full_given_over": 0.0033,
    "dollar_p10": 2, "dollar_p25": 9, "dollar_p50": 22, "dollar_p90": 99,
    "dollar_mean": 42, "share_le56": 0.855,
    "med_over": 25, "med_under": 18,
    "cause97_blank": 0.8401,
    "national": {
        "finding_mix": {"1": 0.5986, "2": 0.2461, "3": 0.1554},
        "case_err_rate": 0.4014,
        "dollar_rate": 0.0873,
        "p_err_earner": 0.5859,
        "p_err_no_earner": 0.3333,
        "p_over_given_err": 0.6130,
        "near_full_given_over": 0.0574,
        "dollar_p10": 3, "dollar_p25": 11, "dollar_p50": 31, "dollar_p90": 202,
        "dollar_mean": 70, "share_le56": 0.691,
        "med_over": 37, "med_under": 23,
        "cause97_blank": 0.584,
    },
}

# UT/national ratios applied to the national dist (in-memory).
# Sparsity guards from the fit: bucket cells with UT unweighted n < 25,
# 97-share/97-coin cells with UT unweighted 97-n < 5, and direction cells
# with UT unweighted non-97 n < 25 keep the national value (ratio 1.0).
# it1 (pure empirical) values below; it2 realized-output calibration
# follows (see ut1_ut_generator.md).
UT_COIN_RATIO = {"earner": 0.9816, "no_earner": 0.7131}

# Global coin calibration scalar (fit by line search against the marginal UT
# case-error rate; the per-stratum ratios above preserve the conditional
# structure). it1 = 1.0 (pure empirical); the line search runs post-it1.
UT_COIN_CAL = 1.10

# Per-bucket element ratios, UT / national.
# it1 pure empirical: earned 1.2677, unearned 0.9107, shelter 1.0118,
# sua 0.7885, medical 1.0274; depcare/hhcomp/arithmetic keep the sparsity
# guard (1.0). it2 one-step realized-output calibration (x real_UT_share /
# synth_share from the it1 validation run) follows, mirroring PA1's it3 /
# NY1's it2 / SD1's it2.
UT_BUCKET_RATIO = {
    "earned": 1.4102, "unearned": 0.9105, "shelter": 1.0375,
    "sua": 0.6166, "medical": 1.4559, "depcare": 1.0,
    "hhcomp": 1.0, "arithmetic": 1.0,
}

# P(over | nature 97) ratios, UT / national, per bucket.
# it2: one-step realized-output calibration (x real/synth P(over|97,b)
# from the it1 pilot). it3: damped half-step (x sqrt(real/synth))
# second correction — the full one-step diverged (up to 2.5x) because
# drawn direction margins only partially materialize.
UT_97_RATIO = {
    "earned": 0.8565, "unearned": 1.1391, "shelter": 0.8731,
    "sua": 1.5065, "medical": 0.9974, "depcare": 1.0,
    "hhcomp": 1.0, "arithmetic": 1.0,
}

# P(nature=97 | bucket) ratios, UT / national, per bucket (it1 pure
# empirical). UT runs more timing variances than national on
# earned/unearned/medical, fewer on shelter/sua.
UT_97_SHARE_RATIO = {
    "earned": 1.6223, "unearned": 1.4949, "shelter": 0.6873,
    "sua": 0.7634, "medical": 1.5325, "depcare": 1.0,
    "hhcomp": 1.0, "arithmetic": 1.0,
}

# Direction balance among non-97 natures, UT / national, per bucket
# (it1 pure empirical). Behavioral direction classes (which way the benefit
# moves when the nature is applied; matches the _corrupt_* else-branches).
UT_OVER_NATURES = frozenset([35, 37, 38, 39, 53, 56, 7])
UT_UNDER_NATURES = frozenset([44, 52, 57, 6, 13])
# UT skews UNDER on earned/medical non-97 variances, OVER on shelter;
# unearned/sua near national. depcare/hhcomp/arithmetic keep 1.0 (guard).
UT_DIR_RATIO = {
    "earned": {"over": 1.2816, "under": 1.7626},
    "unearned": {"over": 1.759, "under": 1.3405},
    "shelter": {"over": 2.0305, "under": 0.8265},
    "sua": {"over": 2.1908, "under": 1.6461},
    "medical": {"over": 1.3359, "under": 1.5249},
    "depcare": {"over": 1.0, "under": 1.0},
    "hhcomp": {"over": 1.0, "under": 1.0},
    "arithmetic": {"over": 1.0, "under": 1.0},
}

# Cause mix ratios (coarse: client/agency/no_fault/other), UT / national,
# fit on NON-97 variances only — 97 causes are resampled from UT_97_CAUSE
# below. UT codes NO no-fault on substantive variances (no_fault 0.0 on
# every bucket — NY-like), so the SD1 it2b basis blowup cannot occur (0.0
# kills the term on any basis).
UT_CAUSE_RATIO = {
    "earned": {"client": 1.0576, "agency": 1.037, "no_fault": 0.0, "other": 0.6012},
    "unearned": {"client": 2.1326, "agency": 0.6812, "no_fault": 0.0, "other": 0.5949},
    "shelter": {"client": 1.6166, "agency": 0.3207, "no_fault": 0.0, "other": 0.3377},
    "sua": {"client": 2.0998, "agency": 0.5085, "no_fault": 0.0, "other": 0.0},
    "medical": {"client": 0.9733, "agency": 1.0245, "no_fault": 0.0, "other": 0.8615},
    "depcare": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
    "hhcomp": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
    "arithmetic": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
}

# UT empirical cause mix ON nature-97 variances, per bucket (raw cause codes).
# UT blanks 84.0% of 97 causes; the recorded remainder is mostly cause 26
# (no-fault), with client-coded 1s on earned/shelter. sua/medical/depcare/
# hhcomp/arithmetic per-bucket cells are too thin (n<5) so they carry the
# pooled UT fallback.
UT_97_CAUSE = {
    "earned": {"1": 0.0508, "26": 0.9492},
    "unearned": {"26": 1.0},
    "shelter": {"1": 0.2954, "4": 0.0857, "26": 0.619},
    "sua": {"1": 0.1097, "4": 0.0227, "26": 0.8676},
    "medical": {"1": 0.1097, "4": 0.0227, "26": 0.8676},
    "depcare": {"1": 0.1097, "4": 0.0227, "26": 0.8676},
    "hhcomp": {"1": 0.1097, "4": 0.0227, "26": 0.8676},
    "arithmetic": {"1": 0.1097, "4": 0.0227, "26": 0.8676},
}

# Dollar-size offsets: UT median error / national median error, per finding
# direction (relative-offset semantics — the generator's national level bias
# is orthogonal and owned by exp31's calibration). Applied as a multiplier
# on the agency-side amount delta inside the corruptors.
UT_S_OVER = 0.6757
UT_S_UNDER = 0.7826

# UT blanks cause on 84.0% of timing-97 variances (measured FY2022-2024).
UT_CAUSE97_BLANK = 0.8401

# Whole-unit ineligibility (mechanism 2): UT's near-full-benefit over share
# (0.0033) is ~1/17 of national (0.0574) — whole-unit errors are
# near-absent in UT. p_unit scales by the near-full|over ratio:
# 0.0125 * 0.0033/0.0574 ~= 0.00072 -> 0.0007.
UT_P_UNIT = 0.0007

_BUCKET_MIX_KEYS = (
    "bucket_probs",
    "bucket_probs_given_earner", "bucket_probs_given_no_earner",
    "bucket_probs_given_earner_senior", "bucket_probs_given_earner_nonsenior",
    "bucket_probs_given_no_earner_senior",
    "bucket_probs_given_no_earner_nonsenior",
)
_NATURE_MIX_KEYS = ("nature_given_bucket_earner", "nature_given_bucket_no_earner")


def _renorm(mix):
    tot = sum(mix.values())
    if tot > 0:
        for k in mix:
            mix[k] /= tot
    return mix


def apply_ut_offsets(dist):
    """Return a dist copy with the UT offset ratios applied (in-memory only).

    Takes the adopted-calibration dist (dollar_mech.adopted_dist output) and
    multiplies: injection coins, per-bucket 97-resolution coins, bucket mixes
    (all stratum keys), earner-conditional nature mixes (97-share and
    direction-balance margins), and per-bucket non-97 cause mixes — each by
    its UT/national ratio, renormalized. The input dist is never mutated.
    """
    d = copy.deepcopy(dist)

    # 1. injection coins. The adopted coins are attrition-corrected to land
    # the national empirical P(error | stratum); scaling by the UT/national
    # conditional ratio assumes materialization (a mechanics property) is
    # state-independent. UT's whole-unit mass is near-zero (UT_P_UNIT=0.0007 vs 0.0125 national);
    # the adopted unit-bucket correction still uses the national P_UNIT_DEFAULT,
    # leaving a tiny over-correction of the earned draw weight that the
    # it2 bucket recalibration absorbs.
    inj = d.get("injection_rate", {})
    for key in ("persistent", "earner", "no_earner"):
        sub = inj.get(key)
        if isinstance(sub, dict):
            for s, r in UT_COIN_RATIO.items():
                if s in sub:
                    sub[s] = min(0.99, sub[s] * r * UT_COIN_CAL)

    # 2. timing-97 resolution coins per bucket (direction margin).
    coins = inj.get("p_over_97_resolve", {})
    for b, r in UT_97_RATIO.items():
        if b in coins:
            coins[b] = min(0.95, max(0.05, coins[b] * r))

    # 3. element-bucket mixes (marginal ratios applied to every stratum key;
    # the recorded marginal then tracks UT regardless of stratum composition).
    for key in _BUCKET_MIX_KEYS:
        mix = d.get(key)
        if isinstance(mix, dict):
            for b, r in UT_BUCKET_RATIO.items():
                if b in mix:
                    mix[b] *= r
            _renorm(mix)

    # 4. nature mixes per bucket: 97-share margin and direction-balance
    # margin (marginal ratios on the earner-conditional mixes the injector
    # draws from).
    for key in _NATURE_MIX_KEYS:
        for b, nmap in d.get(key, {}).items():
            r97 = UT_97_SHARE_RATIO.get(b, 1.0)
            dr = UT_DIR_RATIO.get(b, {"over": 1.0, "under": 1.0})
            for n in list(nmap):
                ni = int(n)
                if ni == 97:
                    nmap[n] *= r97
                elif ni in UT_OVER_NATURES:
                    nmap[n] *= dr["over"]
                elif ni in UT_UNDER_NATURES:
                    nmap[n] *= dr["under"]
            _renorm(nmap)

    # 5. cause mixes per bucket (non-97 coarse ratios on the raw-code draws;
    # 97 causes are resampled from UT_97_CAUSE by the _draw_nature wrapper,
    # and 97-cause blanking is set to UT's 0.8710 by the _recorded_cause
    # wrapper).
    for b, cmap in d.get("cause_given_bucket", {}).items():
        ratios = UT_CAUSE_RATIO.get(b)
        if not ratios:
            continue
        for c in list(cmap):
            cmap[c] *= ratios.get(cause_bucket(int(c)), 1.0)
        _renorm(cmap)

    d.setdefault("_ut", {})["conditioned"] = True
    return d


# ---------------------------------------------------------------------------
# UT-only wrappers (installed by generate_ut, removed on return).
# ---------------------------------------------------------------------------
_INCOME_FIELDS = ("earned", "unearned")
_ut_saved = {}


def _ut_draw_nature(facts, bucket, dist, dir_w, rng):
    """Draw (nature, cause); on 97s resample the cause from UT's empirical
    97-cause mix (recorded basis, pre-blanking — UT blanks 87.1% of 97
    causes, far more than national's 65.4% pooled, so the national drawn
    97-cause mix is not a usable UT basis)."""
    nature, _cause = _ut_saved["draw_nature"](facts, bucket, dist, dir_w, rng)
    if nature == 97:
        mix = UT_97_CAUSE.get(bucket)
        if mix:
            r = rng.random()
            cum = 0.0
            for code, p in mix.items():
                cum += p
                if r < cum:
                    return nature, int(code)
            return nature, int(next(iter(mix)))
    return nature, _cause


def _ut_direction(field, base, new):
    """Benefit-direction implied by an agency-side amount change."""
    if field in _INCOME_FIELDS:
        return "over" if new < base else "under"
    return "over" if new > base else "under"


def _wrap_corruptor(orig):
    """Scale the realized agency-side amount delta by the UT dollar-size
    offset for the implied finding direction. Applied AFTER the adopted
    corruptor (mechanisms 1+4) runs, so it composes with the small-mode and
    coarse-under rescale; the benefit is recomputed downstream from the
    scaled agency facts, keeping facts->benefit mechanics consistent."""
    def wrapped(agency, truth, nature, rng, field, bucket, dist,
                _force_97_dir=None):
        base = truth[field]
        truth_corr, override = orig(agency, truth, nature, rng, field,
                                    bucket, dist,
                                    _force_97_dir=_force_97_dir)
        if truth_corr is not None and field in truth_corr:
            # omission: the truth had `amt` the agency never saw
            d = "over" if field in _INCOME_FIELDS else "under"
            s = UT_S_OVER if d == "over" else UT_S_UNDER
            truth_corr[field] = round(truth_corr[field] * s, 2)
        else:
            new = agency[field]
            if new != base:
                d = _ut_direction(field, base, new)
                s = UT_S_OVER if d == "over" else UT_S_UNDER
                agency[field] = round(base + s * (new - base), 2)
        return truth_corr, override
    return wrapped


def _ut_recorded_cause(nature, cause, rng):
    # UT blanks cause on 87.1% of timing-97 variances (pooled; national's
    # FY2024-calibrated wrapper blanks 32%). Consume the rng draw the
    # national path takes so the rng stream stays aligned with a same-seed
    # national run.
    if nature == 97:
        if rng.random() < UT_CAUSE97_BLANK:
            return None
        return cause
    return cause


def _enable_ut_wrappers():
    if _ut_saved:
        return
    _ut_saved["draw_nature"] = errors._draw_nature
    _ut_saved["income"] = errors._corrupt_income
    _ut_saved["deduction"] = errors._corrupt_deduction
    _ut_saved["recorded_cause"] = errors._recorded_cause
    errors._draw_nature = _ut_draw_nature
    errors._corrupt_income = _wrap_corruptor(errors._corrupt_income)
    errors._corrupt_deduction = _wrap_corruptor(errors._corrupt_deduction)
    errors._recorded_cause = _ut_recorded_cause


def _disable_ut_wrappers():
    if not _ut_saved:
        return
    errors._draw_nature = _ut_saved["draw_nature"]
    errors._corrupt_income = _ut_saved["income"]
    errors._corrupt_deduction = _ut_saved["deduction"]
    errors._recorded_cause = _ut_saved["recorded_cause"]
    _ut_saved.clear()


# ---------------------------------------------------------------------------
# UT-conditioned generation entry point.
# ---------------------------------------------------------------------------
def generate_ut(n=1000, seed=0, dist="experiments/dist.json", out=None,
                max_attempts=12, persistent_buckets=True, tag_state=True):
    """Generate n UT-conditioned synthetic QC cases.

    Pipeline: load national dist -> adopted calibration (exp31, in-memory)
    -> UT offset ratios (this module, in-memory) -> generate with the
    mechanism patches + UT wrappers installed. All patches are removed
    before return; national generation is unaffected.

    Each case dict matches the national schema plus "state": "UT".
    Returns the output path (or the list of JSON lines when out is None).
    """
    from . import dollar_mech, household
    from .distutil import load_dist

    d = load_dist(dist)
    d = dollar_mech.adopted_dist(d)
    d = apply_ut_offsets(d)

    mech_was_on = dollar_mech.is_enabled()
    dollar_mech.enable(under_scale=dollar_mech.EXP31_UNDER_SCALE)
    _enable_ut_wrappers()
    try:
        rng = random.Random(seed)
        lines = []
        for _ in range(n):
            facts = household.sample_household(rng)
            case = dollar_mech.inject_case(
                facts, rng, d, max_attempts=max_attempts,
                persistent_buckets=persistent_buckets,
                p_unit=UT_P_UNIT)
            if tag_state:
                case["state"] = "UT"
            lines.append(json.dumps(case))
    finally:
        _disable_ut_wrappers()
        if not mech_was_on:
            dollar_mech.disable()

    if out is None:
        return lines
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Generate UT-conditioned synthetic QC cases.")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dist", required=True, help="empirical distribution JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-attempts", type=int, default=12)
    ap.add_argument("--persistent-buckets",
                    action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--no-state-tag", action="store_true",
                    help="omit the 'state': 'UT' tag on cases")
    args = ap.parse_args()
    generate_ut(n=args.n, seed=args.seed, dist=args.dist, out=args.out,
                max_attempts=args.max_attempts,
                persistent_buckets=args.persistent_buckets,
                tag_state=not args.no_state_tag)
    print(f"wrote {args.n} UT-conditioned cases -> {args.out}")


if __name__ == "__main__":
    main()
