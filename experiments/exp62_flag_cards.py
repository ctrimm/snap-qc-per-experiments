"""Exp 62 — build plain-language flag cards for flagged cases (deterministic layers).

Per state (default PA, NY): refit the exp58 ranker and the exp61 where-to-look
model on the non-holdout rows, flag the top 20% of the holdout by expected
dollars, and write one card per flagged case:

  why       expected error dollars (exp57-style isotonic calibration),
            priority band, top risk factors from ranker ablation (exp61
            groups) stated as facts from the case, and the benefit at stake
  check     top two parts of the case from the where-to-look model, as
            "about N in 10" likelihoods
  ask_for   a fixed verification checklist per part, plus the state's most
            common type of mistake in that part (training error cases)
  truth     real outcome and T3 label (kept OUT of what any language model
            sees; used only for scoring)

Writes experiments/exp62_cards.jsonl, plus a template rendering of each card
(the no-language-model baseline) in the "template" field.

Usage: OMP_NUM_THREADS=4 python3 experiments/exp62_flag_cards.py [--states PA,NY]
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "experiments" / "eval_pilot"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402
import exp58_agency_rankers as E58  # noqa: E402
import exp61_ranker_reason_codes as E61  # noqa: E402
import labels as L  # noqa: E402

PART_NAME = {"earned": "earned income", "unearned": "unearned income", "shelter": "shelter costs",
             "sua": "the utility allowance", "medical": "medical expenses", "depcare": "dependent care",
             "hhcomp": "household size", "childsupport": "child support", "arithmetic": "the benefit math",
             "other": "other case details", "standard": "the standard deduction", "assets": "assets",
             "reporting": "reporting rules", "income_total": "total income"}
CHECKLIST = {
    "earned": "pay stubs for the last 30 days, and whether anyone started a new job or changed hours",
    "unearned": "current award letters or data matches for Social Security, SSI, unemployment and child support received",
    "shelter": "the current lease or mortgage statement, and who in the household pays rent",
    "sua": "whether the household pays heating or cooling separately, and a utility bill in a member's name",
    "medical": "out-of-pocket medical costs for elderly or disabled members, with receipts or recurring bills",
    "depcare": "the care provider's statement and amount, and whether care is needed for work or training",
    "hhcomp": "who lives in the home and buys food together, and whether anyone moved in or out",
    "childsupport": "court orders and proof of child support paid",
    "arithmetic": "the benefit calculation itself: each amount entered and the totals",
    "other": "the case notes for anything that changed recently",
}
MISTAKE = {35: "income from a source that wasn't reported", 37: "known income left out of the budget",
           38: "more income than was budgeted", 44: "less income than was budgeted",
           52: "a deduction that should have counted but didn't", 53: "a deduction counted that shouldn't have",
           54: "the wrong standard amount used", 56: "a deduction set too high", 57: "a deduction set too low",
           97: "a change between reporting periods", 98: "a typing or math mistake"}
GROUP_FACTS = {  # group -> (feature, plain label) facts to show
    "earned income": [("earned_est", "reported earnings")],
    "unearned income": [("unearned_est", "reported unearned income")],
    "total income": [("gross_income", "reported gross income"), ("hh_size_cert", "household size")],
    "shelter costs": [("rent", "rent"), ("utilities", "utilities"), ("shelter_deduction", "shelter deduction")],
    "utility allowance": [("sua_used", "utility allowance used")],
    "medical deduction": [("medical_claimed", "medical expenses claimed")],
    "dependent care": [("depcare_claimed", "dependent care claimed")],
    "child support": [("child_support_claimed", "child support claimed")],
    "household size": [("hh_size_cert", "household size")],
}
TOP_K = 2  # parts of the case on the card; exp65 uses 3 (--top-k)
TEMPERATURE = None  # exp76: exp74 temperature scaling of the where-to-look odds (--calibrate)
EXP74_T = {"PA": 2.9, "NY": 2.9, "ID": 2.8}  # measured in exp74; other states use 2.9 (pre-registered in exp76)
WORDING = "v1"  # exp76 "v2": "in about N of 10 similar cases with an error"
COUNT_FEATS = {"hh_size_cert", "hh_size_reported", "sua_used"}


def money(v):
    return f"${int(round(v)):,}"


def fact(name, label, x, med):
    v = x[E61.FIDX[name]]
    if name == "sua_used":
        return f"{label}: {'yes' if v else 'no'}"
    if name in COUNT_FEATS:
        return f"{label}: {int(v)}"
    return f"{label}: {money(v)} a month (state typical {money(med[E61.FIDX[name]])})"


def load_labels(st, qc_dir):
    code, hfile, _, _ = E56.STATES[st]
    real = E58.load_state(qc_dir, code)
    lab = {}
    for fy in E58.FY_FILES:  # t3 + t4, indexed like E58.load_state
        import csv
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")))
        idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != code:
                    continue
                lb = L.label_case(row)
                lab[(fy, idx)] = (lb["t3"], lb["t4"], lb["t2"])
                idx += 1
    hold = {tuple(k) for k in json.loads((ROOT / "experiments" / hfile).read_text())["holdout_keys"]}
    tr = [k for k in sorted(real) if k not in hold]
    te = [k for k in sorted(real) if k in hold]
    return real, lab, tr, te


def build_state(st, qc_dir, cfg):
    real, lab, tr, te = load_labels(st, qc_dir)
    return make_cards(st, real, lab, tr, te, cfg, prefix="")


def build_train_cards(st, qc_dir, cfg, folds=5):
    """Cross-fitted cards for non-holdout rows (training data for step 2):
    fit on 4/5 of the non-holdout rows, card the top 20% of the other 1/5."""
    real, lab, tr, _ = load_labels(st, qc_dir)
    rng = np.random.RandomState(62)
    fold = rng.randint(0, folds, len(tr))
    cards = []
    for k in range(folds):
        fit = [t for t, g in zip(tr, fold) if g != k]
        tgt = [t for t, g in zip(tr, fold) if g == k]
        cards += make_cards(st, real, lab, fit, tgt, cfg, prefix="T")
    return cards


def make_cards(st, real, lab, tr, te, cfg, prefix=""):
    from sklearn.ensemble import HistGradientBoostingClassifier
    X, y, a = E58.arrays(real, tr)
    Xh, yh, ah = E58.arrays(real, te)
    f, _ = E56.fit_two_part(X, y, a, cfg["clf"], cfg["reg"])
    iso = E58.dollar_calibrator(X, y, a, cfg["clf"], cfg["reg"])
    med = np.median(X, axis=0)
    tr_e = [i for i, k in enumerate(tr) if y[i] and lab[k][0]]
    wl = HistGradientBoostingClassifier(random_state=61, max_iter=200, learning_rate=0.05).fit(
        X[tr_e], [lab[tr[i]][0] for i in tr_e])
    mistakes = defaultdict(Counter)
    for i in tr_e:
        t3, t4, _ = lab[tr[i]]
        if t4 and int(t4) in MISTAKE:
            mistakes[t3][int(t4)] += 1
    score = f(Xh)
    q80, q90 = np.quantile(score, 0.80), np.quantile(score, 0.90)
    D = E61.reasons(f, Xh, med)
    names = list(E61.GROUPS)
    proba = wl.predict_proba(Xh)
    if TEMPERATURE:
        T = EXP74_T.get(st, 2.9)
        lp = np.log(np.clip(proba, 1e-9, 1)) / T
        lp -= lp.max(axis=1, keepdims=True)
        proba = np.exp(lp) / np.exp(lp).sum(axis=1, keepdims=True)
    cards = []
    for i, k in enumerate(te):
        if score[i] < q80:
            continue
        order = [names[j] for j in np.argsort(-D[i]) if D[i, j] > 0][:3]
        top = np.argsort(-proba[i])[:TOP_K]
        check = [{"part": str(wl.classes_[j]), "name": PART_NAME[str(wl.classes_[j])],
                  "in_10": min(9, max(1, int(round(10 * proba[i, j]))))} for j in top]
        ask = []
        for c in check:
            m = mistakes[c["part"]].most_common(1)
            ask.append({"part": c["part"], "name": c["name"], "ask_for": CHECKLIST.get(c["part"], CHECKLIST["other"]),
                        "common_mistake": MISTAKE[m[0][0]] if m else None})
        facts = []
        for g in order:
            for name, label in GROUP_FACTS[g]:
                s = fact(name, label, Xh[i], med)
                if s not in facts:
                    facts.append(s)
        card = {"card_id": f"{prefix}{st}-{k[0]}-{k[1]}", "state": st,
                "why": {"priority": "top 10%" if score[i] >= q90 else "top 20%",
                        "expected_error_dollars": int(round(float(iso.predict([score[i]])[0]) / 10) * 10),
                        "monthly_benefit": int(round(Xh[i, E61.FIDX["issued_benefit"]])),
                        "risk_factors": order, "facts": facts},
                "check_first": check, "ask_for": ask,
                "truth": {"error": bool(yh[i]), "t3": lab[k][0], "t4": lab[k][1], "finding": lab[k][2],
                          "dollars": float(ah[i])}}
        card["template"] = render_template(card)
        cards.append(card)
    return cards


def render_template(c):
    w = c["why"]
    s1 = (f"This case is in the {w['priority']} of the review queue: about {money(w['expected_error_dollars'])} "
          f"in expected error, on a {money(w['monthly_benefit'])} monthly benefit.")
    s2 = "It stands out for " + " and ".join(w["risk_factors"][:2]) + "." if w["risk_factors"] else ""
    a = c["ask_for"][0]
    if WORDING == "v2":
        s3 = (f"Check {a['name']} first (in about {c['check_first'][0]['in_10']} of 10 similar cases with an error, "
              f"that's where it was): {a['ask_for']}.")
        rest = [f"Then check {b['name']} (about {cf['in_10']} of 10)." for b, cf in zip(c["ask_for"][1:], c["check_first"][1:])]
    else:
        s3 = (f"Check {a['name']} first (about {c['check_first'][0]['in_10']} in 10 similar cases): {a['ask_for']}.")
        rest = [f"Then check {b['name']} (about {cf['in_10']} in 10)." for b, cf in zip(c["ask_for"][1:], c["check_first"][1:])]
    return " ".join(x for x in (s1, s2, s3, *rest) if x)


def card_for_model(c):
    """What a language model may see: everything except truth and template."""
    return {k: v for k, v in c.items() if k not in ("truth", "template")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-dir", default=str(ROOT.parent / "snap-qc-data/raw"))
    ap.add_argument("--states", default="PA,NY")
    ap.add_argument("--top-k", type=int, default=2, help="parts of the case on each card (exp65: 3)")
    ap.add_argument("--calibrate", action="store_true", help="exp76: exp74 temperature scaling of the odds")
    ap.add_argument("--wording", default="v1", choices=["v1", "v2"])
    ap.add_argument("--out", default=None, help="default experiments/exp62_cards.jsonl")
    ap.add_argument("--train-cards", action="store_true",
                    help="cross-fitted cards for non-holdout rows -> exp62_train_cards.jsonl")
    args = ap.parse_args()
    global TOP_K, TEMPERATURE, WORDING
    TOP_K = args.top_k
    TEMPERATURE = args.calibrate
    WORDING = args.wording
    cfgs = {r["state"]: r["cfg"] for r in json.loads((ROOT / "experiments" / "exp58_results.json").read_text())}
    allc = []
    if args.train_cards:
        for st in args.states.split(","):
            cs = build_train_cards(st, args.qc_dir, cfgs[st])
            print(f"{st}: {len(cs)} training cards", flush=True)
            allc += cs
        out = Path(args.out) if args.out else ROOT / "experiments" / "exp62_train_cards.jsonl"
        out.write_text("".join(json.dumps(c) + "\n" for c in allc))
        print(f"wrote {out} ({len(allc)} cards)")
        return
    for st in args.states.split(","):
        cards = build_state(st, args.qc_dir, cfgs[st])
        err = [c for c in cards if c["truth"]["error"] and c["truth"]["t3"]]
        top2 = sum(c["truth"]["t3"] in {x["part"] for x in c["check_first"]} for c in err)
        print(f"{st}: {len(cards)} cards, {len(err)} error cases with a location; check-first top-2 covers {top2 / len(err):.0%}")
        allc += cards
    out = Path(args.out) if args.out else ROOT / "experiments" / "exp62_cards.jsonl"
    out.write_text("".join(json.dumps(c) + "\n" for c in allc))
    print(f"wrote {out} ({len(allc)} cards)")


if __name__ == "__main__":
    main()
