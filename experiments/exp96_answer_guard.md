# Experiment 96 — force the exp92 model to answer instead of looping

**Date:** 2026-10-16 · **Code:** `exp96_guard.py`, `exp85_mcq_rag_task.py` and `exp87_heldout_task.py` (`-T guard=N`), `exp94_96_analyze.py`, `queue_exp94_96.sh`

### Why

exp92's fine-tuned E4B lost 10.8 points on Cornell with tools, and the whole loss was unanswered questions: 67 of 500 hit the 30-message limit while still searching. On the questions it did answer, it matched the base model (76.2% vs 76.8%). If an inference-time guard recovers those answers, the fix for exp92 is cheap and needs no retraining.

### Method (pre-registered)

**The guard** (`exp96_guard.py`):
- After N tool calls (submit not counted), each turn tells the model its tool budget is used up and to call `submit()` with one letter.
- The loop ends at N + 2 calls, or as soon as the model replies without a tool call once the budget is spent, or after its third reply without a tool call.
- If `submit()` was never called, a final step asks for one letter with no tools. Those answers are scored like any other and flagged `forced`.
- The message limit is 40 for guarded runs, so the answer step always runs.

The guard is tested on 2–6 question smoke runs only. Two loop bugs were found that way and fixed before any scored run.

**Models:** the exp92 bf16 base (`gemma-4-e4b-base`) and fine-tuned (`gemma-4-e4b-exp92-tooluse-full`), same files as exp92. Each is probed before its runs (`finish_reason` must be `stop`).

**Arms:**

| Model | Cornell (agent, dated) | exp94 set (224, agent) |
|---|---|---|
| Fine-tuned | guard 4, 6, 8 (no guard: exp92 run) | guard 6, no guard |
| Base | guard 6 (no guard: exp92 run) | guard 6, no guard |

**Readouts:**
- accuracy;
- unanswered (message limit) and forced counts;
- accuracy on forced answers;
- tool calls per question;
- paired bootstrap CIs (2,000 resamples, seed 96): each guard vs the same model unguarded, fine-tuned with guard vs base unguarded, base with guard vs base unguarded.

**Hypotheses:**
- **H1:** with guard 6 on Cornell, the fine-tuned model recovers to within 2 points of the unguarded base (76.8%).
- **H2:** the guard does not hurt the base model (difference above −2 on Cornell).
- **H3 (descriptive):** how accuracy varies with N.

**How to read it:**
- If H1 holds, exp92's fine-tune plus a guard is a working small model that reads the rule. A follow-up then asks whether it beats the exp91 recipe.
- If not, the distillation thread is closed.

### Results

(pending)
