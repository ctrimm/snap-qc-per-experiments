# Experiment 105 — confirming the topic router on the cite-only corpus

**Date:** 2026-10-22 (pre-registered before any part ran) · **Code:** `queue_exp105.sh`, `exp105_decide.py`, `exp105_analyze.py`; state-policy-docs `STATE_POLICY_CITED_LETTERS=cite_only`, `STATE_POLICY_CURATED_GUIDANCE=1` · **Logs:** `snap-qc-data/derived/exp105_logs/`

### Why

exp104 found two changes worth testing, both chosen by looking at Cornell, so this run tests them fresh:
- **Retrieval:** keeping the 458 cited CDSS letters out of search but reachable by citation restores retrieval (hard set top 5: 70.1% → 81.2%).
- **Routing:** questions a model labels `noncitizens` go to the date + notes setup. Estimated from existing runs: 90.8–91.0% vs 89.6%.

Before the run, two additions:
- **Curated standing guidance** (`lookup_rule` returns the standing CDSS letters or regulation subsection for 8 topics, such as MPP 63-503.413's 40% self-employment deduction and ACL 21-101 on mid-period changes). The topics were prioritized from the remaining Cornell misses, so part 0 checks them on our own questions first.
- **A learned router** (logistic regression on topic labels, disagreement with no-tool answers, agreement and tool calls). Cross-validated it scored 90.0% when escalating to the combined setup and 89.2% to date + notes, below the topic router (`exp104_learned_router.py`), so it isn't used.

### Design

**Part 0: corpus check on our own questions** (31B agent, `arm=agent`; the 121 questions of our 224-question hard set whose gold document is Californian, `exp105_ca_hard.jsonl`):
- **P0-A:** current corpus defaults (letters in search, no curated guidance);
- **P0-C:** cite-only letters + curated guidance.

Rule, applied by `exp105_decide.py` before part 1 starts: part 1 uses P0-C's config if P0-C ≥ P0-A − 2 points (within noise: on 121 questions one answer is 0.8 points). Otherwise it uses cite-only letters without curated guidance, which retrieval favors.

**Part 1: the router on all 500 Cornell questions** (31B, as_of 2026-06-01, part 0's config):
1. E4B topic labels for all 500 questions (fresh run, temperature 0, the same prompt as exp104).
2. **Plain:** the plain dated agent on all 500.
3. **Date + notes** (date in the prompt, supersession notes, precedence sentence), only on questions E4B labels `noncitizens`.
4. **Router answer:** date + notes for those, plain for the rest.

### Pre-registered hypotheses and readouts

- **H1 (primary):** router − plain, paired within this run, > 0, with the bootstrap 95% CI's lower bound above 0.
- **H2:** router vs exp98-3 (89.6%, plain on the old corpus), paired. Expected about +1.5; reported with a CI, but run-to-run noise (±2.5) means only a CI above 0 counts.
- **Also reported:**
  - plain (this run) vs exp98-3 and exp102-1 (the corpus effect on the plain agent);
  - citizenship accuracy; share of questions routed;
  - minutes per question;
  - the two disputable-key questions stay in (as in every earlier run).

**Success:** H1 holds and the router is ≥ 91.0%. A router ≥ 92% would be the first single-run result in the target range.

Cornell rules as always: aggregate results only; no question text, answer keys or per-question predictions committed; topic-label ids stay in `snap-qc-data/derived/exp105/`.

### Results

<!-- AUTO-RESULTS:START -->
Scored 2026-10-23 02:47 by `exp105_analyze.py`.

### Part 0: our 121 California hard-set questions (31B agent)

| Arm | Accuracy |
|---|---|
| P0-A: current corpus defaults | 90.1% |
| P0-C: cite-only letters + curated guidance | 93.4% |
| C − A (95% CI) | +3.3 [+0.0, +7.4] |

Part-1 config: `P0-A 90.1% P0-C 93.4% -> -T cite_only=true -T curated=true`

### Part 1: Cornell (500)

| Setup | Accuracy | Citizenship (34) |
|---|---|---|
| Plain (this run) | 88.2% | 70.6% |
| **Router** (E4B `noncitizens` → date + notes; 35 questions, 9 answers changed) | **89.8%** | 91.2% |
| ref exp98-3 (old corpus, plain) | 89.6% | 70.6% |
| ref exp102-1 (new corpus, date + notes) | 86.2% | 91.2% |

| Comparison (paired) | Difference, points (95% CI) |
|---|---|
| **H1:** router − plain (this run) | +1.6 [+0.6, +2.8] |
| **H2:** router − exp98-3 | +0.2 [-2.2, +2.6] |
| plain (this run) − exp98-3 | -1.4 [-3.6, +0.8] |

Minutes: plain 663 (1.33 per question); date + notes on the routed questions 46.
<!-- AUTO-RESULTS:END -->
