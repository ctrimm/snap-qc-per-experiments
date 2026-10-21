# Experiment 102 — two 31B setups on the expanded corpus

**Date:** 2026-10-20 · **Code:** `exp85_mcq_rag_task.py` (existing options), `exp102_analyze.py`, `queue_exp102.sh` · **Logs:** `snap-qc-data/derived/exp102_logs/` · **Corpus:** state-policy-docs `7a265f0`

### Why

Only one Cornell setup has shown clear gains: exp98's combined arm (31B agent + date-filtered passages + thinking + the check step).
- **Citizenship:** 85.3% against 70.6% for the plain agent, including 5 of the 6 refugee and asylee questions.
- **Hardest questions:** 81.3% against 72.0%.
- **The check step:** +2.8 [+1.4, +4.2], 14 answers fixed, none broken.

It ended at 89.2% overall, below the plain agent's 89.6%, partly because 5 questions overflowed the context.

Since then:
- **The corpus has grown** from about 3,980 to 4,461 documents: 16 documents from the Oct 18 update, and 458 CDSS letters cited by the corpus's own letters. These cover semi-annual reporting and mid-period actions (ACL 21-101/101E, ACIN I-58-13), the student and ABAWD handbooks, verification (ACL 20-48), categorical eligibility, the SUAS and noncitizen guidance (ACIN I-23-03).
- **The context problem is understood:** LM Studio divides the loaded context across its 4 slots. With 262,144 loaded, each request gets about 65k, enough for long thinking with passages.
- **Two ideas didn't help** and are left out: supersession notes (exp100) and the date in the prompt (exp101, citizenship 70.6% vs 79.4% same-day).

### Method (pre-registered)

- **Model and setup:** Gemma 4 31B, LM Studio, context 262,144, 4 slots, temperature 0.
- **Arm:** agent + passages + `--reasoning-effort high` + `verify=true`, as_of 2026-06-01. Same prompt as exp98 arm 4. No date in the prompt, no supersession notes, `--retry-on-error 2`.
- **Data:** all 500 Cornell questions, once.
- **Post-hoc label:** the 2026-06-01 date comes from the exp98 audit, so this run is labeled post-hoc, like every 2026-dated arm.

**Readouts:**
- accuracy before and after the check;
- citizenship, hardest questions, and the six refugee and asylee questions;
- errored questions;
- paired bootstrap CIs (2,000 resamples, seed 102) vs exp98 arm 4 (same setup, older corpus, smaller context), vs exp98 arm 3 (the best so far, 89.6%), and vs GPT-6 Astra's untuned 92.2% (reported, not paired).

The corpus and context change together, so a gain over exp98 arm 4 can't be split between them.

**Hypotheses:**
- **H1:** no questions error (exp98 arm 4: 5).
- **H2:** accuracy after the check beats exp98 arm 3 (89.6%).
- **H3 (descriptive):** whether it reaches 92.2%.

**Run time:** about 35–40 hours (exp98 arm 4: 37.5).

### Amendment (2026-10-20, 21:05, before any exp102 run): arm 1 added

exp101's last citizenship run, which finished after this file was written, scored 85.3% with 5 of 6 refugee and asylee questions right. That arm was the plain agent with the date in the prompt, supersession notes and the precedence sentence. The same-day baseline scored 79.4% (0 of 6), the date alone 70.6% (0 of 6), and in exp100 the notes alone 67.6% (0 of 6). So the date and the notes help only together, and the plain agent gets exp98's combined-arm citizenship result without thinking or passages.

The CI is wide: +5.9 [−8.8, +23.5] on 34 questions.

**Arm 1 (new, runs first):** the plain dated agent (exp98 arm 3) + date in the prompt + supersession notes + precedence sentence. No thinking, no passages, no check step.

**Arm 2:** the combined arm, as registered above. Context, corpus and retries are the same for both arms.

**Readouts for arm 1:** paired against exp98 arm 3 (old corpus, no date or notes) and against arm 2.

**H4:** arm 1 beats exp98 arm 3 (89.6%).

**Run time:** arm 1 about 10–12 hours, arm 2 about 35–40.

### Results

<!-- AUTO-RESULTS:START -->
(pending: filled in by `exp102_analyze.py` when the run finishes)
<!-- AUTO-RESULTS:END -->
