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

### Results

Pending.
