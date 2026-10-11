# Experiment 85 — a fuller rulebook, and the rule put in front of the model, on the CalFresh quiz

**Date:** 2026-10-11 · **Code:** `experiments/exp85_mcq_rag_task.py` (pre-registered in its docstring), `exp85_run.sh` · **Logs:** `../snap-qc-data/derived/exp85_logs/`

### Hypothesis

exp84 found the state-policy-docs tools didn't help Gemma 4 E4B (71.6% → 68.6%). Two things could explain it: the corpus held mostly recent California letters about H.R. 1 rather than the rules most questions test (deductions, students, household composition), and the model searched on every question but read a document on only 14% of them, answering from 320-character snippets. Since then the corpus has gained the federal and California rulebooks (CFR for 15 programs, the Food and Nutrition Act, FNS Handbook 310, the FY2024–27 FNS tables, California MPP Division 63; about 3,300 documents, up from 507) and four new tools that return rule text with citations (get_passages, lookup_rule, get_section, calculate_benefit). If either was the problem, E4B should now gain.

### Method

The same 500 CalFresh questions and E4B build as exp84 (LM Studio, Q4_K_M, 128K context, temperature 0). A same-day no-tools baseline, then a 2×2:

- **Corpus:** old (the 507-document corpus exp84 used, state-policy-docs at `e20d2e0`) vs new (expanded). The same server code serves both, so only the content changes. With the old corpus, citation lookups and the calculator find nothing; that's part of what the old corpus lacks.
- **Mode:** auto (no agent: the top 5 passages for the question, California plus federal, at most 2 per document, about 300–600 words each, are put in the prompt) vs agent (a ReAct agent with the four new tools, one attempt, at most 30 messages).

Readouts: accuracy per condition; paired differences with 95% bootstrap CIs (each condition − no tools; new − old within each mode; agent − auto within each corpus); tool use; accuracy by the dataset's error-element topic (descriptive).

Pre-registered hypotheses: H1, auto-attach on the new corpus beats no tools (CI above zero). H2, the new corpus beats the old in both modes. H3 (descriptive), the agent with the new tools vs exp84's agent (68.6%) and vs no tools.

### Results

Pending.
