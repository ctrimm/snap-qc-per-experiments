"""Exp 71 — does writing out the differences first help the model?

Pre-registered (this docstring, committed before training):
  Data      exp52's synthetic SFT corpus (derived/exp52_rlvr train/valid, the
            same cases and prompts as the exp52 best model). Completion =
            a deterministic "Differences:" note listing every agency-vs-verified
            pair that differs by more than $1 (or "none visible"), then the
            usual T1-T5 answer block. No language model writes the rationale.
  Train     Gemma 4 E4B, exp52 LoRA recipe, lr 1e-5, batch 4, seed 52;
            checkpoint fixed in advance at step 400 (the answer-only model's
            step); no checkpoint selection on any real data.
  Eval      once, on the exp59 fresh set (items_confirm.json), eval v1.2,
            max 200 tokens (rationale + answers); answer-only comparator =
            exp59's step-400 predictions on the same items.
  Readouts  (1) overall composite, paired vs answer-only (score.py --base-preds);
            (2) the same on the subset of items with a visible difference
            (same pairs, > $1). "Helps" if the subset CI is above 0; "costs"
            if the overall CI is below 0.

Usage: python3 experiments/exp71_rationale.py data          (writes derived/exp71_sft)
       python3 experiments/exp71_rationale.py subset        (writes eval_pilot/exp71_visible_ids.txt)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT.parent / "snap-qc-data/derived"
sys.path.insert(0, str(ROOT / "experiments/eval_pilot"))
import run_lm  # noqa: E402

PAIRS = [("RAWHSIZE", "CTPRHH", "household size", False), ("CERTHHSZ", "FSUSIZE", "certified unit size", False),
         ("RAWGROSS", "FSGRINC", "gross income", True), ("RAWNET", "FSNETINC", "net income", True),
         ("RAWERND", "FSERNDED", "earned income deduction", True), ("FSCSEXP", "FSCSDED", "child support deduction", True),
         ("SHELDED", "FSSLTDED", "shelter deduction", True)]
FIELD_PAIRS = [("raw_hhsize", "verif_hhsize"), ("cert_hhsize", "verif_unit_size"), ("raw_gross", "verif_gross"),
               ("raw_net", "verif_net"), ("raw_ernded", "ernd_ded"), ("rep_csup_ded", "csup_ded"), ("rep_shel_ded", "shel_ded")]


def val(prompt, code):
    m = re.search(r"\(" + code + r"\):\s*([\d.,-]+)", prompt)
    return float(m.group(1).replace(",", "")) if m else None


def rationale(prompt):
    i = prompt.rfind("AGENCY VIEW")
    p = prompt[i:]
    lines = []
    for a, b, name, money in PAIRS:
        x, y = val(p, a), val(p, b)
        if x is None or y is None or abs(x - y) <= 1:
            continue
        lines.append(f"- {name}: agency {('$' if money else '')}{x:,.0f}, verified {('$' if money else '')}{y:,.0f}")
    return "Differences:\n" + ("\n".join(lines) if lines else "- none visible") + "\n"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    if sys.argv[1] == "data":
        out = D / "exp71_sft"; out.mkdir(parents=True, exist_ok=True)
        n_vis = 0
        for name in ("train", "valid"):
            with open(D / f"exp52_rlvr/{name}.jsonl") as fi, open(out / f"{name}.jsonl", "w") as fo:
                for line in fi:
                    r = json.loads(line)
                    rat = rationale(r["prompt"]); n_vis += "none visible" not in rat
                    fo.write(json.dumps({"prompt": r["prompt"],
                                         "completion": rat + run_lm.format_gold(json.loads(r["answer"]), "class")}) + "\n")
        print(f"wrote {out}; records with a visible difference: {n_vis}")
    elif sys.argv[1] == "subset":
        items = json.loads((ROOT / "experiments/eval_pilot/items_confirm.json").read_text())
        vis = [it["item_id"] for it in items
               if any(num(it["fields"].get(a)) is not None and num(it["fields"].get(b)) is not None
                      and abs(num(it["fields"][a]) - num(it["fields"][b])) > 1 for a, b in FIELD_PAIRS)]
        (ROOT / "experiments/eval_pilot/exp71_visible_ids.txt").write_text("\n".join(vis) + "\n")
        print(f"visible-difference items: {len(vis)} of {len(items)}")
