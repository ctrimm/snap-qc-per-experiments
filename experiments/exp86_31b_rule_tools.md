# Experiment 86 — do the rule tools help Gemma 4 31B on the CalFresh quiz?

**Date:** 2026-10-11 · **Code:** `experiments/exp86_run.sh` (task: `exp85_mcq_rag_task.py`, unchanged) · **Logs:** `../snap-qc-data/derived/exp86_logs/` (not in git: they embed quiz text)

### Hypothesis

state-policy-docs was built to test whether retrieval closes the gap between open models and frontier models on SNAP policy questions. exp85 found the best setup for a small model was an agent with the new rule tools, looking up rules dated to 2025-06-01 (pre-H.R. 1): E4B 76.0% vs 73.4% with no tools. Gemma 4 31B scored 84.8% with no tools in exp70. If the tools help a model that's better at using them, the 31B should gain.

### Method (pre-registered)

The same 500 questions and task code as exp85. Model: `google/gemma-4-31b` in LM Studio (128K context, 4 slots), temperature 0. Two arms:

1. No tools.
2. Agent with get_passages, lookup_rule, get_section and calculate_benefit, on the expanded corpus, dated 2025-06-01 by the server default. One attempt, at most 30 messages.

Nothing about this configuration was changed after exp85.

Readouts: accuracy, and the paired difference (agent − no tools) with a 95% bootstrap CI (2,000 resamples, seed 86); tool use; gained/lost questions.

Hypothesis: the agent beats no tools (CI above zero). Descriptive: the size of the gain compared with E4B's +2.6.

### Results

Both runs completed with no errors. The agent run took about 9 hours (13:29–22:40) at 4 slots.

| Gemma 4 31B, 500 questions | Accuracy |
|---|---|
| No tools | 84.0% |
| **Agent with the rule tools (expanded corpus, dated 2025-06-01)** | **88.8%** |
| Paired difference (95% CI) | **+4.8 points [+2.0, +7.6]** (39 questions gained, 15 lost) |

| Context (paired, same questions) | Difference (95% CI) |
|---|---|
| 31B agent vs E4B agent (exp85, same setup) | +12.8 [+9.0, +16.4] |
| E4B agent vs E4B no tools (exp85) | +2.6 [−1.4, +6.8] |

**Tool use** (calls per question): get_passages 0.93, lookup_rule 0.87, get_section 0.59, calculate_benefit 0.

The 31B reads more than E4B did: about 2.4 calls per question against 1.6, and it often follows a citation with get_section (0.59 per question vs E4B's 0.01). The no-tools score (84.0%) matches exp70 (84.8%) and the published 85.8% (Nava Labs, no tools) within run-to-run variation.

### Verdict

**Held.** The rule tools raise Gemma 4 31B from 84.0% to 88.8% on the 500 CalFresh questions, a CI clearly above zero.

The same setup gave E4B +2.6 with a CI including zero. So the tools pay off more for a model that can use them, and the 31B uses them differently: it opens the cited sections instead of answering from summaries.

This answers the sibling repo's original question for an open model: dated, citation-level retrieval over a real rulebook closes a meaningful part of the gap. A frontier-model comparison on the same setup is the open next step.

Caveats:
- **One run, one setup:** no tuning was done on this quiz, by design.
- **Age of the quiz:** the quiz predates H.R. 1, so tools were dated 2025-06-01.
- **Per-question scores** are kept locally (`../snap-qc-data/derived/exp86_per_question_scores.json`) and not committed, per the dataset licence.

### Next steps

1. Frontier comparison (Claude) with and without the same tools, if approved, since it means paid API calls.
2. exp87 tests the same tools on our own dated question set, where retrieval can also be scored directly (queued).
