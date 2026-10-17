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

**1. Recipe plus passages** (E4B; paired against the recipe; seed 95):

| Question set | Recipe | Recipe + passages | Difference (95% CI) | 31B agent |
|---|---|---|---|---|
| exp94 hard (224) | 79.5% | **88.8%** | **+9.4 [+3.6, +15.2]** | 92.0% |
| exp87 held-out (243) | 95.5% | 96.7% | +1.2 [−2.1, +4.5] | 99.6% |
| Cornell (500, dated) | 74.6% | 76.4% | +1.8 [−1.6, +5.2] | 88.8% |

By kind on the exp94 set, recipe → recipe + passages:

| Kind | Recipe | Recipe + passages |
|---|---|---|
| Date (57) | 66.7% | **86.0%** |
| Combine (23) | 78.3% | 91.3% |
| California (39) | 71.8% | 79.5% |
| Apply (70) | 88.6% | 94.3% |
| Exception (35) | 91.4% | 91.4% |

Against the 31B agent:
- **exp94 set:** −3.1 [−8.5, +2.2], not significant.
- **Cornell:** −12.4 [−16.2, −9.0].

Tool use dropped to 1.2 calls a question on exp94 (recipe: 1.95).

**2. Routers** (keyword rule as pre-registered; the exp87 and Cornell runs are from earlier days, as stated in the method):

| Question set | Keyword match (structured) | Big router | Sent to 31B | vs 31B agent | Small router | vs E4B recipe |
|---|---|---|---|---|---|---|
| exp94 hard | 12.9% | 89.3% | 87.1% | −2.7 [−4.9, −0.9] | 87.1% | +7.6 [+2.2, +12.9] |
| exp87 held-out | 83.5% | 96.7% | 16.5% | −2.9 [−5.3, −0.8] | 96.3% | +0.8 [−0.8, +2.5] |
| Cornell | 12.0% | 86.6% | 88.0% | −2.2 [−3.8, −0.8] | 76.0% | +1.4 [−1.8, +4.6] |

**Disclosure:** the router numbers for exp87 and Cornell first printed while the analysis script was being tested, after the rule had been committed (d8cbedc). The rule was not changed.

### Verdict

- **H1 held:** recipe + passages beats the recipe on the hard set by 9.4 points, mostly on date questions (+19.3). It is the best small-model arm on every set.
- **H2 held:** on Cornell it is +1.8, comfortably above the −2 bound.
- **H3 failed:** the big router comes within 2–3 points of the 31B everywhere, but only by sending 87–88% of questions to it on the hard set and Cornell. Where it sends few questions (exp87, 16.5%), it is 2.9 points short. A keyword rule doesn't find the hard questions. Most hard-set and Cornell questions don't look structured, and the structured ones on exp87 are already easy for E4B. The small router does no better than recipe + passages applied to everything.

**What to ship:**
- **Small model:** E4B with recipe + date-filtered passages, as the default for everything. Within 3 points of the 31B on dated and structured questions, at much lower cost.
- **Open policy questions** (the Cornell style): the 31B. The small model is still 12 points behind there.
- **Routing:** if routing is wanted, it needs a better signal than keywords, such as the small model's confidence or agreement between two small-model runs. That is a possible exp98.
