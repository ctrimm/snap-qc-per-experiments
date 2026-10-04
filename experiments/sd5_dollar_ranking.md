# Experiment SD5: dollar-impact ranking — where errors are rare, P(error) alone wins

**Date:** 2026-10-03 · **Code:** `experiments/sd5_dollar_ranking.py`
(results: `/tmp/sd45out/sd5_results.json`)

## Hypothesis

Tied to the north star (recovery per review hour): PA5's winner was the
two-part P(error)×E[dollars] rule (1.58x at top-20%); NY5's was the direct
expected-dollar rule (1.52x) — and in *both* states P(error)-alone was
*worse than random* at top-10% (PA 0.43x, NY 0.74x): probability of error
and size of error were nearly orthogonal. SD's dollars are tiny (p90 $70)
and rare — does the orthogonality hold where errors are rare, or does the
dollar model become dead weight? Three synth ranking rules ((a)
P(error)-only, (b) two-part, (c) direct) plus two real-trained headroom
arms ((b-r), (c-r)), evaluated on the shared 592-case SD holdout
($6,395 total error dollars).

## Method

Mirror of NY5 with STATE="46", SD7's clean 8-feature set, SD2's no-cw
recipe. (a) calibrated P(error) from the 3-class GBM (isotonic, fit on
the 1,773-row real-SD train split — same calibrator as SD4); (b) P(error)
× E[AMTERR|features] with a `HistGradientBoostingRegressor` on synth
*error* cases (log1p(AMTERR) target, expm1 back-transform, clipped at 0);
(c) one regressor on *all* synth cases (log1p, 0 for correct). Headroom
(b-r)/(c-r): same structures trained on the real-SD train split via
5-fold ensembling. Metric: actual AMTERR recovered in top-k vs random
expectation at top-10/20/30%; dollars-per-hour = recovered / (k ×
hours-per-case), review-cost assumption **30 min/case** (documented
assumption, not measured; sensitivity at 15/60 — the lift ratio is
invariant). AMTERR is the evaluation target only, never a feature.

## Results

Holdout: 592 cases, $6,395 total error dollars. Calibrated P(error) AUC
0.7322 (real-trained 0.7694).

| top-k | random | (a) P(err) | (b) two-part | (c) direct | (b-r) headroom | (c-r) headroom |
|---|---|---|---|---|---|---|
| 10% (n=59) | $637 ($22/hr) | **$1,245, 1.95x, $42/hr** | $881, 1.38x | $924, 1.45x | $1,801, 2.83x | $1,525, 2.39x |
| 20% (n=118) | $1,275 ($22/hr) | $2,644, 2.07x, $45/hr | **$2,660, 2.09x** | $2,564, 2.01x | $3,594, 2.82x | $2,596, 2.04x |
| 30% (n=178) | $1,923 ($22/hr) | **$4,076, 2.12x, $46/hr** | $3,452, 1.79x | $3,972, 2.07x | $4,139, 2.15x | $3,667, 1.91x |

**The winner is (a) P(error)-only** — best synth rule at top-10% and
top-30%, tied at top-20% (2.07x vs 2.09x). This *reverses* the PA/NY
pattern: in both prior states P(error)-alone was worse than random at
top-10% (0.43x/0.74x); in SD it is the best rule (1.95x).

**Why the reversal?** In PA/NY, error dollars lived in a big-dollar
income tail that P(error) couldn't see — probability and size were
orthogonal, and the dollar regressors could reach the tail. SD has no
big-dollar tail (p90 $70; 88.6% of errors ≤$56): the dollars that exist
are found by finding errors *at all*, and the oracle shows they are
hyper-concentrated (top-10% by actual AMTERR holds 83.3% of all error
dollars; top-20% holds 98.2%). Meanwhile SD's synth dollar regressors
are miscalibrated — (b) expected $1,118 but recovered $881 at top-10%,
(c) expected $1,129 vs $924 — the generator's dollar level undershoots
real (SD1: synth p50 $10 vs real $17; Jensen on the log target with no
smearing correction). Multiplying a good P(error) ranker (AUC 0.73) by a
bad E[dollar] estimate *hurts*. Where errors are rare and small, the
dollar model is dead weight: rank by P(error) and take what comes.

Over/under split at top-20% (winner (a)): **$1,884 over / $760 under
(71/29)** — over-issuance dollars are program savings: **$31.93/hr
savings-only** vs random's $13.48/hr (random over-share 0.624 × $22/hr).
Under-issuance dollars found ($760) mean households were underpaid —
outreach value, not recovery. Sensitivity: at 15 min/case the winner runs
$84–$92/hr; at 60 min, $21–$23/hr; lifts unchanged.

Headroom honesty: the real-trained (b-r) reaches 2.82x at top-20% vs the
synth winner's 2.07x — synth captures ~3/4 of the achievable lift. The
generator's feature→dollar conditional is the binding constraint (same
as PA 1.58x vs 3.15x, NY 1.52x vs 2.72x). The real-trained (c-r) direct
arm (2.04x) does *not* beat real two-part here — unlike NY, where direct
won — because SD's P(error) factor is informative rather than a drag.

Oracle anatomy: the dollars live in earned (29 of the top-10% oracle
cases), unearned (15), shelter (7) — over cases (32 of 59). The winner
(a) catches 21/59 error cases at top-10% vs oracle's 59 — the P(error)
ranker finds errors, not dollars, and in SD that is enough.

## Verdict

**CONDITIONAL PASS** — the winner (a) P(error)-only beats random at
top-20% with lift 2.07x ≥ 1.5x, and at all three budgets (1.95x/2.07x/
2.12x). The headline for the whitepaper: **$45/hr vs $22/hr random at
the top-20% review budget (2.07x lift), $31.90/hr in program savings
alone** — achieved by the *simplest* rule, calibrated P(error), with no
dollar model at all.

Honesty notes: (a) log-target regressors underestimate the mean (Jensen,
no smearing correction — ranking unaffected, never quote raw
expected-dollar outputs as point forecasts); (b) synth captures ~3/4 of
real-trained headroom (2.07x vs 2.82x); (c) n=592 holdout, top-10% is 59
cases — the 1.95x has wide CIs; (d) the (a)-vs-(b) gap at top-20% is a
tie (2.07x vs 2.09x) — the "P(error)-alone wins" claim rests on top-10%
and top-30% plus simplicity, not a clean sweep.

## Next steps

- The whitepaper's economics table uses (a) at top-20%: $2,644 vs $1,275
  random, $45/hr vs $22/hr, 41.3% of all error dollars captured
  ($2,644/$6,395), over/under $1,884/$760.
- SD6/SD8 proceed unchanged; SD8's pristine rerun should confirm the
  (a)-rule economics (P(error) AUC is the load-bearing metric).
