# Experiment NY8c: NY-filtered deviations as candidate engine misconfigurations

**Date:** 2026-09-29 · **Code:** `experiments/ny8c_ny_engine_cleanliness.py`

## Hypothesis

Tied to the north star (an instrument that detects eligibility-engine
misconfigurations in QC microdata): NY's error anatomy (NY3) is a timing-
heavy process-layer story, and the benefit-computation errors (nature 75 at
0.20x national) are near-absent. If NY's clean, no-error rows fit the
statutory schedule exactly, then NY's deviations are caseworker/data issues,
not engine misconfigurations — and the exp8b New England uncapped-shelter
pattern (NY was in exp8b's anomaly group of CT/ME/MA/NH/NY/RI) should be
tested inside NY specifically. This experiment runs the exp8b
parameter-fitting battery per fiscal year on NY alone, against the national
fleet and the statute. Materiality bar (from exp8b): a parameter deviation
only counts if it moves benefits by more than $1 for a non-trivial share of
cases.

## Method

Microdata: SNAP QC public-use files FY2020–2024, New York (STATE=36),
read-only. Two row sets per FY, using the exp8b cleaning rule: clean-engine
rows (STATUS=1, RAWBEN==FSBEN, SSI_CAP==0 to exclude NY's simplified-
reporting SSI cases, HOMEDED==1 for housed) and suggestive error rows
(STATUS in {2,3}, RAWBEN!=FSBEN, |AMTERR - (FSBEN-RAWBEN)| <= $1), with
recoupment and residual-analytics anomalies dropped.

The parameter set is exp8b's, fit per FY on NY clean-engine rows and on the
national fleet (Alaska, Hawaii, territories excluded): the 30%
benefit-reduction rate (ordinary least squares slope of BENMAX-RAWBEN on
RAWNET — ordinary least squares just means the straight line that best fits
the cloud of points), the rounding rule for 0.3 x net income (ceiling vs
round vs floor exactness), the 20% earned-income disregard, the minimum
benefit (modal value — the most common value — in the low-benefit cluster),
the standard deduction by household size (fitted from the net-income
identity: gross minus earnings minus deductions minus shelter minus net
should equal the standard deduction), maximum allotments (median benefit at
zero net income), shelter-cap behavior (share of non-elderly cases at or
above the cap), and the homeless deduction. Three tests: (a) the per-FY
NY-vs-fleet-vs-statute parameter table; (b) the exp8b New England
shelter-cap anomaly test inside NY (for non-elderly cases with RAWNET>0 and
SHELDED above the cap: does the recorded net income match the identity with
the shelter deduction capped, or uncapped?); (c) an output-side holdout:
predict RAWBEN = max(BENMAX - ceil(0.3 x RAWNET), minimum benefit for 1-2
person households) on NY clean-engine rows and measure exact-match share.
An FY2024 SUA spot-check (NY's published HCSUA: NYC $1,034 / Nassau-Suffolk
$962 / rest-of-state $854; utilities $408/$378/$346; telephone $31 — OTDA
Notice of Adoption eff 10/1/2024) rounds out the input side. Clean-engine
n per FY: 160 / 87 / 357 / 361 / 367 (fleet: 13,549 / 4,427 / 19,604 /
20,244 / 19,798). NY has 39-155 SSI_CAP!=0 simplified-reporting cases per
FY in the cleaned set (excluded from the deduction fits per the exp8b rule).

## Results

### (a) Parameter battery: NY matches statute everywhere

- **30% benefit-reduction rate:** NY fits at 0.3001/0.3000/0.3000 in
  FY2022-2024 (fleet 0.2990-0.2997); FY2021 interior n=24, too small for a
  slope. FY2020 fit at 0.2635 on n=38 — but this is a recording artifact,
  not an engine behavior: one clean-engine row had RAWNET recorded as the
  gross ($1,548, equal to RAWGROSS) while its benefit was computed from the
  true net ($460.4, exact match). Excluding that single row, the FY2020 NY
  slope is 0.3002. (See the recording-artefact section below.)
- **Rounding:** ceiling exact at 0.96-0.99 in FY2021-2024; FY2020 at 0.895
  on the same small, artifact-contaminated interior set (fleet 0.967).
- **20% earned-income disregard:** 0.2000 exactly in every FY, NY and fleet.
- **Minimum benefit:** $16/$20/$23/$23 fit with modal share 0.89-1.00
  (FY2021 n=9, below the fit threshold; fleet fits $19 as statute expects).
- **Standard deduction:** fits exactly wherever NY has n>=30 (e.g. size 1:
  $177 within-$1 share 0.941 in FY2022; $198 within-$1 0.865 in FY2024).
- **Maximum allotments:** exact wherever NY has n>=30 (sizes 1-2 in most
  years).
- **Shelter cap:** binds hard. NY non-elderly at-cap share 0.583-0.865
  (fleet 0.290-0.402); above-cap share 0.000 in FY2020 and FY2022-2024,
  0.167 in FY2021 (2 rows — neither uncapped-only, details in (b)). Elderly
  maxima ($1,383-$2,365) are legitimate — the cap does not apply to
  elderly/disabled households, which are ~45% of NY's clean-engine rows.
- **Homeless deduction:** zero NY homeless-deduction clean-engine rows in
  all five years (same as fleet); nothing to fit.

No NY-specific parameter deviation meets the materiality bar.

### (b) Shelter-cap anomaly test: NY is clean — cleaner than the fleet

Zero NY uncapped-only cases in all five fiscal years, on clean-engine rows
and on suggestive error rows alike. The only NY over-cap rows:

- FY2021 clean-engine: 2 over-cap rows (of 12 non-elderly shelter rows) —
  one capped-only, one neither (a net-identity residual, not the uncapped
  pattern).
- FY2022 suggestive error rows: 1 over-cap row — capped-only.

For context, the fleet shows 6-21 over-cap clean-engine rows per year with
1-2 uncapped-only cases per year, and the NE-six group (CT/ME/MA/NH/NY/RI)
contributes its own uncapped rows. NY — despite being in exp8b's anomaly
group — contributes none. NY's engine caps shelter deductions per statute.

### (c) Output-side holdout: the "engine-cleanliness %"

| FY | NY clean-engine n | Exact match | Within $1 | MAE | Fleet exact |
|---|---|---|---|---|---|
| 2020 | 158 | 94.30% | 96.20% | $7.37 | 98.54% |
| 2021 | 87 | 95.40% | 95.40% | $17.02 | 97.85% |
| 2022 | 357 | 97.76% | 98.32% | $4.08 | 97.89% |
| 2023 | 361 | 98.34% | 98.61% | $2.33 | 97.74% |
| 2024 | 367 | 97.55% | 97.82% | $4.81 | 97.44% |

NY's raw holdout trails the fleet in FY2020-2021, then matches it. The gap
is fully explained by a NY-specific recording artifact (below), not by the
engine: excluding rows where RAWNET was recorded equal to RAWGROSS while
the component fields imply a lower net, NY's exact-match becomes
98.03% / 97.65% / 98.03% / 98.34% / 98.08% — at fleet level every year. The
FY2021 remainder is two legitimate prorated initial-month rows
(RAWNET=0, RAWBEN<max), which the script already counts separately
(prorated share 0.023 — no NY deviation vs fleet 0.004-0.014).

### The RAWNET==RAWGROSS recording artifact (NY-specific)

In NY's clean-engine rows, a non-trivial slice has RAWNET recorded exactly
equal to RAWGROSS — i.e. net income recorded as if no deductions applied —
while the recorded benefit is computed from the correct, deduction-adjusted
net. Share of interior clean-engine rows (RAWNET>0) with the artifact:

| FY | NY | Fleet |
|---|---|---|
| 2020 | 10.0% (6 of 60) | 0.03% (2 of 6,355) |
| 2021 | 6.1% (2 of 33) | 0.05% |
| 2022 | 0.9% (1 of 109) | 0.05% |
| 2023 | 0.0% | 0.03% |
| 2024 | 2.4% (2 of 84) | 0.02% |

Fleet background is essentially zero; this is a NY recording quirk,
concentrated in FY2020-2021. It is a *file* issue, not an engine issue: for
five of the six FY2020 cases the recorded benefit equals the maximum
allotment (the COVID emergency-allotment signature — benefit brought to max
regardless of net), and for the sixth the benefit matches the net recomputed
from the components exactly ($629 from net $460.4 vs the recorded
$1,548 = gross). The engine's outputs are correct; the RAWNET *field* is
what is stale. Practical consequence: any analysis that regresses on NY's
recorded RAWNET in FY2020-2021 (including this battery's OLS slope and the
holdout) inherits the artifact — use the component-recomputed net for NY in
those years.

### Input-side spot checks

- FY2024 SHELDED is dominated by the $672 cap (129 of 367 clean-engine
  rows) and $0; NY's published SUA values ($1,034/$962/$854 HCSUA,
  $408/$378/$346 utilities) do not appear as standalone SHELDED masses
  because SHELDED bundles rent with utilities — expected, no deviation.
  Telephone $31 appears in 2.45% of rows (phone-only utility households).
- Proration: NY clean-engine rows contain 0-6 prorated-like cases per FY
  (share 0-1.6%) vs fleet 1.0-1.4% — no NY deviation.

## Verdict

Clean NY engine, with one NY-specific data artifact. The parameter battery
finds no NY misconfiguration: the 30% rate, ceiling rounding, 20% earned
disregard, minimum benefits, standard deductions, maximum allotments, and
shelter-cap behavior all match statute, and the exp8b uncapped-shelter
pattern is absent from NY — NY is cleaner than the fleet on that test. The
one FY2020 "deviation" (0.2635 rate slope) traces to a single recording-
artifact row, and the FY2020-2021 holdout gap traces to the NY-specific
RAWNET==RAWGROSS recording quirk (10% of interior clean rows in FY2020 vs
~0% fleet) plus COVID emergency allotments. Corrected for the artifact,
NY's output-side exact-match runs 97.7-98.3% — at fleet level, every year.

Attribution limit (from exp8b, unchanged): the public-use file identifies
states, not eligibility-system vendors, so engine attribution beyond the
state level is impossible from this data. Everything here is NY-program
behavior.

## Next steps

- **Recording-artifact follow-up (small):** the RAWNET==RAWGROSS quirk is
  NY-specific and FY2020-2021-concentrated. Worth checking whether it
  clusters in NYC vs rest-of-state (the file has no county field in
  public-use, so this may need the restricted file or a note to the
  QC-review documentation) — and whether it correlates with the emergency-
  allotment months.
- The FY2021 two-row over-cap clean-engine non-uncapped residuals are
  recording noise, not engine behavior; no follow-up needed.
- **Downstream:** NY3's timing-heavy process-layer story is now doubly
  supported — the engine is clean *and* benefit-computation errors are
  0.20x national. Copilot attention belongs on timing/change workflows,
  not on benefit-formula corrections.
- Methodological note carried forward: when a state's recorded net-income
  field disagrees with the component-recomputed net, the holdout and slope
  tests should run on the recomputed net — the recorded field can be the
  thing that is wrong.
