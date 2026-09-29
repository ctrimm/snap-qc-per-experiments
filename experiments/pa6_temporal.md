# PA6 — temporal stability: does the PA signal hold year to year?

**Date:** 2026-09-29 · **Code:** `experiments/pa6_temporal.py`

## Hypothesis

PA1's PA-conditioning offsets were fit on pooled FY2020–2024 PA microdata,
which launders recent-year marginals into the "training" side of any
temporal test. If the PA signal (which buckets, which directions, which
causes) is genuinely process-layer — exp33's claim — then a model trained
on FY2020–22-fit synthetic should predict FY2023–24 real PA cases about as
well as it predicts FY2020–22 cases, and refitting on old years should cost
little versus the pooled fit. If instead the signal is year-specific, the
temporal test will decay and the POC needs annual refitting. Gate: transfer
(the north star's transfer gate, extended across time).

## Method

**Refit (this experiment's work):** called PA1's `fit_pa_targets` with
`fys=[2020, 2021, 2022]` (the `fit` CLI subcommand has no `--fys` flag — it
always fits pooled; the year filter is applied by calling the fit function
directly from this script, documented here). PA rows: 1,637 (FY2020 631 /
FY2021 189 / FY2022 817). Converted the fit output to `pa_state` constant
overrides with PA1's identical guards, installed by monkey-patching the
`src.synth.pa_state` module attributes (no src file modified; every
generator function reads these globals at call time), then replicated
PA1's it2→it3 recipe:

1. pure-empirical FY2020–22 bucket ratios: earned 0.855, unearned 0.797,
   shelter 1.460, medical 1.372; sua/depcare/hhcomp/arithmetic guarded to
   1.0 (PA unweighted n < 25 in the FY2020–22 window — sua and hhcomp lose
   their pooled-fit adjustments);
2. one-step realized-output bucket calibration × real_PA_share/synth_share
   on a 20k-case pilot (multipliers: earned 1.073, unearned 1.098,
   shelter 1.078, medical 1.411);
3. PA_COIN_CAL line search on 8k-case pilots — chosen **1.00** (not PA1's
   1.08: the FY2020–22 target case-error rate 0.3857 is already landed at
   1.0; PA1's 1.08 was compensating the pooled 0.4125);
4. final generation n=20,000, seed 7 (PA2's n/seed conventions) →
   refit finding L1 vs real PA FY2020–22 = 0.0163.

exp34's codebook caution is handled: nature/cause offsets are pinned to the
FY2024 `dist.json` convention (the generator's national base), and PA
recorded a cause on every nature-97 in all FYs (blank 0.000), so no PA-side
labeling break is laundered. The element/finding labels (STATUS, ELEMENT
codes) are stable across the window.

**Arms (all: PA2's recipe — v1 features, sklearn
HistGradientBoostingClassifier(random_state=0), defaults, no class_weight):**
- T_refit: FY2020–22-fit PA synth → tested on FY2023–24 real PA (clean
  temporal test, 1,631 rows, 739 error cases) AND on FY2020–22 real PA
  (train-period reference, 1,637 rows, 655 error cases).
- T_pooled: pooled-fit PA synth (PA1 as-is, generated before any patching)
  → same two test sets (does refitting on old years matter?).
- Reference: PA2's same-period numbers (arm b, pooled fit, stratified 75/25
  holdout of FY2020–2024: element acc 0.567 / macroF1 0.208; finding acc
  0.388 / macroF1 0.362) — approximate, different test construction.

**Caveats (both directions):** the FY2020–22 test set for T_refit, and the
FY2023–24 test set for T_pooled, share their rows' *marginals* with the
respective offset fits (PA2's caveat, unchanged). This slightly favors the
pooled arm in the head-to-head.

## Results

### Headline: element + finding, both arms, both periods

| arm | test | element acc | element macroF1 | finding acc | finding macroF1 |
|---|---|---|---|---|---|
| T_refit (FY20–22 fit) | FY23–24 | 0.5061 | 0.2143 | 0.4549 | 0.4040 |
| T_refit (FY20–22 fit) | FY20–22 | 0.5221 | 0.1860 | 0.3531 | 0.3168 |
| T_pooled (PA1 as-is) | FY23–24 | 0.5332 | 0.2164 | 0.4261 | 0.3983 |
| T_pooled (PA1 as-is) | FY20–22 | 0.5435 | 0.1961 | 0.3622 | 0.3448 |
| PA2 reference (same-period) | pooled holdout | 0.567 | 0.208 | 0.388 | 0.362 |

**Train-period vs test-period gap (T_refit):** element acc −0.016
(0.5221 → 0.5061), macroF1 **+0.028** (0.1860 → 0.2143). No decay on the
gate metric. Finding acc +0.102 / macroF1 +0.087 — a rise, not a decay.

**Does refitting on old years matter (T_refit vs T_pooled on FY23–24)?**
Element: pooled +0.027 acc, macroF1 a wash (0.2164 vs 0.2143). Finding:
refit +0.029 acc, macroF1 a wash. Small, mixed, and the pooled arm had the
caveat advantage (its fit saw the test marginals). No meaningful penalty
for fitting on 2020–2022 only.

### The finding-task swing is a prior story, not signal

Real PA case-error rate: 0.3857 (FY20–22) → 0.4509 (FY23–24), +6.5pp;
p(over|err) 0.5755 → 0.6267; finding-mix L1 between periods = 0.130.
The refit synth's P(error) = 0.388 matches the *fit* period. PA2 showed the
synth-trained classifier predicts error too eagerly (below majority on
hard accuracy); on FY23–24 that bias is punished less because the true
error rate is higher. The accuracy "improvement" across time is prior
match, not better signal — do not read it as transfer gain.

### Per-bucket F1 decay diagnosis (T_refit, FY20–22 → FY23–24, element task)

| bucket | FY20–22 F1 | FY23–24 F1 | delta | test-set n |
|---|---|---|---|---|
| shelter | 0.664 | 0.663 | −0.001 | 301 → 330 |
| earned | 0.563 | 0.546 | −0.017 | 137 → 193 |
| unearned | 0.358 | 0.279 | **−0.080** | 124 → 91 |
| medical | 0.121 | 0.240 | +0.119 | 41 → 30 |
| sua | 0.000 | 0.037 | +0.037 | 23 → 46 |
| arithmetic/depcare/hhcomp/childsupport/other | ≤0.267 | noisy | ± | ≤11 each |

The two dominant buckets (shelter, earned) are flat. The one real decay is
**unearned** (−0.080), tracking a genuine mix shift: unearned's share of PA
variances fell 0.19 → 0.12 between the periods (FY2023 sua also surged to
0.092 of variances vs 0.016–0.041 elsewhere — the model does not capture
that surge, F1 still ~0, but sua is too rare to move the headline).
Medical improves but stays low (the mechanics gap exp4_v3 flagged, not a
temporal story).

### FY2021 instability (the partial-year file)

FY2021 is Jul–Sep only: 189 PA rows (11.5% of the fit). Including it moves
the fit: finding c/o/u 0.5848/0.2503/0.1649 → 0.6143/0.2220/0.1637,
case-error rate 0.4152 → 0.3857 (−3pp), p(over|err) 0.6029 → 0.5755.
Bucket ratios move modestly (earned 0.888→0.855, unearned 0.773→0.797,
shelter 1.481→1.460, medical 1.364→1.372). The FY2021 file alone runs hot
on correct (0.677 unweighted) — deep EA-era months. It also decided the
coin scalar (1.00 vs >1.00 without it). A production refit cadence should
drop partial years or weight by months covered.

## Verdict

**The PA signal holds year-to-year well enough for the POC; annual
refitting is not required.** The element gate metric (accuracy) decays by
1.6 points across a period with a real +6.5pp case-error-rate drift and a
−7pp unearned-mix shift, while macroF1 rises; per-bucket F1s are flat in
the dominant buckets (shelter −0.001, earned −0.017); and the pooled fit —
which cheats by seeing the test marginals — buys only ~2.7pp on accuracy,
within noise. The finding task's cross-period swings are prior-calibration
artifacts (already flagged by PA2), not signal decay: refit the P(error)
prior per era (or threshold-tune on a recent real slice per PA2's PA4
note), don't retrain the element model annually. Two process notes for any
future refit: (1) exclude partial-year files — FY2021's 189 rows moved the
fitted error rate by 3pp and set the coin scalar; (2) the one bucket to
watch is unearned, the only one with a real temporal decay (−0.080),
tracking its shrinking variance share.

## Next steps

- **PA4 (P(error)):** gate on calibrated binary AUC per era, not hard
  accuracy — the finding task is prior-dominated and the prior drifts
  (+6.5pp FY20–22 → FY23–24). Threshold-tune on a recent real-PA slice.
- Refit cadence decision for production (not POC): biennial refit with a
  standing unearned-bucket watch (the decayed bucket), and a rule to drop
  partial-year QC files from the fit. One-line change, no experiment.
- Optional: rerun the T_refit arm excluding FY2021 to quantify the scalar
  choice's effect on transfer (fit says scalar would move >1.0; transfer
  impact unknown). Cheap — fits in one script run.
