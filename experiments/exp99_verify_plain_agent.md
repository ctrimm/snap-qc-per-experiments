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

### Results

<!-- AUTO-RESULTS:START -->
(pending: filled in by `exp99_analyze.py` when the run finishes)
<!-- AUTO-RESULTS:END -->
