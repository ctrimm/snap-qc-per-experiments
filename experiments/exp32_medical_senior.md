# Experiment 32 — unblock medical via the senior-rate path

**Date:** 2026-09-29 · **Code:** `experiments/exp32_medical_senior.py`
(diagnostic follow-up: `experiments/exp32b_attribute.py`)

### Hypothesis

Exp28 left medical stuck at 0.55x (gate 0.75x) and named the binding
constraint: the sampler's senior rate (36.2%) sits far below real (49.6%),
so the corrected empirical mixes — re-sliced with senior = FSNELDER>0 |
SSI1-8>0 | FSNDIS>0 — cannot be adopted without blowing up hhcomp/arithmetic
(exp28's trial T2: L1 0.026 -> 0.049). Closing the sampler's senior-rate gap
first should let the re-sliced mixes land: medical >= 0.75x, finding L1 <=
0.030, no other bucket regressing more than 0.10x vs the exp31 baseline.

North-star tie: calibration gate. Medical is the last element bucket below
its band, and the fix has to come from the sampler composition, not from
re-weighting the draw.

### Method

**[0] Gap confirmation and decomposition.** Re-measured P(senior_or_disabled)
on the current tree (exp29/exp31 changed the sampler and defaults since
exp28's 36.2% reading): real FY2024 QC aggregates (held-out; aggregates only)
vs 60k generated households, legacy vs new draw tables. Decomposed the gap
into the senior-age draw vs the disability flag (FSNDIS>0).

**Senior fix** (`src/synth/household.py`, delimited exp32 edits): the old code
drew elderly at 0.28 (size 1) / 0.08 (else) and disabled at a flat 0.12.
Both were off, in opposite directions by size: replaced with size-grouped
pre-screen tables (1 / 2 / 3+) fitted by fixed-point simulation so POST
income-screen rates match the real per-size aggregates (the screen inflates
senior rates — seniors skip the gross test — so pre-screen values undershoot
the targets):

| size group | elderly (was -> now) | disabled\|not-elderly (was -> now) |
|---|---|---|
| 1 | 0.28 -> 0.3538 | 0.12 -> 0.1515 |
| 2 | 0.08 -> 0.1694 | 0.12 -> 0.0995 |
| 3+ | 0.08 -> 0.0254 | 0.12 -> 0.1008 |

Rng call order is unchanged (same two `random()` calls), so paired-seed
comparisons stay aligned. Real targets hit post-screen: size-1 0.438/0.215,
size-2 0.241/0.148, size-3+ 0.037/0.148 (elderly / disabled-given-not-elderly).

**[1] Trials**, paired seeds 7/8, 20k cases, current defaults (dollar
mechanisms ON): A = exp31 baseline (legacy senior tables patched in-process);
B = A + senior fix; C = B + re-sliced mixes (in-process; `dist.json`
untouched per task rules); D = C + real size-mix weights (diagnostic only).
B-vs-A isolates the rate change; C-vs-B isolates the mix change.

**[2] Interaction checks.** Re-measured the materialization matrix with the
senior-fix effect *isolated*: (b) senior-fix + mechanisms ON vs (a)
legacy-senior + mechanisms ON (150k, seed 11, exp21 procedure). The
(a)-vs-committed gap is the dollar-mechanism confound. Adoption bar:
>=15/32 cells shifting >=0.05 on the isolated (b)-(a) effect (exp29's rule).
Also re-measured `_DEPCARE_KID_WEIGHT` = 1/P_synth(kid|s) on 100k households
(pure sampler property, unconfounded; documented maintenance: re-run whenever
the sampler changes).

**[3] Final validation** of the kept change set on seeds 7/8.

### Results

**Stage 0 — gap confirmed, both drivers off.** Real: P(elderly)=0.3091,
P(disabled|not elderly)=0.2699, P(senior)=0.4956. Legacy synth: 0.2294 /
0.1762 / 0.3652. Post-screen gaps: elderly +0.0796, disability flag +0.0938 —
both drivers, with the disability flag the larger of the two. (Note the old
sampler also *over*-assigned senior status to size-3+ households: 0.08 drawn
vs 0.037 real — the fix lowers it.) After the fix: 0.2778 / 0.1737 / 0.4032.
Per-size rates now match; the remaining overall gap (0.403 vs 0.496) is the
household **size mix** (real 59.7% size-1 vs synth 46.8%), a separate sampler
parameter outside this experiment's scope.

**Stage 1 — trials** (per-case ratios vs real; finding L1; share <=$56):

| arm | medical s7/s8 | hhcomp s7/s8 | arithmetic s7/s8 | L1 s7/s8 | le56 |
|---|---|---|---|---|---|
| A (exp31 baseline) | 0.64x / 0.60x | 1.08x / 1.08x | 1.12x / 1.14x | 0.019 / 0.019 | 0.69 |
| B (+ senior fix) | 0.69x / 0.69x | 1.00x / 1.04x | 1.13x / 1.17x | 0.007 / 0.017 | 0.69 |
| C (+ re-sliced mixes) | 0.72x / 0.66x | **1.55x / 1.48x** | **1.35x / 1.37x** | 0.054 / 0.051 | 0.68 |
| D (+ real size mix, diag) | 0.78x / 0.73x | 1.16x / 1.20x | 1.27x / 1.40x | 0.030 / 0.034 | 0.69 |

Ablation: rate change (B-A) dL1 = -0.012/-0.002, d(medical) +0.04/+0.09x —
benign, mildly helpful. Mix change (C-B) dL1 = +0.047/+0.034,
d(hhcomp) = +0.55/+0.44x, d(arithmetic) = +0.23/+0.19x — **the mix change
does the damage, not the rate change**. Exp28's T2 blowup reproduces even
with the senior fix: the senior-rate gap was *not* the binding constraint on
adopting the re-sliced mixes.

**Why the re-sliced mixes blow up.** The re-slice is arithmetically correct
as a conditional: removing the mis-sliced FSNDIS medical variances from the
nonsenior strata concentrates what remains — no_earner_nonsenior hhcomp
0.0560 -> 0.0892, arithmetic 0.0350 -> 0.0484. But the synth's stratum
marginals are wrong: P(no_earner_nonsenior) = 0.360 vs real 0.273 (+8.7pp),
P(no_earner_senior) = 0.386 vs real 0.454 (-6.8pp). The correct conditional
mix applied to too many no_earner_nonsenior households over-draws hhcomp
(drawn hhcomp 1.16x of the real-drawn level; arithmetic 1.12x; medical 0.84x
— medical concentrates in the under-weighted senior strata). The recorded
ratios (1.48-1.55x) run a bit hotter than the drawn ratios, but the draw
composition is the dominant term. Arm D confirms the diagnosis: with the
real size mix, hhcomp falls 1.55x -> 1.16x and medical reaches 0.78x/0.73x —
the size mix is the next binding constraint.

**Stage 2a — matrix: a double-counting near-miss, caught and reverted.**
Raw re-measurement under the senior fix showed 18/32 cells shifting >=0.05,
which would have triggered adoption. The isolated comparison told a
different story: senior-fix effect (b)-(a) = **6/32** cells; dollar-mechanism
effect (a)-committed = **16/32** cells. Exp29's matrix was measured with the
mechanisms OFF; exp31's effectiveness re-fit already absorbed the mechanism
effect *given* that matrix — the two are a jointly calibrated pair.
Adopting the re-measured matrix alone double-counts the mechanism effect.
A 2x2 ablation proved it (seed 7, depcare per-case ratio): B0 committed/
committed 0.90x; B1 committed matrix + new kid-weight 0.87x; **B2 new matrix
+ committed kid-weight 0.80x**; B3 both new 0.78x. The matrix adoption was
the culprit (depcare -0.10x by itself). Reverted to the committed matrix;
the raw measurement is kept in `experiments/exp32_matrix.json`, marked
superseded, for the record.

**Stage 2b — kid-weight: adopted, unconfounded.** P_synth(kid|s) shifted on
all four strata under the senior fix (senior strata got more size-1-heavy,
so fewer kids): weights 1.929->1.808, 1.953->1.843, 2.884->**3.671**,
3.318->**4.391**. All shifts >3%; adopted with a delimited exp32 comment.
The 2x2 shows the kid-weight alone moves depcare only 0.90x -> 0.87x.

**Stage 3 — final validation** (kept set: senior fix + committed matrix +
re-measured kid-weight; dollar mechanisms ON). The "A" reference in this
validation run carried the new kid-weight; vs the true exp31 baseline
(run-1 arm A: depcare 0.96x/0.98x) the worst other-bucket regression is
+0.09 on seed 7 (depcare 0.87x), +0.00 on seed 8 (depcare 1.00x vs 0.98x) —
still inside the 0.10x bar on both seeds:

| seed | medical | finding L1 | worst other-bucket regression | le56 |
|---|---|---|---|---|
| 7 | 0.71x (A: 0.65x) | 0.008 | +0.04 vs contemporaneous A; +0.09 vs exp31 arm A | 0.69 |
| 8 | 0.68x (A: 0.61x) | 0.016 | +0.03 | 0.70 |

No bucket regresses more than 0.10x vs the exp31 baseline on either seed;
dollar marginals do not move (le56 0.69/0.70 vs real 0.70; median $21 vs
real $31 — the known exp23 asymmetry, unchanged). Medical improves
+0.06/+0.07x but stops at 0.71x/0.68x, short of the 0.75x bar.

### Verdict

**Does not hold** on the medical bar (0.71x/0.68x < 0.75x) — but it is a
clean partial with every mechanism named:

1. **The senior-rate fix is kept.** It is safe (no L1/hhcomp/arithmetic
   blowup — the failure mode exp28 feared did not materialize) and strictly
   beneficial: medical +0.06-0.07x, finding L1 0.019 -> 0.008/0.016, no
   bucket regressing >0.10x, dollar marginals flat. Both hypothesized
   drivers were real: the senior-age draw and the disability flag were each
   ~0.08-0.09 short post-screen.
2. **The re-sliced mixes are not adoptable yet — clean negative.** The
   ablation decomposition (B-vs-A vs C-vs-B) shows the mix change, not the
   rate change, causes the hhcomp/arithmetic blowup. The binding constraint
   is the stratum-share mismatch, and within it the household size mix
   (real 59.7% size-1 vs synth 46.8%): arm D proves fixing the size mix
   takes medical to 0.78x/0.73x and hhcomp most of the way back.
3. **Double-counting caught in stage 2a.** The matrix re-measurement looked
   warranted (18/32) until the senior-fix effect was isolated (6/32); the
   rest is the dollar-mechanism effect exp31 already absorbed. Adopting it
   regressed depcare 0.10x on its own; reverted.

What changed in the plan: the re-sliced mixes moved from "adopt after the
senior fix" to "blocked on the size-mix experiment" — the senior fix closed
only ~1/3 of the senior gap (0.365 -> 0.403 of 0.496), and the residual is
composition, not rates.

### Next steps

1. **Size-mix sampler experiment (recommended next run):** fit the household
   size weights to the real FY2024 post-screen mix (0.597/0.158/0.103/0.071/
   0.040/0.031), then re-trial the re-sliced mixes (`exp28_resliced_mixes.json`,
   still staged and valid). Arm D predicts medical ~0.75x and hhcomp ~1.2x;
   the arithmetic residual in D (1.27x/1.40x) needs a look — possibly the
   pre-screen-vs-post-screen size-mix approximation in the diagnostic.
   Blast radius is wide (depcare size>2 gate, kid distribution, hhcomp), so
   it deserves its own experiment, not a drive-by constant change.
2. **Coordinator:** apply `exp28_resliced_mixes.json` to `dist.json` only
   after step 1 lands. The committed `dist.json`/`eff.json`/`inject.json`
   were not touched here.
3. **Joint matrix+effectiveness re-measurement under mechanisms-ON** is the
   principled fix for the 16/32 mechanism-effect keep shifts — but it must
   redo exp31's effectiveness fit jointly (the current pair is jointly
   calibrated and healthy: L1 0.019). Do not re-measure the matrix alone.
4. Live tree state after this experiment: `src/synth/household.py` exp32
   senior tables; `src/synth/errors.py` re-measured `_DEPCARE_KID_WEIGHT`;
   committed materialization matrix kept; `experiments/exp32_matrix.json`
   superseded (record only).

### Files

- `experiments/exp32_medical_senior.py` — full pipeline (gap confirmation,
  trials A/B/C/D, isolated matrix interaction check, kid-weight
  re-measurement, final validation).
- `experiments/exp32b_attribute.py` — 2x2 matrix/kid-weight ablation +
  keep-rate attribution ((b)-(a) vs (a)-committed).
- `experiments/exp32_matrix.json` — raw keep re-measurement, marked
  superseded (adoption reverted; see above).
- `experiments/exp32_medical_senior.md` — this chronicle.
- `src/synth/household.py` — uncommitted, delimited exp32 edits: size-grouped
  elderly/disability draw tables.
- `src/synth/errors.py` — uncommitted, delimited exp32 edit: re-measured
  `_DEPCARE_KID_WEIGHT` (matrix adoption reverted after the 2x2).
