# Experiment 65 — three-part flag cards

**Date:** 2026-10-10 · **Code:** `exp65_run.sh`, `exp65_check.py` (uses `exp62_flag_cards.py --top-k 3`, `exp62_rewrite.py`) · **Results:** `exp65_cards.jsonl`, `exp65_notes_*.jsonl`, `exp65_reviewer_packet.md`

## Pre-registration (committed before the run; queued behind exp62 step 2)

### Question

exp62's cards list two parts of the case to check, which covers the real error location for 74–78% of flagged errors. A measurement on the same models (Oct 10) showed three parts would cover 86–88% (PA 88%, NY 86%, ID 87%). Generic advice also gains at three parts (77–83%), so the model's edge moves to the *order*: its first pick is right 45–61% of the time against 17–31% for generic advice. Does a three-part card, numbered with the best bet first, keep the notes accurate, short and readable?

### Fixed in advance

| What | Value |
|---|---|
| Cards | `exp62_flag_cards.py --top-k 3` for PA and NY flagged holdout cases; otherwise identical to exp62 (2-part cards verified byte-identical after the `--top-k` change) |
| Evaluation cards | the same 200 cases as exp62 (`exp62_eval_ids.txt`) |
| Checks | exp62's frozen checks, with the length limit raised from 70 to **80 words** for the third part (the template's third part adds about 8 words) |
| Notes | template; E4B zero-shot; and exp62's distilled E2B (its selected checkpoint) if step 2 produced one. Same prompt as exp62 (cards now list a third check) |
| Reviewer packet | 20 cards (10 PA, 10 NY, seed 65): template vs the best faithful model note, A/B order randomized, key stored separately |

### Pre-declared readouts

1. **Coverage:** top-3 covers the real location for **≥ 85%** of flagged errors in both PA and NY.
2. **Template:** passes all checks on 100% of the 200 cards.
3. **Models:** acceptable as in exp62 (faithful 100%, pass ≥ 95%); report change vs the two-part cards.
4. **Reviewer:** Cory's A/B ratings on the packet decide template vs model for the pilot (no automatic threshold).

## Results

_Pending — runs automatically after exp62 step 2._
