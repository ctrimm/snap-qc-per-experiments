# Experiment 18 — Dollar-error mechanisms
**Date:** 2026-09-29 · **Code:** `experiments/exp18_dollar_mechanisms.py`

## Hypothesis
North-star gate: **calibration**. exp16 found the dollar-error marginal had
drifted: synth p10 is 5.5x real ($22 vs $4), only 38% of synth errors fall
under the $56 tolerance vs 70% real, the over/under dollar asymmetry is
inverted at every quantile, and synth over p99 is $301 vs real $603.
Hypothesis: three generator mechanisms fix the drift — (1) a small-error
mode matching real QC's tiny-variance mass, (2) whole-unit ineligibility
(error = full issued benefit) for the extreme over tail, (3) repairing the
inverted over/under asymmetry. All three are prototyped **in-script** via
patches on `src/synth/errors.py`; production code is untouched, so a
verified mechanism can be merged later behind a flag, exp7-style.

A note on terms: *L1 distance* sums the absolute per-category differences
between two distributions (0 = identical); here it measures the finding-mix
(correct/over/under) gap. A *percentile* pK is the value below which K% of
cases fall.

## Method
- **Real side** (held-out validation; aggregates read from the FY2024 QC
  file, nothing per-row committed): 44,891 rows, 17,836 error cases.
  Signed dollar error = AMTERR signed by STATUS, as in exp16. Also measured
  two new aggregates to calibrate the mechanisms: the share of errors with
  AMTERR ≤ $56 **by direction** (over 0.636, under 0.785 — the small mass is
  under-heavy), and median AMTERR **by (STATUS, nature)** (table below).
- **Synth side**: 20,000 cases per config from the persistent generator with
  experiment-local patches:
  - *Small-error mode (v3):* timing variances (**nature 97**) take small
    perturbations (±$2–30 on the underlying amount, ~$1–9 on the benefit
    through the 30% pass-through; small truth/fabrication amounts on
    zero-base paths) instead of the coarse magnitudes the 97-resolution
    coin currently renders. Recorded under the same (element, nature)
    codes — QC natures don't distinguish magnitude — so the taxonomy mix is
    preserved. A small residual fraction for non-97 natures is grid-searched
    (0.25 over / 0.35 under in the best config). An earlier v2 (smallness by
    *direction* rather than nature) matched the marginal slightly better
    but had no basis in the data; the per-nature medians showed 97s are the
    real small mass (over p50 $20 / under p50 $15, p90 $49/$45; 44% of error
    cases carry a 97), so v3 conditions on 97.
  - *Whole-unit ineligibility:* with probability `p_unit` per case the unit
    is ineligible — correct benefit $0, dollar error = full issued benefit
    (an overissuance, element 150 / nature 99 / cause 10). Calibrated
    against the real 4.9% of overs with AMTERR ≥ 0.9 × RAWBEN
    (near-full-benefit errors).
  - *Recalibration:* the small mode raises attrition (perturbations that
    floor to $0 benefit change are dropped), so the exp7-calibrated
    injection coin under-realizes errors. The coin is scaled up in-script
    (`coin_scale`, on a deep copy of dist — `inject.json` untouched), and
    under-direction draw weights get an importance-weight boost
    (`under_boost`, exp13-style), because small unders are absorbed by the
    $23 minimum-benefit floor more often than small overs hit the
    max-allotment ceiling.
- Compared p10/p25/p50/p90/p99, mean, share ≤ $56, and the over/under gaps
  at each quantile, plus the finding-mix L1. Best config re-run on 3 seeds.

Real median AMTERR by (STATUS, nature) — the aggregate that drove v3:

| STATUS | nature | n | p50 | p90 |
|--------|--------|----:|----:|----:|
| over | 97 | 4083 | 20 | 49 |
| under | 97 | 3769 | 15 | 45 |
| over | 53 | 1444 | 71 | 210 |
| over | 38 | 1409 | 62 | 268 |
| over | 56 | 1361 | 47 | 191 |
| over | 35 | 1287 | 160 | 455 |
| under | 52 | 1005 | 59 | 177 |
| under | 44 | 742 | 43 | 206 |
| under | 57 | 562 | 18 | 94 |
| over | 37 | 539 | 99 | 357 |
| over | 7 | 221 | 231 | 466 |
| over | 98 | 203 | 11 | 127 |

## Results
Best config: 97-small + non-97 residual 0.25/0.35, `p_unit=0.0125`,
`coin_scale=1.05`, `under_boost=1.25`. Absolute dollar error, error cases:

| stat | real | baseline | best | ratio best/real |
|------|-----:|---------:|-----:|----------------:|
| p10  |    4 |       22 |    3 | 0.75 |
| p25  |   11 |       41 |    5 | 0.45 |
| p50  |   31 |       72 |   29 | 0.94 |
| p90  |  201 |      202 |  207 | 1.03 |
| p99  |  528 |      294 |  530 | 1.00 |
| mean | 71.5 |     93.6 | 66–74 | ~1.0 |
| share ≤ $56 | 0.70 | 0.38 | 0.62 | 0.89 |

Over-vs-under dollar asymmetry (absolute $ within each finding):

| stat | real over | real under | synth over | synth under | sign match? |
|------|----------:|-----------:|-----------:|------------:|:-----------:|
| median | 38 | 23 | 33 | 22 | yes |
| mean   | 86 | 49 | 73 | 68 | yes |
| p90    | 244 | 128 | 197 | 216 | **no** |
| p99    | 603 | 361 | 558 | 244 | yes |

Finding mix: real 0.603/0.239/0.158 (correct/over/under) vs best
0.623/0.252/0.125 — **L1 0.067 vs baseline 0.039** (3-seed range
0.064–0.070; all other stats stable across seeds within a few dollars).

What each mechanism contributed (ablation across the grid):
- 97-small alone (no unit, no recalibration): share ≤ $56 0.38 → 0.53;
  medians fall (medO 69→53, medU 81→43) but stay above real.
- Adding the non-97 residual (0.25/0.35): share ≤ $56 → 0.62,
  medO → 33, medU → 22 (real 38/23).
- Whole-unit ineligibility (`p_unit=0.0125`): over p99 301 → 530–558
  (real 603); also lifts over mean/p90, repairing the asymmetry sign at
  the top.
- `coin_scale=1.05` + `under_boost=1.25`: holds the total error rate near
  real after small-mode attrition; the under-draw boost lifts realized
  unders only modestly (+~10% for a 1.25x draw boost — sublinear, because
  97s, the "other" direction class, are unaffected and the extra under
  draws face the same floor absorption).

## Verdict
Hypothesis **partially held** — two mechanisms verify, the third mostly:

1. **Small-error mode: held.** Conditioning smallness on nature 97 (the
   empirically small mass) plus a modest non-97 residual moves p10 22→3,
   p25 41→5, p50 72→29, and share ≤ $56 0.38→0.62 against real 0.70.
2. **Whole-unit ineligibility: held.** Over p99 301→~535 (real 603);
   `p_unit=0.0125` reproduces the real 4.9% near-full-benefit over share.
3. **Asymmetry: mostly repaired.** The over>under sign is now correct at
   median, mean, and p99 (was inverted at all four levels). It remains
   inverted at **p90** (synth 197/216 vs real 244/128): the coarse under
   tail is still too heavy — real per-nature medians show synth's under
   magnitudes oversized (nature 44: real p50 $43; nature 57: real p50 $18;
   nature 52: real p50 $59), while the over natures (35: $160, 7: $231)
   are correctly large.

**Caveat — the finding mix regressed modestly:** L1 0.039 → 0.067,
driven by an under shortfall (0.125 vs 0.158 real). Small unders are
absorbed by the $23 minimum-benefit floor (and the shelter cap) more often
than small overs hit the max-allotment ceiling — genuine SNAP mechanics,
not a bug — and the in-script recalibration only partly compensates. A
full fix needs re-deriving the effectiveness weights and the 97-resolution
coin under the new mechanism (a `calibrate_injection.py` re-run), not
more in-script scaling.

## Next steps
1. (Recommended) Merge the two verified mechanisms into
   `src/synth/errors.py` (97-conditional small perturbations;
   whole-unit-ineligibility mode) behind a flag, then re-run
   `measure_effectiveness.py` + `calibrate_injection.py` to re-derive
   `eff.json`, `dir_weight`, and the 97 coin under the new attrition
   profile — replacing this experiment's in-script scaling. Re-check the
   finding L1 after the re-derive.
2. Fourth mechanism for the p90 asymmetry: rescale coarse **under**
   magnitudes against the real per-nature medians above (nature 44
   +10–40% → +5–25%; nature 57 −15–40% → −8–25%; audit the shelter
   `_typical_amount` against the nature-52 median of $59).
3. Re-run the exp16 script plus the golden eval after the merge — the
   dollar marginal and the retrieval ranking must move together
   (exp16 next-step 3). Also verify the transfer gate: the small mode
   keeps (element, nature) labels, but the label priors shift.
4. `generate.py` was not touched; the `--no-persistent-buckets` path is
   unaffected (this experiment calls `inject()` with
   `persistent_buckets=True` explicitly).
