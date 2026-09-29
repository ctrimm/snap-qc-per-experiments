# NY4 — Prioritization simulation: second decision point of the NY POC track

**Date:** 2026-09-29
**Status:** Complete — decision: **CONDITIONAL PASS**, see Verdict.
**Code:** `experiments/ny4_prioritization.py`
**Deliverables (new files only; no existing file modified):**
- `experiments/ny4_prioritization.py` — retrain + calibrate + rank + report
- `experiments/ny4_prioritization.md` — this chronicle

## Hypothesis

NY2's finding model (NY-conditioned synthetic + GBM, no class_weight) cannot
classify — hard-prediction accuracy 0.393 loses to the 0.633 majority
baseline — but it *ranks* (binary AUC 0.648; NY8's pristine refit 0.626). A
reviewer's workflow doesn't need classification; it needs a ranked queue. If
calibrated P(error) from that model ranks real NY cases better than random
review order, the POC has a CIO-facing metric: errors found per reviewer-hour.

## Method

**Retrain (exact reproduction recipe, from repo root):**
```bash
python3 -m src.synth.ny_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out /tmp/ny45out/ny_synth.jsonl
python3 experiments/ny4_prioritization.py \
    --ny-synth /tmp/ny45out/ny_synth.jsonl \
    --qc-dir ~/workspace/snap-qc-data/raw \
    --holdout-json experiments/ny2_holdout_idx.json
```
The regenerated synth (md5 `9cef4af3bd18f0436741aa1d329514c0`, finding
error rate 0.3651) is the same NY1 recipe NY2 trained on, so the model is
NY2's arm b exactly: `HistGradientBoostingClassifier(random_state=0)`, no
class_weight, 3-class (correct/over/under), P(error) = 1 - P(correct).

**Feature deviation from PA4 (documented, per NY7):** NY7's leakage audit
found `issued_benefit` (RAWBEN — the benefit actually issued) is a
post-decision leakage feature. NY4 trains on NY7's **clean 8-feature set**
from the start — `hh_size, earned, unearned, shelter, sua, medical_exp,
depcare, senior_disabled` — dropping `issued_benefit`. PA4's 9-feature recipe
is deliberately not used. On this holdout the clean-8 set ranks slightly
better than NY2's 9-feature arm (raw AUC 0.663 vs 0.648).

**P(error), not hard labels.** Raw score = 1 - P(correct) = P(over) + P(under)
from the frozen synth-trained GBM.

**Calibration (documented choice).** The synth-trained scores are error-eager
on real NY (NY2's confusion finding), so they are recalibrated on the
real-NY **train split** (2,442 rows — the complement of the shared holdout,
disjoint from everything reported). Isotonic vs Platt (logistic) was chosen
by 5-fold stratified CV Brier score on that slice: isotonic 0.21732 vs Platt
0.22137 — **isotonic won**, refit on the full 2,442-row slice. The holdout
(815 rows, 299 errors, base rate 36.7%) is scored once, ranked by calibrated
P(error), never touched during training or calibration.

**Fairness caveat (inherited from NY2, now quantified by NY8):** NY1's
generator offsets were fit on pooled FY2020–2024 NY microdata *including the
holdout rows*. NY8's pristine refit measured the contamination premium at
~+0.02 on finding AUC and ~0 on element. The ranking numbers below are very
slightly flattered, not pristine.

## Results

Calibrated AUC on the holdout: **0.669** (raw scores on the same holdout:
0.663 — calibration is monotone, so the ranking is the model's, not the
calibrator's). Reference: NY8's pristine finding AUC was **0.626** (9-feature,
no-cw). The +0.04 gap mixes two effects — the clean-8 feature change
(~+0.015 vs NY2's 0.648 on the same contaminated synth) and the ~+0.02
contamination premium NY8 measured. Either way, the ranking clears the NY8
reference.

### Precision@k, lift, and reviewer yield on the shared holdout

Base error rate (random review order): **36.7%** — 36.7 errors per 100 reviews.

| Review budget | n reviewed | precision@k | lift vs random | errors caught | share of all 299 errors | errors per 100 reviews |
|---|---|---|---|---|---|---|
| Top 10% | 82 | 0.51 | 1.40x | 42 | 14.1% | 51.2 (vs 36.7) |
| Top 20% | 163 | 0.49 | 1.34x | 80 | 26.8% | 49.1 (vs 36.7) |
| Top 30% | 244 | 0.50 | 1.35x | 121 | 40.5% | 49.6 (vs 36.7) |
| Top 40% | 326 | 0.47 | 1.29x | 154 | 51.5% | 47.2 (vs 36.7) |
| Top 50% | 408 | 0.49 | 1.32x | 198 | 66.2% | 48.5 (vs 36.7) |

Comparison with PA4 (precision@10% 0.50, lift 1.17x, top half catches 67.0%):
NY's precision@10% is essentially identical (**0.51 vs 0.50**) and its lift
is stronger (**1.40x vs 1.17x** — NY's lower base rate makes the same
absolute enrichment a larger ratio), while the top-half catch is nearly
identical (**66.2% vs 67.0%**).

### Cumulative-gains shape, in words

The gains curve is **flat-topped, not steep** — the same shape PA4 found.
Marginal per-decile error rates: 51%, 47%, 51%, 40%, 54% across the top five
deciles, then a cliff: the **bottom half of the ranking is 25% errors**. In
plain terms: reviewing the riskiest 20% catches 27% of all errors — barely
better than random — but reviewing the riskiest *half* catches **two-thirds
of all errors (198 of 299)** while doing half the reviews. The model's value
is in **deprioritizing the safe half**, not in targeting the riskiest few.

### What would the reviewer be finding? (top-20% cut, 80 caught errors)

- Direction: **57.5% over-issuance / 42.5% under** — mirrors the holdout-wide
  error mix (58.5% / 41.5%). No direction bias in what the ranker catches.
- Dollars (AMTERR): **median $26**, mean $63, p10 $2, p90 $235 — vs $30 median
  holdout-wide. Unlike PA4 (median $12 vs $25 — a sharp small-dollar skew),
  **NY's ranker catches roughly representative dollars**; the p90 of $235
  shows it also reaches into NY's fatter dollar tail. A reviewer optimizing
  error count is not being steered far from the dollar-weighted optimum
  here — but see NY5 for the explicit dollar ranking.

## Verdict

**CONDITIONAL PASS — the ranking beats random review, and NY's numbers are
as good as or better than PA4's on every headline metric.**

In numbers a non-technical executive can understand: New York reviewers
today find errors in about **37 of every 100** cases they review. Reviewing
cases in the model's ranked order, the first 100 reviews turn up about
**49 errors instead of 37 — twelve more errors per hundred** (34% lift), and
the "top 10% riskiest" list is right about half the time. That is not a
precision targeting tool: you cannot hand a supervisor a short list of
"these cases are bad" and have it be right often enough to matter.

What *does* clear an operational bar is triage: **review the riskiest half
of the caseload and skip the safest half, and you catch two-thirds of all
errors (198 of 299) with half the reviews** — 49 errors per 100 reviews vs
37 by random order. If the scarce resource is reviewer hours, the model
earns its keep as a queue-ordering aid. If the goal is a short,
high-confidence hit list, it does not — not at AUC 0.67.

Two honest caveats for the CIO: (1) this is **retrospective ranking on
QC-labeled cases**, not a live deployment — see open questions below; (2)
the numbers carry NY2's holdout-contamination caveat, quantified small by
NY8 (~+0.02 on the finding AUC). Unlike PA4, the caught errors do **not**
skew small-dollar (median $26 vs $30 overall), so error-count gains do not
overstate dollars-recovered gains the way they did in PA.

## Next steps

- **NY5/POC packaging:** frame the deliverable as *triage* (halve the queue,
  keep two-thirds of errors), never as a risk score for individual-case
  action. The 51%-precision top-decile number is the guardrail against
  over-claiming.
- **Open question — feature timing (not solved):** the clean-8 features
  (household size, earnings, shelter costs, SUA, medical, depcare,
  senior/disabled flag) are all known at certification time, which is
  favorable — but this simulation scored cases *after* QC review. Whether
  the feature→error mapping behaves the same when scores are computed
  prospectively at certification, before any review activity, is untested.
- **Open question — calibration maintenance:** the calibration step consumed
  2,442 labeled real-NY cases. In production that labeled slice is the QC
  sample itself, so it exists — but the pipeline must re-calibrate as the
  mix drifts. A stale calibrator silently degrades the queue.
- **Open question — prospective validation:** validate the ranking on a
  *future* QC pull the generator never saw, eliminating the contamination
  caveat entirely.
- **Optional (if dollars matter):** re-rank by expected dollar error —
  NY5 does this against a dollars-recovered metric.
