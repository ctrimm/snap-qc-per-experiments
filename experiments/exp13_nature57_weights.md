# Experiment 13: per-nature importance weights for the 57 residual

## Hypothesis
North-star gate: calibration. Nature 57 ("incorrect deduction amount
included — budgeted too little") sits at 0.50x because its materialization
rate m_{b,57} is low in the persistent flow: drawn 57s often fail to produce
a recorded variance. Importance weights w_{b,57} ∝ 1/m_{b,57}, with m
measured under true hybrid (persistent) conditions, will move 57 toward
~1.0x without regressing the finding mix.

## Method
1. Measured m_{b,57} = P(recorded 57 | drawn 57) by bucket in the persistent
   flow (20k, seed 7, hooked `_draw_nature`): medical 0.279, shelter 0.474,
   earned 0.500, depcare 1.000.
2. Added `_NATURE_57_WEIGHT = {medical: 3.58, shelter: 2.11, earned: 2.00}`
   (1/m) applied to the nature draw in `_draw_nature`.
3. First pass overshot to 1.29x (upweighting the draw shifts the
   materialization dynamics — the exp7 note about non-transfer was right).
   Scaled weights by 0.8 → 1.04x.

## Results
- Nature 57: 0.50x → **1.04x** (synth P(57|variance)=0.0358 vs real 0.0345).
- Finding L1: baseline 0.031, persistent 0.042 (stable; was 0.026/0.045).

## Verdict
**Held.** The 1/m importance-weight mechanism works when m is measured in
the actual (persistent) flow. The 0.8 damping factor confirms the
materialization rate is not invariant to the draw weights — a second
iteration would be needed for exact convergence, but 1.04x is within noise.

## Next steps
1. Exp14: SUA mechanics rework — though sua is at 0.99x, so re-scope to
   whether the 57-weight approach generalizes to other underproduced natures.
   - **Done →** [exp14](exp14_materialization_correction.md): Run as the bucket materialization correction (re-scoped).
2. The damping-factor finding (0.8) suggests a general principle: draw-weight
   corrections need one empirical iteration, not analytic 1/m.
