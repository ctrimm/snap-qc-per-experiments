# Experiment 87 — the rule tools on our own held-out question set

**Date:** 2026-10-11 · **Code:** `experiments/exp87_build_heldout.py` (builder), `exp87_rules.json` (hand-written rule questions), `exp87_heldout_task.py` (pre-registered in its docstring), `exp87_analyze.py`, `queue_after_exp86.sh` · **Data:** `experiments/exp87_heldout.jsonl` · **Logs:** `../snap-qc-data/derived/exp87_logs/`

### Why

The Cornell CalFresh quiz can only be used to evaluate (its license bans training use, and tuning retrieval on it would overfit the test set). It's also mostly recall that small models already have, and it doesn't say which rule answers each question, so retrieval can't be scored on it. exp87 builds a question set from the rulebook itself.

- **Every question is dated.** It starts "As of <date>", and the right answer depends on the rules in force that day.
- **Every question is tied to its governing citation.** That makes retrieval scorable: is the gold document among the passages the model saw?
- **The set is ours,** so it can be used for tuning.

### The set (about 240 questions)

- **Table questions (120):** figures from the FNS cost-of-living tables for a date in FY2024–27.
  - What's asked: maximum allotment, standard deduction, shelter cap, gross and net income limits, minimum allotment.
  - Distractors: mostly the same figure from other fiscal years, so using the wrong year's table gives a wrong answer.
- **Benefit computations (80):** the monthly benefit for a described household, scored by the state-policy-docs calculator (7 CFR 273.10(e)).
  - Distractors: common mistakes, such as the wrong year's tables, skipping the 20% earned income deduction, or applying the elderly/disabled rules wrongly.
- **Rule questions (43):** hand-written from cited passages.
  - Each question carries an evidence phrase, and the builder checks that the phrase appears in the cited text in force on the question's date.
  - Pairs that differ before and after H.R. 1: ABAWD exemption age (over 55 vs over 65), the dependent-child exception, LIHEAP and the utility allowance.
  - Also included: California implementation questions from the CDSS letters, and the QC handbook.

The questions come from the state-policy-docs corpus only, and an overlap scan against the Cornell quiz confirms that.

### Corpus fix found while building

Two dated rule questions failed the evidence check, which exposed a gap in ecfr-markdown. It exported only the current text and one mid-2024 snapshot, so a version in force between those (for example 7 CFR 273.7 from November 18, 2024 to January 16, 2025) was missing. Dated lookups in such windows found nothing.

ecfr-markdown now has `--since`, which exports every distinct version in force since a date, with `effective_to` set to each version's last day. The corpus was re-exported with `--since 2024-01-01` (state-policy-docs branch `ecfr-versions`, merged after exp86 so exp86's corpus didn't change mid-run).

Known remaining gap: the pre-H.R. 1 statute text (U.S. Code 2024 edition) starts on 2025-01-06.

### Method (pre-registered)

See the task docstring.
- **E4B arms:** no tools; attached passages undated, hard-filtered to the question's date, and label mode; agent told the question's date and the `as_of` parameter.
- **31B arms:** no tools and agent.

Readouts: accuracy overall and by part; paired bootstrap CIs; retrieval hit rate per attached-passage arm; agent tool use, including how often `as_of` was passed and how often the calculator was used.

Hypotheses:
- **H1:** dated retrieval beats undated on table questions.
- **H2:** the agent, with the calculator, beats no tools on computation questions.
- **H3:** attached passages beat no tools overall.

### Results

Pending (queued after exp86).
