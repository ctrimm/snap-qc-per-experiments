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

    elderly = rng.random() < (0.28 if size == 1 else 0.08)
    disabled = (not elderly) and rng.random() < 0.12
    senior_or_disabled = elderly or disabled

    n_earners = 0
    earned = 0.0
    # P(any earnings) tuned so post-screen earned>0 ~= 0.27 (real QC FY2024).
    # Household earnings drawn size-dependent, fitted to real FSEARN medians
    # among earners (exp6): the old per-earner lognormal(7.45, .) was far too
    # high and most earners failed the new income screen.
    p_earn = 0.60 if not senior_or_disabled else 0.13
    if rng.random() < p_earn:
        n_earners = 1 if rng.random() < 0.9 else 2
        mu = EARN_MU[min(size, 6)]
        earned = rng.lognormvariate(mu, 0.75)

    unearned = 0.0
    p_une = 0.85 if senior_or_disabled else 0.50
    if rng.random() < p_une:
        unearned = rng.choices([943, 1400, 600], weights=[0.45, 0.35, 0.20])[0] * rng.uniform(0.8, 1.15)

    shelter = rng.uniform(350, 1700)
    if rng.random() < 0.37:
        shelter = 0.0  # subsidized / no shelter cost edge cases
    sua = 1 if rng.random() < 0.72 else 0

    medical = 0.0
    if senior_or_disabled and rng.random() < 0.17:
        medical = rng.uniform(20, 400)

    depcare = 0.0
    if size > 2 and rng.random() < 0.07:
        depcare = rng.uniform(100, 650)

    return {
        "hh_size": size,
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
