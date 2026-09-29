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


def max_allotment(household_size: int) -> int:
    if household_size <= 8:
        return MAX_ALLOTMENT[household_size]
    return MAX_ALLOTMENT[8] + EACH_ADDITIONAL_PERSON * (household_size - 8)


def standard_deduction(household_size: int) -> int:
    return STANDARD_DEDUCTION[min(household_size, 6)]
