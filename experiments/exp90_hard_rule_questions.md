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

Pending (queued after exp89).
