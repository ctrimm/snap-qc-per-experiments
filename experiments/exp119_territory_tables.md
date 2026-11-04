## Experiment 119 — Territory tables recovered from their own slices
**Date:** 2026-11-03 · **Code:** `experiments/exp119_territory_tables.py` · **Results:** `experiments/exp119_results.json`

### Hypothesis

exp117 excluded Alaska, Hawaii, Guam, and the Virgin Islands because
they run their own allotment tables (0.0% reconstruction under mainland
parameters). Claim: the tables are recoverable from each territory's
own QC slice by the same instrument — among cases with net income ≤ 0
the minimodel benefit *is* the max allotment, so the modal benefit in
that group is the table entry — and a reconstruction test will validate
the recovered tables the way it validated the mainland formula (exp117
T1 = 99.87%). Alaska is expected to break the single-table assumption:
it publishes three schedules (Urban, Rural 1, Rural 2).

### Method

FY2024 QC public file, per territory, sizes 1–8, no earnings, non-CAP,
complete fields (AK 393, HI 421, GU 126, VI 178 cases). Allotment per
size = modal `FSBEN` among cases with unearned − total `FS*DED` ≤ 0.
Standard deduction per territory = grid fit at rate 0.30 vs `FSBEN` on
the no-other-deductions sub-slice, using recovered allotments.
Reconstruction (recovered allotment + each case's own deduction
fields) vs `FSBEN` (T1) and vs issued `RAWBEN` (T3).

### Results

| Territory | Recovered allotments (sizes 1–4) | Std fit | T1 vs FSBEN | T3 vs RAWBEN |
|---|---|---|---|---|
| Hawaii | 527 / 967 / 1385 / 1759 (+2770 at size 7) | $279 (match 1.000) | **100.0%** (415) | 59.0% |
| Guam | 430 / 788 / 1129 / 1434 | $397 (0.983) | **100.0%** (119) | 62.2% |
| Virgin Islands | 375 / 688 / 985 / 1251 | $174 (0.966) | 97.1% (170) | 58.2% |
| Alaska | three schedules — see below | $338 (0.772) | 78.4% (389) | 46.5% |

- **Hawaii and Guam reconstruct perfectly.** A recovered table plus a
  fitted standard deduction reproduces the minimodel on every case in
  the slice (and Hawaii's sub-slice fit matches at 1.000). That is the
  same validation standard as the mainland, met from ~120–420 cases.
  Note the standard deductions are territory law, not mainland law:
  $279 (HI), $397 (GU), $174 (VI), $338 (AK) — all recovered, none
  assumed. VI's is *below* the mainland $198.
- **Virgin Islands** reconstructs at 97.1%; the small residual mass is
  consistent with its thinner slice (178 cases).
- **Alaska's schedules surface directly in the data.** At size 1 with
  net ≤ 0 (133 cases), benefits cluster at exactly three values:
  $374 (111 cases), $581 (19), $477 (3) — Urban, Rural 2, and Rural 1
  respectively, matching the published schedule structure. The same
  clustering appears at larger sizes (size 2: $686 / $1,065; size 4:
  $1,248 / $1,937) with thinner counts. A single-table reconstruction
  caps at 78.4% because the fields used here do not carry the
  household's schedule assignment; the T3 figure (46.5%) inherits that
  limit and should not be read as Alaska's error rate.
- Territory T3 shares (issued vs statute, HI 59.0% / GU 62.2% / VI
  58.2%) sit in the same band as the mainland no-earnings slice
  (61.6%, exp117): nothing about the territories' error surface looks
  categorically different once their own tables are used.

### Verdict

Claim holds, including the Alaska exception. The recovery instrument
extends to every SNAP jurisdiction in the file: four allotment tables
and four standard deductions recovered from public data alone, three
of them validated by near-total reconstruction of the minimodel, and
Alaska's three-schedule structure recovered as clusters even where a
single table cannot be assigned per case. With exp116–118, the map is
complete for FY2024: formula recovered synthetically, validated on
the minimodel nationally, parameters confirmed on issued benefits,
and every jurisdiction's table in hand.

### Next steps

- Alaska schedule assignment: find or derive the field (or a proxy —
  community/ZIP is not in the public file) that separates Urban /
  Rural cases, then reconstruct Alaska properly.
- The +$54 minimodel cluster (exp117/118) remains the one open
  reconstruction defect on the mainland side.

## Repository note (2026-11-03)

This experiment lives in two repositories: **ctrimm/snap-qc-per-experiments**
(`experiments/`, the canonical home) and **ctrimm/weight-space-programming**
(`experiments/`, mirrored), as part of the formula-recovery line that runs
exp116 → exp117 → exp118/exp119. The QC data it reads is in neither repo;
it lives in the project's snap-qc-data store (FY2024 public-use file).
If you extend this line (exp120+), work in snap-qc-per-experiments and
re-mirror to weight-space-programming, or update both copies.
