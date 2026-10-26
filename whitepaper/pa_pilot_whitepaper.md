# Finding SNAP Payment Errors Faster in Pennsylvania

**October 26, 2026 (corrected; first version October 23) · State brief · Cory Trimm**

> **Corrected October 26, 2026.** The October 23 version of this brief overstated the tool's results. Its models used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure here comes from the leak-free rebuild (experiment 107). Figures computed directly from the QC data (error rates, error patterns, caseload shares) were not affected.

## Summary

Pennsylvania's FY2025 payment error rate was 9.21%. Under the H.R. 1 cost-sharing rules, that rate means the state would pay 10% of its SNAP benefit costs from FY2028, about **$418 million a year**. This brief shows what a case-ranking tool, built and tested on Pennsylvania's federal QC records, could do about that.

- **It finds 2.7 times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **$128 per review hour against $47**. The top 10% finds 3.7 times.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 2.6× edge. Expected error dollars for the top fifth of the queue were 8% above actual.
- **It's fair by design.** Ranking purely by dollars would review elderly households at 0.42 of their share of error cases. A floor brings that to 0.90, with no measurable cost to the lift.
- **Underpayments:** 26% of Pennsylvania's error dollars are households paid too little (national 28%).
- **Cost share:** in the central scenario (2% of cases reviewed a month, about 20,959 reviews and 75 FTEs), the rate falls to 6.98%, avoiding about **$209 million a year**. Random reviews of the same volume leave it at 8.40%.

**Recommendation:** a shadow pilot. Score the active caseload, have reviewers work the top of the queue alongside current selection with the fairness floor on, and compare the dollars found with the tool's forecast.

## Pennsylvania's errors

Federal QC public-use files, FY2020–2024: 3,268 reviewed Pennsylvania cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | Pennsylvania | National |
|---|---|---|
| Reviewed cases with an error found | 42.7% | 37.9% |
| Error cases: over / under | 843 / 552 | 61% / 39% |
| Error dollars that are underpayments | 26% | 28% |
| Largest shares of error dollars | Wages and salaries 37%, Shelter deduction 24%, Unit composition 7% | Wages and salaries 37%, Shelter deduction 16%, Unit composition 8% |
| Most frequent errors (share of error cases) | Shelter deduction 45%, Wages and salaries 21%, Medical expense deductions 5% | Shelter deduction 31%, Wages and salaries 24%, RSDI benefits 7% |
| Errors coded as reporting or timing issues (nature code 97) | 34% | 42% |
| Errors coded "other" (nature code 99) | 1% | 5% |
| Error cases with no per-error dollar amount recorded | 0.1% | 50.4% |

**Pennsylvania's distinctive problem is the shelter deduction.**
- **Shelter:** it is the most common error by far (45% of error cases, national 31%), and carries 24% of error dollars (national 16%).
- **Wages:** wage errors are less frequent but larger, and carry the most dollars (37%).
- **Ranking:** that's why ranking by the chance of an error alone does poorly; the frequent errors are small. The tool ranks by expected dollars instead.
- **Arithmetic:** benefit arithmetic errors are almost nonexistent (0.1% of error cases), so errors come from the facts entered.

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the household's maximum allotment.

It does not use the benefit the agency issued: in the federal QC data that would let it compare the issued amount with the reviewer's corrected facts (experiment 106).

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

Pennsylvania's model learns from every state's QC cases plus Pennsylvania's maximum allotments, with its own cases weighted ten times. Among the 53 jurisdictions, Pennsylvania ranks 27 on the top-20% lift, 17 on the top-10% lift and 28 on the later-years test (1 = best).

### Results on cases the model never saw

817 Pennsylvania cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |
|---|---|---|---|---|
| 10% of the queue | **3.7×** | $173 ($47) | 2% over | 17 |
| 20% of the queue | **2.7×** | $128 ($47) | 8% over | 27 |
| 20%, trained 2020–22, tested 2023–24 | 2.6× | | | 28 |
| 20%, with the fairness floor | 2.7× | | | |

Reviews are assumed to take 30 minutes. The 53-jurisdiction median is 2.70× (top 20%).

### Fairness

The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.42 | 0.90 |
| Disabled | 0.68 | 1.13 |
| Single parent | 1.83 | 1.07 |
| Childless adult | 2.04 | 1.17 |

In Pennsylvania the floor came out with no measurable cost (a chance effect on the held-out cases). We recommend it on by default.

### Underpayments

A second ranker trained on underpayments finds 2.5 times the underpayment dollars of random review, against 1.9 times for the main ranker (both trained on Pennsylvania's own cases; exp79, leak-free).

### Flag cards for reviewers

Each flagged case can come with a short card saying why it was flagged and which parts of the case to check first. In Pennsylvania the card's top three "check first" items included the real error for 88% of flagged errors (exp65). That figure was measured before experiment 106, on a model using the same reviewer-recorded fields, and has not been rechecked.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

| Scenario | Reviewed a month | Rate after | State share | Avoided a year | Random reviews, same volume |
|---|---|---|---|---|---|
| Today (FY2025 rate) | — | 9.21% | 10% | — | — |
| Low | 1% (10,480 reviews, 37 FTEs) | 8.65% | 10% | $0M | 8.99%, $0M |
| **Central** | 2% (20,959 reviews, 75 FTEs) | 6.98% | 5% | $209M | 8.40%, $0M |
| High | 3% (31,439 reviews, 112 FTEs) | 5.35% | 0% | $418M | 7.57%, $209M |

**The thresholds.** Under the central scenario's other assumptions, Pennsylvania crosses 8% at about **0.9%** of cases reviewed a month (5% share); 6% at about **3.3%** of cases reviewed a month (no share).

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in Pennsylvania

1. **Month 0:** map the case-management fields to the tool's inputs (13 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
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

- **Public data only.** The model was built from federal public-use files, whose income and deduction fields are the QC reviewer's values; for error cases those are the corrected facts, while a deployed tool sees the agency's uncorrected ones. Validate on Pennsylvania's own pre-review case records before relying on these numbers.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **The policy library doesn't cover Pennsylvania yet.** It holds 3 Pennsylvania SNAP documents (DHS operations memoranda). Rule citations on flag cards would need Pennsylvania's SNAP manual added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# Pennsylvania's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_leakfree_results.json'))['PA'], indent=1))"
# refit and re-evaluate every jurisdiction's model, leak-free by default (reproduces exp83_leakfree_results.json)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown
python3 experiments/cost_share_replicate.py --state PA
# regenerate this brief from the results (every figure is computed, not typed)
python3 whitepaper/make_state_brief.py PA
# score cases with the packaged Pennsylvania model
python3 deliverables/state_rankers/score_cases.py --state PA --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: Pennsylvania uses variant C_ctx) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **Leak-free rebuild:** exp106 (the leak), exp107 (the rebuild, later-years test).
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 42).
