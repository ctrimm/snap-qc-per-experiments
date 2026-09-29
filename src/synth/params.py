"""FY2024 SNAP parameters, 48 contiguous states.

HARNESS APPROXIMATIONS — good enough to test the data-gen loop, NOT the
official QC Minimodel. If this ever graduates beyond experiments, replace
with the exact FNS parameters per fiscal year.
"""

MAX_ALLOTMENT = {1: 291, 2: 535, 3: 766, 4: 973, 5: 1155, 6: 1386, 7: 1532, 8: 1751}
EACH_ADDITIONAL_PERSON = 219

STANDARD_DEDUCTION = {1: 198, 2: 198, 3: 198, 4: 208, 5: 244, 6: 279}  # 6 = 6+

SHELTER_DEDUCTION_CAP = 672
EARNED_INCOME_DEDUCTION_RATE = 0.20
MEDICAL_DEDUCTION_THRESHOLD = 35  # elderly/disabled only, excess over this counts
MINIMUM_BENEFIT = 23  # 1-2 person households
QC_ERROR_THRESHOLD = 56  # FY2024: only errors above this count toward PER

# FY2024 SNAP income eligibility limits, 48 contiguous states + DC.
# Validated against statute 2026-09-29 (exp10): FRAC "SNAP FY2024 Income
# Limits" Table 3 / FNS COLA memo. Gross test waived for households with an
# elderly/disabled member. NOTE: an earlier version of this table carried
# ~6%-high values from a later fiscal year (exp10); always annotate the
# fiscal year when updating.
GROSS_INCOME_LIMIT = {1: 1580, 2: 2137, 3: 2694, 4: 3250, 5: 3807,
                      6: 4364, 7: 4921, 8: 5478}  # FY2024, 130% FPL
GROSS_LIMIT_EACH_ADDITIONAL = 557  # FY2024
NET_INCOME_LIMIT = {1: 1215, 2: 1644, 3: 2072, 4: 2500, 5: 2929,
                    6: 3357, 7: 3785, 8: 4214}  # FY2024, 100% FPL
NET_LIMIT_EACH_ADDITIONAL = 429  # FY2024


def gross_income_limit(household_size: int) -> int:
    if household_size <= 8:
        return GROSS_INCOME_LIMIT[household_size]
    return GROSS_INCOME_LIMIT[8] + GROSS_LIMIT_EACH_ADDITIONAL * (household_size - 8)


def net_income_limit(household_size: int) -> int:
    if household_size <= 8:
        return NET_INCOME_LIMIT[household_size]
    return NET_INCOME_LIMIT[8] + NET_LIMIT_EACH_ADDITIONAL * (household_size - 8)


def max_allotment(household_size: int) -> int:
    if household_size <= 8:
        return MAX_ALLOTMENT[household_size]
    return MAX_ALLOTMENT[8] + EACH_ADDITIONAL_PERSON * (household_size - 8)


def standard_deduction(household_size: int) -> int:
    return STANDARD_DEDUCTION[min(household_size, 6)]
