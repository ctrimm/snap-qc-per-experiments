# Experiment 6 — Calibration v4: eligibility-screen injection
**Date:** 2026-09-28 · **Code:** `experiments/exp6_eligibility_screen.py`

## Hypothesis
North star gate: **calibration**. Exp 5 showed the calibration problem is in
*who gets errors*: a flat injection rate can't reproduce the real finding
mix because real error risk is strongly conditioned on household features.
We hypothesized that stratifying injection on earnings status — the single
strongest observable risk gradient — would close most of the remaining
finding-mix gap (L1 = 0.191 at exp 5).

## Method
- From the real FY2024 file: P(error | earner) = 0.592, P(error |
  non-earner) = 0.324 (earner = FSEARN > 0).
- Also measured the *conditional* bucket and nature mixes:
  P(bucket | earner) vs P(bucket | non-earner), and
  P(nature | bucket, earner) vs P(nature | bucket, non-earner). On earners,
  variances are earned 0.557 / shelter 0.178 / unearned 0.131; on
  non-earners, shelter 0.438 / unearned 0.307 / sua 0.105 / medical 0.080.
- `inject()` now works as an eligibility screen: draw earner status from the
  case, apply a calibrated per-stratum coin (see the methodology companion),
  and draw bucket/nature from the stratum-conditional mix.
- `build_dist.py` emits `bucket_probs_given_earner/no_earner` and
  `nature_given_bucket_earner/no_earner`; a shared loader
  (`src/synth/distutil.py`) serves dist.json + eff.json + inject.json with
  int-key normalization; `generate.py`, `measure_effectiveness.py`, and
  `calibrate_injection.py` were refactored onto it.
- 20,000 cases, retry budget 12, compared against exp 5 and the real file.

## Results
| Mix (correct / over / under) | correct | over | under | L1 vs real |
|---|---|---|---|---|
| Real FY2024 | 0.603 | 0.239 | 0.158 | — |
| Exp 5 | 0.698 | 0.193 | 0.109 | 0.191 |
| **Exp 6 (final)** | **0.604** | **0.235** | **0.161** | **0.009** |

Realized error rate: 0.396 (real: 0.397). Over share of errors: 0.593
(real: 0.602).

Element buckets, real vs synth (ratio):
shelter 0.94x, earned 0.97x, unearned 1.00x, sua 1.34x, medical 0.19x,
hhcomp 2.96x, arithmetic 3.33x, depcare 0.05x.

Nature mix, real vs synth (ratio): 97 at 0.91x, 38 at 0.86x, 53 at 0.92x,
56 at 1.02x, 35 at 1.14x, 52 at 1.24x, 44 at 1.10x, 99 at 0.95x, 57 at
0.62x, 37 at 0.89x.

## Verdict
Hypothesis **held decisively**. The finding mix went from L1 = 0.191 to
**L1 = 0.009** — the synthetic prior now matches the real QC file on the
headline calibration target, with the realized error rate (0.396) and the
over/under split both within a point of real. The top three element buckets
(shelter, earned, unearned — 78% of real variances) all calibrate to
0.94–1.00x, and the nature taxonomy is mostly within 0.6–1.2x.

Residuals are now *mechanics* gaps, not calibration gaps: hhcomp 2.96x and
arithmetic 3.33x come from retry-loop selection bias (always-applicable
buckets win the retry lottery — the per-bucket-persistence fix is staged as
exp 7); medical 0.19x and depcare 0.05x need senior/kid-conditioned bucket
mixes and better deduction mechanics; sua 1.34x needs the SUA mechanics
rework. None of these move the finding mix materially.

## Next steps
1. (Recommended) Re-run transfer (exp 4) on this generator — the finding and
   binary tasks should improve substantially with the prior fixed.
2. Exp 7: per-bucket persistence in the retry loop (draw the bucket once
   from the empirical mix, retry natures within it) to kill the
   hhcomp/arithmetic selection bias now binding element transfer.
3. Senior-conditioned bucket mixes (earner × senior cells) for medical;
   kid-conditioned mixes for depcare.
4. SUA mechanics rework (flat-grant vs expense choice) and the unearned /
   shelter error-gradient work.
