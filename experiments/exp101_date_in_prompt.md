# Experiment 101 — telling the model the date

**Date:** 2026-10-20 · **Code:** `exp85_mcq_rag_task.py` amendment 8 (`date_in_prompt`), `exp101_analyze.py`, `queue_exp101.sh` · **Logs:** `snap-qc-data/derived/exp101_logs/`

### Why

In exp100 the 31B read the new supersession notes and still answered under pre-H.R. 1 rules. On a refugee question it wrote that P.L. 119-21 changes "may impact eligibility in the far future (specifically for applications on or after April 1, 2026)."

The Cornell agent prompt never states the date. The tools are dated 2026-06-01 through the server default, but the model assumes the present is around its training date, so an April 2026 implementation date reads as a future change.

On the six refugee and asylee questions keyed to post-H.R. 1 rules:
- **0 of 6:** every agent run so far, with or without the notes.
- **5 of 6:** exp98's combined arm. Its attached passages carry in-force labels, and it had thinking on.

### Method (pre-registered)

All runs: Gemma 4 31B agent, as_of 2026-06-01, thinking off, temperature 0.

**Corpus:** state-policy-docs after the October 19 merge, which adds 16 documents to exp100's corpus, among them ACIN I-29-26E. Arms 1 and 2 run the same day on that corpus.

| # | Questions | Arm |
|---|---|---|
| 1 | Cornell citizenship (34) | baseline: no date in the prompt, no notes (same-day rerun) |
| 2 | Cornell citizenship (34) | date in the prompt ("Answer under the rules in force on June 1, 2026.") |
| 3 | Cornell citizenship (34) | date in the prompt + supersession notes + precedence sentence |
| 4 | Cornell, all 500 | date in the prompt + notes + precedence + check step (scored before and after the check) |

**Post-hoc label:** the date comes from the exp98 audit, so arms 2–4 are labeled post-hoc, like every 2026-dated arm.

**Readouts:**
- accuracy;
- the six refugee and asylee questions;
- paired bootstrap CIs (2,000 resamples, seed 101): arms 2 and 3 vs arm 1; arm 4 vs exp98 arm 3 and vs exp100's full run.

Arm 4's comparisons with earlier runs are also affected by the 16 added documents, which the write-up will note.

**Hypotheses:**
- **H1:** the date in the prompt raises citizenship accuracy over the same-day baseline, and gets at least 3 of the 6 refugee and asylee questions right.
- **H2:** on all 500, arm 4 before the check beats exp98 arm 3 (89.6%).

### Amendment (2026-10-20, 18:50, before any exp101 run)

**The full run (arm 4) is replaced.** exp100's notes didn't help, and the check step added only +0.4 on the plain agent (exp99, exp100). The one setup with a clear positive signal is exp98's combined arm:
- **Citizenship:** 85.3% against 70.6% for the plain agent, and 5 of the 6 refugee and asylee questions right.
- **Hardest questions:** 81.3% against 72.0%.
- **The check step:** +2.8 [+1.4, +4.2], with 14 answers fixed and none broken.

That arm's 5 errored questions were all context overflows ("Context size has been exceeded"). LM Studio divides the loaded context across its 4 slots, so each request had about 33k tokens.

**New arm 4:** exp98's combined arm plus the date.
- agent + date-filtered passages (as_of 2026-06-01) + thinking high + check step + date in the prompt;
- no supersession notes;
- 31B loaded with a 262,144-token context, about 65k a slot;
- `--retry-on-error 2`.

**Arms 1–3** run unchanged, on the same load.

**Readouts for arm 4:**
- vs exp98 arm 4 (paired);
- vs exp98 arm 3, the best so far at 89.6%;
- vs GPT-6 Astra's untuned 92.2%;
- the six refugee and asylee questions, errors, and the check step's changes.

**H2 is replaced:** arm 4 after the check beats exp98 arm 3 (89.6%).

**Run time:** expected 30–40 hours. exp98 arm 4 took 37.5 hours.

### Results

<!-- AUTO-RESULTS:START -->
Scored 2026-10-20 21:00 by `exp101_analyze.py` (aggregate only).

| Arm | n | Accuracy | Refugee/asylee (6) | Errored |
|---|---|---|---|---|
| citizenship 34: baseline (same day) | 34 | 79.4% | 0 of 6 | 0 |
| citizenship 34: date in prompt | 34 | 70.6% | 0 of 6 | 0 |
| citizenship 34: date + notes + precedence | 34 | 85.3% | 5 of 6 | 0 |
| exp98-4: combined, after check | 500 | 89.2% | 5 of 6 | 5 |
| exp98-3: 31B agent 2026 | 500 | 89.6% | 0 of 6 | 0 |
| exp100: notes + precedence, after check | 500 | 89.0% | 0 of 6 | 0 |
| exp100: notes + precedence, before check | 500 | 88.6% | 0 of 6 | 0 |

| Paired contrast (95% CI) | Difference |
|---|---|
| citizenship 34: date in prompt − citizenship 34: baseline (same day) (n = 34) | -8.8 [-17.6, +0.0] |
| citizenship 34: date + notes + precedence − citizenship 34: baseline (same day) (n = 34) | +5.9 [-8.8, +23.5] |
<!-- AUTO-RESULTS:END -->
