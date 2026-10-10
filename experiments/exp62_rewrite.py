"""Exp 62 step 1 — zero-shot plain-language rewrite of flag cards.

The model sees only the card (never the truth fields) and writes a short
note for a caseworker. Greedy, thinking off, max 200 tokens.

Usage (training venv):
  python experiments/exp62_rewrite.py --model mlx-community/gemma-4-e2b-it-bf16 --out NOTES.jsonl [--adapter DIR] [--ids FILE]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROMPT = """You write short notes for SNAP caseworkers. Turn the flag card below into a note of 2 or 3 sentences, at most 70 words, in plain language a new caseworker understands.

Say why the case was flagged, then what to check first and what to ask for.
Rules:
- Use only facts and numbers that are on the card. Do not add any new numbers.
- Check the parts of the case in the order the card lists them.
- Do not say or suggest that the household made a mistake, was overpaid or underpaid, or did anything wrong. The card only says where to look.

Flag card:
{card}

Note:"""


TEACHER_EXTRA = """
Style: write 4 or 5 short sentences. Keep every sentence under 15 words. Use everyday words (say "pay stubs", not "verification of earnings").
Sentence 1: the priority and the expected error in dollars. Sentence 2: the main reasons it stands out. Then one sentence for each thing to check, with what to ask for. If the card lists a most common issue for the first check, mention it briefly.
"""


def card_text(c):
    w = c["why"]
    lines = [f"Priority: {w['priority']} of the review queue",
             f"Expected error: about ${w['expected_error_dollars']:,}",
             f"Monthly benefit: ${w['monthly_benefit']:,}",
             "Why it stands out: " + (", ".join(w["risk_factors"]) or "overall profile")]
    lines += [f"  - {f}" for f in w["facts"]]
    for n, (cf, ask) in enumerate(zip(c["check_first"], c["ask_for"]), 1):
        line = f"Check {'first' if n == 1 else 'second'}: {cf['name']} (about {cf['in_10']} in 10 similar flagged cases). Ask for: {ask['ask_for']}."
        if ask["common_mistake"]:
            line += f" Most common issue here: {ask['common_mistake']}."
        lines.append(line)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default=str(ROOT / "experiments" / "exp62_eval_ids.txt"))
    ap.add_argument("--cards", default=str(ROOT / "experiments" / "exp62_cards.jsonl"))
    ap.add_argument("--teacher", action="store_true", help="add short-sentence style guidance (step-2 teacher)")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    from mlx_lm import generate, load
    model, tok = load(args.model, adapter_path=args.adapter) if args.adapter else load(args.model)
    cards = {c["card_id"]: c for c in map(json.loads, open(args.cards))}
    ids = list(cards) if args.ids == "all" else Path(args.ids).read_text().split()
    ids = ids[: args.limit] if args.limit else ids
    prompt = PROMPT.replace("Flag card:", TEACHER_EXTRA.strip() + "\n\nFlag card:") if args.teacher else PROMPT
    done = set()
    if Path(args.out).exists():  # resume
        done = {json.loads(l)["card_id"] for l in open(args.out)}
    with open(args.out, "a") as fh:
        for i in ids:
            if i in done:
                continue
            p = tok.apply_chat_template([{"role": "user", "content": prompt.format(card=card_text(cards[i]))}],
                                        add_generation_prompt=True, tokenize=False, enable_thinking=False)
            note = generate(model, tok, prompt=p, max_tokens=200, verbose=False).strip()
            fh.write(json.dumps({"card_id": i, "note": note}) + "\n")
            fh.flush()


if __name__ == "__main__":
    main()
