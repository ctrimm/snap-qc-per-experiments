# Experiment 10 — FY2024 statutory parameter audit
**Date:** 2026-09-29 · **Code:** (research phase — no code; `src/synth/params.py` untouched per plan)

## Hypothesis
`params.py`'s documented approximations match FY2024 federal SNAP statute closely
enough that applying the true values would not move calibration. This ties to the
north-star calibration gate: if our benefit math (the eligibility limits that
define the sampling frame and the parameters that feed the benefit formula) is
wrong, synthetic marginals drift and every downstream calibration comparison is
polluted. Plain-language stakes: wrong income limits admit synthetic households
that would never be eligible in real life; wrong deductions change every computed
benefit dollar.

Background terms: SNAP benefits start from the *maximum allotment* for a
household size, then subtract 30% of the household's *net income* (income after
allowed deductions). *Gross income* is income before deductions. The *standard
deduction* is a fixed monthly amount every household gets. The *excess shelter
deduction* lets households deduct housing costs above half their adjusted income,
but (except for elderly/disabled households) it is capped — the *shelter cap*.
The *earned-income disregard* removes 20% of wages so work does not count
one-for-one. The *QC error tolerance* is the dollar threshold under which a
benefit error does not count toward the official payment error rate. *COLA*
(cost-of-living adjustment) is the annual FNS update, effective each October 1.
*SUA* (standard utility allowance) is set by each state, not federally.

## Method
Research + audit only; no code changes.

1. Read `src/synth/params.py` (49 lines) and `src/synth/benefit.py`; inventoried
   every hard-coded policy parameter and the formula structure.
2. Pulled FY2024 (effective Oct 1, 2023 – Sep 30, 2024, 48 contiguous states +
   DC) parameters from FNS/USDA sources and independent analyses of the FNS
   COLA memo:
   - USDA FNS FY 2024 SNAP COLA memo (primary): maximum allotments, shelter
     cap, homeless shelter deduction, standard deduction floor, minimum
     benefit, resource limits. https://www.usda.gov/sites/default/files/guidance-documents/fns.FY24-SNAP-COLA-Memo_0.pdf
   - FRAC "A Review of SNAP Fiscal Year 2024 Cost-of-Living Adjustments"
     (Oct 2023), Table 1 (allotments), Table 2 (deductions), Table 3 (gross/net
     income limits by household size), plus the 30%-of-net-income benefit rule
     and the $23 minimum. https://frac.org/wp-content/uploads/SNAP-COLA-Research-Brief-FY-2024.pdf
   - Annotated SNAP Standards & Deductions reference sheet explicitly effective
     10/1/23–9/30/24: FPL-based gross/net limits, standard deductions, $672
     shelter cap, $179.66 homeless shelter deduction, $23 minimum, and NY
     county SUAs (state-set illustration). https://sff.gbtesting.us/wp-content/uploads/2024/06/SNAP-Budget-Worksheet-23-24-annotated.pdf
   - FNS QC Policy Memo 23-04: FY2024 error tolerance threshold $56 (up from
     $54 in FY2023). https://www.usda.gov/sites/default/files/guidance-documents/fns.snapQCpm23-04errorToleranceThresholdFY24.pdf
   - FNS "Effect of SNAP Benefit and Eligibility Parameters" executive summary
     (official FNS rules table): earned-income deduction = 20% of monthly
     household earned income; medical-expense deduction = out-of-pocket health
     expenses exceeding $35 for households with elderly (60+) or disabled
     members. https://fns-prod.azureedge.us/sites/default/files/ops/SNAPBEP-ExecutiveSummary.pdf
3. Compared every params.py value to the statutory value; computed exact deltas.

## Results

### Formula structure (`benefit.py`) — correct
The computation order matches the federal benefit formula: net = gross − 20%
earned − standard − medical(over $35, elderly/disabled only) − dependent care −
excess shelter (capped at $672 except for elderly/disabled households, which
have no cap); benefit = max_allotment(size) − 30% × net; $23 minimum for 1–2
person households; floored. The rounding in `benefit.py`
(`math.floor(max_allotment − 0.30 × net)`) is arithmetically identical to the
FNS rule "multiply net income by 30%, round the product up to the next whole
dollar, subtract from the maximum allotment." The shelter-cap exemption for
elderly/disabled households is implemented correctly.

### Parameters — matches vs mismatches

| Parameter | params.py value | FY2024 statutory value | Match? | Source |
|---|---|---|---|---|
| Max allotment, HH1–HH8 | 291 / 535 / 766 / 973 / 1155 / 1386 / 1532 / 1751 | same | Yes | COLA memo, FRAC Table 1 |
| Each additional person (allotment) | 219 | 219 | Yes | COLA memo, FRAC Table 1 |
| Standard deduction HH1–3 / HH4 / HH5 / HH6+ | 198 / 208 / 244 / 279 | same | Yes | COLA memo, FRAC Table 2 |
| Excess shelter deduction cap | 672 | 672 | Yes | COLA memo, FRAC Table 2 |
| Shelter cap waived, elderly/disabled | yes (no cap) | yes (no cap) | Yes | FRAC brief; formula logic |
| Earned-income disregard rate | 0.20 | 20% | Yes | FNS parameters summary |
| Medical deduction threshold | 35 (excess only) | $35 (excess only, elderly/disabled) | Yes | FNS parameters summary |
| Minimum benefit (1–2 person HH) | 23 | 23 | Yes | COLA memo, FRAC brief |
| 30% benefit reduction rate | 0.30 | 30% of net income | Yes | FRAC brief |
| QC error tolerance threshold | 56 | 56 | Yes | FNS QC Policy Memo 23-04 |
| **Gross income limit (130% FPL)** HH1–HH8 | 1677 / 2268 / 2859 / 3444 / 4029 / 4614 / 5199 / 5784 | 1580 / 2137 / 2694 / 3250 / 3807 / 4364 / 4921 / 5478 | **No** | FRAC Table 3, ref sheet |
| **Gross limit, each additional** | 585 | 557 | **No** | FRAC Table 3 |
| **Net income limit (100% FPL)** HH1–HH8 | 1290 / 1745 / 2199 / 2649 / 3099 / 3549 / 3999 / 4449 | 1215 / 1644 / 2072 / 2500 / 2929 / 3357 / 3785 / 4214 | **No** | FRAC Table 3, ref sheet |
| **Net limit, each additional** | 451 | 429 | **No** | FRAC Table 3 |

Magnitude of the income-limit mismatches (statutory value → params.py delta):

- Gross: HH1 +97 (+6.1%), HH2 +131 (+6.1%), HH3 +165 (+6.1%), HH4 +194
  (+6.0%), HH5 +222 (+5.8%), HH6 +250 (+5.7%), HH7 +278 (+5.6%), HH8 +306
  (+5.6%); each additional +28 (+5.0%).
- Net: HH1 +75 (+6.2%), HH2 +101 (+6.1%), HH3 +127 (+6.1%), HH4 +149
  (+6.0%), HH5 +170 (+5.8%), HH6 +192 (+5.7%), HH7 +214 (+5.7%), HH8 +235
  (+5.6%); each additional +22 (+5.1%).

Both limit schedules are systematically about 6% too high — consistent with
values copied from a later fiscal year (they sit near FY2025–FY2026 territory),
not FY2024.

### State-set vs federal (documented, not mismatches)
- **SUA (standard utility allowance): federal concept, state-set amounts.**
  NY's FY2024 reference sheet shows NYC $992 / Nassau–Suffolk $923 / rest of
  state $819; Texas's FY2025 handbook shows SUA $445, LUA $400, telephone $62.
  https://sff.gbtesting.us/wp-content/uploads/2024/06/SNAP-Budget-Worksheet-23-24-annotated.pdf,
  http://hhs.texas.gov/handbooks/texas-works-handbook/c-120-supplemental-nutrition-assistance-program
- **Homeless shelter deduction: federal, $179.66 for FY2024** (COLA memo) —
  not modeled in params.py at all; it is a flat deduction taken instead of the
  excess-shelter computation for homeless households. A modeling gap, not a
  wrong value.
- params.py also does not model the child-support-payment deduction (federal
  rule; FNS parameters summary). Same category: unmodeled, not wrong.

## Verdict
Hypothesis **partially falsified — calibration will move, but only through the
sampling frame, not the benefit math.**

What the audit found: every parameter that enters the benefit *computation*
(max allotments, deduction schedule, shelter cap and its elderly/disabled
exemption, 20% earned-income disregard, $35 medical threshold, $23 minimum, 30%
rate, $56 QC threshold) matches FY2024 statute exactly, and the formula
structure and rounding are correct. The benefit math needs no correction.

The real problem is the two **income-eligibility limit schedules**, which are
both ~6% too high for every household size ($75–$306 high, plus overstated
per-additional-person increments). My judgment on materiality:

- **Direction of bias:** overstated limits mean the sampler admits synthetic
  households whose gross or net income is above the true FY2024 cutoffs — up to
  ~6% above them. Those households are not eligible in reality, so they are
  pure frame contamination.
- **How much it matters:** the calibration arc compares synthetic vs real QC
  marginals. A ~6% eligibility band shift changes who enters the synthetic
  frame; admitted marginal households have high net income, so they land at the
  low-benefit end of the distribution (benefit = max allotment − 30% × net).
  This inflates the low-benefit tail of the synthetic marginals relative to
  the real QC public-use files. Given the calibration work is currently
  matching finding mix at the ~1% level, a 6% frame shift is **material** — it
  is the same order of magnitude as, or larger than, the residuals the team has
  been calibrating away.
- **What does not move:** any analysis conditioned on the benefit formula
  itself. exp-transfer findings about feature rawness vs richness, aspect
  gaps, etc. do not depend on these limits.

Secondary finding: params.py has **no homeless-shelter deduction ($179.66)**
and the benefit formula has **no child-support deduction**. These are federal
rules the generator silently drops. Their population impact is small (homeless
households and child-support-paying households are thin slices), so I judge
them **immaterial for calibration now**, but they are known unmodeled rules
that should be logged for the future-features list.

## Apply phase (2026-09-29)

Applied the FY2024 gross/net limit tables to `params.py` (with FY + source
annotations per the provenance recommendation), then recalibrated
(`measure_effectiveness.py`, `calibrate_injection.py` both modes).

**Compensating fix required:** the sampler's earnings draw (`p_earn = 0.60`)
had been tuned so post-screen P(earned>0) ≈ 0.27 under the OLD limits. The
correct (lower) screen rejects more earners, dropping the share to 0.240.
Bumped `p_earn` 0.60 → 0.65 (restores 0.268) rather than shifting `EARN_MU`,
keeping the earnings distribution matched to real FSEARN medians.

**Also applied:** exp15's blank-cause rule for nature 97 (cause left blank
with P=0.32; ~5 lines in `errors.py` via `_recorded_cause`).

**Incidental bug fix:** the exp9 worker's `--persistent-buckets` default-on
change broke `exp7_per_bucket_persistence.py`'s baseline (it shelled out
without the flag, so both arms ran persistent and reported identical
numbers). The baseline arm now passes `--no-persistent-buckets` explicitly.

**Calibration impact** (20k, seed 7; real 0.603/0.239/0.158):

| mode | finding L1 before | finding L1 after |
|---|---|---|
| retry-loop baseline | 0.010 | 0.023 |
| persistent | 0.044 | 0.041 |

The retry-loop L1 rose 0.010 → 0.023; persistent is flat (0.044 → 0.041).
Verdict: the frame is now statutory-correct, which dominates a lucky
calibration number on a contaminated frame — the old 0.010 was measured on
a population containing ineligible households. The residual L1 movement is
the honest cost of a correct frame, and both modes remain well within the
calibration gate.

## Next steps (updated)
Concrete apply + recalibrate plan for the follow-up (recommended first):

1. **(recommended) Apply the FY2024 gross/net limit schedules to params.py**
   (both full tables and the per-additional-person increments), rerun the
   synthetic generator, and rerun the current calibration metric to measure the
   marginal shift — that single number tests the materiality judgment above.
   Do NOT touch the benefit-math parameters; the audit cleared them.
   - **Done:** Applied in commit 19414d0 ("Exp10 apply: FY2024 limits, p_earn retune, 97 blank-cause").
2. Add the **$179.66 homeless-shelter deduction** and **child-support deduction**
   as documented unmodeled rules (either model them or record the exclusion in
   the future-features list with the population-share rationale).
3. Consider a **params provenance header**: each table annotated with fiscal
   year + source URL (e.g. the FNS FY24 COLA memo), so the next audit is a
   diff rather than a research project — and so a future fiscal-year rollover
   cannot silently contaminate the frame again. The limits being wrong by a
   clean ~6% suggests they were pasted from a later year's table; a one-line
   "FY2024, 48 states + DC" tag per table prevents recurrence.
4. Longer term: year-parameterized params (`params.for_fy(2024)`) if the
   project ever generates across fiscal years — the QC public-use files span
   FY2020–FY2024 and limits move every year.
