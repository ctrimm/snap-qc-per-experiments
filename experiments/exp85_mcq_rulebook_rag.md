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

The same server code serves both corpora. The new corpus has no pre-H.R. 1 statute text (the Act compilation is as amended through P.L. 119-21), so dated arms rely on the CFR (mid-2024 versions where the text has changed since), the FY2025 FNS tables, Handbook 310 and MPP Division 63.

Readouts: accuracy per arm; paired differences with 95% bootstrap CIs; tool use; accuracy by the dataset's error-element topic (descriptive).

Hypotheses: H1, auto/new/dated beats no tools (CI above zero). H2, dating helps (arm 4 over 3, arm 5 over 6). H3, the rulebook helps (arm 3 over 2). H4 (descriptive), arm 5 vs no tools and vs exp84's agent (68.6%).

### Results

Pending.
