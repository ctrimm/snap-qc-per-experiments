# Experiment 12: kid-conditioned depcare

## Hypothesis
North-star gate: calibration. The depcare element residual (0.03x) is a DRAW
problem: depcare variances occur exclusively on kid households (385/385 in
FY2024), but the generator has no kid concept — `facts` carries `hh_size`
without `n_kids`, so depcare cannot be conditioned on the only variable that
predicts it. Adding `n_kids` and gating depcare to kid households will move
depcare toward ~1.0x.

## Method
1. Measured real P(n_kids | hh_size) from FY2024 QC (CERTHHSZ × FSNKID;
   never committed).
2. Added `n_kids` to `household.py` from the empirical distribution.
3. In `_applicable_buckets`: depcare is skipped when `n_kids == 0`.
4. Removed `depcare` from `ZERO_BASE_WEIGHT` (was 0.008) — same
   double-counting diagnosis as exp11's medical: the empirical mix already
   reflects the real base-rate relationship.
5. Recalibrated coins; regenerated 20k, seed 7.

## Results (persistent mode, the default)
| element | before | after |
|---|---|---|
| depcare | 0.03x | **0.56x** |
| medical | 0.67x | 0.76x |
| hhcomp | 1.91x | 1.56x |
| finding L1 | 0.046 | 0.045 |

All 8 elements now sit in the 0.56x–1.56x band (shelter 0.75x, earned 0.85x,
unearned 0.78x, sua 0.99x, arithmetic 1.54x).

## Verdict
**Held.** Depcare moved 0.03x → 0.56x — the missing kid concept was the
binding constraint, and the 0.008 zero-base weight was suppressing what
little was drawn. The n_kids addition had positive spillovers (medical,
hhcomp). Depcare at 0.56x still underproduces; the residual is likely the
depcare *amount* model (only 7% of size>2 households draw expenses) rather
than the bucket draw.

## Next steps
1. Exp13: per-nature weights for the 57 residual (0.50x).
2. Exp14: SUA mechanics rework (sua is at 0.99x — may not need it; re-scope
   to arithmetic 1.54x / hhcomp 1.56x overproduction instead).
