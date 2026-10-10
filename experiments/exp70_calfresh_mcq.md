# Experiment 70 — did QC fine-tuning cost the model SNAP policy knowledge?

**Date:** 2026-10-10 · **Code:** `experiments/exp70_calfresh_mcq.py`, `exp70_run.sh` · **Results:** `exp70_*.jsonl`

### Hypothesis

The north star's LM gate has two halves: the QC-variance eval (passed on fresh cases, exp59) and a SNAP policy benchmark, which had never been run. Fine-tuning a small model on narrow synthetic QC tasks can erode general knowledge. If the exp59-confirmed model (E4B + SFT step 400) scores no more than 3 points below its untrained base on CalFresh policy questions, the fine-tune is safe to build on. Pre-registered in the script's docstring (commit before scoring).

### Method

Better Government Lab's 500 CalFresh scenario multiple-choice questions (the Nava Labs benchmark), no tools, one-letter answers: the eval's no-tools instruction, the client attributes and the question; greedy, thinking off, max 8 tokens. Models: E4B untrained, E4B + exp52 SFT step 400, and Gemma 4 31B untrained as a setup check against the published 85.8%. Paired bootstrap (2,000 resamples) for tuned − untrained.

### Results

| Model | Accuracy | Difficulty 1 (n=215) | 2 (n=207) | 3 (n=75) |
|---|---|---|---|---|
| E4B untrained | 72.6% | 78% | 73% | 55% |
| **E4B + QC fine-tune (step 400)** | **74.4%** | 80% | 76% | 52% |
| 31B untrained (setup check) | 84.8% | 90% | 86% | 68% |

Paired difference, fine-tuned − untrained: **+1.8 points [−0.4, +3.8]**. No unparseable answers. The 31B check lands within 1 point of the published 85.8%, so the runner reproduces the benchmark.

### Verdict

Held: no meaningful harm (the interval's lower bound, −0.4, is well above −3). The QC fine-tune leaves policy knowledge intact and may nudge it up slightly, though the gain isn't significant. Both halves of the north star's LM gate are now met for the E4B model: it passes the QC-variance gate on fresh cases and keeps its policy knowledge. The 31B model knows about 10 points more policy than E4B, which matters if the model is ever asked policy questions rather than reading cases.

### Next steps

1. If flag cards or reviewer help ever include policy citations, ground them in the `state-policy-docs` corpus rather than the model's memory (the sibling repo's eval tests exactly that retrieval setup).
2. Optional: the same check for the exp62 explainer E2B.
