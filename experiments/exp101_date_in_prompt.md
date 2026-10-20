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

### Results

<!-- AUTO-RESULTS:START -->
(pending: filled in by `exp101_analyze.py` when the runs finish)
<!-- AUTO-RESULTS:END -->
