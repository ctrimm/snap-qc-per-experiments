# Experiment 65 — three-part flag cards

> **Status:** Paused 2026-10-10: waiting on the reviewer A/B ratings. Nothing running.

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

Run 2026-10-10 06:44–06:57, as specified.

**Coverage (real location among the parts listed, flagged errors):** PA top-1 61%, top-2 78%, **top-3 88%**; NY 57%, 74%, **86%** → readout 1 met (≥ 85%).

| 200 eval cards, three parts | pass all | faithful | leads | short (≤ 80) | readable | words | grade |
|---|---|---|---|---|---|---|---|
| template | **100%** | 100% | 100% | 100% | 100% | 71 | 5.5 |
| E4B zero-shot | 66% | 100% | 100% | 100% | 66% | 47 | 8.2 |
| **E2B distilled (exp62 student)** | **99%** | 100% | 99% | 100% | 100% | 54 | 5.1 |

Readout 2 met (template 100%). Readout 3: the distilled E2B is acceptable (faithful 100%, pass 99% ≥ 95%), although it was trained only on two-part cards. Its two failures (PA-2024-281, PA-2024-705) are checker strictness: it wrote "case details" for the card's "other case details" and kept the right order. E4B zero-shot improved from 46% to 66% but is still not acceptable.

**Reviewer packet:** `exp65_reviewer_packet.md` (20 cards, template vs distilled E2B, A/B order randomized; key in `exp65_reviewer_key.json`). Readout 4 is pending Cory's ratings.

### Verdict

Held. Three parts raise coverage by about 10 points (to 86–88%) with notes that stay accurate, short and readable. The distilled E2B handles the new format without retraining. Template vs model is now a human call.

### Next steps

1. Cory rates the packet; the winner becomes the pilot card format.
2. If the model wins, its notes should keep the likelihoods ("about N in 10"): add them to the teacher's style and re-distill (an hour). If the template wins, ship the template and keep the model for later.

