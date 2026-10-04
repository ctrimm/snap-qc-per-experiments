"""ID-conditioned synthetic QC generation (ID1).

Idaho offsets for the SNAP QC synthetic generator. Fit from pooled
FY2022-2024 QC public-use microdata (STATE='16', n=3,111; FYWGT-weighted;
microdata-implied rates, NOT FNS-published rates) — see
experiments/id1_id_generator.md and `python3 experiments/id1_id_generator.py
fit` for the provenance of every constant below.

FITTING-WINDOW NOTE (NY6 lesson): FY2020 (n=515) and FY2021 (n=213) are
partial-year/thin QC files for Idaho; the offsets are fit on FY2022-2024
only. The ID2 holdout is still built on all pooled FY2020-2024 rows
(stratified 75/25, seed 20260929).

Design: ID conditioning is a set of *relative offsets* applied to the
national (adopted-default) generator's dist, in-memory only. The national
path is untouched: importing this module installs nothing, and
`generate_id()` restores every patch it installs. National (default)
generation behavior is byte-identical with or without this module.

What ID looks like vs national (pooled FY2022-24, FYWGT-weighted):
- errs less often (case-weighted 33.9% vs 40.1%) with an over share of
  61.5% vs 61.3%; the dollar rate is much lower (0.0366 vs 0.0873) and
  errors are much smaller (p50 $19 vs $31, p90 $87 vs $202, mean $36 vs
  $70; medO $21/$37, medU $15/$23; 86.9% of errors <=$56).
- error mix is earned-heavy (1.15x national share) and shelter-heavy
  (1.31x); unearned-light (0.74x), sua-light (0.68x), medical-light (0.62x).
- ID has far MORE timing-97 variances than national (97-share ratios
  1.4-4.4x per bucket).
- direction: on non-97 variances ID is strongly UNDER-skewed on unearned
  (under 0.40x) and shelter (over 0.12x / under 0.07x) vs national.
- ID blanks cause on 50.2% of timing-97 variances (national 58.5%) — ID
  records causes on 97s slightly MORE often than national; the recorded
  97-cause mix is dominated by causes 1 and 26.
- on substantive (non-97) variances ID's cause mix tilts client/other
  (earned client 0.99x/agency 0.73x/other 2.51x; shelter other 4.10x;
  medical client 3.70x) — "other"-coded causes run 1.5-4.1x national.
- near-full|over 0.0076 vs 0.0573 national — whole-unit ineligibility is
  rare in ID, so p_unit is scaled down to 0.0017
  (P_UNIT_DEFAULT x 0.0076/0.0573).

API for ID2 (copy-paste):
    from src.synth.id_state import generate_id
    generate_id(n=20000, seed=7, dist="experiments/dist.json",
               out="data/id_synth.jsonl")

Shell:
    python3 -m src.synth.id_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out data/id_synth.jsonl

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
# ID empirical targets (pooled FY2022-2024 QC, STATE='16', FYWGT-weighted).
# National reference is pooled FY2022-2024 microdata-implied (same basis,
# excluding ID rows).
# ---------------------------------------------------------------------------
ID_OFFSETS = {
    "finding_mix": {"1": 0.6609, "2": 0.2084, "3": 0.1307},
    "case_err_rate": 0.3391,
    "dollar_rate": 0.0366,
    "p_err_earner": 0.4620,
    "p_err_no_earner": 0.2852,
    "p_over_given_err": 0.6146,
    "near_full_given_over": 0.0076,
    "dollar_p10": 2, "dollar_p25": 7, "dollar_p50": 19, "dollar_p90": 87,
    "dollar_mean": 36, "share_le56": 0.869,
    "med_over": 21, "med_under": 15,
    "cause97_blank": 0.5021,
    "national": {
        "finding_mix": {"1": 0.5986, "2": 0.2460, "3": 0.1554},
        "case_err_rate": 0.4014,
        "dollar_rate": 0.0873,
        "p_err_earner": 0.5862,
        "p_err_no_earner": 0.3331,
        "p_over_given_err": 0.6129,
        "near_full_given_over": 0.0573,
        "dollar_p10": 3, "dollar_p25": 11, "dollar_p50": 31, "dollar_p90": 202,
        "dollar_mean": 70, "share_le56": 0.691,
        "med_over": 37, "med_under": 23,
        "cause97_blank": 0.585,
    },
}

# ID/national ratios applied to the national dist (in-memory).
# Sparsity guards from the fit: bucket cells with ID unweighted n < 25,
# 97-share/97-coin cells with ID unweighted 97-n < 5, and direction cells
# with ID unweighted non-97 n < 25 keep the national value (ratio 1.0).
# it1 (pure empirical) values below; it2 realized-output calibration
# follows (see id1_id_generator.md).
ID_COIN_RATIO = {"earner": 0.7881, "no_earner": 0.8562}

# Global coin calibration scalar (fit by line search against the marginal ID
# case-error rate; the per-stratum ratios above preserve the conditional
# structure). 1.0 = pure empirical ratios.
# it2: line search over {0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30}
# after the recalibrations. 1.20 wins (finding L1=0.0235, case_err 0.3450
# vs 0.3391 real) — a larger upward correction than SD's 1.05/PA's 1.08,
# because ID's deep coin cuts (0.79/0.86) plus small-dollar errors
# materialize less often than the national-calibrated correction expects.
# (see id1_id_generator.md). it1's pure-empirical 1.0 undershot the case
# rate at 0.2806 vs 0.3391 (ID's deep coin cuts + small-dollar errors
# materialize less often than the national-calibrated correction expects);
# like SD's 1.05 / PA's 1.08, ID needs an upward correction.
ID_COIN_CAL = 1.20

# Per-bucket element ratios, ID / national.
# it1: pure empirical (earned 1.1547, unearned 0.7401, shelter 1.312,
# sua 0.6802, medical 0.6235; depcare/hhcomp/arithmetic keep the sparsity
# guard 1.0). it2: one-step realized-output calibration
# (x real_ID_share / synth_share from the it1 20k pilot).
ID_BUCKET_RATIO = {
    "earned": 1.4167,
    "unearned": 0.7064,
    "shelter": 1.3036,
    "sua": 0.5914,
    "medical": 0.8405,
    "depcare": 1.0,
    "hhcomp": 1.0,
    "arithmetic": 1.0,
}

# P(over | nature 97) ratios, ID / national, per bucket.
# it1: pure empirical (earned 1.0123, unearned 1.1836, shelter 1.23,
# sua 0.5951, medical 1.0533, depcare 0.6292, hhcomp 0.9899; arithmetic 1.0).
# it2: one-step realized-output calibration
# (x real_ID_P(over|97,b) / synth_P(over|97,b) from the it1 pilot).
ID_97_RATIO = {
    "earned": 1.0289,
    "unearned": 1.1876,
    "shelter": 1.3784,
    "sua": 0.8929,
    "medical": 1.2263,
    "depcare": 1.063,
    "hhcomp": 0.6648,
    "arithmetic": 1.0,
}

# P(nature=97 | bucket) ratios, ID / national, per bucket. ID runs far more
# timing variances than national on every bucket.
# it1: pure empirical (earned 1.9188, unearned 1.4511, shelter 1.3812,
# sua 2.2579, medical 1.9884, depcare 2.8983, hhcomp 4.3906; arithmetic 1.0).
# it2: one-step realized-output calibration (x real_ID_P(97|b) /
# synth_P(97|b) from the it1 pilot).
ID_97_SHARE_RATIO = {
    "earned": 2.2075,
    "unearned": 1.3317,
    "shelter": 1.0654,
    "sua": 1.926,
    "medical": 2.3014,
    "depcare": 4.3686,
    "hhcomp": 5.4431,
    "arithmetic": 1.0,
}

# Direction balance among non-97 natures, ID / national, per bucket.
# Behavioral direction classes (which way the benefit moves when the nature
# is applied; matches the _corrupt_* else-branches).
ID_OVER_NATURES = frozenset([35, 37, 38, 39, 53, 56, 7])
ID_UNDER_NATURES = frozenset([44, 52, 57, 6, 13])
# it1: pure empirical (earned 0.5557/0.9502, unearned 0.7280/0.4024,
# shelter 0.1218/0.0679, sua 0.2757/0.7217; medical/depcare/hhcomp/
# arithmetic keep the sparsity guard 1.0).
# it2: one-step realized-output calibration on the non-97 slice
# (over x= real/synth P(over|non97,b); under x= real/synth P(under|non97,b)).
ID_DIR_RATIO = {
    "earned": {'over': 0.4807, 'under': 0.796},
    "unearned": {'over': 0.6987, 'under': 0.2668},
    "shelter": {'over': 0.0257, 'under': 0.0128},
    "sua": {'over': 0.3112, 'under': 0.4792},
    "medical": {'over': 1.0, 'under': 1.0},
    "depcare": {'over': 1.0, 'under': 1.0},
    "hhcomp": {'over': 1.0, 'under': 1.0},
    "arithmetic": {'over': 1.0, 'under': 1.0},
}

# Cause mix ratios (coarse: client/agency/no_fault/other), ID / national,
# fit on NON-97 variances only — 97 causes are resampled from ID_97_CAUSE
# below.
#
# it2b BASIS CORRECTION (cause-ratio blowup found 2026-10-03 on the SD
# track): the fit's pure non-97-vs-national-non-97 ratios are honest
# against the national NON-97 empirical mix, but apply_id_offsets
# multiplies them onto the dist's MIXED cause basis (dist
# cause_given_bucket includes the 97-draw basis). The baked ratios below
# are rebased as ID_non97_mix / dist_mixed_basis — same ratio
# architecture, basis-aligned denominator. (ID's pure no_fault ratio is
# 0.0, which kills the term on any basis; the rebasing matters for the
# client/agency/other cells, e.g. shelter other 4.10x.)
#
# it3: one-step residual correction on the five fitted buckets'
# non-97 cause cells (x real_cell/synth_cell from the it2 validation run;
# factors 0.87-1.16). Guarded buckets (depcare/hhcomp/arithmetic) keep 1.0.
# no_fault stays 0.0 (ID records no no-fault causes on substantive variances).
ID_CAUSE_RATIO = {
    "earned": {"client": 1.4036, "agency": 1.0572, "no_fault": 0.0, "other": 3.3208},
    "unearned": {"client": 1.6665, "agency": 0.5528, "no_fault": 0.0, "other": 3.4745},
    "shelter": {"client": 2.0368, "agency": 0.4836, "no_fault": 0.0, "other": 4.939},
    "sua": {"client": 2.2376, "agency": 0.5535, "no_fault": 0.0, "other": 1.7676},
    "medical": {"client": 5.0771, "agency": 0.7972, "no_fault": 0.0, "other": 2.3202},
    "depcare": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
    "hhcomp": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
    "arithmetic": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
}

# ID empirical cause mix ON nature-97 variances, per bucket (raw cause codes).
# ID blanks 50.2% of 97 causes; the recorded remainder is dominated by
# causes 1 and 26. depcare/hhcomp/arithmetic fell back to the pooled mix
# (unweighted 97-n < 5 per bucket).
ID_97_CAUSE = {
    "earned": {"1": 0.4956, "2": 0.0094, "4": 0.0091, "20": 0.0083, "26": 0.4243, "99": 0.0533},
    "unearned": {"1": 0.4196, "2": 0.0182, "3": 0.0186, "4": 0.0155, "10": 0.0198, "12": 0.0231, "19": 0.0174, "26": 0.4334, "99": 0.0345},
    "shelter": {"1": 0.4424, "2": 0.0545, "3": 0.0138, "4": 0.1054, "14": 0.0061, "16": 0.0153, "18": 0.0055, "26": 0.3195, "99": 0.0376},
    "sua": {"1": 0.1699, "10": 0.0651, "21": 0.0759, "26": 0.6891},
    "medical": {"1": 0.8962, "10": 0.1038},
    "depcare": {"1": 0.4606, "2": 0.0301, "3": 0.0091, "4": 0.0522, "10": 0.0082, "12": 0.0037, "14": 0.0027, "16": 0.0068, "18": 0.0025, "19": 0.0057, "20": 0.0025, "21": 0.0029, "26": 0.3745, "99": 0.0385},
    "hhcomp": {"1": 0.4606, "2": 0.0301, "3": 0.0091, "4": 0.0522, "10": 0.0082, "12": 0.0037, "14": 0.0027, "16": 0.0068, "18": 0.0025, "19": 0.0057, "20": 0.0025, "21": 0.0029, "26": 0.3745, "99": 0.0385},
    "arithmetic": {"1": 0.4606, "2": 0.0301, "3": 0.0091, "4": 0.0522, "10": 0.0082, "12": 0.0037, "14": 0.0027, "16": 0.0068, "18": 0.0025, "19": 0.0057, "20": 0.0025, "21": 0.0029, "26": 0.3745, "99": 0.0385},
}

# Dollar-size offsets: ID median error / national median error, per finding
# direction (relative-offset semantics — the generator's national level bias
# is orthogonal and owned by exp31's calibration). Applied as a multiplier
# on the agency-side amount delta inside the corruptors, so the
# facts->benefit math stays mechanics-consistent. ID's errors are much
# smaller than national (p90 $87 vs $202); the uniform scale captures the
# level shift, not the shape.
ID_S_OVER = 0.5676
ID_S_UNDER = 0.6522

# ID blanks cause on 50.2% of timing-97 variances (measured FY2022-24).
ID_CAUSE97_BLANK = 0.5021

# Whole-unit ineligibility (mechanism 2): ID's near-full-benefit over share
# (0.0076) is ~1/7.5 of national (0.0573) — whole-unit errors are rare in
# ID. p_unit scales by the near-full|over ratio:
# 0.0125 * 0.0076/0.0573 ~= 0.00166 -> 0.0017.
ID_P_UNIT = 0.0017

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


def apply_id_offsets(dist):
    """Return a dist copy with the ID offset ratios applied (in-memory only).

    Takes the adopted-calibration dist (dollar_mech.adopted_dist output) and
    multiplies: injection coins, per-bucket 97-resolution coins, bucket mixes
    (all stratum keys), earner-conditional nature mixes (97-share and
    direction-balance margins), and per-bucket non-97 cause mixes — each by
    its ID/national ratio, renormalized. The input dist is never mutated.
    """
    d = copy.deepcopy(dist)

    # 1. injection coins. The adopted coins are attrition-corrected to land
    # the national empirical P(error | stratum); scaling by the ID/national
    # conditional ratio assumes materialization (a mechanics property) is
    # state-independent. ID's whole-unit mass is near-zero (ID_P_UNIT=0.0005 vs 0.0125 national);
    # the adopted unit-bucket correction still uses the national P_UNIT_DEFAULT,
    # leaving a tiny over-correction of the earned draw weight that the
    # it2 bucket recalibration absorbs.
    inj = d.get("injection_rate", {})
    for key in ("persistent", "earner", "no_earner"):
        sub = inj.get(key)
        if isinstance(sub, dict):
            for s, r in ID_COIN_RATIO.items():
                if s in sub:
                    sub[s] = min(0.99, sub[s] * r * ID_COIN_CAL)

    # 2. timing-97 resolution coins per bucket (direction margin).
    coins = inj.get("p_over_97_resolve", {})
    for b, r in ID_97_RATIO.items():
        if b in coins:
            coins[b] = min(0.95, max(0.05, coins[b] * r))

    # 3. element-bucket mixes (marginal ratios applied to every stratum key;
    # the recorded marginal then tracks ID regardless of stratum composition).
    for key in _BUCKET_MIX_KEYS:
        mix = d.get(key)
        if isinstance(mix, dict):
            for b, r in ID_BUCKET_RATIO.items():
                if b in mix:
                    mix[b] *= r
            _renorm(mix)

    # 4. nature mixes per bucket: 97-share margin and direction-balance
    # margin (marginal ratios on the earner-conditional mixes the injector
    # draws from).
    for key in _NATURE_MIX_KEYS:
        for b, nmap in d.get(key, {}).items():
            r97 = ID_97_SHARE_RATIO.get(b, 1.0)
            dr = ID_DIR_RATIO.get(b, {"over": 1.0, "under": 1.0})
            for n in list(nmap):
                ni = int(n)
                if ni == 97:
                    nmap[n] *= r97
                elif ni in ID_OVER_NATURES:
                    nmap[n] *= dr["over"]
                elif ni in ID_UNDER_NATURES:
                    nmap[n] *= dr["under"]
            _renorm(nmap)

    # 5. cause mixes per bucket (non-97 coarse ratios on the raw-code draws;
    # 97 causes are resampled from ID_97_CAUSE by the _draw_nature wrapper,
    # and 97-cause blanking is set to ID's 0.8710 by the _recorded_cause
    # wrapper).
    for b, cmap in d.get("cause_given_bucket", {}).items():
        ratios = ID_CAUSE_RATIO.get(b)
        if not ratios:
            continue
        for c in list(cmap):
            cmap[c] *= ratios.get(cause_bucket(int(c)), 1.0)
        _renorm(cmap)

    d.setdefault("_id", {})["conditioned"] = True
    return d


# ---------------------------------------------------------------------------
# ID-only wrappers (installed by generate_id, removed on return).
# ---------------------------------------------------------------------------
_INCOME_FIELDS = ("earned", "unearned")
_id_saved = {}


def _id_draw_nature(facts, bucket, dist, dir_w, rng):
    """Draw (nature, cause); on 97s resample the cause from ID's empirical
    97-cause mix (recorded basis, pre-blanking — ID blanks 87.1% of 97
    causes, far more than national's 65.4% pooled, so the national drawn
    97-cause mix is not a usable ID basis)."""
    nature, _cause = _id_saved["draw_nature"](facts, bucket, dist, dir_w, rng)
    if nature == 97:
        mix = ID_97_CAUSE.get(bucket)
        if mix:
            r = rng.random()
            cum = 0.0
            for code, p in mix.items():
                cum += p
                if r < cum:
                    return nature, int(code)
            return nature, int(next(iter(mix)))
    return nature, _cause


def _id_direction(field, base, new):
    """Benefit-direction implied by an agency-side amount change."""
    if field in _INCOME_FIELDS:
        return "over" if new < base else "under"
    return "over" if new > base else "under"


def _wrap_corruptor(orig):
    """Scale the realized agency-side amount delta by the ID dollar-size
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
            s = ID_S_OVER if d == "over" else ID_S_UNDER
            truth_corr[field] = round(truth_corr[field] * s, 2)
        else:
            new = agency[field]
            if new != base:
                d = _id_direction(field, base, new)
                s = ID_S_OVER if d == "over" else ID_S_UNDER
                agency[field] = round(base + s * (new - base), 2)
        return truth_corr, override
    return wrapped


def _id_recorded_cause(nature, cause, rng):
    # ID blanks cause on 87.1% of timing-97 variances (pooled; national's
    # FY2024-calibrated wrapper blanks 32%). Consume the rng draw the
    # national path takes so the rng stream stays aligned with a same-seed
    # national run.
    if nature == 97:
        if rng.random() < ID_CAUSE97_BLANK:
            return None
        return cause
    return cause


def _enable_id_wrappers():
    if _id_saved:
        return
    _id_saved["draw_nature"] = errors._draw_nature
    _id_saved["income"] = errors._corrupt_income
    _id_saved["deduction"] = errors._corrupt_deduction
    _id_saved["recorded_cause"] = errors._recorded_cause
    errors._draw_nature = _id_draw_nature
    errors._corrupt_income = _wrap_corruptor(errors._corrupt_income)
    errors._corrupt_deduction = _wrap_corruptor(errors._corrupt_deduction)
    errors._recorded_cause = _id_recorded_cause


def _disable_id_wrappers():
    if not _id_saved:
        return
    errors._draw_nature = _id_saved["draw_nature"]
    errors._corrupt_income = _id_saved["income"]
    errors._corrupt_deduction = _id_saved["deduction"]
    errors._recorded_cause = _id_saved["recorded_cause"]
    _id_saved.clear()


# ---------------------------------------------------------------------------
# ID-conditioned generation entry point.
# ---------------------------------------------------------------------------
def generate_id(n=1000, seed=0, dist="experiments/dist.json", out=None,
                max_attempts=12, persistent_buckets=True, tag_state=True):
    """Generate n ID-conditioned synthetic QC cases.

    Pipeline: load national dist -> adopted calibration (exp31, in-memory)
    -> ID offset ratios (this module, in-memory) -> generate with the
    mechanism patches + ID wrappers installed. All patches are removed
    before return; national generation is unaffected.

    Each case dict matches the national schema plus "state": "ID".
    Returns the output path (or the list of JSON lines when out is None).
    """
    from . import dollar_mech, household
    from .distutil import load_dist

    d = load_dist(dist)
    d = dollar_mech.adopted_dist(d)
    d = apply_id_offsets(d)

    mech_was_on = dollar_mech.is_enabled()
    dollar_mech.enable(under_scale=dollar_mech.EXP31_UNDER_SCALE)
    _enable_id_wrappers()
    try:
        rng = random.Random(seed)
        lines = []
        for _ in range(n):
            facts = household.sample_household(rng)
            case = dollar_mech.inject_case(
                facts, rng, d, max_attempts=max_attempts,
                persistent_buckets=persistent_buckets,
                p_unit=ID_P_UNIT)
            if tag_state:
                case["state"] = "ID"
            lines.append(json.dumps(case))
    finally:
        _disable_id_wrappers()
        if not mech_was_on:
            dollar_mech.disable()

    if out is None:
        return lines
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Generate ID-conditioned synthetic QC cases.")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dist", required=True, help="empirical distribution JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-attempts", type=int, default=12)
    ap.add_argument("--persistent-buckets",
                    action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--no-state-tag", action="store_true",
                    help="omit the 'state': 'ID' tag on cases")
    args = ap.parse_args()
    generate_id(n=args.n, seed=args.seed, dist=args.dist, out=args.out,
                max_attempts=args.max_attempts,
                persistent_buckets=args.persistent_buckets,
                tag_state=not args.no_state_tag)
    print(f"wrote {args.n} ID-conditioned cases -> {args.out}")


if __name__ == "__main__":
    main()
