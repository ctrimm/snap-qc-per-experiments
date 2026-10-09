# Experiment 59 — confirmatory gate on a fresh test set

**Date:** 2026-10-09 · **Code:** `eval_pilot/sample.py`, `exp52_quick_eval.py`, `exp53_classifier_vs_llm.py`, `eval_pilot/score.py` · **Results:** `eval_pilot/gate_exp59_*.json`

## Pre-registration (committed before the fresh set was drawn or scored)

### Why

exp52's best model (SFT, step 400) passes all three gate legs under eval v1.2, but on a test set that is no longer clean: several candidates were scored on it, the reported model is the best of them, and v1.2's T3 rule was adopted after its effect was known. The T3 margin is 0.229 vs 0.210. This experiment re-tests the frozen model once, on real QC cases nobody has looked at, under rules fixed in advance. The result is reported as is.

### Frozen before drawing

| What | Fixed value |
|---|---|
| Tuned model | `mlx-community/gemma-4-e4b-it-bf16` + LoRA adapter `exp52_sft_runs/sft_lr1e-5_600/ckpt_400/adapters.safetensors` (SHA-256 `a0bf35d7aaa175a62884633310018b8b7de545f9ef5eb6151e8ef61895f5737e`) |
| Base model | the same bf16 model, no adapter, same runner |
| Runner | `exp52_quick_eval.py --split test --items eval_pilot/items_confirm.json`: direct load, greedy, class-only, max 64 tokens, thinking off |
| Prompt | locked v1.1 few-shot + jargon; the three few-shot examples come from the original `items.json` dev split (unchanged) |
| Items | `sample.py --seed 59 --exclude items.json --splits test_main,test_2024 --out-name items_confirm.json --prefix c`: 1,000 FY2021–23 + 200 FY2024 cases, same stratification plan as exp30, no case from the original 1,400 |
| Scoring | `score.py` eval v1.2 (9-class T3), `--split test` (all 1,200), seed 12345 bootstrap |
| Classifier reference | `exp53_classifier_vs_llm.py --items items_confirm.json` (deterministic; reproduces its exp53 predictions byte-for-byte on the old set) |

### Pass criteria (eval v1.2 gate, unchanged)

1. Composite (T1–T5) of tuned minus base: 95% bootstrap CI lower bound > 0.
2. Tuned beats base on at least 4 of the 5 tasks.
3. Tuned T3 9-class macro-F1 ≥ **0.210** (fixed number; not re-derived from the classifier on the new set).

PASS = all three. The FY2024-only slice, the classifier's scores on the new set, and chance-corrected skill are reported as information, not criteria.

### Rules for the run

- One scoring pass. A crash may be resumed; nothing is re-run because of its result.
- Parse failures count as wrong answers (scorer default).
- No change to the model, prompt, items, scorer or bar after the set is drawn. Any deviation is written here before results.
- Whatever the outcome, the whitepaper and README are updated to match: PASS removes "provisional"; failing only leg 3 becomes "passes two of three checks"; failing leg 1 or 2 means the exp52 result did not replicate.
- The original 1,200 test items are retired to development use from here on.

## Draw note (recorded before any scoring)

The draw ran as specified: 1,200 items (1,000 FY2021–23, 200 FY2024), zero overlap with the original 1,400, and the same finding mix (333 / 375 / 292 and 67 / 75 / 58). Because exp30 took every available case for some element buckets, the FY2021–23 part has fewer of those: arithmetic 15 (was 50), hhcomp 40 (52), other 17 (52), standard 9 (50), and none left for assets, income_total or reporting. Under v1.2 the rare buckets fold into "other" anyway. T3 is scored on 642 items (was 733), with a heavier share of earned, unearned, shelter and SUA. This follows from the pre-registered sampler; nothing was changed.

## Results

_Pending._
