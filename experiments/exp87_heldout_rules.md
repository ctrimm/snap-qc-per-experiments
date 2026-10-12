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

243 questions per arm, no errors. Bootstrap uses 2,000 resamples, seed 87.

| Arm | All | Table (120) | Compute (80) | Rule (43) | Gold doc in passages |
|---|---|---|---|---|---|
| E4B no tools | 28.4% | 26.7% | 31.2% | 27.9% | — |
| E4B passages, undated | 36.6% | 25.8% | 30.0% | 79.1% | 20.2% |
| E4B passages, date filter | 68.7% | 87.5% | 32.5% | 83.7% | 54.3% |
| E4B passages, label dates (bug, see below) | 42.8% | 40.0% | 25.0% | 83.7% | 21.4% |
| E4B passages, label dates (fixed, rerun) | 69.1% | 85.0% | 36.2% | 86.0% | 54.7% |
| **E4B agent** | **84.8%** | 91.7% | 73.8% | 86.0% | — |
| 31B no tools | 35.0% | 26.7% | 33.8% | 60.5% | — |
| **31B agent** | **99.6%** | 100% | 100% | 97.7% | — |

| Paired contrast | All | Table | Compute | Rule |
|---|---|---|---|---|
| Filter vs undated (E4B) | **+32.1 [+25.5, +39.1]** | **+61.7 [+51.7, +70.8]** | +2.5 [−7.5, +12.5] | +4.7 [0.0, +11.6] |
| Label (fixed) vs filter (E4B) | +0.4 [−4.5, +5.3] | −2.5 [−6.7, +0.8] | +3.8 [−10.0, +17.5] | +2.3 [0.0, +7.0] |
| Agent vs no tools (E4B) | **+56.4 [+49.4, +63.4]** | +65.0 | **+42.5 [+27.5, +56.2]** | +58.1 |
| Agent vs no tools (31B) | **+64.6 [+58.4, +70.8]** | +73.3 | +66.2 | +37.2 [+23.3, +51.2] |

Agent tool use:

| Model | Calls per question | calculate_benefit | lookup_rule | get_passages | get_section | Calls carrying `as_of` |
|---|---|---|---|---|---|---|
| E4B | 1.65 | 0.80 | 0.45 | 0.39 | 0.01 | 86% |
| 31B | 1.12 | 0.44 | 0.53 | 0.08 | 0.06 | 100% |

**Label-mode bug.** The first label arm (42.8%) ran with a bug. Label mode applied a "current" filter before weighting by date, which dropped every version that ended before today: past fiscal-year tables, earlier CFR versions, and the pre-H.R. 1 statute. It's fixed in state-policy-docs with a regression test. The rerun (69.1%) is the valid label result. exp85's label arms had the same bug and were rerun too; see that chronicle.

### Verdict

**All three hypotheses held.**

- **H1, dating decides table questions:** filtered retrieval beat undated by 61.7 points on table questions, and put the gold document in the passages 54% of the time against 20%. Fixed label mode performs the same as the filter here.
- **H2, the calculator decides computation questions:** the E4B agent got 73.8% against 31.2%, and the 31B agent got 100%.
- **H3, passages beat no tools overall:** yes, mostly through dating.

On rule questions, any retrieval took E4B from 28% to 79–86%. The 31B agent reached 97.7%, up from 60.5% without tools.

Read these numbers for what they are. The set is open-book by construction:

- **Circular parts:** table answers come from the FNS tables in the corpus, and computation answers were generated by the same calculator the agent calls. Those parts test whether a model finds the right year's figure, or calls the calculator with the right inputs and date. They don't test whether the calculator is right; the calculator is checked separately by unit tests and a hand-worked example.
- **No-tools scores are near chance on tables (27%),** as expected: nobody memorizes each year's figures, and the distractors are the other years' values.
- **The rule questions are the fairer test,** but there are only 43, and I wrote them from the corpus, which may favor phrasing the retriever finds.

Even so, the result is clear. Small open models do far better with dated lookups and a calculator, and the agent beats attached passages because it can call the calculator. The 31B agent nearly saturates the set, so the next version needs harder rule questions: multi-step questions, conflicting sources, and California practice.

### Next steps

1. Extend the rule part to 150+ questions, with harder multi-step and conflicting-source items, written or reviewed by someone other than the retriever's author.
2. Tune retrieval on this set now that it exists, for example `k`, per-document caps, and whether to always include the governing citation from `lookup_rule`. Re-check once on the Cornell quiz.
3. Retrieval on undated questions is weak (20% hits). A tool that infers the date from the question, or defaults it sensibly, would help the attached-passage mode.
