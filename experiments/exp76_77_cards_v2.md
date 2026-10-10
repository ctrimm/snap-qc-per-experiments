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

_Pending._
