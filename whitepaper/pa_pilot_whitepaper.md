# Finding SNAP Payment Errors Faster in Pennsylvania

**October 23, 2026 · State brief · Cory Trimm**


> **Under review (October 26, 2026).** The case-ranking figures in this paper are inflated and should not be cited until corrected figures are published. That covers lift over random review, dollars per review hour, forecast accuracy, the FY2028 cost-share scenarios, and review ratios and fairness-floor results. The models' inputs included values recorded by QC reviewers (corrected income, deductions and household size), which a state would not have before a review (experiment 106). Figures computed directly from the QC data are not affected: error rates, error patterns, caseload shares and dollar concentration.

## Summary

Pennsylvania's FY2025 payment error rate was 9.21%. Under the H.R. 1 cost-sharing rules, that rate means the state would pay 10% of its SNAP benefit costs from FY2028, about **$418 million a year**. This brief shows what a case-ranking tool, built and tested on Pennsylvania's own federal QC records, could do about that.

- **It finds about four times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find 4.1 times the error dollars of a random selection, about **$193 per review hour against $47**. The top 10% finds 6.6 times.
- **Its forecasts are accurate and it holds up over time.** Expected error dollars for the top of the queue landed within 1% of actual. Trained on 2020–22 and tested on 2023–24, it kept a 3.8× edge.
- **It's fair by design for a small cost.** Ranking purely by dollars would under-review elderly households. A floor fixes that for about 3% of the gain (4.1× → 4.0×).
- **It could take Pennsylvania out of cost share.** In the central scenario, reviewing 2% of cases a month in the tool's order brings the rate to about 5.7%, below the 6% threshold, avoiding the full $418 million a year. Random reviews of the same volume would leave the state at 8.4%, still paying 10%.
- **Effort:** about 21,000 reviews a month, roughly 75 reviewer FTEs, in the central scenario.

**Recommendation:** a three-month shadow pilot. Score one month's active cases, have reviewers work the top of the queue alongside current selection, and compare the dollars found with the tool's forecast.

## Pennsylvania's errors

Federal QC public-use files, FY2020–2024: 3,268 reviewed Pennsylvania cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | Pennsylvania | National |
|---|---|---|
| Reviewed cases with an error found | 42.7% | 37.9% |
| Error dollars that are underpayments | 26% | 28% |
| Largest share of error dollars | Wages and salaries 37% | Wages and salaries 37% |
| Second largest | **Shelter deduction 24%** | Shelter deduction 16% |
| Most frequent error | **Shelter deduction, 45% of error cases** | Shelter deduction, 31% |
| Errors coded as reporting or timing issues (nature code 97) | 34% | 42% |
| Arithmetic errors | 0.1% | 1.3% |

**Pennsylvania's distinctive problem is the shelter deduction.** It is the most common error by far, and a quarter of the dollars. Wage errors are less frequent but larger, and they carry the most dollars. That's why ranking by the chance of an error alone does poorly: the frequent errors are small. The tool ranks by **expected dollars** instead.

**The benefit math itself is sound.** Arithmetic errors are almost nonexistent, so errors come from the facts entered: income, housing costs, household members.

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the benefit issued and the household's maximum allotment.

It estimates two things, the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

Pennsylvania's model learns from every state's QC cases, with Pennsylvania's own cases weighted ten times. This "pooled" model beat a Pennsylvania-only model on both tests (3.5× → 4.1× on held-out cases, 3.1× → 3.8× on later years).

### Results on cases the model never saw

817 Pennsylvania cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual |
|---|---|---|---|
| 10% of the queue | **6.6×** | $308 ($47) | 2% under |
| 20% of the queue | **4.1×** | $193 ($47) | 1% under |
| 20%, trained 2020–22, tested 2023–24 | 3.8× | | |
| 20%, with the fairness floor | 4.0× | | |

Reviews are assumed to take 30 minutes. A state can quote "the top fifth of this month's queue likely holds about $X of errors" with a ±15–20% band.

### Fairness

The measure is each household type's share of reviews divided by its share of cases with an error (its error risk), where 1.0 means reviewed in proportion to risk:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.65 | 0.90 |
| Disabled | 0.92 | 1.13 |
| Single parent | 1.47 | 1.07 |
| Childless adult | 1.36 | 1.17 |

The floor guarantees each type a review share in line with its errors. It costs about 3% of the lift. We recommend it on by default.

### Underpayments

About a quarter of Pennsylvania's error dollars are households paid too little. A second ranker trained on underpayments finds 3.9 times the underpayment dollars of random review, against 2.0 times for the main ranker. These figures come from the earlier Pennsylvania-only models (exp79). Pennsylvania could give part of its review budget to this queue.

### Flag cards for reviewers

Each flagged case can come with a short card saying why it was flagged and which parts of the case to check first. In Pennsylvania the card's top three "check first" items include the real error for **88%** of flagged errors. Its "N in 10" odds were recalibrated so they mean what they say. A blind reviewer comparison of template and model-written cards is packaged for a pilot.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

| Scenario | Reviewed a month | Rate after | State share | Avoided a year | Random reviews, same volume |
|---|---|---|---|---|---|
| Today (FY2025 rate) | — | 9.21% | 10% | — | — |
| Low | 1% (10,480 reviews, 37 FTEs) | 8.41% | 10% | $0 | 8.99%, $0 |
| **Central** | **2% (20,959 reviews, 75 FTEs)** | **5.66%** | **0%** | **$418M** | 8.40%, $0 |
| High | 3% (31,438 reviews, 112 FTEs) | 3.82% | 0% | $418M | 7.57%, $209M |

**What it takes to cross 6%:** under the central scenario's other assumptions, Pennsylvania crosses 6% at about **1.7% of cases reviewed a month**. Savings come only when the rate drops a bracket, so the result is all-or-nothing around that line.

**What drives the range:** how many cases are reviewed and how long an error would otherwise have lasted matter more than the tool's accuracy. A pilot should measure both.

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in Pennsylvania

1. **Month 0:** map the case-management fields to the tool's inputs (14 fields plus the maximum allotment) and score a current month's active cases. The model runs on a laptop.
2. **Months 1–3, shadow:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on, flag cards attached and about 10% of reviews on randomly chosen cases. Record the dollars found and the error type.
3. **Read-out:**
   - dollars found against the forecast;
   - dollars per review hour against current selection;
   - the two cost-share drivers (how long found errors had lasted, and the share actually fixed);
   - reviewer ratings of the flag cards.
4. **Refresh yearly** on the new federal QC sample plus the pilot's findings. A model retrained only on the cases it flags loses about 15% of its edge in four years.

## Limitations

- **Public data only.** The model was built from federal public-use files. Pennsylvania's own case records hold more detail and would likely do better after a short refit.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **The policy library is thin for Pennsylvania.** It holds 3 Pennsylvania SNAP documents (DHS operations memoranda), against 755 for California. Flag-card rule citations and policy lookups would need Pennsylvania's SNAP manual and operations memoranda added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# Pennsylvania's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_results.json'))['PA'], indent=1))"
# refit and re-evaluate every jurisdiction's deployed model (reproduces exp83_results.json exactly)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown; try other volumes or a newer rate
python3 experiments/cost_share_replicate.py --state PA
python3 experiments/cost_share_replicate.py --state PA --R 0.0172
# score a month of cases with the packaged Pennsylvania model
python3 deliverables/state_rankers/score_cases.py --state PA --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: Pennsylvania uses variant C_ctx, own rows ×10) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Flag cards:** exp65 and exp74.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (`STATUS`, `AMTERR`, `ELEMENT1`, `NATURE1`; state code 42).
