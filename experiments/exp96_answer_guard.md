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

Both models passed the probe (`finish_reason=stop`). The unguarded rows are exp92's runs of the same model files. Bootstrap: 2,000 resamples, seed 96.

**Cornell (500, agent, dated):**

| E4B (bf16) | Accuracy | Unanswered | Answered by the forced step | Tool calls / q | get_section / q |
|---|---|---|---|---|---|
| Base, no guard (exp92) | 76.8% | 0 | — | 1.09 | 0.00 |
| Base, guard 6 | 77.0% | 0 | 148 | 1.14 | 0.00 |
| Fine-tuned, no guard (exp92) | 66.0% | 67 | — | 4.49 | 1.17 |
| **Fine-tuned, guard 4** | **76.8%** | 0 | 500 | 3.34 | 0.69 |
| Fine-tuned, guard 6 | 74.4% | 0 | 500 | 4.13 | 0.96 |
| Fine-tuned, guard 8 | 75.2% | 0 | 500 | 4.68 | 1.24 |

| Paired contrast | Difference (95% CI) |
|---|---|
| Fine-tuned guard 4 vs fine-tuned unguarded | +10.8 [+7.6, +14.4] |
| Fine-tuned guard 6 vs fine-tuned unguarded | +8.4 [+5.0, +11.6] |
| Fine-tuned guard 8 vs fine-tuned unguarded | +9.2 [+6.0, +12.6] |
| Fine-tuned guard 4 vs base unguarded | 0.0 [−3.4, +3.4] |
| Fine-tuned guard 6 vs base unguarded | −2.4 [−6.0, +1.2] |
| Fine-tuned guard 8 vs base unguarded | −1.6 [−5.2, +1.8] |
| Base guard 6 vs base unguarded | +0.2 [−2.4, +2.8] |

**exp94 hard set (224, agent):**

| E4B (bf16) | No guard | Guard 6 | Difference |
|---|---|---|---|
| Base | 78.1% (4 unanswered) | 79.0% | +0.9 [−4.0, +5.8] |
| Fine-tuned | 75.0% (16 unanswered) | 77.2% | +2.2 [−2.2, +6.2] |

Fine-tuned guard 6 vs base unguarded: −0.9 [−7.6, +5.8].

**What the logs show:** the fine-tuned model never calls `submit()`. In all 1,724 guarded fine-tuned samples (three Cornell runs and one hard-set run) the forced step gave the answer; none has a submit call. It writes its answer as text ("B"), and react then urges it to call submit, again and again. That is exp92's whole failure mode.

The cause is in exp92's training data:
- `exp92_make_sft.py` built the training turns from the 31B's Inspect messages, and react removes the `submit()` call from those messages after it runs (`keep_in_messages` defaults to false).
- So all 464 of the 1,028 training examples that end a trajectory teach a final answer in text. None teach a submit call, even though the submit tool is in every example's schema.

The model learned exactly what it was shown. The base model calls submit on its own most of the time (forced on 148 of 500 Cornell questions).

### Verdict

- **H1 failed narrowly at the pre-registered N = 6:** −2.4 [−6.0, +1.2], against a bound of −2.
- **At N = 4:** the fine-tuned model matches the base exactly (0.0 [−3.4, +3.4]), recovering the full 10.8 points.
- **H2 held:** the guard doesn't hurt the base model (+0.2 on Cornell, +0.9 on the hard set).
- **H3:** accuracy doesn't rise with a bigger budget. N = 4 is best, and N = 6 and 8 read more sections without scoring higher.

**Conclusions:**
- **exp92's verdict needs correcting.** Its loss came from a training-data conversion bug (submit calls stripped), not from the model looping while searching. With answers recovered, the fine-tuned model is as accurate as the base, and it still reads the cited sections more (0.69–1.24 per question vs 0.00).
- **Reading is still not accuracy:** on these sets, opening the rule didn't make the 4B model more accurate. That part of exp92's conclusion stands.
- **No re-distillation planned:** exp95's recipe + passages (no training) is far ahead on the hard set (88.8% vs 77.2% for the guarded fine-tune) and level on Cornell (76.4% vs 76.8%; different builds, Q4 vs bf16), so the fine-tune isn't worth redoing for now. If it is, rebuild the SFT data with `AgentSubmit(keep_in_messages=True)` so final turns are submit calls.
