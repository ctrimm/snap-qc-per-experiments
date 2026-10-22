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
### Retrieval (part A): gold document in get_passages' top results

| Config | Our hard set hit@1 / hit@5 (224) | QA pairs, California hit@5 | QA pairs, federal hit@5 | QA pairs, other states hit@5 |
|---|---|---|---|---|
| pre_letters | 52.7% / 82.6% | 96.4% (n=420) | 98.6% | 97.7% |
| current | 39.7% / 70.1% | 86.4% (n=420) | 98.6% | 97.7% |
| current_decay | 46.4% / 75.9% | 86.9% (n=420) | 98.6% | 97.7% |
| decay_strong | 47.3% / 78.1% | 87.6% (n=420) | 98.6% | 97.7% |
| letters_10y_cutoff | 44.6% / 73.7% | 87.4% (n=420) | 98.6% | 97.7% |
| max2letters_only | 39.7% / 67.4% | 77.4% (n=420) | 98.6% | 97.7% |
| strong_max2letters | 47.3% / 74.1% | 81.4% (n=420) | 98.6% | 97.7% |
| dense | 25.9% / 55.4% | 64.8% (n=420) | 81.1% | 89.0% |
| hybrid | 37.1% / 67.9% | 76.4% (n=420) | 93.2% | 94.5% |
| hybrid_decay_strong | 43.8% / 80.4% | 79.0% (n=420) | 93.2% | 94.5% |
| cited_letters_cite_only | 50.4% / 81.2% | 96.2% (n=420) | 98.6% | 97.7% |

Scored 2026-10-22 08:28 by `exp104_route.py` (exploratory; evaluation set).

### Single setups (full runs)

| Setup | Accuracy |
|---|---|
| plain | 89.6% |
| datenotes | 86.2% |
| combined | 89.2% |
| notes_check | 89.0% |

### How well each signal flags the plain agent's mistakes (52 wrong of 500)

| Signal (higher = riskier) | AUROC | Plain-agent accuracy when flagged / not flagged |
|---|---|---|
| 31B stated confidence (100 − c) | 0.534 | 77.8% (n=27) / 90.3% (n=473) |
| 31B no-tool agreement (5 samples) | 0.504 | 83.3% (n=6) / 89.7% (n=494) |
| 31B no-tool disagrees with plain agent (5 samples) | 0.665 | 65.6% (n=64) / 93.1% (n=436) |
| E4B no-tool agreement (5 samples) | 0.515 | 88.0% (n=83) / 89.9% (n=417) |
| E4B no-tool disagrees with plain agent (5 samples) | 0.635 | 79.8% (n=129) / 93.0% (n=371) |
| E4B stated confidence (100 − c) | 0.533 | 75.0% (n=4) / 89.7% (n=496) |
| plain agent tool calls | 0.603 | 85.6% (n=174) / 91.7% (n=326) |
| plain vs date+notes answers differ | 0.685 | 58.2% (n=55) / 93.5% (n=445) |
| plain vs combined answers differ | 0.712 | 50.0% (n=50) / 94.0% (n=450) |
| 31B topic = noncitizens | 0.56 | 72.7% (n=33) / 90.8% (n=467) |
| E4B topic = noncitizens | 0.567 | 72.2% (n=36) / 90.9% (n=464) |

### Routers (all answers from existing runs)

| Router | Accuracy | vs plain (95% CI) | Questions sent to a second setup |
|---|---|---|---|
| 31B topic = noncitizens → date+notes, else plain | 91.0% | +1.4 [+0.4, +2.6] | answers changed on 7 |
| E4B topic = noncitizens → date+notes, else plain | 90.8% | +1.2 [+0.2, +2.4] | answers changed on 8 |
| answers differ (plain vs date+notes) → combined breaks the tie | 91.2% | +1.6 [-0.2, +3.4] | answers changed on 19 |
| majority of plain, date+notes, combined (ties → plain) | 91.2% | +1.6 [-0.2, +3.4] | answers changed on 19 |
| majority of plain, date+notes, combined, 31B no-tool majority (ties → plain) | 90.2% | +0.6 [-0.8, +2.2] | answers changed on 15 |

### Threshold routers, split-half cross-validated (threshold picked on one half, scored on the other)

| Signal → escalate to | Cross-validated accuracy | Plain on the same halves | Share escalated |
|---|---|---|---|
| 31B stated confidence (100 − c) → combined | 89.4% | 89.6% | 2.6% |
| 31B stated confidence (100 − c) → date+notes | 89.0% | 89.6% | 2.6% |
| 31B stated confidence (100 − c) → notes+check | 89.6% | 89.6% | 0.4% |
| 31B no-tool agreement (5 samples) → combined | 89.6% | 89.6% | 1.2% |
| 31B no-tool agreement (5 samples) → date+notes | 89.4% | 89.6% | 0.6% |
| 31B no-tool agreement (5 samples) → notes+check | 89.6% | 89.6% | 1.2% |
| 31B no-tool disagrees with plain agent (5 samples) → combined | 89.4% | 89.6% | 5.8% |
| 31B no-tool disagrees with plain agent (5 samples) → date+notes | 88.8% | 89.6% | 5.8% |
| 31B no-tool disagrees with plain agent (5 samples) → notes+check | 88.8% | 89.6% | 5.8% |
| E4B no-tool agreement (5 samples) → combined | 90.0% | 89.6% | 8.6% |
| E4B no-tool agreement (5 samples) → date+notes | 89.0% | 89.6% | 4.4% |
| E4B no-tool agreement (5 samples) → notes+check | 89.0% | 89.6% | 7.6% |
| E4B no-tool disagrees with plain agent (5 samples) → combined | 89.8% | 89.6% | 25.8% |
| E4B no-tool disagrees with plain agent (5 samples) → date+notes | 89.0% | 89.6% | 12.2% |
| E4B no-tool disagrees with plain agent (5 samples) → notes+check | 88.8% | 89.6% | 12.2% |
| E4B stated confidence (100 − c) → combined | 89.8% | 89.6% | 0.8% |
| E4B stated confidence (100 − c) → date+notes | 89.6% | 89.6% | 0.8% |
| E4B stated confidence (100 − c) → notes+check | 89.0% | 89.6% | 25.8% |
| plain agent tool calls → combined | 89.0% | 89.6% | 49.4% |
| plain agent tool calls → date+notes | 89.2% | 89.6% | 4.6% |
| plain agent tool calls → notes+check | 88.8% | 89.6% | 46.6% |
| plain vs date+notes answers differ → combined | 91.0% | 89.6% | 11.0% |
| plain vs date+notes answers differ → date+notes | 89.6% | 89.6% | 0.0% |
| plain vs date+notes answers differ → notes+check | 89.4% | 89.6% | 5.4% |
| plain vs combined answers differ → combined | 89.2% | 89.6% | 5.6% |
| plain vs combined answers differ → date+notes | 90.6% | 89.6% | 10.0% |
| plain vs combined answers differ → notes+check | 89.4% | 89.6% | 4.4% |

### Ceilings (a perfect router)

| Setups available | Oracle accuracy |
|---|---|
| plain + date+notes | 92.6% |
| plain + date+notes + combined | 94.6% |
| plain + date+notes + combined + notes+check | 95.2% |
<!-- AUTO-RESULTS:END -->

### Conclusions

**1. Retrieval: the imported letters were the problem, and keeping them cite-only fixes it.**
- **Cause:** with the 458 cited CDSS letters in passage search, the gold document fell out of the top 5 for about 1 in 8 hard questions (82.6% → 70.1%), and California QA top-5 fell from 96.4% to 86.4%.
- **Ranking-only fixes recover part of it:** age weighting gets to 75.9%, strong weighting to 78.1%; capping letters makes it worse (67.4–74.1%).
- **Local embeddings (nomic-embed-text-v1.5) are worse than BM25 on this legal text:** dense 55.4%, hybrid 67.9%, hybrid + strong weighting 80.4% but worse top-1 and California QA.
- **The fix:** keep the imported letters out of search but reachable by citation (`STATE_POLICY_CITED_LETTERS=cite_only` plus the OKF citation links). That recovers 81.2% / 96.2%, and every letter still resolves through `get_section`.

**2. Self-assessed confidence is useless as a router signal** (AUROC 0.50–0.53):
- 31B stated confidence;
- agreement across 5 samples;
- the same from E4B.

The models are confidently wrong.

**3. Disagreement is the useful signal:**
- the plain agent's answer differs from the combined setup's (AUROC 0.71) or from the date + notes setup's (0.69);
- more cheaply, the 31B's no-tool majority answer differs from the plain agent's (0.67; the plain agent is right on 65.6% of those vs 93.1% elsewhere).

**4. The best cheap router is by topic** (labeled by the model, not hand-picked keywords):
- **Rule:** questions E4B or 31B labels `noncitizens` go to the date + notes setup.
- **Accuracy:** 90.8% (E4B labels) and 91.0% (31B labels), vs 89.6%: +1.2 [+0.2, +2.4] and +1.4 [+0.4, +2.6].
- **Cost:** about 7% of questions get one extra 1-minute agent run, plus a 2-minute E4B labeling pass for all 500.

The disagreement tiebreak reaches 91.2% (+1.6 [−0.2, +3.4]), but needs both cheap setups on every question plus the 4.5-minute combined setup on 11%.

**Ceilings:** a perfect router over these setups would reach 92.6–95.2%.

**What this suggests for a confirmatory run (exp105), on one corpus with the cited letters cite-only:**
- the plain dated agent on all 500 questions;
- E4B topic labels, with `noncitizens` questions also run through the date + notes setup;
- the router's answer = date + notes for those, plain otherwise.

Every threshold above was chosen on Cornell, so only a fresh, pre-registered run counts.
