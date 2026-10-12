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

All 327 cards per arm. Judge v2 (31B) parsed 979 of 981 judgments.

| E4B notes | Plain (exp88) | Grounded, inline citations (exp88) | Grounded, citations at end (new) |
|---|---|---|---|
| Citation coverage | — | 97.3% | 82.0% |
| Unsupplied citations | 0% | 0% | 0% |
| Faithful to the card | 100% | 100% | 99.7% |
| Reading grade ≤ 9 | 70.0% | 60.6% | **28.1%** |
| Passing all exp62 checks | 70.0% | 60.6% | **9.2%** |
| Prose words | 52.7 | 63.4 | 64.3 |
| Rule claims (judge v2) | 8 | 105 | 6 |
| Unsupported or contradicted | 0% | **1.9%** (2) | 0% |

Pass rate, end − inline: −51.4 [−57.2, −45.6]; end − plain: −60.9 [−66.4, −55.7].

**The 2 claims judge v2 still flagged** (NY-2024-357) are caseworker instructions: "ask for pay stubs from the last 30 days", "request court orders and proof of payments". Across all three arms, no note misstates a rule.

**Why the end-citation notes read worse:** the scoring removes the "Rules:" line correctly (all 327 notes end with it). The prose itself is harder: grade 10–11, in longer compound sentences ("First, review … by asking for … Second, …"). With the rule text in the prompt, E4B writes more formally, and it lists only some citations (82%).

**Post-hoc check, no GPU:** a "Rules:" line appended by code to the plain notes, from the card's check parts and the fixed element-to-rule map, keeps the plain notes' 70.0% pass rate with complete citations by construction. One caveat: the line lists all the card's check parts, including any the note leaves out. It should be labeled "Rules for the parts to check", or filtered to the parts the note names.

### Verdict

- **H1 held:** under the corrected judge, 1.9% of grounded rule claims are flagged, under the 5% bar. Both flagged claims are instructions, so there are no real misstatements. exp88's 16% was a judge artifact.
- **H2 failed:** moving the citations to the end made notes much harder to read (pass 9.2%) and less complete (82% coverage).

**Design conclusion:** citations don't have to come from the model. The checked parts and their governing rules are known before the note is written, so the model should write the plain note (best readability) and the system should add the rule line. The rule text stays available to the reviewer through the citation. That takes model-written rule claims out of the note entirely, and with them the main risk.

### Next steps

1. Add the system-appended rule line to the flag-card pipeline, filtered to the parts the note names.
2. Run the reviewer A/B on cited vs uncited notes.
