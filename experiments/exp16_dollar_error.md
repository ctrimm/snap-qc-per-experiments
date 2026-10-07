# Experiment 16 — Dollar-error distribution re-check
**Date:** 2026-09-29 · **Code:** `experiments/exp16_dollar_error.py`

## Hypothesis
North-star gate: **calibration**. exp1 measured the dollar-error marginal early
(p90 77 synth vs 78 real) and declared it close enough. The generator has since
changed substantially — direction fixes (exp3), omission coherence (exp5),
eligibility-screen injection (exp6), per-bucket persistence (exp7) — and each
change reweights which corruptions survive into realized cases. Hypothesis: the
dollar-error marginal still tracks the real FY2024 QC distribution. If it has
drifted, the finding mix may look right while the dollar priors fed to a
downstream model are wrong.

A note on terms: a *percentile* pK is the value below which K% of cases fall.
p50 is the median — half the errors are smaller, half larger. p90 is the value
that only the largest 10% of errors exceed. The *mean* is the plain average.

## Method
- **Real side** (held-out validation only; microdata never committed):
  44,891 FY2024 QC rows, 17,836 with STATUS 2 (overissuance) or 3
  (underissuance). Signed dollar error = AMTERR with sign from STATUS
  (positive for over, negative for under). AMTERR is the tech doc's
  authoritative "amount of benefit in error" (non-negative, range 1–2377).
  RAWBEN−FSBEN was considered but rejected: it disagrees with AMTERR on 21.9%
  of error cases (p90 discrepancy $145), while the tech doc's own consistency
  checks use AMTERR directly. Sub-$56 errors stay in: per the tech doc, "error
  amounts of $56 or less were not included in the calculation of State error
  rates" — the official rate excludes them, but the QC file still records
  them with over/under findings.
- **Synth side**: 20,000 fresh cases from the persistent generator
  (`python -m synth.generate --n 20000 --seed 7 --dist ../experiments/dist.json`,
  exp7 per-bucket persistence on by default). Signed dollar error =
  issued_benefit − correct_benefit (= ±dollar_error keyed by finding;
  consistency asserted per case). 7,853 error cases realized (25.6% over /
  13.6% under of all cases — the exp1 finding-mix gap is closed; real is
  23.9% / 15.8%).
- Compared p10/p25/p50/p75/p90/p99 and mean of the absolute error among error
  cases, plus the over-vs-under dollar asymmetry (median/mean/p90/p99 within
  each finding). Also recomputed exp1's all-rows comparison (including the 60%
  of correct cases with $0 error) for continuity.

## Results

Absolute dollar error, error cases only:

| stat | real | synth | ratio (synth/real) |
|------|-----:|------:|-------------------:|
| p10  |    4 |    22 | 5.50 |
| p25  |   11 |    41 | 3.73 |
| p50  |   31 |    74 | 2.39 |
| p75  |   79 |   128 | 1.62 |
| p90  |  201 |   202 | 1.00 |
| p99  |  528 |   304 | 0.58 |
| mean | 71.5 |  93.6 | 1.31 |

The p90 match is a coincidence that masks two opposite problems: the synth
distribution is starved at the bottom (every percentile below p75 inflated
1.6–5.5x) and thinned at the very top (p99 0.58x).

Over-vs-under dollar asymmetry (absolute $ within each finding):

| stat      | real | synth |
|-----------|-----:|------:|
| median over  |   38 |   70 |
| median under |   23 |   82 |
| mean over    | 86.4 | 90.0 |
| mean under   | 48.9 | 100.5 |
| p90 over     |  244 |  190 |
| p90 under    |  128 |  210 |
| p99 over     |  603 |  319 |
| p99 under    |  361 |  262 |

In real QC, over-errors run substantially larger than under-errors (median
38 vs 23; p99 603 vs 361). The generator inverts this: under-errors are
slightly larger than overs at every level.

Continuity with exp1 (all 44,891 rows / 20,000 cases, zeros included): real
p90 78 vs synth p90 126 (exp1: 77 vs 78 — the marginal has genuinely moved),
mean 28.4 vs 36.8.

Supporting facts:
- 69.0% of real error cases have AMTERR ≤ $56 (the FY2024 tolerance cutoff);
  only 37.3% of synth error cases do. Real QC carries enormous mass of tiny
  variances; the generator's corruption mechanics (income perturbations at
  15–50%, hhcomp moving ~$231 median, ±$10–60 arithmetic noise on only ~3%
  of errors) produce coarse moves.
- The generator produced zero whole-unit ineligibility cases (correct_benefit
  == 0) in 20k draws; its "ineligible person included" mode only adds a
  household member (median over $231). The real over-tail's extreme end
  (p99 $603, max $1563) is not reachable by this mechanism.

## Verdict
Hypothesis **fails**. The dollar marginal has drifted since exp1 despite the
finding mix now calibrating well. Three distinct, fixable problems:

1. **Starved low tail.** Real QC is dominated by small variances (p10 $4,
   p25 $11, 69% under the $56 tolerance). The generator makes errors that are
   too coarse — synth p10 is 5.5x real.
2. **Inverted asymmetry.** Real over-errors > under-errors at median, mean,
   p90, and p99. Synth flips the sign of the gap at every level.
3. **Thin extreme over-tail.** Synth over p99 $319 vs real $603; no modeled
   whole-unit ineligibility (error = full issued benefit).

For a QC copilot prior this matters: a model trained on these priors would
over-expect mid-size errors, under-expect both the tiny-variance mass and the
large over-issuances, and learn the wrong directional dollar asymmetry.

## Next steps
1. (Recommended) Add a small-error mechanism: expand the arithmetic/rounding
   bucket's share of realized errors, or add sub-$56 perturbation modes
   (small income rounding, minor deduction mis-keying), targeting ~69% of
   error cases ≤ $56.
   - **Done →** [exp18](exp18_dollar_mechanisms.md): Small-error mode (nature-97 conditioning) verified.
2. Model whole-unit ineligibility (correct benefit $0, error = issued
   benefit) as a distinct over-error mode; this should restore both the
   over-tail and the over>under asymmetry.
   - **Done →** [exp18](exp18_dollar_mechanisms.md): Whole-unit ineligibility mode verified (p = 0.0125).
3. Re-run this script plus the golden eval after the fix — the dollar
   marginal and the retrieval ranking must move together.
   - **Done →** [exp23](exp23_merge_recalibrate.md), [exp26](exp26_combine_dollar.md): Dollar marginal re-checked after merging: share ≤ $56 0.69 vs 0.70 real, p90 inversion fixed.
