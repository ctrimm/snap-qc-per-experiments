# Finding SNAP Payment Errors Faster in New York

**October 23, 2026 · State brief · Cory Trimm**

## Summary

New York's FY2025 payment error rate was 13.18%. Under the H.R. 1 cost-sharing rules that is the top bracket: from FY2028 the state would pay 15% of its SNAP benefit costs, about **$1.08 billion a year**. This brief shows what a case-ranking tool, built and tested on New York's own federal QC records, could do about that.

- **It finds over four times the error dollars of random review.** Reviewers working the top 20% of the tool's queue would find 4.2 times the error dollars of a random selection, about **$234 per review hour against $56**. The top 10% finds 7.0 times, the highest top-10% result of our six pilot states.
- **It holds up over time.** Trained on 2020–22 and tested on 2023–24, it kept a 4.1× edge. Expected error dollars for the top of the queue landed within 6% of actual.
- **It's fair by design.** Ranking purely by dollars would under-review elderly households. A floor brings their share into proportion for about 6% of the gain (4.2× → 3.9×).
- **Cost share falls a bracket in the central scenario.** Reviewing 2% of cases a month in the tool's order brings the rate to about 8.2%. That drops New York from the 15% share to 10%, avoiding about **$360 million a year**. Reviewing 3% a month brings it under 6%, avoiding the full $1.08 billion. Random reviews of the same volume leave New York at 15% in every scenario.
- **Effort:** about 32,500 reviews a month, roughly 116 reviewer FTEs, in the central scenario.

**Recommendation:** a three-month shadow pilot. New York's errors are mostly about changes in income and circumstances not caught in time, so the pilot should test whether working the top of the queue each month catches them sooner.

## New York's errors

Federal QC public-use files, FY2020–2024: 3,257 reviewed New York cases. Shares are of cases with any error found, including small ones, and are unweighted:

| | New York | National |
|---|---|---|
| Reviewed cases with an error found | 36.7% | 37.9% |
| Error dollars that are underpayments | 28% | 28% |
| Largest share of error dollars | Wages and salaries 39% | Wages and salaries 37% |
| Next largest | Shelter deduction 10.5%, household composition 9.6%, Social Security 8.1% | Shelter deduction 16% |
| Most frequent error | Shelter deduction, 27% of error cases | Shelter deduction, 31% |
| Errors coded as reporting or timing issues (nature code 97) | **63%** | 42% |
| Arithmetic errors | 0.8% | 1.3% |

**New York's distinctive problem is timing.** Nearly two-thirds of its errors carry the reporting and timing code, half again the national share. The facts changed, usually income or household members, and the case wasn't updated in time.

**Its dollars are spread across sources.** Wages carry the most error dollars. Social Security, unemployment benefits and household composition each carry more than their national share.

**Implication for a pilot:** a monthly ranked review fits this pattern. It looks at active cases every month, so it can catch changes between recertifications.

## What the tool does

Each month the tool scores every active case using only information the agency already has before any review:
- reported income and earnings;
- deductions, housing and utility costs;
- household size;
- the benefit issued and the household's maximum allotment.

It estimates the chance the case has an error and how many dollars the error would be. It multiplies them to get expected error dollars, and orders the review queue by that number.

New York's model learns from every state's QC cases pooled together, plus inputs that describe New York's benefit levels. It beat a New York-only model on both tests (3.5× → 4.2× on held-out cases, 3.3× → 4.1× on later years).

### Results on cases the model never saw

815 New York cases (25%) were set aside before training:

| Review the top… | Error dollars vs random | Found per review hour (random) | Forecast vs actual |
|---|---|---|---|
| 10% of the queue | **7.0×** | $388 ($56) | 8% under |
| 20% of the queue | **4.2×** | $234 ($56) | 6% under |
| 20%, trained 2020–22, tested 2023–24 | 4.1× | | |
| 20%, with the fairness floor | 3.9× | | |

Reviews are assumed to take 30 minutes. A state can quote "the top fifth of this month's queue likely holds about $X of errors" with a ±15–20% band.

### Fairness

The measure is each household type's share of reviews compared with its share of error dollars, where 1.0 means proportionate:

| Household type | Dollars only | With the floor |
|---|---|---|
| Elderly | 0.62 | 1.20 |
| Disabled | 0.82 | 0.88 |
| Single parent | 1.28 | 0.84 |
| Childless adult | 1.50 | 0.77 |
| Married with children | 2.57 | 1.47 |

The floor costs about 6% of the lift. We recommend it on by default.

### Underpayments

28% of New York's error dollars are households paid too little. A second ranker trained on underpayments finds 4.1 times the underpayment dollars of random review, against 2.4 times for the main ranker. These figures come from the earlier New York-only models (exp79).

### Flag cards for reviewers

Each flagged case can come with a short card saying why it was flagged and which parts of the case to check first. In New York the card's top three "check first" items include the real error for **86%** of flagged errors. Its "N in 10" odds were recalibrated so they mean what they say.

## FY2028 cost share

H.R. 1 sets the state share by payment error rate: 0% under 6%, 5% at 6–8%, 10% at 8–10%, and 15% at 10% or more. We modelled reviews as removing a share of the caseload's error dollars each month (cases reviewed × the tool's lift × the share fixed), with errors otherwise lasting until recertification. All assumptions were fixed before results existed (exp69, exp93).

| Scenario | Reviewed a month | Rate after | State share | Avoided a year | Random reviews, same volume |
|---|---|---|---|---|---|
| Today (FY2025 rate) | — | 13.18% | 15% | — | — |
| Low | 1% (16,266 reviews, 58 FTEs) | 12.04% | 15% | $0 | 12.87%, $0 |
| **Central** | **2% (32,531 reviews, 116 FTEs)** | **8.19%** | **10%** | **$360M** | 12.03%, $0 |
| High | 3% (48,796 reviews, 174 FTEs) | 5.56% | 0% | $1,081M | 10.84%, $0 |

**The three thresholds.** With the central scenario's other assumptions, New York crosses:
- 10% at about **1.0%** of cases reviewed a month;
- 8% at about **2.1%**;
- 6% at about **3.9%**.

Each bracket is worth about $360 million a year.

**What drives the range:** how many cases are reviewed and how long an error would otherwise have lasted matter more than the tool's accuracy. Both are worth measuring in a pilot.

These figures show the size of the opportunity, not a forecast. The model leaves out:
- timing relative to the federal sample month;
- procedural errors outside the public file;
- behavior changes;
- the cost of reviews.

## A pilot in New York

1. **Month 0:** map the case-management fields to the tool's inputs (14 fields plus the maximum allotment) and score a current month's active cases. The model runs on a laptop.
2. **Months 1–3, shadow:** reviewers work a sample from the top of the queue alongside current case selection, with the fairness floor on, flag cards attached and about 10% of reviews on randomly chosen cases. Record the dollars found, the error type, and when the underlying change happened.
3. **Read-out:**
   - dollars found against the forecast;
   - dollars per review hour against current selection;
   - how long found errors had lasted, the key driver of the cost-share estimate, and especially telling for timing errors;
   - reviewer ratings of the flag cards.
4. **Refresh yearly** on the new federal QC sample plus the pilot's findings, keeping a random slice of reviews to watch for blind spots.

## Limitations

- **Public data only.** The model was built from federal public-use files. New York's own case records, including report dates, would likely do better for timing errors after a short refit.
- **Scenarios, not forecasts.** See the cost-share caveats above.
- **The policy library is thin for New York.** It holds 6 New York documents (OTDA administrative directives and GIS messages), against 491 for California. Rule citations and policy lookups would need the SNAP Source Book and current directives added first.
- **The tool prioritizes; it doesn't decide.** Every determination stays with a reviewer.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), in `../snap-qc-data/raw/qcfy20XX_csv/`. Python 3 with numpy, joblib and scikit-learn 1.9.1. For other states, see the companion *State Replication Guide*.

```bash
# New York's numbers as measured (top-10/20% lift, $/hour, forecast, fairness)
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_results.json'))['NY'], indent=1))"
# refit and re-evaluate every jurisdiction's deployed model (reproduces exp83_results.json exactly)
python3 experiments/exp83_context_models_full_eval.py --workers 8
# cost share, every step shown; the three thresholds
python3 experiments/cost_share_replicate.py --state NY
for r in 0.0106 0.0215 0.0395; do python3 experiments/cost_share_replicate.py --state NY --R $r | grep central; done
# score a month of cases with the packaged New York model
python3 deliverables/state_rankers/score_cases.py --state NY --input cases.csv --output ranked.csv --id-col CASE_ID
```

**Sources:**
- **Model and held-out cases:** exp82 (adoption: New York uses variant B_ctx, pooled with state context) and exp83 (evaluation). The held-out cases are fixed in `experiments/exp68_holdouts.json`.
- **Fairness:** exp72 and exp83.
- **Underpayments:** exp79.
- **Flag cards:** exp65 and exp74.
- **Cost share:** exp93; method in `COST-SHARE-REPLICATE.md`.
- **Error pattern:** computed from the five QC files (state code 36).
