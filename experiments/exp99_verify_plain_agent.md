# Experiment 99 — the answer check on the plain dated 31B agent

**Date:** 2026-10-19 · **Code:** `exp85_mcq_rag_task.py` (`-T verify=true`, amendment 6), `exp99_analyze.py`, `queue_exp99.sh` · **Logs:** `snap-qc-data/derived/exp99_logs/`

### Why

In exp98's combined arm (31B agent + passages + thinking, dated 2026-06-01), two effects cancelled out:
- **The check step** added about 3 points over the same run's first answers.
- **Thinking plus passages** cost about the same beforehand.

That arm ended level with the plain dated agent (about 90%). This experiment keeps only the part that helped: the plain dated agent (exp98 arm 3, 89.6%) plus the check step.

### Method (pre-registered)

- **Model:** Gemma 4 31B, LM Studio, 128k context, 4 slots, temperature 0, thinking off.
- **Arm:** agent with the four rule tools, server default as_of 2026-06-01, no attached passages, then `verify_answer`. That step is one no-tools turn: "Check your answer once before it is final…", reply with one letter.
- **Same as before:** exp98 arm 3's prompt and settings, plus the check. The pre-check letter is stored in `metadata["pre_verify"]`, so the arm is scored both ways from one run.
- **Data:** the 500 Cornell questions, run once.
- **Post-hoc label:** the 2026-06-01 date came from exp98's audit of this test set, so the result is labeled post-hoc, as in exp98.

**Readouts:**
- accuracy, final and pre-check;
- paired bootstrap CIs (2,000 resamples, seed 99): final vs pre-check (same run), final vs exp98 arm 3, final vs exp86;
- how many answers the check changed (wrong → right, right → wrong);
- accuracy on citizenship and difficulty-3 questions.

**Hypotheses:**
- **H1:** the check step raises accuracy within the run (CI above 0).
- **H2:** the final accuracy reaches at least 92.2%, GPT-6 Astra's untuned baseline in the Nava PBC field note.
- **H3 (descriptive):** the pre-check accuracy reproduces exp98 arm 3 (89.6%) within 1.5 points. Serving at temperature 0 with 4 slots is not fully deterministic.

### Deviation (2026-10-19, 19:45)

The run was paused after 270 of 500 questions, so exp100 could use the GPU first. It resumes after exp100 on the remaining 230 questions, with the same settings, into a second log. `exp99_analyze.py` merges the two logs.

The decision came after interim numbers had been seen: at 126 questions, the check had fixed none of the plain agent's answers and broken 2. So the pause was partly result-driven. The run will still be completed and scored as pre-registered.

### Results

<!-- AUTO-RESULTS:START -->
Scored 2026-10-19 19:47 by `exp99_analyze.py` (aggregate only). Reference: GPT-6 Astra, untuned baseline, 92.2% (Nava PBC).

| Arm | n | Accuracy | Citizenship | Difficulty 3 |
|---|---|---|---|---|
| exp86: 31B agent, dated 2025-06-01 | 500 | 88.8% | 73.5% | 73.3% |
| exp86: 31B no tools | 500 | 84.0% | 67.6% | 65.3% |
| exp98-1: E4B recipe + passages, 2026-06-01 | 500 | 77.0% | 70.6% | 72.0% |
| exp98-2: 31B no tools, thinking high | 500 | 85.8% | 67.6% | 66.7% |
| exp98-3: 31B agent, 2026-06-01 | 500 | 89.6% | 70.6% | 72.0% |
| exp98-4: 31B agent + passages + thinking, 2026-06-01, after check | 500 | 89.2% | 85.3% | 81.3% |
| exp99: 31B agent, 2026-06-01, after check | 270 | 92.6% | 77.8% | 85.7% |
| exp98-4: before check | 500 | 86.4% | 76.5% | 77.3% |
| exp99: before check | 270 | 93.0% | 83.3% | 88.1% |

| Paired contrast (95% CI, 2,000 resamples) | Difference |
|---|---|
| exp99: 31B agent, 2026-06-01, after check − exp99: before check | -0.4 [-1.5, +0.7] |
| exp99: 31B agent, 2026-06-01, after check − exp98-3: 31B agent, 2026-06-01 | +0.0 [-2.6, +2.6] |
| exp99: 31B agent, 2026-06-01, after check − exp86: 31B agent, dated 2025-06-01 | +0.4 [-2.6, +3.0] |
| exp98-4: 31B agent + passages + thinking, 2026-06-01, after check − exp98-4: before check | +2.8 [+1.4, +4.2] |
| exp98-4: 31B agent + passages + thinking, 2026-06-01, after check − exp98-3: 31B agent, 2026-06-01 | -0.4 [-3.2, +2.4] |
| exp98-3: 31B agent, 2026-06-01 − exp86: 31B agent, dated 2025-06-01 | +0.8 [-1.4, +2.8] |
| exp98-2: 31B no tools, thinking high − exp86: 31B no tools | +1.8 [-0.8, +4.4] |
| exp98-1: E4B recipe + passages, 2026-06-01 − exp95 (2025-06-01) | +0.6 [-2.8, +4.0] |

- **exp99:** the check changed 1 wrong answers to right and 2 right answers to wrong.
- **exp98-4:** the check changed 14 wrong answers to right and 0 right answers to wrong.

Best complete (500-question) arm: **exp98-3: 31B agent, 2026-06-01, 89.6%**. Arms with n < 500 are partial and not comparable on overall accuracy.
<!-- AUTO-RESULTS:END -->
