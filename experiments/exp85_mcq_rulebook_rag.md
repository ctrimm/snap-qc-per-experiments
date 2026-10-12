# Experiment 85 — a fuller rulebook, and the rule put in front of the model, on the CalFresh quiz

**Date:** 2026-10-11 · **Code:** `experiments/exp85_mcq_rag_task.py` (pre-registered in its docstring), `exp85_run.sh` · **Logs:** `../snap-qc-data/derived/exp85_logs/`

### Hypothesis

exp84 found the state-policy-docs tools didn't help Gemma 4 E4B (71.6% → 68.6%). Two things could explain it: the corpus held mostly recent California letters about H.R. 1 rather than the rules most questions test (deductions, students, household composition), and the model searched on every question but read a document on only 14% of them, answering from 320-character snippets. Since then the corpus has gained the federal and California rulebooks (CFR for 15 programs, the Food and Nutrition Act, FNS Handbook 310, the FY2024–27 FNS tables, California MPP Division 63; about 3,300 documents, up from 507) and four new tools that return rule text with citations (get_passages, lookup_rule, get_section, calculate_benefit). If either was the problem, E4B should now gain.

### Method

The same 500 CalFresh questions and E4B build as exp84 (LM Studio, Q4_K_M, 128K context, temperature 0). Two retrieval modes:

- **Auto:** no agent. The top 5 passages for the question (California plus federal, at most 2 per document, about 300–600 words each) are put in the prompt.
- **Agent:** a ReAct agent with the four new tools, one attempt, at most 30 messages.

**Amendment before any scored run.** Cory pointed out the question set predates H.R. 1 (July 4, 2025). A check found only 1 of the old corpus's 326 documents was in force on 2025-06-01; it is almost all post-H.R. 1 letters. So exp84's tools were mostly handing the model rules from after the quiz was written. The design now dates the retrieval instead of pairing old and new corpora in every mode. Six runs:

| Arm | Mode | Corpus | Date filter |
|---|---|---|---|
| 1 | no tools | — | — |
| 2 | auto | old (exp84's, state-policy-docs `e20d2e0`) | none |
| 3 | auto | new | none |
| 4 | auto | new | rules in force on 2025-06-01 |
| 5 | agent | new | rules in force on 2025-06-01 (server default, so the model needn't pass it) |
| 6 | agent | new | none |

The same server code serves both corpora. Dated arms see the CFR (mid-2024 versions where the text has changed since), the FY2025 FNS tables, Handbook 310, MPP Division 63, and the Food and Nutrition Act as it stood before H.R. 1. That last one was a second amendment, made before any retrieval arm was scored: the U.S. Code 2024 edition (current through January 6, 2025) was added, because the corpus first held only the post-H.R. 1 compilation. The no-tools run, done before this change, doesn't touch the corpus and stands.

Readouts: accuracy per arm; paired differences with 95% bootstrap CIs; tool use; accuracy by the dataset's error-element topic (descriptive).

Hypotheses: H1, auto/new/dated beats no tools (CI above zero). H2, dating helps (arm 4 over 3, arm 5 over 6). H3, the rulebook helps (arm 3 over 2). H4 (descriptive), arm 5 vs no tools and vs exp84's agent (68.6%).

Post-hoc additions (after the first results, recorded in the task docstring as amendments 3 and 4):

- **Hint:** the undated attached-passage arm plus one prompt sentence saying the questions reflect pre-H.R. 1 rules.
- **Label date mode, with and without the hint:** a softer date treatment on a branch of state-policy-docs (`date-windows`). Implementation windows were curated by hand for the 22 California letters. Later guidance is kept but down-weighted: ×0.7 if it restates earlier policy and its law predates the question date, otherwise ×0.4. Superseded regulation and statute versions still swap by date. The weights were fixed before the arms ran.

### Results

E4B, 500 questions, no errors. Paired differences use a bootstrap (2,000 resamples, seed 85).

| Arm | Accuracy | vs no tools (95% CI) | Gained / lost |
|---|---|---|---|
| No tools | 73.4% | — | — |
| Auto, old corpus (exp84's) | 71.2% | −2.2 [−5.8, +1.6] | 38 / 49 |
| Auto, new corpus | 74.6% | +1.2 [−2.8, +5.2] | 52 / 46 |
| Auto, new, dated (filter, 2025-06-01) | 72.4% | −1.0 [−4.8, +2.6] | 43 / 48 |
| Agent, new | 74.6% | +1.2 [−2.4, +5.4] | 52 / 46 |
| **Agent, new, dated** | **76.0%** | **+2.6 [−1.4, +6.8]** | 62 / 49 |
| Auto, new + hint (post-hoc) | 74.4% | +1.0 [−2.8, +4.8] | 51 / 46 |
| Auto, label dates (post-hoc) | 72.0% | −1.4 [−5.2, +2.4] | 43 / 50 |
| Auto, label dates + hint (post-hoc) | 72.4% | −1.0 [−4.8, +2.6] | 45 / 50 |
| Auto, label dates, **rerun after bug fix** | 73.6% | +0.2 [−3.4, +3.8] | 44 / 43 |
| Auto, label dates + hint, **rerun after bug fix** | 71.6% | −1.8 [−5.8, +2.0] | 42 / 51 |

Other contrasts:

| Contrast | Difference (95% CI) |
|---|---|
| New vs old corpus (auto) | **+3.4 [0.0, +7.0]** (47 / 30) |
| Dated vs undated (auto) | −2.2 [−4.8, +0.4] (16 / 27) |
| Dated vs undated (agent) | +1.4 [−2.0, +4.8] (39 / 32) |
| Agent vs auto (both dated) | +3.6 [−0.6, +8.0] |
| Agent, new, dated vs exp84's agent (same 500 questions, paired) | **+7.4 [+3.6, +11.4]** (69 / 32) |
| Label vs filter dating (auto) | −0.4 [−2.6, +1.8] |
| Hint vs none (auto, undated) | −0.2 [−2.4, +1.8] |

**Tool use (agent):** about 1.6 calls per question. `lookup_rule` 0.86–0.89 per question, `get_passages` 0.69–0.78, `get_section` about 0.01, `calculate_benefit` 0.

**Passage sources (auto):**

| Share of attached passages | Undated | Dated (filter) | Label |
|---|---|---|---|
| California letters/notices | 19% | 5% | 5% |
| CFR | 36% | 45% | 45% |
| MPP | 21% | 25% | 26% |
| Handbook 310 | 21% | 24% | 25% |

| Questions with at least one California letter attached | Undated | Dated (filter) | Label |
|---|---|---|---|
| Count | 284 | 103 | 109 |

There were 32 questions that the undated arm answered correctly and the label arm missed. A California letter was among the undated arm's passages on 21 of them, and among the label arm's passages on only 5.

**Label-mode bug (found 2026-10-12 in exp87).** Label mode applied a "current" filter before weighting by date. That dropped every document version that ended before today, including the pre-H.R. 1 statute, the mid-2024 CFR versions and the FY2025 tables, so the original label arms saw current rules. After the fix, label is 73.6% against the hard filter's 72.4% (+1.2 [−1.2, +3.4]) and undated's 74.6% (−1.0 [−3.8, +1.6]). California letters were still only 5% of attached passages (on 105 questions), so the reading below is unchanged.

### Verdict

**Partly held.**

- **H3 held (barely):** the expanded rulebook beat exp84's corpus, +3.4 points with a CI from 0.0.
- **H1 did not hold:** no attached-passage arm beat no tools with a CI above zero. Every one of them sits between 71% and 75%.
- **H2 was mixed:** dating helped the agent slightly (+1.4) and hurt attached passages (−2.2). Neither CI excludes zero.
- **H4:** the dated agent is the best arm (76.0%, +2.6 over no tools, CI includes zero), and it clearly beats exp84's agent on the same questions: +7.4 [+3.6, +11.4].

So the rebuild turned a tool setup that hurt into one that helps a little. Most of that comes from better content (the rulebook) and better tools (`lookup_rule` returns the governing text directly). E4B already knows most of what this quiz tests. Retrieval's main effect is to stop it from being led astray, plus a small gain on top.

On dating:

- **The label arm wasn't a real test of soft dating.** The weights were strong enough that California letters rarely made the top 5: 5% of passages, the same as the hard filter. So label and filter came out the same (−0.4).
- **What the data does show:** the undated arm's edge over the dated arms lines up with California letters being in the prompt. On 21 of the 32 questions where undated beat label, undated had a letter and label mostly didn't.
- **My reading:** even on a pre-H.R. 1 quiz, the 2025–26 California letters carry standing California practice the model uses. Cutting them out costs more than the date-mismatched content they bring. That's a post-hoc reading from one run, not a confirmed finding.
- **The hint did nothing** (−0.2).

### Next steps

1. **A cleaner soft-dating test:** labels without down-weighting (letters kept at full weight, each tagged with its date status). Better still, attach the date status per passage and see whether the model uses it. A held-out question set is needed so the weights aren't tuned on this one.
2. **Current California rules:** the 2011 MPP is the corpus's only California regulation. CDSS regulation packages adopted since then, or the ParaRegs series (one is already in the corpus, with per-rule effective dates), would give date-correct California practice without relying on letters.
3. **The 31B model with the dated agent tools:** the sibling repo's original question.
4. **Implementation dates for the federal FNS memos,** the same treatment the California letters got.
