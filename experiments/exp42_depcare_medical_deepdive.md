# Experiment 42: depcare/medical deep dive

**Date:** 2026-09-29 · **Code:** `experiments/exp42_depcare_medical_deepdive.py`

## Hypothesis

North-star gate: calibration. Two stubborn residuals remain — depcare at
~0.41x and medical at ~0.53x of real variance-element shares. Exp12 (kid-gated
depcare) and exp11 (senior-conditioned mixes for medical) both fixed the
*first-order* conditioning, so the hypothesis is that the remaining gap is a
*second-order* missing mechanism discoverable by close quantitative analysis
of real error cases: specific household configurations (earner among kid
households; medical-expense presence and the $35 threshold), specific nature
codes, or specific cause splits where the generator under-draws. If the
analysis instead shows the real conditional rates already match what the
generator draws, the residual is irreducible without case-level features the
generator lacks — a clean negative.

## Method

1. Real side: FY2020–2024 QC public-use files, pooled (held out; never
   committed). Per-case variances from ELEMENT1–9 / NATURE1–9 / AGENCY1–9 /
   AMOUNT1–9; household features FSNKID, FSNK0T4 (kids 0–4), FSNELDER, FSNDIS
   (+ per-person AGE≥60 / DIS=1 fallback), earner = (FSEARN > 0) or any
   EMPSTA in {3,4,5,6,7,8}, FSDEPDED > 0, FSMEDEXP, FSMEDDED > 0.
2. Synth side: 40,000 cases from `src/synth/generate.py --n 40000 --seed 7
   --dist experiments/dist.json` (in-flight generator, see git state below).
3. Same cuts on both sides: nature mix and cause mix per element; conditional
   case-rates P(error | stratum) for strata the generator's draw can see;
   dollar-error size (real per-variance AMOUNT vs synth single-variance
   case dollar_error as proxy); $35-threshold clustering for medical.
4. Effect-size estimates: "draw-fix projection" — hold the synthetic case mix
   fixed and reweight the bucket draw to the real per-stratum rates; report
   where the element share would land (0.41x → ?).

Reproducibility (measured 2026-09-29, in-flight generator):

```
git rev-parse HEAD: f515930843d66d784ee1b95288e600de22353bfa
git status --short (at synth-generation time; my two exp42 files added after):
 M experiments/inject.json
 M src/synth/dollar_mech.py
 M src/synth/errors.py
 M src/synth/household.py
?? experiments/eval_pilot/
?? experiments/exp26_combine_dollar.md / .py, exp27_earned_audit.py,
   exp28_* (resliced_mixes.json, shares_game.py, matrix_backup.json),
   exp29_sampler_positivity.py, exp30_eval_pilot.md,
   exp33_state_heterogeneity.py, exp34_temporal_drift.md / .py,
   exp38_rare_rule_mass.py, exp39_joint_distributions.md / .py
```

(src/ was not modified by this experiment — read-only per standing rules.)

## Results

Baseline check with the in-flight generator (40k synth, seed 7; real =
FY2020–2024 pooled, 167,002 cases). The quoted 0.41x/0.53x are from an older
generator state; today measures **0.59–0.61x depcare, 0.67–0.68x medical**
(variance-share basis; case-rate basis 0.53x / 0.59x).

### A. Variance-element shares

| bucket | real n | real share | synth n | synth share | ratio |
|---|---|---|---|---|---|
| depcare | 1,305 | 0.0156 | 167 | 0.0095 | **0.61x** |
| medical | 3,802 | 0.0455 | 541 | 0.0309 | **0.68x** |
| earned | 19,741 | 0.2363 | 4,018 | 0.2296 | 0.97x |
| unearned | 18,771 | 0.2247 | 4,195 | 0.2397 | 1.07x |
| shelter | 26,046 | 0.3118 | 6,086 | 0.3478 | 1.12x |
| sua | 6,439 | 0.0771 | 1,573 | 0.0899 | 1.17x |
| hhcomp | 2,056 | 0.0246 | 576 | 0.0329 | 1.34x |
| arithmetic | 2,230 | 0.0267 | 343 | 0.0196 | 0.73x |

FY2024-only check (pooled includes partial FY2021): depcare 0.59x, medical
0.67x — same story.

### B. Nature / cause mixes (shares within the element)

| depcare nature | real | synth | medical nature | real | synth |
|---|---|---|---|---|---|
| 52 omitted | 0.222 | 0.132 | 52 omitted | 0.198 | 0.153 |
| 53 shouldn't be incl. | 0.308 | 0.323 | 53 shouldn't be incl. | 0.317 | 0.335 |
| 56 budgeted too much | 0.054 | 0.018 | 56 budgeted too much | 0.020 | 0.007 |
| 57 budgeted too little | 0.036 | **0.162** | 57 budgeted too little | 0.016 | **0.113** |
| 97 timing | 0.282 | 0.365 | 97 timing | 0.404 | 0.388 |
| 98 transcription | 0.028 | 0.000 | 98 transcription | 0.014 | 0.000 |
| 99 other | 0.069 | 0.000 | 99 other | 0.029 | 0.004 |

Cause mix is close on both (depcare agency 0.443 vs 0.407, client 0.226 vs
0.228; medical agency 0.477 vs 0.514, client 0.063 vs 0.079). Synth over-draws
no_fault ~3–4x (depcare 0.186 vs 0.047; medical 0.229 vs 0.075) — the 97/26
"not required to report" mass. Nature 57 is over-drawn 4–7x on both
deductions; 52 is under-drawn on depcare.

Nature × expense presence (real): when medical expenses are on file,
errors are omissions/timing (52: 0.31, 97: 0.46); when not on file, improper
inclusions (53: 0.64). Same pattern for depcare (depded>0 → 52: 0.31;
depded=0 → 53: 0.71).

### C. Depcare conditional rates — P(depcare-error case | stratum)

| stratum (kids, earner) | real n | real rate | synth n | synth rate |
|---|---|---|---|---|
| (no kids, no earner) | 93,598 | 0.003% | 16,503 | 0.000% |
| (no kids, earner) | 14,272 | 0.021% | 5,387 | 0.000% |
| (kids, no earner) | 27,789 | 0.385% | 12,636 | 0.182% |
| (kids, earner) | 31,343 | **3.800%** | 5,474 | **2.631%** |

The earner interaction is 10x in real (3.800 vs 0.385). Synth has the
direction but both kid-cells are low (1.44x and 2.11x under).

| stratum (kids, depded>0) | real rate | synth rate |
|---|---|---|
| (kids, depded=0) | 0.667% | 0.435% |
| (kids, depded>0) | **27.300%** | **10.360%** |

41x ratio in real, 24x in synth — the draw weight on expense-carrying
households is ~2.6x too low. (Synth depded>0 among (kids, earner) is 6.0%
vs real 10.0% — the 7%-of-size>2 expense model underproduces on earners.)

Real-only cuts the generator cannot see yet:

| cut | real rate |
|---|---|
| n_kids=1 / 2 / 3 / 4+ | 1.476% / 2.398% / 3.008% / 2.523% (synth flat: 0.82 / 0.94 / 1.02 / 1.10%) |
| (kids, earner, kids 0–4) | **5.207%** |
| (kids, earner, no kids 0–4) | 2.467% |
| (kids, no earner, kids 0–4) | 0.487% |

Depcare error risk rises with n_kids and concentrates on earner households
with young children — neither concept exists in the draw.

### D. Medical conditional rates

| stratum (senior_dis, medexp>0) | real n | real rate | synth n | synth rate |
|---|---|---|---|---|
| (senior_dis, medexp=0) | 73,721 | 2.014% | 11,819 | 2.081% |
| (senior_dis, medexp>0) | 9,514 | **24.154%** | 2,779 | **10.327%** |
| (not senior_dis, *) | 83,767 | 0.02% | 25,402 | 0.000% |

The medexp=0 cell already matches (2.01 vs 2.08%). The entire residual is
the medexp>0 cell: synth under-draws it 2.34x. (Synth medexp>0 rate among
senior_dis is 19.0% vs real 11.4% — the amount model is generous; the *draw
weight* is the problem, not the expense model.)

$35-threshold check (real, senior_dis): no sharp threshold cliff. Rates by
FSMEDEXP: 0 → 2.0%; 0–35 → 35.2% (n=367); 35–100 → 32.3%; 100+ → 23.3%.
Small expenses are the most error-prone per case, but volume lives at 0
(1,485 errors) and 100+ (2,032 errors). No threshold-specific mechanism
needed — presence/absence dominates.

### E. Dollar-error size — not the problem

| element | real median (p25–p90) | synth median (p25–p90) | real mean | synth mean |
|---|---|---|---|---|
| depcare | $60 ($21–$202) | $71 ($49–$171) | $90.0 | $87.9 |
| medical | $46 ($19–$119) | $55 ($31–$108) | $57.3 | $57.6 |

Means match within 3%. The residual is draw-side, not amount-side —
consistent with the task's suspicion.

### F. Draw-fix projections (effect sizes)

Hold the synth case mix fixed; set per-stratum depcare/medical case rates to
real. Case-rate basis (upper bound on what draw reweighting can do):

| element | strata matched | now | projected |
|---|---|---|---|
| depcare | kids × earner | 0.53x | **0.83x** |
| depcare | kids × earner × depded>0 | 0.53x | 0.81x |
| depcare | kids only | 0.53x | 1.28x (overshoot — synth has 45% kid cases vs real 35%) |
| medical | senior_dis × earner | 0.59x | 0.75x |
| medical | senior_dis × medexp>0 | 0.59x | **1.00x** |
| medical | senior_dis only | 0.59x | 0.73x |

Reading: matching real (senior_dis, medexp>0) rates closes the *entire*
medical gap. Matching (kids, earner) closes ~64% of the depcare gap
(0.53→0.83 of the 0.47 gap to 1.0); the rest is the n_kids scaling, kids04,
and the depded amount model on earners.

## Verdict

**Hypothesis held — no clean negative.** Both residuals decompose into
identifiable draw-side mechanisms; nothing looks irreducible:

1. **Medical: the draw must condition on medical-expense presence within
   senior/disabled households.** Projection 0.59x → 1.00x. The senior
   conditioning (exp11) got the right households; the missing piece is
   concentrating the draw ~2.3x more on the medexp>0 subset. No threshold
   mechanism needed; amount model is fine.
2. **Depcare: add a kids × earner interaction to the draw** (projection
   0.53x → 0.83x). The empirical stratum mix was estimated over all
   households per stratum but is applied only to kid households — re-estimate
   the depcare mix restricted to kid households, or multiply by the
   interaction (~1.4x on (kids, earner), ~2x on (kids, no-earner)).
3. **Depcare: scale with n_kids and add a young-kid concept** (FSNK0T4).
   Real risk rises 1.5% → 3.0% over n_kids 1→3 and hits 5.2% on
   (earner, kids 0–4); synth is flat. Estimated 0.83x → ~0.9x.
4. **Depcare amount model on earners**: synth depded>0 among (kids, earner)
   6.0% vs real 10.0% — raise the expense-draw rate for earner households.
5. **Secondary, both**: nature 57 over-drawn 4–7x, depcare nature 52
   under-drawn; condition nature on expense presence (on-file → 52/97,
   off-file → 53). no_fault cause over-drawn ~3x.

## Next steps

1. **Exp43 (recommended): medical medexp-conditioned draw.** In
   `_applicable_buckets`, upweight the medical bucket ~2.3x when
   `facts["medical_exp"] > 0` (or add a (senior, medexp) slice to the
   stratum mix); regenerate 20k and check medical → ~1.0x with no finding-L1
   regression. Small, high-payoff.
2. **Exp44: depcare kid-restricted stratum mix + kids × earner
   interaction.** Recompute the depcare per-stratum mix on kid households
   only; add n_kids scaling (and optionally kids04) to the draw weight.
   Target depcare 0.6x → ~0.9x.
3. **Exp45 (batchable with 44): depcare expense-model refresh** — raise the
   expense-draw rate for earner households toward the real 10.0% depded>0
   among (kids, earner); verify against the C-table.
4. **Exp13-style per-nature weights** for the 57 over-draw (both deductions)
   and depcare 52 under-draw; gate nature on expense presence.
5. Cause no_fault over-draw (~3x both) — fold into the nature/cause pass or
   a later cause audit.
