# Experiment 20 — per-(bucket, stratum) materialization matrix
**Date:** 2026-09-29 · **Code:** `experiments/exp20_materialization_matrix.py`

## Hypothesis
North-star gate: calibration. Exp14 re-measured the scalar per-bucket
effectiveness eff_b under the exp11 4-stratum mixes: finding L1 improved
(0.042 → 0.036) but hhcomp/arithmetic stayed ~1.5x over, and iterating the
scalar did not converge. Exp14's verdict: the keep rate — the fraction of
drawn variances that actually move the benefit and get recorded — varies by
household stratum, so no single per-bucket number can capture it. Replacing
the scalar 1/eff_b draw weight with a per-(bucket, stratum) matrix 1/m[b][s],
measured from the generator's own draw-vs-materialize behavior and damped
0.8 toward the scalar baseline (exp13's damping rule), should move
hhcomp/arithmetic toward 1.0x and finding L1 below 0.036 without breaking
the fixed buckets (medical, depcare, nature 57). Strata are the exp11 four:
(earner / no-earner) × (senior-or-disabled / neither).

Glossary for this chronicle: *materialization* = a drawn corruption moves
the computed benefit and is recorded (terms.md). *Keep rate* m[b][s] =
P(materialize | bucket b drawn, household in stratum s). *Importance
weights* = drawing buckets with weight 1/m so the recorded mix lands on the
empirical mix despite differential materialization. *Damping* = scaling the
correction 0.8 toward the status quo so one empirical iteration cannot
overshoot (exp13). *IPF* (iterative proportional fitting) = repeatedly
re-fitting weights to close a residual; exp7 documents why naive IPF
oscillates here — the keep rate shifts when the draw weights shift.

## Method
All in-process; only this script and chronicle are written, no repo files
touched, nothing committed. `generate.py` (including the
`--no-persistent-buckets` path) is unmodified.

1. **BEFORE:** 20k cases, seed 7, current persistent generator — replicates
   `generate.py`'s loop exactly (same rng stream, `persistent_buckets=True`,
   `max_attempts=12`).
2. **MEASURE:** monkeypatched `_inject_persistent` to attribute each drawn
   and each recorded variance to the household's stratum (same stratum key
   logic as `_applicable_buckets`); 60k cases, seed 11. Keep rate per cell =
   recorded / drawn, clipped to [0.02, 1.0] (the existing convention).
3. **AFTER:** 20k cases, seed 7 (paired rng stream with BEFORE), with the
   matrix weights patched in: draw weight
   `w(b,s) = 0.8/m[b][s] + 0.2/eff_b`, capped at 2.5x the scalar (trust
   region), with the scalar neutralized inside `_inject_persistent` so the
   two do not stack. Two guardrails added after a first uncapped attempt
   blew up: cells with m < 0.10 are mechanics gaps (the corruptor *cannot*
   materialize there — e.g. medical on non-senior households — so 1/m only
   steals draw mass from buckets that can; they fall back to the scalar).
4. Compared per-case element ratios (the chronicle convention since exp7:
   synth count/cases over real count/cases), share ratios, and finding L1.
   Real aggregates read from the held-out FY2024 QC file, never committed.

## Results

**The measured matrix** (keep rate; recorded/drawn counts; 60k cases):

| bucket | no_earner_nonsenior | earner_nonsenior | no_earner_senior | earner_senior | scalar eff_b |
|---|---|---|---|---|---|
| earned | 0.70 (21/30) | 0.82 (6230/7589) | — (0/1) | 0.75 (304/403) | 0.725 |
| unearned | 0.81 (2603/3205) | 0.95 (483/507) | 0.76 (2569/3391) | 0.83 (74/89) | 0.735 |
| shelter | 0.21 (1735/8262) | 0.47 (1615/3446) | 0.44 (4005/9045) | 0.68 (179/263) | 0.325 |
| sua | 0.15 (765/5095) | 0.43 (634/1468) | 0.33 (1042/3174) | 0.55 (41/75) | 0.322 |
| medical | 0.00 (0/1544) | 0.00 (0/32) | 0.53 (1022/1934) | 0.77 (44/57) | 0.491 |
| depcare | 0.31 (25/80) | 0.71 (266/375) | 0.33 (1/3) | 1.00 (1/1) | 0.525 |
| hhcomp | 0.70 (888/1265) | 0.61 (253/417) | 0.55 (116/211) | 0.41 (11/27) | 0.647 |
| arithmetic | 1.00 (468/469) | 1.00 (131/131) | 1.00 (172/172) | 1.00 (8/8) | 1.000 |

Keep rates vary strongly by stratum (shelter 0.21–0.68, sua 0.15–0.55,
hhcomp 0.41–0.70) — confirming exp14's diagnosis. The medical non-senior
cells are true zeros: the corruptor cannot put a medical variance on a
non-senior household (except rare 53/97-over fabrications), which is why
the gap-cell fallback exists.

**Before → after** (20k, seed 7, paired; per-case ratios = chronicle
convention; share ratios in the script output):

| bucket | before | after | Δ |
|---|---|---|---|
| earned | 0.84x | 0.87x | +0.03 |
| unearned | 0.77x | 0.71x | −0.06 |
| shelter | 0.74x | 0.70x | −0.05 |
| sua | 1.04x | 1.23x | **+0.19 regressed** |
| medical | 0.69x | 0.74x | +0.05 |
| depcare | 0.50x | 0.44x | −0.06 |
| hhcomp | 1.59x | **1.32x** | −0.28 |
| arithmetic | 1.51x | **1.24x** | −0.27 |
| nature 57 (share) | 0.98x | 0.97x | stable |

Finding mix: before 0.615/0.245/0.140 (L1 = **0.036**, reproduces exp14
exactly), after 0.623/0.243/0.134 (L1 = **0.048** — worsened, concentrated
in the under-issuance share).

**The mechanism worked exactly as designed.** The effective correction
w×m (draw weight × realized keep rate) moved to ≈1.0 in every
materializable cell (e.g. sua/no_earner_nonsenior: 0.47 → 1.02; shelter:
0.65 → 0.97; hhcomp: 1.09 → 0.99). And keep rates are approximately
*invariant* to the draw weights: re-measuring under the matrix weights
gave realized rates within ~0.03 of the measured matrix in all
well-sampled cells (sua 0.150→0.172, shelter 0.210→0.219,
hhcomp 0.702→0.681, arithmetic 1.00→1.00). No oscillation — a second damped
iteration would converge, not diverge; the exp7 IPF worry does not apply
to this one-shot stratified correction.

**So why did sua regress and finding L1 worsen?** The scalar was
accidentally compensating for a *second* distortion. The draw mix in
`_applicable_buckets` multiplies the empirical stratum mix by
`ZERO_BASE_WEIGHT` (earned ×0.018, unearned ×0.091, shelter ×0.227 on
zero bases) — but the empirical stratum mix *already reflects* real
zero-base households (this is the same double-counting exp11 diagnosed for
medical's zero-base weight). That suppression deflates
earned/unearned/shelter draws below their empirical shares and relatively
inflates sua (never scaled) and arithmetic (always fully applicable). The
scalar's under-correction of sua in no_earner_nonsenior (w×m = 0.47, far
below 1.0) happened to offset sua's draw-side inflation — two wrongs making
a right. The matrix fixed the materialization half (w×m → 1.02) and exposed
the draw-mix half: sua's recorded share in no_earner_nonsenior jumped
0.133 → 0.210 against an empirical 0.115. The arithmetic residual is now
definitively draw-side: m = 1.0 in all four strata, weight unchanged, yet
still 1.24x — the always-applicable fallback over-draws it.

## Verdict
**Partially held, not shippable.** The hypothesized mechanism is real and
behaves exactly as designed: stratum-dependent keep rates confirmed,
w×m → 1.0 everywhere materializable, no oscillation (keep rates invariant
to draw weights), hhcomp/arithmetic both moved ~0.28x toward 1.0x, medical
improved slightly, nature 57 stable. But the calibration gate did not move
the right way overall: finding L1 0.036 → 0.048 and sua 1.04x → 1.23x
regressed, because the scalar eff_b was masking the zero-base draw
distortion and the matrix removed the mask. Do not apply the matrix to the
generator as-is. The measured matrix stands as a diagnostic (printed by the
script); the binding constraint is now the draw side, not materialization.

## Next steps
1. **(recommended) Exp21: zero-base draw-scaling audit.** Test removing
   earned/unearned/shelter from `ZERO_BASE_WEIGHT` (the exp11 medical
   precedent — the empirical stratum mixes already encode real zero-base
   rates) and check whether the drawn mix lands closer to empirical; then
   re-apply the exp20 matrix on top of the corrected draw. If the
   double-counting diagnosis is right, this fixes sua's inflation *and*
   lets the matrix do its job.
2. If the audit confirms it, fit the draw correction and the
   materialization matrix jointly in one damped iteration (the exp20
   stability finding — keep rates invariant to draw weights — says one
   iteration suffices; no IPF loop needed).
3. The arithmetic residual (1.24x, m = 1.0 everywhere) belongs to the same
   audit: the always-applicable fallback in `_applicable_buckets` is a
   draw-mix problem, and the matrix correctly reports there is nothing to
   fix on the materialization side.
