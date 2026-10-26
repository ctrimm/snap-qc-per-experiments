# Finding SNAP Payment Errors Faster in Utah

**October 26, 2026 (corrected; first version October 23) · State brief · Cory Trimm**

> **Corrected October 26, 2026.** The October 23 version of this brief overstated the tool's results. Its models used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure here comes from the leak-free rebuild (experiment 107). Figures computed directly from the QC data (error rates, error patterns, caseload shares) were not affected.

## Summary

Utah's FY2025 payment error rate was 5.54%, the eighth lowest of 53 jurisdictions and just under the 6% line where H.R. 1 cost sharing begins. Utah owes nothing at that rate. But it is the closest of the pilot states to the line: a rise of half a point would cost about $19 million a year.

- **It finds 2.2 times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **$57 per review hour against $26**. The top 10% finds 2.1 times.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 2.4× edge. Expected error dollars for the top fifth of the queue were 20% above actual.
- **It's fair by design.** Ranking purely by dollars would review elderly households at 0.30 of their share of error cases. A floor brings that to 1.09, at a cost of about 25% of the lift (2.2× → 1.6×).
- **Underpayments:** 37% of Utah's error dollars are households paid too little (national 28%).
- **Cheap insurance:** at its current rate Utah owes nothing. In the model, about 1,633 ranked reviews a month (5.8 FTEs) would bring a rate of 6.5% back under 6% (see *FY2028 cost share*).

**Recommendation:** a shadow pilot. Score the active caseload, have reviewers work the top of the queue alongside current selection with the fairness floor on, and compare the dollars found with the tool's forecast.

## Utah's errors

Federal QC public-use files, FY2020–2024: 4,101 reviewed Utah cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | Utah | National |
|---|---|---|
| Reviewed cases with an error found | 32.8% | 37.9% |
| Error cases: over / under | 779 / 568 | 61% / 39% |
| Error dollars that are underpayments | 37% | 28% |
| Largest shares of error dollars | Wages and salaries 26%, Shelter deduction 22%, Child support received 6% | Wages and salaries 37%, Shelter deduction 16%, Unit composition 8% |
| Most frequent errors (share of error cases) | Shelter deduction 32%, Wages and salaries 28%, Child support received 6% | Shelter deduction 31%, Wages and salaries 24%, RSDI benefits 7% |
| Errors coded as reporting or timing issues (nature code 97) | 46% | 42% |
| Errors coded "other" (nature code 99) | 0% | 5% |
| Error cases with no per-error dollar amount recorded | 67.4% | 50.4% |

**Utah's errors center on the shelter deduction.**
- **Shelter:** shelter-deduction errors are the most common (32% of error cases, national 31%) and carry 22% of error dollars (national 16%).
- **Wages:** wage errors carry 26%.
- **Child support and self-employment:** child support received and self-employment income each carry more than their national share of dollars.
- **Direction:** overpayment cases outnumber underpayment cases about 4 to 3, and underpayments are 37% of error dollars.

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the household's maximum allotment.

It does not use the benefit the agency issued: in the federal QC data that would let it compare the issued amount with the reviewer's corrected facts (experiment 106).

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

Utah's model learns from every state's QC cases plus Utah's maximum allotments. Among the 53 jurisdictions, Utah ranks 50 on the top-20% lift, 53 on the top-10% lift and 40 on the later-years test (1 = best).

### Results on cases the model never saw

1,026 Utah cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |
|---|---|---|---|---|
| 10% of the queue | **2.1×** | $55 ($26) | 49% over | 53 |
| 20% of the queue | **2.2×** | $57 ($26) | 20% over | 50 |
| 20%, trained 2020–22, tested 2023–24 | 2.4× | | | 40 |
| 20%, with the fairness floor | 1.6× | | | |

Reviews are assumed to take 30 minutes. The 53-jurisdiction median is 2.70× (top 20%).

### Fairness

The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.30 | 1.09 |
| Disabled | 0.55 | 1.00 |
| Single parent | 1.55 | 1.05 |
| Childless adult | 0.70 | 0.80 |

The floor costs about 25% of the lift. We recommend it on by default.

### Underpayments

A second ranker trained on underpayments finds 1.3 times the underpayment dollars of random review, against 1.1 times for the main ranker (both trained on Utah's own cases; exp79, leak-free).

### Flag cards for reviewers

Flag-card Rules lines were tested at scale on fresh Utah, Idaho and South Dakota cards (exp97): the small model's citations matched the large model's 100% of the time, and every citation resolved. "Check first" coverage hasn't been measured on Utah cases.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

At 5.54%, Utah pays nothing. **How much a higher rate would cost:** Utah's SNAP benefits are about $372 million a year. Assumptions are the same as the national model's central scenario: 2% of cases reviewed a month, 80% of found errors fixed, errors otherwise lasting 6 months.

| If Utah's rate were… | Share owed | Cost a year | Rate after ranked reviews (≈1,633 a month, 5.8 FTEs) | Rate after random reviews |
|---|---|---|---|---|
| 5.54% (FY2025) | 0% | $0 | 4.80% | 5.05% |
| 6.5% | 5% | about $19M | 5.63% | 5.93% |
| 8.5% | 10% | about $37M | 7.37% | 7.76% |

Ranked reviews bring 6.5% back under 6%; random reviews of the same volume bring 6.5% back under.

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in Utah

1. **Month 0:** map the case-management fields to the tool's inputs (13 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
2. **Months 1–3, shadow:**
   - **Review:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on.
   - **Random slice:** about 10% of reviews on randomly chosen cases.
   - **Record:** the dollars found and the error type. Because Utah sits just under 6%, the pilot's main readout is whether ranked reviews move the rate, so measure how long found errors had lasted and the share actually fixed.
3. **Read-out:**
   - dollars found against the forecast;
   - dollars per review hour against current selection;
   - how long found errors had lasted and the share fixed (the two cost-share drivers).
4. **Refresh yearly** on the new federal QC sample plus the pilot's findings.

## Limitations

- **Public data only.** The model was built from federal public-use files, whose income and deduction fields are the QC reviewer's values; for error cases those are the corrected facts, while a deployed tool sees the agency's uncorrected ones. Validate on Utah's own pre-review case records before relying on these numbers.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **The policy library doesn't cover Utah yet.** It holds 1 Utah SNAP document (the FY2026 SNAP Employment and Training state plan). Rule citations on flag cards would need Utah's SNAP manual added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# Utah's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_leakfree_results.json'))['UT'], indent=1))"
# refit and re-evaluate every jurisdiction's model, leak-free by default (reproduces exp83_leakfree_results.json)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown
python3 experiments/cost_share_replicate.py --state UT
python3 experiments/cost_share_replicate.py --state UT --per 6.5
# regenerate this brief from the results (every figure is computed, not typed)
python3 whitepaper/make_state_brief.py UT
# score cases with the packaged Utah model
python3 deliverables/state_rankers/score_cases.py --state UT --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: Utah uses variant B_ctx) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **Leak-free rebuild:** exp106 (the leak), exp107 (the rebuild, later-years test).
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 49).
