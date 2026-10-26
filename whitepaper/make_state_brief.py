"""Write a state brief (Markdown) whose every figure comes from the committed results; the narrative is per state.

    python3 whitepaper/make_state_brief.py PA NY TX SD UT ID WY

Model figures are the leak-free rebuild (exp107; SNAPQC_FEATURES=leakfree, the default): exp83_leakfree (held-out),
exp107_timesplit (later-years test), exp79_leakfree (underpayment ranker), exp93_leakfree +
experiments/cost_share_replicate.py (FY2025 rate, cost share). Sample sizes from exp68; adopted variants from exp80/82.
Error patterns come straight from the FY2020-24 QC public-use files (unweighted; error cases = STATUS 2 or 3); the
narrative text carries only such data facts, never model figures.
"""
import csv
import glob
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT / "experiments"
RAW = ROOT.parent / "snap-qc-data/raw"
sys.path.insert(0, str(ROOT / "src"))
from synth.codebook import ELEMENT_LABELS  # noqa: E402

load = lambda f: json.loads((EXP / f).read_text())  # noqa: E731
E83, E93 = load("exp83_leakfree_results.json"), load("exp93_leakfree_results.json")["states"]
E68 = {r["state"]: r for r in load("exp68_results.json")}  # sample sizes only
E79 = {r["state"]: r for r in load("exp79_leakfree_results.json")}
ADOPT = {**load("exp80_results.json"), **load("exp82_results.json")}
TS = {s: r["time_split"] for s, r in load("exp107_timesplit_results.json").items()}
E93_MEAS = load("exp93_leakfree_results.json")["measured"]
MED20 = sorted(v["top20"]["lift"] for v in E83.values())[len(E83) // 2]
rank = lambda d: {s: i + 1 for i, s in enumerate(sorted(d, key=lambda s: -d[s]))}  # noqa: E731
R20 = rank({s: v["top20"]["lift"] for s, v in E83.items()})
R10 = rank({s: v["top10"]["lift"] for s, v in E83.items()})
RTS = rank(TS)
RPER = {s: i + 1 for i, s in enumerate(sorted(E93, key=lambda s: E93[s]["per_fy2025"]))}
CODES = {"PA": "42", "NY": "36", "TX": "48", "SD": "46", "UT": "49", "ID": "16", "WY": "56"}
NAMES = {"PA": "Pennsylvania", "NY": "New York", "TX": "Texas", "SD": "South Dakota", "UT": "Utah", "ID": "Idaho", "WY": "Wyoming"}
FILES = {st: f"{st.lower()}_pilot_whitepaper.md" for st in CODES} | {"WY": "wy_state_brief.md"}
CORRECTED = ("> **Corrected October 26, 2026.** The October 23 version of this brief overstated the tool's results. Its models "
             "used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC "
             "file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure "
             "here comes from the leak-free rebuild (experiment 107). Figures computed directly from the QC data (error rates, "
             "error patterns, caseload shares) were not affected.")
STATE_CARDS = {"PA": "88%", "NY": "86%"}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def patterns():
    st = {k: {"n": 0, "err": 0, "over": 0, "under": 0, "od": 0.0, "ud": 0.0, "el": Counter(), "eln": Counter(),
              "nat": Counter(), "amt0": 0} for k in [*CODES, "US"]}
    back = {v: k for k, v in CODES.items()}
    for fy in range(2020, 2025):
        for r in csv.DictReader(open(glob.glob(str(RAW / f"qcfy{fy}_csv/*.csv"))[0], newline="", encoding="latin-1")):
            for k in filter(None, (back.get(r["STATE"].strip()), "US")):
                d = st[k]
                d["n"] += 1
                s, a = r["STATUS"].strip(), num(r["AMTERR"])
                if s not in ("2", "3"):
                    continue
                d["err"] += 1
                if s == "2":
                    d["over"] += 1
                    d["od"] += a
                else:
                    d["under"] += 1
                    d["ud"] += a
                e = int(num(r["ELEMENT1"]))
                d["el"][e] += a
                d["eln"][e] += 1
                d["nat"][int(num(r["NATURE1"]))] += 1
                d["amt0"] += num(r["AMOUNT1"]) == 0
    return st


def hypothetical(s, per):
    """Cost-share scenario for a state at a hypothetical error rate, from cost_share_replicate.py (central scenario)."""
    out = cost_lines(s, ("--per", per))
    head = out.split("\n")[0]
    cen = [ln for ln in out.split("\n") if "central" in ln][0]
    return {"share": head.split("state share ")[1].split(" of")[0], "cost": head.split("= ")[1].split(" a year")[0],
            "after": cen.split("(1 + c x m) = ")[1].split(" ->")[0], "random": cen.split("random reviews: ")[1].split(",")[0]}


def thresholds(s, name):
    """Monthly review share needed to cross each lower bracket line, central scenario's f and m, the state's floor-on
    top-10% lift (as exp93's central scenario)."""
    per = E93[s]["per_fy2025"]; L = E93_MEAS[s]["top10"]["floor_lift"]
    out = []
    for line, sh in ((10, "10%"), (8, "5%"), (6, "no")):
        if per >= line:
            R_ = (per / line - 1) / (6 * L * 0.8)
            out.append(f"{line}% at about **{100 * R_:.1f}%** of cases reviewed a month ({sh} share)")
    return f"**The thresholds.** Under the central scenario's other assumptions, {name} crosses " + "; ".join(out) + "." if out else ""


def pct(a, b):
    return 100 * a / b


def cost_lines(s, extra=()):
    out = subprocess.run(["python3", str(EXP / "cost_share_replicate.py"), "--state", s, *extra],
                         capture_output=True, text=True, check=True).stdout
    return out


NARRATIVE = {
    "PA": {
        "lede": "Pennsylvania's FY2025 payment error rate was 9.21%. Under the H.R. 1 cost-sharing rules, that rate means the state would pay 10% of its SNAP benefit costs from FY2028, about **$418 million a year**. This brief shows what a case-ranking tool, built and tested on Pennsylvania's federal QC records, could do about that.",
        "pattern": """**Pennsylvania's distinctive problem is the shelter deduction.**
- **Shelter:** it is the most common error by far (45% of error cases, national 31%), and carries 24% of error dollars (national 16%).
- **Wages:** wage errors are less frequent but larger, and carry the most dollars (37%).
- **Ranking:** that's why ranking by the chance of an error alone does poorly; the frequent errors are small. The tool ranks by expected dollars instead.
- **Arithmetic:** benefit arithmetic errors are almost nonexistent (0.1% of error cases), so errors come from the facts entered.""",
        "cards": "Each flagged case can come with a short card saying why it was flagged and which parts of the case to check first. In Pennsylvania the card's top three \"check first\" items included the real error for 88% of flagged errors (exp65). That figure was measured before experiment 106, on a model using the same reviewer-recorded fields, and has not been rechecked.",
        "pilot_extra": "",
        "limit_extra": "",
    },
    "NY": {
        "lede": "New York's FY2025 payment error rate was 13.18%. Under the H.R. 1 cost-sharing rules that is the top bracket: from FY2028 the state would pay 15% of its SNAP benefit costs, about **$1.08 billion a year**. This brief shows what a case-ranking tool, built and tested on New York's federal QC records, could do about that.",
        "pattern": """**New York's distinctive problem is timing.**
- **Timing:** nearly two-thirds of its errors (63%) carry the reporting or timing code, half again the national share (42%). The facts changed, usually income or household members, and the case wasn't updated in time.
- **Where the dollars are:** wages carry the most error dollars (39%). Social Security, unemployment benefits and household composition each carry more than their national share.""",
        "cards": "Each flagged case can come with a short card saying why it was flagged and which parts of the case to check first. In New York the card's top three \"check first\" items included the real error for 86% of flagged errors (exp65). That figure was measured before experiment 106, on a model using the same reviewer-recorded fields, and has not been rechecked.",
        "pilot_extra": "Record when the underlying change happened: timing errors are New York's main problem.",
        "limit_extra": "",
    },
    "WY": {
        "lede": "Wyoming's FY2025 payment error rate was 3.96%, the third lowest of 53 jurisdictions (after South Dakota and Idaho) and below the 6% line where H.R. 1 cost sharing begins. Wyoming owes nothing under FY2028 rules at that rate. So for Wyoming, a case-ranking tool is about staying below 6%, finding households that are being underpaid, and using a small review staff well.",
        "pattern": """**Wyoming's errors run both ways.**
- **Underpayments:** 54% of Wyoming's error dollars are underpayments, nearly twice the national share (28%). Over- and underpayment cases are evenly split.
- **Medical deductions:** they carry 12% of its error dollars and 17% of its errors, about four times the national shares. That points to verifying and updating medical expenses as a specific area to review.
- **Few cases:** five years of QC data hold about 1,200 Wyoming cases and about 400 errors, so patterns here are less certain than in large states.""",
        "cards": "\"Check first\" coverage hasn't been measured on Wyoming cases.",
        "pilot_extra": "Score quarterly rather than monthly at first, and run the underpayment queue alongside the main one.",
        "limit_extra": "- **Small sample.** About 1,200 QC cases and 300 held-out cases; check forecasts against Wyoming's own reviews before quoting them.",
    },
    "TX": {
        "lede": "Texas's FY2025 payment error rate was 9.34%. Under the H.R. 1 cost-sharing rules, that rate means the state would pay 10% of its SNAP benefit costs from FY2028, about **$685 million a year**. This brief shows what a case-ranking tool, built and tested on Texas's federal QC records, could do about that.",
        "pattern": """**Texas's distinctive features are in how errors are coded.**
- **Coded "other":** nearly a quarter of its errors carry the "other" nature code (99), about five times the national share. Timing-coded errors run at half the national share.
- **No per-error dollar amounts:** Texas records no per-error dollar amount on virtually every error case (national: about half). The case's total error dollars are still recorded, so the ranker works. But tools that learn *where* in a case the error sits have to learn from reviewers' findings instead (see *Flag cards*).
- **A balanced split:** over- and underpayment cases are evenly balanced, and underpayments are 41% of error dollars (national 28%).""",
        "cards": "Texas's QC records carry no per-error dollar amounts, so the \"check first\" model can't be trained from them alone. In exp63, a where-to-look model beat generic advice after about 100 labelled error cases. A pilot's reviewer findings could supply those in two to four months. Until then, cards can show why a case was flagged and the generic checklist.",
        "pilot_extra": "Record, for each error found, which part of the case it was in: that builds the training data the \"check first\" cards need.",
        "limit_extra": "- **Coding practice.** Texas's heavy use of the \"other\" nature code and its missing per-error dollar amounts make error-type analysis less informative than in most states.",
    },
    "SD": {
        "lede": "South Dakota's FY2025 payment error rate was 2.47%, the lowest of 53 jurisdictions and far below the 6% line where H.R. 1 cost sharing begins. South Dakota owes nothing under FY2028 rules at that rate. For South Dakota the tool is about staying there, finding the few errors there are efficiently, and finding underpayments.",
        "pattern": """**South Dakota's errors are rarer, smaller and mostly about timing.**
- **Fewer errors:** only about a quarter of reviewed cases have any error, against 38% nationally.
- **Timing:** three in four errors carry the reporting or timing code (national 42%).
- **Wages:** wage errors carry nearly half the error dollars.
- **Small amounts:** the median error is $18, against $28 nationally.
- **A balanced split:** over- and underpayment cases are evenly balanced.""",
        "cards": "Flag-card Rules lines were tested at scale on fresh South Dakota, Idaho and Utah cards (exp97): the small model's citations matched the large model's 100% of the time, and every citation resolved. \"Check first\" coverage hasn't been measured on South Dakota cases.",
        "pilot_extra": "With so few errors, a quarterly ranking may be enough. Track whether the top of the queue finds errors sooner than current selection.",
        "limit_extra": "- **Few errors to learn from.** Five years of South Dakota QC data hold about 600 error cases, so check forecasts against the state's own reviews before quoting them.",
    },
    "UT": {
        "lede": "Utah's FY2025 payment error rate was 5.54%, the eighth lowest of 53 jurisdictions and just under the 6% line where H.R. 1 cost sharing begins. Utah owes nothing at that rate. But it is the closest of the pilot states to the line: a rise of half a point would cost about $19 million a year.",
        "pattern": """**Utah's errors center on the shelter deduction.**
- **Shelter:** shelter-deduction errors are the most common (32% of error cases, national 31%) and carry 22% of error dollars (national 16%).
- **Wages:** wage errors carry 26%.
- **Child support and self-employment:** child support received and self-employment income each carry more than their national share of dollars.
- **Direction:** overpayment cases outnumber underpayment cases about 4 to 3, and underpayments are 37% of error dollars.""",
        "cards": "Flag-card Rules lines were tested at scale on fresh Utah, Idaho and South Dakota cards (exp97): the small model's citations matched the large model's 100% of the time, and every citation resolved. \"Check first\" coverage hasn't been measured on Utah cases.",
        "pilot_extra": "Because Utah sits just under 6%, the pilot's main readout is whether ranked reviews move the rate, so measure how long found errors had lasted and the share actually fixed.",
        "limit_extra": "",
    },
    "ID": {
        "lede": "Idaho's FY2025 payment error rate was 3.85%, the second lowest of 53 jurisdictions and below the 6% line where H.R. 1 cost sharing begins. Idaho owes nothing under FY2028 rules at that rate. For Idaho the tool is about staying below the line and using a small review staff well.",
        "pattern": """**Idaho's errors are dominated by the shelter deduction and by timing.**
- **Shelter:** shelter-deduction errors are 43% of error cases (national 31%).
- **Timing:** 64% of errors carry the reporting or timing code (national 42%).
- **Social Security:** Social Security (RSDI) income carries 12% of error dollars, about twice the national share.
- **Small amounts:** the median error is $17, against $28 nationally.""",
        "cards": "Idaho is where the flag cards have been tested most outside Pennsylvania and New York:\n- **Odds:** the cards' \"N in 10\" odds were recalibrated on Idaho cases (exp74).\n- **Rules line:** tested at scale on fresh Idaho, Utah and South Dakota cards (exp97), with 100% agreement with the large model.\n- **Where to look:** that model beat generic advice in Idaho after about 100 labelled error cases (exp63).\n\nThe odds and where-to-look results were measured before experiment 106, on models using the same reviewer-recorded fields, and have not been rechecked.",
        "pilot_extra": "",
        "limit_extra": "- **Small errors.** Idaho's errors are small (median $17), so dollars found per review hour are low even when the lift is good. The case for a pilot rests on accuracy and staying below 6% more than on dollars.",
    },
}


def brief(s, P):
    d, us, v, a = P[s], P["US"], E83[s], ADOPT[s]
    name, n = NAMES[s], NARRATIVE[s]
    e68, e79, e93 = E68[s], E79[s], E93[s]
    fl = v["fairness"]["floor_lift"]
    cost = 100 * (1 - fl / v["top20"]["lift"])
    b, f = v["fairness"]["baseline_ratio"], v["fairness"]["floor_ratio"]
    eld = lambda x: [(ELEMENT_LABELS.get(e, f"code {e}"), pct(c, sum(x.values()))) for e, c in x.most_common(3)]  # noqa: E731
    ed, en = eld(d["el"]), [(ELEMENT_LABELS.get(e, f"code {e}"), pct(c, d["err"])) for e, c in d["eln"].most_common(3)]
    ud = pct(d["ud"], d["od"] + d["ud"])
    usd = pct(us["ud"], us["od"] + us["ud"])
    sc = e93["scenarios"]
    owes = e93["cost_share_now"] > 0
    ev = lambda x: f"{abs(round(100 * (x - 1)))}% {'over' if x > 1 else 'under'}" if abs(x - 1) >= 0.005 else "within 1%"  # noqa: E731
    evs = lambda x: (f"{abs(round(100 * (x - 1)))}% {'above' if x > 1 else 'below'} actual" if abs(x - 1) >= 0.005 else "within 1% of actual")  # noqa: E731
    holdout_pct = round(100 * e68["n_holdout"] / e68["n_rows"])
    L = []
    L += [f"# Finding SNAP Payment Errors Faster in {name}", "", "**October 26, 2026 (corrected; first version October 23) · State brief · Cory Trimm**", "", CORRECTED, "", "## Summary", "", n["lede"], ""]
    L += [f"- **It finds {v['top20']['lift']:.1f} times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **${v['top20']['per_hour_$']:.0f} per review hour against ${v['top20']['random_per_hour_$']:.0f}**. The top 10% finds {v['top10']['lift']:.1f} times.",
          f"- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a {TS[s]:.1f}× edge. Expected error dollars for the top fifth of the queue were {evs(v['top20']['expected_over_actual'])}.",
          f"- **It's fair by design.** Ranking purely by dollars would review elderly households at {b['elderly']:.2f} of their share of error cases. A floor brings that to {f['elderly']:.2f}, " +
          (f"at a cost of about {round(cost)}% of the lift ({v['top20']['lift']:.1f}× → {fl:.1f}×)." if cost >= 0.5 else "with no measurable cost to the lift."),
          f"- **Underpayments:** {round(ud)}% of {name}'s error dollars are households paid too little (national {round(usd)}%)."]
    if owes:
        L.append(f"- **Cost share:** in the central scenario (2% of cases reviewed a month, about {sc['central']['reviews_per_month']:,} reviews and {sc['central']['fte']:.0f} FTEs), the rate falls to {sc['central']['ranker']['per']:.2f}%, avoiding about **${sc['central']['ranker']['saving_vs_now'] / 1e6:,.0f} million a year**. Random reviews of the same volume leave it at {sc['central']['random']['per']:.2f}%.")
    else:
        hyp = {p: hypothetical(s, p) for p in ("6.5", "8.5")}
        back = [p for p, h in hyp.items() if float(h["after"].rstrip("%")) < 6]
        L.append(f"- **Cheap insurance:** at its current rate {name} owes nothing. In the model, about {sc['central']['reviews_per_month']:,} ranked reviews a month ({sc['central']['fte']:.1f} FTEs) would bring "
                 + (" and ".join(f"a rate of {p}%" for p in back) + " back under 6%" if back else "neither a 6.5% nor an 8.5% rate back under 6%") + " (see *FY2028 cost share*).")
    L += ["", "**Recommendation:** a shadow pilot. Score the active caseload, have reviewers work the top of the queue alongside current selection with the fairness floor on, and compare the dollars found with the tool's forecast.", ""]
    L += [f"## {name}'s errors", "", f"Federal QC public-use files, FY2020–2024: {d['n']:,} reviewed {name} cases. Shares are of cases with any error found, including small ones, and are unweighted:", "",
          f"| | {name} | National |", "|---|---|---|",
          f"| Reviewed cases with an error found | {pct(d['err'], d['n']):.1f}% | {pct(us['err'], us['n']):.1f}% |",
          f"| Error cases: over / under | {d['over']} / {d['under']} | {round(pct(us['over'], us['err']))}% / {round(pct(us['under'], us['err']))}% |",
          f"| Error dollars that are underpayments | {round(ud)}% | {round(usd)}% |",
          f"| Largest shares of error dollars | " + ", ".join(f"{k} {x:.0f}%" for k, x in ed) + " | " + ", ".join(f"{k} {x:.0f}%" for k, x in eld(us["el"])) + " |",
          f"| Most frequent errors (share of error cases) | " + ", ".join(f"{k} {x:.0f}%" for k, x in en) + " | " + ", ".join(f"{k} {x:.0f}%" for k, x in [(ELEMENT_LABELS.get(e, e), pct(c, us['err'])) for e, c in us['eln'].most_common(3)]) + " |",
          f"| Errors coded as reporting or timing issues (nature code 97) | {pct(d['nat'][97], d['err']):.0f}% | {pct(us['nat'][97], us['err']):.0f}% |",
          f"| Errors coded \"other\" (nature code 99) | {pct(d['nat'][99], d['err']):.0f}% | {pct(us['nat'][99], us['err']):.0f}% |",
          f"| Error cases with no per-error dollar amount recorded | {pct(d['amt0'], d['err']):.1f}% | {pct(us['amt0'], us['err']):.1f}% |", "", n["pattern"], ""]
    L += ["## What the tool does", "",
          "Each month the tool scores every active case using only information the agency already has before any review:",
          "- reported income and earnings;", "- deductions, housing and utility costs;", "- household size;",
          "- the household's maximum allotment.", "",
          "It does not use the benefit the agency issued: in the federal QC data that would let it compare the issued amount with the reviewer's corrected facts (experiment 106).", "",
          "It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.", "",
          f"{name}'s model learns from every state's QC cases plus {name}'s maximum allotments" + (", with its own cases weighted ten times" if a["adopted"] == "C_ctx" else "") + f". Among the 53 jurisdictions, {name} ranks {R20[s]} on the top-20% lift, {R10[s]} on the top-10% lift and {RTS[s]} on the later-years test (1 = best).", "",
          "### Results on cases the model never saw", "", f"{e68['n_holdout']:,} {name} cases ({holdout_pct}%) were set aside before training:", "",
          "| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |", "|---|---|---|---|---|",
          f"| 10% of the queue | **{v['top10']['lift']:.1f}×** | ${v['top10']['per_hour_$']:.0f} (${v['top10']['random_per_hour_$']:.0f}) | {ev(v['top10']['expected_over_actual'])} | {R10[s]} |",
          f"| 20% of the queue | **{v['top20']['lift']:.1f}×** | ${v['top20']['per_hour_$']:.0f} (${v['top20']['random_per_hour_$']:.0f}) | {ev(v['top20']['expected_over_actual'])} | {R20[s]} |",
          f"| 20%, trained 2020–22, tested 2023–24 | {TS[s]:.1f}× | | | {RTS[s]} |",
          f"| 20%, with the fairness floor | {fl:.1f}× | | | |", "",
          f"Reviews are assumed to take 30 minutes. The 53-jurisdiction median is {MED20:.2f}× (top 20%).", "",
          "### Fairness", "", "The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:", "",
          "| Household type | Dollars only | With the floor |", "|---|---|---|"]
    for k, lab in (("elderly", "Elderly"), ("disabled", "Disabled"), ("single_parent", "Single parent"), ("childless_adult", "Childless adult")):
        if k in b:
            L.append(f"| {lab} | {b[k]:.2f} | {f[k]:.2f} |")
    L += ["", (f"The floor costs about {round(cost)}% of the lift. " if cost >= 0.5 else "In " + name + " the floor came out with no measurable cost (a chance effect on the held-out cases). ") + "We recommend it on by default.", "",
          "### Underpayments", "",
          f"A second ranker trained on underpayments finds {e79['under']['under_lift']:.1f} times the underpayment dollars of random review, against {e79['total']['under_lift']:.1f} times for the main ranker (both trained on {name}'s own cases; exp79, leak-free)." +
          (" Here it does no better than the main ranker, so a separate queue adds little." if e79['under']['under_lift'] <= e79['total']['under_lift'] else ""), "",
          "### Flag cards for reviewers", "", n["cards"], ""]
    L += ["## FY2028 cost share", "",
          "H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).", ""]
    if owes:
        L += ["| Scenario | Reviewed a month | Rate after | State share | Avoided a year | Random reviews, same volume |", "|---|---|---|---|---|---|",
              f"| Today (FY2025 rate) | — | {e93['per_fy2025']:.2f}% | {round(100 * e93['cost_share_now'])}% | — | — |"]
        for key, lab, r in (("low", "Low", "1%"), ("central", "**Central**", "2%"), ("high", "High", "3%")):
            x = sc[key]
            rnd = cost_lines(s).split(f"{key:7s}")[1].split("random reviews: ")[1].split(")")[0]
            L.append(f"| {lab} | {r} ({x['reviews_per_month']:,} reviews, {x['fte']:.0f} FTEs) | {x['ranker']['per']:.2f}% | {round(100 * x['ranker']['cost_share'])}% | ${x['ranker']['saving_vs_now'] / 1e6:,.0f}M | {rnd} |")
        L += ["", thresholds(s, name), ""]
    else:
        L += [f"At {e93['per_fy2025']:.2f}%, {name} pays nothing. **How much a higher rate would cost:** {name}'s SNAP benefits are about ${e93['annual_benefits'] / 1e6:,.0f} million a year. Assumptions are the same as the national model's central scenario: 2% of cases reviewed a month, 80% of found errors fixed, errors otherwise lasting 6 months.", "",
              f"| If {name}'s rate were… | Share owed | Cost a year | Rate after ranked reviews (≈{sc['central']['reviews_per_month']:,} a month, {sc['central']['fte']:.1f} FTEs) | Rate after random reviews |", "|---|---|---|---|---|",
              f"| {e93['per_fy2025']:.2f}% (FY2025) | 0% | $0 | {sc['central']['ranker']['per']:.2f}% | {sc['central']['random']['per']:.2f}% |"]
        for p, h in hyp.items():
            L.append(f"| {p}% | {h['share']} | about {h['cost']} | {h['after']} | {h['random']} |")
        rk = [p for p, h in hyp.items() if float(h["after"].rstrip("%")) < 6]
        rd = [p for p, h in hyp.items() if float(h["random"].rstrip("%")) < 6]
        L += ["", f"Ranked reviews bring {' and '.join(rk) + '%' if rk else 'neither hypothetical rate'} back under 6%; random reviews of the same volume bring {' and '.join(rd) + '%' if rd else 'neither'} back under.", ""]
    L += ["These figures show the size of the opportunity, not a forecast. The model leaves out:",
          "- timing relative to the federal sample month;", "- procedural errors outside the public file;", "- behavior changes;", "- the cost of reviews.", ""]
    L += [f"## A pilot in {name}", "",
          "1. **Month 0:** map the case-management fields to the tool's inputs (13 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.",
          "2. **Months 1–3, shadow:**",
          "   - **Review:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on.",
          "   - **Random slice:** about 10% of reviews on randomly chosen cases.",
          "   - **Record:** the dollars found and the error type." + (f" {n['pilot_extra']}" if n["pilot_extra"] else ""),
          "3. **Read-out:**", "   - dollars found against the forecast;", "   - dollars per review hour against current selection;",
          "   - how long found errors had lasted and the share fixed (the two cost-share drivers).",
          "4. **Refresh yearly** on the new federal QC sample plus the pilot's findings.", ""]
    L += ["## Limitations", "",
          f"- **Public data only.** The model was built from federal public-use files, whose income and deduction fields are the QC reviewer's values; for error cases those are the corrected facts, while a deployed tool sees the agency's uncorrected ones. Validate on {name}'s own pre-review case records before relying on these numbers.",
          "- **Scenarios, not forecasts.** See the cost-share caveats above."]
    if n["limit_extra"]:
        L.append(n["limit_extra"])
    L += [f"- **The policy library doesn't cover {name} yet.** {NARRATIVE_POLICY[s]} Rule citations on flag cards would need {name}'s SNAP manual added first.",
          "- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.", ""]
    L += ["## Technical reproduction", "",
          "Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.", "",
          "```bash",
          f"# {name}'s numbers as measured (top-10/20% lift, $/hour, forecast, fairness)",
          f"python3 -c \"import json; print(json.dumps(json.load(open('experiments/exp83_leakfree_results.json'))['{s}'], indent=1))\"",
          "# refit and re-evaluate every jurisdiction's model, leak-free by default (reproduces exp83_leakfree_results.json)",
          "python3 experiments/exp83_context_models_full_eval.py --workers 8",
          "# cost share, every step shown",
          f"python3 experiments/cost_share_replicate.py --state {s}"]
    if not owes:
        L += [f"python3 experiments/cost_share_replicate.py --state {s} --per 6.5"]
    L += [f"# regenerate this brief from the results (every figure is computed, not typed)",
          f"python3 whitepaper/make_state_brief.py {s}",
          f"# score cases with the packaged {name} model",
          f"python3 deliverables/state_rankers/score_cases.py --state {s} --input cases.csv --output ranked.csv --id-col CASE_ID",
          "```", "",
          "**Sources:**",
          f"- **Model and held-out cases:** exp82 (adoption: {name} uses variant {a['adopted']}) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.",
          "- **Leak-free rebuild:** exp106 (the leak), exp107 (the rebuild, later-years test).", "- **Fairness:** exp72 and exp83.", "- **Underpayments:** exp79.",
          "- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.",
          f"- **Error pattern:** computed from the five QC files (state code {CODES[s]})."]
    return "\n".join(L) + "\n"


UNDER_REVIEW = "> **Under review (October 26, 2026).** The case-ranking figures in this paper are inflated and should not be cited until corrected figures are published. That covers lift over random review, dollars per review hour, forecast accuracy, the FY2028 cost-share scenarios, and review ratios and fairness-floor results. The models' inputs included values recorded by QC reviewers (corrected income, deductions and household size), which a state would not have before a review (experiment 106). Figures computed directly from the QC data are not affected: error rates, error patterns, caseload shares and dollar concentration."

NARRATIVE_POLICY = {
    "PA": "It holds 3 Pennsylvania SNAP documents (DHS operations memoranda).",
    "NY": "It holds 5 New York SNAP documents (an OTDA administrative directive and GIS messages).",
    "WY": "It holds 1 Wyoming SNAP document (the FY2026 SNAP Employment and Training state plan).",
    "TX": "It holds no Texas SNAP documents (its one Texas benefits document is a TANF FAQ).",
    "SD": "It holds 1 South Dakota SNAP document (an employment-and-training policy).",
    "UT": "It holds 1 Utah SNAP document (the FY2026 SNAP Employment and Training state plan).",
    "ID": "It holds 1 Idaho SNAP document (the FY2026 SNAP Employment and Training state plan, amendment 1).",
}

if __name__ == "__main__":
    P = patterns()
    for s in sys.argv[1:]:
        (HERE / FILES[s]).write_text(brief(s, P))
        print("wrote", FILES[s])
