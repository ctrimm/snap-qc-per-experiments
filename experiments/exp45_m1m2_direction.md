# Experiment 45 — M1/M2 direction recalibration for earned

**Date:** 2026-09-29 · **Code:** `experiments/exp45_m1m2_direction.py`

### Hypothesis

Exp27's M1/M2 position-dependent draw mixes are the faithful earned fix
(0.77x → 0.97x) but land finding L1 at 0.037, missing the 0.030 bar —
the residual is entirely the over/under direction split (0.258/0.140 vs
real 0.239/0.158), because M1's earned-richer first variances shift the
direction balance and the direction-balance boosts in `dir_weight` were
calibrated for the marginal draw regime. Re-fitting the direction-balance
boosts — the designated draw-side direction instrument
(`dollar_mech.apply_direction_balance`) — *in the M1/M2 regime* should
recover the split and land finding L1 ≤ 0.030 with earned ≥ 0.90x.

North-star tie: calibration gate. Earned is the largest single variance
bucket in real QC data; the faithful M1/M2 fix is staged behind this
recalibration, and the recalibration must be done in the regime it will
serve (the double-counting bug class: marginal-regime coins carried into
the M1/M2 regime are stale weights).

### Method

**[0] [F4] reproduction on the current tree (harness check).** M1/M2
position-dependent draw mixes measured fresh from the held-out file
(per-stratum first-variance and later-variance bucket mixes; never
trusted from exp27's script), applied via a faithful copy of the current
`errors._inject_persistent` with the single change of position-dependent
mix selection (dollar-mechanism corruptor patches compose through
`errors._apply_one`, so mechanisms stay ON). Plus the phase-1 per-type
coin recalibration in the M1/M2 regime (exp27's [F4] procedure).
Expected starting point: earned ~0.97x, L1 ~0.037, split shifted toward
over. If the reproduction misses badly, the harness is wrong — stop.

**[1] Direction-residual decomposition.** Where does the over-excess live?
Split the (over − target) residual by (bucket × 97/non-97). Expectation:
mostly non-97 earned (natures 37/38) — which says the `dir_weight`
boosts (the non-97 direction instrument) are the right knob. If the
excess is mostly 97s, the 97-resolution coins need the refit instead.

**[2] Direction-balance fit in the M1/M2 regime.** Secant iteration on
20k-case measurements: fit multiplicative corrections (boost_over,
boost_under) applied via `apply_direction_balance` *relative to the
committed dir_weight*, solving for realized (over, under) = (0.239,
0.158). Start (1.0, 1.0); measure sensitivities; solve; clamp to
[0.3, 3.0]; iterate to |o − 0.239| < 0.005 and |u − 0.158| < 0.005 or 4
rounds. The fit is done entirely with M1/M2 active — never fit in one
regime and apply in another.

**[3] Joint validation**, paired seeds 7/8: M1/M2 + refit boosts (+ the
[F4] phase-1 coins). Full bucket table, finding L1, dollar marginals
(share ≤$56, p10/p50/p99). Per exp31's rule: if the draw-regime change
moves the dollar marginals beyond ±0.02/±$2, re-fit the dollar constants
(exp31's procedure); otherwise leave them.

### Results

STAGED — not yet run.

### Verdict

STAGED.

Bars: earned ≥ 0.90x AND finding L1 ≤ 0.030 AND no other bucket
regressing more than 0.10x vs the [F4]-reproduction baseline.

Falsification: if the secant fit hits the [0.3, 3.0] rails or the split
will not move (direction dominated by 97s or by benefit-math structure
rather than draw weights — the stage-[1] decomposition will show it),
the `dir_weight` instrument is insufficient. Then: reject M1/M2 adoption,
report the clean negative, and leave earned at 0.77x pending a different
mechanism. Do not force the fit.

### Next steps

STAGED.

1. If it holds: coordinator adopts M1/M2 (as a draw-regime change in
   `errors.py`, delimited) with the refit boosts folded into
   `dir_weight`; re-fit dollar constants iff [3] says so; re-measure
   anything the maintenance notes tie to the draw regime.
2. If the 97 coins turn out to be the binding instrument (stage [1]):
   refit them via `calibrate_injection.py`'s phase-2 procedure in the
   M1/M2 regime instead.
3. Either way, record the decomposition — it is the first measurement
   of where the direction split lives under M1/M2.

### Files

- `experiments/exp45_m1m2_direction.py` — full pipeline (STAGED).
- `experiments/exp45_m1m2_direction.md` — this chronicle.
