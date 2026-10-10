# Experiment 66 — explanation self-training loop

**Date:** 2026-10-10 · **Code:** `exp66_run.sh`, `exp66_round.py` (uses `exp62_rewrite.py`, `exp62_check.py`, `exp52_sft_train.sh`) · **Results:** `exp66_*`

## Pre-registration (committed before the run; queued behind exp65)

### Question

Can the exp62 student (E2B fine-tuned on filtered 31B notes) improve itself without the teacher? Each round it writes notes, a fixed checker keeps only the ones that pass, and it is retrained on them (rejection-sampling self-training). The checker is code, independent of the model, so the loop can't learn to pass by inventing facts. What it can't see is usefulness, and repeated self-training tends to make outputs more alike, so diversity is tracked.

### Fixed in advance

| What | Value |
|---|---|
| Start | exp62 step-2 student (its selected checkpoint) |
| Each round | sample 2 notes per card (temperature 0.8, top-p 0.95) on 1,200 training cards (fresh random draw per round, never the 100 selection or 200 eval cards); keep one passing note per card (lowest reading grade, then fewest words); retrain E2B **from base** on exp62's filtered teacher pairs + all student passes so far (latest round wins per card); 300 steps, same LoRA recipe; pick the checkpoint (100/200/300) with the best pass rate on the 100 selection cards |
| Stop rule | stop when a round's best selection pass rate isn't at least 1 point above the previous round's; keep the previous model; at most 3 rounds |
| Tracked each round | selection pass rate, faithfulness, mean reading grade, distinct-bigram ratio, share of notes with the most common opening |
| Final | the kept model writes notes for the 200 eval cards once; compared with the exp62 student and the template under exp62's acceptance rule |

### Pre-declared readouts

1. Does the pass rate rise across rounds, and where does it stop?
2. Does faithfulness stay at 100%?
3. Does diversity fall (notes converging on one phrasing)? A fall with no pass-rate gain is a reason to stop the loop even if the rule hasn't triggered.

## Results

_Pending._
