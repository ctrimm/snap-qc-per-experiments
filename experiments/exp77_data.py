"""Exp77: filter v2 teacher notes (all frozen checks + keeps odds and benefit) and write SFT pairs.
Holds out 100 passing cards (seed 77) for checkpoint choice; student prompt with v2 card wording."""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.argv = sys.argv[:1]; sys.path.insert(0, str(ROOT / "experiments"))
import exp62_check as K
import exp62_rewrite as R
import exp76_check as C
K.MAX_WORDS = 80; R.WORDING = "v2"
D = ROOT.parent / "snap-qc-data/derived/exp77_sft"; D.mkdir(parents=True, exist_ok=True)
cards = {c["card_id"]: c for c in map(json.loads, open(ROOT / "experiments/exp76_train_cards.jsonl"))}
notes = [json.loads(l) for l in open(ROOT / "experiments/exp77_teacher_notes.jsonl")]
keep = [n for n in notes if K.check(cards[n["card_id"]], n["note"])["pass"] and C.keeps_odds(cards[n["card_id"]], n["note"])]
print(f"teacher notes {len(notes)}, pass all checks incl. odds+benefit {len(keep)} ({len(keep)/len(notes):.0%})")
rng = random.Random(77); rng.shuffle(keep)
sel, train = keep[:100], keep[100:]
(ROOT / "experiments/exp77_select_ids.txt").write_text("\n".join(n["card_id"] for n in sel) + "\n")
pair = lambda n: {"prompt": R.PROMPT.format(card=R.card_text(cards[n["card_id"]])), "completion": " " + n["note"]}
k = int(len(train) * 0.95)
(D / "train.jsonl").write_text("".join(json.dumps(pair(n)) + "\n" for n in train[:k]))
(D / "valid.jsonl").write_text("".join(json.dumps(pair(n)) + "\n" for n in train[k:]))
print(f"selection 100, SFT train {k}, valid {len(train) - k}")
