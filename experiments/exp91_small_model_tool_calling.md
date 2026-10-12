# Experiment 91 — fixing the small model's tool calling without retraining

**Date:** 2026-10-12 · **Code:** `exp87_heldout_task.py` (arms `agent_strict`, `agent_recipe`), `exp85_mcq_rag_task.py` (`-T recipe=true`), state-policy-docs `STATE_POLICY_REQUIRE_AS_OF`, `exp90_91_analyze.py`, `queue_exp90_91.sh`

### Why

With the same tools, the 31B gains far more than E4B:

| Test | E4B agent | 31B agent |
|---|---|---|
| exp86/85 (Cornell quiz), gain over no tools | +2.6 (CI includes 0) | +4.8 |
| exp87 (held-out set), accuracy | 84.8% | 99.6% |

The exp87 logs show why:
- **Missing dates:** 17 of E4B's 21 wrong computation answers came from calculator calls without `as_of`, so the calculator used today's fiscal-year tables. Overall, 86% of E4B's calls carried the date against 100% for 31B.
- **Not reading the rule:** E4B almost never opens the cited section (`get_section` about 0.01 per question on Cornell vs 31B's 0.59). It answers from summaries.

So the gap is mostly tool-calling discipline, not reasoning.

### Method (pre-registered)

Two cheap fixes, no retraining:

1. **Strict.** The server lists `as_of` as a required parameter in every date-aware tool's schema (`STATE_POLICY_REQUIRE_AS_OF=1`, tested). Small models fill required parameters more reliably than optional ones.
2. **Recipe.** Strict, plus a fixed procedure in the prompt:
   - for benefit amounts, call `calculate_benefit` with every fact and the date;
   - for yearly figures, call `lookup_rule`, which returns that year's table;
   - otherwise call `lookup_rule`, then `get_section` on the best citation;
   - answer only from the tools.

   On the Cornell quiz (undated questions; the server supplies 2025-06-01), the recipe is: `lookup_rule`, then `get_section`, then `get_passages` for California rules.

Arms, all E4B:

| Question set | Arms |
|---|---|
| exp87 held-out | agent (same-day rerun), strict, recipe |
| exp90 hard | agent, strict, recipe |
| Cornell quiz | agent dated (rerun), agent dated + recipe |

Readouts: accuracy, paired CIs against the plain agent, share of calls carrying `as_of`, and `get_section` use.

Hypotheses:
- **H1:** strict raises the share of calls with `as_of` to 95% or more, and E4B's computation accuracy on the exp87 set to at least 90%.
- **H2:** the recipe beats the plain agent on all three sets, closing at least half of the E4B–31B gap on the exp87 set.
- **H3:** on the Cornell quiz, the recipe beats the plain dated agent (exp85: 76.0%), with `get_section` use rising from about 0.

If a large gap remains, the next step is exp92: fine-tune E4B on 31B tool-use trajectories from a separately generated training set (never the Cornell quiz or these test sets).

### Results

Pending (queued after exp89).
