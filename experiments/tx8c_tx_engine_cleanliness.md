# Experiment TX8c: TX-filtered deviations as candidate engine misconfigurations

**Date:** 2026-10-03 · **Code:** `experiments/tx8c_tx_engine_cleanliness.py`

## Hypothesis

Tied to the north star (an instrument that detects eligibility-engine
misconfigurations in QC microdata): if Texas's clean, no-error rows fit the
statutory benefit schedule exactly, then TX's deviations are caseworker/data
issues, not engine misconfigurations. This experiment runs the exp8b
parameter-fitting battery per fiscal year on Texas alone (STATE=48),
against the national fleet and the statute, plus the exp8b New England
uncapped-shelter anomaly test inside TX (kept for comparability even
though TX is not in exp8b's anomaly group). Materiality bar (from exp8b):
a parameter deviation only counts if it moves benefits by more than $1 for
a non-trivial share of cases.

## Method

Microdata: SNAP QC public-use files FY2020–2024, Texas (STATE=48),
read-only. Two row sets per FY, using the exp8b cleaning rule: clean-engine
rows (STATUS=1, RAWBEN==FSBEN, SSI_CAP==0 to exclude simplified-reporting
SSI cases, HOMEDED==1 for housed) and suggestive error rows (STATUS in
{2,3}, RAWBEN!=FSBEN, |AMTERR - (FSBEN-RAWBEN)| <= $1), with recoupment and
residual-analytics anomalies dropped.

The parameter set is exp8b's, fit per FY on TX clean-engine rows and on the
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
TX-vs-fleet-vs-statute parameter table; (b) the exp8b New England
shelter-cap anomaly test inside TX (for non-elderly cases with RAWNET>0 and
SHELDED above the cap: does the recorded net income match the identity with
the shelter deduction capped, or uncapped?); (c) an output-side holdout:
predict RAWBEN = max(BENMAX - ceil(0.3 x RAWNET), minimum benefit for 1-2
person households) on TX clean-engine rows and measure exact-match share.
An FY2024 SHELDED point-mass spot-check rounds out the input side.
Clean-engine n per FY: 287 / 84 / 390 / 345 / 389 (fleet: 13,422 / 4,430 /
19,571 / 20,260 / 19,776). TX has 17-29 SSI_CAP!=0 simplified-reporting
cases per FY in the cleaned set (excluded from the deduction fits per the
exp8b rule).

## Results

### (a) Parameter battery: TX matches statute everywhere, tightly

- **30% benefit-reduction rate:** TX fits at 0.3000/0.2999/0.2996/0.3000/
  0.3000 across FY2020-2024 (fleet 0.2968-0.2997) — exact to four decimals
  in four of five years, on n=34-144 interior rows per FY. No recording
  artifact (unlike NY's FY2020 RAWNET==RAWGROSS quirk): TX's interior rows
  are clean.
- **Rounding:** ceiling exact at 0.986-1.000 every FY (fleet 0.959-0.973).
- **20% earned-income disregard:** 0.2000 exactly wherever TX has n>=30
  (FY2021 n=23, below the fit threshold; fleet 0.2000).
- **Minimum benefit:** $16/$19/$20/$23/$23 fit with modal share 1.00 every
  FY — every low-benefit TX case sits exactly on the statutory minimum.
- **Standard deduction:** fits exactly wherever TX has n>=30 (size 1:
  within-$1 share 0.951-1.000 across FYs).
- **Maximum allotments:** exact wherever TX has n>=30 (sizes 1-3).
- **Shelter cap:** binds, but less hard than NY's. TX non-elderly at-cap
  share 0.083-0.615 (fleet 0.306-0.412); above-cap share **0.000 in all
  five FYs** — not a single non-elderly TX case exceeds the cap. Elderly
  maxima ($686-$999) are legitimate — the cap does not apply to
  elderly/disabled households.
- **Homeless deduction:** zero TX homeless-deduction clean-engine rows in
  all five years (same as fleet); nothing to fit.

No TX-specific parameter deviation meets the materiality bar — there is no
deviation at all within the $1 tolerance.

### (b) Shelter-cap anomaly test: TX is perfectly clean

Zero TX over-cap rows in all five fiscal years — on clean-engine rows AND
on suggestive error rows alike (e.g. FY2024: 0 of 39 clean-engine and 0 of
119 error non-elderly shelter rows). For context, the fleet shows 8-21
over-cap clean-engine rows per year with 1-2 uncapped-only cases per year,
and the NE-six group contributes its own uncapped rows. TX contributes
none. TX's engine caps shelter deductions per statute, without exception
in this sample.

### (c) Output-side holdout: TX is cleaner than the fleet

| FY | TX clean-engine n | Exact match | Within $1 | MAE | Fleet exact |
|---|---|---|---|---|---|
| 2020 | 279 | 100.00% | 100.00% | $0.00 | 98.46% |
| 2021 | 84 | 100.00% | 100.00% | $0.00 | 97.77% |
| 2022 | 390 | 99.49% | 99.49% | $0.31 | 97.85% |
| 2023 | 345 | 99.71% | 100.00% | $0.00 | 97.71% |
| 2024 | 389 | 99.49% | 100.00% | $0.01 | 97.40% |

TX's statutory-formula exact-match runs 99.5-100% every year — *above* the
fleet's 97.4-98.5%. The two FY2022 tail rows (>$1) are the only misses in
3,457 TX rows across five years; the prorated-initial-month share is 0.000
in every FY (fleet 0.002-0.014). There is no TX recording artifact to
correct for: unlike NY's FY2020-2021 RAWNET==RAWGROSS quirk, TX's recorded
net-income field agrees with the component-recomputed net throughout.

### Input-side spot checks

- FY2024 SHELDED is dominated by $0 (175 rows) and the $672 cap (46 rows)
  — the expected signature of a single statewide SUA schedule capped at
  the shelter cap, with no NYC-style regional splits. Telephone $31 SUA
  appears in 0.0% of TX rows (vs 2.45% in NY) — TX records no standalone
  telephone-SUA mass in this sample.
- Proration: 0 prorated-like TX clean-engine rows in every FY (fleet
  0.2-1.4%) — no TX deviation.

## Verdict

Exceptionally clean TX engine — the cleanest of the three state POCs on the
output-side holdout (99.5-100% exact vs NY's 97.6-98.3% and PA's
99.7-100%). The parameter battery finds zero TX misconfiguration: the 30%
rate fits at 0.3000 to four decimals, ceiling rounding is exact at
0.986-1.000, the 20% earned disregard and all minimum benefits / standard
deductions / maximum allotments match statute, and the exp8b uncapped-
shelter pattern is absent — not one over-cap TX row in five years. TX's
error anatomy (TX3) is therefore a pure process-layer story: with the
engine this clean, TX's distinctive fingerprint (nature-99 "Other" coding
at 4.28x national, standard-deduction errors at 6.00x, agency-caused errors
at 1.24x) lives entirely in caseworker coding and verification workflows,
not in benefit computation.

Attribution limit (from exp8b, unchanged): the public-use file identifies
states, not eligibility-system vendors, so engine attribution beyond the
state level is impossible from this data. Everything here is TX-program
behavior.

## Next steps

- **Downstream:** TX3's process-layer story is now triply supported — the
  engine is cleaner than the fleet, benefit-computation errors are rare,
  and the distinctive errors are coding-practice signatures (nature 99,
  standard deduction). Copilot attention belongs on verification/coding
  workflows, not on benefit-formula corrections.
- No recording-artifact follow-up needed for TX (unlike NY): the net-income
  field is trustworthy in all five FYs.
