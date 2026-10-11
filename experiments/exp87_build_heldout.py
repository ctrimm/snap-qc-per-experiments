"""Exp87 — build a held-out SNAP/CalFresh question set from the rulebook (not from the Cornell quiz).

Three parts, every question dated (as_of) and tied to the citation that answers it:
  tables  FNS cost-of-living figures (max allotment, standard deduction, shelter cap, income limits,
          minimum allotment, asset limits) for a date in FY2024-FY2027. Distractors are mostly the same
          figure from other fiscal years, so a model or retriever using the wrong year's table is wrong.
  compute monthly benefit for a described household, gold from state-policy-docs' calculator
          (7 CFR 273.10(e)); distractors from common mistakes (wrong year's tables, skipping the 20%
          earned income deduction, no shelter cap, ignoring the elderly/disabled rules).
  rules   hand-written from cited passages (exp87_rules.json), each with an evidence phrase that must
          appear in the cited text on that date (checked here); includes pre/post H.R. 1 pairs.
Output: experiments/exp87_heldout.jsonl. Seeded (87). Our own data: may be committed and used for tuning.
After building, run audit_mcq_contamination.py over it to confirm no overlap with the Cornell quiz.
"""
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPD = HERE.parents[1] / "state-policy-docs"
sys.path.insert(0, str(SPD))
from mcp_server import benefit_calc as bc  # noqa: E402
from mcp_server.policy_index import get_index, resolve_citation  # noqa: E402

rng = random.Random(87)
FYS = [2024, 2025, 2026, 2027]
LET = "ABCDE"
REGIONS = {"48": "one of the 48 contiguous states or DC", "alaska": "urban Alaska", "hawaii": "Hawaii",
           "guam": "Guam", "virgin islands": "the U.S. Virgin Islands"}


def fy_date(fy):
    start = date(fy - 1, 10, 1)
    return start + timedelta(days=rng.randrange(0, 365))


def money(v):
    return f"${v:,.2f}" if isinstance(v, float) and not float(v).is_integer() else f"${int(v):,}"


def mcq(stem, correct, distractors):
    opts = [correct]
    for d in distractors:
        if d not in opts:
            opts.append(d)
    k = 1
    while len(opts) < 5:  # pad with near values when years coincide
        cand = correct + 7 * k if isinstance(correct, (int, float)) else None
        k += 1
        if cand is not None and cand not in opts and cand > 0:
            opts.append(cand)
    opts = opts[:5]
    rng.shuffle(opts)
    ans = LET[opts.index(correct)]
    body = stem + "\n" + "\n".join(f"{LET[i]}. {money(o) if isinstance(o, (int, float)) else o}" for i, o in enumerate(opts))
    return body, ans


def table_val(fy, kind, title_word, region, size=None, col_region=None):
    t = bc.load_tables(fy)[kind]
    rows = bc._find(t, title_word)
    col = bc._col(rows[0], col_region or region, "urban")
    if size is None:
        return bc._money(rows[1][col])
    return bc._by_size(rows, col, size)[0]


def tables_part(n):
    items = []
    specs = [
        ("maximum monthly allotment", "maximum-allotments-deductions", "maximum monthly allotment",
         "the maximum monthly SNAP allotment for a household of {s} in {r}", True, list(REGIONS)),
        ("standard deduction", "maximum-allotments-deductions", "standard deduction",
         "the SNAP standard deduction for a household of {s} in {r}", True, ["48", "alaska", "hawaii", "guam"]),
        ("excess shelter cap", "maximum-allotments-deductions", "excess shelter",
         "the maximum excess shelter deduction for a household without an elderly or disabled member in {r}", False,
         ["48", "alaska", "hawaii"]),
        ("gross income limit", "income-eligibility-standards", "130%",
         "the SNAP gross monthly income limit (130% of poverty) for a household of {s} in {r}", True, ["48", "alaska", "hawaii"]),
        ("net income limit", "income-eligibility-standards", "net monthly",
         "the SNAP net monthly income limit (100% of poverty) for a household of {s} in {r}", True, ["48", "alaska", "hawaii"]),
        ("minimum allotment", "minimum-allotments", "minimum",
         "the minimum monthly SNAP allotment for an eligible one- or two-person household in {r}", False, ["48"]),
    ]
    paths = {"maximum-allotments-deductions": "maximum-allotments-deductions", "income-eligibility-standards": "income-eligibility-standards",
             "minimum-allotments": "minimum-allotments"}
    per = n // len(specs)
    for name, kind, word, phrase, sized, regions in specs:
        for _ in range(per):
            fy = rng.choice(FYS); d = fy_date(fy); reg = rng.choice(regions)
            ie = kind == "income-eligibility-standards"
            col_reg = ("48" if reg in ("guam", "virgin islands") else reg) if ie else reg
            s = rng.randint(1, 8) if sized else None
            if name == "standard deduction":
                s = rng.randint(1, 6)
            val = lambda f, size=s: table_val(f, kind, word, reg, size, col_reg)
            correct = val(fy)
            distract = [val(f) for f in FYS if f != fy]
            if sized:
                distract.append(val(fy, s + 1 if s < 6 else s - 1))
            stem = f"As of {d:%B %-d, %Y}, what is {phrase.format(s=s, r=REGIONS[reg])}?"
            body, ans = mcq(stem, correct, distract)
            items.append({"category": f"table: {name}", "question": body, "answer": ans, "as_of": d.isoformat(),
                          "citation": f"FNS SNAP cost-of-living tables FY{fy}",
                          "gold_paths": [f"benefits/us/snap-cola-fy{fy}-{paths[kind]}.md"]})
    return items


def compute_part(n):
    items, tries = [], 0
    while len(items) < n and tries < n * 20:
        tries += 1
        fy = rng.choice(FYS); d = fy_date(fy)
        size = rng.randint(1, 6)
        ed = rng.random() < 0.3
        earned = rng.choice([0, 0, rng.randrange(400, 3200, 25)])
        unearned = rng.choice([0, rng.randrange(200, 1600, 10)])
        rent = rng.randrange(300, 1900, 25)
        sua = rng.choice([350, 450, 550, 650])
        med = rng.randrange(50, 400, 5) if ed else 0
        args = dict(household_size=size, earned_income=earned, unearned_income=unearned, shelter_costs=rent,
                    utility_allowance=sua, medical_expenses=med, elderly_or_disabled=ed)
        r = bc.calculate(as_of=d.isoformat(), **args)
        if not r["eligible"] or r["monthly_benefit"] <= 0:
            continue
        correct = r["monthly_benefit"]
        variants = [
            bc.calculate(as_of=fy_date(fy - 1 if fy > 2024 else fy + 1).isoformat(), **args)["monthly_benefit"],
            bc.calculate(as_of=d.isoformat(), **{**args, "earned_income": 0, "unearned_income": earned + unearned})["monthly_benefit"],
            bc.calculate(as_of=d.isoformat(), **{**args, "elderly_or_disabled": not ed,
                                                 "medical_expenses": med or 120})["monthly_benefit"],
            max(0, correct - 30), correct + 25,
        ]
        who = ("including a member who is 60 or older" if ed else "with no elderly or disabled members")
        inc = []
        if earned:
            inc.append(f"{money(earned)} a month in gross wages")
        if unearned:
            inc.append(f"{money(unearned)} a month in unearned income")
        stem = (f"As of {d:%B %-d, %Y}, a SNAP household of {size} in one of the 48 contiguous states, {who}, has "
                f"{' and '.join(inc) or 'no income'}. It pays {money(rent)} a month in rent; the state's standard utility "
                f"allowance is {money(sua)}" + (f"; the elderly member has {money(med)} a month in unreimbursed medical costs" if ed else "")
                + ". It has no dependent care or child support costs, its resources are under the limit, and the state has "
                  "no broad-based categorical eligibility. Using the federal SNAP computation, what is its monthly benefit?")
        body, ans = mcq(stem, correct, variants)
        items.append({"category": "compute: monthly benefit", "question": body, "answer": ans, "as_of": d.isoformat(),
                      "citation": "7 CFR 273.10(e)", "gold_paths": ["benefits/us/ecfr-7-cfr-273-10.md",
                                                                  f"benefits/us/snap-cola-fy{fy}-maximum-allotments-deductions.md"],
                      "inputs": args})
    return items


def rules_part():
    spec = json.loads((HERE / "exp87_rules.json").read_text())
    ix = get_index()
    items, problems = [], []
    for k, q in enumerate(spec["questions"]):
        if q.get("path"):  # state letters: no citation syntax; check the document itself
            d = ix.docs[ix.by_path[q["path"]]]
            r = {"citation": q["citation"], "docs": [q["path"]], "text": d.body}
        else:
            r = resolve_citation(ix, q["citation"], date.fromisoformat(q["as_of"]))
        if "error" in r:
            problems.append(f"{k}: {q['citation']}: {r['error']}"); continue
        if q["evidence"].lower() not in " ".join(r["text"].split()).lower():
            problems.append(f"{k}: evidence not in {q['citation']} on {q['as_of']}: {q['evidence'][:60]!r}"); continue
        opts = q["options"][:]
        correct = opts[0]
        rng.shuffle(opts)
        ans = LET[opts.index(correct)]
        d = date.fromisoformat(q["as_of"])
        body = f"As of {d:%B %-d, %Y}: {q['stem']}\n" + "\n".join(f"{LET[i]}. {o}" for i, o in enumerate(opts))
        items.append({"category": f"rule: {q['topic']}", "question": body, "answer": ans, "as_of": q["as_of"],
                      "citation": r["citation"], "gold_paths": r["docs"]})
    return items, problems


def main():
    rules, problems = rules_part()
    for p in problems:
        print("PROBLEM", p)
    if problems:
        sys.exit(1)
    items = tables_part(120) + compute_part(80) + rules
    for i, it in enumerate(items):
        it["id"] = f"h{i:03d}"
    out = HERE / "exp87_heldout.jsonl"
    out.write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items))
    from collections import Counter
    print(len(items), "questions;", dict(Counter(it["category"].split(":")[0] for it in items)),
          "answer letters", dict(sorted(Counter(it["answer"] for it in items).items())))


if __name__ == "__main__":
    main()
