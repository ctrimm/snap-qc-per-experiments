# Experiments 76–77 — v2 flag cards, and a model that keeps the odds

**Date:** 2026-10-10 · **Code:** `exp76_77_run.sh`, `exp76_check.py`, `exp77_data.py` (with `exp62_flag_cards.py --calibrate --wording v2`, `exp62_rewrite.py --wording v2 --teacher-style v2`)

## Pre-registration (committed before the run)

### exp76 — v2 cards

Cards for PA and NY flagged holdout cases (the same cases as exp62/65), with three parts (exp65), odds recalibrated by exp74's temperature (PA 2.9, NY 2.9; ID 2.8; other states 2.9), and reworded odds: "in about N of 10 similar cases with an error, that's where it was". Scored on exp62's 200 evaluation case ids with exp62's frozen checks (80-word limit) plus a new check, **keeps odds and benefit** (the note gives the first part's "N of 10"/"N in 10" and the monthly benefit). Notes: the v2 template; exp62's distilled E2B (step 100, unchanged).

### exp77 — re-distilled E2B that keeps the odds and benefit

- Training cards: v2 cross-fitted cards for PA, NY, ID, UT, SD (`exp76_train_cards.jsonl`); a random 1,200 (seed 77) go to the teacher.
- Teacher: Gemma 4 31B with style v2 (adds: mention the monthly benefit and each part's "N of 10").
- Filter: keep notes that pass every frozen check **and** keep odds and benefit; 100 held out (seed 77) for checkpoint choice; the rest as student-prompt pairs (95/5).
- Student: E2B, exp52 LoRA recipe, lr 1e-5, 500 steps, checkpoint every 100; choose the checkpoint with the highest selection pass rate (all checks + keeps odds), ties to the earlier step.
- Final: once on the 200 v2 evaluation cards. Acceptable if faithful 100%, all checks ≥ 95%, keeps odds and benefit ≥ 95%.
- Then a new blind A/B packet (template v2 vs the exp77 model if acceptable, else the exp62 model), seed 76.

## Results

### exp76 — v2 cards

Coverage unchanged by recalibration (top-3 88% PA, 86% NY); first-pick odds now span 2–9 in 10 instead of mostly 9.

| 200 v2 cards | pass all | faithful | leads | short (≤ 80) | readable | keeps odds + benefit | words | grade |
|---|---|---|---|---|---|---|---|---|
| v2 template | 56% | 100% | 100% | **56%** | 100% | 100% | 79 | 5.9 |
| exp62 E2B (unchanged) | **100%** | 100% | 100% | 100% | 100% | **0%** | 56 | 5.1 |

The v2 template's longer odds wording ("in about N of 10 similar cases with an error, that's where it was") pushes 44% of its notes past 80 words. The exp62 model passes every check but never states the odds or the benefit.

### exp77 — re-distilled E2B

Teacher (31B, style v2) notes on 1,200 training cards: 762 (64%) passed every check including odds and benefit (the extra content made notes longer, so more failed the length limit than in exp62). SFT on 628 (34 validation), 500 steps; selection pass 0.96–0.99 across checkpoints, step 500 chosen (0.99).

| 200 v2 cards | pass all | faithful | leads | short | keeps odds + benefit | words | grade |
|---|---|---|---|---|---|---|---|
| **exp77 E2B** | **94%** | 100% | 99% | 94% | **100%** | 70 | 1.8 |

Of the 13 failures, 11 are notes of 81–84 words and 2 are the known checker strictness ("case details" for "other case details"). **Not acceptable under the pre-registered bar (95%)**, so the reviewer packet (`exp77_reviewer_packet.md`) compares the v2 template with the exp62 model, per the rule.

**A problem the checker can't see.** The exp77 notes state the odds as, for example, "Check shelter costs first … This had errors in 5 of 10 cases." The card means "among similar cases *with an error*, 5 in 10 had it in shelter costs"; the note reads as "half of such cases have a shelter error". The number is faithful; the meaning isn't. The checker verifies numbers, topics and order, not what a sentence claims about them.

### Verdict

exp76: held as a card build (coverage kept, odds honest), but the v2 template wording is too long. exp77: did not meet its bar (94% vs 95%), and independently it misstates what the odds mean, so it shouldn't ship even with a looser length limit.

### Next steps

1. Shorten the template's odds phrase (e.g. "Most likely: earned income (about 6 in 10 errors like this)").
2. Add a meaning check for the odds sentence (it must say the odds are among errors), applied to teacher notes and model notes, then re-distill.
3. The packet in `exp77_reviewer_packet.md` is still useful: v2 template vs the exp62 model.

