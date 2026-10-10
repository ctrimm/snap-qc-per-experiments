"""Exp 66 — explanation self-training (rejection-sampling loop), round helpers.

build ROUND SAMPLES.jsonl
    From the current student's sampled notes (2 per card), keep one passing
    note per card (lowest reading grade, then fewest words). Training data for
    the round = exp62's filtered teacher pairs + every student pass from
    rounds 1..ROUND (latest round wins per card), student prompt, 95/5 split.
score NOTES.jsonl
    Pass rate and diversity on the 100 held-out selection cards.

Diversity: distinct-bigram ratio across notes, and the share of notes whose
first six words are the most common opening (watch for collapse).
"""
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT.parent / "snap-qc-data/derived"
cmd, args = sys.argv[1], sys.argv[2:]
sys.argv = sys.argv[:1]
sys.path.insert(0, str(ROOT / "experiments"))
import exp62_check as K  # noqa: E402
import exp62_rewrite as R  # noqa: E402

CARDS = {c["card_id"]: c for c in map(json.loads, open(ROOT / "experiments/exp62_train_cards.jsonl"))}


def diversity(notes):
    bi = [tuple(w[i:i + 2]) for w in (re.findall(r"\w+", n.lower()) for n in notes) for i in range(len(w) - 1)]
    opens = Counter(" ".join(n.lower().split()[:6]) for n in notes)
    return round(len(set(bi)) / max(1, len(bi)), 3), round(opens.most_common(1)[0][1] / len(notes), 3)


def pair(cid, note):
    return {"prompt": R.PROMPT.format(card=R.card_text(CARDS[cid])), "completion": " " + note}


if cmd == "build":
    rnd, path = int(args[0]), args[1]
    best = {}
    n = ok = 0
    for r in map(json.loads, open(path)):
        n += 1
        chk = K.check(CARDS[r["card_id"]], r["note"])
        if not chk["pass"]:
            continue
        ok += 1
        key = (chk["grade"], chk["words"])
        if r["card_id"] not in best or key < best[r["card_id"]][0]:
            best[r["card_id"]] = (key, r["note"])
    hist = D / "exp66_student_passes.jsonl"
    prev = [json.loads(l) for l in open(hist)] if hist.exists() and rnd > 1 else []
    prev = [p for p in prev if p["round"] < rnd]
    allp = prev + [{"round": rnd, "card_id": c, "note": v[1]} for c, v in best.items()]
    hist.write_text("".join(json.dumps(p) + "\n" for p in allp))
    latest = {}
    for p in allp:
        latest[p["card_id"]] = p["note"]
    teacher = [json.loads(l) for l in open(D / "exp62_sft/train.jsonl")]
    student = [pair(c, n_) for c, n_ in latest.items()]
    data = teacher + student
    random.Random(66 + rnd).shuffle(data)
    k = int(len(data) * 0.95)
    out = D / f"exp66_r{rnd}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "train.jsonl").write_text("".join(json.dumps(x) + "\n" for x in data[:k]))
    (out / "valid.jsonl").write_text("".join(json.dumps(x) + "\n" for x in data[k:]))
    print(f"round {rnd}: samples {n}, passing {ok} ({ok / n:.0%}), cards with a pass {len(best)}; "
          f"train {k} (teacher {len(teacher)}, student {len(student)})")
elif cmd == "score":
    notes = {r["card_id"]: r["note"] for r in map(json.loads, open(args[0]))}
    sel = (ROOT / "experiments/exp62_select_ids.txt").read_text().split()
    rows = [K.check(CARDS[i], notes[i]) for i in sel if i in notes]
    d2, top_open = diversity([notes[i] for i in sel if i in notes])
    print(json.dumps({"pass": round(sum(r["pass"] for r in rows) / len(rows), 3),
                      "faithful": round(sum(r["faithful"] for r in rows) / len(rows), 3),
                      "mean_grade": round(sum(r["grade"] for r in rows) / len(rows), 2),
                      "distinct_bigrams": d2, "most_common_opening_share": top_open}))
