# Experiment 5 — Calibration v3: omission-coherence fix
**Date:** 2026-09-28 · **Code:** `experiments/exp5_omission_coherence.py`

## Hypothesis
North star gate: **calibration**. Exp 3b's residual was under-issuances stuck
at 9.4% vs 15.8% real. We hypothesized the shortfall was incoherent
omissions: the sampler draws the truth first and the variance independently,
so an "agency omitted X" variance drawn on a household whose truth had no X
no-op'd — the retry loop silently dropped it. Real QC data shows this pattern
is common: 222 FY2024 under-issuance cases carry a shelter variance with
agency-view shelter = $0 (the truth had shelter costs the agency missed).

## Method
- On a zero base, omission-type natures now **correct the truth upward** (the
  truth gains the omitted amount; the agency view stays at the omitted value)
  instead of no-op'ing. Omission types: income 35/37/38, deduction 52/57.
- Commission-type natures keep corrupting the agency view (44: agency counted
  income that wasn't there; 53: agency claimed a deduction that doesn't
  exist).
- Compared 20,000 synthetic cases (retry budget 12) against exp 3b
  (70.2/20.4/9.4) and the real file (60.3/23.9/15.8).

## Results
| Mix (correct / over / under) | correct | over | under | L1 vs real |
|---|---|---|---|---|
| Real FY2024 | 0.603 | 0.239 | 0.158 | — |
| Exp 3b | 0.702 | 0.204 | 0.094 | 0.191 |
| **Exp 5** | **0.698** | **0.193** | **0.109** | **0.191** |

Realized error rate: 0.302 (real: 0.397).

## Verdict
Hypothesis **partially held** — the mechanism is real (under-issuances moved
9.4% → 10.9% in the right direction), but the fix was too small to close the
gap. The deeper problem is not just zero-base incoherence but the injection
policy itself: a flat injection rate ignores that real error risk is
strongly conditioned on household features (earnings status most of all).
L1 stayed at 0.191. This experiment's real contribution was diagnostic: it
showed the calibration problem is in *who gets errors*, not just *how errors
materialize* — which motivated exp 6's eligibility-screen redesign.

## Next steps
1. (Recommended) Condition injection on earners vs non-earners: measure
   P(error | earner) and P(bucket | earner) from the real file, inject
   accordingly (→ exp 6).
2. Calibrate the injection coin against the *realized* post-retry error rate
   per stratum, not the injection-time rate — the retry loop's attrition is
   stratum-dependent (→ the inject.json phase-1 calibration).
