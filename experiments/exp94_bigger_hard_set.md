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

All arms ran on all 224 questions on October 16 (logs in `snap-qc-data/derived/exp94_logs/`, readouts in `exp94_96_results.json`). Bootstrap: 2,000 resamples, seed 94.

| Arm | All 224 | exp90's 75 | New 149 | Apply (70) | Date (57) | California (39) | Exception (35) | Combine (23) |
|---|---|---|---|---|---|---|---|---|
| E4B no tools | 51.3% | 60.0% | 47.0% | 60.0% | 36.8% | 51.3% | 71.4% | 30.4% |
| E4B passages, date filter | 77.7% | 84.0% | 74.5% | 78.6% | 75.4% | 74.4% | 85.7% | 73.9% |
| E4B agent | 82.1% | 88.0% | 79.2% | 91.4% | 71.9% | 76.9% | 91.4% | 73.9% |
| E4B agent, strict | 80.8% | 85.3% | 78.5% | 88.6% | 77.2% | 76.9% | 77.1% | 78.3% |
| E4B agent, recipe | 79.5% | 86.7% | 75.8% | 88.6% | 66.7% | 71.8% | 91.4% | 78.3% |
| 31B no tools | 67.9% | 72.0% | 65.8% | 70.0% | 54.4% | 74.4% | 85.7% | 56.5% |
| **31B agent** | **92.0%** | 89.3% | 93.3% | 88.6% | 89.5% | 94.9% | 97.1% | 95.7% |

(exp95's E4B recipe + passages arm, on the same questions: 88.8%; see exp95.)

| Paired contrast | Difference (95% CI) |
|---|---|
| E4B passages vs no tools | +26.3 [+18.8, +33.5] |
| E4B agent vs no tools | +30.8 [+22.8, +37.9] |
| E4B strict vs agent | −1.3 [−7.1, +4.5] |
| E4B recipe vs agent | −2.7 [−8.5, +2.7] |
| 31B agent vs no tools | +24.1 [+18.3, +29.9] |
| 31B agent vs E4B recipe | +12.5 [+7.1, +18.3] |

**Reproducibility on exp90's 75 (October 12 → October 16):** notools 60.0 → 60.0, passages 84.0 → 84.0, recipe 86.7 → 86.7, strict 84.0 → 85.3, agent 82.7 → 88.0. Per-question correctness agrees on 84–92% of questions, even at temperature 0, since parallel serving isn't deterministic. On 75 questions a single rerun can move an arm by about 5 points, which is one more reason for the larger set.

### Verdict

- **H1 failed:** on 224 questions the recipe doesn't beat the plain agent (−2.7 [−8.5, +2.7]). It is worst on date questions (66.7%, against 71.9% for the plain agent). The logs haven't been examined for why. exp91's +4.0 on exp90 didn't replicate.
- **H2 failed narrowly:** on date questions, date-filtered passages (75.4%) beat the plain agent (71.9%) and the recipe (66.7%), but not the strict agent (77.2%).
- **H3 held:** the 31B agent beats the E4B recipe by 12.5 points [+7.1, +18.3].
- **H4 held:** the new questions are no easier. The 31B agent scores 93.3% on them against 89.3% on exp90's, within the 5-point bound. Every E4B arm scores 6–13 points lower on the new ones. The new set is harder for the small model than for the 31B.

With 224 questions the paired CIs are about ±5–6 points, against about ±9 with 75. Use `exp94_hard.jsonl` for later hard-set comparisons. A second reviewer is still advised.
