# Finding SNAP Payment Errors Faster in New York

**October 26, 2026 (corrected; first version October 23) · State brief · Cory Trimm**

> **Corrected October 26, 2026.** The October 23 version of this brief overstated the tool's results. Its models used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure here comes from the leak-free rebuild (experiment 107). Figures computed directly from the QC data (error rates, error patterns, caseload shares) were not affected.

## Summary

New York's FY2025 payment error rate was 13.18%. Under the H.R. 1 cost-sharing rules that is the top bracket: from FY2028 the state would pay 15% of its SNAP benefit costs, about **$1.08 billion a year**. This brief shows what a case-ranking tool, built and tested on New York's federal QC records, could do about that.

- **It finds 3.0 times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find about **$171 per review hour against $56**. The top 10% finds 4.3 times.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 3.1× edge. Expected error dollars for the top fifth of the queue were 1% above actual.
- **It's fair by design.** Ranking purely by dollars would review elderly households at 0.54 of their share of error cases. A floor brings that to 1.20, at a cost of about 16% of the lift (3.0× → 2.5×).
- **Underpayments:** 28% of New York's error dollars are households paid too little (national 28%).
- **Cost share:** in the central scenario (2% of cases reviewed a month, about 32,531 reviews and 116 FTEs), the rate falls to 9.96%, avoiding about **$360 million a year**. Random reviews of the same volume leave it at 12.03%.

**Recommendation:** a shadow pilot. Score the active caseload, have reviewers work the top of the queue alongside current selection with the fairness floor on, and compare the dollars found with the tool's forecast.

## New York's errors

Federal QC public-use files, FY2020–2024: 3,257 reviewed New York cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | New York | National |
|---|---|---|
| Reviewed cases with an error found | 36.7% | 37.9% |
| Error cases: over / under | 696 / 498 | 61% / 39% |
| Error dollars that are underpayments | 28% | 28% |
| Largest shares of error dollars | Wages and salaries 39%, Shelter deduction 11%, Unit composition 10% | Wages and salaries 37%, Shelter deduction 16%, Unit composition 8% |
| Most frequent errors (share of error cases) | Shelter deduction 27%, Wages and salaries 23%, RSDI benefits 10% | Shelter deduction 31%, Wages and salaries 24%, RSDI benefits 7% |
| Errors coded as reporting or timing issues (nature code 97) | 63% | 42% |
| Errors coded "other" (nature code 99) | 1% | 5% |
| Error cases with no per-error dollar amount recorded | 0.0% | 50.4% |

**New York's distinctive problem is timing.**
- **Timing:** nearly two-thirds of its errors (63%) carry the reporting or timing code, half again the national share (42%). The facts changed, usually income or household members, and the case wasn't updated in time.
- **Where the dollars are:** wages carry the most error dollars (39%). Social Security, unemployment benefits and household composition each carry more than their national share.

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the household's maximum allotment.

It does not use the benefit the agency issued: in the federal QC data that would let it compare the issued amount with the reviewer's corrected facts (experiment 106).

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

New York's model learns from every state's QC cases plus New York's maximum allotments. Among the 53 jurisdictions, New York ranks 5 on the top-20% lift, 7 on the top-10% lift and 4 on the later-years test (1 = best).

### Results on cases the model never saw

815 New York cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual | Rank of 53 |
|---|---|---|---|---|
| 10% of the queue | **4.3×** | $238 ($56) | 4% over | 7 |
| 20% of the queue | **3.0×** | $171 ($56) | 1% over | 5 |
| 20%, trained 2020–22, tested 2023–24 | 3.1× | | | 4 |
| 20%, with the fairness floor | 2.5× | | | |

Reviews are assumed to take 30 minutes. The 53-jurisdiction median is 2.70× (top 20%).

### Fairness

The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.54 | 1.20 |
| Disabled | 0.71 | 0.88 |
| Single parent | 1.43 | 0.84 |
| Childless adult | 1.11 | 0.77 |

The floor costs about 16% of the lift. We recommend it on by default.

### Underpayments

A second ranker trained on underpayments finds 2.0 times the underpayment dollars of random review, against 1.6 times for the main ranker (both trained on New York's own cases; exp79, leak-free).

### Flag cards for reviewers

Each flagged case can come with a short card saying why it was flagged and which parts of the case to check first. In New York the card's top three "check first" items included the real error for 89% of flagged errors on the leak-free model (exp108; 86% before). A fixed list of New York's three most common error locations would cover 79%, so the model's value is mostly in which item it lists first.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

| Scenario | Reviewed a month | Rate after | State share | Avoided a year | Random reviews, same volume |
|---|---|---|---|---|---|
| Today (FY2025 rate) | — | 13.18% | 15% | — | — |
| Low | 1% (16,266 reviews, 58 FTEs) | 12.42% | 15% | $0M | 12.87%, $0M |
| **Central** | 2% (32,531 reviews, 116 FTEs) | 9.96% | 10% | $360M | 12.03%, $0M |
| High | 3% (48,797 reviews, 174 FTEs) | 7.63% | 5% | $721M | 10.84%, $0M |

**The thresholds.** Under the central scenario's other assumptions, New York crosses 10% at about **2.0%** of cases reviewed a month (10% share); 8% at about **4.0%** of cases reviewed a month (5% share); 6% at about **7.4%** of cases reviewed a month (no share).

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in New York

1. **Month 0:** map the case-management fields to the tool's inputs (13 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
2. **Months 1–3, shadow:**
   - **Review:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on.
   - **Random slice:** about 10% of reviews on randomly chosen cases.
   - **Record:** the dollars found and the error type. Record when the underlying change happened: timing errors are New York's main problem.
3. **Read-out:**
   - dollars found against the forecast;
   - dollars per review hour against current selection;
   - how long found errors had lasted and the share fixed (the two cost-share drivers).
4. **Refresh yearly** on the new federal QC sample plus the pilot's findings.

## Limitations

- **Public data only.** The model was built from federal public-use files, whose income and deduction fields are the QC reviewer's values; for error cases those are the corrected facts, while a deployed tool sees the agency's uncorrected ones. Validate on New York's own pre-review case records before relying on these numbers.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **The policy library doesn't cover New York yet.** It holds 5 New York SNAP documents (an OTDA administrative directive and GIS messages). Rule citations on flag cards would need New York's SNAP manual added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# New York's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_leakfree_results.json'))['NY'], indent=1))"
# refit and re-evaluate every jurisdiction's model, leak-free by default (reproduces exp83_leakfree_results.json)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown
python3 experiments/cost_share_replicate.py --state NY
# regenerate this brief from the results (every figure is computed, not typed)
python3 whitepaper/make_state_brief.py NY
# score cases with the packaged New York model
python3 deliverables/state_rankers/score_cases.py --state NY --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: New York uses variant B_ctx) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **Leak-free rebuild:** exp106 (the leak), exp107 (the rebuild, later-years test).
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 36).
