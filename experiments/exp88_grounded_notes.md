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

All 327 cards, both arms, no errors. Every judgment parsed.

| E4B notes | Plain | Grounded |
|---|---|---|
| Citation coverage (checked elements whose rule is cited) | 0% | **97.3%** |
| Notes with a citation not supplied in the prompt | 0% | **0%** |
| Notes not faithful to the card (exp62 check: numbers or topics not on the card, blame words) | 0% | 0% |
| Notes leading with the first check | 99.7% | 100% |
| Notes passing all exp62 checks | 70.0% | 60.6% |
| Mean words | 52.7 | 69.2 |
| Rule claims per note (31B judge) | 0.02 | 0.63 |
| Rule claims judged unsupported or contradicted | 16.7% (of 6) | 16.1% (of 205) |

**Why fewer grounded notes pass the exp62 checks:** every failure in both arms is the reading-grade check (grade 9 or below): 129 grounded notes against 98 plain. The longer notes and the legal nouns that come with a citation raise the grade.

**The judge's "unsupported" claims, adjudicated by hand:** of the 33 claims in grounded notes judged unsupported (none contradicted), 32 are the card's own instructions recast as rules. For example, "shelter costs are reviewed via the current lease or mortgage statement" restates the card's "ask for", not a rule claim. The remaining one ("unearned income includes Social Security, SSI, unemployment and child support") is correct per the full text of 7 CFR 273.9(b)(2). The judge's 900-character excerpt simply stopped before that list. So no grounded note was found to misstate a rule.

### Verdict

- **H1 held:** 97.3% coverage, and no unsupplied (likely made-up) citations.
- **H2 failed as pre-registered:** 16.1% of claims were judged unsupported, against a bar of 10%. On inspection, the judge counted the card's instructions as rule claims, and none of the grounded notes misstates a rule. The judge prompt needs to exclude instructions taken from the card, and excerpts should not be truncated mid-list.
- **H3 held on faithfulness:** no grounded note added a number or topic not on the card. It cost readability, though: 31 more notes exceed reading grade 9.

Attaching the governing rule turns the notes into cited guidance with no invented citations. The remaining work is plainer wording around the citation.

### Next steps

1. **Fix the judge:** exclude instructions that come from the card, give it the full section text, and re-judge both arms. This is cheap, with no new notes needed.
2. **Readability:** put the citation at the end of the note ("Rules: 7 CFR 273.9(b)(2); 273.9(d)(6)(ii)") instead of inline, and measure whether the reading grade recovers.
3. **Reviewer study:** a cited vs uncited note packet, like exp77's, to see whether reviewers find the citations useful.
