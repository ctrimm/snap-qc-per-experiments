# Experiment 62 (design) — plain-language flag cards for reviewers

**Date:** 2026-10-09 · **Status:** steps 1–2 done; reviewer comparison in exp65 · **Builds on:** exp58 (ranker), exp61 (where-to-look), exp52/59/60 (language models)

## Goal

For every case the ranker puts at the top of a state's review queue, give the caseworker a short, accurate answer to two questions:

1. **Why was this case flagged?**
2. **What should I check first, and how can I help?**

The answer has to be faithful (say nothing the system didn't actually compute), point at the right part of the case, and be readable in under 30 seconds.

## What the evidence says

| Finding | Source | Consequence |
|---|---|---|
| The ranker's reasons explain risk and dollars at stake, not location | exp61 | Use them for "why flagged", not for "where to look" |
| A per-state where-to-look model names the error's part in its top two 74–78% of the time (PA, NY, ID) | exp61 | Use it for "check first" |
| Public QC fields rarely show the correction itself (13–18% of errors) | Oct 9 check | A language model can't find the error by reasoning over these fields; don't ask it to |
| E4B reads cases best; E2B is 1.8× faster but weaker at reading cases cold | exp59, exp60 | Rewriting a finished card is easier, so try E2B first |

## Design: three deterministic layers, plus an optional language layer

**Layer 1. Why flagged (ranker).** Expected error dollars, priority band (top 10% / 20%), and the top two or three reason groups from ablation, written as facts from the case: "Reported income of $2,140 is high for a one-person household. The monthly benefit is $291, so an error here would be costly."

**Layer 2. Check first (where-to-look model).** The top two parts of the case with plain likelihoods: "In similar flagged cases, the error was usually in earned income (about 6 in 10) or shelter costs (about 2 in 10)."

**Layer 3. What to ask for (policy checklist).** A fixed table per part of the case, written once from SNAP verification rules and reviewed by a QC lead. Examples:

| Part | First checks |
|---|---|
| Earned income | Pay stubs for the last 30 days; any new job or change in hours; employer or wage-database match |
| Unearned income | SSA/SSI, unemployment and child-support amounts against current award letters or data matches |
| Shelter costs | Current lease or mortgage statement; who in the household pays rent |
| Utility allowance | Whether the household pays heating or cooling separately; utility bill in a member's name |
| Household size | Who lives in the home and buys food together; any member who moved in or out |
| Medical | Out-of-pocket costs for elderly or disabled members; receipts and recurring bills |
| Dependent care | Provider statement and amount; whether care is needed for work or training |

Each part will also carry the state's most common type of mistake there (T4), e.g. "most errors here are a new job not reported".

**How the caseworker helps (feedback).** One step at the end of each review: was there an error, which part, how many dollars. This closes the loop. It measures whether "check first" was right, retrains the where-to-look model each year, and gives states that don't record error locations (TX) the labels they lack.

**Layer 4, optional. Plain-language rewrite (language model).** The model receives the finished card and returns two or three sentences. It may not add facts, numbers or reasons that aren't on the card.

## Post-training plan for Layer 4 (cheapest first; stop when the checks pass)

1. **No training.** Prompt E2B and E4B with the card and a fixed format. Score automatically on 200 cards:
   - faithfulness: every number and named part appears on the card; no new reasons
   - leads with the card's first "check first" part
   - readability: under 70 words, about 8th-grade reading level
2. **Distillation, only if step 1 fails.** Gemma 4 31B writes explanations for about 2,000 cards (synthetic cases plus real non-holdout cases), automatic checks discard any that fail, and E2B is fine-tuned on the rest (about an hour on the Mac Studio). Re-score on the same 200 cards.
3. **Reward tuning, only if step 2 still misses.** GRPO with faithfulness, length and reading-level rewards, reusing the exp52 infrastructure.

Human check at every step: 15–20 cards rated by a QC reviewer for clarity and usefulness. Automatic checks catch made-up facts; only reviewers can tell whether a card helps.

## Success criteria (to be frozen before the build's first scoring)

- 100% of rewritten cards pass the faithfulness check (any made-up fact is a failure).
- "Check first" covers the real error in its top two for at least 70% of flagged error cases in PA and NY (exp61 level).
- Reviewer rating: most cards judged clear and useful.

## Frozen before any language model output (2026-10-10)

- **Cards:** `exp62_flag_cards.py` → `exp62_cards.jsonl`, 327 cards (PA 164, NY 163; top 20% of each holdout). Check-first top-2 covers the real error location for 78% (PA) and 74% (NY) of flagged errors with a location label: **design criterion 2 met.**
- **Evaluation set:** 200 cards, 100 per state, `random.Random(62)` → `exp62_eval_ids.txt`.
- **Checker:** `exp62_check.py` (faithful numbers and topics, no forbidden claims; leads with the first check-first part; ≤ 70 words; Flesch-Kincaid ≤ 9). Verified on planted mistakes (wrong number, accusation, "overpaid", topic not on card, wrong order, too long): all caught. Two checker/card bugs were fixed before freezing, found on the template baseline: the instruction-word match caught "review" in "review queue", and likelihoods could read "10 in 10", now capped at 9.
- **Baseline:** the deterministic template passes 100% of checks (63 words, grade 6.3). A language model can therefore only match it on automatic checks; its possible gain is clarity to a human reader.
- **Step 1 (no training):** E2B and E4B, greedy, thinking off, max 200 tokens, one fixed prompt (`exp62_rewrite.py`). A model's notes are **acceptable** if faithful on 100% of the 200 cards and passing all checks on ≥ 95%.
- **Decision rule:** the smallest acceptable model goes to a blind reviewer comparison against the template (15–20 cards). If neither is acceptable, step 2 (distillation with filtering) runs. If the reviewer doesn't prefer the model's notes, ship the template.

## Step 1 result (2026-10-10 00:45)

| 200 eval cards | pass all | faithful | leads | short | readable | words | grade |
|---|---|---|---|---|---|---|---|
| template | 100% | 100% | 100% | 100% | 100% | 63 | 6.3 |
| E2B zero-shot | 40% | 100% | 100% | 100% | 40% | 55 | 9.1 |
| E4B zero-shot | 46% | 100% | 100% | 100% | 46% | 49 | 8.9 |

Neither is acceptable (≥ 95% pass); both fail only on reading level. No invented facts, numbers or accusations in 400 notes. Per the decision rule, step 2 runs.

## Step 2 procedure (fixed before running, 2026-10-10)

- **Training cards:** `exp62_flag_cards.py --train-cards --states PA,NY,ID,UT,SD`: 2,535 cross-fitted cards from non-holdout rows (5 folds; fit on 4/5, card the top 20% of the other 1/5). No overlap with the 200 eval cards (those are holdout cases).
- **Teacher:** Gemma 4 31B with the student prompt plus short-sentence style guidance (`--teacher`); the guidance was tuned on 6 training cards only.
- **Filter:** keep teacher notes passing every frozen check against their own card (`exp62_step2_data.py`); 100 passing cards held out (seed 62) for checkpoint choice; the rest as SFT pairs with the **student** prompt (95/5 train/valid).
- **Student:** E2B, answer-only SFT with the exp52 LoRA recipe, lr 1e-5, 500 steps, checkpoint every 100.
- **Checkpoint choice:** highest pass rate on the 100 held-out training cards; ties to the earlier step.
- **Final:** the chosen checkpoint writes notes for the 200 eval cards once; same acceptance rule as step 1 (faithful 100%, pass ≥ 95%).

## Step 2 result (2026-10-10 06:44)

Teacher (31B) notes on 2,535 training cards: 2,513 (99%) passed every check. SFT on 2,292 (121 validation), 500 steps, 0.73 it/s, val loss 0.137 → 0.086. Every checkpoint scored 100% on the 100 selection cards; the rule picked step 100.

| 200 eval cards | pass all | faithful | leads | short | readable | words | grade |
|---|---|---|---|---|---|---|---|
| template | 100% | 100% | 100% | 100% | 100% | 63 | 6.3 |
| E2B zero-shot | 40% | 100% | 100% | 100% | 40% | 55 | 9.1 |
| E4B zero-shot | 46% | 100% | 100% | 100% | 46% | 49 | 8.9 |
| **E2B distilled (step 2)** | **100%** | **100%** | **100%** | **100%** | **100%** | **42** | **4.2** |

**Verdict: acceptable** under the frozen rule. The distilled E2B notes are shorter and plainer than the template, with no invented facts. Two things for the reviewer comparison: they drop the "about N in 10" likelihoods and the monthly benefit (the teacher omitted them and the student learned that), and every note follows the same five-sentence pattern ("Top 10% priority. Expected error is $70. … First, check … Next, check …"). Per the decision rule, the template vs model choice goes to a blind reviewer comparison (exp65's packet).

## What it isn't

It doesn't decide anything about a household, and it doesn't touch the federal QC sample. It explains why the state's own review queue put a case where it did, and suggests where to start.
