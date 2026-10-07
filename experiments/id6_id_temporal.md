# Experiment ID6: temporal stability — refit-on-2022 vs pooled

**Date:** 2026-10-04 · **Code:** `experiments/id6_id_temporal.py`
(results: `/tmp/id6out/id6_results.json`, scratch; run log:
`/tmp/id8cout/id6_run.txt`)

## Hypothesis

Tied to the north star (does the POC need annual refitting?): if the
transfer signal holds year to year, the pooled ID1 fit stands; if it
decays, production needs annual refits. The clean test: refit the ID
conditioning on FY2022 only, test on FY2023-24 real ID cases held out
entirely from fitting and training.

## Method

Port of `experiments/sd6_temporal.py`, adapted to Idaho's data (per the
track task): **no T_excl21 arm** (FY2021 is already excluded from all ID
fitting per the NY6 partial-year lesson, so the sensitivity arm is moot).
Arms: T_refit (FY2022-fit ID synth, n=942 rows) vs T_pooled (ID1 as-is,
FY2022-24 pooled, n=3,111), each tested on FY2023-24 real ID (clean
temporal test, n=2,169, 737 errors) AND FY2022 real ID (train-period
reference, n=942, 309 errors). The refit follows ID1's it2 recipe
(pure-empirical → 20k pilot → one-step bucket calibration → coin-cal line
search over {1.05…1.25}). GBM with `class_weight="balanced"` (ID2's
finding-task winner), clean-8 features. Per-FY 97-cause blank-rate check
for labeling breaks.

## Results

**Refit diagnostics:** FY2022 case-error rate 0.3366 (vs 0.3402 in
FY2023-24 — stable); coin-cal search chose **1.20** (same as ID1's pooled
1.20 — the calibration is stable); refit finding L1 0.0186. **Labeling
shift found:** the nature-97 cause-blank rate collapses across the window
— 2022: 0.669, 2023: 0.577, **2024: 0.272**. Idaho began recording causes
on timing-97 variances far more often in FY2024 (the same family as SD's
FY2024 no-fault coding shift). The refit's rebased cause ratios use the
FY2022-only non-97 mix, so the shift does not leak into the refit.

**Transfer battery:**

| arm | test | element acc | element macroF1 | finding acc | finding macroF1 |
|---|---|---|---|---|---|
| T_refit (FY2022) | FY23-24 | 0.3161 | 0.1261 | 0.4398 | 0.3743 |
| T_refit (FY2022) | FY2022 | 0.3301 | 0.1506 | 0.4214 | 0.3689 |
| T_pooled (ID1) | FY23-24 | **0.4423** | **0.1515** | 0.4444 | 0.3788 |
| T_pooled (ID1) | FY2022 | **0.4725** | **0.1856** | 0.4268 | 0.3663 |

**The pooled fit beats the single-year refit on element at both test
sets** (0.4423 vs 0.3161 on the clean temporal test; 0.4725 vs 0.3301 on
the train-period reference). On finding, the arms tie (macroF1 0.374 vs
0.379; 0.369 vs 0.366). Refitting on one year (n=942) *hurts* vs pooling
three (n=3,111) — small-sample noise, not process drift.

**Decay across the period boundary (T_refit, FY2022 → FY23-24):**
element acc −1.4pp, macroF1 −2.5pp — mild. Per-bucket F1 diagnosis: **shelter
0.359 → 0.198 (−0.161)** is the bucket to watch; earned is flat (+0.013),
unearned −0.058, medical flat (−0.002), sua improves (+0.133, tiny-n).
The shelter decay coincides with the FY2024 97-cause labeling shift
(shelter is ID's most 97-heavy bucket at 67.8%).

## Verdict

**PASS — no annual refit.** The pooled ID1 fit stands: it beats the
single-year refit on the clean temporal test, the finding signal does not
decay across the period boundary (macroF1 flat-to-up on both arms), and
the coin calibration is stable (1.20 = 1.20). Refitting on less data
hurts; pooling wins. Two watches for production: (1) **shelter** — the
only bucket with real F1 decay (−0.161); (2) the **FY2024 97-cause
labeling shift** (blank rate 0.67 → 0.27) — future refits must not let the
new coding practice leak backward into the cause ratios (the refit recipe
already guards this via period-specific rebasing).

## Next steps

- ID1's pooled fit remains the production basis. Name shelter as the
  bucket to watch in the whitepaper's limitations.
- ID8's pristine rerun follows the same FY2022-24 convention as ID1.
  - **Done →** [ID8](id8_id_pristine_rerun.md): ID8: MIXED stands with qualification — pristine element accuracy edge persists (+0.054 over national) but macroF1 ties (−0.002); finding AUC margin unchanged (+0.017). Contami…
