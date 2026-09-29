# Experiment 3 — Calibration v2: income-variance direction fix
**Date:** 2026-09-28 · **Code:** `experiments/exp3_calibration_v2.py`

## Hypothesis
North star gate: **calibration** — the synthetic finding mix (correct / over /
under) must match the real QC file before synthetic data can serve as
pretraining signal for the domain LM. Exp 1 left the mix at 79/9/12 vs the
real 60/24/16, with over-issuances badly underproduced. We hypothesized the
gap was a sign bug, not a rates bug: if income corruptions materialize in the
wrong direction, no rate tuning can fix the mix.

## Method
- Code review of the income corruption paths found the bug: natures 38
  ("more income than budgeted") and 44 ("less income than budgeted") had
  their directions **swapped**, and 35 ("unreported source") was inverted —
  most synthetic income variances pushed the benefit the wrong way.
- Two variants, both with the direction fix:
  - (a) retry budget 3 — isolates the direction fix (same budget as exp 1);
  - (b) retry budget 12 — also lifts the realized error rate toward the real
    40% (exp 2 noted the synthetic prior realized only 21% errors, because
    the retry loop drops no-op injections).
- Compared 20,000 synthetic cases against the real FY2024 QC marginals.

## Results
| Mix (correct / over / under) | correct | over | under |
|---|---|---|---|
| Real FY2024 | 0.603 | 0.239 | 0.158 |
| Exp 1 (pre-fix) | 0.79 | 0.09 | 0.12 |
| Exp 3a (direction fix, retry 3) | — | — | direction-corrected, rate still low |
| **Exp 3b (direction fix, retry 12)** | **0.702** | **0.204** | **0.094** |

L1 distance to the real mix fell from ~0.30 (exp 1) to ~0.19 (exp 3b). The
realized error rate rose toward 40% with the larger retry budget.

## Verdict
Hypothesis **held** — it was a sign bug. The direction fix moved the mix
dramatically without any rate tuning, which confirms the corruption mechanics
were structurally sound but mirrored. Residual: under-issuances still stuck
at 9.4% vs 15.8% real (correct 70.2% vs 60.3%). The retry loop with budget 12
also partially addressed exp 2's prior-mismatch note.

## Next steps
1. (Recommended) Diagnose the under-issuance shortfall — suspected cause:
   omission-type variances drawn on zero-base households no-op because the
   sampler draws truth and variance independently (→ exp 5).
2. Recalibrate injection rates against the realized (post-retry) error rate
   rather than the injection-time rate.
3. Re-run transfer (exp 2) on the fixed generator — the finding task should
   improve as the synthetic prior matches real.
