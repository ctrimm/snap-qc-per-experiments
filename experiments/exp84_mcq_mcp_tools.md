# Experiment 84 — do the state-policy-docs MCP tools help small models on the CalFresh quiz?

**Date:** 2026-10-10 · **Code:** `experiments/exp84_mcq_tools_task.py` (pre-registered in its docstring), `exp84_run.sh` · **Logs:** `../snap-qc-data/derived/exp84_logs/`

### Hypothesis

exp70 found the QC-trained E4B keeps its SNAP policy knowledge (about 73–74% on the 500-question CalFresh benchmark), about 10 points below Gemma 4 31B. The sibling `state-policy-docs` repo exposes a policy corpus through MCP tools (search, read a document, list documents). If a small model can look up the rule instead of recalling it, its accuracy should rise, possibly enough to close part of the gap to the 31B model.

### Method

The 500 Better Government Lab CalFresh questions in exp70's format (A–E). The sibling repo's harness can't load this file (it expects four option columns, A–D), so exp84 reuses its MCP tool setup in its own Inspect task. Gemma 4 E2B and E4B served by LM Studio (both Q4_K_M, 128K context, 4 parallel slots), temperature 0. Without tools: one answer. With tools: an Inspect ReAct agent with the three MCP tools and submit(), one attempt, at most 30 messages. Errors count wrong. Readout: accuracy and the paired difference with − without tools per model (bootstrap 95% CI), plus how often the tools were used.

Setup notes: the first smoke runs failed on request format (fixed by using chat completions) and on context length (a single document read returns up to 60,000 characters; fixed by loading the models with a 128K context), before any scored run.

### Results

| 500 CalFresh questions | Without tools | With state-policy-docs tools | Paired difference (95% CI) | Questions gained / lost |
|---|---|---|---|---|
| Gemma 4 E4B | 71.6% | 68.6% | **−3.0 points [−6.8, +0.6]** | 41 / 56 |
| Gemma 4 E2B | 70.6% | 68.2% | **−2.4 points [−6.0, +1.4]** | 41 / 53 |

No errors or missing answers in any run. With tools, both models called a tool on every question: E4B 3.4 calls per question (1,493 searches, 113 document lists, 71 document reads); E2B 2.7 (1,285 searches, 52 lists, 33 reads). E4B without tools (71.6%) is close to exp70's bf16 72.6%, as expected for a 4-bit build.

### Verdict

Did not hold. The policy tools don't raise accuracy for either small model; the point estimates are slightly lower and the intervals include zero, so the honest reading is "no gain, possibly a small loss". The models searched on every question but opened a document on only 7% (E2B) to 14% (E4B) of them, answering from search snippets instead of reading the rule, and snippet text sometimes pulled them off a right answer they'd have given anyway (41 questions gained, 53–56 lost).

### Next steps

1. Retrieval would need to put the rule in front of the model rather than leave it to choose: e.g. automatically attach the top passages to every question (no agent), or force a document read before answering.
2. The same test on Gemma 4 31B, the sibling repo's original question (whether retrieval closes the gap to frontier models), remains open; small models aren't the right test bed for agentic retrieval.

