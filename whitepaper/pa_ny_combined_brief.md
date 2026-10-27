# SNAP Payment-Error Ranking: Pennsylvania and New York

**October 26, 2026 (corrected; first versions September 29 and October 23, 2026) · Two-state brief · Cory Trimm**

> **Corrected October 26, 2026.** The October 23 version overstated the tool's results. Its models used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure here comes from the October 26 rebuild: leak-free inputs (experiment 107), trained and scored on the errors that count toward the official payment error rate, errors the QC reviewer found whose amount is over the federal tolerance (experiments 111–112).

## Summary

The same ranking tool has been built and tested in both states on their federal QC records (FY2020–2024), on cases each model never saw. Reviewing the top fifth of the queue finds about **3.0 times** (Pennsylvania) and **3.5 times** (New York) the error dollars of random review. Those are the dollars of errors over the federal tolerance, the ones the official payment error rate counts.

| Held-out cases, top 20% of the queue | Pennsylvania | New York |
|---|---|---|
| QC cases (held out) | 3,268 (817) | 3,257 (815) |
| Error dollars vs random review | **3.0×** | **3.5×** |
| Found per review hour (random) | $109 ($36) | $163 ($47) |
| Top 10% of the queue vs random | 4.4× | 5.2× |
| Dollar forecast vs actual | 17% over | 7% under |
| Trained 2020–22, tested 2023–24 | 3.0× | 3.6× |
| With the fairness floor | 2.7× | 3.3× |
| FY2025 payment error rate | 9.21% | 13.18% |
| FY2028 cost share at that rate | 10%, $418M a year | 15%, $1,081M a year |
| Central scenario (2% of cases reviewed a month): rate after | 6.61% | 8.99% |
| Central scenario: share and amount avoided a year | 10% → 5%, $209M | 15% → 10%, $360M |
| Central scenario: reviews a month (FTEs) | 20,959 (75) | 32,531 (116) |

## The honest differences

- **What goes wrong:**
  - **Pennsylvania:** its errors are about the shelter deduction: 45% of its error cases and 24% of error dollars (national 31% and 16%).
  - **New York:** its errors are about timing: 63% carry the reporting or timing code (national 42%).
- **Neither state clears 6% in the central scenario.**
  - **Pennsylvania:** it would need about 2.7% of cases reviewed a month.
  - **New York:** each bracket needs more review: 10% at about 1.4% of cases a month, 8% at 2.8%, and 6% at 5.1%.
- **The fairness floor costs both states.** Ranking purely by dollars reviews elderly households at 0.71 (Pennsylvania) and 0.72 (New York) of their share of error cases. The floor brings them to 0.94 and 1.28. It costs Pennsylvania about 10% of its lift and New York about 7%.

## How this evolved

**September 29: proof of concept.** The first version of this brief reported rankers trained only on **synthetic** cases, built to test whether the generator carried real signal. At a 20% review budget they recovered:
- **Pennsylvania:** $5,483 against $3,851 for random review ($67 against $47 per review hour);
- **New York:** $6,958 against $4,574 ($85 against $56).

**October 23: real QC records.** The models moved to real QC records and reported 4.1× and 4.2×. Those numbers were inflated by the reviewer-recorded inputs described above.

**October 26: today's models (3.0× and 3.5×).** Leak-free, and counting only errors over the tolerance. Their per-hour figures aren't comparable with the proof of concept's, which counted every error.

**Two findings from the first version still hold:**
- **Rank by dollars:** ranking by the chance of an error alone does worse than random at the top of the queue, because frequent errors are small.
- **Arithmetic is not the problem:** the states' benefit arithmetic is sound, so errors come from the facts entered.

## Pilot shape (same for any state)

1. Score a month of active cases with the packaged model.
2. Run in shadow alongside existing review, with the fairness floor on and about 10% of reviews on random cases.
3. Compare dollars found with the forecast.

A pilot on the state's own pre-review case records is also the first real test of these numbers. The public data's income and deduction fields are reviewer values for error cases. Rebuilding pre-review values (experiment 109) cut our model's dollar recall by about 17% on a one-year-ahead test, so expect real results somewhat below these.

## Full papers

- `whitepaper/pa_pilot_whitepaper.pdf` and `whitepaper/ny_pilot_whitepaper.pdf`: the state briefs.
- `whitepaper/state_replication_guide.pdf`: how any state reproduces this.

Every figure here is checked against the committed results by `python3 whitepaper/state_numbers.py check`.
