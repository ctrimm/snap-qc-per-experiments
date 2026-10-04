# Experiment UT8c: Utah benefit-engine cleanliness

**Date:** 2026-10-04 · **Code:**
`experiments/ut8c_ut_engine_cleanliness.py` (read-only on the microdata;
prints to stdout, no repo writes)

## Hypothesis

Tied to the north star: the POC story attributes QC errors to the human
process layer (certification, verification, reporting). That attribution
only holds if Utah's benefit engine — the statutory formula mapping
reported facts to the issued allotment — matches federal statute. If the
engine deviates, "errors" could be systematic misconfigurations, and the
whole track's premise changes.

## Method

Replicates exp8b's national parameter-fitting machinery restricted to Utah
(STATE=49, FY2020–2024) vs (a) the national fleet fitted the same way and
(b) published federal statute per fiscal year. Fits use only clean-engine
rows (STATUS=1, RAWBEN==FSBEN, SSI_CAP==0, housed — reported fields are
the engine's inputs); error rows are examined descriptively only. Tests:
30% benefit-reduction rate (OLS slope), ceiling rounding, 20% earned-income
disregard, minimum benefit, standard deduction, maximum allotments,
shelter-cap behavior, homeless deduction, SUA application; the exp8b New
England uncapped-shelter anomaly pattern in UT specifically (UT is not one
of the NE-six states — dropped SD/46 from that list); and an output-side
holdout (statutory formula predicted on UT clean-engine rows per FY).

## Results

**Parameter table (UT vs statute, per FY):** the 30% rate fits at
0.3001–0.3002 every FY (statute 0.3000); the 20% earned-income disregard at
0.2000 every FY; minimum benefit, standard deduction, and maximum
allotments match statute exactly in all five FYs; ceiling rounding exact
on 90–98% of rows (fleet: 96–97%). No parameter deviates by more than $1
for any non-trivial share of cases — inside exp8b's materiality bar.

**Shelter cap:** UT non-elderly above-cap share 0.000 in all five FYs
(max SHELDED exactly at the cap) — zero uncapped-shelter cases. The exp8b
New England anomaly pattern is absent in UT (the fleet shows 1.0–1.8%
above-cap; UT shows none).

**Output-side holdout** (statutory formula on UT clean-engine rows):
FY2020 99.18% exact, FY2021 95.58%, FY2022 97.63%, FY2023 97.35%, FY2024
98.66% — within-$1 at 99.35–100% every FY, at or above the fleet's
97.4–98.5% exact. No recording artifact of the NY kind (NY's FY2020–21
RAWNET==RAWGROSS rows); UT's worst FY (2021, 95.58%) is the thin
partial-year file (n=113 clean-engine rows), not a systematic deviation.

**SUA spot-check:** no SUA-style round point mass in UT FY2024 SHELDED
(no $31 telephone-SUA mass); nothing to flag.

## Verdict

**PASS — the engine is clean.** Every fitted parameter matches statute
within the $1 materiality bar, the shelter cap is respected exactly, and
the output-side holdout predicts RAWBEN at 95.6–99.2% exact per FY. UT's
QC errors live in the human process layer (verification, reporting,
timing) — consistent with UT3's anatomy (wage timing, shelter-deduction
verification, client-coded). The POC premise holds: the copilot
prioritizes human review; it does not second-guess the benefit math.

## Next steps

- The whitepaper's "The problem" section cites the holdout exact-match
  range (95.6–99.2% per FY) vs the fleet.
- No engine work needed anywhere downstream; UT1–UT8 proceed on the
  process-layer premise.
