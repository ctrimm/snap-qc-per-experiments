## Experiment 117 — Real-data slice recovery: the issued function's parameters are the statutory parameters
**Date:** 2026-11-03 · **Code:** `experiments/exp117_real_slice_recovery.py` · **Results:** `experiments/exp117_results.json`

### Hypothesis

Exp116 calibrated a black-box recovery instrument on the synth harness.
This experiment points it at real data. Slice of the FY2024 QC public-use
file where recovery is feasible from samples: household sizes 1–4, no
earnings, mainland states + DC (AK/HI/GU/VI use their own allotment
tables), excluding SSI-CAP cases: 29,641 cases (29,572 with complete
fields). Claim, stated to be wrong-able: the formula that reproduces the
QC minimodel (`FSBEN`) from verified inputs will also recover the
*issued* function's (`RAWBEN`) effective parameters, and if agencies
systematically run shifted parameters, the fit against `RAWBEN` will
return different values than the fit against `FSBEN`.

Variable semantics per the FY2024 tech doc (Mathematica): `RAWBEN` =
reported benefit the unit received; `FSBEN` = benefit calculated by the
QC minimodel from QC-verified data; `BENFIX` = `FSBEN` adjusted for
errors the QC reviewer found; `FS*DED` = the minimodel's calculated
deductions from the verified data. (This corrects exp116b, which mislabeled
`FSBEN` as the issued benefit; the issued benefit is `RAWBEN`.)

### Method

- Statutory prediction per case: FY2024 allotment by size, minus 0.30 ×
  net, net = max(0, unearned − the case's own `FS*DED` total), minimum
  benefit $23 (sizes 1–2), floored — the exp116 formula.
- T1: prediction vs `FSBEN` (does the formula + fields reconstruct the
  minimodel?). T2: vs `BENFIX`. T3: vs `RAWBEN`, with residual anatomy
  and a per-state breakdown.
- Effective-parameter fit on the no-other-deductions sub-slice (10,315
  cases; only the standard deduction in play): grid over the standard
  deduction ($120–280) at rate 0.30, then over the rate (0.24–0.36) at
  the best deduction, maximizing exact-match share. Run against all
  three targets; `FSBEN` is the control.

### Results

| Test | Exact agreement | Weighted | Reading |
|---|---|---|---|
| T1 pred vs FSBEN (minimodel) | **99.87%** | 99.87% | formula + fields = the minimodel |
| T2 pred vs BENFIX (corrected) | 86.70% | 85.08% | reviewer adjustments move 13.2% of cases |
| T3 pred vs RAWBEN (issued) | **61.61%** | 59.52% | the agency error surface, this slice |

- T1's 38 mismatches include a +$54 cluster (28 cases) — a fingerprint
  of one treatment the formula here does not capture; unexplained, left
  on the record. Under mainland parameters the territory cases score
  0.0% exact, as expected: same formula shape, different tables (their
  recovery is a parameter problem of exactly the exp116 kind).
- `FSBEN` vs `BENFIX` differ in 13.2% of slice cases, mean adjustment
  $58.10 where they differ — but the modal `BENFIX` residual against the
  prediction is exactly −$1 (1,576 cases). By count, reviewer
  corrections are dominated by very small errors; by dollars, they are
  not.
- T3 residuals are nearly symmetric (18.7% of cases issued above the
  prediction, 19.8% below), modal residuals −$1 (743), +$1 (416), −$3,
  +$2, −$10: many small deviations, both directions. Per-state exact
  share ranges from 49.9% (Virginia, n=511) to 72.5% (Wisconsin, n=670).
- **Parameter fits:**

| Target | Std deduction fit | Rate fit | Match at fit |
|---|---|---|---|
| FSBEN (control) | $198 | 0.30 | 97.1% |
| BENFIX | $198 | 0.30 | 88.7% |
| RAWBEN (issued) | **$198** | **0.30** | 77.1% |

### Verdict

The hypothesis's interesting half fails, and the failure is the finding:
**on this slice, the issued function runs the statutory parameters.**
The control fit returns $198 / 0.30 against the minimodel, and the same
values come back against the issued benefits — no shifted deduction, no
drifted rate. The 38-point gap between what the minimodel computes from
verified facts and what households were actually issued is case-level
variance: wrong facts or misapplied deductions on individual cases,
small in modal size, symmetric in direction, varying by state. Payment
error here is a fact-finding and deduction-application problem, not a
formula-configuration problem.

Scope limits, stated plainly: sizes 1–4 with no earnings (the earnings
staircase and wage verification may behave differently); deduction
amounts are conditioned on the minimodel's own calculated fields, so
agency deduction errors appear inside T3's residuals rather than as
parameter shifts; FY2024 only; unweighted shares are sample shares
(weighted shares reported alongside and close).

### Next steps

- exp118 (proposed): extend the frame to earnings cases (FSEARN > 0) — recover the
  effective earned-income treatment from `RAWBEN` (rate and staircase
  vs smooth), the one parameter family this slice could not see.
- exp119 (proposed): territory tables (AK/HI/GU/VI) recovered from their own slices
  the same way — pure parameter recovery against a different table.
- The +$54 T1 cluster (28 cases): identify the shared trait before any
  broader claim about the minimodel reconstruction.

### Relation to exp8b

exp8b fit national effective parameters from this file and found the
statute ($198-class parameters, 0.30 rate). exp117 confirms that
result with an exact instrument on a defined slice — reconstruct the
minimodel first (99.87%), then fit — and exp118/exp119 extend it to
earnings cases and the territories.

## Repository note (2026-11-03)

This experiment lives in two repositories: **ctrimm/snap-qc-per-experiments**
(`experiments/`, the canonical home) and **ctrimm/weight-space-programming**
(`experiments/`, mirrored), as the real-data sequel to exp116's recovery
program there. It was drafted in a stale sandbox snapshot of this repo
under the number exp53 and renumbered to exp117 on arrival: the canonical
series already runs to exp115. The QC data it reads is not in either repo;
it lives in the project's snap-qc-data store (FY2024 public-use file,
`qc_pub_fy2024.csv`). If you extend this line (exp118+), work here in
snap-qc-per-experiments and re-mirror, or update both copies.
