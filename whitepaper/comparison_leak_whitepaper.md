# An Independent Comparison, and the Leak It Found

**October 26, 2026 · Whitepaper · Cory Trimm**

## Summary

In October we compared our SNAP error-ranking tool with an independent project on the same problem: [giannella/snap_qc](https://github.com/giannella/snap_qc), which turns the same federal quality-control (QC) data into ranked lists of if-then rules for each state. The comparison did what independent checks are for. It found a serious flaw in our own work, and it showed that the corrected tool is still useful.

1. **Our published ranker figures were inflated by a data leak.**
   - **The fields:** in the federal QC file, the "reported" income, deduction and household-size fields are what the **QC reviewer recorded**, which for an error case are the corrected facts.
   - **The leak:** our models used those fields next to the benefit the agency actually issued. A model that sees both can spot an error by noticing they disagree, something no state can do before a review.
   - **How it showed:** on giannella's test, our model flagged errors with 100% precision, which no honest model achieves when only 12% of cases have an error.
2. **Corrected, the tool still works, at a lower level.** Without the issued benefit:

   | Median of 53 | Published | Corrected |
   |---|---|---|
   | Top 20% of the review queue vs random | 4.0× | **2.7×** |
   | Top 10% vs random | 6.4× | **3.3×** |
   | FY2028 cost share avoided, central scenario | $6.05 billion | **$3.42 billion** |

3. **On the same test, the corrected tool beats giannella's lists.** Trained on FY2022–23 and tested on each state's FY2024 cases, under their error definition, paired over 49 states at a 10% review budget:
   - **Dollars:** it finds about **$3.5 billion a year** in error dollars against their $2.2 billion, and more in 39 of 49 states.
   - **Precision:** a flagged case has an error more often (0.32 against 0.30 at 10%; 0.40 against 0.32 at 5%).
   - **Their advantage:** their lists are interpretable rules a state can read and edit; ours is a score.
4. **The comparison confirmed some of our findings and changed others.**
   - **Agreed:** pooling across states beats state-only models; the public file misses part of each state's errors; and training numbers overstate real performance.
   - **Changed:** the fairness floor that protects older and disabled households turned out to cost about 10% of the tool's gain in the median state, not 1%.
   - **Stronger:** the finding that dollar ranking under-reviews older households got stronger once the leak was removed.

Every paper, brief, guide and dashboard from this project has been corrected (October 26). The code now uses the leak-free inputs by default.

## What we did, in plain terms

| Step | What we did | What we found |
|---|---|---|
| Compare findings | Read giannella/snap_qc's documentation and set their claims beside ours | Agreement on pooling, data visibility and testing; a different definition of "error" |
| Same test, both tools | Trained our model their way and scored it on their FY2024 test, by their rules | Our model looked perfect: every flagged case was an error |
| Find out why | Checked what the input fields hold, in the QC documentation and in the data | The "reported" fields are the QC reviewer's corrected values |
| Remove the leak | Took the issued benefit out of the model's inputs and reran everything | About two-thirds of the published gain held up (2.7× against 4.0×) |
| Compare again | Leak-free model on their test | Ours finds more error dollars in 39 of 49 states, at slightly higher precision |
| Correct everything | Rebuilt the models, papers, briefs and dashboard; made leak-free the default | Corrected October 26 |

## The two projects

| | giannella/snap_qc | This project |
|---|---|---|
| What a state gets | A ranked list of if-then rules per state, in an Excel workbook | A scoring model per state that ranks cases by expected error dollars |
| How cases are ranked | By how often a rule's flagged cases have an error (precision), with a statistical safety margin | By expected error dollars (chance of an error × likely dollars) |
| What counts as an error | A payment off by more than the federal tolerance ($56 in FY2024), the official definition: about 12% of cases | Any error found by the reviewer: about 38% of cases |
| Data | FY2017–19 and FY2022–24; dollars converted to 2026 prices | FY2020–24; nominal dollars |
| Benefit input | Benefit recomputed from the reported facts | The issued benefit (until October 26) |

That last row is the whole story. Their benefit input agrees with the reviewer's facts and can't reveal an error. Ours, the amount actually issued, disagreed with those facts exactly when there was an error.

## How the leak was found

**The comparison test.** giannella publishes, per state, how its lists did a year ahead: mined on FY2022–23, scored on FY2024. We trained our model the same way, applied their exclusions and their error definition, and matched their test frame exactly (a median of 847 cases per state, the same 12.4% error rate).

| Median of 49 states, FY2024 | Our published model | giannella's lists |
|---|---|---|
| Precision at a 5% review budget | **1.00** | 0.32 |
| Share of error dollars caught at a 5% budget | 0.59 | 0.14 |

**Why that's impossible.** A 5% budget flags about 44 cases in the median state, and errors occur in 12% of cases. Flagging only errors, in every state, means the model can see the answer.

**What the fields hold.** The QC technical documentation says the raw file "is generated from the monthly reviews"; QC reviewers "gather financial and demographic information from the sampled unit's case file, reinterview the participants, and then determine whether the SNAP unit received the correct SNAP benefit amount." We checked the 5,809 FY2024 cases with an over-threshold error:

| Field our models used | Equals the reviewer's calculated value |
|---|---|
| Reported gross income (`RAWGROSS`) | 98.9% |
| Earned-income deduction (`RAWERND`) | 98.1% |
| Certified household size (`CERTHHSZ`) | 100% |
| Shelter deduction (`SHELDED`) | 91.9% |
| Net income (`RAWNET`) | 86.0% |

Applying the benefit formula to the reported net income reproduces the **reviewer's** corrected benefit in 79.8% of these cases, and the benefit the agency **issued** in 0.8%.

**Why it was missed.** In early October we removed four fields that are explicitly the reviewer's (`FSEARN` and others) and called the rest "agency-side". That check looked at clean cases, where the agency's and the reviewer's values are the same. It never looked at error cases, the only place the difference shows.

## The corrected tool

We removed the two inputs built from the issued benefit and reran everything with the same data, splits, seeds and settings (experiments 106 and 107). The rerun matched the published results exactly when the two inputs were put back, so the change comes from those inputs alone.

| Median of 53 jurisdictions | Published | Corrected |
|---|---|---|
| Top 20% of the queue vs random review | 3.97× | **2.70×** (range 1.98–3.67) |
| Top 10% | 6.38× | **3.31×** |
| Trained 2020–22, tested 2023–24 | 3.80× | **2.61×** |
| Dollar forecast within 20% of actual | 52 of 53 | 43 of 53 |
| Older households' review ratio, ranking by dollars (1.0 = in proportion to risk) | 0.61 | **0.33** |
| Cost of the fairness floor (median state) | about 1.5% of the gain | **about 10%** |
| Underpayment ranker vs main ranker (underpayment dollars) | 3.4× vs 1.5× | **1.8× vs 1.5×** |
| FY2028 cost share avoided: central (low–high) | $6.05B ($0.39–10.06B) | **$3.42B ($0.21–6.63B)** |

**What held up:**
- **The tool finds more error dollars than random review in every state:** at least 2.0 times in 52 of 53.
- **Ranking by dollars under-reviews older households.** It does so even more clearly without the leak, under either error definition.
- **The fairness floor fixes that.**

**What didn't:**
- **The headline numbers.** About a third of the published gain was the leak.
- **The floor's cost.** It is no longer nearly free.
- **The separate underpayment ranker.** It is now only slightly better than the main one.

## The corrected tool against giannella's lists

| Median of 49 states, FY2024, their error definition | Ours (corrected) | giannella | Ours higher in |
|---|---|---|---|
| Precision, 5% budget | 0.40 | 0.32 | 33 of 49 |
| Precision, 10% budget | 0.32 | 0.30 | 33 of 49 |
| Share of error dollars caught, 5% budget | 0.26 | 0.14 | 39 of 49 |
| Share of error dollars caught, 10% budget | 0.41 | 0.27 | 39 of 49 |

**In dollars, summed over the 49 states:**

| Per year | giannella | Ours |
|---|---|---|
| Over-threshold error dollars | $8.31B | $8.31B |
| Found at a 5% review budget | $1.18B | $2.28B |
| Found at a 10% review budget | $2.21B | $3.53B |
| FY2028 cost share avoided (central scenario, each tool's own lift) | $2.83B | $4.88B |

**Why some states show double the cost share avoided.** The rules set a state's share in steps (0%, 5%, 10% or 15% of benefits by error-rate band), so cost share avoided jumps by whole steps. Where the two tools' error rates after review land in different bands, the totals diverge sharply:
- **Exactly double:** in 5 states our lift drops the rate two bands and theirs one. California, for example, goes 15% → 5% ($1.19B) against 15% → 10% ($596M).
- **Ours against nothing:** in 7 more states ours crosses a band line and theirs doesn't (New York, Florida, Illinois and others).
- **The other way:** in Kansas, theirs crosses and ours doesn't.
- **Everywhere else:** in the other 36 states both land in the same band and avoid the same amount.

The underlying difference is about 1.6 times the error dollars found; the band steps magnify it. A state-level "double" or "$0" can flip with a small change in lift, so read the dollars found as the steadier comparison.

**What their lists offer that ours doesn't:**
- **Readable rules:** they are if-then rules a reviewer can read, question and edit.
- **Workbook delivery:** they ship as a workbook that recomputes when a state pastes its own cases.
- **Inflation adjustment:** they convert dollars to current prices, which they found helps lists applied three years after their training data. We haven't tested that.

## Where the two projects agree, and where the definition matters

**Agreements:**
- **Pooling:** learning from every state's cases beats a state's own cases alone.
- **What the public data misses:** it excludes ineligible cases, so states see roughly 43–91% of their own errors in it. Their figure is about 71% nationally; ours is that published error rates run 2–3 points above what the file implies.
- **Held-out testing:** training numbers overstate real performance; judge only on held-out data, and re-test on a second period.

**The definition of an error changes the older-households picture:**

| FY2022–24 | Elderly or disabled households | Other households |
|---|---|---|
| Any error (our definition) | 45.4% | 33.0% |
| Error over the tolerance threshold (official, theirs) | 12.6% | 17.2% |

**Older and disabled households have more errors, but smaller ones.** Under the official definition they have fewer.
- **giannella's result:** their precision-ranked lists catch more of these households' errors.
- **Ours:** a dollar-ranked tool reviews them less than random selection would under either definition (corrected: 0.33 of their share of any-error risk; 0.50 under the official definition).

The fairness concern belongs to dollar ranking specifically, and the floor fixes it.

## What changed, and what we still need to check

**Changed (October 26):**
- **Models:** all 53 state models were rebuilt without the issued benefit.
- **Documents:** every paper, state brief, the replication guides and the state-map dashboard now carry the corrected figures and a correction note.
- **Code:** the leak-free inputs are the default (`SNAPQC_FEATURES=leakfree`); the old inputs remain only to reproduce the published results.

**Not yet rechecked.** These used models with the same reviewer-recorded fields and may also be inflated:
1. the flag cards' "check first" coverage (86–88%);
2. the flag cards' odds calibration;
3. the retraining simulation (a ranker trained only on its own flags loses about 15% in four years);
4. the early household-type tests.

They are marked in the papers, and they are the next experiment.

**A limit no public-data work can remove.** For error cases the reported facts are still the reviewer's corrected values, while a state's tool would see its own uncorrected values. Both projects share this. The only real test of either tool is a pilot on a state's own pre-review case records.

## The lesson

Before using any field from the QC file, ask: would a state agency have this value, as is, before a QC review? The fields that fail that test:
- the `FS*` fields;
- the reported `RAW*` fields, except the issued benefit;
- the error amount and finding;
- the error codes.

Combining a value the agency had with one only the reviewer had is the specific trap. We found it because someone else built the same thing differently and published their numbers. That is an argument for publishing, and for comparing.

## Technical reproduction

Code: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments). Their repo: [github.com/giannella/snap_qc](https://github.com/giannella/snap_qc) at `eedb3f5` (v2.7.0), cloned beside ours as `giannella-snap_qc`. Data: FY2020–2024 QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles).

```bash
# the comparison: B0 (reproduces exp83), B1/B2 on their FY2024 test; then the leak-free re-run and fairness by definition
SNAPQC_FEATURES=legacy python3 experiments/exp106_giannella_comparison.py --workers 8
python3 experiments/exp106_leakfree.py --workers 8
# the rebuild (leak-free is the default): evaluation, cost share, underpayments, later years, packaged models
python3 experiments/exp83_context_models_full_eval.py --workers 8
python3 experiments/exp93_cost_share_current_models.py --workers 6
python3 experiments/exp79_underpayment_ranker.py --workers 8
python3 experiments/exp107_timesplit.py --workers 8
python3 experiments/exp107_package.py --workers 8
# the dollar comparison (writes the table below and the vault note)
python3 whitepaper/giannella_dollar_comparison.py
```

**The leak check itself, on the FY2024 file:** compare `RAWGROSS` with `FSGRINC`, `RAWNET` with `FSNETINC`, `SHELDED` with `FSSLTDED` and `CERTHHSZ` with `FSUSIZE` on cases with STATUS 2 or 3. The reported field equals the reviewer's calculated value in 86–100% of them.

**Write-ups:**
- `experiments/exp106_giannella_comparison.md` (pre-registration, two amendments, results);
- `experiments/exp107_leakfree_rebuild.md`;
- the README section "Feature set: leak-free by default".

## Appendix: the two tools, state by state

How to read the table:
- **Test:** each tool trained or mined on FY2022–23 and scored on the state's FY2024 QC cases, under giannella's error definition (over the $56 tolerance).
- **Error dollars a year:** FY2024 cases weighted to the caseload, times 12.
- **Found:** each tool's share of error dollars caught at the budget, times that total.
- **Dollar lift:** dollars caught at 10% ÷ 0.10.
- **Cost share avoided:** the central scenario (2% of cases reviewed a month, 80% of found errors fixed, errors lasting 6 months) with each tool's own lift.

These are scenario estimates on one test year, not forecasts.

<!-- DOLLAR-TABLE:START -->
| State | Over-threshold error $ a year | Found at 5%: giannella | Found at 5%: ours | Found at 10%: giannella | Found at 10%: ours | 10% dollar lift: giannella / ours | FY2025 rate | FY2028 cost share avoided: giannella | ours |
|---|---|---|---|---|---|---|---|---|---|
| Alabama (AL) | $127.9M | $16.7M | $36.1M | $32.3M | $50.6M | 2.52× / 3.96× | 9.52% | $85.4M | $85.4M |
| Arizona (AZ) | $162.1M | $18.7M | $67.3M | $45.1M | $93.3M | 2.78× / 5.75× | 10.80% | $97.8M | $195.5M |
| Arkansas (AR) | $29.6M | $4.9M | $5.2M | $9.0M | $10.0M | 3.04× / 3.39× | 8.81% | $24.1M | $24.1M |
| California (CA) | $1,197.5M | $261.8M | $356.8M | $430.1M | $496.7M | 3.59× / 4.15× | 10.93% | $595.8M | $1,191.7M |
| Colorado (CO) | $123.8M | $16.7M | $28.3M | $27.5M | $47.9M | 2.22× / 3.87× | 10.09% | $63.3M | $126.5M |
| Connecticut (CT) | $88.1M | $10.7M | $24.2M | $21.5M | $39.2M | 2.44× / 4.45× | 9.08% | $44.8M | $44.8M |
| Delaware (DE) | $19.7M | $3.0M | $5.2M | $4.9M | $8.5M | 2.49× / 4.30× | 16.00% | $0.0M | $0.0M |
| District of Columbia (DC) | $47.6M | $6.1M | $11.7M | $10.1M | $20.2M | 2.12× / 4.23× | 18.66% | $0.0M | $0.0M |
| Florida (FL) | $665.1M | $97.6M | $116.2M | $151.8M | $220.6M | 2.28× / 3.32× | 12.97% | $0.0M | $324.7M |
| Georgia (GA) | $351.3M | $33.8M | $120.7M | $79.9M | $179.5M | 2.27× / 5.11× | 15.21% | $0.0M | $0.0M |
| Idaho (ID) | $21.5M | $5.4M | $7.5M | $9.7M | $9.7M | 4.52× / 4.49× | 3.85% | $0.0M | $0.0M |
| Illinois (IL) | $474.8M | $53.6M | $151.1M | $85.7M | $264.3M | 1.80× / 5.57× | 14.67% | $0.0M | $221.2M |
| Indiana (IN) | $103.8M | $17.5M | $27.0M | $31.4M | $48.0M | 3.02× / 4.63× | 9.77% | $70.0M | $70.0M |
| Iowa (IA) | $28.7M | $6.0M | $10.9M | $10.4M | $14.5M | 3.60× / 5.06× | 5.34% | $0.0M | $0.0M |
| Kansas (KS) | $20.9M | $4.1M | $1.1M | $5.4M | $3.6M | 2.61× / 1.75× | 9.44% | $18.8M | $0.0M |
| Kentucky (KY) | $84.2M | $27.5M | $22.3M | $40.1M | $37.2M | 4.75× / 4.42× | 4.70% | $0.0M | $0.0M |
| Louisiana (LA) | $145.1M | $22.5M | $42.6M | $40.4M | $63.4M | 2.78× / 4.36× | 8.14% | $92.8M | $185.6M |
| Maine (ME) | $27.9M | $6.9M | $4.8M | $9.2M | $8.1M | 3.31× / 2.89× | 10.81% | $17.4M | $17.4M |
| Maryland (MD) | $154.7M | $15.6M | $29.2M | $35.9M | $40.3M | 2.32× / 2.61× | 13.08% | $0.0M | $0.0M |
| Massachusetts (MA) | $293.2M | $39.6M | $84.3M | $78.2M | $136.1M | 2.67× / 4.64× | 12.49% | $128.9M | $128.9M |
| Michigan (MI) | $324.2M | $42.5M | $94.8M | $88.6M | $141.4M | 2.73× / 4.36× | 9.89% | $149.6M | $149.6M |
| Minnesota (MN) | $96.3M | $18.0M | $20.4M | $29.0M | $30.2M | 3.01× / 3.13× | 12.58% | $43.1M | $43.1M |
| Mississippi (MS) | $60.3M | $9.2M | $14.9M | $17.4M | $21.3M | 2.89× / 3.53× | 9.51% | $39.7M | $39.7M |
| Missouri (MO) | $75.8M | $13.1M | $9.2M | $26.9M | $16.2M | 3.55× / 2.14× | 8.67% | $72.6M | $72.6M |
| Montana (MT) | $12.7M | $2.7M | $2.3M | $3.3M | $2.8M | 2.60× / 2.19× | 8.86% | $8.0M | $8.0M |
| Nebraska (NE) | $16.4M | $1.8M | $5.0M | $3.0M | $7.4M | 1.84× / 4.50× | 5.90% | $0.0M | $0.0M |
| Nevada (NV) | $90.1M | $20.3M | $30.1M | $29.5M | $40.2M | 3.28× / 4.46× | 6.22% | $50.8M | $50.8M |
| New Hampshire (NH) | $11.6M | $2.2M | $2.1M | $3.5M | $3.2M | 3.00× / 2.79× | 8.85% | $7.6M | $7.6M |
| New Jersey (NJ) | $113.7M | $12.5M | $36.0M | $36.2M | $45.4M | 3.18× / 4.00× | 6.86% | $92.2M | $92.2M |
| New Mexico (NM) | $102.1M | $15.4M | $15.9M | $25.6M | $35.3M | 2.51× / 3.46× | 16.81% | $0.0M | $0.0M |
| New York (NY) | $677.5M | $36.0M | $261.5M | $136.7M | $381.1M | 2.02× / 5.62× | 13.18% | $0.0M | $360.3M |
| North Carolina (NC) | $271.4M | $31.6M | $69.7M | $60.0M | $95.7M | 2.21× / 3.53× | 7.36% | $0.0M | $140.7M |
| North Dakota (ND) | $7.5M | $0.9M | $2.8M | $1.6M | $3.1M | 2.14× / 4.10× | 9.89% | $0.0M | $5.4M |
| Ohio (OH) | $173.5M | $47.3M | $33.4M | $67.6M | $57.6M | 3.90× / 3.32× | 6.76% | $151.7M | $151.7M |
| Oklahoma (OK) | $156.7M | $17.2M | $49.8M | $33.8M | $71.2M | 2.16× / 4.54× | 11.04% | $75.0M | $150.0M |
| Oregon (OR) | $191.4M | $22.0M | $47.5M | $62.0M | $84.6M | 3.24× / 4.42× | 14.14% | $0.0M | $78.6M |
| Pennsylvania (PA) | $399.4M | $56.1M | $100.2M | $131.1M | $189.7M | 3.28× / 4.75× | 9.21% | $208.8M | $208.8M |
| Rhode Island (RI) | $43.5M | $5.0M | $11.8M | $9.3M | $16.5M | 2.13× / 3.80× | 12.42% | $0.0M | $16.9M |
| South Carolina (SC) | $95.9M | $12.9M | $28.8M | $26.2M | $40.6M | 2.73× / 4.24× | 8.80% | $62.8M | $62.8M |
| South Dakota (SD) | $7.2M | $1.5M | $0.5M | $1.9M | $2.8M | 2.62× / 3.86× | 2.47% | $0.0M | $0.0M |
| Tennessee (TN) | $81.0M | $9.8M | $11.8M | $18.9M | $29.3M | 2.34× / 3.62× | 9.44% | $76.4M | $76.4M |
| Texas (TX) | $670.0M | $69.9M | $154.2M | $123.6M | $234.9M | 1.84× / 3.50× | 9.34% | $342.6M | $342.6M |
| Utah (UT) | $15.4M | $2.1M | $1.5M | $3.5M | $5.1M | 2.25× / 3.30× | 5.54% | $0.0M | $0.0M |
| Vermont (VT) | $8.7M | $1.9M | $1.9M | $3.2M | $3.0M | 3.66× / 3.46× | 5.38% | $0.0M | $0.0M |
| Virginia (VA) | $155.0M | $26.9M | $28.7M | $41.1M | $52.2M | 2.65× / 3.37× | 12.32% | $85.7M | $85.7M |
| Washington (WA) | $138.8M | $20.3M | $53.9M | $37.4M | $64.6M | 2.70× / 4.66× | 6.98% | $95.1M | $95.1M |
| West Virginia (WV) | $56.3M | $8.0M | $15.8M | $15.2M | $24.8M | 2.70× / 4.41× | 6.69% | $25.2M | $25.2M |
| Wisconsin (WI) | $88.0M | $4.6M | $26.6M | $11.8M | $38.2M | 1.35× / 4.33× | 5.72% | $0.0M | $0.0M |
| Wyoming (WY) | $4.4M | $0.4M | $0.7M | $1.0M | $0.9M | 2.21× / 2.14× | 3.96% | $0.0M | $0.0M |
| **Total, 49 states** | **$8.31B** | **$1.18B** | **$2.28B** | **$2.21B** | **$3.53B** | | | **$2.83B** | **$4.88B** |
<!-- DOLLAR-TABLE:END -->
