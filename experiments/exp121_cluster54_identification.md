## Experiment 121 — The +$54 minimodel cluster is the homeless shelter deduction, recorded in a different field
**Date:** 2026-11-03 · **Code:** `experiments/exp121_cluster54_identification.py` · **Results:** `experiments/exp121_results.json`

### Hypothesis

exp117/exp118's reconstruction of the QC minimodel (`FSBEN`) is exact
except for a thin residual tail whose modal value is exactly +$54
(28 no-earnings cases, 9 earnings cases): the minimodel pays $54 more
than the statutory formula predicts from the case's own verified
inputs and `FS*DED` fields. Since $54 = 0.30 × $180, the standing
hypothesis was a $180 deduction the formula does not see. This
experiment hunts the shared trait directly rather than guessing:
rebuild both frames, isolate the cluster, scan the file's columns for
a diverging value, then verify by re-scoring with the candidate fix.

### Method

Pooled frame (mainland+DC, sizes 1–4, non-CAP, complete, earnings and
no-earnings: 39,262 cases), prediction recomputed exactly as in
exp117/exp118, cluster = `FSBEN` − prediction = $54 exactly (n = 37).
Scan: every column with 2–40 distinct values in the frame, scored by
the largest cluster-vs-baseline share lift. Then the confirmatory
test the scan points to, applied to the whole frame.

### Results

- **The scan's structural hits are unambiguous.** Every one of the 37
  cluster cases has `FSSLTDED` = 0 (baseline: 34% zero), zero
  dependent-care and child-support deductions, and — the tell —
  `SHELDED` = 180 and `HOMELESS_DED` = 180. The file carries the
  homeless shelter deduction as its own field, and in these cases the
  `FS*DED` shelter field the earlier experiments read is 0 while the
  minimodel's own shelter deduction is the $180 homeless amount.
  $180 × 0.30 = $54, to the dollar, with no rounding slack — which is
  why the cluster is exactly +$54 in every case rather than smeared.
- **It is not only the cluster.** 78 frame cases carry
  `HOMELESS_DED` = 180. Their residuals before the fix: 37 at +$54,
  31 at $0 (the deduction does not bind — net income already ≤ 0, so
  one more deduction changes nothing), and 10 in a partial-binding
  tail (+$2…+$53) where the deduction binds only in part through the
  max(0, ·) and minimum-benefit steps.
- **Verification closes it.** Adding `HOMELESS_DED` to the shelter
  deduction and re-scoring the whole pooled frame: exact
  reconstruction of the minimodel rises from 99.86% to **99.98%**,
  and the +$54 residual disappears entirely (0 cases remain). The
  remaining 0.02% is the unrelated thin tail exp117/exp118 already
  recorded.
- Geography and composition of the cluster, for the record: sizes
  1–3 only (27/7/3), spread across states (MA 10, UT 9, CO 5, MO 4,
  OR 3, ME 2, others) — a national parameter treatment, not a state
  quirk.

### Verdict

Identified, and it was a field-semantics defect in exp117/exp118's
instrument, not a minimodel behavior: for homeless households the QC
minimodel applies the $180 homeless shelter deduction from the
`HOMELESS_DED` field, while the `FSSLTDED` field carries 0 — so any
reconstruction that reads only the `FS*DED` fields under-deducts by
$180 and under-pays by exactly $54 wherever the deduction binds.
exp117/118's headline numbers are unaffected at their stated
precision (the cluster was inside the 0.13–0.15% non-exact tail), but
the corrected reconstruction standard for this file is: shelter
deduction := `FSSLTDED` + `HOMELESS_DED`. With that, mainland
minimodel reconstruction stands at 99.98% on the pooled slice — the
one open reconstruction defect from exp119's next-steps list is
closed.

### Next steps

- None for this defect. Any future reconstruction work on this file
  should use the corrected shelter field from the start.

## Repository note (2026-11-03)

This experiment lives in two repositories: **ctrimm/snap-qc-per-experiments**
(`experiments/`, the canonical home) and **ctrimm/weight-space-programming**
(`experiments/`, mirrored), as part of the formula-recovery line that runs
exp116 → exp117 → exp118/exp119 → exp120–exp122. The QC data it reads is
in neither repo; it lives in the project's snap-qc-data store (FY2024
public-use file). If you extend this line (exp123+), work in
snap-qc-per-experiments and re-mirror to weight-space-programming, or
update both copies.
