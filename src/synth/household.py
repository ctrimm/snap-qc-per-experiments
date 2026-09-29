"""Household fact sampler. Plausible-not-precise: the calibration experiment
(exp1) measures how far the synthetic marginals are from the real QC file,
and we iterate here until they are close enough for a test harness.

The sampler models the QC sample frame: certified households. Draws that
fail the SNAP gross/net income tests are rejected and resampled (exp6):
ineligible high earners are essentially absent from real QC files
(4/44,891 FY2024 cases with $0 issued benefit) and their corruptions cannot
materialize against the benefit floor.
"""
import random

from . import benefit as benefit_mod
from . import params

# Log-median of monthly household earnings among earners, by household size.
# Fitted to real FY2024 QC FSEARN medians (exp6); sigma 0.75 matches the
# observed spread. All earners pass the income screen at these levels.
EARN_MU = {1: 7.23, 2: 7.75, 3: 7.97, 4: 8.18, 5: 8.32, 6: 8.46}

# exp29: stratum-conditioned base-positivity tables (pre-screen P(field > 0)
# per stratum), fitted so POST-screen P(base > 0) matches the real FY2024 QC
# per-stratum aggregates (see experiments/exp29_sampler_positivity.py).
# Replaces the old flat rates (unearned 0.85/0.50 by senior flag alone;
# shelter 0.63 flat; sua 0.72 flat), which missed senior strata on unearned
# (real 0.95/0.81), earner/senior strata on shelter (real 0.88/0.91/0.95),
# and the whole per-stratum sua spread (real 0.46-0.88). Stratum keys match
# errors._stratum_key. Only WHO has a positive base changes: amounts,
# benefit math, and injection are untouched. Note the values are
# PRE-screen draw probabilities: the income screen attenuates unearned on
# earner strata (drawn unearned often fails the net-income test), so e.g.
# earner_nonsenior needs pre-screen 0.492 to land post-screen 0.260; the
# earner_senior unearned cell is steep enough to need bisection (0.913 ->
# 0.809).
BASE_POSITIVITY = {
    "unearned": {"no_earner_nonsenior": 0.465, "earner_nonsenior": 0.492,
                 "no_earner_senior": 0.953, "earner_senior": 0.913},
    "shelter":  {"no_earner_nonsenior": 0.500, "earner_nonsenior": 0.876,
                 "no_earner_senior": 0.909, "earner_senior": 0.908},
    "sua":      {"no_earner_nonsenior": 0.456, "earner_nonsenior": 0.811,
                 "no_earner_senior": 0.823, "earner_senior": 0.886},
}
# Legacy (pre-exp29) flat rates, for in-process BEFORE comparisons:
#   {"unearned": {s: 0.50/0.85}, "shelter": {s: 0.63}, "sua": {s: 0.72}}.
# Patching BASE_POSITIVITY to these values reproduces the old sampler
# exactly (same rng call order).

# exp32: elderly/disability draw rates refit so POST income-screen rates match
# the real FY2024 QC per-size aggregates (senior = FSNELDER>0 | SSI1-8>0 |
# FSNDIS>0; real P(elderly)=0.309, P(disabled|not elderly)=0.270,
# P(senior)=0.496). Both drivers were off: the senior-age draw (size-1
# 0.28->0.354, size-2 0.08->0.169, size-3+ 0.08->0.025) and the disability flag
# (0.12 flat -> 0.152/0.100/0.101 by size group). Values are PRE-screen: the
# income screen inflates senior rates (seniors skip the gross test), so these
# were tuned by fixed-point simulation to land the post-screen targets
# (see experiments/exp32_medical_senior.py). Size groups: 1 / 2 / 3+.
_P_ELDERLY_BY_SIZE = {1: 0.3538, 2: 0.1694, 3: 0.0254}
_P_DISABLED_BY_SIZE = {1: 0.1515, 2: 0.0995, 3: 0.1008}
# Legacy (pre-exp32) rates, for in-process BEFORE comparisons:
#   elderly 0.28 if size==1 else 0.08; disabled 0.12 flat.
# Patching the two tables to {1:0.28,2:0.08,3:0.08} / {1:0.12,2:0.12,3:0.12}
# reproduces the old sampler exactly (same rng call order).


def _income_eligible(facts: dict) -> bool:
    size = facts["hh_size"]
    gross = facts["earned"] + facts["unearned"]
    if not facts["senior_disabled"] and gross > params.gross_income_limit(size):
        return False
    return benefit_mod.compute(facts)["net"] <= params.net_income_limit(size)


def sample_household(rng: random.Random) -> dict:
    for _ in range(25):
        facts = _sample_unscreened(rng)
        if _income_eligible(facts):
            return facts
    return facts  # give up gracefully; the injector handles odd cases


def _sample_unscreened(rng: random.Random) -> dict:
    size = rng.choices([1, 2, 3, 4, 5, 6], weights=[0.45, 0.25, 0.14, 0.09, 0.04, 0.03])[0]

    _szg = 1 if size == 1 else (2 if size == 2 else 3)
    elderly = rng.random() < _P_ELDERLY_BY_SIZE[_szg]
    disabled = (not elderly) and rng.random() < _P_DISABLED_BY_SIZE[_szg]
    senior_or_disabled = elderly or disabled
    n_earners = 0
    earned = 0.0
    # P(any earnings) tuned so post-screen earned>0 ~= 0.27 (real QC FY2024).
    # Bumped 0.60 -> 0.65 when the FY2024 income limits were corrected
    # (exp10): the lower screen rejects more earners, so more must be drawn
    # pre-screen to hold the post-screen share.
    p_earn = 0.65 if not senior_or_disabled else 0.13
    # Household earnings drawn size-dependent, fitted to real FSEARN medians
    # among earners (exp6): the old per-earner lognormal(7.45, .) was far too
    # high and most earners failed the new income screen.
    if rng.random() < p_earn:
        n_earners = 1 if rng.random() < 0.9 else 2
        mu = EARN_MU[min(size, 6)]
        earned = rng.lognormvariate(mu, 0.75)

    # Stratum key for the base-positivity tables below. Matches
    # errors._stratum_key; earned and senior_disabled are already fixed at
    # this point, so the key is known before these fields are drawn.
    _skey = ("earner" if earned > 0 else "no_earner") + "_" + \
            ("senior" if senior_or_disabled else "nonsenior")

    unearned = 0.0
    if rng.random() < BASE_POSITIVITY["unearned"][_skey]:
        unearned = rng.choices([943, 1400, 600], weights=[0.45, 0.35, 0.20])[0] * rng.uniform(0.8, 1.15)

    shelter = rng.uniform(350, 1700)
    if rng.random() >= BASE_POSITIVITY["shelter"][_skey]:
        shelter = 0.0  # subsidized / no shelter cost edge cases
    sua = 1 if rng.random() < BASE_POSITIVITY["sua"][_skey] else 0

    medical = 0.0
    if senior_or_disabled and rng.random() < 0.17:
        medical = rng.uniform(20, 400)

    depcare = 0.0
    if size > 2 and rng.random() < 0.07:
        depcare = rng.uniform(100, 650)

    # n_kids from the empirical FY2024 distribution (exp12): depcare
    # variances occur exclusively on kid households.
    _KID_DIST = {
        1: [(0, 0.98), (1, 0.02)],
        2: [(0, 0.36), (1, 0.58), (2, 0.06)],
        3: [(0, 0.04), (1, 0.23), (2, 0.67), (3, 0.06)],
        4: [(0, 0.01), (1, 0.05), (2, 0.35), (3, 0.55), (4, 0.04)],
        5: [(0, 0.005), (1, 0.01), (2, 0.07), (3, 0.42), (4, 0.46), (5, 0.03)],
        6: [(1, 0.01), (2, 0.03), (3, 0.09), (4, 0.54), (5, 0.31), (6, 0.02)],
    }
    _kd = _KID_DIST[min(size, 6)]
    _ks, _ws = zip(*_kd)
    n_kids = rng.choices(_ks, weights=_ws)[0]

    return {
        "hh_size": size,
        "n_kids": n_kids,
        "earned": round(earned, 2),
        "unearned": round(unearned, 2),
        "shelter": round(shelter, 2),
        "sua": sua,
        "medical_exp": round(medical, 2),
        "depcare": round(depcare, 2),
        "senior_disabled": 1 if senior_or_disabled else 0,
        # shared features for transfer experiments (exp4+)
        "review_month": rng.randint(1, 12),
        "n_elderly": 1 if elderly else 0,
        "n_disabled": 1 if disabled else 0,
    }
