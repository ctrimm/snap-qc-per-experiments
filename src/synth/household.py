"""Household fact sampler. Plausible-not-precise: the calibration experiment
(exp1) measures how far the synthetic marginals are from the real QC file,
and we iterate here until they are close enough for a test harness.
"""
import random


def sample_household(rng: random.Random) -> dict:
    size = rng.choices([1, 2, 3, 4, 5, 6], weights=[0.45, 0.25, 0.14, 0.09, 0.04, 0.03])[0]

    elderly = rng.random() < (0.28 if size == 1 else 0.08)
    disabled = (not elderly) and rng.random() < 0.12
    senior_or_disabled = elderly or disabled

    n_earners = 0
    earned = 0.0
    if not senior_or_disabled or rng.random() < 0.25:
        n_earners = rng.choices([0, 1, 2], weights=[0.73, 0.24, 0.03])[0]
        for _ in range(n_earners):
            # monthly wages, roughly lognormal around ~$1,400
            earned += rng.lognormvariate(7.45, 0.75)

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
    }
