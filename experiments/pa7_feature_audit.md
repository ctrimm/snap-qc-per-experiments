# PA7 — Feature sanity audit: the "defend this to a CIO" check

**Date:** 2026-09-29
**Status:** Complete — decision: **PASS** (see Verdict).
**Gate:** transfer
**Deliverables (new files only; no existing file modified):**
- `experiments/pa7_feature_audit.py` — retrain + two importance measures + leakage retrain
- `experiments/pa7_feature_audit.md` — this chronicle

## Hypothesis

PA2's transfer numbers (element acc 0.567, macroF1 0.208, shelter F1 0.741
on real held-out PA cases) only mean something if the model got there by
learning legitimate, certification-time process signals — the income levels,
deduction amounts, and household facts a caseworker actually sees — rather
than by keying on post-decision fields (the issued benefit) or
reviewer-coded artifacts that smuggle the label into the features. If the
top features are the same deduction/timing/income facts that PA3's anatomy
found driving real PA errors, the model learned the right thing; if the
only strong features are the decision outcome or reviewer codes, the POC
numbers are suspect.

## Method

Retrained PA2's best arm exactly per its reproduction recipe: PA-conditioned
synthetic (n=20000, seed 7, generated with `synth.pa_state`), sklearn
`HistGradientBoostingClassifier(random_state=0)` with no class_weight,
evaluated on the shared holdout (`experiments/pa2_holdout_idx.json`), element
task on the 349 held-out error cases. Retrain reproduced PA2 to four
decimals (acc 0.5673, macroF1 0.2077 vs reported 0.567/0.208) — the same
model is being audited.

Feature importance, two independent measures on the same fitted model:
- **GBM gain:** sum of per-node split gains across every tree of every
  iteration, normalized to shares. What the model itself leaned on.
- **Permutation importance:** 20 repeats on the holdout; drop in accuracy
  and in macroF1 when each feature is shuffled. What the model's score
  actually depends on. (Note: with correlated features this understates any
  single feature, since its signal survives in its correlates.)

Leakage audit: every v1 feature traced to its QC field and classified as
known-at-certification or post-decision/reviewer-coded. Anything touching
AMTERR, RAWBEN, FSBEN, STATUS, or the ELEMENT/NATURE/CAUSE label arrays is
flagged; then the model is retrained with flagged features removed and the
performance delta reported. Microdata read-only throughout; synthetic
regenerated fresh for this run (not copied into the repo).

## Results

### 1. Retrain reproduces PA2

| arm | acc | macroF1 |
|---|---|---|
| b) PA synth + GBM no-cw (PA2 reported) | 0.567 | 0.208 |
| b) retrained here | 0.5673 | 0.2077 |
| b) without leakage features (corrected) | 0.5587 | 0.2001 |

### 2. Top features, plain-language (9 features total in v1 — there is no top 20)

GBM gain share:

| rank | feature | gain share | what it is |
|---|---|---|---|
| 1 | shelter | 0.230 | shelter deduction amount (rent + utilities/SUA) |
| 2 | earned | 0.224 | monthly wages/salary on the case budget |
| 3 | unearned | 0.214 | monthly SSI, Social Security, VA, other unearned income |
| 4 | issued_benefit | 0.164 | benefit amount actually issued (RAWBEN) |
| 5 | depcare | 0.050 | dependent care deduction claimed |
| 6 | medical_exp | 0.045 | medical expense deduction (elderly/disabled members) |
| 7 | senior_disabled | 0.042 | an elderly or disabled person is in the household |
| 8 | hh_size | 0.020 | number of people on the case |
| 9 | sua | 0.012 | household receives the standard utility allowance |

Permutation importance on the holdout (drop when shuffled; dAcc / dF1macro):

| rank (by dAcc) | feature | dAcc | dF1macro |
|---|---|---|---|
| 1 | earned | +0.182 | +0.080 |
| 2 | unearned | +0.149 | +0.054 |
| 3 | shelter | +0.052 | +0.023 |
| 4 | issued_benefit | +0.016 | +0.014 |
| 5 | hh_size | +0.012 | +0.020 |
| 6 | medical_exp | +0.006 | +0.002 |
| 7 | senior_disabled | +0.003 | +0.018 |
| 8 | depcare | +0.002 | +0.028 |
| 9 | sua | +0.001 | +0.003 |

The two measures agree on the story with one ordering flip: gain puts
shelter first, permutation puts earned/unearned first. That is expected —
the issued benefit is a near-deterministic function of income, shelter, and
deductions, so the model spreads its splits across the correlated inputs
(high gain each) while shuffling any single one leaves the others carrying
the signal (low permutation drop). Neither measure puts any deduction,
household, or timing flag in the suspicious column.

### 3. Feature-by-feature classification, cross-checked against PA3

- **shelter — plausible, and the strongest agreement with PA3.** PA3: shelter
  deduction is 45.2% of PA errors (1.45x national); the four deduction-
  construction natures (52/53/56/57) all run 1.7–1.8x; wrongly-omitted
  shelter deductions run 2.3x. The model leaning hardest on the shelter
  deduction amount is the model learning PA's single most distinctive real
  pattern.
- **earned — plausible.** PA3: wages are 19.4% of PA errors; newly-employed
  wage errors 1.51x with the largest median dollars in PA's mix ($258);
  paycheck-timing errors (nature 97 on earned) are 9.9% of errors. Income
  volatility is the other half of the process story.
- **unearned — plausible.** PA3: unearned is 16.7% of PA errors; SSI/RSDI
  mis-budgeting (known-but-omitted SSI 1.46x, lower-than-budgeted 1.38x).
  Ordinary benefit-adjustment volatility, not a reviewer artifact.
- **issued_benefit — SUSPICIOUS (post-decision).** See leakage audit below.
- **depcare / medical_exp — plausible.** PA3: medical is 1.24x national with
  wrongly-included medical deductions at 1.93x; both are deduction-
  construction inputs, exactly where PA3 says PA's errors live.
- **senior_disabled — plausible.** It gates the medical deduction and the
  excess-medical rules — a household-composition fact with a real mechanism.
- **hh_size — plausible.** Household size sets the allotment and several
  deduction caps; composition facts are legitimate inputs.
- **sua — plausible, negligible.** Whether the household gets the standard
  utility allowance is part of the shelter math. Two disclosures: (1) SUA1
  carries reviewer consistency edits ("some values have been edited to
  obtain consistency with UTIL", FY2024 Tech Doc), a mild reviewer touch on
  an *input* field; (2) it has the lowest importance under both measures, so
  it cannot be driving anything.

Cross-check summary: the important features point at the same
deduction-construction and income-volatility patterns PA3 found in real PA
data. The model ignores what PA3 says is ignorable — there is no
computation-error signal available in v1 (no arithmetic fields), consistent
with PA3's finding that PA's benefit engine is clean (nature 75 at 0.12x).
Agreement is strong evidence the model learned the right thing.

### 4. Explicit leakage audit

Provenance of every v1 feature:

| feature | QC field | known at certification? |
|---|---|---|
| hh_size | CERTHHSZ | yes |
| earned | FSEARN | yes |
| unearned | FSUNEARN | yes |
| shelter | SHELDED | yes |
| sua | SUA1 | yes (with the reviewer-consistency-edit caveat above) |
| medical_exp | FSMEDEXP | yes |
| depcare | FSDEPDED | yes |
| senior_disabled | FSNELDER / FSNDIS | yes |
| issued_benefit | RAWBEN | **NO — the benefit actually issued is the decision outcome** |

Labels: STATUS is used only as the *finding* label (not a feature of the
element model); ELEMENT1 is the element *label*; AMTERR and FSBEN are not
used anywhere. No feature touches the ELEMENT/NATURE/CAUSE arrays.

**Exactly one leakage feature exists: issued_benefit (RAWBEN).** It is the
caseworker's decision outcome, not a certification-time input. Retraining
without it: acc 0.5587 vs 0.5673 (delta -0.0086), macroF1 0.2001 vs 0.2077
(delta -0.0076). The clean arm's gain shares concentrate on the same
legitimate inputs (shelter 0.274, earned 0.256, unearned 0.255, depcare
0.057, medical 0.052, senior/disabled 0.048, hh_size 0.045, sua 0.014).

Plain statement: the leakage is real but nearly immaterial. issued_benefit
is redundant — it is a near-deterministic function of the income and
deduction inputs — so removing it barely moves the numbers. The corrected,
leakage-free figures are acc 0.559 / macroF1 0.200, essentially the same POC
story as reported. The v1 feature set should drop issued_benefit going
forward; nothing else changes.

## Verdict

**PASS — the model keys on legitimate process signals and is free of
material leakage.** The two importance measures independently put the
shelter deduction amount, earned income, and unearned income on top — the
same deduction-construction and income-volatility patterns PA3 found in real
PA microdata (shelter 1.45x, deduction natures 1.7–1.8x, newly-employed
wages 1.51x). The audit found exactly one post-decision feature, the issued
benefit; removing it changes accuracy by -0.009 and macroF1 by -0.008 —
the POC transfer numbers stand with the corrected figures acc 0.559 /
macroF1 0.200. The model is not cheating. Recommendation: carry the
8-feature (no issued_benefit) set forward as the clean v1.

### Defend-to-a-CIO paragraph

The model predicts which part of a SNAP case is most likely to be wrong
using only the facts a caseworker already has when the case is certified:
household size, wages, other income like Social Security, the rent and
utility costs claimed, and the medical and child-care deductions claimed.
That is the whole input — no reviewer notes, no knowledge of the outcome,
nothing a worker would not see on the application. It leans hardest on the
shelter deduction and income amounts, which is exactly where Pennsylvania's
real errors cluster in five years of federal review data: wrongly included
or omitted shelter deductions run up to twice the national rate, while PA's
benefit math itself is nearly error-free. We explicitly tested whether the
model was cheating by sneaking in the final benefit decision or any review
codes; we found one such field, removed it, and the results barely moved
(less than one percentage point), because the legitimate inputs already
carry the signal. So the model's accuracy comes from learning PA's real
error patterns — messy deduction paperwork and paycheck timing — not from
peeking at the answer.

## Next steps

- Adopt the 8-feature set (drop issued_benefit) as the clean v1 for all
  future PA-track training; rerun the national arm without issued_benefit to
  confirm the PA-vs-national gap that drove PA2's PASS verdict is unchanged.
- PA4's P(error) work should use the clean feature set from the start.
- No new generator mechanics needed: the current v1 features already cover
  PA3's top patterns; the macroF1 tail gap (medical/sua) is a mechanics
  question for the generator, not a feature-leakage question.
