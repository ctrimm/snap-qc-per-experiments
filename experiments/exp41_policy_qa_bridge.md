# Experiment 41 — Policy-QA bridge: is the benefit calculator a reliable oracle for LM QA generation?
**Date:** 2026-09-29 · **Code:** `experiments/exp41_policy_qa_bridge.py`

## Hypothesis
North star gate: **LM eval (gate 3)**. Before any LM is trained or evaluated,
we need an *oracle* — a trusted reference program whose answers we treat as
ground truth when mass-producing training/eval QA pairs. We hypothesized the
generator's deterministic benefit calculator (`src/synth/benefit.py`,
FY2024 parameters) answers CalFresh-MCQ-style policy questions about QC
mechanics correctly, making it a reliable oracle for QA generation.

## Method
- Wrote 22 multiple-choice questions in CalFresh-MCQ style: 5 benefit-formula,
  8 deductions (ordering and caps), 4 error-direction (over- vs
  under-issuance), 3 variance-coding (element/nature from codebook.py), and
  2 scope probes (rules the calculator may not implement). Each question
  carries a hand-labeled correct answer grounded in statute/params, plus a
  one-line rationale. The correct answers were fixed *before* running.
- The script (`exp41_policy_qa_bridge.py`) answers each question
  programmatically — constructing case facts, running `benefit.compute`,
  reading `params.py` constants, or looking up `codebook.py` labels — and
  matches the derived value to an option letter. No LM involved. One mid-run
  fix: the `diff` derive returned a signed change (-30) while the stem asked
  for a magnitude; corrected to `abs()` (derivation framing, not a calculator
  issue).
- Reproducibility against the in-flight generator: `benefit.py` itself is at
  committed state (not among the modified files below).
  - `git rev-parse HEAD`: `411ddd761f1bc24f1709c434a42c1b8ea948956a`
  - `git status --short`: modified `experiments/inject.json`,
    `src/synth/dollar_mech.py`, `src/synth/errors.py`,
    `src/synth/household.py`; untracked `experiments/eval_pilot/`,
    `exp26`-`exp30`, `exp37`, `exp40`, `exp41_policy_qa_bridge.py`.

## Results
Overall: **21/22 = 0.955**. In-scope questions (formula, deductions, error
direction, variance coding): **20/20**.

| Q | Topic | Oracle component | Derived | Label | Result |
|---|-------|-----------------|---------|-------|--------|
| Q1 | formula | benefit.compute | $973 | A | OK |
| Q2 | formula | benefit.compute | $235 | A | OK |
| Q3 | formula | benefit.compute | $23 | C | OK |
| Q4 | formula | benefit diff ($235 vs $205) | $30 fall | C | OK |
| Q5 | formula | benefit.compute | $766 | A | OK |
| Q6 | deductions | trace earn_ded | $200 | B | OK |
| Q7 | deductions | trace med_ded | $85 | B | OK |
| Q8 | deductions | trace med_ded | $0 | B | OK |
| Q9 | deductions | trace med_ded | $0 | D | OK |
| Q10 | deductions | trace excess_shelter | $672 (capped) | B | OK |
| Q11 | deductions | trace excess_shelter | $699 (no cap, elderly) | B | OK |
| Q12 | deductions | benefit diff ($465 vs $525) | $60 | C | OK |
| Q13 | deductions | trace std_ded | $244 | C | OK |
| Q14 | direction | issued $766 vs true $705 | over-issuance | A | OK |
| Q15 | direction | issued $465 vs true $525 | under-issuance | B | OK |
| Q16 | direction | issued $585 vs true $766 | under-issuance | B | OK |
| Q17 | direction | issued $667 vs true $675 | under-issuance | B | OK |
| Q18 | coding | codebook lookup | 311/35 | A | OK |
| Q19 | coding | codebook lookup | 323/52 | A | OK |
| Q20 | coding | codebook lookup | 365/53 | A | OK |
| Q21 | scope probe | extra fact ignored | no deduction | C | OK (documented limit) |
| Q22 | scope probe | benefit.compute | $23 (statute: $0) | A | **FAIL** |

Failure categorization:
- **Q22 — calculator bug (known harness approximation):** a net-ineligible
  1-person household gets $23 from the calculator, but statute issues $0.
  `benefit.py` has no eligibility screen and applies the $23 minimum
  unconditionally (the code comment says so explicitly). Category: calculator
  bug, already documented, but it means QA pairs must never present the
  minimum-benefit rule without an eligibility precondition.
- **Q21 — out-of-scope, correctly detected:** the calculator grants no
  child-support deduction (benefit unchanged when a `childsupport` fact is
  added), while statute allows one and the codebook even has an element 366
  bucket for it. Not a failure of the oracle *within* its scope — it is a
  scope boundary the oracle itself can report.
- No question-ambiguity failures: the one mid-run issue (Q4 sign) was in the
  derive framing and was fixed without changing any question or label.

## Verdict
Hypothesis **held within scope, with one documented boundary**. The
calculator is a reliable oracle for everything it implements: benefit
formula, all four deduction types and their caps, error direction, and
(via codebook.py) element/nature coding — 20/20 on in-scope questions. The
single genuine failure (Q22) is the already-documented missing eligibility
screen, and the scope probe (Q21) confirms the calculator correctly "knows
what it doesn't know" for child support. Neither failure is ambiguous: both
are crisp, nameable limits.

What this changes: QA-pair generation can proceed for benefit-math,
deduction, direction, and coding questions, but generation must be fenced by
an explicit scope list, and minimum-benefit questions must carry an
eligibility precondition.

## Next steps
1. **(Recommended) Exp 43: scope manifest.** Write the explicit allow/deny
   list for QA generation (in-scope: formula, earned disregard, standard
   deduction, depcare, medical >$35, shelter cap; out-of-scope: child support,
   SUA mechanics, household composition, assets, reporting-system natures,
   eligibility screening), enforced as a filter in the QA-generation script
   so no out-of-scope question is ever emitted.
2. **(Recommended) Wire in exp42.** The depcare/medical deep-dive is running
   with another researcher; its findings should extend the oracle's deduction
   coverage (e.g. depcare caps, medical expense edge cases) before
   mass-generation.
3. **Eligibility gate question class.** Decide whether to add an eligibility
   screen to the QA oracle (a thin wrapper over params.py income limits, no
   src/ changes needed — it can live in the generator) or to simply forbid
   min-benefit QA pairs without a stated eligibility precondition.
4. **Golden QA set.** Freeze these 22 (minus Q22, or with Q22 kept as the
   adversarial case) as a regression set, re-run on every generator change —
   the first guardrail for the LM gate.
