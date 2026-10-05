# Experiment 50 — offsets excluding the pandemic years (FY2022–2024 refit)

**Date:** 2026-10-03 · **Code:** `experiments/exp50_offsets_ex_pandemic.py` · **Results:** `/tmp/exp50_results.json` (not committed)

## Hypothesis

The PA/NY state offsets baked into `src/synth/pa_state.py` / `src/synth/ny_state.py`
were fit on pooled FY2020–2024 QC microdata. FY2020 was a partial file (27,112
rows nationally) and FY2021 collapsed (9,832 rows nationally; NY 221, PA 189 rows).
NY6 already showed partial-year files can move fitted quantities — FY2021's 221 NY
rows moved the fitted NY error rate 1.9pp. If the pandemic years distort the
offsets, refitting on FY2022–2024 only (PA n=2,448 / NY n=2,637, vs pooled 3,268 /
3,257) should move the baked constants materially, and any published conclusion
built on them (pa_state/ny_state docstring claims, the PA/NY-conditioned training
data behind the POCs) needs revisiting. Gate: calibration — the offsets ARE the
state dimension of the generator's calibration.

## Method

Called PA1's `fit_pa_targets` and NY1's `fit_ny_targets` with `fys=[2022, 2023,
2024]` — the exact fitting recipe (same sparsity guards, same FYWGT weighting;
the `fit` CLI has no `--fys` flag, so the filter is applied by calling the fit
functions directly). Compared every fitted constant against the pooled
FY2020–2024 refit with the same recipe (apples-to-apples; "new minus old").

Sanity check: the pooled refit reproduces the baked constants exactly
(PA_S_OVER 0.9118, PA_S_UNDER 0.8571, NY_S_OVER 1.0294, NY_S_UNDER 1.0,
PA_CAUSE97_BLANK 0.0, NY_CAUSE97_BLANK 0.2189 — all diff 0.0000), so the
comparison is the recipe speaking, not a version skew. One caveat carried
forward: the baked `*_BUCKET_RATIO` include a one-step realized-output
calibration (documented in pa1's fit notes); the deltas here are pure-empirical
old vs pure-empirical new, i.e. the recipe's own sensitivity.

QC microdata was read-only throughout; nothing written to `snap-qc-data/` beside
the repo checkout; no microdata committed.

## Results

National reference also shifts when FY2020–21 leave: national case error rate
0.3849 → 0.3992, national dollar rate 0.0859 → 0.0868 (FY2022–24 only).

### PA (pooled n=3,268 → FY22–24 n=2,448; FY2020–21 contributed 820 PA rows)

| offset | pooled | FY22–24 | delta | rel |
|---|---|---|---|---|
| case_err_rate | 0.4125 | 0.4435 | +0.0310 | +7.5% |
| dollar_rate | 0.0846 | 0.0943 | +0.0097 | +11.5% |
| p(over\|err) | 0.5985 | 0.6126 | +0.0141 | +2.4% |
| medO / medU ($) | 31 / 18 | 33 / 21 | +2 / +3 | +6.5% / +16.7% |
| s_over / s_under | 0.9118 / 0.8571 | 0.8684 / 0.9130 | −0.0433 / +0.0559 | −4.8% / +6.5% |
| bucket: shelter | 1.4420 | 1.4233 | −0.0186 | −1.3% |
| bucket: unearned | 0.6846 | 0.5980 | −0.0865 | −12.6% |
| bucket: sua | 0.6164 | 0.7317 | +0.1153 | +18.7% |
| bucket: earned | 0.9347 | 1.0224 | +0.0877 | +9.4% (crosses 1.0) |
| bucket: hhcomp | 0.9475 | 1.2205 | +0.2730 | +28.8% |
| bucket: medical | 1.1623 | 0.9855 | −0.1767 | −15.2% (crosses 1.0) |
| coin_earner / no_earner | 0.9635 / 1.1351 | 1.0312 / 1.1383 | +0.0677 / +0.0032 | +7.0% / +0.3% |
| cause: unearned_other | 0.9828 | 1.6206 | +0.6379 | +64.9% |
| cause: earned_other | 0.5736 | 0.8424 | +0.2688 | +46.8% |
| cause: shelter_other | 0.8191 | 0.5578 | −0.2612 | −31.9% |
| cause: medical_other | 0.4356 | 0.2001 | −0.2355 | −54.1% |
| 97share_medical | 0.2497 | 1.0000 | +0.7503 | guard flip (see below) |
| 97resolve_medical | 0.3998 | 1.0000 | +0.6002 | guard flip (see below) |
| dir_over/under_shelter | 1.1536 / 1.2187 | 1.2055 / 1.2773 | +0.0518 / +0.0586 | +4.5% / +4.8% |
| cause97_blank | 0.0000 | 0.0000 | 0.0000 | unchanged |

PA/national error-rate ratio rises 1.072 → 1.111 (case) and 0.985 → 1.086 (dollar):
PA was "about national" on the dollar rate pooled; FY22–24-only it runs ~9% above.

### NY (pooled n=3,257 → FY22–24 n=2,637; FY2020–21 contributed 620 NY rows)

| offset | pooled | FY22–24 | delta | rel |
|---|---|---|---|---|
| case_err_rate | 0.3655 | 0.3691 | +0.0037 | +1.0% |
| dollar_rate | 0.0854 | 0.0838 | −0.0016 | −1.9% |
| p(over\|err) | 0.5750 | 0.5741 | −0.0010 | −0.2% |
| medO / medU ($) | 35 / 21 | 37 / 25 | +2 / +4 | +5.7% / +19.0% |
| s_over / s_under | 1.0294 / 1.0000 | 1.0000 / 1.0870 | −0.0294 / +0.0870 | −2.9% / +8.7% |
| bucket: medical | 1.7477 | 1.2729 | −0.4748 | −27.2% |
| bucket: hhcomp | 1.5846 | 1.6096 | +0.0250 | +1.6% |
| bucket: shelter | 0.8105 | 0.8771 | +0.0666 | +8.2% |
| bucket: sua | 1.2056 | 0.9712 | −0.2344 | −19.4% (crosses 1.0) |
| 97share_sua | 2.3192 | 2.2866 | −0.0326 | −1.4% (holds) |
| 97share_arithmetic | 7.2122 | 9.1093 | +1.8971 | +26.3% (fragile, ~8–9 cases) |
| 97share_depcare | 1.4163 | 1.0000 | −0.4163 | guard flip (see below) |
| 97resolve_hhcomp | 1.2393 | 0.8506 | −0.3887 | −31.4% (n=10→8) |
| dir_under_shelter | 1.5910 | 1.9082 | +0.3173 | +19.9% (under-skew strengthens) |
| dir_over_shelter | 0.5744 | 0.3908 | −0.1836 | −32.0% |
| cause: sua_other | 0.4750 | 0.0000 | −0.4750 | sparse cell (zero 'other' causes in window) |
| cause: unearned_other | 0.4979 | 0.8634 | +0.3655 | +73.4% |
| coin_no_earner | 0.9535 | 0.9080 | −0.0455 | −4.8% |
| cause97_blank | 0.2189 | 0.1873 | −0.0316 | −14.4% |

NY/national error-rate ratio: 0.942 → 0.914 (case), 0.9945 → 0.9584 (dollar) —
NY stays the below-national state on both.

### Guard-flip artifacts (recipe, not signal)

Three of the largest deltas are the sparsity guard firing differently, not
empirical movement: PA 97-share medical (0.2497 → 1.0) and PA 97-resolve medical
(0.3998 → 1.0) — unweighted 97-n went 5 → 3, below the ≥5 guard; NY 97-share
depcare (1.4163 → 1.0) — 97-n went 5 → 4. These cells are too thin to condition
on in the FY22–24 window and should not drive the verdict.

## Verdict

**Yes, the pandemic years move the offsets — measurably, but no published
conclusion flips.** Max |delta| across all fitted constants is +1.90
(NY 97-share arithmetic, 7.2122 → 9.1093 — a ~8-case fragile cell, excluded from
the honest max). The honest max is **+0.64 (PA cause unearned_other,
0.9828 → 1.6206)** and **−0.47 (NY bucket medical, 1.7477 → 1.2729)**.

PA/NY headline deltas: PA case rate +3.1pp (+7.5%), PA dollar rate +0.97pp
(+11.5%), NY case rate +0.4pp (+1.0%), NY dollar rate −0.16pp (−1.9%). In
PA/national-ratio terms: PA 1.072 → 1.111 (case), 0.985 → 1.086 (dollar);
NY 0.942 → 0.914 (case), 0.9945 → 0.9584 (dollar).

Published-conclusion audit:
- PA "errs more often than national, with smaller errors" — holds and strengthens
  (case ratio 1.11; s_over 0.87 / s_under 0.91 still < 1).
- PA "shelter-heavy (1.44x), unearned-light (0.68x)" — holds (1.42x / 0.60x).
- PA "earned-light" 0.93 → 1.02 softens to neutral; medical 1.16 → 0.99 crosses 1.0
  both ways — minor claims, direction unchanged on the flagship.
- NY "errs less often, dollar rate matches" — holds (ratios 0.91 / 0.96).
- NY "medical-heavy (1.75x)" — **weakens to 1.27x**; direction holds, but the
  magnitude is the one published claim whose basis should be quoted as
  pooled-FY2020–24, since the pandemic years carried a disproportionate share of
  NY medical variances (82 → 59 unweighted). This is the single material
  distortion found.
- NY "hhcomp-heavy 1.58x / shelter-light 0.81x / sua 97-share 2.32x" — all hold
  (1.61x / 0.88x / 2.29x).
- The PA POC economics ($6,074 vs $3,851 random at 20% review budget, exp44) and
  the ranker results are a separate pipeline — refitting offsets does not change
  any published number there without a full pa2 rerun.

So: the pandemic years do distort the cross-state offsets (PA's error levels and
NY's medical mix most), but every directional published conclusion survives; the
only conclusion needing a basis note is NY's medical-heavy magnitude.

## Next steps

1. **Recommended:** if the NY-conditioned training data is ever refreshed, quote
   the medical-heavy claim with its basis ("1.75x pooled FY2020–24; 1.27x on
   FY2022–24") — a one-line docstring basis note in `src/synth/ny_state.py`.
   (Not doing it here: exp50 does not modify existing files.)
2. A real refit decision (rebaking PA/NY constants on FY2022–24) would modestly
   re-condition PA upward (+3.1pp error rate) and soften NY medical conditioning;
   worth doing only alongside a pa2/ny2 transfer rerun so the ranker numbers move
   or stay put on evidence, not on arithmetic.
3. The fragile small cells (NY arithmetic 97-share ~8 cases, PA/NY medical/depcare
   97 guards, NY sua 'other' causes at zero) are the wrong lever for annual
   refitting — any FY-window refit should keep or raise the sparsity guards
   rather than chase them.
