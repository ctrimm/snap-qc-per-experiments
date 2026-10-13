# Experiment 92 — teaching E4B the 31B's tool use (distillation)

**Date:** 2026-10-12 · **Code:** `exp92_build_train.py` (training questions), `exp92_make_sft.py` (trajectories to SFT data), `exp92_run.sh` (pipeline; pre-registered here) · **Data:** `experiments/exp92_train.jsonl` · **Outputs:** `../snap-qc-data/derived/exp92/`, `exp92_logs/`, model `~/.lmstudio/models/snap-qc/gemma-4-e4b-exp92-tooluse`

### Why

exp91 showed that prompts and schemas fix E4B's mechanical tool calls, but not the behavior that makes the 31B better on open policy questions: looking up the rule, opening the cited section and reading it before answering. On the Cornell quiz, 31B calls `get_section` 0.59 times per question and E4B 0.01–0.07, even when told to. exp92 tests whether E4B can learn that behavior from the 31B's own tool-use transcripts.

### Method (pre-registered)

1. **Training questions, never from a test set.**
   - 250 table and benefit-amount questions from the exp87 generator with seed 92 (exact duplicates of exp87 questions dropped).
   - Open rule questions written by Gemma 4 31B from 397 passages sampled (seed 92) from 7 CFR 271–275, the Food and Nutrition Act (before and after P.L. 119-21), FNS Handbook 310, MPP Division 63 and the CDSS letters. Each must parse, have five distinct options, and carry an evidence phrase found in its passage.
   - Any question sharing a 10-word sequence with the Cornell quiz, exp87 or exp90 is dropped, and the merged file must pass the overlap audit against the Cornell quiz. The quiz is never used for training, per its licence.
2. **Teacher transcripts:** the Gemma 4 31B agent (exp87 task, plain agent prompt, tools over the full corpus) answers every training question. Only correctly answered transcripts are kept.
3. **SFT data:** one example per model turn (each tool call, and the final submit), with the tool schemas as served. Tool results are cut at 8,000 characters. 10% of questions are held out for validation loss only.
4. **Training:** LoRA on `mlx-community/gemma-4-e4b-it-bf16`, following the exp52 recipe (rank 16, scale 20, 16 layers, lr 1e-5, batch 4, `--mask-prompt`, thinking off), 8,192-token window, 2 epochs, seed 92. **The final checkpoint is used;** none is chosen on a test set.
5. **Evaluation:** base and tuned are the same bf16 MLX model in the same LM Studio engine, 128K context, 4 slots, temperature 0. Arms:

| Set | Mode |
|---|---|
| Cornell quiz | Agent, dated 2025-06-01 (exp85 task, plain agent prompt) |
| Cornell quiz | No tools (does tool training cost policy knowledge?) |
| exp90 hard | Agent |
| exp87 held-out | Agent (in-distribution for the structured part: same templates, different seed) |

Readouts: accuracy and paired bootstrap CIs (tuned − base, seed 92); tool use (`get_section` per question, the share of calls carrying `as_of`, calls per question); errors and missing answers.

Hypotheses:
- **H1:** on the Cornell quiz with tools, tuned beats base (CI above 0), and tuned `get_section` use is at least 0.3 per question.
- **H2:** on exp90, tuned beats base by at least 5 points.
- **H3:** no-tools Cornell accuracy doesn't drop by more than 2 points (CI lower bound above −4).

If H1 fails, the reading behavior isn't learnable from about 500–600 transcripts at this size. Routing open questions to the 31B, or attaching date-filtered passages, stays the recommendation.

### Deviations from the pre-registration (recorded before results were read)

1. **No structured questions in training.** The overlap guard dropped all 250 structured questions: they share template phrases with exp87 ("what is the maximum monthly SNAP allotment for a household of…"). Training used 374 open questions only (21 failed the evidence check). Consequences: no calculator transcripts in training, and exp87 is out of distribution.
2. **Rebuilt model files.** `mlx_lm.fuse` wrote a text-only Gemma 4 (665 tensors; vision and audio towers and the vision config dropped). LM Studio loaded it without stopping at the end-of-turn token, so it generated to the limit (5.5 hours on a 2-minute arm; that partial run is discarded as `_void_tuned_textonly_cornell_notools`). With the adapter loaded directly in `mlx_lm`, the model stops normally. The evaluated model is the base model's full file set with the 665 fine-tuned language-model tensors swapped in (112 changed by training, as expected for LoRA on 16 layers × 7 projections). The base arms were unaffected.

### Results

| Stage | Result |
|---|---|
| Training questions | 374 open questions (397 generated) |
| 31B teacher | 336 of 374 correct, 1,140 examples (1,028 train, 112 valid) |
| Training | 514 iterations; final train loss 0.264, validation loss 0.533; peak memory 120 GB; about 5 hours |

| bf16 E4B, same engine and settings | Base | Tuned | Tuned − base (95% CI) | Gained / lost |
|---|---|---|---|---|
| Cornell, no tools | 72.2% | 71.8% | −0.4 [−2.0, +1.2] | 8 / 10 |
| **Cornell, agent (dated)** | **76.8%** | **66.0%** | **−10.8 [−15.0, −7.0]** | 28 / 82 |
| exp90, agent | 81.3% | 73.3% | −8.0 [−17.3, +1.3] | 4 / 10 |
| exp87, agent | 76.1% | 73.7% | −2.5 [−10.3, +4.9] | 42 / 48 |

exp87 by part: table 94.2% → 65.8%, computation 42.5% → 83.8%, rule 88.4% → 76.7%.

**Tool use on Cornell, per question:**

| | get_section | get_passages | lookup_rule | All calls |
|---|---|---|---|---|
| Base | 0.00 | 0.21 | 0.87 | 1.09 |
| Tuned | 1.17 | 2.30 | 0.99 | 4.49 |

**Where the loss comes from:**

| | Answered | Accuracy on answered |
|---|---|---|
| Cornell, base | 500 of 500 | 76.8% |
| Cornell, tuned | 433 of 500 | 76.2% |
| exp90, base | 74 of 75 | 82.4% |
| exp90, tuned | 67 of 75 | 82.1% |

- All 67 unanswered Cornell questions (and 8 on exp90) hit the 30-message limit.
- The tuned model's conversations are about twice as long (median 39K characters vs 19K; 90th percentile 202K), with repeated `get_passages` loops (up to 12 calls in a row).
- The dates it passed on Cornell were almost all 2025-06 (the server default), so wrong dates are not the cause.

### Verdict

**Did not hold.**

- **H1 failed.** The tuned model learned the behavior: it calls `get_section` 1.17 times per question, above the 0.3 bar. But accuracy fell 10.8 points.
- **H2 failed:** −8.0 on exp90, CI including zero.
- **H3 held:** no knowledge lost without tools.

Distillation taught E4B to look things up and read them, but not when to stop. Every lost point is an unanswered question that ran into the message limit. On the questions it answered, reading the rule gave E4B no gain (76.2% vs 76.8%, 82.1% vs 82.4%), unlike the 31B. Two likely contributors:
- **Training/inference mismatch:** tool results were cut at 8,000 characters in training but returned in full at inference, so the model met much longer contexts than it was trained on.
- **One-sided examples:** only the 31B's successful, fairly short searches, so no examples of giving up a search and answering.

The computation gain on exp87 (+41 points, with no calculator training) and the table loss (−28) are unexplained and come from an out-of-distribution set. I'm not drawing conclusions from them.

**Bottom line for the small model:** for E4B, reading the governing section doesn't raise accuracy on the questions it answers, so more distillation is unlikely to pay. The practical design stays:
- the exp91 recipe for structured questions (dates, tables, calculator);
- date-filtered attached passages, or the 31B, for open policy questions.

### Next steps (only if the small model must answer open questions itself)

1. Match training and inference: cap tool results at 8,000 characters at inference (a server option) or train on full results.
2. Add a loop guard: refuse repeated identical calls and force an answer after N calls.
3. Include trajectories that stop early with an answer.

Then re-run the same pre-registered evaluation once.
