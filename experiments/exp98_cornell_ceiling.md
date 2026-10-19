# Experiment 98 — how far can Gemma 4 go on the Cornell quiz?

**Date:** 2026-10-17 · **Code:** `exp85_mcq_rag_task.py` (amendment 6: `as_of`, `verify`), `queue_exp98.sh` · **Logs:** `snap-qc-data/derived/exp98_logs/`

### Why

The best Cornell result so far is 88.8%, from the 31B agent with rule tools dated 2025-06-01 (exp86). A Nava PBC field note (["What AI gets wrong about SNAP"](https://fieldnotes.navapbc.com/p/what-ai-gets-wrong-about-snap-and)) reports, on the same 500 questions:
- **GPT-6 Astra, baseline:** 92.2%.
- **With a revised system prompt:** 98.3% (three runs). The prompt also directs web search for immigration and SSN questions.

No model was fine-tuned. The author wrote the revised prompt from the errors on these 500 questions and flags the risk of overfitting. So the comparison that holds up is 92.2%.

### Audit of the 22 questions every run got wrong (done before this experiment)

Of the 500, 22 were wrong in all seven Cornell runs. Those runs are:
- 31B: agent, no tools;
- E4B: agent, recipe, recipe + passages;
- the exp96 base and fine-tuned models.

They were read against the corpus, privately. No question text or answer key is recorded here, per the quiz's license.

| What went wrong | Questions |
|---|---|
| Noncitizen questions keyed to post-H.R. 1 rules (refugees and asylees not eligible); every run answered under pre-H.R. 1 rules | 6 |
| A California rule in the corpus that no run applied: the 40% standard self-employment deduction (CDSS ParaRegs), and a client's statement sufficing for student status (ACL 21-58, restated in ACL 26-25) | 4 |
| Key defensible, the models misread or misreasoned | 7 |
| Key disputable: the rules don't clearly pick the keyed option over another | 5 |

**The quiz is not pre-H.R. 1, at least not throughout.** exp85 assumed it was and dated retrieval to 2025-06-01. Evidence against that:
- **The utility allowance:** one question uses a $663 standard utility allowance. That is California's FFY2026 SUA (October 2025–September 2026; ACIN I-40-26: "increased from $663 to $686").
- **The noncitizen keys:** six follow the rules California applied from April 1, 2026.
- **The noncitizen scores:** on the 34 citizenship questions, E4B's agent scores 67.6% undated and 52.9% dated 2025-06-01; the dated 31B agent scores 73.5%. The pre-H.R. 1 date has been costing points there.

Overall, dating still helped slightly in exp85 (76.0% vs 74.6%), so the quiz may mix periods.

**Ceiling:** leaving out the 5 disputable questions, the most a model can get is about 99%.

### Method (pre-registered; arms run once each)

All runs: dated agent arms use the server default and dated passages; temperature 0.

| # | Model | Arm | Date | Thinking | What it tests |
|---|---|---|---|---|---|
| 1 | E4B (Q4) | recipe + passages | 2026-06-01 | off | the date fix for the small model (vs exp95: 76.4% at 2025-06-01) |
| 2 | 31B | no tools | — | high | reasoning alone (vs 84.0%, thinking off) |
| 3 | 31B | agent | 2026-06-01 | off | the date fix (vs exp86: 88.8% at 2025-06-01) |
| 4 | 31B | agent + passages, then verify | 2026-06-01 | high | everything combined. The pre-verify answer is kept, so the arm is scored with and without the check step. |

**Post-hoc note:** 2026-06-01 was chosen from the audit, i.e., from looking at answer keys in this test set. It is inside the FFY2026 window the $663 SUA implies, and after California's April 2026 noncitizen change. Arms 1, 3 and 4 are therefore informed by the test set, and are labeled post-hoc. Arm 2 isn't.

The verify step is generic ("check your answer once against the rule text and tool results"). It names no topic.

Bootstrap: 2,000 resamples, seed 98, paired against the earlier runs named above.

**Hypotheses:**
- **H1:** the 2026-06-01 date raises the 31B agent above 88.8%, gaining mostly on citizenship questions.
- **H2:** thinking raises 31B no-tools above 84.0%.
- **H3:** arm 4 scores at least 92.2%, GPT-6 Astra's untuned baseline.
- **H4 (descriptive):** what the verify step adds within arm 4.

**Next, if needed:** a Cornell-style practice set of our own, written from the corpus and checked against Cornell for overlap, would let prompt guidance be developed without touching the test set. Then one more pre-registered Cornell run.

### Results

<!-- AUTO-RESULTS:START -->
Scored 2026-10-19 10:14 by `exp99_analyze.py` (aggregate only). Reference: GPT-6 Astra, untuned baseline, 92.2% (Nava PBC).

| Arm | Accuracy | Citizenship (34) | Difficulty 3 (75) |
|---|---|---|---|
| exp86: 31B agent, dated 2025-06-01 | 88.8% | 73.5% | 73.3% |
| exp86: 31B no tools | 84.0% | 67.6% | 65.3% |
| exp98-1: E4B recipe + passages, 2026-06-01 | 77.0% | 70.6% | 72.0% |
| exp98-2: 31B no tools, thinking high | 85.8% | 67.6% | 66.7% |
| exp98-3: 31B agent, 2026-06-01 | 89.6% | 70.6% | 72.0% |
| exp98-4: 31B agent + passages + thinking, 2026-06-01, after check | 89.2% | 85.3% | 81.3% |
| exp98-4: before check | 86.4% | 76.5% | 77.3% |

| Paired contrast (95% CI, 2,000 resamples) | Difference |
|---|---|
| exp98-4: 31B agent + passages + thinking, 2026-06-01, after check − exp98-4: before check | +2.8 [+1.4, +4.2] |
| exp98-4: 31B agent + passages + thinking, 2026-06-01, after check − exp98-3: 31B agent, 2026-06-01 | -0.4 [-3.2, +2.4] |
| exp98-3: 31B agent, 2026-06-01 − exp86: 31B agent, dated 2025-06-01 | +0.8 [-1.4, +2.8] |
| exp98-2: 31B no tools, thinking high − exp86: 31B no tools | +1.8 [-0.8, +4.4] |
| exp98-1: E4B recipe + passages, 2026-06-01 − exp95 (2025-06-01) | +0.6 [-2.8, +4.0] |

- **exp98-4:** the check changed 14 wrong answers to right and 0 right answers to wrong.

Best arm: **exp98-3: 31B agent, 2026-06-01, 89.6%**.
<!-- AUTO-RESULTS:END -->
