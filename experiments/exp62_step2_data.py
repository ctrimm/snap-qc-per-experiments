"""Exp62 step 2: filter teacher notes with the frozen checker and write SFT data.

Keeps teacher notes that pass every exp62 check against their own (training)
card. Holds out 100 passing cards (seed 62) as the checkpoint-selection set;
the rest become {"prompt", "completion"} pairs using the STUDENT prompt
(no teacher style guidance), so the fine-tuned model is run exactly like step 1.
"""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments")); sys.argv = sys.argv[:1]
import exp62_check as K
import exp62_rewrite as R
D = ROOT.parent / "snap-qc-data/derived/exp62_sft"; D.mkdir(parents=True, exist_ok=True)
cards = {c["card_id"]: c for c in map(json.loads, open(ROOT / "experiments/exp62_train_cards.jsonl"))}
notes = [json.loads(l) for l in open(ROOT / "experiments/exp62_teacher_notes.jsonl")]
keep = [n for n in notes if K.check(cards[n["card_id"]], n["note"])["pass"]]
print(f"teacher notes {len(notes)}, pass all checks {len(keep)} ({len(keep)/len(notes):.0%})")
rng = random.Random(62); rng.shuffle(keep)
sel, train = keep[:100], keep[100:]
(ROOT / "experiments/exp62_select_ids.txt").write_text("\n".join(n["card_id"] for n in sel) + "\n")
def pair(n): return {"prompt": R.PROMPT.format(card=R.card_text(cards[n["card_id"]])), "completion": " " + n["note"]}
k = int(len(train) * 0.95)
(D / "train.jsonl").write_text("".join(json.dumps(pair(n)) + "\n" for n in train[:k]))
(D / "valid.jsonl").write_text("".join(json.dumps(pair(n)) + "\n" for n in train[k:]))
print(f"selection set 100, SFT train {k}, valid {len(train) - k}")
