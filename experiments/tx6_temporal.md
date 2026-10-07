# TX6 — Temporal stability: refit-on-2020–22 vs pooled on held-out 2023–24

**Date:** 2026-10-03 · **Code:** `experiments/tx6_temporal.py`

## Hypothesis

TX3 found a genuine regime change: TX's errors flipped from over-tilted
(FY2020-21: 59%/57% over) to under-tilted (FY2022-24: 45%/48%/49% over).
If the transfer signal is temporally stable, a generator refit on
FY2020-22 should still predict FY2023-24 errors — or the POC needs annual
refitting. Plain-language terms: GBM = gradient-boosted trees; the
"clean temporal test" = train on FY2020-22-fit synthetic, test on real
FY2023-24 TX rows the refit never saw.

## Method

Three synth arms, same GBM recipe (no class_weight), element + finding
tasks: **T_refit** (fit on FY2020-22 TX microdata via TX1's recipe:
pure-empirical ratios → 20k pilot → one-step bucket calibration →
coin-cal line search over {0.94,...,1.02}); **T_pooled** (TX1 as-is,
pooled FY2020-24); **T_excl21** (FY2020+22 fit, excluding the partial-year
FY2021 — the NY6 sensitivity arm). Tested on real TX FY2023-24 (clean
temporal test, n=1,797) AND on FY2020-22 (train-period reference, n=1,660).
Per the NY6 lesson, partial-year FY2020-21 files are excluded from the
*refit* (documented); the pooled TX1 fit keeps them for n. The refit uses
TX1's bucket-only one-step recipe (the 97-share it2b refinement is not
replicated — documented simplification; it affects cause fidelity, not the
transfer tasks).

## Results

**Fits:** FY20-22 (n=1,660): case_err 0.4297, p(over|err) 0.5341;
excl21 (n=1,478): case_err 0.4371, p(over|err) 0.5182; FY23-24 ref
(n=1,797): case_err 0.4414, p(over|err) 0.4860. The under-tilt deepens in
the test period (0.534 → 0.486 over-share).

**Labeling break found:** TX's nature-97 cause-blank rate is 1.0000 in
FY2020-2023 and 0.0000 in FY2024 — TX went from blanking *all* 97 causes
to recording *all* of them in a single year. (The pooled TX1 fit at 0.7995
averages across this break.) This does not affect the transfer tasks
(causes are not features), but any TX cause-mix analysis must stratify by
FY.

| Arm | Test | Element acc | Finding acc |
|---|---|---|---|
| T_refit (FY20-22) | FY23-24 (clean) | 0.4406 | 0.4240 |
| T_refit (FY20-22) | FY20-22 (train ref) | 0.4069 | 0.3380 |
| T_pooled (TX1) | FY23-24 (clean) | 0.4406 | **0.4680** |
| T_pooled (TX1) | FY20-22 (train ref) | 0.3779 | 0.3922 |
| T_excl21 (FY20+22) | FY23-24 (clean) | **0.4581** | 0.4023 |
| T_excl21 (FY20+22) | FY20-22 (train ref) | 0.4221 | 0.3452 |

**Element:** no decay across the boundary — T_refit *improves* +0.034
(0.4069 → 0.4406) on the clean test, a mix-alignment rise like NY6's
(+0.089). On the clean test, T_refit ties T_pooled (0.4406) and T_excl21
wins (0.4581).

**Finding:** T_refit improves +0.086 across the boundary (0.3380 →
0.4240) — the signal holds despite the direction flip. But on the clean
test, T_pooled (0.4680) beats T_refit (0.4240).

**Per-bucket F1 decay (T_refit, train-period → test-period):** earned
+0.051, shelter +0.022, unearned +0.036, sua +0.013, medical +0.065 (no
decay on the major buckets); arithmetic −0.223 (n=37→19), depcare −0.256
(n=17→13) decay but on tiny samples. Buckets to watch: arithmetic and
depcare.

## Verdict

**PASS with a qualification.** The element gate metric does not decay —
it *rises* +0.034 across the period boundary, and the refit arm matches
pooled on the clean temporal test (0.4406 = 0.4406). The under-tilt flip
does not break transfer: finding accuracy rises +0.086 despite the regime
change. Qualification: on the finding task, T_pooled beats T_refit on the
clean test (0.4680 vs 0.4240) — the pooled fit's extra FY2023-24 data
helps more than the refit's period-purity. For production: **drop
partial-year QC files from refits** (T_excl21 wins element at 0.4581 —
the NY6 lesson replicates); watch arithmetic and depcare (the only
decaying buckets, both small-n); and stratify any cause-mix work by FY
(the FY2024 97-cause labeling break).

## Next steps

- **TX8** (pristine rerun) is the remaining temporal confound to close.
  - **Done →** [TX8](tx8_tx_pristine_rerun.md): TX8: PASS — the MIXED verdict is not a contamination artifact: pristine refit excluding all 865 holdout rows confirms finding edge, contamination premium +0.003 on finding AUC…
- The FY2024 97-cause labeling break (1.0 → 0.0 blank rate) should be
  verified against the FY2024 QC documentation — if TX changed its
  reviewer instructions, the generator's 0.7995 pooled blank rate needs a
  FY-conditional form.
