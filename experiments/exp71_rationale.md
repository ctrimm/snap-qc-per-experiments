# Experiment 71 — does writing out the differences first help?

**Date:** 2026-10-10 · **Code:** `experiments/exp71_rationale.py`, `exp71_run.sh` · **Results:** `eval_pilot/preds_exp71_rationale_fresh.jsonl`, `gate_exp71_*.json`

### Hypothesis

Only 12% of real fresh-set cases (148 of 1,200) show a visible agency-vs-verified difference. On those, a model trained to list the differences before answering might do better than the answer-only exp52 model. Pre-registered in the script's docstring (commit `0e2ef07`): E4B, the exp52 corpus with a deterministic "Differences:" note before each answer, step 400 fixed in advance, scored once on the exp59 fresh set against the answer-only step-400 predictions.

### Results

| Fresh set | composite | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|---|
| answer-only (exp59) | 0.334 | 0.750 | 0.516 | 0.244 | 0.053 | 0.137 |
| **differences-first** | **0.072** | 0.400 | 0.219 | 0.149 | 0.022 | 0.161 |

Paired difference: all items **−0.260 [−0.279, −0.241]**, 0/5 wins; visible-difference subset (148 items) **−0.179 [−0.231, −0.126]**.

What went wrong: the model answered T1 "error" for all 1,200 cases (accuracy 66.7% = the error share), including the 888 where it wrote "none visible", and called 86% of them underissuance. It also misread some values (it listed $1 differences although the training notes used a > $1 rule). All 1,200 answers parsed; this is the model's behaviour, not a parsing artifact. Training loss looked healthy (validation 0.083 vs 0.117 for answer-only), but the rationale tokens are easy to copy and make up most of each target, so the average loss hides how little was learned about the answers.

### Verdict

Did not hold, by a wide margin, on both readouts ("costs": the overall CI is entirely below 0). The likely causes are untested: (1) the easy rationale tokens dilute the training signal for the answer tokens, and (2) the fixed step 400 may be too few steps for the longer format. Testing either needs a new, pre-registered run (e.g., weighting the loss on answer tokens, or selecting the step on dev data). Given that real cases rarely show the error (12%), the ceiling for this idea is low, so it isn't worth chasing now.

### Next steps

None planned. Answer-only fine-tuning stays the recipe for case reading.
