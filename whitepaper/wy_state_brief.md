# Finding SNAP Payment Errors Faster in Wyoming

**October 26, 2026 (corrected; first version October 23) · State brief · Cory Trimm**

> **Corrected October 26, 2026.** The October 23 version of this brief overstated the tool's results. Its models used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure here comes from the leak-free rebuild (experiment 107). Figures computed directly from the QC data (error rates, error patterns, caseload shares) were not affected.

## Summary

Wyoming's FY2025 payment error rate was 3.96%, the third lowest of 53 jurisdictions (after South Dakota and Idaho) and below the 6% line where H.R. 1 cost sharing begins. Wyoming owes nothing under FY2028 rules at that rate. So for Wyoming, a case-ranking tool is about staying below 6%, finding households that are being underpaid, and using a small review staff well.

- **It finds 2.0 times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **$55 per review hour against $28**. The top 10% finds 2.1 times.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 2.1× edge. Expected error dollars for the top fifth of the queue were 2% above actual.
- **It's fair by design.** Ranking purely by dollars would review elderly households at 0.27 of their share of error cases. A floor brings that to 1.35, at a cost of about 31% of the lift (2.0× → 1.4×).
- **Underpayments:** 54% of Wyoming's error dollars are households paid too little (national 28%).
- **Cheap insurance:** at its current rate Wyoming owes nothing. In the model, about 268 ranked reviews a month (1.0 FTEs) would bring a rate of 6.5% back under 6% (see *FY2028 cost share*).

**Recommendation:** a shadow pilot. Score the active caseload, have reviewers work the top of the queue alongside current selection with the fairness floor on, and compare the dollars found with the tool's forecast.

## Wyoming's errors

Federal QC public-use files, FY2020–2024: 1,191 reviewed Wyoming cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | Wyoming | National |
|---|---|---|
| Reviewed cases with an error found | 34.0% | 37.9% |
| Error cases: over / under | 202 / 203 | 61% / 39% |
| Error dollars that are underpayments | 54% | 28% |
| Largest shares of error dollars | Wages and salaries 28%, Shelter deduction 18%, Medical expense deductions 12% | Wages and salaries 37%, Shelter deduction 16%, Unit composition 8% |
| Most frequent errors (share of error cases) | Shelter deduction 25%, Wages and salaries 24%, Medical expense deductions 17% | Shelter deduction 31%, Wages and salaries 24%, RSDI benefits 7% |
| Errors coded as reporting or timing issues (nature code 97) | 57% | 42% |
| Errors coded "other" (nature code 99) | 3% | 5% |
| Error cases with no per-error dollar amount recorded | 55.1% | 50.4% |

**Wyoming's errors run both ways.**
- **Underpayments:** 54% of Wyoming's error dollars are underpayments, nearly twice the national share (28%). Over- and underpayment cases are evenly split.
- **Medical deductions:** they carry 12% of its error dollars and 17% of its errors, about four times the national shares. That points to verifying and updating medical expenses as a specific area to review.
- **Few cases:** five years of QC data hold about 1,200 Wyoming cases and about 400 errors, so patterns here are less certain than in large states.

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the household's maximum allotment.

It does not use the benefit the agency issued: in the federal QC data that would let it compare the issued amount with the reviewer's corrected facts (experiment 106).

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

Wyoming's model learns from every state's QC cases plus Wyoming's maximum allotments. Among the 53 jurisdictions, Wyoming ranks 53 on the top-20% lift, 52 on the top-10% lift and 50 on the later-years test (1 = best).

### Results on cases the model never saw

297 Wyoming cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |
|---|---|---|---|---|
| 10% of the queue | **2.1×** | $58 ($27) | 3% under | 52 |
| 20% of the queue | **2.0×** | $55 ($28) | 2% over | 53 |
| 20%, trained 2020–22, tested 2023–24 | 2.1× | | | 50 |
| 20%, with the fairness floor | 1.4× | | | |

Reviews are assumed to take 30 minutes. The 53-jurisdiction median is 2.70× (top 20%).

### Fairness

The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.27 | 1.35 |
| Disabled | 0.37 | 0.83 |
| Single parent | 1.25 | 1.09 |
| Childless adult | 0.86 | 0.86 |

The floor costs about 31% of the lift. We recommend it on by default.

### Underpayments

A second ranker trained on underpayments finds 2.8 times the underpayment dollars of random review, against 2.8 times for the main ranker (both trained on Wyoming's own cases; exp79, leak-free).

### Flag cards for reviewers

"Check first" coverage hasn't been measured on Wyoming cases.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

At 3.96%, Wyoming pays nothing. **How much a higher rate would cost:** Wyoming's SNAP benefits are about $60 million a year. Assumptions are the same as the national model's central scenario: 2% of cases reviewed a month, 80% of found errors fixed, errors otherwise lasting 6 months.

| If Wyoming's rate were… | Share owed | Cost a year | Rate after ranked reviews (≈268 a month, 1.0 FTEs) | Rate after random reviews |
|---|---|---|---|---|
| 3.96% (FY2025) | 0% | $0 | 3.35% | 3.61% |
| 6.5% | 5% | about $3M | 5.50% | 5.93% |
| 8.5% | 10% | about $6M | 7.19% | 7.76% |

Ranked reviews bring 6.5% back under 6%; random reviews of the same volume bring 6.5% back under.

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in Wyoming

1. **Month 0:** map the case-management fields to the tool's inputs (13 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
2. **Months 1–3, shadow:**
   - **Review:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on.
   - **Random slice:** about 10% of reviews on randomly chosen cases.
   - **Record:** the dollars found and the error type. Score quarterly rather than monthly at first, and run the underpayment queue alongside the main one.
3. **Read-out:**
   - dollars found against the forecast;
   - dollars per review hour against current selection;
   - how long found errors had lasted and the share fixed (the two cost-share drivers).
4. **Refresh yearly** on the new federal QC sample plus the pilot's findings.

## Limitations

- **Public data only.** The model was built from federal public-use files, whose income and deduction fields are the QC reviewer's values; for error cases those are the corrected facts, while a deployed tool sees the agency's uncorrected ones. Validate on Wyoming's own pre-review case records before relying on these numbers.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **Small sample.** About 1,200 QC cases and 300 held-out cases; check forecasts against Wyoming's own reviews before quoting them.
- **The policy library doesn't cover Wyoming yet.** It holds 1 Wyoming SNAP document (the FY2026 SNAP Employment and Training state plan). Rule citations on flag cards would need Wyoming's SNAP manual added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# Wyoming's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_leakfree_results.json'))['WY'], indent=1))"
# refit and re-evaluate every jurisdiction's model, leak-free by default (reproduces exp83_leakfree_results.json)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown
python3 experiments/cost_share_replicate.py --state WY
python3 experiments/cost_share_replicate.py --state WY --per 6.5
# regenerate this brief from the results (every figure is computed, not typed)
python3 whitepaper/make_state_brief.py WY
# score cases with the packaged Wyoming model
python3 deliverables/state_rankers/score_cases.py --state WY --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: Wyoming uses variant B_ctx) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **Leak-free rebuild:** exp106 (the leak), exp107 (the rebuild, later-years test).
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 56).
