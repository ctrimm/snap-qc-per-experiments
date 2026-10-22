# Experiment 104 — what a per-question routing layer could use

**Date:** 2026-10-22 · **Code:** `exp104_retrieval.py` (part A), `exp104_signals_task.py` + `queue_exp104.sh` (part B), `exp104_route.py` (part C); state-policy-docs `STATE_POLICY_LETTER_WEIGHTS` (weighting variants) · **Logs:** `snap-qc-data/derived/exp104_logs/`, `exp104/retrieval.jsonl`

### Why

No single setup has beaten the plain dated 31B agent (89.6%) by more than noise. Rerunning that setup flips about 4% of answers, which is ±2.5 points on 500 questions. But different setups get different questions right:
- the plain agent or the date + notes setup: 92.6%;
- plus the combined setup: 94.6%.

So the next gains come from routing each question to the right setup. This experiment collects the cheap measurements for designing that layer. It's exploratory, on the evaluation set; a router chosen from it needs a fresh, pre-registered run to be confirmed.

### Parts

**A. Retrieval, no model.** How often the gold document is in `get_passages`' top 1 and top 5:
- **Question sets:** the 224-question hard set, and the 2,658 verified QA pairs from the Oct 18 Hugging Face work.
- **Configs:** the corpus before the CDSS letters; the current corpus; current + letter weighting; two stronger weightings.

**B. Cheap signals on the Cornell quiz** (no tools, about an hour):
- 31B and E4B answering with a stated confidence (0–100);
- 31B and E4B answering 5 times at temperature 0.7 (agreement);
- 31B and E4B labeling each question's topic with `lookup_rule`'s 38 topics.

**C. Routing analysis** (`exp104_route.py`, from existing full runs: plain, date + notes, combined, notes + check):
- how well each signal flags the plain agent's mistakes (AUROC, and accuracy when flagged vs not);
- routers by topic, by disagreement with a tiebreak, and by majority vote;
- threshold routers, cross-validated on two halves (pick on one, score on the other);
- oracle ceilings.

**Caveat:** comparisons mixing runs on the old corpus (plain, combined, notes + check) and the new one (date + notes) can't be separated from the corpus change.

### Results

<!-- AUTO-RESULTS:START -->
(pending)
<!-- AUTO-RESULTS:END -->
