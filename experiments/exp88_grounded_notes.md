# Experiment 88 — rule-grounded flag-card notes

**Date:** 2026-10-11 · **Code:** `experiments/exp88_grounded_notes.py` (pre-registered in its docstring) · **Outputs:** `../snap-qc-data/derived/exp88/`

### Why

The flag-card notes (exp62–77) tell a reviewer where to look: shelter costs first, then earned income, and so on. They never say what the rule is. A reviewer acting on a note needs the governing rule, and a model that paraphrases rules can get them wrong (exp77's notes already misstated the odds). This tests the outcome the project actually cares about: whether attaching the governing rule text lets a small model cite the right rule for each check without misstating it.

### Method (pre-registered)

- **Cards:** all 327 v2 flag cards (Pennsylvania and New York, 2020–2024).
- **Element-to-rule mapping:** each check element maps to its federal rule.

| Element | Rule |
|---|---|
| Shelter | 7 CFR 273.9(d)(6)(ii) |
| Earned income | 273.9(b)(1) |
| Unearned income | 273.9(b)(2) |
| Utility allowance | 273.9(d)(6)(iii) |
| Medical | 273.9(d)(3) |
| Household size | 273.1(a) |
| Dependent care | 273.9(d)(4) |
| Child support | 273.9(d)(5) |
| Benefit math | 273.10(e)(1) |

- **Excerpts:** taken from state-policy-docs, dated to the case year (2024-01-01 at the earliest, since the corpus holds CFR versions from 2024 on).
- **Writer:** stock Gemma 4 E4B, two arms.
  - **Plain:** exp62's prompt.
  - **Grounded:** the same prompt plus the excerpts and an instruction to cite each rule.
- **Judge:** Gemma 4 31B lists each rule claim in a note as supported, unsupported or contradicted by the excerpts.
- **Automatic scoring:** citation coverage, citations not supplied in the prompt, and exp62's frozen checks (faithful to the card, leads with the first check, length, reading level).

Hypotheses:
- **H1:** coverage above 80%, with unsupplied citations in under 5% of notes.
- **H2:** under 10% of rule claims are unsupported or contradicted.
- **H3:** grounding doesn't make notes less faithful to the card.

### Results

Pending (queued after exp87's E4B arms).
