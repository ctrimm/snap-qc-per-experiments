# Experiment ID5: dollar-impact ranking — SD's P-alone reversal REPLICATES in Idaho

**Date:** 2026-10-04 · **Code:** `experiments/id5_id_dollar_ranking.py`
(results: `/tmp/id45out/id5_results.json`, scratch; run log:
`/tmp/id8cout/id5_run.txt`)

## Hypothesis

Tied to the north star (recovery per review hour) and the track's key
scientific question: SD5 found a reversal — in South Dakota (lowest PER,
p90 $70, no big-dollar tail), P(error)-alone beat both dollar rankers
because the synth dollar regressors were miscalibrated dead weight. Idaho
is the 2nd-lowest PER state (3.85% FY2025) with the same small-dollar
profile (ID p90 $87; 86.9% of errors ≤$56). Does the reversal replicate,
or is SD a one-off? Three synth ranking rules ((a) P(error)-only, (b)
two-part, (c) direct) plus two real-trained headroom arms ((b-r), (c-r)),
evaluated on the shared 960-case ID holdout ($10,713 total error dollars).

## Method

Port of `experiments/sd5_dollar_ranking.py` with STATE="16", ID7's clean
8-feature set, and ID2's **balanced** recipe (documented departure: ID2's
finding-task winner is the balanced arm, not no-cw). (a) calibrated
P(error) from the 3-class GBM (isotonic, fit on the 2,879-row real-ID
train split — same calibrator as ID4; holdout AUC 0.6755; real-trained
0.7206); (b) P(error) × E[AMTERR|features] with a
`HistGradientBoostingRegressor` on synth *error* cases (log1p(AMTERR)
target, expm1 back-transform, clipped at 0); (c) one regressor on *all*
synth cases (log1p, 0 for correct). Headroom (b-r)/(c-r): same structures
trained on the real-ID train split via 5-fold ensembling. Metric: actual
AMTERR recovered in top-k vs random expectation at top-10/20/30%;
dollars-per-hour = recovered / (k × hours-per-case), review-cost
assumption **30 min/case** (documented assumption, not measured;
sensitivity at 15/60 — the lift ratio is invariant). AMTERR is the
evaluation target only, never a feature.

## Results

| top-k | random | (a) P(err) | (b) two-part | (c) direct | (b-r) headroom | (c-r) headroom |
|---|---|---|---|---|---|---|
| 10% (n=96) | $1,071 ($22/hr) | **$1,894, 1.77x, $39/hr** | $656, 0.61x, $14/hr | $1,799, 1.68x, $37/hr | $2,120, 1.98x | $2,472, 2.31x |
| 20% (n=192) | $2,143 ($22/hr) | $3,000, 1.40x, $31/hr | $1,941, 0.91x, $20/hr | $3,037, 1.42x, $32/hr | $4,464, 2.08x | $4,127, 1.93x |
| 30% (n=288) | $3,214 ($22/hr) | **$4,057, 1.26x, $28/hr** | $3,686, 1.15x, $26/hr | $3,914, 1.22x, $27/hr | $5,918, 1.84x | $5,701, 1.77x |

**The winner is (a) P(error)-only** — best synth rule at top-10% (1.77x)
and top-30% (1.26x), tied at top-20% (1.40x vs 1.42x for direct). **SD's
reversal replicates.** In PA/NY, P(error)-alone was worse than random at
top-10% (0.43x/0.74x); in ID, as in SD, it is the best rule (1.77x).

**Why the reversal replicates:** Idaho has no big-dollar tail (p90 $87;
86.9% of errors ≤$56): the dollars that exist are found by finding errors
*at all*, and the oracle shows they are hyper-concentrated (top-10% by
actual AMTERR holds 74.3% of all error dollars; top-20% holds 93.5%;
top-30% holds 99.5%). Meanwhile ID's synth dollar regressors are
miscalibrated — (b) expected $1,653 but recovered $656 at top-10%, (c)
expected $1,236 vs $1,799 — the generator's dollar level undershoots real
(ID1: synth p50 $7 vs real $19; Jensen on the log target with no smearing
correction). Multiplying a good P(error) ranker (AUC 0.676) by a bad
E[dollar] estimate *hurts*: the two-part rule is **worse than random** at
top-10% (0.61x, $14/hr vs $22/hr random) and below random at top-20%
(0.91x). Where errors are rare and small, the dollar model is dead weight:
rank by P(error) and take what comes.

**Over/under split at top-20% (winner (a)):** **$2,397 over / $603 under
(80/20)** — over-issuance dollars are program savings: **$24.97/hr
savings-only** vs random's ~$13.4/hr (random over-share ≈ 61% × $22/hr).
Under-issuance dollars found ($603) mean households were underpaid —
outreach value, not recovery. Sensitivity: at 15 min/case the winner runs
$62–$79/hr; at 60 min, $16–$20/hr; lifts unchanged.

**Headroom honesty:** the real-trained (b-r) reaches 2.08x at top-20% vs
the synth winner's 1.40x — synth captures ~2/3 of the achievable lift.
The generator's feature→dollar conditional is the binding constraint
(same as PA 1.58x vs 3.15x, NY 1.52x vs 2.72x, SD 2.07x vs 2.82x). The
real-trained (c-r) direct arm (1.93x) does *not* beat real two-part here
— unlike NY, where direct won — because ID's P(error) factor is
informative rather than a drag (same as SD).

**Oracle anatomy:** the dollars live in shelter (64 of the top-20%
oracle cases), earned (61), unearned (35) — over cases (130 of 192). The
winner (a) catches 92/192 error cases at top-20% vs oracle's 192 — the
P(error) ranker finds errors, not dollars, and in ID that is enough.

## Verdict

**CONDITIONAL PASS** — the winner (a) P(error)-only beats random at all
three budgets (1.77x/1.40x/1.26x). The headline for the whitepaper:
**$31/hr vs $22/hr random at the top-20% review budget (1.40x lift),
$24.97/hr in program savings alone** — achieved by the *simplest* rule,
calibrated P(error), with no dollar model at all.

Honesty notes: (a) the top-20% lift (1.40x) is modest — below the ~1.5x
bar, and the (a)-vs-(c) gap there is a tie (1.40x vs 1.42x); the
"P(error)-alone wins" claim rests on top-10% and top-30% plus simplicity,
not a clean sweep; (b) log-target regressors underestimate the mean
(Jensen, no smearing correction — ranking unaffected, never quote raw
expected-dollar outputs as point forecasts); (c) synth captures ~2/3 of
real-trained headroom (1.40x vs 2.08x); (d) n=960 holdout, top-10% is 96
cases — the 1.77x has wide CIs; (e) the two-part rule's 0.61x at top-10%
is the strongest "dollar model hurts" signal in any state so far.

**The scientific answer: SD's low-PER reversal is not a one-off.** Two
low-PER, small-dollar states (SD p90 $70, ID p90 $87) now show
P(error)-alone as the winning synth rule, while the two higher-PER,
big-dollar-tail states (PA, NY) show P-alone worse than random at
top-10%. The emerging rule: *where errors are rare and small, rank by
P(error); where a big-dollar tail exists, model the dollars.*

## Next steps

- The whitepaper's economics table uses (a) at top-20%: $3,000 vs $2,143
  random, $31/hr vs $22/hr, 28.0% of all error dollars captured
  ($3,000/$10,713), over/under $2,397/$603.
- ID6/ID8 proceed unchanged; ID8's pristine rerun should confirm the
  (a)-rule economics (P(error) AUC is the load-bearing metric).
  - **Done →** [ID6](id6_id_temporal.md), [ID8](id8_id_pristine_rerun.md): ID6: PASS — no annual refit: pooled fit beats single-year refit on the clean temporal test; finding signal flat across the FY2022→FY23-24 boundary; coin-cal stable (1.20=1.20)… ID8: MIXED stands with qualification — pristine element accuracy edge persists (+0.054 over national) but macroF1 ties (−0.002); finding AUC margin unchanged (+0.017). Contami…
- The fairness check (exp47 pattern) runs on the (a) winner — and the
  risk-regressivity caveat, currently scoped to dollar-maximizing rankers,
  needs re-examination for a P(error)-only winner.
