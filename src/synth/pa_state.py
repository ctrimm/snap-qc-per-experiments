"""PA-conditioned synthetic QC generation (PA1).

Pennsylvania offsets for the SNAP QC synthetic generator. Fit from pooled
FY2020-2024 QC public-use microdata (STATE='42', n=3,268; FYWGT-weighted;
microdata-implied rates, NOT FNS-published rates) — see
experiments/pa1_pa_generator.md and `python3 experiments/pa1_pa_generator.py
fit` for the provenance of every constant below.

Design: PA conditioning is a set of *relative offsets* applied to the
national (adopted-default) generator's dist, in-memory only. The national
path is untouched: importing this module installs nothing, and
`generate_pa()` restores every patch it installs. National (default)
generation behavior is byte-identical with or without this module.

What PA looks like vs national (pooled, FYWGT-weighted):
- errs more often (case-weighted 41.3% vs 38.5%) but with SMALLER errors
  (median error $25 vs $28). Per exp33, the state-specific part lives in
  error SIZE, so dollar offsets are relative scales, not absolute targets.
- error mix is shelter-heavy (45.9% of variances vs 31.8%) and
  unearned-light (17.0% vs 24.8%).
- PA has fewer timing-97 variances than national (33.9% vs ~43% of
  variances), and its non-97 natures are more directional (both over and
  under up ~1.1-1.4x per bucket; "other" natures down).
- PA never leaves cause blank on timing-97 variances (0.000 all FYs vs
  0.32 national FY2024 / 0.68 pooled) and records mostly cause 99
  (undetermined) on them. PA never uses cause 26 (no-fault) on
  substantive (non-97) variances.
- PA's benefit engine matches statute 99.7-100% every FY (exp8c), so all
  offsets below are process/human-layer (mixes, rates, sizes) — no engine
  parameters are touched.

API for PA2 (copy-paste):
    from src.synth.pa_state import generate_pa
    generate_pa(n=20000, seed=7, dist="experiments/dist.json",
               out="data/pa_synth.jsonl")

Shell:
    python3 -m src.synth.pa_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out data/pa_synth.jsonl

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
# PA empirical targets (pooled FY2020-2024 QC, STATE='42', FYWGT-weighted).
# National reference is pooled FY2020-2024 microdata-implied (same basis).
# ---------------------------------------------------------------------------
PA_OFFSETS = {
    "finding_mix": {"1": 0.5875, "2": 0.2469, "3": 0.1656},
    "case_err_rate": 0.4125,
    "dollar_rate": 0.0846,
    "p_err_earner": 0.5468,
    "p_err_no_earner": 0.3624,
    "p_over_given_err": 0.5985,
    "near_full_given_over": 0.0529,
    "dollar_p10": 3, "dollar_p25": 8, "dollar_p50": 25, "dollar_p90": 156,
    "dollar_mean": 57, "share_le56": 0.752,
    "med_over": 31, "med_under": 18,
    "cause97_blank": 0.0,
    "national": {
        "finding_mix": {"1": 0.6151, "2": 0.2372, "3": 0.1477},
        "case_err_rate": 0.3849,
        "dollar_rate": 0.0859,
        "p_err_earner": 0.5675,
        "p_err_no_earner": 0.3193,
        "p_over_given_err": 0.6162,
        "near_full_given_over": 0.0576,
        "dollar_p10": 3, "dollar_p25": 9, "dollar_p50": 28, "dollar_p90": 187,
        "dollar_mean": 66, "share_le56": 0.700,
        "med_over": 34, "med_under": 21,
        "cause97_blank": 0.678,
    },
}

# PA/national ratios applied to the national dist (in-memory).
# Sparsity guards from the fit: bucket cells with PA unweighted n < 25,
# 97-share/97-coin cells with PA unweighted 97-n < 5, and direction cells
# with PA unweighted non-97 n < 25 keep the national value (ratio 1.0).
PA_COIN_RATIO = {"earner": 0.9635, "no_earner": 1.1351}

# Global coin calibration scalar (fit by line search against the marginal PA
# case-error rate; the per-stratum ratios above preserve the conditional
# structure). 1.0 = pure empirical ratios. Set to 1.08: the no_earner coin
# hits its 0.99 ceiling (P(err|no_earner) caps at ~0.335 vs 0.362 empirical —
# a structural materialization limit: PA's shelter-heavy mix materializes
# worse than the national mix the draw correction was measured under).
# The 1.08 scalar lifts the marginal to 0.399 (vs 0.4125) and lands
# finding L1 0.028, at the cost of P(err|earner) 0.576 vs 0.547 empirical.
# Documented in pa1_pa_generator.md; revisit if the materialization model
# becomes state-conditional.
PA_COIN_CAL = 1.08

PA_BUCKET_RATIO = {
    "earned": 0.9492, "unearned": 0.6723, "shelter": 1.5425,
    "sua": 0.5368, "medical": 1.5631, "depcare": 1.0,
    "hhcomp": 0.6117, "arithmetic": 1.0,
}
# Note: the shelter/medical/hhcomp/sua ratios above include a one-step
# realized-output calibration (x real_PA_share / synth_share from the it2
# validation run). The pure empirical PA/national ratios are shelter 1.442,
# medical 1.162, hhcomp 0.948, sua 0.616; the calibration corrects for the
# PA nature-mix shift changing per-bucket materialization (the national
# materialization correction in the draw was measured under the national
# nature mix). See pa1_pa_generator.md.

# P(over | nature 97) ratios, PA / national, per bucket.
PA_97_RATIO = {
    "earned": 1.0449, "unearned": 0.9331, "shelter": 0.7963,
    "sua": 1.6499, "medical": 0.3998, "depcare": 1.0,
    "hhcomp": 1.0, "arithmetic": 1.0,
}

# P(nature=97 | bucket) ratios, PA / national, per bucket.
PA_97_SHARE_RATIO = {
    "earned": 1.0978, "unearned": 0.3623, "shelter": 0.8936, "sua": 0.7383,
    "medical": 0.2497, "depcare": 1.0, "hhcomp": 1.0, "arithmetic": 1.0,
}

# Direction balance among non-97 natures, PA / national, per bucket.
# Behavioral direction classes (which way the benefit moves when the nature
# is applied; matches the _corrupt_* else-branches). Note nature 39 is
# behaviorally over but sits in errors._dirclass "other" — the national
# dir_weight and these PA ratios compose multiplicatively, so the
# classification only needs to be consistent between fit and apply.
PA_OVER_NATURES = frozenset([35, 37, 38, 39, 53, 56, 7])
PA_UNDER_NATURES = frozenset([44, 52, 57, 6, 13])
PA_DIR_RATIO = {
    "earned": {"over": 1.1838, "under": 1.1257},
    "unearned": {"over": 1.0874, "under": 1.3149},
    "shelter": {"over": 1.1536, "under": 1.2187},
    "sua": {"over": 1.1197, "under": 0.5914},
    "medical": {"over": 1.1675, "under": 0.8024},
    "depcare": {"over": 1.0, "under": 1.0},
    "hhcomp": {"over": 1.4122, "under": 1.4298},
    "arithmetic": {"over": 1.0, "under": 1.0},
}

# Cause mix ratios (coarse: client/agency/no_fault/other), PA / national,
# fit on NON-97 variances only — 97 causes are resampled from PA_97_CAUSE
# below, because the national 97-cause draw is distorted by national's
# 97-cause blanking (which PA does not do). Note no_fault = 0.0: PA never
# uses cause 26 on substantive variances.
PA_CAUSE_RATIO = {
    "earned": {"client": 1.1111, "agency": 1.0086, "no_fault": 0.0, "other": 0.5736},
    "unearned": {"client": 0.5682, "agency": 1.1790, "no_fault": 0.0, "other": 0.9828},
    "shelter": {"client": 1.0368, "agency": 0.9782, "no_fault": 0.0, "other": 0.8191},
    "sua": {"client": 0.4599, "agency": 1.3893, "no_fault": 0.0, "other": 0.3875},
    "medical": {"client": 0.0, "agency": 1.1870, "no_fault": 0.0, "other": 0.4356},
    "depcare": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
    "hhcomp": {"client": 1.1003, "agency": 1.1193, "no_fault": 0.0, "other": 0.3024},
    "arithmetic": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
}

# PA empirical cause mix ON nature-97 variances, per bucket (raw cause codes).
# PA records a cause on every 97 (never blanks) and it is usually 99
# (undetermined). Buckets with PA unweighted 97-n < 5 fall back to the pooled
# PA 97-cause mix (the depcare/hhcomp/arithmetic entries below).
PA_97_CAUSE = {
    "earned": {"99": 0.5668, "1": 0.2493, "26": 0.1592, "10": 0.0182, "16": 0.0066},
    "unearned": {"99": 0.4440, "1": 0.1872, "26": 0.1277, "15": 0.0633,
                 "19": 0.0620, "20": 0.0484, "12": 0.0348, "18": 0.0325},
    "shelter": {"99": 0.4821, "1": 0.3285, "26": 0.1033, "2": 0.0322,
                "4": 0.0287, "7": 0.0223, "12": 0.0029},
    "sua": {"99": 0.7024, "1": 0.1303, "18": 0.0929, "20": 0.0744},
    "medical": {"99": 0.5044, "1": 0.4956},
    "depcare": {"99": 0.5088, "1": 0.2937, "26": 0.1194, "2": 0.0194,
                "4": 0.0172, "7": 0.0134, "10": 0.0054, "20": 0.0047,
                "15": 0.0041, "12": 0.0040, "19": 0.0040, "18": 0.0040,
                "16": 0.0019},
    "hhcomp": {"99": 0.5088, "1": 0.2937, "26": 0.1194, "2": 0.0194,
               "4": 0.0172, "7": 0.0134, "10": 0.0054, "20": 0.0047,
               "15": 0.0041, "12": 0.0040, "19": 0.0040, "18": 0.0040,
               "16": 0.0019},
    "arithmetic": {"99": 0.5088, "1": 0.2937, "26": 0.1194, "2": 0.0194,
                   "4": 0.0172, "7": 0.0134, "10": 0.0054, "20": 0.0047,
                   "15": 0.0041, "12": 0.0040, "19": 0.0040, "18": 0.0040,
                   "16": 0.0019},
}

# Dollar-size offsets: PA median error / national median error, per finding
# direction (relative-offset semantics — the generator's national level bias
# is orthogonal and owned by exp31's calibration). Applied as a multiplier
# on the agency-side amount delta inside the corruptors, so the
# facts->benefit math stays mechanics-consistent.
PA_S_OVER = 0.9118
PA_S_UNDER = 0.8571

# PA never blanks cause on timing-97 variances (measured 0.000 in every FY).
PA_CAUSE97_BLANK = 0.0

# Whole-unit ineligibility (mechanism 2): PA's near-full-benefit over share
# (0.0529) matches national (0.0576), so p_unit stays at the national default.
PA_P_UNIT = None  # None = keep dollar_mech.P_UNIT_DEFAULT

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


def apply_pa_offsets(dist):
    """Return a dist copy with the PA offset ratios applied (in-memory only).

    Takes the adopted-calibration dist (dollar_mech.adopted_dist output) and
    multiplies: injection coins, per-bucket 97-resolution coins, bucket mixes
    (all stratum keys), earner-conditional nature mixes (97-share and
    direction-balance margins), and per-bucket non-97 cause mixes — each by
    its PA/national ratio, renormalized. The input dist is never mutated.
    """
    d = copy.deepcopy(dist)

    # 1. injection coins. The adopted coins are attrition-corrected to land
    # the national empirical P(error | stratum); scaling by the PA/national
    # conditional ratio assumes materialization (a mechanics property) is
    # state-independent. The whole-unit mass is unchanged for PA, so no
    # re-derivation of the unit-bucket correction is needed.
    inj = d.get("injection_rate", {})
    for key in ("persistent", "earner", "no_earner"):
        sub = inj.get(key)
        if isinstance(sub, dict):
            for s, r in PA_COIN_RATIO.items():
                if s in sub:
                    sub[s] = min(0.99, sub[s] * r * PA_COIN_CAL)

    # 2. timing-97 resolution coins per bucket (direction margin).
    coins = inj.get("p_over_97_resolve", {})
    for b, r in PA_97_RATIO.items():
        if b in coins:
            coins[b] = min(0.95, max(0.05, coins[b] * r))

    # 3. element-bucket mixes (marginal ratios applied to every stratum key;
    # the recorded marginal then tracks PA regardless of stratum composition).
    for key in _BUCKET_MIX_KEYS:
        mix = d.get(key)
        if isinstance(mix, dict):
            for b, r in PA_BUCKET_RATIO.items():
                if b in mix:
                    mix[b] *= r
            _renorm(mix)

    # 4. nature mixes per bucket: 97-share margin and direction-balance
    # margin (marginal ratios on the earner-conditional mixes the injector
    # draws from).
    for key in _NATURE_MIX_KEYS:
        for b, nmap in d.get(key, {}).items():
            r97 = PA_97_SHARE_RATIO.get(b, 1.0)
            dr = PA_DIR_RATIO.get(b, {"over": 1.0, "under": 1.0})
            for n in list(nmap):
                ni = int(n)
                if ni == 97:
                    nmap[n] *= r97
                elif ni in PA_OVER_NATURES:
                    nmap[n] *= dr["over"]
                elif ni in PA_UNDER_NATURES:
                    nmap[n] *= dr["under"]
            _renorm(nmap)

    # 5. cause mixes per bucket (non-97 coarse ratios on the raw-code draws;
    # 97 causes are resampled from PA_97_CAUSE by the _draw_nature wrapper,
    # and 97-cause blanking is zeroed by the _recorded_cause wrapper).
    for b, cmap in d.get("cause_given_bucket", {}).items():
        ratios = PA_CAUSE_RATIO.get(b)
        if not ratios:
            continue
        for c in list(cmap):
            cmap[c] *= ratios.get(cause_bucket(int(c)), 1.0)
        _renorm(cmap)

    d.setdefault("_pa", {})["conditioned"] = True
    return d


# ---------------------------------------------------------------------------
# PA-only wrappers (installed by generate_pa, removed on return).
# ---------------------------------------------------------------------------
_INCOME_FIELDS = ("earned", "unearned")
_pa_saved = {}


def _pa_draw_nature(facts, bucket, dist, dir_w, rng):
    """Draw (nature, cause); on 97s resample the cause from PA's empirical
    97-cause mix (PA records a cause on every 97, usually 99/undetermined —
    unlike national, where 32% are blanked and the recorded remainder skews
    toward no-fault 26)."""
    nature, _cause = _pa_saved["draw_nature"](facts, bucket, dist, dir_w, rng)
    if nature == 97:
        mix = PA_97_CAUSE.get(bucket)
        if mix:
            r = rng.random()
            cum = 0.0
            for code, p in mix.items():
                cum += p
                if r < cum:
                    return nature, int(code)
            return nature, int(next(iter(mix)))
    return nature, _cause


def _pa_direction(field, base, new):
    """Benefit-direction implied by an agency-side amount change."""
    if field in _INCOME_FIELDS:
        return "over" if new < base else "under"
    return "over" if new > base else "under"


def _wrap_corruptor(orig):
    """Scale the realized agency-side amount delta by the PA dollar-size
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
            s = PA_S_OVER if d == "over" else PA_S_UNDER
            truth_corr[field] = round(truth_corr[field] * s, 2)
        else:
            new = agency[field]
            if new != base:
                d = _pa_direction(field, base, new)
                s = PA_S_OVER if d == "over" else PA_S_UNDER
                agency[field] = round(base + s * (new - base), 2)
        return truth_corr, override
    return wrapped


def _pa_recorded_cause(nature, cause, rng):
    # PA never blanks cause on timing-97 variances (0.000 measured, all FYs;
    # national blanks 0.32). Consume the rng draw the national path would
    # take so the rng stream stays aligned with a same-seed national run.
    if nature == 97:
        rng.random()
        return cause
    return cause


def _enable_pa_wrappers():
    if _pa_saved:
        return
    _pa_saved["draw_nature"] = errors._draw_nature
    _pa_saved["income"] = errors._corrupt_income
    _pa_saved["deduction"] = errors._corrupt_deduction
    _pa_saved["recorded_cause"] = errors._recorded_cause
    errors._draw_nature = _pa_draw_nature
    errors._corrupt_income = _wrap_corruptor(errors._corrupt_income)
    errors._corrupt_deduction = _wrap_corruptor(errors._corrupt_deduction)
    errors._recorded_cause = _pa_recorded_cause


def _disable_pa_wrappers():
    if not _pa_saved:
        return
    errors._draw_nature = _pa_saved["draw_nature"]
    errors._corrupt_income = _pa_saved["income"]
    errors._corrupt_deduction = _pa_saved["deduction"]
    errors._recorded_cause = _pa_saved["recorded_cause"]
    _pa_saved.clear()


# ---------------------------------------------------------------------------
# PA-conditioned generation entry point.
# ---------------------------------------------------------------------------
def generate_pa(n=1000, seed=0, dist="experiments/dist.json", out=None,
                max_attempts=12, persistent_buckets=True, tag_state=True):
    """Generate n PA-conditioned synthetic QC cases.

    Pipeline: load national dist -> adopted calibration (exp31, in-memory)
    -> PA offset ratios (this module, in-memory) -> generate with the
    mechanism patches + PA wrappers installed. All patches are removed
    before return; national generation is unaffected.

    Each case dict matches the national schema plus "state": "PA".
    Returns the output path (or the list of JSON lines when out is None).
    """
    from . import dollar_mech, household
    from .distutil import load_dist

    d = load_dist(dist)
    d = dollar_mech.adopted_dist(d)
    d = apply_pa_offsets(d)

    mech_was_on = dollar_mech.is_enabled()
    dollar_mech.enable(under_scale=dollar_mech.EXP31_UNDER_SCALE)
    _enable_pa_wrappers()
    try:
        rng = random.Random(seed)
        lines = []
        for _ in range(n):
            facts = household.sample_household(rng)
            case = dollar_mech.inject_case(
                facts, rng, d, max_attempts=max_attempts,
                persistent_buckets=persistent_buckets)
            if tag_state:
                case["state"] = "PA"
            lines.append(json.dumps(case))
    finally:
        _disable_pa_wrappers()
        if not mech_was_on:
            dollar_mech.disable()

    if out is None:
        return lines
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Generate PA-conditioned synthetic QC cases.")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dist", required=True, help="empirical distribution JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-attempts", type=int, default=12)
    ap.add_argument("--persistent-buckets",
                    action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--no-state-tag", action="store_true",
                    help="omit the 'state': 'PA' tag on cases")
    args = ap.parse_args()
    generate_pa(n=args.n, seed=args.seed, dist=args.dist, out=args.out,
                max_attempts=args.max_attempts,
                persistent_buckets=args.persistent_buckets,
                tag_state=not args.no_state_tag)
    print(f"wrote {args.n} PA-conditioned cases -> {args.out}")


if __name__ == "__main__":
    main()
