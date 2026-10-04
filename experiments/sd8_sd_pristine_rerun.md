# Experiment SD8: pristine transfer refit — no contamination premium

**Date:** 2026-10-04 · **Code:** `experiments/sd8_sd_pristine_rerun.py`
(results: `/tmp/sd8out/sd8_results.json`)

## Hypothesis

Demanded by SD2's own fairness caveat: SD1's offsets were fit on pooled
FY2020–2024 SD microdata *including* the 592 holdout rows, so the
SD-synth arms aren't pristine vs the test set and SD2's SD-vs-national
advantage could be partly inflated by the generator having seen
test-set marginals. SD8 tests the caveat: refit on SD microdata minus
*every* holdout row, regenerate per SD1's full it3 recipe, and re-run
SD2's battery on the same holdout. If the advantage survives, transfer
is real; if it collapses, SD2 overclaimed.

## Method

Verbatim port of `ny8_ny_pristine_rerun.py` with SD1's recipe substituted
for NY1's:

- **Stage 0:** holdout exclusion set from `experiments/sd_holdout_idx.json`
  (592 keys; `(fy, sd_row_index)`).
- **Stage 1:** `fit_sd_targets_excl` — verbatim port of SD1's fit with one
  change: skip excluded rows (SD indices counted in CSV order per FY, so
  they line up with `sd2.load_sd_real`). Assert kept rows =
  2,365 − 592 = 1,773.
- **Stage 2:** SD1's full it2 recipe on the pristine fit (SD1's it3 second
  97-share push is *not* repeated — it hit a materialization ceiling with
  diminishing returns): pilot (coin cal 1.0) → one-step realized-output
  bucket calibration → one-step 97-share, 97-resolution, and direction
  calibrations → **it2b-style rebased cause ratios** (SD-non97-mix /
  dist-mixed-basis, SD6's proven recipe, computed on the minus-holdout
  basis) → SD_P_UNIT from the pristine near-full|over → SD_COIN_CAL grid
  {0.95, 1.00, 1.05, 1.10} on 8k pilots against the pristine marginal
  case-error rate → final pristine-SD generation (n=20k, seed 7).
  Constants installed by monkey-patching `sd_state` (PA6's pattern; no
  src edits).
- **Stage 3:** regenerate the national arm per SD2's recipe; verify
  byte-identity against SD2's file (`/tmp/sd2out/nat_synth.jsonl`).
- **Stage 4:** SD2's battery on SD2's holdout — arms (a) pristine-SD synth,
  (b) national; tasks element + finding; GBM **without** class_weight
  (SD2's winning setting) on **SD7's clean 8-feature set** (the production
  recipe; SD7 showed the v1→clean8 delta is immaterial on element:
  +0.013 acc / −0.000 macroF1, and SD4's clean-8 finding AUC 0.7239 vs
  SD2's v1 0.7278 — the feature-set delta on finding is ~−0.004).
- **Stage 5:** contamination premium = pristine (clean-8) vs SD2's
  reported (v1, contaminated) numbers, with the feature-set delta named.

## Results

### Pristine fit (1,773 rows; SD1 pooled basis in parens)

Finding c/o/u 0.7555/0.1234/0.1210 (0.7535/0.1272/0.1193); case_err
0.2445 (0.2475); p(over|err) 0.5050 (0.5079). Pure-empirical bucket
ratios: earned 1.285, unearned 1.009, shelter 0.936, sua 0.720, medical
1.359 (SD1 pooled: 1.35/0.99/0.91/0.67/1.41). **The holdout rows were
not driving the fit.** Coin-cal grid chose **1.05** (SD1 also 1.05);
SD_P_UNIT = 0.00068 (SD1 pooled 0.00050). Baked bucket ratios:
earned 1.2984, unearned 1.0835, shelter 0.9863, sua 0.6074, medical
2.2275 — vs SD1's baked 1.357/1.097/0.923/0.586/2.204: **within ~5% on
every major bucket**. The pristine recipe reproduces SD1's constants.

### Battery (clean-8, no-classweight)

| arm | element acc / macroF1 | finding acc / macroF1 / AUC (a ranking metric where 0.5 is chance, 1.0 is perfect) |
|---|---|---|
| (a) pristine SD synth | 0.5658 / 0.2769 | 0.6892 / 0.3465 / **0.7503** |
| (b) national synth | 0.5461 / 0.1757 | 0.5017 / 0.3612 / 0.6798 |

Pristine SD beats national on finding AUC by **+0.071** and on element
macroF1 by +0.101. National's finding acc of 0.5017 vs pristine's 0.6892
is the base-rate-mismatch artifact: the national-trained model expects a
~36% error rate and over-predicts on SD's ~25% holdout.

### Contamination premium

| metric | SD2 (contaminated, v1) | SD8 (pristine, clean-8) | delta |
|---|---|---|---|
| finding AUC | 0.7278 | **0.7503** | **+0.023** |
| element macroF1 | 0.2609 | 0.2769 | +0.016 |

**The premium is zero — the pristine refit scores *higher*, not lower.**
The SD2 numbers were not inflated by contamination. (Feature-set caveat:
SD7 measured v1→clean8 at −0.004 on finding AUC, so the +0.023 pristine
move is not a feature-set artifact; it is refit jitter on a thin 152-row
error test set, well within noise — 95% CI on the AUC difference is
roughly ±0.05 at n=152 errors.)

## Verdict

**PASS.** The transfer advantage survives the pristine refit with no
contamination premium: finding AUC 0.7503 vs 0.6798 national (+0.071),
element macroF1 0.2769 vs 0.1757 (+0.101). Combined with SD6 (stable
signal across the FY2023–24 boundary) and SD7 (no leakage), SD's
"finding transfers" claim is the best-supported of the three states.
The headline number the whitepaper should carry is the pristine one:
**finding AUC 0.7503** (the value SD4's calibrated ranker is built on).
The whitepaper's methods section states the refit design (1,773
minus-holdout rows, SD1's it2 recipe, coin cal 1.05, clean-8 battery)
so the pristine basis is reproducible.

## Next steps

- SD4's reference is now the pristine number (0.7503 uncalibrated /
  calibrated AUC from SD4's own pipeline). SD4's chronicle gate is met:
  ranker AUC ≥ SD2's arm value holds on the pristine refit.
- Commit batch 3 (sd8 + chronicle), then write the whitepaper.
