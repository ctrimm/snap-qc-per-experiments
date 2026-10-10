"""Exp76/77 checks: exp62's frozen checks on a given card file (80-word limit for three parts),
plus "keeps_odds": the note gives the first check's "N of 10" (or "N in 10") and the monthly benefit.

Usage: python3 experiments/exp76_check.py CARDS.jsonl IDS.txt NOTES.jsonl|template ...
       python3 experiments/exp76_check.py --packet CARDS.jsonl IDS.txt NOTES.jsonl OUT_PREFIX
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
args = sys.argv[1:]; sys.argv = sys.argv[:1]
sys.path.insert(0, str(ROOT / "experiments"))
import exp62_check as K  # noqa: E402

K.MAX_WORDS = 80


def keeps_odds(c, note):
    n = c["check_first"][0]["in_10"]
    t = note.lower().replace(",", "")
    odds = re.search(rf"\b{n}\s+(of|in|out of)\s+10\b", t) is not None
    ben = str(c["why"]["monthly_benefit"]) in t
    return odds and ben


def score(cards, ids, notes):
    rows = []
    for i in ids:
        if i in notes:
            r = K.check(cards[i], notes[i]); r["keeps_odds"] = keeps_odds(cards[i], notes[i]); rows.append(r)
    n = len(rows)
    agg = {k: sum(r[k] for r in rows) / n for k in ("pass", "faithful", "leads", "short", "readable", "keeps_odds")}
    agg.update(n=n, words=sum(r["words"] for r in rows) / n, grade=sum(r["grade"] for r in rows) / n)
    return agg


def load(cards_path, ids_path):
    cards = {c["card_id"]: c for c in map(json.loads, open(cards_path))}
    return cards, Path(ids_path).read_text().split()


if args and args[0] == "--packet":
    cards, ids = load(args[1], args[2])
    notes = {r["card_id"]: r["note"] for r in map(json.loads, open(args[3]))}
    rng = random.Random(76)
    pick = [i for st in ("PA", "NY") for i in rng.sample([i for i in ids if i.startswith(st) and i in notes], 10)]
    md = ["# Flag-card reviewer packet (v2 cards): which note would help you more?\n",
          "For each case, read both notes and mark which is clearer and more useful (A, B, or same). "
          "Both come from the same flag card; one is a fixed template, the other is written by a language model.\n"]
    key = {}
    for n, i in enumerate(pick, 1):
        pair = [("template", cards[i]["template"]), ("model", notes[i])]; rng.shuffle(pair)
        key[i] = {"A": pair[0][0], "B": pair[1][0]}
        md += [f"## Case {n} ({i.split('-')[0]})\n", f"**A.** {pair[0][1]}\n", f"**B.** {pair[1][1]}\n",
               "Clearer: A / B / same · More useful: A / B / same\n"]
    Path(args[4] + "_packet.md").write_text("\n".join(md)); Path(args[4] + "_key.json").write_text(json.dumps(key, indent=1))
    print("wrote", args[4] + "_packet.md")
elif args:
    cards, ids = load(args[0], args[1])
    K.CARDS = cards
    for a in args[2:]:
        notes = {i: c["template"] for i, c in cards.items()} if a == "template" else \
            {r["card_id"]: r["note"] for r in map(json.loads, open(a))}
        g = score(cards, ids, notes)
        print(f"{Path(a).name}: n={g['n']} PASS {g['pass']:.0%} | faithful {g['faithful']:.0%} leads {g['leads']:.0%} "
              f"short {g['short']:.0%} readable {g['readable']:.0%} keeps odds+benefit {g['keeps_odds']:.0%} | "
              f"words {g['words']:.0f} grade {g['grade']:.1f}")
