# Experiment 90 — harder rule questions

**Date:** 2026-10-12 · **Code:** `experiments/exp90_build_hard.py`, `exp90_hard.json` (questions), `exp87_heldout_task.py` (`-T data=exp90_hard.jsonl`), `exp90_91_analyze.py`, `queue_exp90_91.sh` · **Data:** `experiments/exp90_hard.jsonl`

### Why

The 31B agent nearly maxed out exp87 (99.6%), and exp87's 43 rule questions mostly asked for one fact. exp90 asks for rules applied to a case.

### The set (75 questions)

| Kind | Count | Example |
|---|---|---|
| Apply | 40 | Expedited service from income, resources and rent; the excess shelter deduction with the FY2025 cap; LIHEAP and utility-allowance cases before and after H.R. 1; cost-share tiers at boundary error rates; student exemptions; IPV and work-requirement penalties; claim look-back periods; income treatment (in-kind, reimbursements, roomers, rental income) |
| Date | 17 | ABAWD ages before and after H.R. 1; California's implementation lag (applications received before vs after April 1 and June 1, 2026; recertifications due in May vs June; new members reported before vs after June 1) |
| Combine | 10 | A 59-year-old who turns 60 in the application month; minimum benefit in an initial month; which household size sets the reporting threshold; QC threshold adjustment |
| Exception | 5 | Which exceptions survive H.R. 1 |
| California | 3 | |

Every question cites its sources, and the builder checks each evidence phrase against the source text in force on the question's date: all 75 passed. The questions were written from the corpus by the same author as the retrieval tools, so a second reviewer remains a good idea.

### Method (pre-registered)

Same task code as exp87.
- **E4B arms:** no tools, passages filtered by date, agent, and exp91's strict and recipe agent arms.
- **31B arms:** no tools and agent.

Readouts: accuracy overall and by kind; paired bootstrap CIs (seed 90); agent tool use, including how often `as_of` was passed.

Hypotheses:
- **H1:** the 31B agent stays below 95% (the set is harder than exp87's rule part).
- **H2:** every retrieval arm beats no tools for both models.

### Results

75 questions per arm, no errors. Bootstrap uses 2,000 resamples, seed 90.

| Arm | All | Apply (40) | Date (17) | Combine (10) | Exception (5) | California (3) |
|---|---|---|---|---|---|---|
| E4B no tools | 60.0% | 67.5% | 35.3% | 60.0% | 80% | 2 of 3 |
| E4B passages, date filter | 84.0% | 87.5% | **70.6%** | 90.0% | 80% | 3 of 3 |
| E4B agent | 82.7% | 97.5% | 47.1% | 90.0% | 80% | 2 of 3 |
| E4B agent, strict (exp91) | 84.0% | 95.0% | 58.8% | 80.0% | 100% | 2 of 3 |
| E4B agent, recipe (exp91) | 86.7% | 95.0% | 58.8% | 100% | 100% | 2 of 3 |
| 31B no tools | 72.0% | 80.0% | 58.8% | 70.0% | 100% | 0 of 3 |
| **31B agent** | **92.0%** | 95.0% | 82.4% | 100% | 100% | 2 of 3 |

| Paired contrast | Difference (95% CI) |
|---|---|
| E4B passages vs no tools | +24.0 [+13.3, +36.0] |
| E4B agent vs no tools | +22.7 [+9.3, +36.0] |
| 31B agent vs no tools | +20.0 [+9.3, +30.7] |
| E4B recipe vs 31B agent | −5.3 [−13.3, +2.7] |

### Verdict

**Held.**

- **H1:** the set is harder. The 31B agent scored 92.0% (exp87's rule part: 97.7%).
- **H2:** every retrieval arm beats no tools for both models, by 20–24 points.

The hardest questions are about **dates**, especially California's implementation lag: which rules apply to an application received before a cutoff, or a recertification due in a given month.
- No tools: E4B 35%, 31B 59%.
- With tools: the 31B agent reaches 82%. E4B's best is the date-filtered passages (71%), better than any of its agent arms (47–59%), because the passages are dated for it while the agent has to work the date out itself.
- Applying a rule to a household's facts is nearly solved with tools (95–98%).

Caveats: 75 questions (only 3 California items and 5 exceptions), written by the tools' author. A second reviewer and more questions would tighten this.
