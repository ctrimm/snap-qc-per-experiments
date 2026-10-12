"""Exp92 — turn Gemma 4 31B tool-use trajectories (Inspect logs) into mlx-lm chat SFT data.

Keeps only questions the 31B answered correctly. Each model turn becomes one example: the conversation up to
and including that turn, with the tool schemas the model saw, so --mask-prompt trains exactly that turn (the
tool call, or the final submit). Tool results are cut at 8,000 characters to fit an 8,192-token training
window (marked "[...truncated for training]"); system prompt, user turn and tool schemas are kept as served.
Reasoning blocks are dropped (thinking is off when E4B is evaluated). 10% of questions (seed 92) go to valid.
Usage: python experiments/exp92_make_sft.py LOG_DIR OUT_DIR
"""
import glob
import json
import random
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

CUT = 8000


def text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for c in content or []:
        if getattr(c, "type", "") == "text":
            parts.append(c.text)
    return "".join(parts)


def tool_schemas(sample):
    for ev in sample.events or []:
        if getattr(ev, "event", "") == "model" and getattr(ev, "tools", None):
            out = []
            for t in ev.tools:
                params = t.parameters.model_dump(exclude_none=True) if hasattr(t.parameters, "model_dump") else t.parameters
                out.append({"type": "function", "function": {"name": t.name, "description": t.description, "parameters": params}})
            return out
    return None


def convert(msgs):
    out = []
    for m in msgs:
        if m.role == "system":
            out.append({"role": "system", "content": text_of(m.content)})
        elif m.role == "user":
            out.append({"role": "user", "content": text_of(m.content)})
        elif m.role == "assistant":
            d = {"role": "assistant", "content": text_of(m.content).strip()}
            if m.tool_calls:
                d["tool_calls"] = [{"id": tc.id, "type": "function",
                                    "function": {"name": tc.function, "arguments": tc.arguments or {}}} for tc in m.tool_calls]
            out.append(d)
        elif m.role == "tool":
            c = text_of(m.content)
            if len(c) > CUT:
                c = c[:CUT] + "\n[...truncated for training]"
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "name": m.function, "content": c})
    return out


def main(log_dir, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    log = read_eval_log(sorted(glob.glob(f"{log_dir}/*.eval"))[-1])
    samples = [s for s in log.samples if float(list(s.scores.values())[0].value or 0) == 1.0 and not s.error]
    ids = sorted(str(s.id) for s in samples)
    random.Random(92).shuffle(ids)
    valid_ids = set(ids[: len(ids) // 10])
    rows = {"train": [], "valid": []}
    turns = 0
    for s in samples:
        tools = tool_schemas(s)
        msgs = convert(s.messages)
        split = "valid" if str(s.id) in valid_ids else "train"
        for i, m in enumerate(msgs):
            if m["role"] == "assistant" and (m.get("tool_calls") or m["content"]):
                rows[split].append({"messages": msgs[: i + 1], "tools": tools}); turns += 1
    for k, v in rows.items():
        random.Random(92).shuffle(v)
        (out / f"{k}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in v))
    print(json.dumps({"samples": len(log.samples), "correct_kept": len(samples), "examples": turns,
                      "train": len(rows["train"]), "valid": len(rows["valid"])}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
