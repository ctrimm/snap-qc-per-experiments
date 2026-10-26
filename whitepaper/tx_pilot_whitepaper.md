# Finding SNAP Payment Errors Faster in Texas

**October 26, 2026 (corrected; first version October 23) · State brief · Cory Trimm**

> **Corrected October 26, 2026.** The October 23 version of this brief overstated the tool's results. Its models used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure here comes from the leak-free rebuild (experiment 107). Figures computed directly from the QC data (error rates, error patterns, caseload shares) were not affected.

## Summary

Texas's FY2025 payment error rate was 9.34%. Under the H.R. 1 cost-sharing rules, that rate means the state would pay 10% of its SNAP benefit costs from FY2028, about **$685 million a year**. This brief shows what a case-ranking tool, built and tested on Texas's federal QC records, could do about that.

- **It finds 2.2 times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **$118 per review hour against $54**. The top 10% finds 2.9 times.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 2.2× edge. Expected error dollars for the top fifth of the queue were 8% below actual.
- **It's fair by design.** Ranking purely by dollars would review elderly households at 0.21 of their share of error cases. A floor brings that to 0.95, at a cost of about 17% of the lift (2.2× → 1.8×).
- **Underpayments:** 41% of Texas's error dollars are households paid too little (national 28%).
- **Cost share:** in the central scenario (2% of cases reviewed a month, about 28,837 reviews and 103 FTEs), the rate falls to 7.92%, avoiding about **$343 million a year**. Random reviews of the same volume leave it at 8.52%.

**Recommendation:** a shadow pilot. Score the active caseload, have reviewers work the top of the queue alongside current selection with the fairness floor on, and compare the dollars found with the tool's forecast.

## Texas's errors

Federal QC public-use files, FY2020–2024: 3,457 reviewed Texas cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | Texas | National |
|---|---|---|
| Reviewed cases with an error found | 44.3% | 37.9% |
| Error cases: over / under | 765 / 765 | 61% / 39% |
| Error dollars that are underpayments | 41% | 28% |
| Largest shares of error dollars | Wages and salaries 31%, Shelter deduction 16%, Unit composition 9% | Wages and salaries 37%, Shelter deduction 16%, Unit composition 8% |
| Most frequent errors (share of error cases) | Shelter deduction 27%, Wages and salaries 23%, Standard utility allowance 7% | Shelter deduction 31%, Wages and salaries 24%, RSDI benefits 7% |
| Errors coded as reporting or timing issues (nature code 97) | 21% | 42% |
| Errors coded "other" (nature code 99) | 24% | 5% |
| Error cases with no per-error dollar amount recorded | 99.9% | 50.4% |

**Texas's distinctive features are in how errors are coded.**
- **Coded "other":** nearly a quarter of its errors carry the "other" nature code (99), about five times the national share. Timing-coded errors run at half the national share.
- **No per-error dollar amounts:** Texas records no per-error dollar amount on virtually every error case (national: about half). The case's total error dollars are still recorded, so the ranker works. But tools that learn *where* in a case the error sits have to learn from reviewers' findings instead (see *Flag cards*).
- **A balanced split:** over- and underpayment cases are evenly balanced, and underpayments are 41% of error dollars (national 28%).

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the household's maximum allotment.

It does not use the benefit the agency issued: in the federal QC data that would let it compare the issued amount with the reviewer's corrected facts (experiment 106).

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

Texas's model learns from every state's QC cases plus Texas's maximum allotments. Among the 53 jurisdictions, Texas ranks 49 on the top-20% lift, 41 on the top-10% lift and 49 on the later-years test (1 = best).

### Results on cases the model never saw

865 Texas cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |
|---|---|---|---|---|
| 10% of the queue | **2.9×** | $156 ($54) | 18% under | 41 |
| 20% of the queue | **2.2×** | $118 ($54) | 8% under | 49 |
| 20%, trained 2020–22, tested 2023–24 | 2.2× | | | 49 |
| 20%, with the fairness floor | 1.8× | | | |

Reviews are assumed to take 30 minutes. The 53-jurisdiction median is 2.70× (top 20%).

### Fairness

The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.21 | 0.95 |
| Disabled | 0.61 | 0.90 |
| Single parent | 1.79 | 1.18 |
| Childless adult | 0.74 | 0.74 |

The floor costs about 17% of the lift. We recommend it on by default.

### Underpayments

A second ranker trained on underpayments finds 1.9 times the underpayment dollars of random review, against 1.4 times for the main ranker (both trained on Texas's own cases; exp79, leak-free).

### Flag cards for reviewers

Texas's QC records carry no per-error dollar amounts, so the "check first" model can't be trained from them alone. In exp63, a where-to-look model beat generic advice after about 100 labelled error cases. A pilot's reviewer findings could supply those in two to four months. Until then, cards can show why a case was flagged and the generic checklist.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

| Scenario | Reviewed a month | Rate after | State share | Avoided a year | Random reviews, same volume |
|---|---|---|---|---|---|
| Today (FY2025 rate) | — | 9.34% | 10% | — | — |
| Low | 1% (14,418 reviews, 52 FTEs) | 8.95% | 10% | $0M | 9.12%, $0M |
| **Central** | 2% (28,837 reviews, 103 FTEs) | 7.92% | 5% | $343M | 8.52%, $0M |
| High | 3% (43,255 reviews, 154 FTEs) | 6.65% | 5% | $343M | 7.68%, $343M |

**The thresholds.** Under the central scenario's other assumptions, Texas crosses 8% at about **1.9%** of cases reviewed a month (5% share); 6% at about **6.2%** of cases reviewed a month (no share).

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in Texas

1. **Month 0:** map the case-management fields to the tool's inputs (13 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
2. **Months 1–3, shadow:**
   - **Review:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on.
   - **Random slice:** about 10% of reviews on randomly chosen cases.
   - **Record:** the dollars found and the error type. Record, for each error found, which part of the case it was in: that builds the training data the "check first" cards need.
3. **Read-out:**
   - dollars found against the forecast;
   - dollars per review hour against current selection;
   - how long found errors had lasted and the share fixed (the two cost-share drivers).
4. **Refresh yearly** on the new federal QC sample plus the pilot's findings.

## Limitations

- **Public data only.** The model was built from federal public-use files, whose income and deduction fields are the QC reviewer's values; for error cases those are the corrected facts, while a deployed tool sees the agency's uncorrected ones. Validate on Texas's own pre-review case records before relying on these numbers.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **Coding practice.** Texas's heavy use of the "other" nature code and its missing per-error dollar amounts make error-type analysis less informative than in most states.
- **The policy library doesn't cover Texas yet.** It holds no Texas SNAP documents (its one Texas benefits document is a TANF FAQ). Rule citations on flag cards would need Texas's SNAP manual added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# Texas's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_leakfree_results.json'))['TX'], indent=1))"
# refit and re-evaluate every jurisdiction's model, leak-free by default (reproduces exp83_leakfree_results.json)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown
python3 experiments/cost_share_replicate.py --state TX
# regenerate this brief from the results (every figure is computed, not typed)
python3 whitepaper/make_state_brief.py TX
# score cases with the packaged Texas model
python3 deliverables/state_rankers/score_cases.py --state TX --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: Texas uses variant B_ctx) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **Leak-free rebuild:** exp106 (the leak), exp107 (the rebuild, later-years test).
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 48).
