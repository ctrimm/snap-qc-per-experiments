# Experiment 103 — screening the expanded corpus on hard questions before the next full run

**Date:** 2026-10-21 · **Code:** `exp103_build_screen.py`, `exp103_analyze.py`, `queue_exp103.sh`, `exp85_mcq_rag_task.py` amendment 9 (`subset=ids:`, `letter_decay`), state-policy-docs `d7e8b55` (`STATE_POLICY_LETTER_DECAY`) · **Logs:** `snap-qc-data/derived/exp103_logs/`

### Why

Each full Cornell run costs 10–40 hours. exp102 arm 1 (plain 31B agent + date + supersession notes + precedence, on the corpus with 458 more CDSS letters) fixed citizenship: 90.9% vs 69.7%, and 6 of 6 refugee and asylee questions. But it lost income and deduction questions (13 fixed, 28 broken), often after reading old letters such as ACL 12-25 from 2012.

Because the corpus and the prompt changed together, the cause is unclear. From here on, setups are screened on a hard subset first, and only a winner gets a full run.

**What changed in state-policy-docs:** an opt-in letter age weight. With `STATE_POLICY_LETTER_DECAY=1`, CDSS letter passages are ranked by their age on the question's date: weight 1.0 up to 5 years, 0.6 up to 10 years, 0.35 beyond.

### Method (pre-registered)

**Screening set** (`exp103_build_screen.py`, built after exp102 arm 1 finishes; ids kept in `snap-qc-data/derived`, not committed):
- **hard:** every question any 2026-dated 31B full run got wrong (exp98 arms 3 and 4, exp100 full, exp102 arm 1), plus all citizenship and difficulty-3 questions. About 150.
- **controls:** 40 questions all those runs got right (seed 103), as a regression check.

The set is chosen from test results, so screening scores are optimistic about absolute accuracy. They are for ranking setups, and a full 500-question run must confirm any winner.

**Arms:** all Gemma 4 31B agent, as_of 2026-06-01, corpus `d7e8b55`, 262k context, 4 connections, one arm at a time.

| Arm | Letter weighting | Date + notes + precedence |
|---|---|---|
| A0 | off | off |
| A1 | on | off |
| A2 | on | on |

**References**, from existing runs on the same ids:
- exp98 arm 3: old corpus, plain;
- exp102 arm 1: new corpus, date + notes + precedence, no weighting.

**Readouts:**
- accuracy on hard and on controls;
- citizenship and the six refugee and asylee questions;
- paired bootstrap CIs (2,000 resamples, seed 103): A1 − A0 is the weighting effect, A2 − A1 the prompt effect given weighting, A0 − exp98 arm 3 the corpus effect.

**Decision rule:**
- **Which arm wins:** the arm with the highest overall screening accuracy goes to a full 500-question run, if it beats exp98 arm 3 on the screening set by at least 3 points and loses at most 2 of the 40 controls.
- **If no arm qualifies:** no full run. The corpus mechanism is reworked first.

### Results

<!-- AUTO-RESULTS:START -->
(pending: filled in by `exp103_analyze.py` when the arms finish)
<!-- AUTO-RESULTS:END -->
