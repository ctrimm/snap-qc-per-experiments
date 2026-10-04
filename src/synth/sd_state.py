"""SD-conditioned synthetic QC generation (SD1).

South Dakota offsets for the SNAP QC synthetic generator. Fit from pooled
FY2020-2024 QC public-use microdata (STATE='46', n=2,365; FYWGT-weighted;
microdata-implied rates, NOT FNS-published rates) — see
experiments/sd1_sd_generator.md and `python3 experiments/sd1_sd_generator.py
fit` for the provenance of every constant below.

Design: SD conditioning is a set of *relative offsets* applied to the
national (adopted-default) generator's dist, in-memory only. The national
path is untouched: importing this module installs nothing, and
`generate_sd()` restores every patch it installs. National (default)
generation behavior is byte-identical with or without this module.

What SD looks like vs national (pooled, FYWGT-weighted):
- errs much less often (case-weighted 24.8% vs 38.6%) with a balanced
  over share (49.7% vs 61.6% of errors are overissuances); the dollar rate
  is much lower (0.0239 vs 0.0859) and errors are much smaller
  (p50 $17 vs $28, p90 $70 vs $186, mean $34 vs $66; medO $18/$34,
  medU $16/$21; 88.6% of errors <=$56).
- error mix is earned-heavy (1.32x national share) and medical-heavy
  (1.41x); sua-light (0.67x).
- SD has far MORE timing-97 variances than national (97-share ratios
  1.8-3.1x per bucket).
- direction: SD skews UNDER on earned/unearned/shelter non-97 variances
  (over 0.85-0.89x, under 1.67-1.82x).
- SD blanks cause on 87.1% of timing-97 variances (national 65.4% pooled /
  32% in the generator's FY2024-calibrated wrapper) — SD records causes on
  97s far LESS often than national does; the recorded remainder is all
  cause 26 (no-fault).
- on substantive (non-97) variances SD codes almost everything no-fault:
  cause ratios explode (shelter 53x, sua 1218x, unearned 36x) because the
  national no-fault share is near zero — SD's coding practice is
  "timing/no-fault" for the substance of its errors.
- near-full|over 0.0024 vs 0.0574 national — whole-unit ineligibility is
  near-absent in SD, so p_unit is scaled down to 0.0005
  (P_UNIT_DEFAULT x 0.0024/0.0574).

API for SD2 (copy-paste):
    from src.synth.sd_state import generate_sd
    generate_sd(n=20000, seed=7, dist="experiments/dist.json",
               out="data/sd_synth.jsonl")

Shell:
    python3 -m src.synth.sd_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out data/sd_synth.jsonl

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
# SD empirical targets (pooled FY2020-2024 QC, STATE='46', FYWGT-weighted).
# National reference is pooled FY2020-2024 microdata-implied (same basis,
# excluding SD rows).
# ---------------------------------------------------------------------------
SD_OFFSETS = {
    "finding_mix": {"1": 0.7525, "2": 0.1229, "3": 0.1245},
    "case_err_rate": 0.2475,
    "dollar_rate": 0.0239,
    "p_err_earner": 0.4483,
    "p_err_no_earner": 0.1760,
    "p_over_given_err": 0.4967,
    "near_full_given_over": 0.0024,
    "dollar_p10": 2, "dollar_p25": 7, "dollar_p50": 17, "dollar_p90": 70,
    "dollar_mean": 34, "share_le56": 0.886,
    "med_over": 18, "med_under": 16,
    "cause97_blank": 0.8710,
    "national": {
        "finding_mix": {"1": 0.6136, "2": 0.2378, "3": 0.1486},
        "case_err_rate": 0.3864,
        "dollar_rate": 0.0859,
        "p_err_earner": 0.5667,
        "p_err_no_earner": 0.3215,
        "p_over_given_err": 0.6155,
        "near_full_given_over": 0.0574,
        "dollar_p10": 3, "dollar_p25": 9, "dollar_p50": 28, "dollar_p90": 186,
        "dollar_mean": 66, "share_le56": 0.702,
        "med_over": 34, "med_under": 21,
        "cause97_blank": 0.654,
    },
}

# SD/national ratios applied to the national dist (in-memory).
# Sparsity guards from the fit: bucket cells with SD unweighted n < 25,
# 97-share/97-coin cells with SD unweighted 97-n < 5, and direction cells
# with SD unweighted non-97 n < 25 keep the national value (ratio 1.0).
# it1 (pure empirical) values below; it2 realized-output calibration
# follows (see sd1_sd_generator.md).
SD_COIN_RATIO = {"earner": 0.791, "no_earner": 0.5474}

# Global coin calibration scalar (fit by line search against the marginal SD
# case-error rate; the per-stratum ratios above preserve the conditional
# structure). 1.0 = pure empirical ratios.
# it2: line search over {0.95, 1.0, 1.05, 1.1} after the recalibrations
# (see sd1_sd_generator.md). it1's pure-empirical 1.0 undershot the case rate
# at 0.2326 vs 0.2475 (SD's deep coin cuts + small-dollar errors materialize
# less often than the national-calibrated correction expects); like PA's
# 1.08 — which fought a materialization ceiling — SD needs an upward
# correction. 1.05 wins (case_err 0.2467 vs 0.2475 real).
SD_COIN_CAL = 1.05

# Per-bucket element ratios, SD / national.
# it2: one-step realized-output calibration (x real_SD_share / synth_share
# from the it1 validation run), mirroring PA1's it3 / NY1's it2. Pure
# empirical SD/national ratios were earned 1.3221, unearned 0.9886,
# shelter 0.9273, sua 0.6742, medical 1.4051; depcare/hhcomp/arithmetic
# keep the sparsity guard (1.0).
# it2: one-step realized-output calibration (x real_SD_share / synth_share
# from the it1 validation run, coin cal 1.05), mirroring PA1's it3 / NY1's
# it2. Pure empirical SD/national ratios were earned 1.3221, unearned 0.9886,
# shelter 0.9273, sua 0.6742, medical 1.4051; depcare/hhcomp/arithmetic keep
# the sparsity guard (1.0). The calibration corrects for the SD nature-mix
# shift changing per-bucket materialization (the national materialization
# correction in the draw was measured under the national nature mix).
# Medical's x=1.569 absorbs the it1 medical under-recording
# (real 0.0664 vs synth 0.0423).
SD_BUCKET_RATIO = {
    "earned": 1.357, "unearned": 1.0972, "shelter": 0.9229,
    "sua": 0.5856, "medical": 2.204, "depcare": 1.0,
    "hhcomp": 1.0, "arithmetic": 1.0,
}

# P(over | nature 97) ratios, SD / national, per bucket.
# it2: one-step realized-output calibration (x real_SD_P(over|97,b) /
# synth_P(over|97,b) from the it1 run). Pure empirical ratios were earned
# 0.8098, unearned 1.0303, shelter 0.8471, sua 0.5678, medical 0.6876,
# depcare 1.3417; hhcomp/arithmetic keep 1.0 (tiny-n guard).
SD_97_RATIO = {
    "earned": 0.8441, "unearned": 1.0669, "shelter": 1.0682,
    "sua": 0.781, "medical": 0.822, "depcare": 1.4043,
    "hhcomp": 1.0, "arithmetic": 1.0,
}

# P(nature=97 | bucket) ratios, SD / national, per bucket. SD runs far more
# timing variances than national on every bucket (depcare 3.14x passes the
# >=5 guard on n=?? — checked in the fit; arithmetic/hhcomp keep 1.0).
# it2: one-step realized-output calibration (x real_SD_P(97|b) /
# synth_P(97|b) from the it1 run). Pure empirical ratios were earned 1.7995,
# unearned 2.1874, shelter 1.772, sua 2.4609, medical 1.9982, depcare 3.1391;
# hhcomp/arithmetic keep the sparsity guard (1.0). it1 undershot the 97
# share on every major bucket (earned 0.609 vs 0.721, shelter 0.618 vs
# 0.875) — the generator's materialization on timing natures runs low under
# the SD mix, so the calibration pushes the draw margins up.
# it3: second one-step correction (x real_SD_P(97|b) / synth_P(97|b) from
# the it2b run). it2's x=1.05-1.42 under-corrected everywhere (realized
# earned 0.639 vs 0.721, shelter 0.683 vs 0.875) — the generator's timing-97
# materialization runs low under the SD mix, so the drawn margin only
# partially materializes. it3 multiplies the it2 values by the residual
# factors (earned 1.128, unearned 1.226, shelter 1.281, sua 1.052, medical
# 1.245, depcare 1.385).
SD_97_SHARE_RATIO = {
    "earned": 2.4, "unearned": 3.4373, "shelter": 3.216, "sua": 2.7135,
    "medical": 2.9024, "depcare": 5.5599, "hhcomp": 1.0,
    "arithmetic": 1.0,
}

# Direction balance among non-97 natures, SD / national, per bucket.
# Behavioral direction classes (which way the benefit moves when the nature
# is applied; matches the _corrupt_* else-branches). Note nature 39 is
# behaviorally over but sits in errors._dirclass "other" — the national
# dir_weight and these SD ratios compose multiplicatively, so the
# classification only needs to be consistent between fit and apply.
SD_OVER_NATURES = frozenset([35, 37, 38, 39, 53, 56, 7])
SD_UNDER_NATURES = frozenset([44, 52, 57, 6, 13])
# it2: one-step realized-output calibration on the non-97 slice
# (over x= real/synth P(over|non97,b); under x= real/synth P(under|non97,b)).
# Pure empirical ratios were earned 0.8921/1.6841, unearned 0.8491/1.8242,
# shelter 0.8502/1.6706. The it1 margins overshot directionality on
# earned/unearned (realized over 0.746/0.635 vs real 0.617/0.487) because
# materialization asymmetry eats part of the drawn margin — same pattern as
# NY1's it2. sua/medical/depcare/hhcomp/arithmetic keep 1.0 (sparsity guard).
SD_DIR_RATIO = {
    "earned": {"over": 0.738, "under": 2.5365},
    "unearned": {"over": 0.6509, "under": 2.5663},
    "shelter": {"over": 0.9704, "under": 1.4936},
    "sua": {"over": 1.0, "under": 1.0},
    "medical": {"over": 1.0, "under": 1.0},
    "depcare": {"over": 1.0, "under": 1.0},
    "hhcomp": {"over": 1.0, "under": 1.0},
    "arithmetic": {"over": 1.0, "under": 1.0},
}

# Cause mix ratios (coarse: client/agency/no_fault/other), SD / national,
# fit on NON-97 variances only — 97 causes are resampled from SD_97_CAUSE
# below. SD's substantive variances are agency-dominated (earned 0.841,
# shelter 0.955, sua 0.950) — the coding-practice story is "agency-caused",
# the mirror of NY's no-fault=0.0.
#
# it2b BASIS CORRECTION (cause-ratio blowup found 2026-10-03): the fit's
# pure non-97-vs-national-non-97 ratios (earned no_fault 0.0, unearned 36x,
# shelter 53x, sua 1218x) are honest against the national NON-97 empirical
# mix (no_fault ~0.001), but apply_sd_offsets multiplies them onto the
# dist's MIXED cause basis (no_fault 0.24-0.35, since dist cause_given_bucket
# includes the 97-draw basis). 0.31 x 53x blew no_fault to ~0.50 of the
# realized non-97 mix (real 0.015) and cause L1 to 0.55. The baked ratios
# below are rebased as SD_non97_mix / dist_mixed_basis — same ratio
# architecture, basis-aligned denominator. Multiplying each coarse group by
# its rebased ratio and renormalizing lands the SD empirical non-97 mix
# exactly. (NY never hit this: NY's no_fault ratio was 0.0, which kills the
# term on any basis.)
SD_CAUSE_RATIO = {
    "earned": {"client": 0.4552, "agency": 2.4766, "no_fault": 0.0, "other": 0.4454},
    "unearned": {"client": 1.2043, "agency": 1.515, "no_fault": 0.0794, "other": 0.5907},
    "shelter": {"client": 0.0399, "agency": 3.6216, "no_fault": 0.0884, "other": 0.0},
    "sua": {"client": 0.0, "agency": 1.8596, "no_fault": 0.3199, "other": 0.0},
    "medical": {"client": 3.6956, "agency": 1.2433, "no_fault": 0.0, "other": 0.6255},
    "depcare": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
    "hhcomp": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
    "arithmetic": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
}

# SD empirical cause mix ON nature-97 variances, per bucket (raw cause codes).
# SD blanks 87.1% of 97 causes; the recorded remainder is entirely cause 26
# (no-fault) — the pooled fallback, since every per-bucket 97-cause cell is
# the same degenerate mix.
SD_97_CAUSE = {
    "earned": {"26": 1.0},
    "unearned": {"26": 1.0},
    "shelter": {"26": 1.0},
    "sua": {"26": 1.0},
    "medical": {"26": 1.0},
    "depcare": {"26": 1.0},
    "hhcomp": {"26": 1.0},
    "arithmetic": {"26": 1.0},
}

# Dollar-size offsets: SD median error / national median error, per finding
# direction (relative-offset semantics — the generator's national level bias
# is orthogonal and owned by exp31's calibration). Applied as a multiplier
# on the agency-side amount delta inside the corruptors, so the
# facts->benefit math stays mechanics-consistent. SD's errors are much
# smaller than national (p90 $70 vs $186); the uniform scale captures the
# level shift, not the shape.
SD_S_OVER = 0.5294
SD_S_UNDER = 0.7619

# SD blanks cause on 87.1% of timing-97 variances (measured pooled).
SD_CAUSE97_BLANK = 0.8710

# Whole-unit ineligibility (mechanism 2): SD's near-full-benefit over share
# (0.0024) is ~1/24 of national (0.0574) — whole-unit errors are
# near-absent in SD. p_unit scales by the near-full|over ratio:
# 0.0125 * 0.0024/0.0574 ~= 0.00052 -> 0.0005.
SD_P_UNIT = 0.0005

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


def apply_sd_offsets(dist):
    """Return a dist copy with the SD offset ratios applied (in-memory only).

    Takes the adopted-calibration dist (dollar_mech.adopted_dist output) and
    multiplies: injection coins, per-bucket 97-resolution coins, bucket mixes
    (all stratum keys), earner-conditional nature mixes (97-share and
    direction-balance margins), and per-bucket non-97 cause mixes — each by
    its SD/national ratio, renormalized. The input dist is never mutated.
    """
    d = copy.deepcopy(dist)

    # 1. injection coins. The adopted coins are attrition-corrected to land
    # the national empirical P(error | stratum); scaling by the SD/national
    # conditional ratio assumes materialization (a mechanics property) is
    # state-independent. SD's whole-unit mass is near-zero (SD_P_UNIT=0.0005 vs 0.0125 national);
    # the adopted unit-bucket correction still uses the national P_UNIT_DEFAULT,
    # leaving a tiny over-correction of the earned draw weight that the
    # it2 bucket recalibration absorbs.
    inj = d.get("injection_rate", {})
    for key in ("persistent", "earner", "no_earner"):
        sub = inj.get(key)
        if isinstance(sub, dict):
            for s, r in SD_COIN_RATIO.items():
                if s in sub:
                    sub[s] = min(0.99, sub[s] * r * SD_COIN_CAL)

    # 2. timing-97 resolution coins per bucket (direction margin).
    coins = inj.get("p_over_97_resolve", {})
    for b, r in SD_97_RATIO.items():
        if b in coins:
            coins[b] = min(0.95, max(0.05, coins[b] * r))

    # 3. element-bucket mixes (marginal ratios applied to every stratum key;
    # the recorded marginal then tracks SD regardless of stratum composition).
    for key in _BUCKET_MIX_KEYS:
        mix = d.get(key)
        if isinstance(mix, dict):
            for b, r in SD_BUCKET_RATIO.items():
                if b in mix:
                    mix[b] *= r
            _renorm(mix)

    # 4. nature mixes per bucket: 97-share margin and direction-balance
    # margin (marginal ratios on the earner-conditional mixes the injector
    # draws from).
    for key in _NATURE_MIX_KEYS:
        for b, nmap in d.get(key, {}).items():
            r97 = SD_97_SHARE_RATIO.get(b, 1.0)
            dr = SD_DIR_RATIO.get(b, {"over": 1.0, "under": 1.0})
            for n in list(nmap):
                ni = int(n)
                if ni == 97:
                    nmap[n] *= r97
                elif ni in SD_OVER_NATURES:
                    nmap[n] *= dr["over"]
                elif ni in SD_UNDER_NATURES:
                    nmap[n] *= dr["under"]
            _renorm(nmap)

    # 5. cause mixes per bucket (non-97 coarse ratios on the raw-code draws;
    # 97 causes are resampled from SD_97_CAUSE by the _draw_nature wrapper,
    # and 97-cause blanking is set to SD's 0.8710 by the _recorded_cause
    # wrapper).
    for b, cmap in d.get("cause_given_bucket", {}).items():
        ratios = SD_CAUSE_RATIO.get(b)
        if not ratios:
            continue
        for c in list(cmap):
            cmap[c] *= ratios.get(cause_bucket(int(c)), 1.0)
        _renorm(cmap)

    d.setdefault("_sd", {})["conditioned"] = True
    return d


# ---------------------------------------------------------------------------
# SD-only wrappers (installed by generate_sd, removed on return).
# ---------------------------------------------------------------------------
_INCOME_FIELDS = ("earned", "unearned")
_sd_saved = {}


def _sd_draw_nature(facts, bucket, dist, dir_w, rng):
    """Draw (nature, cause); on 97s resample the cause from SD's empirical
    97-cause mix (recorded basis, pre-blanking — SD blanks 87.1% of 97
    causes, far more than national's 65.4% pooled, so the national drawn
    97-cause mix is not a usable SD basis)."""
    nature, _cause = _sd_saved["draw_nature"](facts, bucket, dist, dir_w, rng)
    if nature == 97:
        mix = SD_97_CAUSE.get(bucket)
        if mix:
            r = rng.random()
            cum = 0.0
            for code, p in mix.items():
                cum += p
                if r < cum:
                    return nature, int(code)
            return nature, int(next(iter(mix)))
    return nature, _cause


def _sd_direction(field, base, new):
    """Benefit-direction implied by an agency-side amount change."""
    if field in _INCOME_FIELDS:
        return "over" if new < base else "under"
    return "over" if new > base else "under"


def _wrap_corruptor(orig):
    """Scale the realized agency-side amount delta by the SD dollar-size
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
            s = SD_S_OVER if d == "over" else SD_S_UNDER
            truth_corr[field] = round(truth_corr[field] * s, 2)
        else:
            new = agency[field]
            if new != base:
                d = _sd_direction(field, base, new)
                s = SD_S_OVER if d == "over" else SD_S_UNDER
                agency[field] = round(base + s * (new - base), 2)
        return truth_corr, override
    return wrapped


def _sd_recorded_cause(nature, cause, rng):
    # SD blanks cause on 87.1% of timing-97 variances (pooled; national's
    # FY2024-calibrated wrapper blanks 32%). Consume the rng draw the
    # national path takes so the rng stream stays aligned with a same-seed
    # national run.
    if nature == 97:
        if rng.random() < SD_CAUSE97_BLANK:
            return None
        return cause
    return cause


def _enable_sd_wrappers():
    if _sd_saved:
        return
    _sd_saved["draw_nature"] = errors._draw_nature
    _sd_saved["income"] = errors._corrupt_income
    _sd_saved["deduction"] = errors._corrupt_deduction
    _sd_saved["recorded_cause"] = errors._recorded_cause
    errors._draw_nature = _sd_draw_nature
    errors._corrupt_income = _wrap_corruptor(errors._corrupt_income)
    errors._corrupt_deduction = _wrap_corruptor(errors._corrupt_deduction)
    errors._recorded_cause = _sd_recorded_cause


def _disable_sd_wrappers():
    if not _sd_saved:
        return
    errors._draw_nature = _sd_saved["draw_nature"]
    errors._corrupt_income = _sd_saved["income"]
    errors._corrupt_deduction = _sd_saved["deduction"]
    errors._recorded_cause = _sd_saved["recorded_cause"]
    _sd_saved.clear()


# ---------------------------------------------------------------------------
# SD-conditioned generation entry point.
# ---------------------------------------------------------------------------
def generate_sd(n=1000, seed=0, dist="experiments/dist.json", out=None,
                max_attempts=12, persistent_buckets=True, tag_state=True):
    """Generate n SD-conditioned synthetic QC cases.

    Pipeline: load national dist -> adopted calibration (exp31, in-memory)
    -> SD offset ratios (this module, in-memory) -> generate with the
    mechanism patches + SD wrappers installed. All patches are removed
    before return; national generation is unaffected.

    Each case dict matches the national schema plus "state": "SD".
    Returns the output path (or the list of JSON lines when out is None).
    """
    from . import dollar_mech, household
    from .distutil import load_dist

    d = load_dist(dist)
    d = dollar_mech.adopted_dist(d)
    d = apply_sd_offsets(d)

    mech_was_on = dollar_mech.is_enabled()
    dollar_mech.enable(under_scale=dollar_mech.EXP31_UNDER_SCALE)
    _enable_sd_wrappers()
    try:
        rng = random.Random(seed)
        lines = []
        for _ in range(n):
            facts = household.sample_household(rng)
            case = dollar_mech.inject_case(
                facts, rng, d, max_attempts=max_attempts,
                persistent_buckets=persistent_buckets,
                p_unit=SD_P_UNIT)
            if tag_state:
                case["state"] = "SD"
            lines.append(json.dumps(case))
    finally:
        _disable_sd_wrappers()
        if not mech_was_on:
            dollar_mech.disable()

    if out is None:
        return lines
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Generate SD-conditioned synthetic QC cases.")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dist", required=True, help="empirical distribution JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-attempts", type=int, default=12)
    ap.add_argument("--persistent-buckets",
                    action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--no-state-tag", action="store_true",
                    help="omit the 'state': 'SD' tag on cases")
    args = ap.parse_args()
    generate_sd(n=args.n, seed=args.seed, dist=args.dist, out=args.out,
                max_attempts=args.max_attempts,
                persistent_buckets=args.persistent_buckets,
                tag_state=not args.no_state_tag)
    print(f"wrote {args.n} SD-conditioned cases -> {args.out}")


if __name__ == "__main__":
    main()
