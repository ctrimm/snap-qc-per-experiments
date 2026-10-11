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

Pending.
