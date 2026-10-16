# Experiment 94 — a bigger hard rule-question set (75 → 224)

**Date:** 2026-10-16 · **Code:** `exp94_more.json` (149 new questions), `exp94_build_more.py`, `exp87_heldout_task.py` (`-T data=exp94_hard.jsonl`), `exp94_96_analyze.py`, `queue_exp94_96.sh` · **Data:** `experiments/exp94_hard.jsonl`

### Why

exp90 has 75 questions, so its 95% intervals are about ±9 points. exp91's recipe effect there (+4.0) and exp92's loss (−8.0) both came out "not significant." Every later choice that uses the hard set needs a larger one.

### The set

The 75 exp90 questions are carried over unchanged (same ids and option order). The 149 new ones are hand-written from the state-policy-docs corpus in the same format, weighted toward the kinds exp90 found hardest:

| Kind | exp90 | New | Total | Examples of the new ones |
|---|---|---|---|---|
| Date | 17 | 40 | 57 | H.R. 1 implementation in California (noncitizens April 1, 2026; ABAWD June 1, 2026; LPIE June 1, 2026), FNS memos (QC exclusion periods, waiver terminations), CFR and Act versions (internet costs, LUA telephone, administrative cost share), FY2026 vs FFY2027 figures, county waivers and the Early Denial Waiver by date |
| California | 3 | 36 | 39 | ACL 25-92, ACIN I-29-26, ACIN I-14-26, ACL 25-93, 26-04 (standard medical deduction), 25-68 (SUAS, weatherization), 26-16 (AB 42), 26-25, 26-43, MPP 63-804 (hearings) |
| Exception | 5 | 30 | 35 | Five-year waiting period exemptions, dependent-child exemption under 14, resource exclusions (retirement accounts, EITC, vehicles, property for sale, SSI members), dependent care by a relative, student exemptions |
| Apply | 40 | 30 | 70 | Cost-share look-back years, SAVE pending, expedited delivery, filing date, FFY2027 California tables |
| Combine | 10 | 13 | 23 | Full benefit computations (FY2026 federal and FFY2027 California), elderly households (net test only, uncapped shelter, medical), IPV vs ABAWD-ineligible member treatment |

Checks, enforced by the builder:
- **Evidence:** every evidence phrase appears in a cited source's text as of the question's date.
- **Options:** five distinct options per question.
- **No near-duplicates:** a new stem is refused if more than half of its 12-word sequences appear in one exp90 stem, or in another new stem on the same date. Deliberate date pairs (the same question on two dates) are allowed.
- **Arithmetic:** each benefit computation was cross-checked with `calculate_benefit`, and amounts were set so that every rounding procedure allowed by 7 CFR 273.10(e)(1)(ii) gives the same answer. Two questions were adjusted by $2 of shelter cost for this.
- **Consistency:** one draft question was replaced because two California sources conflict on it (ACL 25-93 vs ACIN I-14-26, on whether the dependent child must live in the household).

The questions were written by the same author as the tools and exp90. A second reviewer is still advised.

New answer key: A 27, B 27, C 40, D 32, E 23.

### Method (pre-registered)

Same task code as exp90/91 (`exp87_heldout_task.py`), run on all 224 questions on the same day.

| Model | Arms |
|---|---|
| E4B (Q4_K_M) | notools, auto_filter (date-filtered passages), agent, agent_strict, agent_recipe |
| 31B | notools, agent |

Readouts:
- accuracy overall, by kind, and by subset (the exp90 75 vs the new 149);
- paired bootstrap CIs (2,000 resamples, seed 94);
- reproducibility on the exp90 75: agreement with the October 12 runs of the same arms.

Hypotheses:
- **H1:** on all 224, the exp91 recipe beats the plain agent for E4B (CI above 0).
- **H2:** E4B with date-filtered passages beats every E4B agent arm on date questions.
- **H3:** the 31B agent beats the E4B recipe overall (CI above 0).
- **H4:** the new 149 are no easier than the exp90 75: 31B agent accuracy on the new subset is within 5 points of its accuracy on the old subset, or lower.

### Results

(pending)
