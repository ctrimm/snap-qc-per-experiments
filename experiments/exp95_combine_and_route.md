# Experiment 95 — combine what worked for E4B, and route the rest

**Date:** 2026-10-16 · **Code:** `exp87_heldout_task.py` (arm `agent_recipe_passages`), `exp85_mcq_rag_task.py` (`-T passages=true`), `exp94_96_analyze.py` (router), `queue_exp94_96.sh`

### Why

Two things helped E4B, on different kinds of question:
- **The exp91 recipe** fixed mechanical tool use (dates, yearly tables, the calculator): +6.6 on the exp87 set.
- **Date-filtered passages** beat every agent arm on date questions (exp90: 71% vs 47–59%).

They have never been tried together. And the design recommended after exp92 is "small model plus a router that sends open policy questions to the 31B." That has never been measured either.

### Method (pre-registered)

**1. Recipe plus passages (new runs, E4B Q4_K_M).**
- **Arm:** `agent_recipe_passages`: the recipe agent, with the top-5 date-filtered passages (`get_passages`, as_of = the question's date) attached to the question, as in the auto arms. One prompt sentence says the excerpts are there.
- **Cornell quiz:** the Cornell recipe, passages and tools all dated 2025-06-01.
- **Question sets:** exp94 (224), exp87 (243), Cornell (500).

**2. Routers (computed from per-question results, no new model calls).** A fixed keyword rule on the question stem decides which kind of question it is:

```
STRUCTURED = monthly (SNAP|CalFresh)? benefit | how much | what is/are the maximum/minimum | resource limit |
             asset limit | standard deduction | utility allowance | income (eligibility)? standard/limit |
             gross income standard | deduction is/amount
```

| Router | Structured questions | Everything else |
|---|---|---|
| Big | E4B recipe | 31B agent |
| Small | E4B recipe | E4B recipe + passages |

Cost is reported as the share of questions sent to the 31B.

The routers use these runs:
- **exp94 set:** the same-day exp94 runs.
- **exp87 set:** E4B recipe from exp91 (October 12) and 31B agent from exp87 (October 12).
- **Cornell:** E4B recipe from exp91 (October 12) and 31B agent from exp86 (October 11).

The model files and corpus are the same as in those runs. The rule was written before any exp95 result and is not tuned. Its keyword match rate on each set is reported.

**Readouts:**
- accuracy;
- paired bootstrap CIs (2,000 resamples, seed 95): recipe+passages vs recipe, big router vs E4B recipe, big router vs 31B agent, small router vs E4B recipe;
- share of questions sent to the 31B.

**Hypotheses:**
- **H1:** recipe + passages beats the recipe on the exp94 set (CI above 0), mostly on date questions.
- **H2:** recipe + passages is no worse than the recipe on Cornell (difference above −2).
- **H3:** the big router comes within 3 points of the 31B agent on every set while sending at most 70% of questions to it.

### Results

(pending)
