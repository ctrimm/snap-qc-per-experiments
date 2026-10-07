# Experiment 33 — state-level heterogeneity

**Date:** 2026-09-29 · **Code:** `experiments/exp33_state_heterogeneity.py`

## Hypothesis

A meaningful share of payment-error-rate variance is state-level, and the
national synthetic generator — which has no state input at all — cannot
reproduce it. If the state-level signal is large and stable, the generator
needs a state dimension. This moves the **calibration gate**: synthetic
marginals must match real QC not only nationally but across states.

## Method

Real side: FY2020–FY2024 QC public-use microdata (held-out validation; never
committed). For each state (53 codes: 50 states + DC + territories), computed
two payment error rates from raw microdata, weighted by FYWGT:

- **dollar-weighted rate** = sum(FYWGT × AMTERR) / sum(FYWGT × FSBEN), the
  FNS-style payment error rate (share of dollars paid in error);
- **case-weighted rate** = weighted share of sampled cases with STATUS 2/3
  (over/underpayment).

Spread measured by **coefficient of variation** (CV = standard deviation
divided by the mean — the relative width of the distribution, unit-free), both
plain and caseload-weighted. Year-to-year stability via Pearson (linear
agreement of the rates) and Spearman (agreement of the state *rankings*).

Cross-check: FNS-published official state payment error rates (FRAC
compilation of FNS releases, fetched 2026-09-29; note FNS never published
FY2020/FY2021) ranked against the microdata-implied rankings.

Synth side: 20,000 cases from `python3 -m src.synth.generate --n 20000
--seed 7 --dist experiments/dist.json --out /tmp/exp33_synth.jsonl`
(persistent buckets on, defaults). Confirmed the case schema has no state
field, then measured the per-state **L1-style gap** (mean absolute deviation,
caseload-weighted) between each real state rate and the single synthetic
national rate.

Reproducibility: `git rev-parse HEAD` = `f515930843d66d784ee1b95288e600de22353bfa`;
`git status --short` at run time showed uncommitted edits in another
researcher's work — `M src/synth/dollar_mech.py`, `M src/synth/errors.py`,
`M src/synth/household.py` (src/ treated as read-only, not touched).

## Results

### Real QC: state error rates vary enormously and the pattern is persistent

Pooled FY2020–2024, dollar-weighted (FNS-style) rate by state:

| Lowest states | Rate | Highest states | Rate |
|---|---|---|---|
| South Dakota | 2.39% | California | 9.72% |
| Idaho | 3.45% | Connecticut | 9.75% |
| Wyoming | 4.08% | Maryland | 10.00% |
| Utah | 4.15% | Maine | 10.28% |
| Hawaii | 4.53% | Illinois | 10.80% |
| Arkansas | 4.60% | Michigan | 11.89% |
| New Jersey | 4.79% | Rhode Island | 12.52% |
| Alaska | 4.91% | Oregon | 12.83% |
| Kentucky | 4.94% | Georgia | 13.31% |
| Nebraska | 5.14% | District of Columbia | 17.64% |

Dispersion and stability:

| Metric | Dollar-weighted rate | Case-weighted rate |
|---|---|---|
| Min / max | 2.39% / 17.64% (7.4x) | 24.75% / 50.82% (2.1x) |
| CV (unweighted) | 0.346 | 0.137 |
| CV (caseload-weighted) | 0.335 | — |
| FY2023 vs FY2024 Spearman | 0.825 | — |
| FY2020 vs FY2024 Spearman | 0.590 | — |
| FY2023 vs FY2024 Pearson | 0.836 | — |

National trend for context: dollar-weighted national rate rose from 8.12%
(FY2020) to 9.17% (FY2024); case-weighted from 35.49% to 40.99%. (FY2021
microdata is Jul–Sep only, one quarter.)

### The variation lives in error size, not error frequency

| Component across states | CV |
|---|---|
| Case error frequency | 0.137 |
| Average error size ($ per error case) | 0.252 |

States differ more in how *big* their errors are than in how *often* they
err. That points at administration and review practice rather than caseload
composition: when a state errs, the dollar magnitude of the error is the
state-specific part.

### The synthetic generator's gap: it can only predict the national mean

| Check | Value |
|---|---|
| Synth national dollar-rate (n=20,000) | 8.87% |
| State field in synth cases | absent (confirmed) |
| Mean \|real state rate − synth rate\| (caseload-weighted) | 2.20 pp |
| Real mean absolute deviation of state rates about the national mean | 1.98 pp |

The generator's best possible state-level prediction is its national rate,
8.87%. That constant misses each state by 2.2 percentage points on average —
about the same size as the state variation itself (1.98 pp). In calibration
terms: the entire state dimension of the real distribution is unmodeled.

### Cross-check against FNS-published official state rates

| FY | Microdata mean | Published mean | Spearman (rank) | Pearson |
|---|---|---|---|---|
| 2023 | 7.8% | 12.1% | 0.518 | 0.152 |
| 2024 | 8.1% | 9.8% | 0.692 | 0.592 |

Rankings broadly agree (FY2024 Spearman 0.69), but levels diverge because
published rates include procedural errors and federal QC re-review
adjustments that the raw public-use STATUS/AMTERR do not capture. Largest
FY2023 mismatches: Alaska (microdata 4.66% vs published 60.37%), New Jersey
(5.37% vs 35.70%), Hawaii (4.38% vs 20.94%), South Carolina (8.12% vs
22.57%), Delaware (10.15% vs 22.80%). The Pearson for FY2023 (0.15) is
wrecked by these outliers; Spearman is the honest number.

## Verdict

**Hypothesis confirmed: a state dimension is warranted.** State effects are
large (7.4x spread, CV ~0.34 on the dollar rate), persistent (rank stability
Spearman 0.83 year-to-year), and the current generator reproduces exactly
none of them (2.2 pp average per-state miss).

**Form it should take: state-conditioned error-rate offsets, not state
policy parameters.** The evidence points away from policy parameters (SUA
values, broad-based categorical eligibility) and toward
administration/practice:

- The variance sits in average error *size* (CV 0.252), not frequency
  (CV 0.137) — policy parameters mostly change who is eligible and benefit
  levels, which moves frequency; error size moves when caseworkers/agencies
  handle reviews differently.
- State rankings are stable across years (Spearman 0.83 FY23→FY24), which
  fits persistent administrative capacity differences better than policy
  churn.
- The published-vs-microdata gap itself is administration-shaped: procedural
  errors (incomplete reviews, a state-agency practice) are what inflate
  Alaska/NJ/HI official rates far above their payment-error substance.

Concretely: a per-state offset vector fit from pooled microdata-implied
rates (held-out), sampled proportional to caseload, with a national-rate
fallback for unseen states. Calibrate it against *microdata-implied* rates,
not published rates — the published series mixes in procedural errors that
are out of scope for a payment-error copilot.

## Next steps

1. **Prototype state-conditioned generation (recommended next run):** add a
   `--state-mix` input — per-state error-rate multiplier from pooled
   microdata + caseload-weighted state sampling — and measure the per-state
   L1 drop vs the constant-rate baseline. Small, directly tests this verdict.
   - **Done →** [PA1](pa1_pa_generator.md), [NY1](ny1_ny_generator.md): State-conditioned generators built per state (PA, NY, then TX/SD/UT/ID); a national `--state-mix` is still open.
2. **Test the administration hypothesis:** decompose each state's errors
   into agency-caused vs client-caused using the microdata AGENCY cause
   field; if high-rate states skew agency-caused, the offset should apply to
   agency-driven variances specifically.
3. **Procedural-error note:** published-vs-microdata rank gaps correlate
   with known procedural-error episodes (Alaska, NJ FY2023); document which
   of the two rate definitions the copilot is actually trained to predict
   before any transfer evaluation is run.
   - **Done →** [exp40](exp40_published_rate_calibration.md): Rate definition settled: train on the microdata-implied substance rate, not published rates.
