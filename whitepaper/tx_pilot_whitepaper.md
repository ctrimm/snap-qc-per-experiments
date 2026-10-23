# Finding SNAP Payment Errors Faster in Texas

**October 23, 2026 · State brief · Cory Trimm**

## Summary

Texas's FY2025 payment error rate was 9.34%. Under the H.R. 1 cost-sharing rules, that rate means the state would pay 10% of its SNAP benefit costs from FY2028, about **$685 million a year**. This brief shows what a case-ranking tool, built and tested on Texas's federal QC records, could do about that.

- **It finds 3.6 times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **$194 per review hour against $54**. The top 10% finds 5.7 times.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 3.3× edge. Expected error dollars for the top fifth of the queue were 3% above actual.
- **It's fair by design.** Ranking purely by dollars would review elderly households at 0.41 of their share of error cases. A floor brings that to 0.95, with no measurable cost to the lift.
- **Underpayments:** 41% of Texas's error dollars are households paid too little (national 28%).
- **Cost share:** in the central scenario (2% of cases reviewed a month, about 28,837 reviews and 103 FTEs), the rate falls to 6.13%, avoiding about **$343 million a year**. Random reviews of the same volume leave it at 8.52%.

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
- the benefit issued and the household's maximum allotment.

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

Texas's model learns from every state's QC cases plus inputs that describe Texas's benefit levels. Texas is in the lower part of the national range (top-20% lift 45th of 53, later-years test 50th), but pooling still lifted it substantially: from 2.7× to 3.6× on held-out cases, and from 2.3× to 3.3× on later years.

### Results on cases the model never saw

865 Texas cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |
|---|---|---|---|---|
| 10% of the queue | **5.7×** | $306 ($54) | 1% over | 44 |
| 20% of the queue | **3.6×** | $194 ($54) | 3% over | 45 |
| 20%, trained 2020–22, tested 2023–24 | 3.3× | | | 50 |
| 20%, with the fairness floor | 3.6× | | | |

For comparison, a Texas-only model found 2.7× on the same held-out cases. Reviews are assumed to take 30 minutes. The 53-jurisdiction median is 3.97× (top 20%).

### Fairness

The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.41 | 0.95 |
| Disabled | 0.63 | 0.90 |
| Single parent | 1.60 | 1.18 |
| Childless adult | 1.20 | 0.74 |

In Texas the floor came out with no measurable cost (a chance effect on the held-out cases). We recommend it on by default.

### Underpayments

A second ranker trained on underpayments finds 3.9 times the underpayment dollars of random review, against 2.0 times for the main ranker. These figures come from the earlier Texas-only models (exp79).

### Flag cards for reviewers

Texas's QC records carry no per-error dollar amounts, so the "check first" model can't be trained from them alone. In exp63, a where-to-look model beat generic advice after about 100 labelled error cases. A pilot's reviewer findings could supply those in two to four months. Until then, cards can show why a case was flagged and the generic checklist.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

| Scenario | Reviewed a month | Rate after | State share | Avoided a year | Random reviews, same volume |
|---|---|---|---|---|---|
| Today (FY2025 rate) | — | 9.34% | 10% | — | — |
| Low | 1% (14,418 reviews, 52 FTEs) | 8.59% | 10% | $0M | 9.12%, $0M |
| **Central** | 2% (28,837 reviews, 103 FTEs) | 6.13% | 5% | $343M | 8.52%, $0M |
| High | 3% (43,255 reviews, 154 FTEs) | 4.29% | 0% | $685M | 7.68%, $343M |

**The two thresholds.** Under the central scenario's other assumptions, Texas crosses 8% at about **0.7%** of cases reviewed a month (to the 5% share, about $343 million a year avoided) and 6% at about **2.1%** (no share, $685 million a year).

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in Texas

1. **Month 0:** map the case-management fields to the tool's inputs (14 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
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

- **Public data only.** The model was built from federal public-use files. Texas's own case records would likely do better after a short refit.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **Coding practice.** Texas's heavy use of the "other" nature code and its missing per-error dollar amounts make error-type analysis less informative than in most states.
- **The policy library doesn't cover Texas yet.** It holds no Texas SNAP documents (its one Texas benefits document is a TANF FAQ). Rule citations on flag cards would need Texas's SNAP manual added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# Texas's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_results.json'))['TX'], indent=1))"
# refit and re-evaluate every jurisdiction's deployed model (reproduces exp83_results.json exactly)
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
- **State-only baseline:** exp68.
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 48).
