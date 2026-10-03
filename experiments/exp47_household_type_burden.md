# Exp47 — household-type review burden of the PA/NY dollar rankers

**Date:** 2026-10-03
**Status:** Complete — decision: **MIXED/INFORMATIVE** (no gate; fairness audit), see Verdict.
**Code:** `experiments/exp47_household_type_burden.py`
**Deliverables:**
- `experiments/exp47_household_type_burden.py` — taxonomy + ranker reproduction + per-type burden tables
- `experiments/exp47_household_type_burden.md` — this chronicle
- Raw tables: `/tmp/exp47out/exp47_results.json` (scratch, not committed)

## Hypothesis

The pilot whitepapers and blog draft show the dollar rankers (PA two-part,
NY direct expected-dollar) recover ~1.5x the dollars of random review — but
dollars concentrate in income errors, so the ranked queue tilts toward
households with earnings. The open fairness question a peer reviewer will
ask: does the ranker over-review certain household types relative to their
actual error risk, or is the tilt proportional to where errors and dollars
are? Expected shape if proportional: review_rate_t / base_error_rate_t
roughly constant across types. Expected shape if not: systematic
over/under-review of specific types.

## Method

**Household taxonomy** (documented from the FY2024 tech-doc codebook;
priority elderly > disabled > composition so multigenerational units count
in the elder/disabled type):
- `elderly`: FSELDER=1 (elderly individual in unit)
- `disabled_nonelderly`: FSDIS=1, FSELDER=0
- `single_parent`: COMPOSITION in (2,3,6) — children + one adult
- `married_with_kids`: COMPOSITION=4
- `multiadult_with_kids`: COMPOSITION=5
- `child_only`: COMPOSITION=1
- `childless_adult`: COMPOSITION=0
- Types with <25 holdout rows merge into `other_small` (PA: child_only n<25;
  NY: child_only n=17 + multiadult_with_kids n=16).

**Holdouts:** the shared `experiments/pa2_holdout_idx.json` (817) and
`experiments/ny2_holdout_idx.json` (815). Not rebuilt.

**Rankers reproduced exactly from the published recipes** (pooled seed-7
synthetic, same as the published runs):
- PA: pa5 winner (b) two-part — `HistGradientBoostingClassifier` on PA-synth,
  isotonic calibration on the real PA train split, ×
  `HistGradientBoostingRegressor` (log1p) on PA-synth error cases; V1 features.
- NY: ny5 winner (c) direct — `HistGradientBoostingRegressor` (log1p) on all
  NY-synth cases; CLEAN8 features.

**Reproduction check:** NY matches the published NY5 numbers exactly
(top-20%: $6,958 / 30.4%). PA shifts: top-20% $6,074 → **$5,483** (28.4%;
lift 1.42x vs published 1.58x). Cause: the exp44 fitted household-size mix
was adopted into `src/synth/household.py` *after* PA5 ran and *before* NY5
ran, so PA5's published numbers used the legacy mix. The fairness analysis
below uses current defaults (the ranker as it exists today); the qualitative
picture — two-part beats random by a real margin — is unchanged.

**Metrics per type** at top-10%/20%/30%: n, share of holdout, base error
rate, review rate (share of the type's cases selected), precision within the
type's reviewed cases, error dollars recovered per type, share of the type's
own error dollars recovered, random-baseline expectation. Decision metric:
`review_rate_t / base_error_rate_t` per type + CV across types; random
baseline gives `(k/n)/base_error_rate_t` for comparison. Plus a marginal
check: mean predicted $ of selected vs unselected cases *within* each type
(tests whether the ranker misallocates even on its own dollar objective).

## Results

### PA top-20% (k=163; overall $5,483 / 28.4%, precision 0.491)

| type | n | base_err | rev_rate | prec | rec_$ | ratio rev/base |
|---|---|---|---|---|---|---|
| elderly | 307 | 0.476 | 0.104 | 0.656 | 1,201 | **0.219** |
| disabled_nonelderly | 168 | 0.542 | 0.179 | 0.700 | 1,360 | **0.330** |
| single_parent | 122 | 0.393 | 0.393 | 0.396 | 1,198 | 1.000 |
| married_with_kids | 30 | 0.500 | 0.267 | 0.625 | 352 | 0.533 |
| multiadult_with_kids | 33 | 0.697 | 0.364 | 0.750 | 709 | 0.522 |
| childless_adult | 148 | 0.149 | 0.209 | 0.097 | 380 | **1.409** |
| other_small | 9 | 0.444 | 0.222 | 1.000 | 283 | 0.500 |

Proportionality CV = 0.598 (range 0.219–1.409). Random baseline ratios for
comparison: elderly 0.419, disabled 0.368, childless 1.339.

### NY top-20% (k=163; overall $6,958 / 30.4%, precision 0.466)

| type | n | base_err | rev_rate | prec | rec_$ | ratio rev/base |
|---|---|---|---|---|---|---|
| elderly | 341 | 0.340 | 0.114 | 0.436 | 1,609 | **0.336** |
| disabled_nonelderly | 155 | 0.419 | 0.148 | 0.652 | 923 | **0.354** |
| single_parent | 95 | 0.526 | 0.274 | 0.731 | 2,531 | 0.520 |
| married_with_kids | 29 | 0.345 | 0.172 | 0.200 | 173 | 0.500 |
| childless_adult | 162 | 0.235 | 0.340 | 0.273 | 1,062 | **1.447** |
| other_small | 33 | 0.606 | 0.455 | 0.600 | 660 | 0.750 |

Proportionality CV = 0.585 (range 0.336–1.447). Same shape as PA at all
three budgets (top-10% CV 1.126, top-30% CV 0.477 — the tilt is strongest
at the top of the list).

### The uncomfortable finding, stated plainly

The tilt is **not** proportional to error risk — in either state. Elderly
households have the highest error rates among large types (PA 0.476, NY
0.340) and disabled non-elderly higher still (PA 0.542, NY 0.419), yet the
ranker reviews them at the *lowest* rates relative to their risk (ratios
0.22–0.35). Childless adults have the *lowest* error rates (PA 0.149, NY
0.235) and get the *highest* relative review rates (ratios 1.41–1.45) —
with poor precision when reviewed (PA 0.097, NY 0.273). For PA's elderly,
the ranker's ratio (0.219) is worse than random allocation would give
(0.419): relative to error risk, the dollar ranker treats the highest-risk
group worse than a lottery.

**Mechanism:** dollars concentrate in income errors; elderly/disabled
errors are frequent but small-dollar (shelter/medical/SUA timing — the same
tail NY2 flagged). A dollars-per-hour objective rationally deprioritizes
them. This is not a detection failure: precision within reviewed
elderly/disabled cases is high (PA 0.62–0.73, NY 0.44–0.65) — when reviewed,
errors are found. It is purely an allocation effect.

**Exonerating check (marginal):** within every type, selected cases carry
far higher predicted $ than unselected cases of the same type (PA: 2–3x;
NY: 5–14x). The ranker is not misallocating on its own objective — it is
allocating exactly as a dollar-maximizer should. The tilt is a property of
the objective, not a bug in the ranking.

**Why it matters for the pilot:** if the pilot's goal includes finding
underpayments owed to vulnerable households — elderly/disabled carry high
under-issuance exposure via medical deductions and fixed incomes — the
dollar ranker works against that goal while optimizing the headline $/hr.
The whitepapers' over/under split (70/30) is reported in aggregate; this
experiment shows the under-review burden falls disproportionately on the
types most likely to be underpaid.

## Verdict

**MIXED/INFORMATIVE — the ranker is dollar-efficient and risk-regressive
at the same time.** Proportional to expected dollars: yes, the allocation
is efficient (marginal check passes in every type, both states). Proportional
to error risk: no — elderly and disabled households, the highest-error-rate
groups, are systematically under-reviewed relative to their risk, and
childless adults systematically over-reviewed, in both states and at all
three budgets. The blog draft's earnings-tilt paragraph should cite this
experiment rather than promising it as future work.

## Next steps

- **For the pilot:** consider type-aware review budgets (reserve a slice of
  reviews per type proportional to base error rate), a blended objective
  (dollars + error-rate equity), or an under-issuance-weighted arm targeted
  at elderly/disabled types. Evaluate each on both $/hr and per-type
  review-rate parity.
- **For the post:** replace the "next one on the list" paragraph with these
  numbers; the uncomfortable finding belongs in the piece, not under it.
- Revisit after the FY2025 microdata lands (watch: `fy2025-qc-microdata-watch`):
  the type mixes and the elderly/disabled error-rate gaps may have moved.
- Optional: per-type over/under split (are the missed elderly errors
  disproportionately under-issuances? the pilot-relevant question).
