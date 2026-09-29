"""NY-conditioned synthetic QC generation (NY1).

New York offsets for the SNAP QC synthetic generator. Fit from pooled
FY2020-2024 QC public-use microdata (STATE='36', n=3,257; FYWGT-weighted;
microdata-implied rates, NOT FNS-published rates) — see
experiments/ny1_ny_generator.md and `python3 experiments/ny1_ny_generator.py
fit` for the provenance of every constant below.

Design: NY conditioning is a set of *relative offsets* applied to the
national (adopted-default) generator's dist, in-memory only. The national
path is untouched: importing this module installs nothing, and
`generate_ny()` restores every patch it installs. National (default)
generation behavior is byte-identical with or without this module.

What NY looks like vs national (pooled, FYWGT-weighted):
- errs less often (case-weighted 36.6% vs 38.8%) with a lower over share
  (57.5% vs 61.8% of errors are overissuances); dollar rate matches
  (0.0854 vs 0.0859) but the error tail is heavier (p90 $201 vs $183,
  mean $72 vs $65) while medians match ($29/$28, medO $35/$34, medU $21/$21).
- error mix is medical-heavy (1.75x national share) and hhcomp-heavy
  (1.58x), shelter-light (0.81x).
- NY has far MORE timing-97 variances than national (97-share ratios
  1.2-2.6x per bucket; 2.32x on sua).
- direction: shelter variances skew under (over 0.57x, under 1.59x);
  sua skews over (over 1.55x, under 0.49x).
- NY blanks cause on 21.9% of timing-97 variances (national 69.7% pooled /
  32% in the generator's FY2024-calibrated wrapper) — NY records causes on
  97s far more often than national does.
- NY never uses cause 26 (no-fault) on substantive (non-97) variances
  (0.000 all buckets); medical non-97 causes are all agency-caused.
- near-full|over 0.0657 vs 0.0568 national — p_unit stays at the national
  default.

API for NY2 (copy-paste):
    from src.synth.ny_state import generate_ny
    generate_ny(n=20000, seed=7, dist="experiments/dist.json",
               out="data/ny_synth.jsonl")

Shell:
    python3 -m src.synth.ny_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out data/ny_synth.jsonl

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
# NY empirical targets (pooled FY2020-2024 QC, STATE='36', FYWGT-weighted).
# National reference is pooled FY2020-2024 microdata-implied (same basis).
# ---------------------------------------------------------------------------
NY_OFFSETS = {
    "finding_mix": {"1": 0.6345, "2": 0.2101, "3": 0.1553},
    "case_err_rate": 0.3655,
    "dollar_rate": 0.0854,
    "p_err_earner": 0.5858,
    "p_err_no_earner": 0.3075,
    "p_over_given_err": 0.5750,
    "near_full_given_over": 0.0657,
    "dollar_p10": 3, "dollar_p25": 10, "dollar_p50": 29, "dollar_p90": 201,
    "dollar_mean": 72, "share_le56": 0.692,
    "med_over": 35, "med_under": 21,
    "cause97_blank": 0.2189,
    "national": {
        "finding_mix": {"1": 0.6122, "2": 0.2398, "3": 0.1480},
        "case_err_rate": 0.3878,
        "dollar_rate": 0.0859,
        "p_err_earner": 0.5653,
        "p_err_no_earner": 0.3225,
        "p_over_given_err": 0.6184,
        "near_full_given_over": 0.0568,
        "dollar_p10": 3, "dollar_p25": 9, "dollar_p50": 28, "dollar_p90": 183,
        "dollar_mean": 65, "share_le56": 0.703,
        "med_over": 34, "med_under": 21,
        "cause97_blank": 0.697,
    },
}

# NY/national ratios applied to the national dist (in-memory).
# Sparsity guards from the fit: bucket cells with NY unweighted n < 25,
# 97-share/97-coin cells with NY unweighted 97-n < 5, and direction cells
# with NY unweighted non-97 n < 25 keep the national value (ratio 1.0).
NY_COIN_RATIO = {"earner": 1.0362, "no_earner": 0.9535}

# Global coin calibration scalar (fit by line search against the marginal NY
# case-error rate; the per-stratum ratios above preserve the conditional
# structure). 1.0 = pure empirical ratios.
# it2: line search over {0.90, 0.93, 0.96, 1.0} (see ny1_ny_generator.md).
# 0.96 wins: finding L1 0.0202, case_err 0.3651 vs 0.3655 real. (The it1
# pure-empirical 1.0 overshot the case rate at 0.3889 once the bucket and
# direction recalibrations raised materialization; unlike PA's 1.08 — which
# fought a materialization ceiling — NY needs a small downward correction.)
NY_COIN_CAL = 0.96

# it2: one-step realized-output calibration (x real_NY_share / synth_share
# from the it1 validation run), mirroring PA1's it3. Pure empirical
# NY/national ratios were earned 1.0080, unearned 1.0875, shelter 0.8105,
# sua 1.2056, medical 1.7477, hhcomp 1.5846; the calibration corrects for
# the NY nature-mix shift changing per-bucket materialization (the national
# materialization correction in the draw was measured under the national
# nature mix). depcare/arithmetic keep the sparsity guard (1.0).
NY_BUCKET_RATIO = {
    "earned": 1.0133, "unearned": 1.1821, "shelter": 0.8290,
    "sua": 1.0549, "medical": 2.0411, "depcare": 1.0,
    "hhcomp": 1.3287, "arithmetic": 1.0,
}

# P(over | nature 97) ratios, NY / national, per bucket.
# it2: one-step realized-output calibration (x real_NY_P(over|97,b) /
# synth_P(over|97,b) from the it1 run). Pure empirical ratios were earned
# 1.1465, unearned 0.9690, shelter 0.8955, sua 1.0589, medical 0.7002,
# hhcomp 1.2393; depcare/arithmetic keep the it1 value (tiny-n guard).
NY_97_RATIO = {
    "earned": 1.1465, "unearned": 0.9403, "shelter": 0.9577,
    "sua": 1.2199, "medical": 0.7776, "depcare": 1.1982,
    "hhcomp": 0.8052, "arithmetic": 0.2807,
}

# P(nature=97 | bucket) ratios, NY / national, per bucket. NY runs far more
# timing variances than national on every bucket (arithmetic 7.21x is
# tiny-n: 9 unweighted 97s — kept by the >=5 guard, arithmetic is rare).
NY_97_SHARE_RATIO = {
    "earned": 1.1575, "unearned": 2.0169, "shelter": 1.7781, "sua": 2.3192,
    "medical": 2.0738, "depcare": 1.4163, "hhcomp": 2.6164,
    "arithmetic": 7.2122,
}

# Direction balance among non-97 natures, NY / national, per bucket.
# Behavioral direction classes (which way the benefit moves when the nature
# is applied; matches the _corrupt_* else-branches). Note nature 39 is
# behaviorally over but sits in errors._dirclass "other" — the national
# dir_weight and these NY ratios compose multiplicatively, so the
# classification only needs to be consistent between fit and apply.
NY_OVER_NATURES = frozenset([35, 37, 38, 39, 53, 56, 7])
NY_UNDER_NATURES = frozenset([44, 52, 57, 6, 13])
NY_DIR_RATIO = {
    # it2: one-step realized-output calibration on the non-97 slice
    # (over x= real/synth P(over|non97,b); under x= real/synth P(under|non97,b)).
    # Pure empirical ratios were earned 1.2094/0.9248, unearned 1.1562/0.9136,
    # shelter 0.5744/1.5910, sua 1.5532/0.4949, medical 1.0901/0.7887,
    # hhcomp 0.8716/0.9634. The it1 margins overshot directionality on
    # earned/unearned and undershot on shelter/medical/hhcomp (materialization
    # asymmetry eats part of the drawn margin, so this under-corrects safely).
    "earned": {"over": 0.9820, "under": 2.5624},
    "unearned": {"over": 1.0473, "under": 1.2494},
    "shelter": {"over": 0.8148, "under": 1.2228},
    "sua": {"over": 1.5016, "under": 0.5539},
    "medical": {"over": 1.7522, "under": 0.3790},
    "depcare": {"over": 1.0, "under": 1.0},
    "hhcomp": {"over": 1.6152, "under": 0.6967},
    "arithmetic": {"over": 1.0, "under": 1.0},
}

# Cause mix ratios (coarse: client/agency/no_fault/other), NY / national,
# fit on NON-97 variances only — 97 causes are resampled from NY_97_CAUSE
# below, because the national 97-cause draw is distorted by national's
# much higher 97-cause blanking (NY blanks 0.219 vs 0.32 national FY2024 /
# 0.70 pooled). Note no_fault = 0.0: NY never uses cause 26 on substantive
# variances; medical non-97 causes are all agency-caused (client/other 0.0).
NY_CAUSE_RATIO = {
    "earned": {"client": 0.8151, "agency": 1.2073, "no_fault": 0.0, "other": 0.6112},
    "unearned": {"client": 1.2683, "agency": 1.0212, "no_fault": 0.0, "other": 0.4979},
    "shelter": {"client": 0.3908, "agency": 1.6062, "no_fault": 0.0, "other": 2.3552},
    "sua": {"client": 0.0413, "agency": 1.6407, "no_fault": 0.0, "other": 0.4750},
    "medical": {"client": 0.0, "agency": 1.2429, "no_fault": 0.0, "other": 0.0},
    "depcare": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
    "hhcomp": {"client": 0.7001, "agency": 1.4516, "no_fault": 0.0, "other": 0.3295},
    "arithmetic": {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0},
}

# NY empirical cause mix ON nature-97 variances, per bucket (raw cause codes).
# NY blanks 21.9% of 97 causes; the recorded remainder below is what NY
# reviewers actually record (dominated by cause 1/agency and 12, not 99 —
# unlike PA's 99-heavy 97 mix). Buckets with NY unweighted 97-n < 5 would
# fall back to the pooled NY 97-cause mix; all buckets here pass the guard.
NY_97_CAUSE = {
    "earned": {"1": 0.413, "2": 0.0333, "3": 0.0178, "10": 0.0408,
               "12": 0.2114, "14": 0.0167, "16": 0.0308, "20": 0.0199,
               "22": 0.0067, "26": 0.1387, "99": 0.071},
    "unearned": {"1": 0.1937, "7": 0.0061, "8": 0.0046, "10": 0.0624,
                 "12": 0.1229, "14": 0.0135, "15": 0.1421, "16": 0.0851,
                 "18": 0.0317, "19": 0.0283, "20": 0.0094, "22": 0.0408,
                 "26": 0.141, "99": 0.1184},
    "shelter": {"1": 0.4287, "2": 0.0486, "4": 0.0164, "10": 0.0778,
                "12": 0.1036, "14": 0.0126, "15": 0.011, "16": 0.0383,
                "19": 0.0079, "22": 0.0144, "26": 0.1866, "99": 0.0542},
    "sua": {"1": 0.1309, "2": 0.0148, "10": 0.1783, "12": 0.3459,
            "14": 0.0203, "15": 0.0182, "16": 0.1042, "17": 0.0201,
            "26": 0.0476, "99": 0.1199},
    "medical": {"1": 0.0912, "2": 0.0349, "10": 0.0138, "12": 0.1191,
                "14": 0.0152, "15": 0.3743, "16": 0.1715, "20": 0.0181,
                "26": 0.0632, "99": 0.0988},
    "depcare": {"1": 0.3648, "12": 0.1018, "16": 0.3441, "99": 0.1893},
    "hhcomp": {"1": 0.0816, "2": 0.1055, "3": 0.4179, "10": 0.1002,
               "12": 0.2947},
    "arithmetic": {"10": 0.0995, "18": 0.1034, "19": 0.5472, "20": 0.0588,
                   "22": 0.0961, "26": 0.095},
}

# Dollar-size offsets: NY median error / national median error, per finding
# direction (relative-offset semantics — the generator's national level bias
# is orthogonal and owned by exp31's calibration). Applied as a multiplier
# on the agency-side amount delta inside the corruptors, so the
# facts->benefit math stays mechanics-consistent. NY's heavier error tail
# (p90 $201 vs $183) cannot be matched by this uniform scale — it is a
# documented structural limitation (see ny1_ny_generator.md).
NY_S_OVER = 1.0294
NY_S_UNDER = 1.0

# NY blanks cause on 21.9% of timing-97 variances (measured pooled).
NY_CAUSE97_BLANK = 0.2189

# Whole-unit ineligibility (mechanism 2): NY's near-full-benefit over share
# (0.0657) is close to national (0.0568), so p_unit stays at the default.
NY_P_UNIT = None  # None = keep dollar_mech.P_UNIT_DEFAULT

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


def apply_ny_offsets(dist):
    """Return a dist copy with the NY offset ratios applied (in-memory only).

    Takes the adopted-calibration dist (dollar_mech.adopted_dist output) and
    multiplies: injection coins, per-bucket 97-resolution coins, bucket mixes
    (all stratum keys), earner-conditional nature mixes (97-share and
    direction-balance margins), and per-bucket non-97 cause mixes — each by
    its NY/national ratio, renormalized. The input dist is never mutated.
    """
    d = copy.deepcopy(dist)

    # 1. injection coins. The adopted coins are attrition-corrected to land
    # the national empirical P(error | stratum); scaling by the NY/national
    # conditional ratio assumes materialization (a mechanics property) is
    # state-independent. The whole-unit mass is unchanged for NY, so no
    # re-derivation of the unit-bucket correction is needed.
    inj = d.get("injection_rate", {})
    for key in ("persistent", "earner", "no_earner"):
        sub = inj.get(key)
        if isinstance(sub, dict):
            for s, r in NY_COIN_RATIO.items():
                if s in sub:
                    sub[s] = min(0.99, sub[s] * r * NY_COIN_CAL)

    # 2. timing-97 resolution coins per bucket (direction margin).
    coins = inj.get("p_over_97_resolve", {})
    for b, r in NY_97_RATIO.items():
        if b in coins:
            coins[b] = min(0.95, max(0.05, coins[b] * r))

    # 3. element-bucket mixes (marginal ratios applied to every stratum key;
    # the recorded marginal then tracks NY regardless of stratum composition).
    for key in _BUCKET_MIX_KEYS:
        mix = d.get(key)
        if isinstance(mix, dict):
            for b, r in NY_BUCKET_RATIO.items():
                if b in mix:
                    mix[b] *= r
            _renorm(mix)

    # 4. nature mixes per bucket: 97-share margin and direction-balance
    # margin (marginal ratios on the earner-conditional mixes the injector
    # draws from).
    for key in _NATURE_MIX_KEYS:
        for b, nmap in d.get(key, {}).items():
            r97 = NY_97_SHARE_RATIO.get(b, 1.0)
            dr = NY_DIR_RATIO.get(b, {"over": 1.0, "under": 1.0})
            for n in list(nmap):
                ni = int(n)
                if ni == 97:
                    nmap[n] *= r97
                elif ni in NY_OVER_NATURES:
                    nmap[n] *= dr["over"]
                elif ni in NY_UNDER_NATURES:
                    nmap[n] *= dr["under"]
            _renorm(nmap)

    # 5. cause mixes per bucket (non-97 coarse ratios on the raw-code draws;
    # 97 causes are resampled from NY_97_CAUSE by the _draw_nature wrapper,
    # and 97-cause blanking is set to NY's 0.2189 by the _recorded_cause
    # wrapper).
    for b, cmap in d.get("cause_given_bucket", {}).items():
        ratios = NY_CAUSE_RATIO.get(b)
        if not ratios:
            continue
        for c in list(cmap):
            cmap[c] *= ratios.get(cause_bucket(int(c)), 1.0)
        _renorm(cmap)

    d.setdefault("_ny", {})["conditioned"] = True
    return d


# ---------------------------------------------------------------------------
# NY-only wrappers (installed by generate_ny, removed on return).
# ---------------------------------------------------------------------------
_INCOME_FIELDS = ("earned", "unearned")
_ny_saved = {}


def _ny_draw_nature(facts, bucket, dist, dir_w, rng):
    """Draw (nature, cause); on 97s resample the cause from NY's empirical
    97-cause mix (recorded basis, pre-blanking — NY blanks 21.9% of 97
    causes, far fewer than national's 69.7% pooled, so the national drawn
    97-cause mix is not a usable NY basis)."""
    nature, _cause = _ny_saved["draw_nature"](facts, bucket, dist, dir_w, rng)
    if nature == 97:
        mix = NY_97_CAUSE.get(bucket)
        if mix:
            r = rng.random()
            cum = 0.0
            for code, p in mix.items():
                cum += p
                if r < cum:
                    return nature, int(code)
            return nature, int(next(iter(mix)))
    return nature, _cause


def _ny_direction(field, base, new):
    """Benefit-direction implied by an agency-side amount change."""
    if field in _INCOME_FIELDS:
        return "over" if new < base else "under"
    return "over" if new > base else "under"


def _wrap_corruptor(orig):
    """Scale the realized agency-side amount delta by the NY dollar-size
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
            s = NY_S_OVER if d == "over" else NY_S_UNDER
            truth_corr[field] = round(truth_corr[field] * s, 2)
        else:
            new = agency[field]
            if new != base:
                d = _ny_direction(field, base, new)
                s = NY_S_OVER if d == "over" else NY_S_UNDER
                agency[field] = round(base + s * (new - base), 2)
        return truth_corr, override
    return wrapped


def _ny_recorded_cause(nature, cause, rng):
    # NY blanks cause on 21.9% of timing-97 variances (pooled; national's
    # FY2024-calibrated wrapper blanks 32%). Consume the rng draw the
    # national path takes so the rng stream stays aligned with a same-seed
    # national run.
    if nature == 97:
        if rng.random() < NY_CAUSE97_BLANK:
            return None
        return cause
    return cause


def _enable_ny_wrappers():
    if _ny_saved:
        return
    _ny_saved["draw_nature"] = errors._draw_nature
    _ny_saved["income"] = errors._corrupt_income
    _ny_saved["deduction"] = errors._corrupt_deduction
    _ny_saved["recorded_cause"] = errors._recorded_cause
    errors._draw_nature = _ny_draw_nature
    errors._corrupt_income = _wrap_corruptor(errors._corrupt_income)
    errors._corrupt_deduction = _wrap_corruptor(errors._corrupt_deduction)
    errors._recorded_cause = _ny_recorded_cause


def _disable_ny_wrappers():
    if not _ny_saved:
        return
    errors._draw_nature = _ny_saved["draw_nature"]
    errors._corrupt_income = _ny_saved["income"]
    errors._corrupt_deduction = _ny_saved["deduction"]
    errors._recorded_cause = _ny_saved["recorded_cause"]
    _ny_saved.clear()


# ---------------------------------------------------------------------------
# NY-conditioned generation entry point.
# ---------------------------------------------------------------------------
def generate_ny(n=1000, seed=0, dist="experiments/dist.json", out=None,
                max_attempts=12, persistent_buckets=True, tag_state=True):
    """Generate n NY-conditioned synthetic QC cases.

    Pipeline: load national dist -> adopted calibration (exp31, in-memory)
    -> NY offset ratios (this module, in-memory) -> generate with the
    mechanism patches + NY wrappers installed. All patches are removed
    before return; national generation is unaffected.

    Each case dict matches the national schema plus "state": "NY".
    Returns the output path (or the list of JSON lines when out is None).
    """
    from . import dollar_mech, household
    from .distutil import load_dist

    d = load_dist(dist)
    d = dollar_mech.adopted_dist(d)
    d = apply_ny_offsets(d)

    mech_was_on = dollar_mech.is_enabled()
    dollar_mech.enable(under_scale=dollar_mech.EXP31_UNDER_SCALE)
    _enable_ny_wrappers()
    try:
        rng = random.Random(seed)
        lines = []
        for _ in range(n):
            facts = household.sample_household(rng)
            case = dollar_mech.inject_case(
                facts, rng, d, max_attempts=max_attempts,
                persistent_buckets=persistent_buckets)
            if tag_state:
                case["state"] = "NY"
            lines.append(json.dumps(case))
    finally:
        _disable_ny_wrappers()
        if not mech_was_on:
            dollar_mech.disable()

    if out is None:
        return lines
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Generate NY-conditioned synthetic QC cases.")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dist", required=True, help="empirical distribution JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-attempts", type=int, default=12)
    ap.add_argument("--persistent-buckets",
                    action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--no-state-tag", action="store_true",
                    help="omit the 'state': 'NY' tag on cases")
    args = ap.parse_args()
    generate_ny(n=args.n, seed=args.seed, dist=args.dist, out=args.out,
                max_attempts=args.max_attempts,
                persistent_buckets=args.persistent_buckets,
                tag_state=not args.no_state_tag)
    print(f"wrote {args.n} NY-conditioned cases -> {args.out}")


if __name__ == "__main__":
    main()
