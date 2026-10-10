"""Exp 62 — automatic checks for plain-language flag-card notes.

A note passes when it is:
  faithful   every number in it appears on the card; every case part or
             topic it names appears on the card; no forbidden claims (fault,
             fraud, a finding, a direction of error, an action against the
             household)
  leads      in the "what to check" part (from the first check/ask-for
             word on), names the card's first check-first part before the second
  short      at most 70 words
  readable   Flesch-Kincaid grade at most 9

Usage: python3 experiments/exp62_check.py NOTES.jsonl [NOTES2.jsonl ...]
  NOTES.jsonl lines: {"card_id": ..., "note": ...}; "template" scores the
  deterministic template baseline from exp62_cards.jsonl.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = {c["card_id"]: c for c in map(json.loads, open(ROOT / "experiments" / "exp62_cards.jsonl"))}
EVAL_IDS = (ROOT / "experiments" / "exp62_eval_ids.txt").read_text().split()

TOPICS = {  # topic -> regex; a topic in the note must also be on the card
    "earned income": r"earned income|earnings|wages?|pay ?stubs?|paycheck|\bjob\b|hours",
    "unearned income": r"unearned|social security|\bssi\b|unemployment|award letter",
    "shelter": r"shelter|\brent\b|mortgage|lease|housing",
    "utility allowance": r"utility allowance|\bsua\b|heating|cooling|utilit",
    "medical": r"medical",
    "dependent care": r"dependent care|child ?care|day ?care|care provider",
    "child support": r"child support",
    "household size": r"household size|who lives|moved in|moved out|household members",
    "assets": r"\bassets?\b|bank account|savings",
    "benefit math": r"calculation|math|computation",
}
FORBIDDEN = r"fraud|\blie[sd]?\b|lying|intentional|penalt|disqualif|\bden(y|ied)\b|terminat|guilt|" \
            r"overpaid|underpaid|overpayment|underpayment|over-?issu|under-?issu|" \
            r"made (a |an )?(mistake|error)|has (a |an )?(mistake|error)|is wrong|was wrong|did something wrong|cheat"


def card_text(c):
    return json.dumps({k: v for k, v in c.items() if k not in ("truth", "template")}).lower()


def numbers(s):
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", s)}


def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(1, n)


def fk_grade(s):
    sents = max(1, len(re.findall(r"[.!?]+(?:\s|$)", s)))
    words = re.findall(r"[A-Za-z0-9$%'-]+", s)
    if not words:
        return 99.0
    syl = sum(syllables(w) for w in words)
    return 0.39 * len(words) / sents + 11.8 * syl / len(words) - 15.59


def check(c, note):
    t, ct = note.lower(), card_text(c)
    allowed = numbers(ct)
    bad_nums = sorted(numbers(t) - allowed)
    bad_topics = [k for k, rx in TOPICS.items() if re.search(rx, t) and not re.search(rx, ct)]
    forbidden = re.findall(FORBIDDEN, t)
    p1, p2 = (re.escape(x["name"].lower()) for x in c["check_first"][:2])

    def first(rx):
        m = re.search(rx, t)
        return m.start() if m else None
    # accept the topic synonyms for the part names too
    syn = {"earned income": TOPICS["earned income"], "unearned income": TOPICS["unearned income"],
           "shelter costs": TOPICS["shelter"], "the utility allowance": TOPICS["utility allowance"],
           "medical expenses": TOPICS["medical"], "dependent care": TOPICS["dependent care"],
           "household size": TOPICS["household size"], "child support": TOPICS["child support"]}
    n1, n2 = c["check_first"][0]["name"], c["check_first"][1]["name"]
    # order is judged on the "what to check" part: from the first instruction word on
    m = re.search(r"\b(check|look at|start with|ask for|verify|confirm)\b", t)
    t_check = t[m.start():] if m else ""

    def first_in(rx):
        mm = re.search(rx, t_check)
        return mm.start() if mm else None
    f1 = first_in(syn.get(n1, p1)); f2 = first_in(syn.get(n2, p2))
    leads = f1 is not None and (f2 is None or f1 <= f2)
    words = len(re.findall(r"\S+", note))
    grade = fk_grade(note)
    faithful = not bad_nums and not bad_topics and not forbidden
    return {"faithful": faithful, "leads": leads, "short": words <= 70, "readable": grade <= 9.0,
            "pass": faithful and leads and words <= 70 and grade <= 9.0,
            "bad_numbers": bad_nums, "bad_topics": bad_topics, "forbidden": forbidden,
            "words": words, "grade": round(grade, 1)}


def score(notes):
    rows = [check(CARDS[i], notes[i]) for i in EVAL_IDS if i in notes]
    n = len(rows)
    agg = {k: sum(r[k] for r in rows) / n for k in ("faithful", "leads", "short", "readable", "pass")}
    agg.update(n=n, mean_words=sum(r["words"] for r in rows) / n, mean_grade=sum(r["grade"] for r in rows) / n)
    return agg, rows


def main():
    for arg in sys.argv[1:]:
        if arg == "template":
            notes = {i: c["template"] for i, c in CARDS.items()}
        else:
            notes = {r["card_id"]: r["note"] for r in map(json.loads, open(arg))}
        agg, rows = score(notes)
        print(f"{arg}: n={agg['n']} PASS {agg['pass']:.0%} | faithful {agg['faithful']:.0%} leads {agg['leads']:.0%} "
              f"short {agg['short']:.0%} readable {agg['readable']:.0%} | words {agg['mean_words']:.0f} grade {agg['mean_grade']:.1f}")


if __name__ == "__main__":
    main()
