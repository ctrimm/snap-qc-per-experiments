# Finding SNAP Payment Errors Faster in South Dakota

**October 23, 2026 · State brief · Cory Trimm**

## Summary

South Dakota's FY2025 payment error rate was 2.47%, the lowest of 53 jurisdictions and far below the 6% line where H.R. 1 cost sharing begins. South Dakota owes nothing under FY2028 rules at that rate. For South Dakota the tool is about staying there, finding the few errors there are efficiently, and finding underpayments.

- **It finds 4.2 times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **$90 per review hour against $22**. The top 10% finds 6.4 times.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 3.9× edge. Expected error dollars for the top fifth of the queue were 10% above actual.
- **It's fair by design.** Ranking purely by dollars would review elderly households at 0.37 of their share of errors. A floor brings that to 1.08, at a cost of about 5% of the lift (4.2× → 4.0×).
- **Underpayments:** 42% of South Dakota's error dollars are households paid too little (national 28%).
- **Cheap insurance:** at its current rate South Dakota owes nothing. In the model, about 737 ranked reviews a month (2.6 FTEs) would bring a rate of 6.5% or 8.5% back under 6% (see *FY2028 cost share*).

**Recommendation:** a shadow pilot. Score the active caseload, have reviewers work the top of the queue alongside current selection with the fairness floor on, and compare the dollars found with the tool's forecast.

## South Dakota's errors

Federal QC public-use files, FY2020–2024: 2,365 reviewed South Dakota cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | South Dakota | National |
|---|---|---|
| Reviewed cases with an error found | 25.7% | 37.9% |
| Error cases: over / under | 304 / 303 | 61% / 39% |
| Error dollars that are underpayments | 42% | 28% |
| Largest shares of error dollars | Wages and salaries 46%, Shelter deduction 10%, RSDI benefits 7% | Wages and salaries 37%, Shelter deduction 16%, Unit composition 8% |
| Most frequent errors (share of error cases) | Wages and salaries 36%, Shelter deduction 25%, RSDI benefits 7% | Shelter deduction 31%, Wages and salaries 24%, RSDI benefits 7% |
| Errors coded as reporting or timing issues (nature code 97) | 74% | 42% |
| Errors coded "other" (nature code 99) | 0% | 5% |
| Error cases with no per-error dollar amount recorded | 75.1% | 50.4% |

**South Dakota's errors are rarer, smaller and mostly about timing.**
- **Fewer errors:** only about a quarter of reviewed cases have any error, against 38% nationally.
- **Timing:** three in four errors carry the reporting or timing code (national 42%).
- **Wages:** wage errors carry nearly half the error dollars.
- **Small amounts:** the median error is $18, against $28 nationally.
- **A balanced split:** over- and underpayment cases are evenly balanced.

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the benefit issued and the household's maximum allotment.

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

South Dakota's model learns from every state's QC cases plus inputs that describe South Dakota's benefit levels, with its own cases weighted ten times. Pooling lifted South Dakota's model the most of any pilot state: from 2.7× to 4.2× on held-out cases (16th of 53), and from 2.5× to 3.9× on later years.

### Results on cases the model never saw

592 South Dakota cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |
|---|---|---|---|---|
| 10% of the queue | **6.4×** | $138 ($22) | 19% over | 27 |
| 20% of the queue | **4.2×** | $90 ($22) | 10% over | 16 |
| 20%, trained 2020–22, tested 2023–24 | 3.9× | | | 17 |
| 20%, with the fairness floor | 4.0× | | | |

For comparison, a South Dakota-only model found 2.7× on the same held-out cases. Reviews are assumed to take 30 minutes. The 53-jurisdiction median is 3.97× (top 20%).

### Fairness

The measure is each household type's share of reviews compared with its share of error dollars, where 1.0 means proportionate:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.37 | 1.08 |
| Disabled | 0.79 | 1.12 |
| Single parent | 1.85 | 1.01 |
| Childless adult | 0.86 | 0.97 |

The floor costs about 5% of the lift. We recommend it on by default.

### Underpayments

A second ranker trained on underpayments finds 1.9 times the underpayment dollars of random review, against 1.8 times for the main ranker. These figures come from the earlier South Dakota-only models (exp79). In South Dakota the gain is small, so a separate queue adds little there.

### Flag cards for reviewers

Flag-card Rules lines were tested at scale on fresh South Dakota, Idaho and Utah cards (exp97): the small model's citations matched the large model's 100% of the time, and every citation resolved. "Check first" coverage hasn't been measured on South Dakota cases.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

At 2.47%, South Dakota pays nothing. **How much a higher rate would cost:** South Dakota's SNAP benefits are about $176 million a year. Assumptions are the same as the national model's central scenario: 2% of cases reviewed a month, 80% of found errors fixed, errors otherwise lasting 6 months.

| If South Dakota's rate were… | Share owed | Cost a year | Rate after ranked reviews (≈737 a month, 2.6 FTEs) | Rate after random reviews |
|---|---|---|---|---|
| 2.47% (FY2025) | 0% | $0 | 1.54% | 2.25% |
| 6.5% | 5% | about $9M | 4.06% | 5.93% |
| 8.5% | 10% | about $18M | 5.32% | 7.76% |

Ranked reviews bring both hypothetical rates back under 6%. Random reviews of the same volume bring 6.5% under too, but not 8.5%. The further the rate rises, the more the ranking matters.

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in South Dakota

1. **Month 0:** map the case-management fields to the tool's inputs (14 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
2. **Months 1–3, shadow:**
   - **Review:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on.
   - **Random slice:** about 10% of reviews on randomly chosen cases.
   - **Record:** the dollars found and the error type. With so few errors, a quarterly ranking may be enough. Track whether the top of the queue finds errors sooner than current selection.
3. **Read-out:**
   - dollars found against the forecast;
   - dollars per review hour against current selection;
   - how long found errors had lasted and the share fixed (the two cost-share drivers).
4. **Refresh yearly** on the new federal QC sample plus the pilot's findings.

## Limitations

- **Public data only.** The model was built from federal public-use files. South Dakota's own case records would likely do better after a short refit.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **Few errors to learn from.** Five years of South Dakota QC data hold about 600 error cases. The top-10% forecast ran 19% high on held-out cases, so check forecasts against the state's own reviews before quoting them.
- **The policy library doesn't cover South Dakota yet.** It holds 1 South Dakota SNAP document (an employment-and-training policy). Rule citations on flag cards would need South Dakota's SNAP manual added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# South Dakota's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_results.json'))['SD'], indent=1))"
# refit and re-evaluate every jurisdiction's deployed model (reproduces exp83_results.json exactly)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown
python3 experiments/cost_share_replicate.py --state SD
python3 experiments/cost_share_replicate.py --state SD --per 6.5
# regenerate this brief from the results (every figure is computed, not typed)
python3 whitepaper/make_state_brief.py SD
# score cases with the packaged South Dakota model
python3 deliverables/state_rankers/score_cases.py --state SD --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: South Dakota uses variant C_ctx) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **State-only baseline:** exp68.
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 46).
