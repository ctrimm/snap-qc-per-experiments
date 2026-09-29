"""Variance taxonomy: QC element/nature/cause codes, bucket mappings, and the
empirical distributions computed from the real FY2024 QC public-use file.

Element/nature/cause labels transcribed from the FY2024 QC Technical
Documentation codebook (Chapter V).
"""

# element code -> bucket used by the synthetic generator
ELEMENT_BUCKETS = {
    311: "earned", 312: "earned", 314: "earned", 321: "earned",
    331: "unearned", 332: "unearned", 333: "unearned", 334: "unearned",
    335: "unearned", 336: "unearned", 342: "unearned", 343: "unearned",
    344: "unearned", 345: "unearned", 346: "unearned", 350: "unearned",
    323: "depcare",
    363: "shelter",
    364: "sua",
    365: "medical",
    366: "childsupport",
    150: "hhcomp",
    211: "assets", 212: "assets", 213: "assets", 214: "assets",
    221: "assets", 222: "assets", 224: "assets", 225: "assets",
    520: "arithmetic",
    540: "reporting", 542: "reporting", 560: "reporting",
    361: "standard", 371: "income_total", 372: "income_total",
}

ELEMENT_LABELS = {
    311: "Wages and salaries", 312: "Self-employment", 314: "Other earned income",
    321: "Earned income deductions", 323: "Dependent care deduction",
    331: "RSDI benefits", 332: "Veterans' benefits", 333: "SSI",
    334: "Unemployment compensation", 336: "Other government benefits",
    346: "Other unearned income", 350: "Child support received",
    363: "Shelter deduction", 364: "Standard utility allowance",
    365: "Medical expense deductions", 150: "Unit composition",
    520: "Arithmetic computation", 560: "Reporting systems",
}

NATURE_LABELS = {
    35: "Unreported source of income",
    37: "All income from source known but not included",
    38: "More income received from this source than budgeted",
    44: "Less income received from this source than budgeted",
    52: "Deduction that should have been included was not",
    53: "Deduction included that should not have been",
    54: "Incorrect standard used",
    56: "Incorrect deduction amount included - budgeted too much",
    57: "Incorrect deduction amount included - budgeted too little",
    97: "Not required to be reported or acted upon (time frames/reporting)",
    98: "Transcription or computation errors",
    99: "Other",
}

CAUSE_LABELS = {
    1: "Information not reported",
    2: "Incomplete/incorrect info provided; agency not required to verify",
    4: "Incorrect information provided by client (IPV)",
    10: "Policy incorrectly applied",
    12: "Reported information disregarded or not applied",
    14: "Agency failed to follow up on inconsistent/incomplete information",
    16: "Agency failed to verify required information",
    19: "Mass change (computer-generated)",
    22: "Agency budgeted an incorrect amount",
    26: "Change not required to be reported/acted upon",
}

# cause code -> coarse bucket for experiments
CAUSE_BUCKETS = {
    1: "client", 2: "client", 4: "client",
    10: "agency", 12: "agency", 14: "agency", 16: "agency",
    18: "agency", 19: "agency", 20: "agency", 21: "agency", 22: "agency",
    26: "no_fault",
}


def cause_bucket(code: int) -> str:
    return CAUSE_BUCKETS.get(code, "other")


def element_bucket(code: int) -> str:
    return ELEMENT_BUCKETS.get(code, "other")
