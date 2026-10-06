"""Exp52 quick eval: greedy classification answers on the eval's dev split.

The fast, fixed metric for exp52's autoresearch-style sweep. Loads the bf16
base (optionally with a LoRA adapter) directly with mlx_lm, renders the
locked v1.1 prompt (few-shot + jargon, thinking off, single user turn) for
the 197 dev items that are not few-shot examples, and writes run_lm-format
predictions that score.py reads. The 1,200 test items are never touched
here; they are scored once, at the end, on the chosen configuration.

Usage (training venv):
  python experiments/exp52_quick_eval.py --out preds.jsonl [--adapter DIR]
Prints: composite on dev, per-task primaries, and answers changed vs --base-preds.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE / "eval_pilot"
sys.path.insert(0, str(EVAL))
import run_lm  # noqa: E402

MODEL = "mlx-community/gemma-4-e4b-it-bf16"


def dev_items_and_examples():
    items = json.loads((EVAL / "items.json").read_text())
    dev = [d for d in items if d["split"] == "dev"]
    seen, examples, ex_ids = set(), [], set()
    for d in dev:  # same rule as run_lm.py --condition few
        if d["finding"] not in seen:
            seen.add(d["finding"])
            examples.append((d["fields"], d["labels"]))
            ex_ids.add(d["item_id"])
        if len(examples) == 3:
            break
    return [d for d in dev if d["item_id"] not in ex_ids], examples


def synthetic_check(model, tok, generate, spec):
    """In-distribution learnability: same metrics on synthetic valid cases."""
    import score as S
    path, _, n = spec.partition(":")
    recs = [json.loads(l) for l in open(path)][: int(n or 120)]
    preds = []
    for r in recs:
        p = tok.apply_chat_template([{"role": "user", "content": r["prompt"]}],
                                    add_generation_prompt=True, tokenize=False, enable_thinking=False)
        preds.append(run_lm.parse_class(generate(model, tok, prompt=p, max_tokens=64, verbose=False))[0])
    gold = [json.loads(r["answer"]) for r in recs]
    print(f"synthetic valid n={len(recs)}")
    skills = []
    for t in ("t1", "t2", "t3", "t4", "t5"):
        pairs = [(p.get(t), g[t]) for p, g in zip(preds, gold) if g[t] is not None]
        classes = S.L.TASKS[t]["values"]
        f1, cc = S.macro_f1(pairs, classes), S.chance_corrected(pairs, classes)
        skills.append(cc["excess"])
        print(f"  syn_{t} macroF1 {f1:.3f} kappa {cc['kappa']:.3f} excess {cc['excess']:.3f} p {cc['p_value']:.3f}")
    print(f"synthetic mean excess (T1-T5): {sum(skills) / len(skills):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-preds", default=None)
    ap.add_argument("--split", default="dev", choices=["dev", "test"],
                    help="test = the 1,200 locked test items (final gate only)")
    ap.add_argument("--synthetic", default=None,
                    help="also score this many records of a synthetic valid.jsonl: PATH[:N]")
    args = ap.parse_args()

    from mlx_lm import generate, load
    model, tok = load(MODEL, adapter_path=args.adapter) if args.adapter else load(MODEL)
    if args.synthetic:
        synthetic_check(model, tok, generate, args.synthetic)
    items, examples = dev_items_and_examples()
    if args.split == "test":  # direct load: mlx_lm.server drops adapters for "default_model"
        items = [d for d in json.loads((EVAL / "items.json").read_text())
                 if d["split"] in ("test_main", "test_2024")]
    with open(args.out, "w") as fh:
        for it in items:
            prompt = tok.apply_chat_template(
                [{"role": "user", "content": run_lm.build_class_prompt(it["fields"], "jargon", examples)}],
                add_generation_prompt=True, tokenize=False, enable_thinking=False)
            raw = generate(model, tok, prompt=prompt, max_tokens=64, verbose=False)
            parsed, ok = run_lm.parse_class(raw)
            fh.write(json.dumps({"item_id": it["item_id"], "kind": "class", "raw": raw,
                                 "parsed": parsed, "parse_ok": ok}) + "\n")

    ids = Path(args.out).with_suffix(".ids")
    ids.write_text("\n".join(it["item_id"] for it in items) + "\n")
    res = subprocess.run([sys.executable, str(EVAL / "score.py"), "--items", str(EVAL / "items.json"),
                          "--preds", args.out, "--split", args.split, "--ids", str(ids)],
                         capture_output=True, text=True)
    print(res.stdout.strip())
    if args.base_preds:
        base = {r["item_id"]: r["raw"] for r in map(json.loads, open(args.base_preds))}
        new = {r["item_id"]: r["raw"] for r in map(json.loads, open(args.out))}
        print(f"changed_vs_base: {sum(base.get(k) != v for k, v in new.items())}/{len(new)}")


if __name__ == "__main__":
    main()
