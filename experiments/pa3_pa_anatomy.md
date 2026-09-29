# PA3 — Pennsylvania SNAP QC error anatomy

**Date:** 2026-09-29 · **Code:** `experiments/pa3_pa_anatomy.py`

## Hypothesis

Tied to the north star (a small domain LM as a SNAP QC copilot): exp8c showed
PA's benefit-calculation engine matches federal statute 99.7-100% every year,
so PA's errors must live in the human/process layer (verification, timing,
procedure). If that is right, PA's error anatomy should show the fingerprints
of process failure — deduction-construction mistakes (52/53/56/57), timing
and move-related shelter errors (97/64), verification gaps (causes 12/14/16) —
and should show *clean* benefit computation (nature 75, arithmetic) at or below
national levels. This experiment quantifies that anatomy against the national
baseline, which does two jobs: it calibrates what a PA-flavored generator (and
a PA POC copilot) must reproduce, and it tells the copilot where to point its
attention.

## Method

Microdata: SNAP QC public-use files FY2020-2024, read-only
(`~/workspace/snap-qc-data/`). Pennsylvania = STATE 42 (n = 3,268 rows;
1,395 error cases), national = all rows (n = 167,002). All shares are FYWGT-
weighted. Element/nature/cause mixes are computed on each error case's primary
variance (slot 1); a check against all nine variance slots gave identical mixes
to four decimals, so error cases effectively carry one recorded variance.
Element, nature, and cause code meanings were taken from the FY2024 QC
Technical Documentation codebook (Chapter V). Dollar-error quantiles are on
AMTERR among error cases. Outlier ratios are PA share divided by national
share. FY trend table is PA-only, per fiscal year (note: FY2021's file is a
partial year, n = 189, July-September only).

## Results

### 1. Finding mix, direction mix, dollar-error quantiles (FYWGT-weighted)

| Mix | PA | National |
|---|---|---|
| Correct | 58.8% | 61.4% |
| Over-issuance | 24.7% | 23.8% |
| Under-issuance | 16.6% | 14.9% |
| Implied error rate | 41.3% | 38.6% |

Among error cases, direction: PA 59.9% over / 40.1% under vs national
61.5% / 38.5% — PA leans slightly more toward under-issuance.

Dollar-error quantiles (AMTERR, errors only):

| | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|
| PA (all) | $3 | $8 | $25 | $55 | $156 |
| National (all) | $3 | $9 | $28 | $74 | $186 |
| PA over-issuances | $3 | $9 | $31 | $76 | $197 |
| PA under-issuances | $3 | $7 | $18 | $39 | $93 |

PA's errors run slightly smaller than the nation's, especially under-
issuances and the right tail.

### 2. Element, nature, cause mixes — PA vs national

**Element buckets** (PA share, ratio vs national):

| Bucket | PA | Ratio PA/US |
|---|---|---|
| shelter | 45.2% | 1.45 |
| earned | 22.5% | 0.84 |
| unearned | 16.7% | 0.72 |
| medical | 5.4% | 1.24 |
| sua | 4.4% | 0.80 |
| hhcomp | 2.3% | 0.82 |
| depcare | 1.5% | 1.08 |
| childsupport | 0.8% | 1.01 |
| arithmetic | 0.4% | 0.22 |
| standard deduction | 0.0% | 0.00 |

Top element codes in PA: 363 shelter deduction (45.2%), 311 wages (19.4%),
365 medical (5.4%), 331 RSDI (4.5%), 364 SUA (4.4%), 333 SSI (4.4%).

**Nature of variance** (top PA shares, ratio vs national):

| Nature | Label (plain) | PA | Ratio |
|---|---|---|---|
| 97 | Timing: not required to report/act yet | 33.4% | 0.84 |
| 53 | Deduction included that should not have been | 16.7% | 1.66 |
| 52 | Deduction that should have been included was not | 10.5% | 1.81 |
| 38 | More income received than budgeted | 9.0% | 1.00 |
| 44 | Less income received than budgeted | 5.7% | 1.23 |
| 37 | Known income source not included at all | 4.2% | 1.39 |
| 35 | Unreported source of income | 3.0% | 0.53 |
| 56 | Deduction amount budgeted too high | 2.5% | 1.76 |
| 39 | Employment status changed: unemployed to employed | 2.4% | 1.51 |
| 64 | Wrong amount after a change of residence | 2.4% | 1.91 |
| 99 | Other nature | 1.7% | 0.29 |
| 57 | Deduction amount budgeted too low | 1.2% | 1.70 |
| 75 | Benefit/eligibility incorrectly computed | 0.14% | 0.12 |
| 98 | Transcription/computation errors | 0.06% | 0.05 |

The four deduction-construction natures (52/53/56/57) are all 1.7-1.8x the
national share. Benefit-computation errors (75) and transcription errors (98)
are nearly absent in PA. PA is also light on hidden-income errors: unreported
source of income (35) is 0.53x national, and "other" nature (99) is 0.29x.

**Cause** (top PA shares, ratio vs national):

| Cause | Label (plain) | PA | Ratio |
|---|---|---|---|
| 1 | Information not reported | 23.0% | 1.14 |
| 12 | Reported information disregarded / not applied | 20.9% | 1.20 |
| 99 | Other (unspecified) | 20.1% | 3.53 |
| 10 | Policy incorrectly applied | 8.8% | 0.85 |
| 2 | Incomplete info; agency not required to verify | 6.2% | 0.88 |
| 14 | Failed to follow up on inconsistent info | 4.7% | 1.16 |
| 4 | Wrong info provided by client (IPV) | 4.6% | 0.74 |
| 26 | Not required to report/act (no fault) | 4.0% | 0.58 |
| 18 | Data entry/coding error | 2.9% | 1.34 |
| 16 | Agency failed to verify required info | 1.0% | 0.18 |
| 22 | Agency budgeted an incorrect amount | 0.2% | 0.17 |
| 19 | Mass change (computer-generated) | 0.3% | 0.08 |
| 3 | Info withheld by client (IPV) | 0.2% | 0.09 |
| 17 | Computer programming error | 0.4% | 0.21 |

Cause buckets: agency 39.9% (0.85x), client 33.8% (1.01x), "other" 22.4%
(1.77x), no-fault 4.0% (0.58x).

Two coding-practice flags: PA reviewers code cause as "Other" (99) at 3.5x
the national rate, concentrated in shelter (52% of PA's cause-99 weight) and
earned income (31%). Meanwhile specific agency-failure codes (16 failed to
verify, 19 mass change, 22 budgeted wrong amount, 17 programming error, 3
withheld/IPV) are all at 0.08-0.21x national. PA's true agency-attributable
share is likely understated by the coarse coding, not genuinely that clean.

Top cause x element combos in PA (weighted share of all PA errors):
shelter x info-not-reported 12.0%, shelter x cause-Other 10.5%, earned x
info-not-reported 7.4%, shelter x reported-info-disregarded 6.9%, earned x
cause-Other 6.1%, unearned x reported-info-disregarded 5.2%, shelter x
incomplete-info 5.0%, shelter x wrong-info-by-client 4.3%.

### 3. Top PA error patterns in plain language

(Element bucket + nature, primary variance; shares of PA errors; weighted case
counts; national comparison.)

1. **Shelter costs changed but the case couldn't or didn't have to act in
   time** (shelter/97): 20.1% of PA errors, ~400k weighted cases, median $9,
   64% under-issuance. Plain reading: rent changed (or a move happened) inside
   a reporting window where the agency wasn't required to act — usually the
   household came up a few dollars short. 1.22x national.
2. **A shelter deduction was on the budget that shouldn't have been**
   (shelter/53): 10.2%, ~203k, median $30, 90% over-issuance. 1.95x national.
3. **Paycheck timing — earnings changed but the case wasn't required to act
   yet** (earned/97): 9.9%, ~197k, median $23, 61% over. 0.92x national.
4. **A shelter deduction the household was entitled to was left off**
   (shelter/52): 7.7%, ~153k, median $24, 89% under-issuance. 2.30x national —
   PA's most distinctive pattern by ratio among the big ones.
5. **Wages came in higher than budgeted** (earned/38): 4.6%, ~91k, median
   $65, 95% over. 0.97x national — ordinary income volatility, not PA-specific.
6. **RSDI came in higher than budgeted** (unearned/38, likely benefit
   adjustments): 4.4%, ~88k, median $19, 93% over. 1.03x national.
7. **SSI the agency knew about was left off the budget entirely**
   (unearned/37): 4.0%, ~79k, median $30, 99% over. 1.46x national.
8. **SSI came in lower than budgeted** (unearned/44): 4.0%, ~80k, median $23,
   88% under. 1.38x national.

Also notable: **medical deduction included that shouldn't have been**
(medical/53): 3.6%, ~72k, median $48, 98% over, 1.93x national; and
**newly employed — wages from a new job not budgeted** (earned/39): 2.4%,
~47k weighted cases, median **$258** — rare but the largest-dollar pattern in
PA's mix, 97% over-issuance, 1.51x national.

### 4. FY trend within PA — the mix is stable

| FY | n | err rate | over-share | shelter | earned | unearned | medical | agency-cause |
|---|---|---|---|---|---|---|---|---|
| 2020 | 631 | 40.3% | 62.6% | 47.1% | 19.3% | 19.7% | 7.5% | 41.9% |
| 2021 | 189 | 32.8% | 50.8% | 44.5% | 16.4% | 22.6% | 6.3% | 42.1% |
| 2022 | 817 | 42.8% | 58.0% | 43.9% | 24.1% | 18.6% | 5.7% | 47.8% |
| 2023 | 817 | 47.6% | 61.0% | 44.4% | 24.8% | 12.2% | 3.0% | 33.4% |
| 2024 | 814 | 42.9% | 64.4% | 45.6% | 25.9% | 12.7% | 4.9% | 36.0% |

Shelter's share sits at 44-47% every year; earned income drifts up modestly
(16-19% to 25-26%); the direction mix stays around 60% over. The FY2021 row
is noisy (partial-year file, n = 189). The only visible drift is unearned
income falling from ~20% to ~12% in 2023-2024 as earned income rose — plausibly
the post-pandemic labor-market mix shift, not a PA policy change (flagged as
speculation; the microdata alone cannot distinguish).

## Verdict

The hypothesis holds: PA's error anatomy is a process-layer story, and it is a
*distinctive* one. The engine-is-clean result from exp8c is independently
corroborated here — nature 75 (benefit incorrectly computed) runs at 0.12x
national, arithmetic errors at 0.22x, and transcription/computation errors at
0.05x. PA's computers add correctly; its people and procedures mis-handle
deductions and timing.

What makes PA distinctive is not hidden income — PA is *below* national on
unreported income sources (0.53x) — but deduction administration: shelter
deductions dominate (45% of errors, 1.45x national), all four deduction-
construction natures run 1.7-1.8x national, wrongly-omitted shelter deductions
(shortchanging households, 89% under) run 2.3x national, and move-related
shelter amount errors (nature 64) run 1.9x. The characteristic PA error is
small-dollar (median $25 vs $28 national): high-frequency, small misses in
shelter deduction construction and timing, plus a thin tail of big newly-
employed wage errors (median $258).

Caveats: (a) PA reviewers code cause as "Other" at 3.5x the national rate, so
the agency-attributable share is likely understated and cross-state cause
comparisons for PA should be read with that grain of salt; (b) FY2021 is a
partial-year file; (c) cause coding is a reviewer judgment, not ground truth —
the "verification gap" reading of causes 12/1 is an inference from codes, not
a direct observation of worker behavior.

## Next steps

- **Calibration gate (recommended):** a PA-flavored generator profile must
  reproduce shelter ~45%, the 52/53/56/57 cluster at ~1.7-1.8x national, nature
  75/98 near zero, small-dollar timing mass (97) with the under-lean on
  shelter, and the rare large-dollar earned/39 tail — add a PA slice to the
  golden calibration set with these as targets.
- **Copilot PA POC:** prioritize (1) shelter deduction construction checks
  (included-vs-omitted, amount), (2) change-of-residence workflows, (3)
  newly-employed wage detection, (4) medical deduction review — in that order
  of weighted case mass.
- **Cause-99 audit (small):** pull the PA cause-99 cases and hand-code a
  sample against the specific agency codes to estimate how much of PA's
  "Other" is really failed verification (16) vs budgeted-wrong-amount (22) —
  this decides how to interpret PA's agency share for the copilot's
  verification-gap features.
- Do not build a PA-specific benefit-computation correction: the engine is
  clean and the data re-confirms it.
