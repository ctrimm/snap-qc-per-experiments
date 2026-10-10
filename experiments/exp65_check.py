"""Exp65: exp62 checks on three-part cards (80-word limit), plus the reviewer packet.

Usage: python3 experiments/exp65_check.py NOTES.jsonl|template ...   (scores on exp65_cards.jsonl)
       python3 experiments/exp65_check.py --packet NOTES.jsonl       (writes the blind A/B packet)
"""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
args = sys.argv[1:]; sys.argv = sys.argv[:1]
sys.path.insert(0, str(ROOT / "experiments"))
import exp62_check as K
K.CARDS = {c["card_id"]: c for c in map(json.loads, open(ROOT / "experiments/exp65_cards.jsonl"))}
K.MAX_WORDS = 80


def packet(notes_path):
    """20 cards (10 PA, 10 NY): the three-part template vs the model note, order randomized; key kept separately."""
    notes = {r["card_id"]: r["note"] for r in map(json.loads, open(notes_path))}
    rng = random.Random(65)
    ids = [i for st in ("PA", "NY") for i in rng.sample([i for i in K.EVAL_IDS if i.startswith(st) and i in notes], 10)]
    md, key = ["# exp65 reviewer packet: which note would help you more?\n",
               "For each case, read both notes and mark which is clearer and more useful (A, B, or same). "
               "Both come from the same flag card; one is a fixed template, the other is written by a language model.\n"], {}
    for n, i in enumerate(ids, 1):
        pair = [("template", K.CARDS[i]["template"]), ("model", notes[i])]
        rng.shuffle(pair)
        key[i] = {"A": pair[0][0], "B": pair[1][0]}
        md += [f"## Case {n} ({i.split('-')[0]})\n", f"**A.** {pair[0][1]}\n", f"**B.** {pair[1][1]}\n",
               "Clearer: A / B / same · More useful: A / B / same\n"]
    (ROOT / "experiments/exp65_reviewer_packet.md").write_text("\n".join(md))
    (ROOT / "experiments/exp65_reviewer_key.json").write_text(json.dumps(key, indent=1))
    print("wrote experiments/exp65_reviewer_packet.md (+ key)")


if args and args[0] == "--packet":
    packet(args[1])
else:
    sys.argv[1:] = args
    K.main()
