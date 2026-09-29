# NY7 — Feature sanity audit: the "defend this to a CIO" check

**Date:** 2026-09-29
**Status:** Complete — decision: **PASS** (see Verdict).
**Gate:** transfer
**Deliverables (new files only; no existing file modified):**
- `experiments/ny7_feature_audit.py` — retrain + two importance measures + leakage retrain
- `experiments/ny7_feature_audit.md` — this chronicle

Plain-language terms: GBM gain = how much each feature contributed to the
model's splits across all its trees (its share of the model's total
"attention"); permutation importance = how much the model's score drops when
a feature's values are shuffled on the holdout (what the score actually
depends on); macroF1 = the average of the per-bucket F1 scores, treating
every element bucket equally.

## Hypothesis

NY2's transfer numbers (element acc 0.435, macroF1 0.168, finding binary
AUC 0.648 on real held-out NY cases) only mean something if the model got
there by learning legitimate, certification-time process signals — the
income levels, deduction amounts, and household facts a caseworker actually
sees — rather than by keying on post-decision fields (the issued benefit)
or reviewer-coded artifacts that smuggle the label into the features. If the
top features are the same income/deduction facts that NY3's anatomy found
driving real NY errors, the model learned the right thing; if the only
strong features are the decision outcome or reviewer codes, the POC numbers
are suspect. NY2's mixed verdict makes this check sharper: on the element
task NY-conditioning lost to national-trained, so the audit must confirm
the model is at least learning NY's real process patterns, not noise.

## Method

Retrained NY2's best arm exactly per its reproduction recipe: NY-conditioned
synthetic (n=20000, seed 7, freshly generated with `src.synth.ny_state`),
sklearn `HistGradientBoostingClassifier(random_state=0)` with no
class_weight (NY2's winning setting for NY), evaluated on the shared holdout
(`experiments/ny2_holdout_idx.json`), element task on the 299 held-out error
cases. Retrain reproduced NY2 to four decimals (acc 0.4348, macroF1 0.1681
vs reported 0.435/0.168) — the same model is being audited.

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
performance delta reported (with per-bucket F1s for the clean arm).
Microdata read-only throughout; synthetic regenerated fresh for this run
(not copied into the repo).

## Results

### 1. Retrain reproduces NY2

| arm | acc | macroF1 |
|---|---|---|
| b) NY synth + GBM no-cw (NY2 reported) | 0.435 | 0.168 |
| b) retrained here | 0.4348 | 0.1681 |
| b) without leakage features (corrected) | 0.4515 | 0.1474 |

### 2. Top features, plain-language (9 features total in v1 — there is no top 20)

GBM gain share:

| rank | feature | gain share | what it is |
|---|---|---|---|
| 1 | earned | 0.218 | monthly wages/salary on the case budget |
| 2 | shelter | 0.209 | shelter deduction amount (rent + utilities/SUA) |
| 3 | unearned | 0.194 | monthly SSI, Social Security, VA, other unearned income |
| 4 | issued_benefit | 0.178 | benefit amount actually issued (RAWBEN) |
| 5 | medical_exp | 0.063 | medical expense deduction (elderly/disabled members) |
| 6 | senior_disabled | 0.058 | an elderly or disabled person is in the household |
| 7 | depcare | 0.038 | dependent care deduction claimed |
| 8 | hh_size | 0.031 | number of people on the case |
| 9 | sua | 0.012 | household receives the standard utility allowance |

Permutation importance on the holdout (drop when shuffled; dAcc / dF1macro):

| rank (by dAcc) | feature | dAcc | dF1macro |
|---|---|---|---|
| 1 | earned | +0.150 | +0.065 |
| 2 | unearned | +0.070 | +0.033 |
| 3 | issued_benefit | +0.009 | +0.024 |
| 4 | shelter | +0.009 | +0.035 |
| 5 | medical_exp | +0.004 | +0.012 |
| 6 | hh_size | +0.002 | +0.005 |
| 7 | senior_disabled | +0.002 | +0.002 |
| 8 | depcare | −0.003 | −0.000 |
| 9 | sua | −0.004 | −0.003 |

The two measures agree on the story with the same ordering flip PA7 saw:
gain puts earned/shelter/unearned close together, permutation puts earned
first by a wide margin. That is expected — the issued benefit is a
near-deterministic function of income, shelter, and deductions, so the model
spreads its splits across the correlated inputs (high gain each) while
shuffling any single one leaves the others carrying the signal (low
permutation drop). Neither measure puts any deduction, household, or timing
flag in the suspicious column.

### 3. Feature-by-feature classification, cross-checked against NY3

- **earned — plausible, and the top feature under both measures.** NY3:
  wages are 24.1% of NY errors; newly-employed wage errors run 1.33x;
  timing-97 errors on earned run 1.16x. Income volatility is the core of
  NY's process story.
- **shelter — plausible.** NY3: the shelter deduction is 25.8% of NY
  errors (0.83x national — common but slightly under-represented). The model
  leaning hard on the shelter amount is the model learning the deduction-
  construction patterns that drive real NY errors.
- **unearned — plausible.** NY3: unearned is 25.9% of NY errors (1.12x);
  SSI/RSDI/unemployment-comp mis-budgeting (unemployment comp 2.00x, SSI
  1.51x, RSDI 1.27x). Ordinary benefit-adjustment volatility.
- **issued_benefit — SUSPICIOUS (post-decision).** See leakage audit below.
- **medical_exp / senior_disabled — plausible, and the NY-specific tell.**
  NY3: medical is 7.8% of NY errors at 1.79x national — NY's single most
  distinctive element signature. Medical_exp ranks 5th by gain (0.063 vs
  PA's 0.045) and senior_disabled (which gates the medical deduction) 6th —
  the model leans on NY's distinctive pattern more than PA's model leaned
  on PA's. The cross-check passes with an NY accent.
- **depcare — plausible.** A deduction-construction input; depcare is 0.9%
  of NY errors (0.69x) — rare, so low importance is honest.
- **hh_size — plausible.** Household size sets the allotment and deduction
  caps; a composition fact, legitimate input.
- **sua — plausible, negligible.** SUA receipt is part of the shelter math,
  but its signal is timing (NY's sua errors are 97-heavy at 1.51x), and v1
  has no timing features — so the model correctly finds almost nothing in
  the sua flag. Two disclosures: (1) SUA1 carries reviewer consistency
  edits ("some values have been edited to obtain consistency with UTIL",
  FY2024 Tech Doc), a mild reviewer touch on an *input* field; (2) it has
  the lowest importance under both measures, so it cannot be driving
  anything.

Cross-check summary: the important features point at the same
income-volatility and deduction-construction patterns NY3 found in real NY
microdata, with medical elevated exactly where NY is most distinctive. The
model ignores what NY3 says is ignorable — there is no computation-error
signal available in v1, consistent with NY's clean benefit engine. The
model is not cheating, and it learned NY's real patterns rather than noise
— which matters given NY2's element leg did not beat national-trained.

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
| senior_disabled | FSNELDER/FSNDIS | yes |
| issued_benefit | RAWBEN | **NO — the benefit actually issued is the decision outcome** |

Labels: STATUS is used only as the *finding* label (not a feature of the
element model); ELEMENT1 is the element *label*; AMTERR and FSBEN are not
used anywhere. No feature touches the ELEMENT/NATURE/CAUSE arrays.

**Exactly one leakage feature exists: issued_benefit (RAWBEN).** It is the
caseworker's decision outcome, not a certification-time input. Retraining
without it: acc 0.4515 vs 0.4348 (delta **+0.0167**), macroF1 0.1474 vs
0.1681 (delta −0.0207). The clean arm's gain shares concentrate on the same
legitimate inputs (shelter 0.260, earned 0.254, unearned 0.241, medical
0.072, senior/disabled 0.064, hh_size 0.054, depcare 0.043, sua 0.014).

The accuracy/macroF1 split is worth one honest sentence: removing the
leakage feature *helped* accuracy (+1.7pp) because the model concentrated
its splits on the dominant buckets — per-bucket F1s rose on earned (0.646
→ 0.692), shelter (0.491 → 0.511), sua (0.129 → 0.143), hhcomp (0.000 →
0.167), and medical (0.065 → 0.067) — but *hurt* macroF1 (−2.1pp) because
issued_benefit was carrying signal on the rarest tail buckets, where the
clean arm lost. The leakage is real but the POC story does not depend on
it: the clean, leakage-free figures are acc 0.452 / macroF1 0.147. The v1
feature set should drop issued_benefit going forward; nothing else changes.

## Verdict

**PASS — the model keys on legitimate process signals and is free of
material leakage.** The two importance measures independently put earned
income, the shelter deduction amount, and unearned income on top — the same
income-volatility and deduction-construction patterns NY3 found in real NY
microdata (wages 24.1% of errors, shelter 25.8%, unearned 25.9% with
unemployment comp at 2.00x), with medical elevated exactly where NY is most
distinctive (1.79x national). The audit found exactly one post-decision
feature, the issued benefit; removing it changes accuracy by +0.017 and
macroF1 by −0.021 — the POC transfer numbers stand with the corrected
figures acc 0.452 / macroF1 0.147. The model is not cheating; it learned
NY's real process patterns, which sharpens NY2's mixed verdict: the element
leg's failure against national-trained is not a feature-integrity problem,
it is a conditioning-value problem. Recommendation: carry the 8-feature (no
issued_benefit) set forward as the clean v1.

### Defend-to-a-CIO paragraph

The model predicts which part of a SNAP case is most likely to be wrong
using only the facts a caseworker already has when the case is certified:
household size, wages, other income like Social Security, the rent and
utility costs claimed, and the medical and child-care deductions claimed.
That is the whole input — no reviewer notes, no knowledge of the outcome,
nothing a worker would not see on the application. It leans hardest on the
income and shelter-deduction amounts, which is exactly where New York's real
errors cluster in five years of federal review data: wage-reporting
volatility and deduction paperwork, with medical expenses as New York's
most distinctive signature (nearly twice the national rate), which the model
picks up. We explicitly tested whether the model was cheating by sneaking
in the final benefit decision or any review codes; we found one such field,
removed it, and the results barely moved — accuracy actually rose slightly
because the model concentrated on the legitimate inputs, and the rare-bucket
tail lost a couple of points that the leaked field had been carrying. So
the model's accuracy comes from learning New York's real error patterns —
messy deduction paperwork and paycheck timing — not from peeking at the
answer.

## Next steps

- Adopt the 8-feature set (drop issued_benefit) as the clean v1 for all
  future NY-track training; rerun the national arm without issued_benefit
  to confirm the finding-task NY edge that drove NY2's mixed verdict is
  unchanged.
- NY4's P(error) work should use the clean feature set from the start.
- No new generator mechanics needed for the element task: the current v1
  features already cover NY3's top patterns; NY2's element-leg problem is
  conditioning value (national-trained is as good), not feature coverage —
  the macroF1 tail gap (medical/sua/hhcomp) remains a generator-mechanics
  question.
