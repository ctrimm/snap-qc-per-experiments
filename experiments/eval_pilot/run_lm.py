"""LM runner for the QC-variance eval pilot (exp30).

Runs frozen eval items against an OpenAI-compatible chat endpoint
(LM Studio default). Two prompts per item:
  - classification prompt (T1-T5, MCQ): sees NO benefit amounts at all
  - dollar prompt (T6, free-form integer): sees FSBEN, never RAWBEN

Prompt-format A/B (exp17 open question 6):
  --condition zero | few     (few-shot examples come from the dev split only)
  --template  jargon | plain

Env:
  QC_EVAL_BASE_URL  default http://localhost:1234/v1
  QC_EVAL_MODEL     model id as shown in LM Studio (required)
  QC_EVAL_API_KEY   optional

Usage:
  python3 run_lm.py --condition zero --template jargon --split test \\
      --out preds_zero_jargon.jsonl
  python3 run_lm.py --condition few --template plain --split test \\
      --out preds_few_plain.jsonl
  python3 run_lm.py --dry-run            # print one prompt, no HTTP calls

Output JSONL: {item_id, kind, condition, template, model, raw, parsed, parse_ok}.
Safe to re-run: item_ids already present in --out are skipped.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import labels as L  # noqa: E402

BASE_URL = os.environ.get("QC_EVAL_BASE_URL", "http://localhost:1234/v1")
MODEL = os.environ.get("QC_EVAL_MODEL", "")
API_KEY = os.environ.get("QC_EVAL_API_KEY", "")

SYSTEM = ("You are a SNAP Quality Control reviewer. Read the case record "
          "carefully and answer the review questions. Base your answers only "
          "on the record shown.")

T3_GLOSS = {
    "earned": "wages, self-employment, or other earnings misreported",
    "unearned": "Social Security, SSI, unemployment, or other unearned income misreported",
    "depcare": "dependent care deduction wrong",
    "shelter": "shelter costs wrong",
    "sua": "standard utility allowance wrong",
    "medical": "medical expense deduction wrong",
    "childsupport": "child support deduction wrong",
    "hhcomp": "wrong people counted in the household",
    "assets": "countable assets wrong",
    "arithmetic": "math or computation mistake",
    "reporting": "reporting-system or missed-report issue",
    "standard": "wrong standard deduction or standard used",
    "income_total": "total income computed wrong",
    "other": "something else",
}

OPT_T1 = ["error", "correct"]
OPT_T2 = ["correct", "overissuance", "underissuance"]
OPT_T3 = L.ELEMENT_BUCKETS
OPT_T4 = [str(c) for c in L.NATURE_CODES]
OPT_T5 = ["client", "agency", "no_fault", "other"]


def lettered(options, fmt):
    return "\n".join(f"({chr(65 + i)}) {fmt(o)}" for i, o in enumerate(options))


def build_class_prompt(fields, template, examples=()):
    case = L.render(fields, template=template, view="class")
    ex_text = ""
    for ex_fields, ex_labels in examples:
        ex_text += ("--- Example ---\n"
                    f"{L.render(ex_fields, template=template, view='class')}\n"
                    f"Correct answers:\n{format_gold(ex_labels, 'class')}\n\n")
    return f"""{SYSTEM}

{ex_text}--- Case under review ---
{case}

Questions. Answer each with the letter of the best option.

T1. Does this case contain a payment error?
{lettered(OPT_T1, lambda o: o)}

T2. What is the review finding?
{lettered(OPT_T2, lambda o: o)}

T3. What kind of variance best explains the error? (If T1 is correct, N/A.)
{lettered(OPT_T3, lambda o: f"{o}: {T3_GLOSS[o]}")}

T4. How did the variance happen? (If T1 is correct, N/A.)
{lettered(OPT_T4, lambda o: f"{o} {L.NATURE_LABELS[int(o)]}")}

T5. Who is primarily responsible for the variance? (If T1 is correct, N/A.)
{lettered(OPT_T5, lambda o: o)}

Format your answer exactly as:
T1: <letter>
T2: <letter>
T3: <letter or N/A>
T4: <letter or N/A>
T5: <letter or N/A>"""


def build_dollar_prompt(fields, template, examples=()):
    case = L.render(fields, template=template, view="dollar")
    ex_text = ""
    for ex_fields, ex_labels in examples:
        ex_text += ("--- Example ---\n"
                    f"{L.render(ex_fields, template=template, view='dollar')}\n"
                    f"Correct answer:\n{format_gold(ex_labels, 'dollar')}\n\n")
    return f"""{SYSTEM}

{ex_text}--- Case under review ---
{case}

T6. What is the dollar payment error for this case? Use a signed whole-dollar
integer: positive = overissuance (too much paid), negative = underissuance
(too little paid), 0 = correct. Small discrepancies may be within tolerance;
give your best estimate.

Format your answer exactly as:
T6: <integer>"""


def format_gold(labels, kind):
    if kind == "class":
        t1 = "A" if labels["t1"] == "error" else "B"
        t2 = chr(65 + OPT_T2.index(labels["t2"]))
        t3 = chr(65 + OPT_T3.index(labels["t3"])) if labels["t3"] else "N/A"
        t4 = chr(65 + OPT_T4.index(labels["t4"])) if labels["t4"] else "N/A"
        t5 = chr(65 + OPT_T5.index(labels["t5"])) if labels["t5"] else "N/A"
        return f"T1: {t1}\nT2: {t2}\nT3: {t3}\nT4: {t4}\nT5: {t5}"
    return f"T6: {labels['t6']}"


# ---------------------------------------------------------------- parsing

def _opt_letter(text, options):
    """Map a raw answer to one of options (letter or value text)."""
    if text is None:
        return None
    t = text.strip().strip("().").upper()
    if t in ("N/A", "NA", "NONE"):
        return None
    if len(t) == 1 and "A" <= t <= chr(64 + len(options)):
        return options[ord(t) - 65]
    low = text.strip().lower()
    for o in options:
        if low == o.lower() or low == o:
            return o
    # nature codes may be answered as bare numbers
    for o in options:
        if low == str(o).lower():
            return o
    return "UNPARSEABLE"


def _opt_int(text):
    if text is None:
        return None
    t = text.strip().upper()
    if t in ("N/A", "NA", "NONE"):
        return None
    m = re.search(r"[-+]?\$?\s?[\d,]+", t)
    if not m:
        return "UNPARSEABLE"
    try:
        return int(m.group(0).replace("$", "").replace(",", "").replace(" ", ""))
    except ValueError:
        return "UNPARSEABLE"


def parse_class(raw):
    ans = {}
    for m in re.finditer(r"^T?([1-5])\s*[:\-]\s*(.+?)\s*$",
                         raw or "", re.M | re.I):
        ans["t" + m.group(1)] = m.group(2)
    parsed = {
        "t1": _opt_letter(ans.get("t1"), OPT_T1),
        "t2": _opt_letter(ans.get("t2"), OPT_T2),
        "t3": _opt_letter(ans.get("t3"), OPT_T3),
        "t4": _opt_letter(ans.get("t4"), OPT_T4),
        "t5": _opt_letter(ans.get("t5"), OPT_T5),
    }
    ok = (parsed["t1"] in OPT_T1 and parsed["t2"] in OPT_T2
          and all(v != "UNPARSEABLE" for v in parsed.values()))
    return parsed, ok


def parse_dollar(raw):
    m = re.search(r"^T?6\s*[:\-]\s*(.+?)\s*$", raw or "", re.M | re.I)
    v = _opt_int(m.group(1) if m else None)
    # no "T6:" line at all (e.g. truncated at max_tokens) is a failed parse
    return {"t6": v}, (v is not None and v != "UNPARSEABLE")


# ---------------------------------------------------------------- LM call

def chat(prompt, temperature=0.0, max_tokens=400):
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens}
    last = None
    for attempt in range(4):
        try:
            r = requests.post(f"{BASE_URL}/chat/completions", headers=headers,
                              json=body, timeout=300)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001 - retry transient failures
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"chat failed after retries: {last}")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default=str(HERE / "items.json"))
    ap.add_argument("--condition", default="zero", choices=["zero", "few"])
    ap.add_argument("--template", default="jargon", choices=["jargon", "plain"])
    ap.add_argument("--split", default="test",
                    choices=["test", "test_main", "test_2024", "dev", "all"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--ids", default=None,
                    help="file of item_ids (one per line) to restrict the run to")
    args = ap.parse_args()

    if not args.dry_run and not MODEL:
        ap.error("QC_EVAL_MODEL is not set (model id as shown in LM Studio)")

    with open(args.items) as fh:
        items = json.load(fh)
    splits = {"test": ("test_main", "test_2024"), "all": ("test_main", "test_2024", "dev"),
              "test_main": ("test_main",), "test_2024": ("test_2024",),
              "dev": ("dev",)}[args.split]
    items = [it for it in items if it["split"] in splits]
    if args.ids:
        keep = set(Path(args.ids).read_text().split())
        items = [it for it in items if it["item_id"] in keep]
    if args.limit:
        items = items[:args.limit]

    examples = []
    if args.condition == "few":
        with open(args.items) as fh:
            dev = json.load(fh)
        dev = [d for d in dev if d["split"] == "dev"]
        # deterministic: first correct, first over, first under in dev order
        seen = set()
        for d in dev:
            f = d["finding"]
            if f not in seen:
                seen.add(f)
                examples.append((d["fields"], d["labels"]))
            if len(examples) == 3:
                break

    if args.dry_run:
        it = items[0]
        print("=" * 70 + "\nCLASSIFICATION PROMPT\n" + "=" * 70)
        print(build_class_prompt(it["fields"], args.template, examples))
        print("=" * 70 + "\nDOLLAR PROMPT\n" + "=" * 70)
        print(build_dollar_prompt(it["fields"], args.template, examples))
        print("=" * 70 + "\nGOLD:", format_gold(it["labels"], "class"),
              "|", format_gold(it["labels"], "dollar"))
        return

    out_path = Path(args.out or
                    f"preds_{args.condition}_{args.template}_{args.split}.jsonl")
    done = set()
    if out_path.exists():
        with open(out_path) as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    done.add((r["item_id"], r["kind"]))

    n_new = 0
    with open(out_path, "a") as fh:
        for n, it in enumerate(items):
            for kind, builder, parser in (
                    ("class", build_class_prompt, parse_class),
                    ("dollar", build_dollar_prompt, parse_dollar)):
                if (it["item_id"], kind) in done:
                    continue
                prompt = builder(it["fields"], args.template, examples)
                raw = chat(prompt, temperature=args.temperature,
                           max_tokens=args.max_tokens)
                parsed, ok = parser(raw)
                fh.write(json.dumps({
                    "item_id": it["item_id"], "kind": kind,
                    "condition": args.condition, "template": args.template,
                    "model": MODEL, "raw": raw, "parsed": parsed,
                    "parse_ok": ok}) + "\n")
                fh.flush()
                n_new += 1
            if (n + 1) % 25 == 0:
                print(f"  {n + 1}/{len(items)} items", flush=True)
    print(f"done: {n_new} new predictions -> {out_path}")


if __name__ == "__main__":
    main()
