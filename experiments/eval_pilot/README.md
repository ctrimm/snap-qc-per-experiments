# QC-variance eval pilot — Mac Studio runbook

**Eval v1.1 (2026-10-05).** Changes from v1, all from the exp30 Mac Studio
runs (see `../exp30_eval_pilot.md`):
- `max_tokens` 1500 (was 400): at 400, 13–65% of dollar answers were cut
  off before the `T6:` line; at 1500, 0% for gemma-4-31b.
- Prompt condition locked to **few-shot + jargon** (few-shot removes
  classification truncation; jargon vs plain tied, jargon truncates less).
- T6 is scored and reported but **left out of the composite and the win
  count**: with RAWBEN withheld, no model tested beats the always-$0 dummy.
  Gate leg 2 is now ≥ 4 wins of 5 tasks (was 4 of 6).
- `score.py --ref-preds` reports composite vs a reference model (e.g. the
  untuned 31B). Informational only, not part of PASS.
- `run_lm.py --ids FILE` / `score.py --ids FILE` restrict to an item subset
  (e.g. `subset_300.txt`, a stratified 300-item cut).

v1 results (`preds_base_*`, `score_base_*`) stay as recorded under v1 rules.

Runs the frozen 1,400-item QC-variance eval (exp17 design, exp30 pilot build)
against a local model served by LM Studio's OpenAI-compatible endpoint.
No raw QC microdata needed on this machine: `items.json` ships the frozen
item IDs, labels, and de-identified input fields (public-use values only,
no PII). Nothing here trains anything.

## Prereqs

1. **LM Studio** installed, with any chat-capable local model loaded
   (the pilot was designed around a ~30B-class model; smaller models work
   but expect noisier scores).
2. In LM Studio, start the local server (Developer tab → "Start server",
   default `http://localhost:1234/v1`). Note the exact model id shown in
   LM Studio (e.g. `qwen3-30b-a3b-instruct-2507`).
3. Python 3.9+ with `requests` (`pip install requests`). Everything else is
   stdlib. No torch / transformers / GPU needed.

## Setup

```bash
cd experiments/eval_pilot   # this directory
export QC_EVAL_MODEL="<model id exactly as shown in LM Studio>"
# optional overrides:
# export QC_EVAL_BASE_URL="http://localhost:1234/v1"
# export QC_EVAL_API_KEY="..."   # only if your endpoint needs one
```

Sanity check the prompt rendering before spending GPU time:

```bash
python3 run_lm.py --dry-run --condition zero --template jargon
```

## Step 1 (v1 only) — run the base model (4 prompt conditions)

Under v1.1 the condition is locked, so a base run is one command:

```bash
python3 run_lm.py --condition few --template jargon --split test \
    --out preds_<model>_few_jargon.jsonl     # max_tokens 1500 by default
```

The four-condition sweep below is how v1 chose that condition:

Each condition runs the 1,200 locked test items (2 prompts per item:
classification T1–T5 + dollar T6). At ~2–4 s per prompt on a 30B model,
expect roughly **1.5–2.5 hours per condition**, ~6–10 hours for all four.
Re-running is safe: finished items are skipped.

```bash
python3 run_lm.py --condition zero --template jargon --split test \
    --out preds_base_zero_jargon.jsonl
python3 run_lm.py --condition zero --template plain  --split test \
    --out preds_base_zero_plain.jsonl
python3 run_lm.py --condition few  --template jargon --split test \
    --out preds_base_few_jargon.jsonl
python3 run_lm.py --condition few  --template plain  --split test \
    --out preds_base_few_plain.jsonl
```

The few-shot examples are drawn from the 200-item **dev** split only —
the test set is never used for prompt iteration.

## Step 2 — run the synthetic-pretrained model

Point `QC_EVAL_MODEL` at the pretrained checkpoint (same tokenizer family
as the base) and run the locked v1.1 condition:

```bash
export QC_EVAL_MODEL="<synthetic-pretrained model id>"
python3 run_lm.py --condition few --template jargon --split test \
    --out preds_tuned_few_jargon.jsonl
```

## Step 3 — score and check the gate

```bash
# dummy/most-frequent baselines (reference; also committed as baselines.json)
python3 score.py --items items.json --dummy --split test

# base model alone
python3 score.py --items items.json \
    --preds preds_base_few_jargon.jsonl --split test

# gate decision: tuned vs its own base (same prompt condition);
# --ref-preds adds an informational comparison against the untuned 31B
python3 score.py --items items.json \
    --preds preds_tuned_few_jargon.jsonl \
    --base-preds preds_base_few_jargon.jsonl \
    --ref-preds preds_base_few_jargon_31b.jsonl \
    --split test --out gate_few_jargon.json

# year-robustness cut (FY2024 slice, reported separately)
python3 score.py --items items.json \
    --preds preds_tuned_few_jargon.jsonl \
    --base-preds preds_base_few_jargon.jsonl \
    --split test_2024 --out gate_2024.json
```

## Reading the score table

```
task  primary   acc      n
t1      0.812   0.845   1200     # detection macroF1
t2      0.701   0.760   1200     # finding macroF1
t3      0.355   0.402    712     # element macroF1 (error cases w/ primary)
t4      ...                      # nature macroF1
t5      ...                      # cause macroF1
t6      0.688     --    1200     # dollar direction accuracy
composite (T1-T5): 0.412
```

- `primary` is the metric that counts: macroF1 for T1–T5, direction
  accuracy for T6. (T6 secondaries — MAE, tolerance-band credits,
  exact-match rate — are in the JSON.)
- `composite` = mean over T1–T5 (v1.1; T6 reported only) of
  (model − dummy) / (ceiling − dummy), i.e. "fraction of the way from
  guessing to the best tabular reference". T2/T3 ceilings are the published
  real→real GBM numbers (0.832 / 0.422); the rest use 1.0 as a placeholder
  until reference numbers exist — flagged in the JSON under `ceilings`.

## What "passes" means (gate 3, this half)

The synthetic-pretrained model passes **iff all three hold** against its
own base model on the same prompt condition:

1. **Composite strictly higher**, with the 95% paired-bootstrap CI
   (10,000 resamples) excluding zero.
2. **Wins on at least 4 of the 5 composite tasks** (T1–T5) individually
   (per-task bootstrap CI excludes zero). v1 was 4 of 6 with T6 included.
3. **T3 element macroF1 ≥ 0.214** — the GBM synth→real floor. A language
   model reading the actual case facts should beat a GBM trained on
   synthetic tabular features at naming the error element.

`score.py` prints the verdict as `PASS=True/False` when `--base-preds` is
given. The other half of gate 3 (CalFresh MCQ) is scored separately.

## Choosing the prompt condition (open question 6)

The pilot runs all four conditions on the base model so the choice is made
from data, not taste: keep the condition with the best **discrimination**
(dummy < base gap, and later base < tuned gap), not the highest absolute
score. Few-shot can inflate scores while compressing the gap — if it does,
prefer zero-shot.

## Files

| file | what |
|---|---|
| `items.json` | frozen sample: ids, labels, flags, input fields (1,400 items) |
| `denylist.txt` | `fiscal_year case_id_hash` per item — exclude from all training |
| `sampling_report.json` | actual-vs-plan tables, rule-agreement + dollar stats |
| `baselines.json` | dummy/most-frequent baselines on the 1,200 test items |
| `sample.py` | frozen sampler (needs the raw QC CSVs; sandbox-side) |
| `labels.py` | label pipeline + deterministic prompt rendering |
| `score.py` | scorer: per-task metrics, composite, bootstrap gate |
| `run_lm.py` | OpenAI-compatible runner (this machine) |

## Troubleshooting

- `QC_EVAL_MODEL is not set` → export it with the exact id from LM Studio.
- Connection refused → LM Studio server not started (Developer tab).
- `parse_ok: false` rows in the JSONL → the model didn't follow the answer
  format; they count as wrong. If frequent, the model may need the few-shot
  condition or a chat template that follows instructions better.
- Slow: lower `--limit` for a quick smoke (`--limit 20`), or run one
  condition overnight.
