# Experiment 89 — a corrected judge for exp88, and citations at the end of the note

**Date:** 2026-10-12 · **Code:** `experiments/exp89_rejudge_and_end_cites.py` (pre-registered in its docstring), `exp89_run.sh` · **Outputs:** `../snap-qc-data/derived/exp88/` (`notes_grounded_end.jsonl`, `judge2_*.jsonl`)

### Why

exp88 left two loose ends.

1. Its judge flagged 16% of rule claims as unsupported. By hand, 32 of those 33 were the card's own instructions, and 1 was correct but cut off in a 900-character excerpt.
2. Inline citations cost readability: 31 more notes failed the grade-9 check.

### Method (pre-registered)

- **Part A:** judge v2 re-judges exp88's plain and grounded notes. It gets the full section text, up to 6,000 characters each, and is told explicitly to ignore instructions, documents to request, household facts and card numbers.
- **Part B:** a new arm, grounded_end. Same excerpts as exp88; the note keeps the plain style and ends with one line, "Rules: …".
- **Scoring:** coverage, unsupplied citations, exp62's checks on the prose alone, and judge v2.

Hypotheses:
- **H1:** under 5% of grounded rule claims unsupported or contradicted under judge v2.
- **H2:** grounded_end's pass rate is within 3 points of plain, with coverage over 90%.

### Results

Pending.
