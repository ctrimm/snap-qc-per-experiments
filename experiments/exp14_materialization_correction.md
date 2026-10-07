# Experiment 14: bucket materialization correction (re-scoped from SUA)

## Hypothesis
North-star gate: calibration. Original scope was SUA mechanics rework, but
sua sits at 0.99x — no rework needed. Re-scoped to the hhcomp (1.56x) and
arithmetic (1.54x) overproduction in persistent mode: the 1/eff_b draw
weighting should land recorded shares exactly on empirical if eff_b equals
the true keep rate. Re-measuring eff_b under the new stratum-conditional
mixes (exp11/12 changed them) should close the residual.

## Method
1. Re-ran `measure_effectiveness.py` with n=8000 (was 4000) under the
   current 4-stratum mixes; hhcomp eff 0.58 → 0.647.
2. Recalibrated injection coins; regenerated 20k, seed 7.
3. Iterated once more (draw weights affect materialization).

## Results (persistent mode)
| metric | before | after 1 iter | after 2 iters |
|---|---|---|---|
| finding L1 | 0.042 | 0.036 | 0.036 |
| hhcomp | 1.56x | 1.59x | 1.59x |
| arithmetic | 1.54x | ~1.5x | ~1.5x |

Finding L1 improved (0.042 → 0.036), but hhcomp/arithmetic did not move.
The iteration does not converge on these buckets.

## Verdict
**Did not hold.** The 1/eff_b correction is theoretically exact but
practically insufficient: eff_b (harmonic-mean feasibility) does not equal
the true keep rate under stratum-conditional mixes. The mismatch is likely
structural — hhcomp/arithmetic corruptions change hh_size or add noise in
ways that interact with the benefit formula non-linearly, so the keep rate
depends on the household composition beyond what a single per-bucket scalar
captures. A per-(bucket, stratum) keep-rate matrix, or modeling the
corruption mechanics directly, would be the next step.

## Next steps
1. Per-(bucket, stratum) materialization matrix instead of the scalar eff_b.
   - **Done →** [exp20](exp20_materialization_matrix.md): Per-(bucket, stratum) matrix built; mechanism works, exposed the zero-base double-count.
2. The remaining calibration residuals (hhcomp 1.59x, arithmetic ~1.5x) are
   now the binding constraints; medical/depcare/57 are resolved.
   - **Done →** [exp21](exp21_zerobase_audit.md): Zero-base audit fixed the residuals: hhcomp 1.59 → 1.11x, arithmetic 1.51 → 1.10x.
