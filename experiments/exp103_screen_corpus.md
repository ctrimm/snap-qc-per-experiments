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

### Amendment (2026-10-21, 15:35, after A0, before A1–A3 results): arm A3 added

**What A0 showed:** the new corpus alone scored 2.6 points below exp98 arm 3 on the screening set ([−7.8, +2.1]). exp102 arm 1 (same corpus plus date + notes + precedence) scored 6.3 points below A0, so the prompt changes cost more than the corpus. The precedence sentence ("follow a statute or newer state guidance over an older regulation") may push the model toward letters on income questions.

**A3:** letter weighting + date in the prompt + supersession notes, without the precedence sentence. It runs after A2.

**New readouts:**
- A3 − A1 (date + notes, given weighting);
- A2 − A3 (the precedence sentence);
- exp102 arm 1 − A0 (the prompt effect without weighting, from existing runs).

A3 joins the decision rule on the same terms. This amendment was made after seeing A0, so the A3 comparison is labeled post-hoc.

### Results

<!-- AUTO-RESULTS:START -->
Scored 2026-10-22 04:30 by `exp103_analyze.py` (aggregate only; screening set chosen from test results).

| Arm | All (193) | Hard (153) | Controls (40) | Citizenship (34) | Refugee/asylee (6) |
|---|---|---|---|---|---|
| A0: new corpus | 70.5% | 62.7% | 40 of 40 | 70.6% | 0 of 6 |
| A1: + letter weighting | 71.0% | 64.1% | 39 of 40 | 73.5% | 0 of 6 |
| A2: + weighting + date + notes + precedence | 69.9% | 63.4% | 38 of 40 | 88.2% | 5 of 6 |
| A3: + weighting + date + notes (no precedence) | 68.9% | 63.4% | 36 of 40 | 82.4% | 5 of 6 |
| ref exp98-3: old corpus, plain | 73.1% | 66.0% | 40 of 40 | 70.6% | 0 of 6 |
| ref exp102-1: new corpus + date + notes, no weighting | 64.2% | 54.9% | 40 of 40 | 91.2% | 6 of 6 |

| Effect (95% CI) | Difference |
|---|---|
| letter weighting: A1 − A0 | +0.5 [-3.6, +4.7] |
| prompt given weighting: A2 − A1 | -1.0 [-5.7, +3.6] |
| date + notes given weighting: A3 − A1 | -2.1 [-7.3, +3.1] |
| precedence sentence: A2 − A3 | +1.0 [-4.1, +5.7] |
| corpus: A0 − exp98-3 | -2.6 [-7.8, +2.1] |
| A2 − exp98-3 | -3.1 [-9.3, +3.1] |
| A3 − exp98-3 | -4.1 [-9.8, +1.6] |
| prompt, no weighting: exp102-1 − A0 | -6.2 [-13.0, +0.5] |

**Decision rule:** no arm qualifies (needs +3 over exp98-3 on this set and at most 2 controls lost).
<!-- AUTO-RESULTS:END -->
