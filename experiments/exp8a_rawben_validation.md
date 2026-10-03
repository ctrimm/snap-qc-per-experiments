# Experiment 8a — RAWBEN validation: is the issued benefit a clean read of the agency's engine?
**Date:** 2026-09-29 · **Code:** `/tmp/exp8a_validate_rawben.py` (read-only;
data stays out of the repo) · **Data:** `snap-qc-data/raw/` (beside the repo checkout)
FY2020–2024 public-use files (167,002 rows total)

## Hypothesis
Exp 8 wants to reverse-engineer the production eligibility engine
behaviorally: the QC file carries household facts plus two benefit numbers
per case. If **RAWBEN** is truly the benefit the state agency's system
computed and issued, then (facts → RAWBEN) pairs are black-box observations
of the real rules engine, and we can later fit its effective parameters
(shelter cap, SUA tiers, disregards) and flag deviations from statute.
This experiment validates that premise before any fitting is attempted.

Plain terms: *FSBEN* = the benefit the QC reviewer calculated the household
*should* have gotten (the "correct" answer). *RAWBEN* = the benefit the
household actually got. *AMTERR* = the dollar size of the mistake
(unsigned — always positive). *STATUS* = 1 (amount correct), 2
(over-issuance: got too much), 3 (under-issuance: got too little).

## Method
1. Read the FY2024 tech doc codebook for the documented definitions of
   FSBEN, RAWBEN, AMTERR, STATUS.
2. For each FY2020–2024 file, check the identity
   AMTERR == |FSBEN − RAWBEN| (exact and within $1), overall and by STATUS.
   Also check sign consistency: STATUS=2 should mean RAWBEN > FSBEN,
   STATUS=3 RAWBEN < FSBEN, STATUS=1 RAWBEN == FSBEN.
3. Sanity: RAWBEN/FSBEN distributions, blanks, zeros, extreme values;
   whether the relationship holds across fiscal years.
4. Confirm a state identifier exists; count PA cases per FY (needed for
   exp8b–c, which fit on Pennsylvania).

## Results
Codebook (FY2024 tech doc, Mathematica):
- RAWBEN: "Reported amount of SNAP benefits that the unit was certified
  to receive during the sample month." Origin: reported (R).
- FSBEN: "Final calculated benefit" = MAX(minimum benefit,
  BENMAX − ROUND(0.3 × FSNETINC)). Origin: calculated (C).
- AMTERR: "Dollar amount of any identified error, or the difference between
  the benefits the State agency authorized and the benefits the State
  agency should have authorized." Unsigned, range 0–2377.
- STATUS: 1 = amount correct, 2 = overissuance, 3 = underissuance.

Identity check AMTERR == |FSBEN − RAWBEN|:

| FY | cases | exact match | within $1 | RAWBEN blank | FSBEN blank |
|---|---|---|---|---|---|
| 2020 | 27,112 | 0.853 | 0.922 | 0 | 0 |
| 2021 (Jul–Sep only) | 9,832 | 0.790 | 0.863 | 0 | 0 |
| 2022 | 41,391 | 0.867 | 0.930 | 0 | 0 |
| 2023 | 43,776 | 0.857 | 0.932 | 0 | 0 |
| 2024 | 44,891 | 0.850 | 0.925 | 0 | 0 |

FY2024 by STATUS (exact-match rate): correct 0.895 (27,055 cases), over
0.778 (10,734), under 0.786 (7,102). Sign consistency: over-issuances have
RAWBEN > FSBEN in 94.2% (10,113/10,734); under-issuances have RAWBEN <
FSBEN in 96.0% (6,820/7,102); "correct" cases have RAWBEN == FSBEN in
89.5% (24,208/27,055).

Where the identity breaks, the causes are identifiable:
- **Rounding (±$1):** 3,374 FY2024 cases (7.5%) differ by exactly $1 —
  FSBEN rounds 0.3 × net income, RAWBEN comes from the state's system.
- **Error tolerance:** small discrepancies the reviewer doesn't count as
  errors (AMTERR = 0, STATUS = 1).
- **Non-engine adjustments (~10% of "correct" cases):** 2,847 FY2024
  STATUS=1 cases have RAWBEN ≠ FSBEN with *no recorded variance* and
  AMTERR = 0 — including 1,158 differing by more than $60, spread across
  states. These are not eligibility-engine outputs; the likely cause is
  post-certification adjustments such as claim recoupment (benefit reduced
  to collect a prior overissuance), which the reviewer correctly does not
  code as a certification error.
- **Reporting anomalies (rare):** e.g. one Guam case with RAWBEN = 7,075,
  FSBEN = 163, AMTERR = 544 — RAWBEN far outside any benefit formula.
  A handful per file.

Distributions (FY2024): RAWBEN mean $361 / median $291 / max $7,075
(codebook range 0–7,075); FSBEN mean $355 / median $291 / max $3,923
(codebook range 1–3,923). A few RAWBEN = 0 per file (2–7 cases).

State identifier: `STATE` (FIPS-style codes; PA = 42) in all five files,
plus `STATENAME` ("Pennsylvania" for all 814 FY2024 PA cases — coding is
clean). PA case counts: 2020: 631, 2021: 189, 2022: 817, 2023: 817, 2024:
814 — **3,268 PA cases total**. PA FY2024 identity check: exact 0.840;
STATUS=1 with RAWBEN == FSBEN 0.899 — consistent with national.

## Verdict
**RAWBEN is usable as the agency-computed benefit for rules recovery,
with filters.** The codebook definitions, the 85%/92% identity match, and
the 94–96% sign consistency all confirm RAWBEN is what the state's system
issued and FSBEN is what it should have issued. But ~10% of "correct"
cases carry non-engine adjustments (recoupment-type), and a few cases are
reporting anomalies — so exp8b must fit on a cleaned observation set:
- **Keep:** STATUS=1 with RAWBEN == FSBEN (agency computed correctly;
  89.5% of correct cases), plus STATUS 2/3 where RAWBEN = FSBEN ± AMTERR
  (agency computed from wrong inputs — still engine behavior).
- **Drop:** STATUS=1 with RAWBEN ≠ FSBEN and no variance (not an engine
  output); cases where |FSBEN − RAWBEN| wildly exceeds AMTERR (reporting
  anomalies); tolerate ±$1 as rounding.

## Next steps
1. (Recommended) **Exp8b — parameter fitting on PA:** fit effective
   engine parameters (shelter cap, SUA tiers, income disregards, minimum
   benefit) from (facts → RAWBEN) on the cleaned PA set (3,268 cases),
   then compare fitted values against statute/PA policy docs to flag
   deviations.
2. Decide the tolerance handling for near-misses: exclude |diff| ≤ $1 or
   model rounding explicitly.
3. Check whether the recoupment-type cases (STATUS=1, RAWBEN < FSBEN, no
   variance) are identifiable from other columns — if so they become a
   useful auxiliary label rather than just dropped rows.
