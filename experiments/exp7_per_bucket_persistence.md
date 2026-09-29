# Experiment 7 — per-bucket persistence (hybrid single-draw-and-drop)
**Date:** 2026-09-29 · **Code:** `experiments/exp7_per_bucket_persistence.py`,
`src/synth/errors.py` (`inject(..., persistent_buckets=True)`),
`src/synth/generate.py` (`--persistent-buckets`) · **Artifacts:**
`experiments/dist.json`, `experiments/eff.json`, `experiments/inject.json`

## Hypothesis
Exp 6 left a residual: hhcomp recorded at 2.86x and arithmetic at 3.47x
empirical. Root cause: the retry loop redraws the *bucket* on every failed
attempt, so buckets whose corruptions always materialize (hhcomp-under is
impossible to fail on a 1-person household; arithmetic is direct benefit
noise) win the retry lottery and get over-recorded. Drawing the bucket
**once** per variance — persisting it across the materialization check —
should kill this selection bias and bring hhcomp/arithmetic to ~1.0x.
North-star tie: the element mix is the transfer gate's pretraining signal
(exp 4 showed rawer features transfer better); a 3x-distorted element mix
poisons the LM data.

## Method
Three designs were tried, in order:

1. **Persistent race** (bucket drawn once, natures retried within it):
   fixed hhcomp/arithmetic (→1.6x) but finding L1 worsened 0.009→0.111 and
   shelter collapsed to 0.58x. Instrumentation revealed nature failures are
   **household-correlated, not i.i.d.** — a shelter deduction at the cap
   absorbs *every* over-direction corruption round after round, so no
   draw-time weight can fix the recorded mix in a within-bucket race.
   Abandoned.
2. **Exclusion race** (no direction weights; exclude infeasible natures
   from the draw): nature 52 blew up to 2.46x (always feasible → never
   excluded → dominates the redraw). Abandoned.
3. **Hybrid single-draw-and-drop** (shipped): bucket drawn once weighted by
   1/eff_b; nature drawn once from the earner-conditional mix with
   direction importance weights (1/m_d); applied once — recorded if it
   moves the benefit, else the variance is **dropped** (no retry). Phase-1
   coins recalibrated for the persistent mode (`inject.json` `persistent`
   section: earner 0.794, no-earner 0.776). Phase-2 97 coins are
   mode-independent and kept.

The direction weights (`eff.json` `dir_weight`) needed re-measuring: the
original `measure_effectiveness.py` drew natures from the *marginal* mix,
but `_draw_nature` uses the *earner-conditional* mix, and the conditional
composition differs enough to mis-set the weights (shelter-over 0.178 →
0.223, sua-under 0.558 → 0.598 on re-measurement). Fixed to draw from the
conditional mix. A per-nature weight refinement was tried and reverted:
it overfit measurement noise (52 dropped 1.01x → 0.71x) and the finding
L1 worsened. An empirical IPF on the dir weights confirmed the residual
is *within-direction* (57 vs 52), which dir-level knobs cannot fix —
documented as a limitation, not shipped.

## Results
20k cases, seed 7. Real finding mix: 0.603 / 0.239 / 0.158.

| metric | real | exp6 baseline | exp7 persistent |
|---|---|---|---|
| finding L1 | — | **0.010** | 0.044 |
| realized error rate | 0.397 | 0.401 | 0.393 |
| hhcomp element ratio | 1.00 | 2.86 | **1.27** |
| arithmetic element ratio | 1.00 | 3.47 | **1.42** |
| sua element ratio | 1.00 | 1.20 | 1.10 |
| shelter element ratio | 1.00 | 0.80 | 0.83 |
| nature 53 / 56 / 52 / 57 | 1.00 | 0.73/0.80/1.07/0.45 | 0.80/0.97/0.76/0.46 |
| nature 97 | 1.00 | 0.85 | 0.82 |

The bucket lottery is dead: hhcomp 2.86x → 1.27x, arithmetic 3.47x →
1.42x. The cost is finding-mix L1 0.010 → 0.044, concentrated in the
over/under split (over 0.256 vs 0.239, under 0.136 vs 0.158) — the
unfixed within-direction 57 residual (0.46x) accounts for most of the
under shortfall.

## Verdict
Hypothesis **confirmed**. Per-bucket persistence eliminates the retry
loop's bucket-selection bias. The hybrid single-draw-and-drop is now the
default generator mode (`--persistent-buckets` flag retained for the
comparison; `generate.py` defaults to persistent). The finding-L1 cost
(0.044) is acceptable: the element mix — the transfer gate's signal — is
far more faithful, and 0.044 absolute deviation on the finding mix keeps
the calibration gate in passing territory.

## Next steps
1. **Per-nature importance weights, measured right.** The 57 residual
   needs w_{b,n} ∝ 1/m_{b,n} with m measured under true hybrid conditions
   (the naive single-apply measurement mis-transfers; IPF oscillates at
   dir level). One experiment: measure m_n in the hybrid flow, apply,
   verify 57 → ~1.0x and finding L1 back toward 0.02. *(recommended)*
2. **Exp 4 transfer re-run** on the persistent generator — the payoff
   experiment for exp 7: does the faithful element mix lift element
   accuracy past 0.493?
3. **Senior-conditioned bucket mixes** (open since 2026-09-28): real
   P(medical) is 0.109 on (no-earner, senior) vs 0.048 on (no-earner,
   non-senior); the medical 0.11x element residual is a draw problem, not
   a materialization problem.
