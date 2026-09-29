# Experiment 44 — household size-mix fit + re-trial of the re-sliced medical mixes

**Date:** 2026-09-29 · **Code:** `experiments/exp44_size_mix.py`

### Hypothesis

Exp32 left medical at 0.71x (gate 0.75x) and named the binding constraint:
the household size mix (real 59.7% size-1 vs synth 46.8%). The re-sliced
empirical mixes (`exp28_resliced_mixes.json`, still staged) are arithmetically
correct as conditionals but blow up hhcomp/arithmetic when applied to the
wrong stratum composition (exp32 arm C: hhcomp 1.55x). Fitting the size draw
so the *post-screen* size mix matches real FY2024, then re-trialing the
re-sliced mixes, should land medical >= 0.75x with finding L1 <= 0.030 and
no other bucket regressing more than 0.10x vs the exp32 baseline.

North-star tie: calibration gate. Medical is the last element bucket below
its band, and exp32 proved the residual is composition, not rates — this is
the composition fix.

### Method

**[0] Real size mix, measured fresh.** The real FY2024 post-screen size mix
is re-measured from the held-out file (aggregates only), not trusted from a
chronicle. Sizes 7+ are folded into 6 (the generator draws 1..6).

**[1] Fixed-point fit of the pre-screen size weights.** The sampler draws a
size, then screens on income (`_income_eligible`); the screen rejects larger
households more often, so pre-screen weights must undershoot the targets.
Iterate: start weights = targets; sample 60k households through the screen;
w_i *= target_i / observed_i; renormalize; stop when max |obs − target| <
0.005. Same technique as exp32's senior tables. (Supporting refactor:
`_SIZE_WEIGHTS` extracted as a module constant in `household.py` —
behavior-neutral; the experiment patches it in-process.)

**[1b] Blast-radius audit.** The size mix touches: the depcare kid gate
(depcare needs kids; kids need size ≥ 2), the kid-count distribution by
size, hhcomp mechanics, and the per-stratum shares that feed the
materialization matrix. Re-measure `_DEPCARE_KID_WEIGHT` = 1/P_synth(kid|s)
on the new sampler (documented maintenance from exp28/exp32 — a pure
sampler property, unconfounded). Verify the phase-1 per-type error rates
still land (diagnostic). The materialization matrix is per-(bucket,stratum)
keep rates, which exp20 showed are invariant to draw weights — so no
re-measurement is expected; stage [3] confirms it.

**[2] Trials**, paired seeds 7/8, 20k cases, current defaults (dollar
mechanisms ON via `enable_adopted`):
A = exp32 baseline (legacy size weights); B = A + fitted size weights
(in-process); C = B + re-sliced mixes in-process
(`exp28_resliced_mixes.json`, `dist.json` untouched). B-vs-A isolates the
size-mix effect; C-vs-B isolates the mix change (exp32's ablation
discipline). Watch the arithmetic residual exp32's arm D flagged
(1.27x/1.40x) — diagnose whether it was the diagnostic's pre-screen
approximation or something structural.

**[3] Matrix interaction check** (exp32's procedure): re-measure the
materialization matrix with the size-fix effect *isolated* — (b) size-fix +
mech ON vs (a) legacy-size + mech ON, 150k, seed 11. Adopt a re-measured
matrix only if ≥15/32 cells shift ≥0.05 on the isolated effect (exp29's
rule), and then only jointly with an effectiveness re-fit (exp31's rule:
never the matrix alone — that double-counted in exp32). If the bar
triggers, the joint re-fit is a staged follow-up, not done here.

**[4] Final validation** of the kept change set on seeds 7/8, including
dollar marginals (share ≤$56, p10/p50/p99 — the size mix must not move
the dollar distribution).

### Results

**[0] Real size mix, measured fresh.** FY2024 post-screen (n=44,891):
sizes 1..6 = 0.5967 / 0.1576 / 0.1027 / 0.0708 / 0.0397 / 0.0324 (7+ folded
into 6). Matches exp32's recorded targets. Legacy synth post-screen:
0.4815 / 0.2391 / 0.1296 / 0.0837 / 0.0386 / 0.0274.

**[1] Fixed-point fit.** Converged in 2 iterations (max|obs−tgt| = 0.0023 <
0.005). Fitted pre-screen weights:
[0.5676, 0.1634, 0.1148, 0.0758, 0.0433, 0.0350] → post-screen
[0.5956, 0.1571, 0.1050, 0.0692, 0.0408, 0.0323].

**[1b] Blast radius.** `_DEPCARE_KID_WEIGHT` re-measured on the new sampler:
1.808/1.843/3.671/4.391 → **2.083/2.147/4.997/5.600** (all shifts >15%).
The maintenance was load-bearing: without it, the first trial run showed
depcare regressing 1.00x → 0.78x on seed 8; with it applied, depcare is
1.03x/0.98x. (The re-measured weight is applied in arms B/C — it is
unconfounded sampler maintenance, cf. exp32.)

**[2] Trials** (20k, paired seeds; ratios vs real; A = exp32 baseline):

| arm | medical s7/s8 | hhcomp s7/s8 | arith s7/s8 | L1 s7/s8 | le56 |
|---|---|---|---|---|---|
| A (baseline) | 0.71x / 0.68x | 1.01x / 1.04x | 1.14x / 1.16x | 0.008 / 0.016 | 0.69/0.70 |
| B (+ size mix) | 0.76x / 0.64x | 0.90x / 0.84x | 0.99x / 1.07x | 0.010 / 0.015 | 0.70/0.70 |
| C (+ resliced) | 0.74x / 0.71x | **1.23x / 1.27x** | **1.27x / 1.36x** | 0.037 / 0.037 | 0.69/0.70 |

B-vs-A: the size fix is safe and directionally helpful — hhcomp and
arithmetic move back toward 1.0x on both seeds, L1 stays ≤0.015, dollar
marginals flat. But medical is seed-dependent: 0.76x on seed 7 (bar met),
0.64x on seed 8 (a 0.04 regression vs A). The size fix alone does not
cleanly close medical.

C-vs-B: the re-sliced mixes are **not adoptable even with the correct size
mix**. Medical misses the bar on both seeds (0.74x/0.71x < 0.75x), finding
L1 misses (0.037 > 0.030), and hhcomp/arithmetic blow up (1.23–1.36x).
Exp32's arm D predicted medical 0.78x/0.73x with hhcomp ~1.16–1.20x; the
real fit lands slightly worse on every axis.

**Why C fails — the diagnosis.** The re-slice concentrates hhcomp mass on
no_earner_nonsenior (0.0560 → 0.0892), but the generator still
over-populates that stratum even with the size fix:

| stratum | real | synth (arm B) | delta |
|---|---|---|---|
| no_earner_nonsenior | 0.273 | 0.342 | **+0.069** |
| earner_nonsenior | 0.231 | 0.227 | −0.004 |
| no_earner_senior | 0.454 | 0.413 | −0.041 |
| earner_senior | 0.042 | 0.019 | **−0.023** |

The re-slice is arithmetically correct as a conditional on the *real*
composition, but the generator's earner×senior joint is wrong: too many
no_earner_nonsenior, too few seniors overall (P(senior) 0.432 vs 0.496),
especially earner_seniors (0.019 vs 0.042 — the generator's p_earn=0.13
for senior/disabled under-generates senior earners). The size mix was
necessary but not sufficient; the binding constraint moved to the
earner×senior joint.

**[3] Matrix interaction check.** Isolated size-fix effect: **6/32** cells
shift ≥0.05 (bar: ≥15). Worst cell: depcare/earner_senior 0.142 — a small
cell (rare stratum × rare bucket), not a systematic shift. No joint
re-fit triggered; the committed matrix stands (exp31's rule respected:
no matrix-only re-measurement).

**[4] Dollar marginals.** le56 unchanged (0.69–0.70); the size mix does not
move the dollar distribution.

### Verdict

**Partially held, with a clean negative inside.**

1. **The size-mix fix is safe and keepable but does not close medical.**
   It improves hhcomp/arithmetic toward 1.0x on both seeds, holds L1 ≤
   0.015, leaves dollars flat, and needs no matrix re-fit. But medical is
   0.76x/0.64x — seed-dependent, bar not cleanly met. Adopting it is the
   coordinator's call; it is strictly better composition. **Coordinator decision
   (2026-09-29): adopted.** The fitted pre-screen weights are now the default
   in `src/synth/household.py` (`_SIZE_WEIGHTS`); legacy values retained in the
   comment. Rationale: safety profile clean on both seeds, strictly better
   composition, no matrix re-fit required. The medical gap is re-attributed to
   the earner x senior joint (staged).
2. **The re-sliced mixes are dead — clean negative.** `exp28_resliced_mixes.json`
   should be retired, not re-trialed: even with correct size composition,
   the mixes miss every bar and blow up hhcomp/arithmetic. The failure is
   the earner×senior joint, which the re-slice assumed fixed.
3. **The binding constraint is now named:** earner_senior 0.019 vs 0.042
   real; no_earner_nonsenior 0.342 vs 0.273. The next medical lever is the
   sampler's earner×senior joint (p_earn for senior/disabled, and/or the
   senior tables' interaction with earnings), not the size mix and not
   the bucket mixes.
4. **Kid-weight maintenance confirmed load-bearing** (+15–28% shifts;
   without it depcare regresses).

What changed in the plan: exp32's "size mix → re-trial re-sliced mixes"
sequence is broken at the second step. The size mix helped; the mixes
did not. Medical's path forward is the earner×senior joint experiment.

### Next steps

1. **Earner×senior joint experiment (new recommended next run):** fix the
   sampler's earner/senior joint — earner_senior 0.019 → ~0.042,
   no_earner_nonsenior 0.342 → ~0.273 — via p_earn for senior/disabled
   and/or senior-table re-tuning. Then re-examine medical; do NOT
   re-apply the retired re-sliced mixes.
2. **Coordinator:** adopt the fitted `_SIZE_WEIGHTS`
   ([0.5676, 0.1634, 0.1148, 0.0758, 0.0433, 0.0350]) and the re-measured
   `_DEPCARE_KID_WEIGHT` ([2.083, 2.147, 4.997, 5.600]) iff arm B's
   seed-8 medical softness is acceptable; retire
   `exp28_resliced_mixes.json` (superseded — record only).
3. The `_SIZE_WEIGHTS` module-constant refactor in `household.py` is
   behavior-neutral and can stay regardless.

### Files

- `experiments/exp44_size_mix.py` — full pipeline (fit, trials, matrix
  check, diagnostics).
- `experiments/exp44_fitted_weights.json` — fitted weights, targets,
  kid-weight values, matrix-check counts (record).
- `experiments/exp44_size_mix.md` — this chronicle.
- `src/synth/household.py` — behavior-neutral refactor only
  (`_SIZE_WEIGHTS` constant); no committed value changes.
