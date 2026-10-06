"""Exp52 SFT data: answer-only supervised pairs from the GRPO corpus.

Converts exp52_rlvr_dataset.py output ({"prompt", "answer"}) into mlx_lm.lora's
{"prompt", "completion"} format, where the completion is the gold answer block
exactly as the eval's few-shot examples show it (run_lm.format_gold). No
reasoning text: this tests whether gemma-4-e4b can learn the case -> labels
mapping at all from a dense signal (the GRPO sweep only learned label priors).

Usage: python3 experiments/exp52_sft_data.py SRC_DIR OUT_DIR
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "eval_pilot"))
import run_lm  # noqa: E402

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for name in ("train", "valid"):
    with open(src / f"{name}.jsonl") as fi, open(out / f"{name}.jsonl", "w") as fo:
        for line in fi:
            r = json.loads(line)
            fo.write(json.dumps({"prompt": r["prompt"],
                                 "completion": run_lm.format_gold(json.loads(r["answer"]), "class")}) + "\n")
print(f"wrote {out}")
