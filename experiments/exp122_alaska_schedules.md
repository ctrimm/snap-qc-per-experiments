## Experiment 122 — Alaska schedule assignment was in the file all along: BENMAX is the fingerprint
**Date:** 2026-11-03 · **Code:** `experiments/exp122_alaska_schedules.py` · **Results:** `experiments/exp122_results.json`

### Hypothesis

exp119 recovered Alaska's three allotment schedules (Urban / Rural 1 /
Rural 2) as benefit clusters but could not assign households to
schedules — the fields it used carry no sub-state geography, and the
public file has no community or ZIP. Claim tested here: some field in
the file separates the clusters anyway. Among Alaska size-1 cases
with net income ≤ 0 and no earnings, the minimodel benefit *is* the
schedule's size-1 allotment (374 / 477 / 581), so any column whose
values partition those three outcomes cleanly is an assignment key.

### Method

Alaska frame (sizes 1–8, no earnings, non-CAP, complete; n = 395).
Separation scan over the probe set (size 1, net ≤ 0, n = 133): every
column with 2–25 distinct values, purity = weighted share of cases
sitting at their column-value's modal benefit. Outcome columns
(`BENFIX`, `RAWBEN`, `AMTERR`) excluded — a first pass that left them
in "found" `BENFIX` at 0.99 purity, which is a restatement of the
answer, not a separator. Parameter lookups stay in. Then: assign by
the winner, fit the standard deduction per schedule (grid, rate 0.30,
as in exp119), and reconstruct the full frame, against an honest
single-table control computed on the same cases.

### Results

- **`BENMAX` separates perfectly (purity 1.000).** The file carries
  each case's maximum allotment as a parameter field, and at net ≤ 0
  `BENMAX` equals `FSBEN` for **100%** of cases in the frame. A case's schedule is therefore readable from its own row: the
  schedule whose recovered table value at the case's size equals its
  `BENMAX`. `MINIMUM_BEN` also separates (it is schedule-specific
  too) and is used for the sizes 1–2 minimum in the reconstruction.
- **Schedule shares in the frame:** Urban 321 (81%), Rural 2 64
  (16%), Rural 1 10 (3%) — assignments for all 395 cases, including
  Rural 1 at sizes where exp119 saw no plateau cluster (by
  elimination: `BENMAX` matches neither recovered table).
- **Reconstruction with assignment: 98.0% exact on the full frame**
  (std $338, fitted identically for pooled / Urban / Rural 2). On the
  sizes 1–6 subset where the Urban table is fully observed (n = 389),
  the same-frame comparison is **82.3% single-table → 99.0% with
  assignment** (exp119's 78.4% was the same control on its frame and
  settings). The exp119 Alaska cap was an assignment problem, exactly
  as suspected, and it is now closed.
- **The 8 remaining misses are one narrow shape:** all rural,
  sizes 6/7/9, residuals +$3 (×7) and +$4 (×1) — the minimodel pays
  slightly *more* than the assigned reconstruction, consistent with a
  standard deduction a few dollars higher for large rural households
  than the pooled $338. The rural binding-case sample (n = 18) is too
  thin to pin it; recorded, not resolved.
- **Cross-check that validates exp119 independently:** for Hawaii,
  Guam, and the Virgin Islands, `BENMAX` at net ≤ 0 (sizes 1–4)
  matches exp119's recovered allotment tables at **100.0%** in all
  three territories (96 / 74 / 76 cases). The tables exp119 recovered
  blind, from benefit clusters alone, are confirmed by a parameter
  field that played no part in recovering them.

### Verdict

Assignment found, and it was never geography: the public file encodes
each Alaska household's schedule in its maximum-allotment parameter.
With it, every jurisdiction in the FY2024 file now reconstructs at
97–100%: the recovery map from exp116–119 is complete, and Alaska's
"data limit" from exp119 is retired — the limit was in the field set
the earlier experiments happened to read, not in the file. The
methodological note cuts both ways and is worth keeping: `BENMAX`
would have trivialized exp119's table recovery had it been read
first, which is precisely why the blind recovery is the result and
this experiment is its confirmation.

### Next steps

- The large-rural standard-deduction wobble (8 cases, +$3–4) is the
  only open item, and it needs a bigger Alaska sample (another FY's
  file) more than it needs more method.

## Repository note (2026-11-03)

This experiment lives in two repositories: **ctrimm/snap-qc-per-experiments**
(`experiments/`, the canonical home) and **ctrimm/weight-space-programming**
(`experiments/`, mirrored), as part of the formula-recovery line that runs
exp116 → exp117 → exp118/exp119 → exp120–exp122. The QC data it reads is
in neither repo; it lives in the project's snap-qc-data store (FY2024
public-use file). If you extend this line (exp123+), work in
snap-qc-per-experiments and re-mirror to weight-space-programming, or
update both copies.
