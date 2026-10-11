"""Exp 70 — did QC fine-tuning cost the model SNAP policy knowledge?

The north star's LM gate has two halves: the QC-variance eval (passed, exp59)
and a SNAP policy benchmark. This runs the second half: the 500 CalFresh
scenario multiple-choice questions (Better Government Lab, cornellbgl/
SNAP_scenarios; local copy ~/datasets/snap_scenarios), no tools, one letter.

Pre-registered (in this docstring, committed before scoring):
  models   Gemma 4 E4B untrained; E4B + exp52 SFT step-400 adapter (the
           exp59-confirmed model); Gemma 4 31B untrained as a setup check
           against the published 85.8% (Nava Labs, no tools)
  prompt   the eval's no-tools instruction + client attributes + question;
           greedy, thinking off, max 8 tokens; first standalone letter A-E
  readout  accuracy; paired difference tuned - untrained with a 95%
           bootstrap CI (2,000 resamples, seed 70). "No meaningful harm" if
           the CI's lower bound is above -3 points.
  also     accuracy by difficulty rating; unparseable answers count wrong

Usage (training venv): python experiments/exp70_calfresh_mcq.py --model M [--adapter DIR] --out PREDS.jsonl
       python3 experiments/exp70_calfresh_mcq.py --score A.jsonl B.jsonl   (B - A paired)
"""
import argparse
import csv
import json
import re
from pathlib import Path

DATA = Path.home() / "datasets/snap_scenarios/snap_scenarios.csv"
INSTR = ("You answer multiple-choice questions about CalFresh, California's SNAP program. "
         "Respond with EXACTLY one letter: A, B, C, D or E. Nothing else — no explanation, no punctuation.")


def rows():
    return list(csv.DictReader(open(DATA, newline="")))


def prompt(r):
    return f"{INSTR}\n\nClient:\n{r['preamble_attributes'].strip()}\n\n{r['question'].strip()}\n\nAnswer:"


def parse(text):
    m = re.search(r"\b([A-E])\b", text.strip().upper())
    return m.group(1) if m else None


def run(args):
    from mlx_lm import generate, load
    model, tok = load(args.model, adapter_path=args.adapter) if args.adapter else load(args.model)
    out = Path(args.out)
    done = {json.loads(l)["question_id"] for l in open(out)} if out.exists() else set()
    with open(out, "a") as fh:
        for r in rows():
            if r["question_id"] in done:
                continue
            p = tok.apply_chat_template([{"role": "user", "content": prompt(r)}], add_generation_prompt=True,
                                        tokenize=False, enable_thinking=False)
            raw = generate(model, tok, prompt=p, max_tokens=8, verbose=False)
            fh.write(json.dumps({"question_id": r["question_id"], "raw": raw, "pred": parse(raw),
                                 "gold": r["correct_single_answer"].strip(),
                                 "difficulty": r["difficulty_rating"].split(".")[0]}) + "\n")
            fh.flush()


def score(paths):
    import random
    res = [{r["question_id"]: r for r in map(json.loads, open(p))} for p in paths]
    for d in res:  # committed copies keep only correct/incorrect (the answer key stays out of git: dataset licence)
        for r in d.values():
            if "correct" in r:
                r.setdefault("pred", bool(r["correct"])); r.setdefault("gold", True)
    for p, d in zip(paths, res):
        acc = sum(r["pred"] == r["gold"] for r in d.values()) / len(d)
        by = {}
        for r in d.values():
            by.setdefault(r["difficulty"] or "?", []).append(r["pred"] == r["gold"])
        print(f"{Path(p).name}: n={len(d)} accuracy {acc:.1%} | unparseable {sum(r['pred'] is None for r in d.values())} | "
              + " ".join(f"difficulty {k}: {sum(v) / len(v):.0%} (n={len(v)})" for k, v in sorted(by.items())))
    if len(paths) == 2:
        ids = sorted(set(res[0]) & set(res[1]))
        diff = [(res[1][i]["pred"] == res[1][i]["gold"]) - (res[0][i]["pred"] == res[0][i]["gold"]) for i in ids]
        rng = random.Random(70)
        boots = sorted(sum(rng.choice(diff) for _ in diff) / len(diff) for _ in range(2000))
        print(f"paired {Path(paths[1]).name} - {Path(paths[0]).name}: {sum(diff) / len(diff):+.1%} "
              f"[{boots[50]:+.1%}, {boots[1949]:+.1%}]")
# Licence note: cornellbgl/SNAP_scenarios is CC-BY-NC-ND-4.0 (evaluation only; no training use, no
# redistribution). --out files carry predictions and gold letters: keep them outside git
# (../snap-qc-data/derived/exp70_preds/); the committed exp70_*.jsonl keep question_id, correct, difficulty.


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model"); ap.add_argument("--adapter"); ap.add_argument("--out")
    ap.add_argument("--score", nargs="+")
    a = ap.parse_args()
    score(a.score) if a.score else run(a)
