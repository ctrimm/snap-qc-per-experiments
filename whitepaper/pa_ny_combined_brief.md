# SNAP payment-error pilot — two-state evidence (PA + NY)

**Date:** 2026-09-29 · **Source repo:** `ctrimm/snap-qc-per-experiments` (branch `main`)

We've now run the same validation in two states, and the same story holds in both:
the benefit-calculation engine is clean, so the errors live in the human process
layer — and a model trained only on synthetic cases calibrated to that state's
caseload recovers ~1.6x the error dollars of random review at the same review
budget.

## Pennsylvania

- **Data:** 3,268 QC cases, FY2020–24.
- **Engine check:** benefit-calculation engine matches statute 99.7–100% — errors are process-layer.
- **Signature:** shelter errors ~2x national; computation errors 0.1x national.
- **Winner:** two-part ranker (error probability × predicted dollars). At a 20%
  review budget: **$6,074 vs $3,851 random** ($75 vs $47 per review hour),
  capturing **31.5%** of all error dollars. Of that, **$4,239 is over-issuance**
  (direct program savings).

## New York

- **Data:** 3,257 QC cases, FY2020–24.
- **Engine check:** benefit-calculation engine matches statute 94–98% — errors are process-layer.
- **Signature:** timing errors 1.56x national (nearly two-thirds of errors),
  medical errors 1.79x, utility-allowance errors 1.51x.
- **Winner:** direct expected-dollar ranker. At a 20% review budget:
  **$6,958 vs $4,574 random** ($85 vs $56 per review hour), capturing **30.4%**
  of error dollars. Of that, **$4,751 is over-issuance** (direct savings).

## The honest differences

- PA's winner is the two-part ranker; NY's is a direct expected-dollar model —
  because NY's frequent errors are tiny timing errors (median $10–14) while the
  dollars sit in the income-error tail.
- NY conditioning beats national training on finding errors and on dollars, but
  not on fine-grained error-type prediction (NY's signature sits in rare
  medical/utility buckets the generator places poorly).
- The transferable product is **case prioritization, not error labeling**.
- In both states, ranking by error probability alone is **worse than random** at
  the top slice — the ranker must be dollar-aware.

## Pilot shape (same for any state)

Train on the state's own historical QC extracts, validate on a recent holdout,
run in shadow alongside existing review. No production system changes, no new
data collection, no new PII.

## Full whitepapers (same six-section format)

- `whitepaper/pa_pilot_whitepaper.pdf`
- `whitepaper/ny_pilot_whitepaper.pdf`
- Replication runbook for new states: `docs/STATE_POC_RUNBOOK.md`

## Caveat on the economics

The $/hour and captured-dollar figures are measured on QC microdata that is
visible in public files. An independent NY analysis estimates only ~62% of NY's
error cases are visible in public data (our track independently lands at ~67%);
the numbers above are the optimistic read of that reality — a planning read
would apply the visibility discount.
