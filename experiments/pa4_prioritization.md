# PA4 — Prioritization simulation: second decision point of the PA POC track

**Date:** 2026-09-29
**Status:** Complete — decision: **CONDITIONAL PASS**, see Verdict.
**Code:** `experiments/pa4_prioritization.py`
**Deliverables (new files only; no existing file modified):**
- `experiments/pa4_prioritization.py` — retrain + calibrate + rank + report
- `experiments/pa4_prioritization.md` — this chronicle

## Hypothesis

PA2's finding model (PA-conditioned synthetic + GBM, no class_weight) cannot
classify — hard-prediction accuracy 0.388 loses to the 0.573 majority
baseline — but it *ranks* (binary AUC 0.645). A reviewer's workflow doesn't
need classification; it needs a ranked queue. If calibrated P(error) from
that model ranks real PA cases better than random review order, the POC has
a CIO-facing metric: errors found per reviewer-hour.

## Method

**Retrain (exact reproduction recipe, from repo root):**
```bash
cd src && python3 -m synth.pa_state --n 20000 --seed 7 \
    --dist ../experiments/dist.json --out /tmp/pa4out/pa_synth.jsonl
python3 experiments/pa4_prioritization.py \
    --pa-synth /tmp/pa4out/pa_synth.jsonl \
    --qc-dir ../snap-qc-data/raw \
    --holdout-json experiments/pa2_holdout_idx.json
```
The regeneration was verified byte-identical (md5 `64fd2f0bfb11d0fcff6d239f98bf02b2`)
to the seed-7 file PA2 trained on, so the model is PA2's arm b exactly:
`HistGradientBoostingClassifier(random_state=0)`, no class_weight, 3-class
(correct/over/under), v1 features.

**P(error), not hard labels.** Raw score = 1 - P(correct) = P(over) + P(under)
from the frozen synth-trained GBM. The raw scores reproduce PA2's ranking
signal exactly: AUC 0.645 on the real-PA train split (PA2 reported 0.645).

**Calibration (documented choice).** The synth-trained scores are error-eager
on real PA (PA2's confusion finding), so they are recalibrated on the
real-PA **train split** (2,451 rows — the complement of the shared holdout,
disjoint from everything reported; this is PA2's recommended "validation
slice" step). Isotonic vs Platt (logistic) was chosen by 5-fold stratified
CV Brier score on that slice: isotonic 0.22247 vs Platt 0.22477 — **isotonic
won**, refit on the full 2,451-row slice. The holdout (817 rows, 349 errors,
base rate 42.7%) is scored once, ranked by calibrated P(error), never
touched during training or calibration.

**Fairness caveat (inherited from PA2, still applies):** PA1's generator
offsets were fit on pooled FY2020–2024 PA microdata *including the holdout
rows*. The offset fit sees only pooled marginals, not test labels, so the
optimism is small — but the ranking numbers below are very slightly
flattered, not pristine.

## Results

Calibrated AUC on the holdout: **0.68** (raw scores on the same holdout:
0.67 — calibration is monotone, so the ranking is the model's, not the
calibrator's; the 0.645→0.67 gap vs PA2 is split-sample noise, same model).

### Precision@k, lift, and reviewer yield on the shared holdout

Base error rate (random review order): **42.7%** — 42.7 errors per 100 reviews.

| Review budget | n reviewed | precision@k | lift vs random | errors caught | share of all 349 errors | errors per 100 reviews |
|---|---|---|---|---|---|---|
| Top 10% | 82 | 0.50 | 1.17x | 41 | 11.8% | 50.0 (vs 42.7) |
| Top 20% | 163 | 0.49 | 1.14x | 79 | 22.6% | 48.5 (vs 42.7) |
| Top 30% | 245 | 0.53 | 1.24x | 130 | 37.2% | 53.1 (vs 42.7) |
| Top 40% | 327 | 0.56 | 1.31x | 183 | 52.4% | 56.0 (vs 42.7) |
| Top 50% | 408 | 0.57 | 1.34x | 234 | 67.0% | 57.4 (vs 42.7) |

### Cumulative-gains shape, in words

The gains curve is **flat-topped, not steep**. The top decile is only weakly
enriched (50% errors vs 43% baseline) — there is no sharply risky elite for
the model to pinpoint. Per-decile error rates: 50%, 47%, 62%, 65%, 63% across
the top five deciles, then a cliff: the **bottom half of the ranking is 28%
errors**. In plain terms: reviewing the riskiest 20% catches 23% of all
errors — barely better than random — but reviewing the riskiest *half*
catches **67% of all errors (234 of 349)** while doing half the reviews. The
model's value is in **deprioritizing the safe half**, not in targeting the
riskiest few.

### What would the reviewer be finding? (top-20% cut, 79 caught errors)

- Direction: **62% over-issuance / 38% under** — mirrors the holdout-wide
  error mix (60.5% / 39.5%). No direction bias in what the ranker catches.
- Dollars (AMTERR): **median $12**, mean $26, p10 $1, p90 $61 — vs $25 median
  holdout-wide. **The ranker skews toward smaller-dollar errors.** A reviewer
  optimizing dollars recovered, not error count, would want a
  dollar-weighted ranking; this one is error-count-weighted.

## Verdict

**CONDITIONAL PASS — the ranking beats random review, but the margin only
matters for one of the two operational use cases.**

In numbers a non-technical executive can understand: Pennsylvania reviewers
today find errors in about **43 of every 100** cases they review. Reviewing
cases in the model's ranked order, the first 100 reviews turn up about
**49 errors instead of 43 — six more errors per hundred** (14% lift), and the
"top 10% riskiest" list is right only half the time. That is not a precision
targeting tool: you cannot hand a supervisor a short list of "these cases are
bad" and have it be right often enough to matter.

What *does* clear an operational bar is triage: **review the riskiest half of
the caseload and skip the safest half, and you catch two-thirds of all errors
(234 of 349) with half the reviews** — 57 errors per 100 reviews vs 43 by
random order. If the scarce resource is reviewer hours, the model earns its
keep as a queue-ordering aid. If the goal is a short, high-confidence hit
list, it does not — not at AUC 0.68.

Two honest caveats for the CIO: (1) this is **retrospective ranking on
QC-labeled cases**, not a live deployment — see open questions below; (2) the
caught errors skew small-dollar (median $12 vs $25 overall), so
error-count gains overstate dollars-recovered gains.

## Next steps

- **PA5/POC packaging:** frame the deliverable as *triage* (halve the queue,
  keep two-thirds of errors), never as a risk score for individual-case
  action. The 50%-precision top-decile number is the guardrail against
  over-claiming.
- **Open question — feature timing (not solved):** the v1 features
  (household size, earnings, shelter costs, SUA, medical, depcare,
  senior/disabled flag, issued benefit) are all known at certification time,
  which is favorable — but this simulation scored cases *after* QC review.
  Whether the feature→error mapping behaves the same when scores are computed
  prospectively at certification, before any review activity, is untested.
- **Open question — calibration maintenance:** the calibration step consumed
  2,451 labeled real-PA cases. In production that labeled slice is the QC
  sample itself, so it exists — but the pipeline must re-calibrate as the mix
  drifts (PA3 showed the earned/unearned mix shifting in 2023–2024; exp34 owns
  temporal drift). A stale calibrator silently degrades the queue.
- **Open question — prospective validation:** per the PA2 fairness caveat,
  the generator saw holdout rows' marginals. Before any operational claim,
  validate the ranking on a *future* QC pull the generator never saw.
- **Optional (if dollars matter):** re-rank by expected dollar error
  (P(error) × predicted |AMTERR|) — exp16/exp18 own the dollar machinery —
  and re-run this simulation against a dollars-recovered metric.
