# Experiment 97 — the flag-card "Rules:" line at scale, on fresh cards

**Date:** 2026-10-16 · **Code:** `exp97_rules_line.py` (pre-registered in its docstring; `rules_line()` is the pipeline function), `exp62_rewrite.py`, `queue_exp97.sh` · **Data:** `exp97_cards.jsonl`, `exp97_ids.txt`

### Why

exp89 found the design that works for cited flag notes: the model writes the plain note, and code appends the "Rules:" line. It kept the plain notes' 70% pass rate with complete citations. But that was a post-hoc check on 327 PA/NY cards, with an unfiltered line that also listed parts the note never mentions. This experiment builds the filtered version into the pipeline and tests it on cards no note model has seen.

### Method (pre-registered)

**Cards:** 517 v2 cards for the Idaho, Utah and South Dakota holdout cases (three parts, calibrated odds). They don't overlap exp77's training cards (those are cross-fitted on the non-holdout rows).

Texas was the first choice but can't be carded: in FY2022 only 1 of 866 Texas QC records carries an error-location label (Pennsylvania: 353 of 817), and the where-to-look model trains on those labels.

**Writers** (mlx, greedy, v2 wording):
- **E2B:** the shipped model, exp77's E2B at step 500.
- **E4B:** E4B zero-shot, the bf16 build. exp88/89's plain arm used the Q4 build.

**The Rules line** is written by code from the card's check parts and exp88's fixed element-to-rule map. Each citation is resolved as of the case date.
- **All:** every mapped check part, labeled "Rules for the parts to check".
- **Filtered:** only the parts the note names, found by a keyword detector. If it finds none, it falls back to the "All" line.

**Reference:** Gemma 4 31B reads each note and the card's part names, and lists the parts the note tells the caseworker to check.

**Readouts, per writer:**
- exp76's checks on the prose: pass all checks, keeps odds and benefit, words, grade;
- the filtered line's precision and recall against the reference, and its exact-match share;
- the "All" line's precision;
- the share of notes where the detector found nothing;
- the share of citations that resolve on the case date.

**Hypotheses:**
- **H1:** the E2B notes pass all checks on at least 90% of fresh cards (exp77: 94% on PA/NY).
- **H2:** the filtered line's precision and recall are each at least 95% for both writers.
- **H3 (descriptive):** how often an unfiltered line cites a part the note never mentions.

**Dev check (not scored):** on exp77's 200 PA/NY notes, the detector found every mapped part. The E2B style names each check part.

### Results

Run October 17, 01:05–02:05 (`snap-qc-data/derived/exp97/`, `exp97_results.json`). The 31B parsed all 1,034 judgments. Every citation resolved in the corpus on its case date.

| 517 fresh cards | E2B (shipped, exp77) | E4B zero-shot |
|---|---|---|
| Pass all exp76 checks | **97.1%** | 76.4% |
| Keeps odds and benefit | 100% | 0% |
| Words | 70.6 | 47.4 |
| Reading grade | 1.8 | 8.1 |
| Detector found no part | 0% | 0% |
| Filtered line, precision vs 31B | **100%** | 89.6% |
| Filtered line, recall vs 31B | **100%** | 99.5% |
| Filtered line, exact match | 100% | 74.9% |
| Unfiltered ("All") line, precision | 100% | 73.8% |

**Why E4B's filter over-lists:** E4B's notes open with the card's reason ("flagged because of earned income and shelter costs"), then tell the caseworker to check only one or two parts. The detector counts the reason sentence, so the line lists a part the note mentions but never says to check (shelter 60 times, earned 30, unearned 28). Misses are rare: 5, all child support. The E2B notes name every check part in its own sentence, so the filter and the full list agree.

**Post-hoc (not pre-registered, same data):** running the detector only on the note's sentences that don't give the flag reason (no "flagged", "stand out" or "priority") gives:

| Writer | Precision | Recall | Exact match |
|---|---|---|---|
| E4B | 97.8% | 99.1% | 93.6% |
| E2B | 100% | 100% | 100% |

It would need a fresh confirmation before it's adopted.

### Verdict

- **H1 held:** the shipped E2B passes all checks on 97.1% of fresh ID/UT/SD cards, above the 90% bar and above its PA/NY result (94%). It keeps the odds and benefit on every card.
- **H2 held for E2B, failed for E4B:** E2B is at 100% / 100%. E4B's precision is 89.6% (recall 99.5%). The post-hoc sentence filter brings it to 97.8%.
- **H3:** an unfiltered line cites a part the note never names on 26% of E4B's listed parts, and on none of E2B's.

**For the pipeline:** with the shipped E2B writer, the code-appended "Rules:" line is correct on every fresh card, at grade-2 reading level, with no model-written rule text. That makes the cited flag card ready for the reviewer A/B. If another writer is ever used, add the reason-sentence filter and re-test it.
