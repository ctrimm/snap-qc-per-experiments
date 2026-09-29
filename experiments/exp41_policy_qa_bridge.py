"""Exp 41 — policy-QA bridge: is the deterministic benefit calculator a reliable
oracle for generating LM training/eval QA pairs?

22 multiple-choice questions in CalFresh-MCQ style (stem + 4 options). Every
answer is derived programmatically from benefit.py / params.py / codebook.py —
no language model involved. An *oracle* here means a trusted reference program
whose outputs we treat as ground truth when mass-producing QA pairs.

Question coverage:
  - benefit formula (max allotment - 30% of net income; $23 minimum benefit)
  - deduction ordering and caps (20% earned disregard, standard deduction by
    size, dependent care, medical >$35 for elderly/disabled only, shelter cap)
  - error direction (over- vs under-issuance from a case change)
  - variance coding (which element/nature a described error maps to)
  - scope probes (rules the calculator does NOT implement)

Derive kinds:
  benefit   -> compute(facts)["benefit"] must equal the option value
  trace     -> a computation-trace field (earn_ded, std_ded, med_ded,
               excess_shelter) must equal the option value
  diff      -> benefit(facts_b) - benefit(facts_a) must equal the option value
  direction -> compare issued vs true benefit; over if issued > true
  params    -> a params.py constant must equal the option value
  codebook  -> element/nature labels in codebook.py must match the option
  scope     -> the calculator must demonstrably ignore the rule's facts

Usage: python experiments/exp41_policy_qa_bridge.py
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit  # noqa: E402
from synth import params  # noqa: E402
from synth import codebook  # noqa: E402


def F(**kw):
    """Case facts with the keys benefit.compute() reads."""
    d = {"hh_size": 3, "earned": 0, "unearned": 0, "medical_exp": 0,
         "senior_disabled": False, "depcare": 0, "shelter": 0}
    d.update(kw)
    return d


def _dir(issued, true):
    if issued > true:
        return "over"
    if issued < true:
        return "under"
    return "none"


QUESTIONS = [
    dict(
        id="Q1", topic="benefit formula", kind="benefit",
        text=("A 4-person household has no earnings, no unearned income, and "
              "no shelter costs. What is its monthly SNAP benefit under the "
              "FY2024 formula?"),
        choices=[("A", 973, "$973"), ("B", 766, "$766"),
                 ("C", 672, "$672"), ("D", 0, "$0")],
        correct="A",
        rationale=("Zero net income means the full maximum allotment for a "
                   "4-person household: $973."),
        derive={"kind": "benefit", "facts": F(hh_size=4)},
    ),
    dict(
        id="Q2", topic="benefit formula", kind="benefit",
        text=("A 2-person household's countable net income is $1,000/month. "
              "What is its benefit?"),
        choices=[("A", 235, "$235"), ("B", 335, "$335"),
                 ("C", 300, "$300"), ("D", 205, "$205")],
        correct="A",
        rationale=("Benefit = max allotment - 30% of net income: "
                   "$535 - 0.30 x $1,000 = $235."),
        derive={"kind": "benefit",
                "facts": F(hh_size=2, unearned=1198)},  # net lands at 1000
    ),
    dict(
        id="Q3", topic="benefit formula", kind="benefit",
        text=("A 1-person household's computation comes out to $5. What is "
              "the household actually issued?"),
        choices=[("A", 0, "$0"), ("B", 5, "$5"),
                 ("C", 23, "$23"), ("D", 56, "$56")],
        correct="C",
        rationale=("The minimum benefit is $23 for 1-2 person households. "
                   "Caveat: the calculator applies it unconditionally; "
                   "statute applies it to eligible households only (see Q22)."),
        derive={"kind": "benefit",
                "facts": F(hh_size=1, unearned=1298)},  # raw math -> $0
    ),
    dict(
        id="Q4", topic="benefit formula", kind="diff",
        text=("Holding everything else fixed, raising a household's unearned "
              "income by $100 raises net income by $100. By how much does the "
              "benefit fall?"),
        choices=[("A", 10, "$10"), ("B", 20, "$20"),
                 ("C", 30, "$30"), ("D", 50, "$50")],
        correct="C",
        rationale="Benefit falls by 30% of each added dollar of net income.",
        derive={"kind": "diff",
                "facts_a": F(hh_size=2, unearned=1198),
                "facts_b": F(hh_size=2, unearned=1298)},
    ),
    dict(
        id="Q5", topic="benefit formula", kind="benefit",
        text=("A 3-person household with $0 net income receives the maximum "
              "allotment. How much?"),
        choices=[("A", 766, "$766"), ("B", 973, "$973"),
                 ("C", 535, "$535"), ("D", 672, "$672")],
        correct="A",
        rationale="FY2024 maximum allotment for a 3-person household: $766.",
        derive={"kind": "benefit", "facts": F(hh_size=3)},
    ),
    dict(
        id="Q6", topic="deductions", kind="trace",
        text=("A household member earns $1,000/month. What is the "
              "earned-income disregard?"),
        choices=[("A", 150, "$150"), ("B", 200, "$200"),
                 ("C", 250, "$250"), ("D", 300, "$300")],
        correct="B",
        rationale="The earned-income disregard is 20% of earnings.",
        derive={"kind": "trace", "key": "earn_ded",
                "facts": F(earned=1000)},
    ),
    dict(
        id="Q7", topic="deductions", kind="trace",
        text=("An elderly household member has $120/month in out-of-pocket "
              "medical expenses. What is the medical deduction?"),
        choices=[("A", 120, "$120"), ("B", 85, "$85"),
                 ("C", 35, "$35"), ("D", 0, "$0")],
        correct="B",
        rationale=("Only medical costs over $35 count, for elderly/disabled "
                   "members only: $120 - $35 = $85."),
        derive={"kind": "trace", "key": "med_ded",
                "facts": F(senior_disabled=True, medical_exp=120)},
    ),
    dict(
        id="Q8", topic="deductions", kind="trace",
        text=("An elderly member has exactly $35/month in medical expenses. "
              "What is the medical deduction?"),
        choices=[("A", 35, "$35"), ("B", 0, "$0"),
                 ("C", 70, "$70"), ("D", 17.5, "$17.50")],
        correct="B",
        rationale="The first $35 is excluded, so $35 - $35 = $0.",
        derive={"kind": "trace", "key": "med_ded",
                "facts": F(senior_disabled=True, medical_exp=35)},
    ),
    dict(
        id="Q9", topic="deductions", kind="trace",
        text=("A household with no elderly or disabled members has "
              "$200/month in medical expenses. What is the medical deduction?"),
        choices=[("A", 200, "$200"), ("B", 165, "$165"),
                 ("C", 35, "$35"), ("D", 0, "$0")],
        correct="D",
        rationale="The medical deduction is only available to households with "
                  "an elderly or disabled member.",
        derive={"kind": "trace", "key": "med_ded",
                "facts": F(medical_exp=200)},
    ),
    dict(
        id="Q10", topic="deductions", kind="trace",
        text=("A non-elderly household's shelter costs exceed half its "
              "adjusted income by $699. What is its excess shelter deduction?"),
        choices=[("A", 699, "$699"), ("B", 672, "$672"),
                 ("C", 502, "$502"), ("D", 350, "$350")],
        correct="B",
        rationale=("The excess shelter deduction is capped at $672 for "
                   "households without an elderly/disabled member."),
        derive={"kind": "trace", "key": "excess_shelter",
                "facts": F(earned=1500, shelter=1200)},  # excess = 699
    ),
    dict(
        id="Q11", topic="deductions", kind="trace",
        text=("Same facts as above, but the household includes an elderly "
              "member. What is its excess shelter deduction?"),
        choices=[("A", 672, "$672"), ("B", 699, "$699"),
                 ("C", 700, "$700"), ("D", 502, "$502")],
        correct="B",
        rationale="No shelter cap applies to elderly/disabled households.",
        derive={"kind": "trace", "key": "excess_shelter",
                "facts": F(earned=1500, shelter=1200, senior_disabled=True)},
    ),
    dict(
        id="Q12", topic="deductions", kind="diff",
        text=("A household gains a $200/month dependent care deduction it was "
              "missing. All else equal, its benefit rises by?"),
        choices=[("A", 200, "$200"), ("B", 100, "$100"),
                 ("C", 60, "$60"), ("D", 40, "$40")],
        correct="C",
        rationale=("$200 less net income x 30% = $60 more in benefits."),
        derive={"kind": "diff",
                "facts_a": F(earned=1500, depcare=0),
                "facts_b": F(earned=1500, depcare=200)},
    ),
    dict(
        id="Q13", topic="deductions", kind="trace",
        text="What is the FY2024 standard deduction for a 5-person household?",
        choices=[("A", 198, "$198"), ("B", 208, "$208"),
                 ("C", 244, "$244"), ("D", 279, "$279")],
        correct="C",
        rationale="The standard deduction varies by household size: $244 for "
                  "a 5-person household.",
        derive={"kind": "trace", "key": "std_ded",
                "facts": F(hh_size=5)},
    ),
    dict(
        id="Q14", topic="error direction", kind="direction",
        text=("QC finds $500/month in earned income the household never "
              "reported; the agency had budgeted $0 earnings. Issued benefit "
              "$766; correct benefit $705. What kind of error is this?"),
        choices=[("A", "over", "Over-issuance"),
                 ("B", "under", "Under-issuance"),
                 ("C", "none", "No error"),
                 ("D", "unknown", "Cannot tell from these facts")],
        correct="A",
        rationale=("Issued $766 > correct $705: the household got too much. "
                   "Unreported income is the classic over-issuance driver."),
        derive={"kind": "direction",
                "facts_issued": F(earned=0),
                "facts_true": F(earned=500)},
    ),
    dict(
        id="Q15", topic="error direction", kind="direction",
        text=("The agency failed to grant a $200/month dependent care "
              "deduction. Issued benefit $465; correct benefit $525. What "
              "kind of error is this?"),
        choices=[("A", "over", "Over-issuance"),
                 ("B", "under", "Under-issuance"),
                 ("C", "none", "No error"),
                 ("D", "unknown", "Cannot tell from these facts")],
        correct="B",
        rationale=("Issued $465 < correct $525: the household got too little. "
                   "A missed deduction understates the benefit."),
        derive={"kind": "direction",
                "facts_issued": F(earned=1500, depcare=0),
                "facts_true": F(earned=1500, depcare=200)},
    ),
    dict(
        id="Q16", topic="error direction", kind="direction",
        text=("The agency budgeted $800/month of unearned income the "
              "household never received. Issued $585; correct $766. What kind "
              "of error is this?"),
        choices=[("A", "over", "Over-issuance"),
                 ("B", "under", "Under-issuance"),
                 ("C", "none", "No error"),
                 ("D", "unknown", "Cannot tell from these facts")],
        correct="B",
        rationale=("Overstating income understates the benefit: issued $585 < "
                   "correct $766, so the household got too little."),
        derive={"kind": "direction",
                "facts_issued": F(unearned=800),
                "facts_true": F(unearned=0)},
    ),
    dict(
        id="Q17", topic="error direction", kind="direction_supplied",
        text=("An elderly household's true excess shelter deduction was "
              "$699, but the agency applied the $672 cap. Issued $667; "
              "correct $675. What kind of error is this?"),
        choices=[("A", "over", "Over-issuance"),
                 ("B", "under", "Under-issuance"),
                 ("C", "none", "No error"),
                 ("D", "unknown", "Cannot tell from these facts")],
        correct="B",
        rationale=("Misapplying the cap to an elderly household understates "
                   "the deduction: issued $667 < correct $675."),
        derive={"kind": "direction_supplied", "issued": 667,
                "facts_true": F(earned=1500, shelter=1200,
                                senior_disabled=True)},
    ),
    dict(
        id="Q18", topic="variance coding", kind="codebook",
        text=("A reviewer finds wages the household never reported. Which "
              "element/nature codes describe this variance?"),
        choices=[("A", "311/35", "Element 311 / nature 35"),
                 ("B", "321/35", "Element 321 / nature 35"),
                 ("C", "311/37", "Element 311 / nature 37"),
                 ("D", "331/35", "Element 331 / nature 35")],
        correct="A",
        rationale=("Element 311 = wages and salaries; nature 35 = unreported "
                   "source of income."),
        derive={"kind": "codebook", "element": 311, "nature": 35,
                "element_label": "Wages and salaries",
                "nature_label": "Unreported source of income"},
    ),
    dict(
        id="Q19", topic="variance coding", kind="codebook",
        text=("The agency omitted a dependent care deduction the household "
              "qualified for. Which element/nature codes describe this "
              "variance?"),
        choices=[("A", "323/52", "Element 323 / nature 52"),
                 ("B", "323/53", "Element 323 / nature 53"),
                 ("C", "363/52", "Element 363 / nature 52"),
                 ("D", "321/52", "Element 321 / nature 52")],
        correct="A",
        rationale=("Element 323 = dependent care deduction; nature 52 = "
                   "deduction that should have been included but was not."),
        derive={"kind": "codebook", "element": 323, "nature": 52,
                "element_label": "Dependent care deduction",
                "nature_label": ("Deduction that should have been included "
                                 "was not")},
    ),
    dict(
        id="Q20", topic="variance coding", kind="codebook",
        text=("The agency granted a medical expense deduction to a household "
              "with no elderly or disabled member. Which element/nature codes "
              "describe this variance?"),
        choices=[("A", "365/53", "Element 365 / nature 53"),
                 ("B", "365/52", "Element 365 / nature 52"),
                 ("C", "363/53", "Element 363 / nature 53"),
                 ("D", "365/56", "Element 365 / nature 56")],
        correct="A",
        rationale=("Element 365 = medical expense deductions; nature 53 = "
                   "deduction included that should not have been."),
        derive={"kind": "codebook", "element": 365, "nature": 53,
                "element_label": "Medical expense deductions",
                "nature_label": "Deduction included that should not have been"},
    ),
    dict(
        id="Q21", topic="scope probe", kind="scope",
        text=("A household pays $300/month in court-ordered child support. "
              "What child-support deduction does the benefit calculator grant?"),
        choices=[("A", 300, "$300 (the full amount)"),
                 ("B", 150, "$150"),
                 ("C", "none", "$0 - the calculator has no child-support "
                               "deduction")],
        correct="C",
        rationale=("Out of oracle scope: element 366 (child support) exists "
                   "in the codebook buckets, but benefit.py implements no "
                   "child-support deduction. Real statute allows one."),
        derive={"kind": "scope", "extra_key": "childsupport",
                "facts": F(unearned=1000)},
    ),
    dict(
        id="Q22", topic="scope probe", kind="benefit",
        text=("A 1-person household's net income is above the FY2024 net "
              "limit, so it is ineligible; the raw benefit math comes out to "
              "$0. Under federal statute, what benefit is issued?"),
        choices=[("A", 0, "$0 - ineligible households get no benefit"),
                 ("B", 23, "$23 (minimum benefit)"),
                 ("C", 291, "$291"), ("D", 56, "$56")],
        correct="A",
        rationale=("Statute: failing the net income test means ineligible, "
                   "$0. The calculator applies the $23 minimum "
                   "unconditionally and has no eligibility screen - a known "
                   "harness approximation (see benefit.py comment)."),
        derive={"kind": "benefit",
                "facts": F(hh_size=1, unearned=1500)},  # net 1302 > limit 1215
    ),
]


def derive_answer(q):
    """Derive the oracle's answer for one question. Returns (value, detail)."""
    d = q["derive"]
    kind = d["kind"]
    if kind == "benefit":
        v = benefit.compute(d["facts"])["benefit"]
        return v, f"benefit={v}"
    if kind == "trace":
        v = benefit.compute(d["facts"])[d["key"]]
        return v, f"{d['key']}={v}"
    if kind == "diff":
        # Magnitude of the benefit change; the question stems ask "by how
        # much does the benefit fall/rise", so the sign is framing, not math.
        a = benefit.compute(d["facts_a"])["benefit"]
        b = benefit.compute(d["facts_b"])["benefit"]
        return abs(b - a), f"benefit_b={b} benefit_a={a}"
    if kind == "direction":
        issued = benefit.compute(d["facts_issued"])["benefit"]
        true = benefit.compute(d["facts_true"])["benefit"]
        return _dir(issued, true), f"issued={issued} true={true}"
    if kind == "direction_supplied":
        true = benefit.compute(d["facts_true"])["benefit"]
        return _dir(d["issued"], true), f"issued={d['issued']} true={true}"
    if kind == "codebook":
        el = codebook.ELEMENT_LABELS[d["element"]]
        na = codebook.NATURE_LABELS[d["nature"]]
        ok = (el == d["element_label"]) and (na == d["nature_label"])
        return f"{d['element']}/{d['nature']}" if ok else "MISMATCH", (
            f"element_label='{el}' nature_label='{na}'")
    if kind == "scope":
        base = benefit.compute(d["facts"])["benefit"]
        facts2 = dict(d["facts"]); facts2[d["extra_key"]] = 300
        with_extra = benefit.compute(facts2)["benefit"]
        if base == with_extra:
            return "none", (f"benefit unchanged at {base} when "
                            f"'{d['extra_key']}' fact added")
        return "GRANTED", f"benefit changed {base} -> {with_extra}"
    raise ValueError(f"unknown derive kind {kind}")


def match_value(derived, choice_value):
    if isinstance(choice_value, (int, float)) and isinstance(
            derived, (int, float)):
        return round(float(derived), 2) == round(float(choice_value), 2)
    return derived == choice_value


def main():
    repo = Path(__file__).resolve().parent.parent
    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                         capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--short"], cwd=repo,
                            capture_output=True, text=True).stdout.strip()

    print("=== exp41 policy-QA bridge ===")
    print(f"git rev: {rev}")
    print("git status --short:")
    print(status if status else "  (clean)")
    print()

    rows = []
    for q in QUESTIONS:
        derived, detail = derive_answer(q)
        letter = None
        for lab, val, _disp in q["choices"]:
            if match_value(derived, val):
                letter = lab
                break
        ok = (letter == q["correct"])
        rows.append((q["id"], q["topic"], q["kind"], str(derived), detail,
                     letter or "?", q["correct"], ok))

    print(f"{'Q':<5}{'topic':<16}{'oracle':<10}{'derived':<10}"
          f"{'match->':<9}{'label':<7}ok")
    n_ok = 0
    for r in rows:
        qid, topic, kind, derived, _det, letter, correct, ok = r
        n_ok += ok
        print(f"{qid:<5}{topic:<16}{kind:<10}{derived:<10}"
              f"{letter+'->':<9}{correct:<7}{'OK' if ok else 'FAIL'}")
    print()
    print(f"Accuracy: {n_ok}/{len(rows)} = {n_ok / len(rows):.3f}")
    print()
    print("--- per-question oracle detail ---")
    for q, r in zip(QUESTIONS, rows):
        _qid, _t, _k, _der, detail, letter, correct, ok = r
        print(f"{q['id']}: derived_letter={letter} labeled={correct} "
              f"{'OK' if ok else 'FAIL'} | {detail}")
        if not ok:
            print(f"    RATIONALE: {q['rationale']}")

    in_scope = [r for r, q in zip(rows, QUESTIONS)
                if q["topic"] != "scope probe" and q["id"] != "Q22"]
    print()
    print(f"In-scope accuracy (excl. Q21/Q22 probes): "
          f"{sum(r[7] for r in in_scope)}/{len(in_scope)}")


if __name__ == "__main__":
    main()
