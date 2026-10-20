# Experiment 100 — telling the model when a statute has overtaken the regulation

**Date:** 2026-10-19 · **Code:** state-policy-docs `mcp_server/supersessions.json` and `server.py` (local commit "Supersession notes …"); `exp85_mcq_rag_task.py` amendment 7 and `exp87_heldout_task.py` amendment (`supersession`, `precedence`, `subset`/`category`); `exp100_analyze.py`; `queue_exp100.sh` · **Logs:** `snap-qc-data/derived/exp100_logs/`

### Why

On the 34 Cornell citizenship questions, the dated 31B agent (exp98 arm 3) got 10 wrong. On those 10, its tools returned California's post-H.R. 1 guidance (ACL 25-92 and ACIN I-29-26, 14 times each) and the amended Food and Nutrition Act Sec. 6(f) (8 times). It still answered under the old rules.

The same results contained 7 CFR 273.4 and MPP 63-405, which still list refugees and asylees as eligible noncitizens. FNS hasn't amended 273.4 since 2019, so the eCFR (and ecfr-markdown) carry the pre-H.R. 1 text. The model resolves the conflict in favor of the regulation.

### What changed (state-policy-docs)

- **`mcp_server/supersessions.json`:** four entries for regulation text P.L. 119-21 overrides before amendment:

  | Topic | Regulation | Statute | California applies from |
  |---|---|---|---|
  | Noncitizens | 7 CFR 273.4(a), MPP 63-405.1 | Act Sec. 6(f), Sec. 10108 | 2026-04-01 |
  | ABAWD | 7 CFR 273.24(a)/(c), MPP 63-410 | Act Sec. 6(o), Sec. 10102 | 2026-06-01 |
  | LIHEAP-triggered SUA | 7 CFR 273.9(d)(6)(iii) | Act Sec. 5(e)(6)(C)(iv), Sec. 10103 | — |
  | Internet costs | 7 CFR 273.9(d)(6)(ii) | Act Sec. 5(e)(6)(E), Sec. 10104 | — |

  Each note states the current rule and cites the statute and the state's guidance. All of it was checked against the corpus.
- **The tools:** `get_passages`, `lookup_rule` and `get_section` attach a `superseded_in_part` note to any text under a matched citation, on dates on or after July 4, 2025. `lookup_rule` then lists the statute before the regulation. `STATE_POLICY_SUPERSESSION=0` turns this off, and every earlier experiment ran with it off. The tests pass (34).
- **The prompt sentence** (`precedence=true`), general and naming no topic: "When a statute or newer state guidance conflicts with an older regulation, follow the newer rule: a regulation can stay out of date until it is amended, and tool results flag text that a statute has changed (superseded_in_part)."

### Method (pre-registered)

All runs: Gemma 4 31B agent, LM Studio, temperature 0, thinking off, the same four tools.

| # | Questions | Arms | Purpose |
|---|---|---|---|
| 1 | Our exp94 hard set, the 28 noncitizen questions (as of each question's date) | baseline (notes off) vs notes + precedence | Development check on our own set |
| 2 | Cornell, the 34 citizenship questions (as_of 2026-06-01) | baseline vs notes + precedence | The targeted test |
| 3 | Cornell, all 500 (as_of 2026-06-01) | notes + precedence + check step (scored before and after the check) | Overall effect, compared with exp98 arm 3 and exp99 |

The date 2026-06-01 is post-hoc from the exp98 audit, so arms 2 and 3 are labeled post-hoc.

Bootstrap: 2,000 resamples, seed 100. Arms 1 and 2 are run the same day, so their baselines are same-day reruns.

**Hypotheses:**
- **H1:** notes + precedence raise accuracy on Cornell's 34 citizenship questions above the same-day baseline (difference > 0). A CI excluding 0 is not expected at n = 34.
- **H2:** on our 28 noncitizen questions, notes + precedence don't lower accuracy.
- **H3:**
  - **Before the check:** arm 3 is no worse than exp98 arm 3 on all 500 (difference above −1.5). The notes affect only noncitizen, ABAWD, SUA and internet text.
  - **After the check:** arm 3 reaches exp99's final accuracy or better.

### Results

<!-- AUTO-RESULTS:START -->
Scored 2026-10-20 17:39 by `exp100_analyze.py` (aggregate only).

| Arm | n | Accuracy |
|---|---|---|
| dev 28: baseline | 28 | 96.4% |
| dev 28: notes + precedence | 28 | 96.4% |
| Cornell 34 citizenship: baseline | 34 | 70.6% |
| Cornell 34 citizenship: notes + precedence | 34 | 67.6% |
| Cornell 500: notes + precedence, after check | 500 | 89.0% |
| exp98-3: 31B agent 2026 (no notes) | 500 | 89.6% |
| exp99: 31B agent 2026, after check | 270 | 92.6% |
| Cornell 500: notes + precedence, before check | 500 | 88.6% |
| exp99: before check | 270 | 93.0% |

| Paired contrast (95% CI) | Difference |
|---|---|
| dev 28: notes + precedence − dev 28: baseline (n = 28) | +0.0 [+0.0, +0.0] |
| Cornell 34 citizenship: notes + precedence − Cornell 34 citizenship: baseline (n = 34) | -2.9 [-11.8, +5.9] |
| Cornell 500: notes + precedence, before check − exp98-3: 31B agent 2026 (no notes) (n = 500) | -1.0 [-3.0, +1.0] |
| Cornell 500: notes + precedence, after check − exp99: 31B agent 2026, after check (n = 270) | -0.4 [-2.6, +2.2] |
| Cornell 500: notes + precedence, after check − Cornell 500: notes + precedence, before check (n = 500) | +0.4 [-0.4, +1.2] |

For reference, exp98 arm 3 on the same 34 citizenship questions: 70.6%.
<!-- AUTO-RESULTS:END -->
