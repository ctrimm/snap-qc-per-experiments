# Experiment 84 — do the state-policy-docs MCP tools help small models on the CalFresh quiz?

**Date:** 2026-10-10 · **Code:** `experiments/exp84_mcq_tools_task.py` (pre-registered in its docstring), `exp84_run.sh` · **Logs:** `../snap-qc-data/derived/exp84_logs/`

### Hypothesis

exp70 found the QC-trained E4B keeps its SNAP policy knowledge (about 73–74% on the 500-question CalFresh benchmark), about 10 points below Gemma 4 31B. The sibling `state-policy-docs` repo exposes a policy corpus through MCP tools (search, read a document, list documents). If a small model can look up the rule instead of recalling it, its accuracy should rise, possibly enough to close part of the gap to the 31B model.

### Method

The 500 Better Government Lab CalFresh questions in exp70's format (A–E). The sibling repo's harness can't load this file (it expects four option columns, A–D), so exp84 reuses its MCP tool setup in its own Inspect task. Gemma 4 E2B and E4B served by LM Studio (both Q4_K_M, 128K context, 4 parallel slots), temperature 0. Without tools: one answer. With tools: an Inspect ReAct agent with the three MCP tools and submit(), one attempt, at most 30 messages. Errors count wrong. Readout: accuracy and the paired difference with − without tools per model (bootstrap 95% CI), plus how often the tools were used.

Setup notes: the first smoke runs failed on request format (fixed by using chat completions) and on context length (a single document read returns up to 60,000 characters; fixed by loading the models with a 128K context), before any scored run.

### Results

_Pending (runs overnight)._
