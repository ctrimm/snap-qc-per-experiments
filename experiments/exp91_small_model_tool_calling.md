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

All E4B. Paired bootstrap against the plain agent run the same day.

| Question set | Plain agent | Strict | Recipe | Recipe − plain (95% CI) | 31B agent |
|---|---|---|---|---|---|
| exp87 held-out (243) | 88.9% | 92.6% | **95.5%** | **+6.6 [+2.1, +10.7]** | 99.6% |
| exp90 hard (75) | 82.7% | 84.0% | 86.7% | +4.0 [−2.7, +10.7] | 92.0% |
| Cornell quiz (500, dated) | 75.6% | — | 74.6% | −1.0 [−4.6, +2.4] | 88.8% (exp86) |

**exp87 set by part** (wrong answers, plain → strict → recipe):

| Part | Plain | Strict | Recipe |
|---|---|---|---|
| Computation (of 80) | 17 | 4 | 3 |
| Table (of 120) | 4 | 8 | 3 |
| Rule (of 43) | 6 | 6 | 5 |

**Dates in calls:** the share of calls carrying `as_of` didn't change (87%, 87%, 85%). The calls without it are all `calculate_benefit` calls, about 60 in every arm. With the date marked required, E4B usually follows the bad call with a second one that includes the date, so computation errors fall from 17 to 3–4 without the first call improving.

**Reading the rule:** on the exp87 set, `get_section` calls went from 6 to 17 with the recipe. On the Cornell quiz the recipe barely moved it (0.01 → 0.07 calls per question), even though the procedure tells the model to read the cited section. 31B does this 0.59 times per question.

### Verdict

**Partly held.**

- **H1 (strict):** half held. Computation accuracy reached 95% (≥ 90%), but through retries; the first call still omits the date about as often (`as_of` share stays about 86%).
- **H2 (recipe beats the plain agent on all three sets):** held only on the exp87 set, where it closes about 62% of the gap to 31B (88.9% → 95.5% vs 99.6%). Not significant on exp90; slightly negative on Cornell.
- **H3 (Cornell):** did not hold. The recipe didn't raise accuracy or make E4B read the cited rule.

Schema and prompt fixes repair E4B's tool use where the right call is mechanical: the calculator with a date, or the table for a year. They don't make it do what the 31B does on open policy questions, which is to open and read the governing section before answering. That remaining gap is behavior a prompt didn't instill.

### Next steps

1. **exp92, the remaining gap:** fine-tune E4B on 31B tool-use trajectories (lookup, then read the section, then answer), generated on a separately built training set. Never use the Cornell quiz or the exp87/90 test sets. Evaluate once on Cornell and exp90.
2. **In production:** use the recipe plus the required date for structured questions, and route open policy questions to 31B, or to E4B with attached, date-filtered passages, which did best on exp90's date questions.
