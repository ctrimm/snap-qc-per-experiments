"""Deterministic SNAP benefit computation (the harness's stand-in for the QC
Minimodel). Standard federal computation order:

  net = gross - 20% earned - standard - medical(>35, elderly/disabled)
            - depcare - excess shelter (capped)
  benefit = max_allotment(size) - 0.30 * net   (min $23 for 1-2 person HHs)
"""
import math
from . import params


def compute(facts: dict) -> dict:
    size = facts["hh_size"]
    gross = facts["earned"] + facts["unearned"]

    earn_ded = math.floor(params.EARNED_INCOME_DEDUCTION_RATE * facts["earned"])
    std_ded = params.standard_deduction(size)
    med_ded = max(0.0, facts["medical_exp"] - params.MEDICAL_DEDUCTION_THRESHOLD) \
        if facts["senior_disabled"] else 0.0

    adjusted = gross - earn_ded - std_ded - med_ded - facts["depcare"]

    excess_shelter = max(0.0, facts["shelter"] - 0.5 * max(adjusted, 0.0))
    if not facts["senior_disabled"]:
        excess_shelter = min(excess_shelter, params.SHELTER_DEDUCTION_CAP)

    net = max(0.0, adjusted - excess_shelter)
    benefit = params.max_allotment(size) - 0.30 * net
    benefit = max(0.0, benefit)
    if size <= 2 and benefit > 0:
        benefit = max(benefit, params.MINIMUM_BENEFIT)
    benefit = math.floor(benefit)

    return {
        "benefit": benefit,
        "gross": round(gross, 2),
        "net": round(net, 2),
        "earn_ded": earn_ded,
        "std_ded": std_ded,
        "med_ded": round(med_ded, 2),
        "excess_shelter": round(excess_shelter, 2),
    }
