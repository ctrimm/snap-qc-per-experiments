## Experiment 116 — Black-box formula recovery: from synthetic cases to the exact formula, then to weights
**Date:** 2026-11-03 · **Code:** `experiments/exp116_formula_recovery.py` (recovery/compiler), `experiments/exp116b_qc_audit.py` (real-data scoping)

### Hypothesis

The benefit calculator in `src/synth/benefit.py` can be treated the way an
auditor treats a state eligibility system: a black box that takes household
facts and returns a payment. Claim: from query access alone (facts in,
integer benefit out; no code, no parameter file), the calculator's exact
parameters and structure can be recovered to the dollar, a planted
parameter defect can be found and priced, and the recovered formula can be
compiled into network weights that reproduce the calculator exactly —
while trained models fit on the same distribution cannot. If this holds
on the harness, the same instrument is a candidate for real systems,
where the "calculator" is a state's implementation and the diff against
the statute is the payment-error surface. Moves gates 1–2 indirectly: it
validates a new use of the generator (as a system under test, not just a
data source) and scopes the real-data version.

### Method

- **Oracle.** `benefit.compute` in a child process, JSON-lines protocol.
  The recovery code never imports `params` or `benefit`; the diff step
  reads `params.py` as the auditor's copy of the statute. 14,379 queries
  per recovery run.
- **Recovery probes.** Max allotments (zero-income queries per size,
  sizes 1–10); minimum benefit (saturating unearned income); standard
  deduction per size (first unearned dollar that moves the benefit);
  benefit rate (exact 1,000-dollar slope span); earned rate (long-run
  slope ratio) plus a structure test — integer-sequence match of the
  smooth `0.2·E` model vs the `floor(0.2·E)` staircase model over 3,000
  points; medical threshold (integer-sequence fit over candidates, and a
  non-senior control); depcare slope at size 8 (adjusted income stays
  positive across the sweep); shelter factor (exact sequence fit on the
  rising segment), shelter cap (plateau level pins a ~$3 window;
  confirmation probes at shifted adjusted incomes disambiguate — a $1
  cap difference moves the continuous benefit $0.30, which crosses an
  integer boundary at most alignments), senior shelter (uncapped check).
- **Arm B (defect).** Same recovery against an oracle with two planted
  stale parameters the recovery cannot see: shelter cap $672 → $638,
  size-3 standard deduction $198 → $183. Diff is taken against the
  statute (`params.py`), as an audit would.
- **Arm C (compiled weights).** The recovered formula compiled to a ReLU
  network in DAG weight form (per household size; senior gating via the
  min-gadget `min(h, BIG·s)`). Two compositions: v1, the pure continuous
  relaxation (earned deduction as `0.2·E`); v2, the earned staircase —
  a discontinuity — computed in code and fed through the input transform
  `E' = (E − floor(E/5)) / 0.8` (earned income enters the net only via
  the `(1 − rate)·E` term). Final floor and minimum benefit also applied
  in code. This follows the rounding-boundary doctrine from the
  weight-space program: continuous parts in weights, discontinuous
  steps in ordinary code.
- **Arm D (trained controls).** 40,000 sampler cases with oracle labels:
  a scaled MLP (64,64) and a histogram gradient-boosting model, honestly
  tuned. Evaluated on 20,000 fresh sampler cases and 20,000 wide-uniform
  probes (deliberately beyond the screened caseload ranges — they test
  the function, not the fit), plus a monotonicity probe (benefit must be
  nonincreasing in unearned income; 300 households × 13 income levels).

### Results

**Arm A — clean recovery is exact.** Every parameter recovered to the
dollar (rates to float precision):

| Parameter | Recovered | Statute |
|---|---|---|
| Max allotments, sizes 1–8 | 291 / 535 / 766 / 973 / 1155 / 1386 / 1532 / 1751 | identical |
| Each additional person | $219 | $219 |
| Standard deduction, sizes 1–8 | 198 / 198 / 198 / 208 / 244 / 279 / 279 / 279 | identical |
| Minimum benefit | $23, sizes 1–2 only | identical |
| Benefit rate | 0.30 | 0.30 |
| Earned deduction | rate 1/5, **floored** (staircase model: 0 mismatches / 3,000; smooth model: 220) | 0.20, floored |
| Medical threshold | $35, senior-only (non-senior sweep flat) | identical |
| Depcare | 1:1, no cap to $1,500 | identical |
| Shelter factor / cap | 0.5 / $672; senior uncapped | identical |

**Arm B — the diff names both defects at full price.** Against the
statute, the recovered table disagrees in exactly two cells: shelter cap
$638 (defect −$34) and size-3 standard deduction $183 (defect −$15).
All other cells exact. One methodological find inside the result: from a
single shelter probe, caps $637 and $638 produce identical integer
output (the $1 output floor swallows a $0.30 benefit difference at that
alignment) — the confirmation probes at shifted incomes are what make
the cap exact, and they are now part of the protocol.

**Arm C — compiled weights reproduce the calculator exactly.** The DAG
weights match the recovered continuous formula to 5.9e-12. End to end
against the oracle (fresh cases, both eval sets):

| Composition | Sampler (20k) exact | Uniform (20k) exact | Max err |
|---|---|---|---|
| v1 relaxation (staircase left in the net's side) | 96.67% | 91.57% | $1 |
| v2 staircase in code | **100%** | **100%** | **$0** |

The v1 residual is precisely the earned staircase: at most $1, only
where the sub-dollar deduction gap crosses the output floor. Moving
that one discontinuity into code closes it completely.

**Arm D — trained controls are approximations, and break a law-implied
property.**

| Model | Sampler mean / max err | Uniform mean / max err | Within $1 (sampler) | Monotonicity violations |
|---|---|---|---|---|
| MLP (scaled, 64×64) | $5.81 / $71.99 | $235.47 / $1,019.61 | 22.2% | 261 / 3,900 (6.7%) |
| GBM (hist, 300 iters) | $6.01 / $158.22 | $262.31 / $1,185.14 | 27.7% | 350 / 3,900 (9.0%) |

The uniform column is extrapolation beyond any real caseload and is
reported as a function test, not a fit failure. The on-distribution
numbers are the fair comparison, and they are still ~$6 average error
with three-figure worst cases and routine monotonicity breaks — the
same trained-vs-compiled gap the weight-space program found on the
statutory formulas, now reproduced inside this repo's own harness.

**Arm 52b — the real file has what recovery needs.** FY2024 QC
public-use file (44,891 cases): the reported issued benefit (`RAWBEN`),
the QC minimodel's calculated benefit (`FSBEN`), and the corrected
benefit (`BENFIX`) are all present at case level, as are the minimodel's
deduction fields (`FSSTDDED`, `FSERNDED`, `FSSLTDED`, `FSMEDDED`,
`FSDEPDED`, …). `BENFIX ≠ FSBEN` in 6,890 cases (15.3%), mean correction
$67.04 — the case-level error signal exists in public data. (Correction,
2026-11-03, from exp117's tech-doc check: the original draft of this
section mislabeled `FSBEN` as the issued benefit. `RAWBEN` is the
issued/reported benefit; `FSBEN` is calculated by the QC minimodel,
which is why the envelope check below tracked the statute so cleanly.
Exp117 runs the full three-way comparison.) In the size-1 / no-earnings slice (23,331 cases), the statutory
lower envelope behaves as theory requires: at unearned ≤ $198 the
median and 10th-percentile benefit are both exactly $291 (the full
allotment); in higher bins only 0.07–1.4% of cases fall below their
own statutory line (candidate under-issuances or data quirks), with
shelter and other deductions pushing the rest above it.

### Verdict

Hypothesis holds on the harness, completely: blind recovery is exact,
planted defects are found and priced to the dollar, and the recovered
formula compiles to weights that are the calculator (100% agreement,
max error $0), at a total cost of ~29k oracle queries across both arms.
The recovery instrument is calibrated. The trained controls replicate
the known result — fit is not the formula, and property violations are
where that shows.

### Next steps

- **exp117 (done): real-data slice recovery.** Fit the recovery
  protocol to the FY2024 QC file for one dense slice (size 1, no
  earnings, by state group where counts allow): recover the issued
  function's effective standard deduction and rate from `FSBEN`, and
  the corrected function's from `BENFIX`, and diff. The `FS*DED`
  columns let the protocol condition on the agency's own deductions
  instead of treating them as noise.
- exp118 (proposed): apply the recovery to state-conditioned generators
  (`pa_state.py` et al.) as additional systems under test — do their
  effective parameters match their documented state rules?
- Open question for the chronicle record: recovery assumed query access.
  Real systems give samples, not queries; the sample-based version
  (kink estimation from caseload-density data) is the harder instrument
  and the honest sequel if exp117's slices are too thin.

## Repository note (2026-11-03)

This experiment lives in two repositories: **ctrimm/snap-qc-per-experiments**
(`experiments/`, the canonical home — the generator it runs against is
`src/synth/` here) and **ctrimm/weight-space-programming** (`experiments/`,
mirrored with the generator files under `src/synth/` so it also runs
standalone there), because it extends that repo's compiled-weights program
to formula recovery. It was drafted in a stale sandbox snapshot of this
repo under the numbers exp52/exp53 and renumbered to exp116/exp117 on
arrival: the canonical series already runs to exp115, and its own
exp52/exp53 are the GRPO and classifier experiments. If you extend this
line (exp118+), work here in snap-qc-per-experiments and re-mirror to
weight-space-programming, or update both copies — and read this chronicle
and exp117's first.
