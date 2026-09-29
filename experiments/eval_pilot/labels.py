"""Label pipeline + deterministic input rendering for the QC-variance eval pilot.

Reads real QC public-use rows (pandas Series / dict-like) and produces:
  - labels: T1..T6 per the exp17 schema (see TASKS below)
  - fields: de-identified input field dicts (agency view + verification view)
  - render(): deterministic case text in jargon or plain-English templates,
    for the classification view (no benefit amounts) or the dollar view
    (FSBEN shown, RAWBEN never shown).

Label rules (decisions documented in experiments/exp30_eval_pilot.md):
  - "reportable variance" = ELEMENTi recorded AND AMOUNTi > 0. Variances with
    AMOUNT = 0 are tolerance/non-reportable: excluded from labels, and their
    taxonomy codes never enter the input text.
  - primary variance = reportable variance with the largest AMOUNT;
    tie-break = lowest variance index.
  - T1 = STATUS != 1 (official case finding). T2 = STATUS mapped to
    correct/overissuance/underissuance. Label-side use of STATUS is not
    leakage: inputs never see STATUS/AMTERR/ELEMENT*/NATURE*/AGENCY*/DISCOV*/
    RAWBEN, and classification inputs see no benefit amounts at all.
  - T3/T4/T5 come from the primary variance (element bucket / nature code /
    cause bucket via src/synth/codebook.py). Defined only for error cases
    with a reportable primary variance whose nature code is one of the 12
    standard codes.
  - T6 = signed AMTERR (+ overissuance, - underissuance, 0 correct).
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from synth.codebook import (  # noqa: E402
    element_bucket,
    cause_bucket,
    ELEMENT_LABELS,
    NATURE_LABELS,
)

# ---------------------------------------------------------------- constants

FINDINGS = ["correct", "overissuance", "underissuance"]
STATUS_TO_FINDING = {1: "correct", 2: "overissuance", 3: "underissuance"}

ELEMENT_BUCKETS = [
    "earned", "unearned", "depcare", "shelter", "sua", "medical",
    "childsupport", "hhcomp", "assets", "arithmetic", "reporting",
    "standard", "income_total", "other",
]

NATURE_CODES = [35, 37, 38, 44, 52, 53, 54, 56, 57, 97, 98, 99]
NATURE_SET = set(NATURE_CODES)

CAUSE_BUCKETS = ["client", "agency", "no_fault", "other"]

TASKS = {
    "t1": {"name": "detection", "values": ["error", "correct"]},
    "t2": {"name": "finding", "values": FINDINGS},
    "t3": {"name": "element", "values": ELEMENT_BUCKETS},
    "t4": {"name": "nature", "values": [str(c) for c in NATURE_CODES]},
    "t5": {"name": "cause", "values": CAUSE_BUCKETS},
    "t6": {"name": "dollar", "values": None},  # free-form signed integer
}

# (key, jargon label, plain-English label, view)
# view: "agency" = reported/as-budgeted, "verif" = QC-verified/final,
#       "dollar" = shown only on the dollar task (never RAWBEN).
FIELD_SPEC = [
    ("state_name", "State", "State", "agency"),
    ("sample_month", "Sample month (YRMONTH)", "Sample month", "agency"),
    ("raw_hhsize", "Reported number of people in household (RAWHSIZE)",
     "Household size on the case record", "agency"),
    ("cert_hhsize", "Certified unit size (CERTHHSZ)",
     "Certified SNAP unit size", "agency"),
    ("raw_gross", "Reported gross countable unit income (RAWGROSS)",
     "Total countable income before deductions, as reported", "agency"),
    ("raw_net", "Reported net countable unit income (RAWNET)",
     "Total countable income after deductions, as reported", "agency"),
    ("raw_ernded", "Reported earned income deduction (RAWERND)",
     "Earned-income deduction claimed", "agency"),
    ("rep_csup_ded", "Reported child support payment deduction (FSCSEXP)",
     "Child support paid to someone outside the home (deduction claimed)", "agency"),
    ("rep_depcare_ded", "Reported dependent care deduction (FSDEPDED)",
     "Dependent care costs (deduction claimed)", "agency"),
    ("rep_med_exp", "Reported medical expenses (FSMEDEXP)",
     "Out-of-pocket medical expenses reported", "agency"),
    ("rep_shel_ded", "Reported shelter deduction (SHELDED)",
     "Shelter deduction claimed", "agency"),
    ("rent", "Rent/mortgage amount (RENT)", "Monthly rent or mortgage", "agency"),
    ("util", "Utility amount (UTIL)", "Monthly utility costs", "agency"),
    ("sua_use", "Standard utility allowance - usage and entitlement (SUA1)",
     "Standard utility allowance: household's usage and entitlement", "agency"),
    ("sua_amt", "Standard utility allowance - prorated (SUA2)",
     "Standard utility allowance: prorated amount", "agency"),
    ("homeless", "Indicator of homelessness (HOMEDED)",
     "Homeless household flag", "agency"),
    ("verif_unit_size", "Constructed certified unit size (FSUSIZE)",
     "Verified SNAP unit size", "verif"),
    ("verif_hhsize", "Number of people in household (CTPRHH)",
     "Verified household size", "verif"),
    ("verif_gross", "Final gross countable unit income (FSGRINC)",
     "Verified total countable income before deductions", "verif"),
    ("verif_net", "Final net countable unit income (FSNETINC)",
     "Verified total countable income after deductions", "verif"),
    ("verif_earned", "Countable unit earned income (FSEARN)",
     "Verified earned income total", "verif"),
    ("verif_unearned", "Countable unit unearned income (FSUNEARN)",
     "Verified unearned income total", "verif"),
    ("inc_sources", "Verified income by source", "Verified income by source", "verif"),
    ("std_ded", "Standard deduction (FSSTDDED)",
     "Standard deduction used in the benefit calculation", "verif"),
    ("ernd_ded", "Calculated earned income deduction (FSERNDED)",
     "Earned-income deduction used in the benefit calculation", "verif"),
    ("med_ded", "Calculated medical expense deduction (FSMEDDED)",
     "Medical expense deduction used in the benefit calculation", "verif"),
    ("shel_ded", "Calculated excess shelter expense deduction (FSSLTDED)",
     "Excess shelter deduction used in the benefit calculation", "verif"),
    ("tot_ded", "Total deductions (FSTOTDED)",
     "Total deductions used in the benefit calculation", "verif"),
    ("csup_ded", "Child support payment deduction (FSCSDED)",
     "Child support deduction used in the benefit calculation", "verif"),
    ("shel_exp", "Calculated shelter expenses (FSSLTEXP)",
     "Verified total shelter expenses", "verif"),
    ("homeless_ded", "Amount of homeless household shelter deduction (HOMELESS_DED)",
     "Homeless shelter deduction amount", "verif"),
    ("composition", "Unit composition code (COMPOSITION)",
     "Household composition code", "verif"),
    ("cat_elig", "Categorical eligibility status code (CAT_ELIG)",
     "Categorical eligibility status code", "verif"),
    ("has_child", "Indicator of child in unit (FSKID)",
     "Child in the home", "verif"),
    ("has_elder", "Indicator of elderly individual in unit (FSELDER)",
     "Elderly person in the home", "verif"),
    ("n_elder", "Number of elderly individuals in unit (FSNELDER)",
     "Number of elderly people in the home", "verif"),
    ("n_disab", "Number of individuals age 59 and younger with a disability in unit (FSNDIS)",
     "Number of people with a disability in the home", "verif"),
    ("fsben", "Final calculated benefit (FSBEN)",
     "Correct monthly benefit as recomputed by QC", "dollar"),
]

# verified income-source aggregates rendered under "inc_sources" (nonzero only)
INCOME_SOURCES = [
    ("FSWAGES", "wages and salaries"),
    ("FSSLFEMP", "self-employment income"),
    ("FSOTHERN", "other earned income"),
    ("FSSOCSEC", "Social Security benefits"),
    ("FSVET", "veterans benefits"),
    ("FSSSI", "SSI"),
    ("FSUNEMP", "unemployment compensation"),
    ("FSWCOMP", "workers' compensation"),
    ("FSOTHGOV", "other government benefits"),
    ("FSTANF", "TANF cash assistance"),
    ("FSDEEM", "deemed income"),
    ("FSOTHUN", "other unearned income"),
    ("FSCSUPRT", "child support received"),
    ("FSGA", "general assistance"),
    ("FSEDLOAN", "educational loans"),
    ("FSDIVER", "diversion payments"),
    ("FSENERGY", "energy assistance"),
    ("FSFOSTER", "foster care payments"),
    ("FSRENTMINC", "rental income (property managed)"),
    ("FSINTER", "interest income"),
    ("FSANNUITY", "annuity income"),
    ("FSPENSION", "pension income"),
    ("FSOLDAGE", "old-age benefits"),
    ("FSSURV", "survivors benefits"),
    ("FSSTRIKE", "strike benefits"),
    ("FSRENTINC", "rental income"),
    ("FSALIMNY", "alimony"),
    ("FSGOVROY", "government royalties"),
    ("FSGOVDIV", "government dividends"),
    ("FSGOVINTER", "government interest"),
    ("FSTRUST", "trust income"),
    ("FSUNK", "income from unknown source"),
    ("FSWGESUP", "wage supplementation"),
    ("FSCONT", "contributions"),
]


# ---------------------------------------------------------------- helpers

def _num(row, key, default=None):
    try:
        v = row.get(key, default)
    except AttributeError:
        v = default
    if v is None:
        return default
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if math.isnan(f):
        return default
    return f


def _int_or_none(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return int(round(f))


def _money(v):
    """Render a dollar amount as a plain integer, or 'not reported'."""
    i = _int_or_none(v)
    return str(i) if i is not None else "not reported"


# ---------------------------------------------------------------- labels

def primary_variance(row):
    """Return the primary variance dict or None.

    Primary = reportable variance (ELEMENT recorded, AMOUNT > 0) with the
    largest AMOUNT; tie-break = lowest variance index. AMOUNT is unsigned in
    the file, so largest |dollar| == largest AMOUNT.
    """
    best = None
    for i in range(1, 10):
        e = _int_or_none(_num(row, f"ELEMENT{i}"))
        a = _num(row, f"AMOUNT{i}", 0.0) or 0.0
        if e is None or a <= 0:
            continue
        if best is None or a > best["amount"]:
            best = {
                "index": i,
                "element": e,
                "nature": _int_or_none(_num(row, f"NATURE{i}")),
                "cause": _int_or_none(_num(row, f"AGENCY{i}")),
                "amount": a,
            }
    return best


def first_recorded_variance(row):
    """Lowest-index reportable variance (open question 2 comparator)."""
    for i in range(1, 10):
        e = _int_or_none(_num(row, f"ELEMENT{i}"))
        a = _num(row, f"AMOUNT{i}", 0.0) or 0.0
        if e is not None and a > 0:
            return {
                "index": i,
                "element": e,
                "nature": _int_or_none(_num(row, f"NATURE{i}")),
                "cause": _int_or_none(_num(row, f"AGENCY{i}")),
                "amount": a,
            }
    return None


def variance_stats(row):
    """Counts of recorded / reportable variances (for flags)."""
    n_rec = n_rep = 0
    for i in range(1, 10):
        e = _int_or_none(_num(row, f"ELEMENT{i}"))
        if e is None:
            continue
        n_rec += 1
        if (_num(row, f"AMOUNT{i}", 0.0) or 0.0) > 0:
            n_rep += 1
    return n_rec, n_rep


def label_case(row):
    """Return the T1..T6 label dict for one QC row.

    T3/T4/T5 are None when the case has no reportable primary variance, or
    when the primary nature code is outside the 12 standard codes (such rows
    are excluded at sampling time).
    """
    status = _int_or_none(_num(row, "STATUS"))
    amterr = _num(row, "AMTERR", 0.0) or 0.0
    finding = STATUS_TO_FINDING.get(status)
    labels = {
        "t1": "error" if status != 1 else "correct",
        "t2": finding,
        "t3": None,
        "t4": None,
        "t5": None,
        "t6": None,
    }
    if finding == "correct":
        labels["t6"] = 0
    elif finding == "overissuance":
        labels["t6"] = int(round(amterr))
    elif finding == "underissuance":
        labels["t6"] = -int(round(amterr))
    prim = primary_variance(row)
    if prim is not None and status != 1:
        labels["t3"] = element_bucket(prim["element"])
        if prim["nature"] in NATURE_SET:
            labels["t4"] = str(prim["nature"])
        labels["t5"] = cause_bucket(prim["cause"]) if prim["cause"] is not None else "other"
        labels["_primary"] = prim  # internal; stripped before writing items
    return labels


# ---------------------------------------------------------------- fields

def extract_fields(row):
    """De-identified input fields for one row (no PII; public-use values)."""
    g = lambda k: _num(row, k)  # noqa: E731
    state_name = row.get("STATENAME", row.get("STATE", ""))
    try:
        if state_name is None or (isinstance(state_name, float) and math.isnan(state_name)):
            state_name = str(row.get("STATE", ""))
    except TypeError:
        pass
    fields = {
        "state_name": str(state_name).strip(),
        "sample_month": _int_or_none(g("YRMONTH")),
        "raw_hhsize": _int_or_none(g("RAWHSIZE")),
        "cert_hhsize": _int_or_none(g("CERTHHSZ")),
        "raw_gross": _int_or_none(g("RAWGROSS")),
        "raw_net": _int_or_none(g("RAWNET")),
        "raw_ernded": _int_or_none(g("RAWERND")),
        "rep_csup_ded": _int_or_none(g("FSCSEXP")),
        "rep_depcare_ded": _int_or_none(g("FSDEPDED")),
        "rep_med_exp": _int_or_none(g("FSMEDEXP")),
        "rep_shel_ded": _int_or_none(g("SHELDED")),
        "rent": _int_or_none(g("RENT")),
        "util": _int_or_none(g("UTIL")),
        "sua_use": _int_or_none(g("SUA1")),
        "sua_amt": _int_or_none(g("SUA2")),
        "homeless": _int_or_none(g("HOMEDED")),
        "verif_unit_size": _int_or_none(g("FSUSIZE")),
        "verif_hhsize": _int_or_none(g("CTPRHH")),
        "verif_gross": _int_or_none(g("FSGRINC")),
        "verif_net": _int_or_none(g("FSNETINC")),
        "verif_earned": _int_or_none(g("FSEARN")),
        "verif_unearned": _int_or_none(g("FSUNEARN")),
        "inc_sources": [
            {"code": code, "label": label, "amount": _int_or_none(g(code))}
            for code, label in INCOME_SOURCES
            if _int_or_none(g(code))
        ],
        "std_ded": _int_or_none(g("FSSTDDED")),
        "ernd_ded": _int_or_none(g("FSERNDED")),
        "med_ded": _int_or_none(g("FSMEDDED")),
        "shel_ded": _int_or_none(g("FSSLTDED")),
        "tot_ded": _int_or_none(g("FSTOTDED")),
        "csup_ded": _int_or_none(g("FSCSDED")),
        "shel_exp": _int_or_none(g("FSSLTEXP")),
        "homeless_ded": _int_or_none(g("HOMELESS_DED")),
        "composition": _int_or_none(g("COMPOSITION")),
        "cat_elig": _int_or_none(g("CAT_ELIG")),
        "has_child": _int_or_none(g("FSKID")),
        "has_elder": _int_or_none(g("FSELDER")),
        "n_elder": _int_or_none(g("FSNELDER")),
        "n_disab": _int_or_none(g("FSNDIS")),
        "fsben": _int_or_none(g("FSBEN")),
    }
    return fields


# ---------------------------------------------------------------- rendering

def render(fields, template="jargon", view="class"):
    """Deterministic case text.

    template: "jargon" (codebook field language) or "plain" (plain English).
    view: "class" (classification tasks - no benefit amounts at all) or
          "dollar" (dollar task - FSBEN shown; RAWBEN never shown).
    """
    assert template in ("jargon", "plain")
    assert view in ("class", "dollar")
    L = 1 if template == "plain" else 0  # label index: 0=jargon,1=plain
    lines = []
    lines.append("AGENCY VIEW - what the state agency had on record when it "
                 "budgeted the case:")
    for key, jargon, plain, fview in FIELD_SPEC:
        if fview != "agency":
            continue
        label = (jargon, plain)[L]
        lines.append(f"- {label}: {_fmt_field(key, fields[key])}")
    lines.append("")
    lines.append("VERIFICATION VIEW - what the QC reviewer verified through "
                 "documentation and collateral contacts:")
    for key, jargon, plain, fview in FIELD_SPEC:
        if fview != "verif":
            continue
        label = (jargon, plain)[L]
        lines.append(f"- {label}: {_fmt_field(key, fields[key])}")
    if view == "dollar":
        lines.append("")
        lines.append("BENEFIT (QC-recomputed correct amount):")
        label = ("Final calculated benefit (FSBEN)",
                 "Correct monthly benefit as recomputed by QC")[L]
        lines.append(f"- {label}: {_money(fields['fsben'])}")
    lines.append("")
    lines.append("All dollar amounts are monthly dollars.")
    return "\n".join(lines)


def _fmt_field(key, value):
    if key == "inc_sources":
        if not value:
            return "none reported"
        return "; ".join(f"{s['label']}: ${_money(s['amount'])}" for s in value)
    if key in ("sample_month",):
        return str(value) if value is not None else "not reported"
    if key in ("has_child", "has_elder"):
        if value is None:
            return "not reported"
        return "yes" if value == 1 else "no"
    if key == "homeless":
        if value is None:
            return "not reported"
        return "yes" if value == 1 else "no"
    if key == "state_name":
        return value or "not reported"
    return _money(value)
