# SNAP Payment-Error Ranking: Pennsylvania and New York

**October 23, 2026 (first version September 29, 2026) · Two-state brief · Cory Trimm**

## Summary

The same ranking tool has been built and tested in both states on their federal QC records (FY2020–2024), on cases each model never saw. In both, reviewing the top fifth of the queue finds about four times the error dollars of random review, and dollar forecasts land within 6% of actual.

| Held-out cases, top 20% of the queue | Pennsylvania | New York |
|---|---|---|
| QC cases (held out) | 3,268 (817) | 3,257 (815) |
| Error dollars vs random review | **4.1×** | **4.2×** |
| Found per review hour (random) | $193 ($47) | $234 ($56) |
| Top 10% of the queue vs random | 6.6× | 7.0× |
| Dollar forecast vs actual | 1% under | 6% under |
| Trained 2020–22, tested 2023–24 | 3.8× | 4.1× |
| With the fairness floor | 4.0× | 3.9× |
| "Check first" flag-card coverage (top three items) | 88% | 86% |
| FY2025 payment error rate | 9.21% | 13.18% |
| FY2028 cost share at that rate | 10%, $418M a year | 15%, $1,081M a year |
| Central scenario (2% of cases reviewed a month): rate after | 5.66% | 8.19% |
| Central scenario: avoided a year | $418M | $360M |
| Central scenario: reviews a month (FTEs) | 20,959 (75) | 32,531 (116) |

## The honest differences

- **Pennsylvania's errors are about the shelter deduction:** 45% of its error cases and 24% of error dollars (national 31% and 16%). New York's are about timing: 63% of its errors carry the reporting or timing code (national 42%).
- **New York is in the top cost-share bracket.** The central scenario drops it one bracket (15% → 10%); reaching 6% would take reviewing about 3.9% of cases a month. Pennsylvania crosses 6% at about 1.7%.
- **The fairness floor costs New York more** (about 6% of the lift, against about 3% in Pennsylvania), because ranking purely by dollars under-reviews elderly households more there (0.62 of their share of errors, against 0.65).

## How this evolved

The first version of this brief (September 29) reported the proof of concept: rankers trained only on **synthetic** cases, built to test whether the generator carried real signal. At a 20% review budget they recovered:
- **Pennsylvania:** $5,483 against $3,851 for random review ($67 against $47 per review hour);
- **New York:** $6,958 against $4,574 ($85 against $56).

Those rankers proved the signal; they were never the deployable tool. The current models learn from real QC records (each state's own cases pooled with every other state's) and find about three times as many dollars per review hour ($193 against $67 in Pennsylvania; $234 against $85 in New York). Two findings from the first version still hold:
- **Rank by dollars:** ranking by the chance of an error alone does worse than random at the top of the queue, because frequent errors are small.
- **Arithmetic is not the problem:** the states' benefit arithmetic is sound, so errors come from the facts entered.

## Pilot shape (same for any state)

1. Score a month of active cases with the packaged model.
2. Run in shadow alongside existing review, with the fairness floor on and about 10% of reviews on random cases.
3. Compare dollars found with the forecast.

There are no production system changes and no new data collection.

## Full papers

- `whitepaper/pa_pilot_whitepaper.pdf` and `whitepaper/ny_pilot_whitepaper.pdf`: the state briefs.
- `whitepaper/state_replication_guide.pdf`: how any state reproduces this.

Every figure here is checked against the committed results by `python3 whitepaper/state_numbers.py check`.
