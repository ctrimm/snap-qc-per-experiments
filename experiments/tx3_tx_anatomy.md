# TX3 — Texas SNAP QC error anatomy

**Date:** 2026-10-03 · **Code:** `experiments/tx3_tx_anatomy.py`

## Hypothesis

Tied to the north star (a small domain LM as a SNAP QC copilot): PA3 showed
that with a clean benefit-computation engine, a state's errors sit in the
human/process layer — verification, timing, procedure. TX8c (run alongside
this analysis) shows TX's engine is the cleanest of the three state POCs
(99.5-100% output-side exact match, zero over-cap shelter rows in five
years), so TX's errors should likewise be process-layer. But TX's program
differs from PA's and NY's (no state income tax, distinct county-administered
delivery, large caseload), so the *shape* of the process layer may differ.
This experiment quantifies TX's anatomy against the national baseline to
calibrate a TX-flavored generator profile and to tell the copilot where to
point its attention. Plain-language terms: AMTERR = the actual dollar size
of the error on a case; FYWGT = the survey weight that scales each sampled
case up to the caseload it represents; L1 (where used) = the mean absolute
difference between two mixes.

## Method

Microdata: SNAP QC public-use files FY2020-2024, read-only
(`~/workspace/snap-qc-data/`). Texas = STATE 48 (n = 3,457 rows;
1,530 error cases), national = all rows (n = 167,002). All shares are
FYWGT-weighted. Element/nature/cause mixes are computed on each error case's
primary variance (slot 1); the all-nine-slots check gave identical mixes to
three decimals, so error cases effectively carry one recorded variance.
Element, nature, and cause code meanings were taken from the FY2024 QC
Technical Documentation codebook (Chapter V). Dollar-error quantiles are on
AMTERR among error cases. Outlier ratios are TX share divided by national
share. FY trend table is TX-only, per fiscal year (note: FY2020-2021's files
are partial years — FY2020 n = 612, FY2021 n = 182, July-September only).

## Results

### 1. Finding mix, direction mix, dollar-error quantiles (FYWGT-weighted)

| Mix | TX | National |
|---|---|---|
| Correct | 56.6% | 61.4% |
| Over-issuance | 22.3% | 23.8% |
| Under-issuance | 21.1% | 14.9% |
| Implied error rate | 43.4% | 38.6% |

Among error cases, direction: TX 51.4% over / 48.6% under vs national
61.5% / 38.5% — TX leans much more toward under-issuance than either PA or
NY (a larger share of its errors shortchange households).

Dollar-error quantiles (AMTERR, errors only):

| | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|
| TX (all) | $3 | $10 | $27 | $60 | $149 |
| National (all) | $3 | $9 | $28 | $74 | $186 |
| TX over-issuances | $3 | $12 | $30 | $65 | $178 |
| TX under-issuances | $3 | $9 | $25 | $50 | $134 |

TX's errors run smaller than national's across the board (p90 $149 vs
$186), with under-issuances notably larger at the median than national's
($25 vs $21) — TX's under-tilt is a *dollars* fact as well as a count fact.

### 2. Element mix — the standard-deduction and "other" signature

| Element bucket | TX share | National share | TX/nat ratio |
|---|---|---|---|
| Standard deduction | 3.37% | 0.56% | **6.00x** |
| Arithmetic | 3.05% | 1.97% | 1.55x |
| Dependent care | 1.79% | 1.37% | 1.31x |
| Utility allowance (SUA) | 7.13% | 5.59% | 1.28x |
| Household composition | 3.30% | 2.80% | 1.18x |
| Earned income | 28.99% | 26.81% | 1.08x |
| Shelter deduction | 27.79% | 31.10% | 0.89x |
| Unearned income | 19.67% | 23.24% | 0.85x |
| Medical expenses | 2.44% | 4.34% | **0.56x** |

The 6.00x standard-deduction ratio is TX's standout — but it is a
**FY2022 one-year blip**, not a stable fingerprint (see §4): 104
standard-deduction error cases in FY2022 vs 0-15 in every other year, 102
coded nature 99 and 99 coded cause 19 ("Mass change, computer-generated").
The FY2022 COLA mass change misfired on the standard deduction and QC
coded the fallout. Excluding FY2022, TX's stable element signature is:
depcare/sua/earned above national, medical (0.56x) and shelter (0.89x)
below — the inverse of NY's medical-heavy profile.

### 3. Nature mix — TX codes "Other" (99) at 4.28x national

| Nature | Label | TX share | Nat share | Ratio |
|---|---|---|---|---|
| 99 | Other | 24.70% | 5.77% | **4.28x** |
| 54 | Incorrect standard used | 1.49% | 0.72% | 2.08x |
| 64 | Incorrect amount from change | 2.28% | 1.23% | 1.85x |
| 75 | Benefit/allotment/eligibility incorrectly computed | 2.04% | 1.17% | 1.74x |
| 57 | Incorrect deduction amount included | 1.07% | 0.70% | 1.53x |
| 97 | Not required to be reported/acted on (timing) | below national on most buckets (see TX1) | | 0.48-1.04x |

TX's defining nature fact: **nearly one in four TX errors (24.7%) is coded
nature 99 "Other"**, vs 5.8% nationally. This is not the PA pattern
(deduction-construction 52/53/56/57 at 1.7-1.8x) and not the NY pattern
(timing 97 at 1.56x) — TX's reviewers reach for "Other" where NY's reach
for timing codes. The top TX patterns by weight:

1. **shelter × 99** (12.5% of TX errors, 4.45x national, median $21) —
   TX's #1 pattern; shelter issues the reviewer couldn't fit to a
   specific nature.
2. earned × 97 (9.9%, 0.93x — timing on wages, at national rate).
3. shelter × 97 (6.8%, 0.41x — well below national).
4. **standard × 99** (3.2%, 10.88x — the FY2022 mass-change blip).
5. earned × 99 (3.1%, 3.28x).

Nature 75 (benefit incorrectly computed) at 1.74x deserves a note: it looks
like a computation-layer signal, but TX8c's engine is 99.5-100% clean —
these are reviewer-coded "computed wrong" on cases the engine actually got
right, i.e. a coding-practice signature, not an engine fact.

### 4. FY trend within TX — the direction flip and the FY2022 blip

| FY | n | err rate | over-share | shelter | earned | unearned | medical | sua | depcare | standard |
|---|---|---|---|---|---|---|---|---|---|---|
| 2020 | 612 | 41.2% | 59.2% | 28.0% | 31.3% | 21.0% | 2.9% | 5.0% | 3.2% | 0.0% |
| 2021 | 182 | 36.8% | 56.9% | 32.5% | 27.5% | 23.9% | 1.0% | 11.3% | 0.0% | 0.0% |
| 2022 | 866 | 46.9% | 45.0% | 20.6% | 26.3% | 18.4% | 1.1% | 4.5% | 2.2% | **13.6%** |
| 2023 | 842 | 44.1% | 47.8% | 29.4% | 30.9% | 16.8% | 2.9% | 7.5% | 1.8% | 1.0% |
| 2024 | 955 | 45.5% | 49.4% | 29.3% | 29.0% | 18.9% | 4.3% | 7.8% | 1.6% | 1.4% |

Two real temporal patterns: (a) **the direction flip** — TX's errors were
over-tilted in FY2020-2021 (59%/57% over) and flipped to under-tilted in
FY2022-2024 (45%/48%/49% over). The pooled 51.4% over-share averages across
a genuine regime change, not a stable mix. (b) **The FY2022 standard-
deduction blip** (13.6% vs ~1% in all other years) — the mass-change
misfire documented in §2. The FY2020-2021 rows are noisy (partial-year
files).

### 5. Cause mix — agency-heavy, specific codes

| Cause bucket | TX share | National share | Ratio |
|---|---|---|---|
| Agency | 58.2% | 47.1% | **1.24x** |
| Client | 30.0% | 33.4% | 0.90x |
| No-fault (26) | 5.3% | 6.8% | 0.77x |
| Other (99) | 6.5% | 12.6% | 0.51x |

Top specific causes (TX/nat): cause 2 (incomplete/incorrect info) 2.19x,
cause 19 (mass change) 2.09x, cause 10 (policy incorrectly applied) 1.68x,
cause 12 (reported info disregarded) 1.39x, cause 22 (budgeted wrong
amount) 1.32x. TX does not have PA's cause-99 distortion (0.51x — TX
under-codes "other" cause) and uses specific agency codes honestly. TX's
agency-attributable share (58%) is the highest of the three state POCs.

### 6. TX above/below national — the downstream table

**Above national (TX share / national share):** standard deduction 6.00x
(FY2022 blip); arithmetic 1.55x; depcare 1.31x; SUA 1.28x; earned 1.08x;
nature 99 ("Other") 4.28x; natures 54/64/75/57 at 1.53-2.08x; causes 2
(2.19x), 19 (2.09x), 10 (1.68x), 12 (1.39x); patterns shelter/99 4.45x,
earned/99 3.28x, standard/99 10.88x.

**Below national:** medical 0.56x; shelter 0.89x; unearned 0.85x; timing
nature 97 at 0.48-1.04x per bucket (the anti-NY); cause 99 ("other") 0.51x;
cause 1 (not reported) 0.70x.

## Verdict

The hypothesis holds, with a TX-specific twist that is neither PA's nor
NY's. TX's engine is the cleanest of the three POCs (TX8c), and its errors
are process-layer — but the process failure in TX looks like **coding
practice, not verification gaps**: TX's reviewers code one in four errors
as nature 99 "Other" (4.28x national), led by shelter×99 (4.45x, TX's #1
pattern by weight). Where PA's fingerprint was deduction *construction* and
NY's was *timing*, TX's is **"other"-coding with an underissuance tilt**:
p(over|err) 51.4% vs 61.5% national, a tilt that *flipped* in FY2022 (from
59% over to 45% over) — a genuine regime change the pooled number hides.
TX's agency-cause share (58%, 1.24x) is the highest of the three POCs, and
its cause coding is honest (specific agency codes, no cause-99 distortion).

Two qualifications for downstream use: (a) the 6.00x standard-deduction
ratio is a FY2022 mass-change one-year blip (104 cases, 99 coded cause 19)
— the generator correctly excludes it (standard is not a supported
generator bucket), but any TX analysis that pools FY2022 inherits it; (b)
nature 75 at 1.74x is a coding signature, not an engine signal (TX8c's
engine is 99.5-100% clean).

Caveats: (a) FY2020-2021 are partial-year files; (b) the direction flip
needs one more year to confirm as a permanent regime vs a FY2022-2024
episode; (c) cause coding remains reviewer judgment — the "agency-heavy"
reading is an inference from codes, not a direct observation of worker
behavior.

## Next steps

- **TX2's transfer battery** should expect the element leg to be *harder*
  than NY's in one specific way: TX's #1 pattern (shelter×99) is a coding-
  practice signature with no clean feature correlate — the model cannot
  learn "reviewer coded Other" from agency-view facts. The finding and
  dollar legs carry the transferable signal.
- **TX6 (temporal)** must test the direction flip: a refit on FY2020-21 vs
  pooled, evaluated on FY2023-24, will show whether the under-tilt is
  stable or the flip breaks the transfer.
- The FY2022 mass-change blip is a natural experiment for the generator's
  robustness — noted, not modeled.
