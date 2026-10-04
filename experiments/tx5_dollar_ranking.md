# TX5 — Dollar-impact ranking: the THIRD DECISION POINT of the TX POC track

**Date:** 2026-10-03 · **Code:** `experiments/tx5_dollar_ranking.py`

## Hypothesis

TX4 showed P(error) ranking finds more *errors* per review (29% lift) but
skews toward smaller dollars (caught median $21 vs $30). If probability of
error and size of error are nearly orthogonal — as PA5/NY5 found — then a
dollar-aware ranking rule should recover more *dollars* per review hour
than P(error)-alone. Three rules, evaluated at top-10/20/30% review
budgets on the shared TX2 holdout: (a) **P(error)-only** (calibrated GBM);
(b) **two-part:** calibrated P(error) × E[AMTERR|features] (dollar
regressor = GBM regressor on synth *error* cases, log1p(AMTERR) target,
expm1 back-transform, clipped at 0); (c) **direct:** one GBM regressor on
*all* synth cases, log1p(AMTERR) (0 for correct). Plus (b-r)/(c-r)
headroom arms trained on the real-TX train split via 5-fold ensembling
(the transfer ceiling, not a product). Plain-language terms: AMTERR = the
actual dollar size of the error; lift = dollars recovered divided by the
random-order expectation; the 30-min/case review-cost assumption is
documented, not measured (sensitivity at 15/60 min shown — the lift ratio
is invariant to it). **AMTERR is the evaluation target only, never an
input feature.**

## Method

Shared holdout (865 TX cases, 383 errors, $23,168 total error dollars).
Models: TX2's recipe on TX synth (n=20,000, seed 7, clean 8-feature set
per TX7, GBM without class_weight). Metric: actual AMTERR recovered in
top-k vs random-order expectation; dollars-per-hour = recovered / (k ×
hours-per-case). Honesty notes carried from NY5: log-target regressors
underestimate the mean (Jensen, no smearing correction — ranking is
unaffected, but never quote raw expected-dollar outputs as point
forecasts).

## Results

**Winner: (b) two-part** — like PA5, not NY5. (All $/hr at the 30-min
review assumption.)

| Budget | Random | (a) P(err) | (b) two-part | (c) direct | (b-r) headroom | (c-r) headroom |
|---|---|---|---|---|---|---|
| Top-10% $ rec. | $2,303 | $2,249 | **$3,188** | $2,910 | $3,902 | $4,507 |
| Top-10% lift | 1.00x | 0.98x | **1.38x** | 1.26x | 1.69x | 1.96x |
| Top-10% $/hr | $54 | $52 | **$74** | $68 | $91 | $105 |
| Top-20% $ rec. | $4,634 | $4,914 | **$5,798** | $5,580 | $7,470 | $7,150 |
| Top-20% lift | 1.00x | 1.06x | **1.25x** | 1.20x | 1.61x | 1.54x |
| Top-20% $/hr | $54 | $57 | **$67** | $65 | $86 | $83 |
| Top-30% lift | 1.00x | 1.13x | 1.08x | 1.11x | 1.51x | 1.49x |

**The P(error)-alone surprise, confirmed a third time:** (a) is *worse
than random* at top-10% (0.98x, $52/hr vs $54/hr) — probability of error
and size of error are nearly orthogonal in TX's mix, just as in PA
(0.43x) and NY (0.74x). At top-20% (a) manages only 1.06x.

**Why (b) beats (c) in TX (the NY-vs-PA divergence, resolved TX-side):**
NY5's winner was (c) direct because NY's P(error) factor dragged the
product toward high-frequency small-dollar timing errors. TX has the
opposite structure: its P(error) factor is *under*-tilted and its dollar
regressor can reach the income-error tail, so the two-part product works
— like PA5's. TX's (b) vs (c) gap is small (1.25x vs 1.20x at top-20%),
but (b) wins at all three budgets.

**Over/under split at top-20% (winner):** over $3,866 / under $1,932
(67%/33%). Savings-only (over-issuance = program savings): **$44.69/hr vs
$32.38/hr random**. Total $/hr: $67 vs $54.

**Headroom honesty:** synth (b) captures 1.25x vs real-trained (b-r)
1.61x; synth (c) 1.20x vs real-trained (c-r) 1.54x — the generator's
feature→dollar conditional is the binding constraint, same as NY (1.52x
vs 2.72x) and PA (1.58x vs 3.15x). TX's headroom gap is narrower than
NY's/PA's in absolute lift terms.

**Calibration note:** the P(error) calibrator (isotonic, CV Brier 0.19965
vs 0.20362) reaches AUC 0.7025 on the holdout; the real-trained P(error)
headroom hits 0.7885. Expected-dollar outputs overestimate at top-10%
($9,008 expected vs $5,798 recovered for (b)) — the Jensen gap, ranking
unaffected.

## Verdict

**CONDITIONAL PASS — the winner beats random at top-20% with lift 1.25x,
below the ~1.5x bar.** TX5's economics are the weakest of the three state
POCs: (b) two-part recovers $5,798 vs $4,634 random at top-20% ($67/hr vs
$54/hr; savings-only $44.69/hr vs $32.38/hr). The gate's "~1.5x"
is not met — TX's lift (1.25x) trails PA (1.58x) and NY (1.52x). The
conditionality: (1) the lift is real and consistent across budgets
(1.38x/1.25x/1.08x); (2) P(error)-alone's sub-random top-10% confirms the
dollar-aware architecture is *necessary*, not optional; (3) the headroom
(1.61x) shows the economics improve as the generator's dollar conditional
improves — the lever is defined. The whitepaper reports 1.25x honestly
against the 1.5x bar.

## Next steps

- **TX6** tests whether the under-tilt (which the dollar ranking leans on)
  is temporally stable.
- **TX8** quantifies how much of the 1.25x is contamination premium.
- Generator lever for the dollar conditional: TX1's structural residual
  (p90 175 vs 149) is where the missing headroom lives.
