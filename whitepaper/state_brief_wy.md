# Finding SNAP Payment Errors Faster in Wyoming

**October 23, 2026 · State brief · Cory Trimm**

## Summary

Wyoming's FY2025 payment error rate was 3.96%, the third lowest of 53 jurisdictions (after South Dakota and Idaho) and below the 6% line where H.R. 1 cost sharing begins. Wyoming owes nothing under FY2028 rules at that rate. So for Wyoming, a case-ranking tool is not about avoiding a bill. It's about four other things:
- staying below 6%;
- finding households that are being underpaid;
- using a small review staff well;
- showing that the approach works for a small state.

- **A tool that works despite a small sample.** Wyoming has only about 1,200 federal QC cases from five years, too few to train a good model on its own: a Wyoming-only model found 1.7 times the error dollars of random review. A model that learns from every state's cases, plus Wyoming's benefit levels, finds **3.8 times** (top 20% of the queue), a little below the 53-jurisdiction median of 4.0×. The top 10% finds 5.3 times.
- **Wyoming's errors run both ways.** 54% of Wyoming's error dollars are underpayments, nearly twice the national share (28%). A review program in Wyoming finds households being shorted about as often as overpayments.
- **Medical deductions stand out.** They account for 12% of Wyoming's error dollars and 17% of its errors, about four times the national shares.
- **It's cheap insurance.** If Wyoming's rate rose to 6.5% it would owe about $3 million a year, and at 8.5% about $6 million. In the model, one reviewer FTE working the top of the queue (about 270 reviews a month) brings either back under 6%.
- **The caveats are larger here.** The later-years test (train 2020–22, test 2023–24) gave 2.9×, the lowest of the 53 jurisdictions, and the fairness floor costs more than in large states (3.8× → 3.3×).

**Recommendation:** a light pilot. Score the caseload quarterly, have existing reviewers work the top of the queue plus the underpayment queue, and use the results to decide whether a monthly ranking is worth it.

## Wyoming's errors

Federal QC public-use files, FY2020–2024: 1,191 reviewed Wyoming cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | Wyoming | National |
|---|---|---|
| Reviewed cases with an error found | 34.0% | 37.9% |
| Error dollars that are underpayments | **54%** | 28% |
| Error cases: over / under | 202 / 203 | 61% / 39% |
| Largest share of error dollars | Wages and salaries 28% | Wages and salaries 37% |
| Next largest | Shelter deduction 18%, **medical deductions 12%** | Shelter deduction 16%, medical 3% |
| Most frequent errors | Shelter 25%, wages 24%, **medical 17%** of error cases | Shelter 31%, wages 24%, medical 4% |
| Errors coded as reporting or timing issues (nature code 97) | 57% | 42% |

**Wyoming's errors are evenly split between over- and underpayments,** which is unusual. Medical expense deductions, which apply to elderly and disabled household members, matter far more than elsewhere. That points to verifying and updating medical expenses as a specific area to review.

**The numbers are small.** Five years of Wyoming QC data hold about 400 error cases. Patterns here are less certain than in large states.

## What the tool does

Each month (or quarter) the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the benefit issued and the household's maximum allotment.

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

**Why pooling matters for Wyoming:** a model trained on Wyoming's cases alone found 1.7× on held-out cases and 1.5× on later years. Learning from every state's cases, plus two inputs that describe Wyoming's benefit levels, lifted that to 3.8× and 2.9×. Errors follow similar patterns across states; the state inputs let the model adjust to Wyoming's benefit amounts.

### Results on cases the model never saw

297 Wyoming cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual |
|---|---|---|---|
| 10% of the queue | **5.3×** | $146 ($27) | 4% over |
| 20% of the queue | **3.8×** | $105 ($28) | 10% under |
| 20%, trained 2020–22, tested 2023–24 | 2.9× (lowest of 53) | | |
| 20%, with the fairness floor | 3.3× | | |

Reviews are assumed to take 30 minutes. With so few held-out cases, these figures carry wider uncertainty than in large states. A pilot should check them on Wyoming's own reviews.

### Fairness

The measure is each household type's share of reviews compared with its share of error dollars, where 1.0 means proportionate:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | **0.45** | 1.35 |
| Disabled | **0.51** | 0.83 |
| Single parent | 1.09 | 1.09 |
| Childless adult | 1.28 | 0.86 |

**Elderly and disabled households need the floor most.** Ranking purely by dollars would review them at half their share of errors, the strongest under-review among the three states in these briefs. That matters doubly in Wyoming, where medical-deduction errors (which mainly affect these households) are common.

**The floor costs more here:** about 13% of the lift (3.8× → 3.3×), against 3–6% in Pennsylvania and New York. We still recommend it on by default.

### Underpayments

With 54% of error dollars being underpayments, the underpayment ranker is especially relevant. Trained on underpayments, it finds 2.8 times the underpayment dollars of random review, against 1.9 times for the total-dollar ranker. These figures come from the earlier Wyoming-only models (exp79); a pooled version would likely do better.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. For FY2028 a state may use its FY2025 or FY2026 rate; later years use the rate from three years earlier. At 3.96%, Wyoming pays nothing.

**How much a higher rate would cost:** Wyoming's SNAP benefits are about $60 million a year. Assumptions are the same as the national model (exp69/exp93): 2% of cases reviewed a month, 80% of found errors fixed, errors otherwise lasting 6 months.

| If Wyoming's rate were… | Share owed | Cost a year | Rate after ranked reviews (≈270 a month, 1 FTE) | Cost after |
|---|---|---|---|---|
| 3.96% (FY2025) | 0% | $0 | 2.68% | $0 |
| 6.5% | 5% | about $3M | 4.40% | $0 |
| 8.5% | 10% | about $6M | 5.76% | $0 |

**Ranked vs random:** random reviews of the same volume would bring 6.5% under 6% too (5.93%), but not 8.5% (7.76%, still 5%). The ranking matters more the further the rate rises.

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in Wyoming

1. **Quarter 0:** map the case-management fields to the tool's inputs (14 fields plus the maximum allotment) and score the active caseload. The model runs on a laptop.
2. **Quarters 1–2:**
   - **Queues:** existing reviewers work the top of two queues, total error dollars and underpayments, with the fairness floor on.
   - **Random slice:** about 10% of reviews on randomly chosen cases.
   - **What to record:** dollars found, direction, and the error element (especially medical deductions).
3. **Read-out:**
   - dollars found against the forecast;
   - underpayments found and corrected;
   - how long found errors had lasted;
   - whether a monthly ranking would pay for itself.
4. **Refresh yearly** on the new federal QC sample, which matters more in a small state where each year adds relatively many cases.

## Limitations

- **Small sample.** About 1,200 QC cases and 300 held-out cases. Pooling helps, but the later-years result (2.9×) is the lowest nationally, and forecasts should be checked against Wyoming's own reviews before they are quoted.
- **Public data only.** Wyoming's own case records would likely do better after a short refit.
- **The policy library barely covers Wyoming.** It holds 1 Wyoming SNAP document (the FY2026 SNAP Employment and Training state plan). Rule citations would need Wyoming's SNAP manual added first.
- **Flag-card coverage wasn't measured for Wyoming.** It was measured in Pennsylvania and New York (86–88%) and tested at scale in Idaho, Utah and South Dakota.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# Wyoming's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_results.json'))['WY'], indent=1))"
# the small-jurisdiction pooling comparison (state-only vs pooled, both readouts)
python3 -c "import json; print(json.load(open('experiments/exp80_results.json'))['WY'])"
# refit and re-evaluate every jurisdiction's deployed model (reproduces exp83_results.json exactly)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share at the FY2025 rate and at hypothetical higher rates
python3 experiments/cost_share_replicate.py --state WY
python3 experiments/cost_share_replicate.py --state WY --per 6.5
python3 experiments/cost_share_replicate.py --state WY --per 8.5
# score cases with the packaged Wyoming model
python3 deliverables/state_rankers/score_cases.py --state WY --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp80 (small-jurisdiction context pooling; Wyoming adopts variant B_ctx) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **State-only baseline:** exp68.
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 56).
