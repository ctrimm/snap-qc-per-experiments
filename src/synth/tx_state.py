"""TX-conditioned synthetic QC generation (TX1).

Texas offsets for the SNAP QC synthetic generator. Fit from pooled
FY2020-2024 QC public-use microdata (STATE='48', n=3,457; FYWGT-weighted;
microdata-implied rates, NOT FNS-published rates) — see
experiments/tx1_tx_generator.md and `python3 experiments/tx1_tx_generator.py
fit` for the provenance of every constant below.

Design: TX conditioning is a set of *relative offsets* applied to the
national (adopted-default) generator's dist, in-memory only. The national
path is untouched: importing this module installs nothing, and
`generate_tx()` restores every patch it installs. National (default)
generation behavior is byte-identical with or without this module.

What TX looks like vs national (pooled, FYWGT-weighted):
- errs MORE often (case-weighted 43.4% vs 38.3%) with a much lower over
  share (51.4% vs 62.4% of errors are overissuances — TX tilts toward
  underissuances); the dollar rate is lower (0.0740 vs 0.0869) and the
  error tail is lighter (p90 $149 vs $188, mean $58 vs $66) while medians
  are close ($27/$28, medO $30/$34, medU $25/$20).
- error mix is depcare-heavy (1.59x national share), sua-heavy (1.22x),
  earned-heavy (1.15x); medical-light (0.62x), shelter-light (0.88x).
- TX has FEWER timing-97 variances than national on most buckets
  (97-share ratios 0.48-1.04x; sua 0.48x, shelter 0.56x) — the opposite of
  NY's timing-heavy profile.
- direction: errors skew under across buckets (over 0.29-0.73x,
  under up to 1.91x on medical).
- TX blanks cause on 79.95% of timing-97 variances (national 64.4% pooled)
  — and every recorded 97 cause is code 26 (no-fault), verified 180/180.
- TX essentially never uses cause 26 (no-fault) on substantive (non-97)
  variances (0.0 on 7 of 8 buckets); non-97 causes skew agency-side.
- near-full|over 0.0225 vs 0.0599 national — p_unit stays at the national
  default (documented structural residual).

API for TX2 (copy-paste):
    from src.synth.tx_state import generate_tx
    generate_tx(n=20000, seed=7, dist="experiments/dist.json",
               out="data/tx_synth.jsonl")

Shell:
    python3 -m src.synth.tx_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out data/tx_synth.jsonl

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
# TX empirical targets (pooled FY2020-2024 QC, STATE='48', FYWGT-weighted).
# National reference is pooled FY2020-2024 microdata-implied (same basis).
# ---------------------------------------------------------------------------
TX_OFFSETS = {
    "finding_mix": {"1": 0.5656, "2": 0.2234, "3": 0.2109},
    "case_err_rate": 0.4344,
    "dollar_rate": 0.0740,
    "p_err_earner": 0.6279,
    "p_err_no_earner": 0.3363,
    "p_over_given_err": 0.5144,
    "near_full_given_over": 0.0225,
    "dollar_p10": 3, "dollar_p25": 10, "dollar_p50": 27, "dollar_p90": 149,
    "dollar_mean": 58, "share_le56": 0.743,
    "med_over": 30, "med_under": 25,
    "cause97_blank": 0.7995,
    "national": {
        "finding_mix": {"1": 0.6175, "2": 0.2387, "3": 0.1438},
        "case_err_rate": 0.3825,
        "dollar_rate": 0.0869,
        "p_err_earner": 0.5605,
        "p_err_no_earner": 0.3202,
        "p_over_given_err": 0.6241,
        "near_full_given_over": 0.0599,
        "dollar_p10": 3, "dollar_p25": 9, "dollar_p50": 28, "dollar_p90": 188,
        "dollar_mean": 66, "share_le56": 0.699,
        "med_over": 34, "med_under": 20,
        "cause97_blank": 0.644,
    },
}

# TX/national ratios applied to the national dist (in-memory).
# Sparsity guards from the fit: bucket cells with TX unweighted n < 25,
# 97-share/97-coin cells with TX unweighted 97-n < 5, and direction cells
# with TX unweighted non-97 n < 25 keep the national value (ratio 1.0).
TX_COIN_RATIO = {"earner": 1.1204, "no_earner": 1.0501}

# Global coin calibration scalar (fit by line search against the marginal TX
# case-error rate; the per-stratum ratios above preserve the conditional
# structure). 1.0 = pure empirical ratios.
# it2: line search over {0.96, 0.98, 1.0, 1.02} on the it2 component set,
# then {0.97, 0.98, 0.99, 1.0} after the it2b 97-share correction (which
# raised the case rate). 0.98 wins: finding L1 0.0279, case_err 0.4345 vs
# 0.4344 real — essentially exact. Unlike NY's 0.96 (which corrected an
# overshoot), TX needs only a touch-down after the 97-share fix.
TX_COIN_CAL = 0.98

# it2: one-step realized-output calibration (x real_TX_share /
# synth_share from the it1 pilot), mirroring PA1's it3 / NY1's it2.
# Pure empirical ratios were earned 1.1486, unearned 0.9757, shelter 0.8788,
# sua 1.2221, medical 0.6170, depcare 1.5871, hhcomp 0.9863, arithmetic
# 1.1180. The sua correction (1.22 -> 0.91) is the material move: it1
# overshot sua's realized share once the 97-share cut bit.
TX_BUCKET_RATIO = {
    "earned": 1.3286, "unearned": 0.9745, "shelter": 0.8515,
    "sua": 0.9108, "medical": 0.6318, "depcare": 1.5268,
    "hhcomp": 0.9510, "arithmetic": 1.2521,
}

# P(over | nature 97) ratios, TX / national, per bucket.
# it1 pure empirical ratios KEPT: the one-step realized-output correction
# (x real/synth P(over|97,b)) overshot on every bucket — TX's 97-resolution
# instrument has gain > 1, unlike NY's. See tx1_tx_generator.md.
TX_97_RATIO = {
    "earned": 0.9449, "unearned": 0.7025, "shelter": 0.9160,
    "sua": 0.9730, "medical": 0.9158, "depcare": 1.1361,
    "hhcomp": 1.0, "arithmetic": 1.0,
}

# it2b: one-step realized-output correction (x real/synth 97-share from the
# it2 pilot). The it1 pure-empirical 97-share ratios left the realized
# 97-share at 0.41 vs 0.29 real — 97s materialize at a higher rate than the
# drawn mix implies, so the instrument under-corrects. Pure empirical ratios
# were earned 1.0378, unearned 0.7964, shelter 0.5578, sua 0.4768, medical
# 0.8177, depcare 0.7010, hhcomp/arithmetic 1.0 (tiny-n guard).
TX_97_SHARE_RATIO = {
    "earned": 0.9601, "unearned": 0.6395, "shelter": 0.2859, "sua": 0.2808,
    "medical": 0.7728, "depcare": 0.4432, "hhcomp": 0.0993,
    "arithmetic": 0.0,
}

# Direction balance among non-97 natures, TX / national, per bucket.
# Behavioral direction classes (which way the benefit moves when the nature
# is applied; matches the _corrupt_* else-branches). Note nature 39 is
# behaviorally over but sits in errors._dirclass "other" — the national
# dir_weight and these TX ratios compose multiplicatively, so the
# classification only needs to be consistent between fit and apply.
TX_OVER_NATURES = frozenset([35, 37, 38, 39, 53, 56, 7])
TX_UNDER_NATURES = frozenset([44, 52, 57, 6, 13])
TX_DIR_RATIO = {
    # it1 pure empirical ratios KEPT: the one-step realized-output correction
    # (x real/synth on the non-97 direction slice) overshot badly (finding L1
    # 0.0169 -> 0.0685 undamped, 0.0394 sqrt-damped) — the direction
    # instrument amplifies drawn-margin shifts on TX's mix. it1 already lands
    # p(over|err) within 0.015. See tx1_tx_generator.md.
    "earned": {"over": 0.7063, "under": 1.3299},
    "unearned": {"over": 0.7320, "under": 1.4570},
    "shelter": {"over": 0.2852, "under": 0.6707},
    "sua": {"over": 0.4059, "under": 1.1637},
    "medical": {"over": 0.5290, "under": 1.9066},
    "depcare": {"over": 0.3685, "under": 0.8337},
    "hhcomp": {"over": 0.5575, "under": 0.7184},
    "arithmetic": {"over": 1.0, "under": 1.0},
}

# Cause mix ratios (coarse: client/agency/no_fault/other), TX / national,
# fit on NON-97 variances only — 97 causes are resampled from TX_97_CAUSE
# below, because the national 97-cause draw is distorted by national's
# lower 97-cause blanking (TX blanks 0.7995 vs 0.644 national pooled).
# Note no_fault = 0.0 on most buckets: TX essentially never uses cause 26
# (no-fault) on substantive (non-97) variances (depcare keeps 1.0).
TX_CAUSE_RATIO = {
    "earned": {"client": 0.3373, "agency": 1.6224, "no_fault": 0.0, "other": 0.5135},
    "unearned": {"client": 0.7603, "agency": 1.1691, "no_fault": 0.0, "other": 0.7274},
    "shelter": {"client": 1.2845, "agency": 0.7626, "no_fault": 0.0, "other": 0.2748},
    "sua": {"client": 1.41, "agency": 0.9171, "no_fault": 0.0, "other": 0.1545},
    "medical": {"client": 1.4999, "agency": 1.0492, "no_fault": 0.0, "other": 0.2825},
    "depcare": {"client": 1.3018, "agency": 0.9218, "no_fault": 1.0, "other": 0.4266},
    "hhcomp": {"client": 1.103, "agency": 0.9781, "no_fault": 0.0, "other": 0.7927},
    "arithmetic": {"client": 0.0, "agency": 0.9992, "no_fault": 0.0, "other": 1.1153},
}

# TX empirical cause mix ON nature-97 variances, per bucket (raw cause codes).
# TX blanks 79.95% of 97 causes; the recorded remainder is 100% cause 26
# (no-fault) in every bucket — the unweighted per-bucket 97-cause n falls
# below the >=5 guard, so every bucket uses the pooled TX 97-cause mix
# ({'26': 1.0}), verified directly against the microdata (180/180 = 26).
TX_97_CAUSE = {
    "earned": {"26": 1.0},
    "unearned": {"26": 1.0},
    "shelter": {"26": 1.0},
    "sua": {"26": 1.0},
    "medical": {"26": 1.0},
    "depcare": {"26": 1.0},
    "hhcomp": {"26": 1.0},
    "arithmetic": {"26": 1.0},
}

# Dollar-size offsets: TX median error / national median error, per finding
# direction (relative-offset semantics — the generator's national level bias
# is orthogonal and owned by exp31's calibration). Applied as a multiplier
# on the agency-side amount deltas inside the corruptors, so the
# facts->benefit math stays mechanics-consistent. TX's lighter error tail
# (p90 $149 vs $188) is only partly matched by this uniform scale — a
# documented structural limitation (see tx1_tx_generator.md).
TX_S_OVER = 0.8824
TX_S_UNDER = 1.25

# TX blanks cause on 79.95% of timing-97 variances (FYWGT-weighted, pooled).
TX_CAUSE97_BLANK = 0.7995

# Whole-unit ineligibility (mechanism 2): TX's near-full-benefit over share
# (0.0225) is well below national (0.0599), so the unit tail is smaller in
# TX — p_unit stays at the national default as a documented structural
# residual (re-deriving the unit-bucket correction is out of TX1 scope).
TX_P_UNIT = None  # None = keep dollar_mech.P_UNIT_DEFAULT

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


def apply_tx_offsets(dist):
    """Return a dist copy with the TX offset ratios applied (in-memory only).

    Takes the adopted-calibration dist (dollar_mech.adopted_dist output) and
    multiplies: injection coins, per-bucket 97-resolution coins, bucket mixes
    (all stratum keys), earner-conditional nature mixes (97-share and
    direction-balance margins), and per-bucket non-97 cause mixes — each by
    its TX/national ratio, renormalized. The input dist is never mutated.
    """
    d = copy.deepcopy(dist)

    # 1. injection coins. The adopted coins are attrition-corrected to land
    # the national empirical P(error | stratum); scaling by the TX/national
    # conditional ratio assumes materialization (a mechanics property) is
    # state-independent. The whole-unit mass is unchanged for TX, so no
    # re-derivation of the unit-bucket correction is needed.
    inj = d.get("injection_rate", {})
    for key in ("persistent", "earner", "no_earner"):
        sub = inj.get(key)
        if isinstance(sub, dict):
            for s, r in TX_COIN_RATIO.items():
                if s in sub:
                    sub[s] = min(0.99, sub[s] * r * TX_COIN_CAL)

    # 2. timing-97 resolution coins per bucket (direction margin).
    coins = inj.get("p_over_97_resolve", {})
    for b, r in TX_97_RATIO.items():
        if b in coins:
            coins[b] = min(0.95, max(0.05, coins[b] * r))

    # 3. element-bucket mixes (marginal ratios applied to every stratum key;
    # the recorded marginal then tracks TX regardless of stratum composition).
    for key in _BUCKET_MIX_KEYS:
        mix = d.get(key)
        if isinstance(mix, dict):
            for b, r in TX_BUCKET_RATIO.items():
                if b in mix:
                    mix[b] *= r
            _renorm(mix)

    # 4. nature mixes per bucket: 97-share margin and direction-balance
    # margin (marginal ratios on the earner-conditional mixes the injector
    # draws from).
    for key in _NATURE_MIX_KEYS:
        for b, nmap in d.get(key, {}).items():
            r97 = TX_97_SHARE_RATIO.get(b, 1.0)
            dr = TX_DIR_RATIO.get(b, {"over": 1.0, "under": 1.0})
            for n in list(nmap):
                ni = int(n)
                if ni == 97:
                    nmap[n] *= r97
                elif ni in TX_OVER_NATURES:
                    nmap[n] *= dr["over"]
                elif ni in TX_UNDER_NATURES:
                    nmap[n] *= dr["under"]
            _renorm(nmap)

    # 5. cause mixes per bucket (non-97 coarse ratios on the raw-code draws;
    # 97 causes are resampled from TX_97_CAUSE by the _draw_nature wrapper,
    # and 97-cause blanking is set to TX's 0.2189 by the _recorded_cause
    # wrapper).
    for b, cmap in d.get("cause_given_bucket", {}).items():
        ratios = TX_CAUSE_RATIO.get(b)
        if not ratios:
            continue
        for c in list(cmap):
            cmap[c] *= ratios.get(cause_bucket(int(c)), 1.0)
        _renorm(cmap)

    d.setdefault("_tx", {})["conditioned"] = True
    return d


# ---------------------------------------------------------------------------
# TX-only wrappers (installed by generate_tx, removed on return).
# ---------------------------------------------------------------------------
_INCOME_FIELDS = ("earned", "unearned")
_tx_saved = {}


def _tx_draw_nature(facts, bucket, dist, dir_w, rng):
    """Draw (nature, cause); on 97s resample the cause from TX's empirical
    97-cause mix (recorded basis, pre-blanking — TX blanks 21.9% of 97
    causes, far fewer than national's 69.7% pooled, so the national drawn
    97-cause mix is not a usable TX basis)."""
    nature, _cause = _tx_saved["draw_nature"](facts, bucket, dist, dir_w, rng)
    if nature == 97:
        mix = TX_97_CAUSE.get(bucket)
        if mix:
            r = rng.random()
            cum = 0.0
            for code, p in mix.items():
                cum += p
                if r < cum:
                    return nature, int(code)
            return nature, int(next(iter(mix)))
    return nature, _cause


def _tx_direction(field, base, new):
    """Benefit-direction implied by an agency-side amount change."""
    if field in _INCOME_FIELDS:
        return "over" if new < base else "under"
    return "over" if new > base else "under"


def _wrap_corruptor(orig):
    """Scale the realized agency-side amount delta by the TX dollar-size
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
            s = TX_S_OVER if d == "over" else TX_S_UNDER
            truth_corr[field] = round(truth_corr[field] * s, 2)
        else:
            new = agency[field]
            if new != base:
                d = _tx_direction(field, base, new)
                s = TX_S_OVER if d == "over" else TX_S_UNDER
                agency[field] = round(base + s * (new - base), 2)
        return truth_corr, override
    return wrapped


def _tx_recorded_cause(nature, cause, rng):
    # TX blanks cause on 21.9% of timing-97 variances (pooled; national's
    # FY2024-calibrated wrapper blanks 32%). Consume the rng draw the
    # national path takes so the rng stream stays aligned with a same-seed
    # national run.
    if nature == 97:
        if rng.random() < TX_CAUSE97_BLANK:
            return None
        return cause
    return cause


def _enable_tx_wrappers():
    if _tx_saved:
        return
    _tx_saved["draw_nature"] = errors._draw_nature
    _tx_saved["income"] = errors._corrupt_income
    _tx_saved["deduction"] = errors._corrupt_deduction
    _tx_saved["recorded_cause"] = errors._recorded_cause
    errors._draw_nature = _tx_draw_nature
    errors._corrupt_income = _wrap_corruptor(errors._corrupt_income)
    errors._corrupt_deduction = _wrap_corruptor(errors._corrupt_deduction)
    errors._recorded_cause = _tx_recorded_cause


def _disable_tx_wrappers():
    if not _tx_saved:
        return
    errors._draw_nature = _tx_saved["draw_nature"]
    errors._corrupt_income = _tx_saved["income"]
    errors._corrupt_deduction = _tx_saved["deduction"]
    errors._recorded_cause = _tx_saved["recorded_cause"]
    _tx_saved.clear()


# ---------------------------------------------------------------------------
# TX-conditioned generation entry point.
# ---------------------------------------------------------------------------
def generate_tx(n=1000, seed=0, dist="experiments/dist.json", out=None,
                max_attempts=12, persistent_buckets=True, tag_state=True):
    """Generate n TX-conditioned synthetic QC cases.

    Pipeline: load national dist -> adopted calibration (exp31, in-memory)
    -> TX offset ratios (this module, in-memory) -> generate with the
    mechanism patches + TX wrappers installed. All patches are removed
    before return; national generation is unaffected.

    Each case dict matches the national schema plus "state": "TX".
    Returns the output path (or the list of JSON lines when out is None).
    """
    from . import dollar_mech, household
    from .distutil import load_dist

    d = load_dist(dist)
    d = dollar_mech.adopted_dist(d)
    d = apply_tx_offsets(d)

    mech_was_on = dollar_mech.is_enabled()
    dollar_mech.enable(under_scale=dollar_mech.EXP31_UNDER_SCALE)
    _enable_tx_wrappers()
    try:
        rng = random.Random(seed)
        lines = []
        for _ in range(n):
            facts = household.sample_household(rng)
            case = dollar_mech.inject_case(
                facts, rng, d, max_attempts=max_attempts,
                persistent_buckets=persistent_buckets)
            if tag_state:
                case["state"] = "TX"
            lines.append(json.dumps(case))
    finally:
        _disable_tx_wrappers()
        if not mech_was_on:
            dollar_mech.disable()

    if out is None:
        return lines
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Generate TX-conditioned synthetic QC cases.")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dist", required=True, help="empirical distribution JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-attempts", type=int, default=12)
    ap.add_argument("--persistent-buckets",
                    action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--no-state-tag", action="store_true",
                    help="omit the 'state': 'TX' tag on cases")
    args = ap.parse_args()
    generate_tx(n=args.n, seed=args.seed, dist=args.dist, out=args.out,
                max_attempts=args.max_attempts,
                persistent_buckets=args.persistent_buckets,
                tag_state=not args.no_state_tag)
    print(f"wrote {args.n} TX-conditioned cases -> {args.out}")


if __name__ == "__main__":
    main()
