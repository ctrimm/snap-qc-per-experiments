# NY3 — New York SNAP QC error anatomy

**Date:** 2026-09-29 · **Code:** `experiments/ny3_ny_anatomy.py`

## Hypothesis

Tied to the north star (a small domain LM as a SNAP QC copilot): PA3 showed
that with a clean benefit-computation engine, a state's errors sit in the
human/process layer — verification, timing, procedure. NY8c (run alongside
this analysis) shows NY's engine also matches the statutory formula, so NY's
errors should likewise be process-layer: deduction-construction mistakes
(52/53/56/57), timing errors (97), verification causes (12/14/16), with
benefit-computation (nature 75) and arithmetic at or below national. But NY's
program differs from PA's (NYC caseload, distinct SUA schedule, no PACAP
equivalent), so the *shape* of the process layer may differ. This experiment
quantifies NY's anatomy against the national baseline to calibrate an
NY-flavored generator profile and to tell the copilot where to point its
attention. Plain-language terms: AMTERR = the actual dollar size of the error
on a case; FYWGT = the survey weight that scales each sampled case up to the
caseload it represents; L1 (where used) = the mean absolute difference
between two mixes.

## Method

Microdata: SNAP QC public-use files FY2020-2024, read-only
(`snap-qc-data/` beside the repo checkout). New York = STATE 36 (n = 3,257 rows;
1,194 error cases), national = all rows (n = 167,002). All shares are
FYWGT-weighted. Element/nature/cause mixes are computed on each error case's
primary variance (slot 1); the all-nine-slots check gave identical mixes to
three decimals, so error cases effectively carry one recorded variance.
Element, nature, and cause code meanings were taken from the FY2024 QC
Technical Documentation codebook (Chapter V). Dollar-error quantiles are on
AMTERR among error cases. Outlier ratios are NY share divided by national
share. FY trend table is NY-only, per fiscal year (note: FY2021's file is a
partial year, n = 221, July-September only).

## Results

### 1. Finding mix, direction mix, dollar-error quantiles (FYWGT-weighted)

| Mix | NY | National |
|---|---|---|
| Correct | 63.5% | 61.4% |
| Over-issuance | 21.0% | 23.8% |
| Under-issuance | 15.5% | 14.9% |
| Implied error rate | 36.5% | 38.6% |

Among error cases, direction: NY 57.5% over / 42.5% under vs national
61.5% / 38.5% — NY leans slightly more toward under-issuance (a larger share
of its errors shortchange households).

Dollar-error quantiles (AMTERR, errors only):

| | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|
| NY (all) | $3 | $10 | $29 | $86 | $201 |
| National (all) | $3 | $9 | $28 | $74 | $186 |
| NY over-issuances | $5 | $12 | $35 | $116 | $243 |
| NY under-issuances | $3 | $7 | $21 | $51 | $178 |

NY's errors run about the national median but with a slightly fatter right
tail (p75 $86 vs $74; over-issuance p90 $243 vs national all-error $186).

### 2. Element, nature, cause mixes — NY vs national

**Element buckets** (NY share, ratio vs national):

| Bucket | NY | Ratio NY/US |
|---|---|---|
| unearned | 25.9% | 1.12 |
| shelter | 25.8% | 0.83 |
| earned | 24.1% | 0.90 |
| sua | 8.4% | 1.51 |
| medical | 7.8% | 1.79 |
| hhcomp | 3.7% | 1.32 |
| other | 1.5% | 1.17 |
| arithmetic | 1.1% | 0.54 |
| depcare | 0.9% | 0.69 |
| standard deduction | 0.3% | 0.55 |
| reporting | 0.3% | 2.12 |
| child support | 0.2% | 0.26 |

Top element codes in NY: 363 shelter deduction (25.8%), 311 wages (22.0%),
331 RSDI (8.9%, 1.27x), 364 SUA (8.4%, 1.51x), 365 medical (7.8%, 1.79x),
333 SSI (7.7%, 1.51x), 334 unemployment compensation (4.4%, 2.00x),
150 unit composition (3.7%, 1.32x).

**Nature of variance** (NY shares, ratio vs national):

| Nature | Label (plain) | NY | Ratio |
|---|---|---|---|
| 97 | Timing: not required to report/act yet | 62.1% | 1.56 |
| 53 | Deduction included that should not have been | 6.2% | 0.62 |
| 38 | More income received than budgeted | 6.2% | 0.69 |
| 35 | Unreported source of income | 4.3% | 0.74 |
| 44 | Less income received than budgeted | 3.2% | 0.68 |
| 52 | Deduction that should have been included was not | 3.1% | 0.54 |
| 37 | Known income source not included at all | 2.9% | 0.95 |
| 39 | Employment status changed: unemployed to employed | 2.1% | 1.33 |
| 99 | Other nature | 1.5% | 0.26 |
| 98 | Transcription/computation errors | 1.1% | 1.01 |
| 40 | Employment status changed: employed to unemployed | 0.8% | 1.32 |
| 41 | Change only in amount of earnings | 0.5% | 0.48 |
| 64 | Wrong amount after a change of residence | 0.4% | 0.28 |
| 57 | Deduction amount budgeted too low | 0.3% | 0.37 |
| 75 | Benefit/eligibility incorrectly computed | 0.23% | 0.20 |
| 56 | Deduction amount budgeted too high | 0.11% | 0.08 |

Timing (97) is NY's story: 62% of its errors, 1.56x the national share — vs
33% in PA. Conversely, all four deduction-construction natures (52/53/56/57)
run *below* national (0.08-0.62x) — the mirror image of PA's 1.7-1.8x
overhang. Benefit-computation errors (75) are rare in NY (0.20x national),
corroborating the clean engine. Move-related shelter errors (64) are low
(0.28x). Unreported-income (35) runs below national (0.74x), like PA.

**Coding flag:** about 4.2% of NY's errors carry nature codes that do not
exist in the codebook (7, 8, 12, 13, 32, 33, 123, 200) — mostly on household
composition (element 150) and wages (311). These look like cause codes
misfiled into the nature field. It is a small, NY-specific recording quirk;
the national background for such codes is near zero (nature 200 runs 9.5x
national on just 2 NY rows).

**Cause** (top NY shares, ratio vs national):

| Cause | Label (plain) | NY | Ratio |
|---|---|---|---|
| 1 | Information not reported | 25.9% | 1.29 |
| 12 | Reported information disregarded / not applied | 24.4% | 1.40 |
| 10 | Policy incorrectly applied | 10.4% | 1.01 |
| 16 | Agency failed to verify required information | 8.4% | 1.47 |
| 26 | Not required to report/act (no fault) | 7.9% | 1.16 |
| 99 | Other (unspecified) | 6.2% | 1.09 |
| 15 | Failed to follow up on impending changes | 5.2% | 2.47 |
| 22 | Agency budgeted an incorrect amount | 3.0% | 2.54 |
| 14 | Failed to follow up on inconsistent info | 2.2% | 0.53 |
| 2 | Incomplete info; agency not required to verify | 2.1% | 0.29 |
| 19 | Mass change (computer-generated) | 1.4% | 0.36 |
| 18 | Data entry/coding error | 0.9% | 0.43 |
| 20 | Arithmetic computation error | 0.5% | 0.23 |
| 17 | Computer programming error | 0.1% | 0.07 |

Cause buckets: agency 51.2% (1.09x), client 28.5% (0.85x), "other" 12.4%
(0.99x), no-fault 7.9% (1.16x).

Unlike PA — where reviewers dump 20% of errors into cause-99 at 3.5x the
national rate — NY codes specifically: cause-99 sits at 6.2%, essentially the
national rate (1.09x), and the specific agency-failure codes that PA
under-codes (16 failed-to-verify at 1.47x, 15 failed-follow-up at 2.47x,
22 budgeted-wrong-amount at 2.54x) all run *above* national in NY. NY's
agency share is likely real, not an artifact. One more asymmetry vs PA: cause
2 ("agency not required to verify") is only 0.29x national in NY, and IPV
causes 3/4 are 0.33x/0.08x.

Top cause x element combos in NY (weighted share of all NY errors):
shelter x info-not-reported 7.8%, earned x reported-info-disregarded 7.2%,
earned x info-not-reported 7.2%, unearned x info-not-reported 5.3%, shelter x
reported-info-disregarded 3.5%, shelter x not-required-to-report (no fault)
3.2%, unearned x failed-to-verify 2.9%. (About 5% of NY error weight carries
an element code with a blank cause field — excluded from the cause mixes, as
in PA3.)

### 3. Top NY error patterns in plain language

(Element bucket + nature, primary variance; shares of NY errors; weighted
case counts; national comparison.)

1. **Shelter costs changed but the case couldn't or didn't have to act in
   time** (shelter/97): 21.9% of NY errors, ~617k weighted cases, median
   $10, 60% under-issuance. 1.33x national. NY's single biggest pattern —
   small-dollar rent changes inside reporting windows.
2. **Unearned income arrived (or changed) on timing the case couldn't act
   on** (unearned/97): 17.1%, ~482k, median $14, 62% over-issuance.
   **2.03x national** — NY's most distinctive big pattern.
3. **Paycheck timing — earnings changed but the case wasn't required to act
   yet** (earned/97): 11.1%, ~312k, median $24, 67% over. 1.03x national —
   ordinary, not NY-specific.
4. **Medical expenses changed on untouchable timing** (medical/97): 5.4%,
   ~151k, median $16, 58% under. **3.39x national.**
5. **Wages came in higher than budgeted** (earned/38): 4.5%, ~127k, median
   $150, 90% over. 0.96x national — ordinary income volatility.
6. **Utility allowance applied on timing the case couldn't act on**
   (sua/97): 3.8%, ~108k, median $9, 64% over. **3.06x national.**
7. **A utility allowance was on the budget that shouldn't have been**
   (sua/53): 3.4%, ~94k, median $115, 97% over. 1.44x national — NY's one
   deduction-construction pattern above national.
8. **Unearned income the agency knew about was left off the budget**
   (unearned/37): 2.7%, ~75k, median $165, 98% over. 0.97x national.
9. **Unreported wage income** (earned/35): 2.2%, ~62k, median $230, 92%
   over. 0.72x national — below the national share.
10. **Unreported unearned income** (unearned/35): 2.1%, ~59k, median $183,
    94% over. 0.76x national.
11. **Newly employed — wages from a new job not budgeted** (earned/39):
    2.1%, ~59k, median $192, 97% over. 1.33x national.
12. **Unearned income came in lower than budgeted** (unearned/44): 1.7%,
    ~49k, median $134, 97% under. 0.59x national.

Timing patterns (97) total about 58% of all NY errors by weight — the
distinctive NY fingerprint is unearned-income timing (2.03x), medical timing
(3.39x), and SUA timing (3.06x). The large-dollar tail is thinner than PA's:
NY's biggest recurring pattern by median is earned/35 at $230 vs PA's
newly-employed tail at $258.

### 4. FY trend within NY — stable, with shelter's share drifting up

| FY | n | err rate | over-share | shelter | earned | unearned | medical | sua | agency-cause |
|---|---|---|---|---|---|---|---|---|---|
| 2020 | 399 | 32.0% | 56.3% | 19.6% | 26.7% | 19.7% | 10.3% | 12.8% | 58.1% |
| 2021 | 221 | 39.7% | 58.8% | 23.8% | 15.7% | 31.4% | 11.8% | 9.2% | 57.1% |
| 2022 | 896 | 36.1% | 56.7% | 26.2% | 23.9% | 28.7% | 5.8% | 9.8% | 48.6% |
| 2023 | 856 | 35.9% | 57.3% | 27.6% | 28.1% | 20.5% | 6.8% | 7.1% | 56.7% |
| 2024 | 885 | 38.7% | 58.1% | 30.3% | 26.5% | 27.6% | 4.7% | 4.4% | 38.9% |

Shelter's share climbs steadily (20% to 30%) while medical and SUA shares
fall; the direction mix holds around 57% over. The FY2021 row is noisy
(partial-year file, n = 221). The FY2024 drop in agency-cause share (to
38.9%) is the only sharp move in the table and is worth one verification
pass before being treated as a trend. Note the FY2023->FY2024 unearned jump
(20.5% to 27.6%).

### 5. NY above/below national — the downstream table

**Above national (NY share / national share):** medical 1.79x, SUA 1.51x,
household composition 1.32x, unearned income 1.12x; timing nature 97 1.56x;
nature 39 (newly employed) 1.33x; causes 22 (budgeted wrong amount) 2.54x,
15 (failed follow-up on impending changes) 2.47x, 16 (failed to verify)
1.47x, 12 (reported info disregarded) 1.40x, 1 (not reported) 1.29x;
patterns unearned/97 2.03x, medical/97 3.39x, sua/97 3.06x, sua/53 1.44x,
shelter/97 1.33x, earned/39 1.33x.

**Below national:** shelter 0.83x, earned 0.90x, arithmetic 0.54x, dependent
care 0.69x, child support 0.26x; natures 52/53/56/57 (deduction
construction) 0.54x/0.62x/0.08x/0.37x; nature 75 (benefit miscomputed) 0.20x;
nature 64 (move-related shelter) 0.28x; nature 35 (unreported income) 0.74x;
cause 2 0.29x, cause 14 0.53x, IPV causes 3/4 0.33x/0.08x.

## Verdict

The hypothesis holds, with a NY-specific twist. NY's engine is clean
(NY8c: benefit-computation errors at 0.20x national, arithmetic at 0.54x —
the computers add correctly), and its errors are process-layer. But the
process failure in NY looks nothing like PA's. Where PA's fingerprint was
deduction *construction* (all four 52/53/56/57 natures at 1.7-1.8x), NY
runs all four *below* national and instead concentrates in *timing*:
nature 97 is 62% of NY errors at 1.56x national. NY's distinctive mass is
unearned-income timing (2.03x), medical-expense timing (3.39x), and
utility-allowance timing (3.06x) — changes arriving inside reporting windows
the caseworker wasn't required to act on. NY's one deduction-construction
overhang is wrongly-included SUAs (sua/53, 1.44x, median $115, 97% over).

Two coding-practice notes, both favorable for cross-state comparison: (a) NY
does not have PA's cause-99 distortion — cause-99 sits at the national rate
(1.09x), and NY uses the specific agency codes (16, 15, 22) PA under-codes,
all above national; NY's agency-attributable share (51%) is likely honest.
(b) A small NY-specific quirk: ~4% of NY errors carry non-codebook nature
codes (7/8/12/13/32/33/123/200), mostly on household composition and wages —
cause codes misfiled into the nature field; small enough to ignore for
generator calibration, worth a flag in the file.

Caveats: (a) FY2021 is a partial-year file (n = 221); (b) the FY2024
agency-cause drop (38.9%) needs one more year before it counts as a trend;
(c) cause coding remains reviewer judgment — the "verification gap" reading
of causes 1/12/16 is an inference from codes, not a direct observation of
worker behavior; (d) the non-codebook nature codes (~4%) mean a small slice
of the nature mix is mislabeled.

## Next steps

- **Calibration gate (recommended):** an NY-flavored generator profile must
  reproduce nature 97 at ~62% (1.56x national) with the
  unearned/97-medical/97-sua/97 fingerprint at 2.0x/3.4x/3.1x, nature
  52/53/56/57 *below* national, nature 75/98 near zero, shelter rising
  20%-30% across years, and medical/SUA timing mass with the under-lean —
  add an NY slice to the golden calibration set with these as targets.
- **Copilot NY POC:** prioritize (1) unearned-income timing/change review
  (especially UC 334 at 2.00x and SSI 333 at 1.51x), (2) medical-expense
  deduction timing, (3) SUA applicability review (sua/53), (4) shelter-change
  timing — in that order of weighted case mass.
- **NY vs PA comparison note:** the two states' process failures are
  complementary (PA: deduction construction; NY: timing) — a copilot trained
  on pooled national mixes will mis-allocate attention in both; state
  conditioning is warranted (see exp33).
- Do not build an NY-specific benefit-computation correction: the engine is
  clean and the data re-confirms it.
