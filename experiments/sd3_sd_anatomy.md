# Experiment SD3: South Dakota SNAP QC error anatomy

**Date:** 2026-10-03 · **Code:** `experiments/sd3_sd_anatomy.py`
(results: `/tmp/sd3out/anatomy.json`)

## Hypothesis

Tied to the north star (a copilot that directs reviewer attention to the
right failure modes): PA's fingerprint was deduction-construction
(shelter-heavy), NY's was timing (nature 97 at 1.56x national, medical
1.79x). SD8c proved SD's benefit engine is the cleanest of the three
states (99.0–100.0% output-side exact match), so SD3 should find a
process-layer fingerprint — but which one? This experiment compares SD
(STATE=46, n=2,365 pooled; 607 error rows) against national across
FY2020–2024: finding mix, direction mix, dollar-error quantiles,
element/nature/cause mixes with SD-vs-national ratios, top patterns in
plain language, and FY trends. All rates FYWGT-weighted.

## Method

Microdata-only, read-only on `snap-qc-data/raw` (beside the repo checkout). Primary
variance slot (ELEMENT1/NATURE1/AGENCY1); all-slots element-bucket mix for
the ratio table. "National" = all non-SD rows pooled FY2020–2024.

## Results

**One-line characterization: SD is a timing/reporting story — "not
required to be reported or acted upon."** When SD errs, it is
overwhelmingly about household changes that fell inside reporting
time-frames: nature 97 ("not required to be reported or acted upon") is
74.9% of SD variances at **1.89x national** — the most timing-heavy
fingerprint of the three states (NY 62% at 1.56x, PA lower).

- **Finding mix:** correct/over/under 0.7525/0.1229/0.1245 — SD errs far
  less than national (0.6138/0.2376/0.1485).
- **Direction:** nearly balanced, 49.7% over / 50.3% under (national
  61.5/38.5 over-heavy) — and balanced in *every* FY (0.45–0.53 over).
  SD's errors don't systematically favor the program or the household.
- **Dollars:** small. |AMTERR| p50 $17 (national $28), p90 $70 ($186),
  mean $34 ($66); over-errors median $18, under-errors $16. 88.6% of
  errors ≤$56.
- **Element buckets (SD vs national ratios):** earned **1.45x**, medical
  **1.40x** above; shelter 0.78x, sua 0.68x, hhcomp 0.23x, depcare 0.50x
  below; unearned 0.96x near national. **Arithmetic 0.00x — SD records
  zero arithmetic/computation variances in five years**, corroborating
  SD8c's clean engine from the other direction. (assets 14.2x is tiny-n
  noise; "other" 2.17x is small-n.)
- **Nature:** after 97 (1.89x), the substantive natures all run *below*
  national: 53 (0.27x), 37 (0.18x), 35 (0.39x), 52 (0.54x), 38 (0.60x).
  SD's non-timing errors are a thin, honest tail — no single substantive
  failure mode dominates.
- **Cause:** SD codes causes specifically and honestly (cause-99
  "unknown" 0.08x national — no PA-style 99 distortion). no-fault/26 at
  4.03x, agency causes 10 (2.15x), 20 (4.55x), 22 (3.34x), 14 (1.83x)
  above; client causes 1 (0.38x), 2 (0.35x) below. On substantive
  variances SD's story is "agency-caused" (0.81 of non-97 causes); on
  timing-97s the recorded causes are 100% no-fault — with 87.1% of 97
  causes blanked.
- **Top patterns (plain language):** (1) wages × timing-97, 27.8% of SD
  error weight (2.59x national), median error $20, split over/under;
  (2) shelter deduction × timing-97, 21.3% (1.29x), median $9, skews
  under; (3) RSDI/unearned × timing-97, 16.9% (2.01x), median $15, skews
  over; (4) wages × "more income than budgeted" (nature 38), 4.2%,
  median $57 — the largest typical substantive error; (5) medical ×
  timing-97, 3.9% (2.44x), median $15.
- **FY trend:** microdata case-error rate rises 21.7% → 18.3% → 24.8% →
  28.2% → 30.6% (FY2020–2024) — note this is the microdata basis, not
  FNS's 3.28% FY2024 published payment rate (same published-vs-microdata
  divergence as PA/NY). Direction stays balanced every year. **Coding-
  practice shift in FY2024:** no-fault (cause 26) jumps to 0.58 of
  causes vs ~0.00 in FY2020–2023 — SD started coding timing variances
  no-fault in FY2024 (previously agency-coded). SD6 should watch whether
  the FY2024 mix shift breaks temporal stability.
- **Coding-practice notes:** cause-99 distortion absent (0.08x); no
  non-codebook nature codes of note (nature 111 appears at 1.91x but
  tiny-n); arithmetic variances entirely absent.

## Verdict

**Held.** SD's fingerprint is process-layer (timing/verification), not
computation-layer: 74.9% timing variances at 1.89x national, zero
arithmetic errors in five years, a 99.0–100.0% clean engine (SD8c), and
small, direction-balanced dollar errors. The copilot attention order for
SD: (1) reported-change timing workflows on wages/shelter/RSDI, (2)
medical-expense timing, (3) the small substantive tail (unreported/more
income than budgeted). The ratios table is the calibration spec for
future generator work (already consumed by SD1) and the whitepaper's
anatomy paragraph.

## Next steps

- SD4/SD5 ranker features should lean on timing-adjacent signals
  (earned-income presence, shelter/SUA status, senior/disabled medical)
  rather than computation signals — SD7's feature audit will confirm.
- SD6 temporal stability: watch the FY2024 no-fault coding shift — a
  refit on 2020–22 tested on 2023–24 straddles the shift.
- The FY2020→2024 microdata error-rate rise (21.7%→30.6%) vs the flat
  3.28% published payment rate is a documented basis divergence, not an
  SD program deterioration claim — the whitepaper must carry the same
  caveat PA/NY carried.
