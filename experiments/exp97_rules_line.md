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

(pending)
