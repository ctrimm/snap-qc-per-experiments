# Finding SNAP Payment Errors Faster in Idaho

**October 23, 2026 · State brief · Cory Trimm**

## Summary

Idaho's FY2025 payment error rate was 3.85%, the second lowest of 53 jurisdictions and below the 6% line where H.R. 1 cost sharing begins. Idaho owes nothing under FY2028 rules at that rate. For Idaho the tool is about staying below the line and using a small review staff well.

- **It finds 3.6 times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **$79 per review hour against $22**. The top 10% finds 5.5 times.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 3.3× edge. Expected error dollars for the top fifth of the queue were 7% below actual.
- **It's fair by design.** Ranking purely by dollars would review elderly households at 0.59 of their share of error cases. A floor brings that to 1.11, at a cost of about 1% of the lift (3.6× → 3.5×).
- **Underpayments:** 27% of Idaho's error dollars are households paid too little (national 28%).
- **Cheap insurance:** at its current rate Idaho owes nothing. In the model, about 1,300 ranked reviews a month (4.6 FTEs) would bring a rate of 6.5% or 8.5% back under 6% (see *FY2028 cost share*).

**Recommendation:** a shadow pilot. Score the active caseload, have reviewers work the top of the queue alongside current selection with the fairness floor on, and compare the dollars found with the tool's forecast.

## Idaho's errors

Federal QC public-use files, FY2020–2024: 3,839 reviewed Idaho cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | Idaho | National |
|---|---|---|
| Reviewed cases with an error found | 33.7% | 37.9% |
| Error cases: over / under | 785 / 507 | 61% / 39% |
| Error dollars that are underpayments | 27% | 28% |
| Largest shares of error dollars | Wages and salaries 29%, Shelter deduction 25%, RSDI benefits 12% | Wages and salaries 37%, Shelter deduction 16%, Unit composition 8% |
| Most frequent errors (share of error cases) | Shelter deduction 43%, Wages and salaries 21%, Child support received 5% | Shelter deduction 31%, Wages and salaries 24%, RSDI benefits 7% |
| Errors coded as reporting or timing issues (nature code 97) | 64% | 42% |
| Errors coded "other" (nature code 99) | 12% | 5% |
| Error cases with no per-error dollar amount recorded | 37.9% | 50.4% |

**Idaho's errors are dominated by the shelter deduction and by timing.**
- **Shelter:** shelter-deduction errors are 43% of error cases (national 31%).
- **Timing:** 64% of errors carry the reporting or timing code (national 42%).
- **Social Security:** Social Security (RSDI) income carries 12% of error dollars, about twice the national share.
- **Small amounts:** the median error is $17, against $28 nationally.

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the benefit issued and the household's maximum allotment.

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

Idaho's model learns from every state's QC cases plus inputs that describe Idaho's benefit levels. Idaho is near the bottom of the national range: top-20% lift 50th of 53, later-years test 49th, and the fewest error dollars per review hour of all 53 ($79), because its errors are small. Pooling still lifted it from 2.8× to 3.6× on held-out cases, and from 2.5× to 3.3× on later years.

### Results on cases the model never saw

960 Idaho cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |
|---|---|---|---|---|
| 10% of the queue | **5.5×** | $124 ($22) | 12% under | 47 |
| 20% of the queue | **3.6×** | $79 ($22) | 7% under | 50 |
| 20%, trained 2020–22, tested 2023–24 | 3.3× | | | 49 |
| 20%, with the fairness floor | 3.5× | | | |

For comparison, a Idaho-only model found 2.8× on the same held-out cases. Reviews are assumed to take 30 minutes. The 53-jurisdiction median is 3.97× (top 20%).

### Fairness

The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.59 | 1.11 |
| Disabled | 0.74 | 0.85 |
| Single parent | 1.53 | 1.15 |
| Childless adult | 1.26 | 1.09 |

The floor costs about 1% of the lift. We recommend it on by default.

### Underpayments

A second ranker trained on underpayments finds 2.1 times the underpayment dollars of random review, against 1.2 times for the main ranker. These figures come from the earlier Idaho-only models (exp79).

### Flag cards for reviewers

Idaho is where the flag cards have been tested most outside Pennsylvania and New York:
- **Odds:** the cards' "N in 10" odds were recalibrated on Idaho cases (exp74).
- **Rules line:** tested at scale on fresh Idaho, Utah and South Dakota cards (exp97), with 100% agreement with the large model.
- **Where to look:** that model beat generic advice in Idaho after about 100 labelled error cases (exp63).

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

At 3.85%, Idaho pays nothing. **How much a higher rate would cost:** Idaho's SNAP benefits are about $282 million a year. Assumptions are the same as the national model's central scenario: 2% of cases reviewed a month, 80% of found errors fixed, errors otherwise lasting 6 months.

| If Idaho's rate were… | Share owed | Cost a year | Rate after ranked reviews (≈1,300 a month, 4.6 FTEs) | Rate after random reviews |
|---|---|---|---|---|
| 3.85% (FY2025) | 0% | $0 | 2.55% | 3.51% |
| 6.5% | 5% | about $14M | 4.30% | 5.93% |
| 8.5% | 10% | about $28M | 5.62% | 7.76% |

Ranked reviews bring both hypothetical rates back under 6%. Random reviews of the same volume bring 6.5% under too, but not 8.5%. The further the rate rises, the more the ranking matters.

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in Idaho

1. **Month 0:** map the case-management fields to the tool's inputs (14 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
2. **Months 1–3, shadow:**
   - **Review:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on.
   - **Random slice:** about 10% of reviews on randomly chosen cases.
   - **Record:** the dollars found and the error type.
3. **Read-out:**
   - dollars found against the forecast;
   - dollars per review hour against current selection;
   - how long found errors had lasted and the share fixed (the two cost-share drivers).
4. **Refresh yearly** on the new federal QC sample plus the pilot's findings.

## Limitations

- **Public data only.** The model was built from federal public-use files. Idaho's own case records would likely do better after a short refit.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **Small errors.** Idaho's errors are small, so dollars found per review hour are the lowest of 53 jurisdictions even with a 3.6× lift. The case for a pilot rests on accuracy and staying below 6% more than on dollars.
- **The policy library doesn't cover Idaho yet.** It holds 1 Idaho SNAP document (the FY2026 SNAP Employment and Training state plan, amendment 1). Rule citations on flag cards would need Idaho's SNAP manual added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# Idaho's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_results.json'))['ID'], indent=1))"
# refit and re-evaluate every jurisdiction's deployed model (reproduces exp83_results.json exactly)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown
python3 experiments/cost_share_replicate.py --state ID
python3 experiments/cost_share_replicate.py --state ID --per 6.5
# regenerate this brief from the results (every figure is computed, not typed)
python3 whitepaper/make_state_brief.py ID
# score cases with the packaged Idaho model
python3 deliverables/state_rankers/score_cases.py --state ID --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: Idaho uses variant B_ctx) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **State-only baseline:** exp68.
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 16).
