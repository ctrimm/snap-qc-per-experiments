# An Independent Comparison, and the Leak It Found

**October 26, 2026 · Whitepaper · Cory Trimm**

## TL;DR: giannella/snap_qc and this project

| | giannella/snap_qc | This project |
|---|---|---|
| Question | Which SNAP cases should a state review first? | Same |
| Data | Federal QC public-use files, FY2017–19 and FY2022–24 | Same files, FY2020–24 |
| Inputs | **Rebuilt pre-review values:** starting from the reviewer's values and the error codes, the field in error is shifted until the benefit formula gives the benefit the agency issued | **The reviewer's recorded values;** until October 26 also the issued benefit, which was the leak |
| What counts as an error | Off by more than the federal tolerance ($56 in FY2024), the official definition: about 12% of cases | **The same, since October 26** (experiments 111–112); before that, any error the reviewer found: about 38% |
| Ranked by | Chance that a flagged case has an error, with a 99% safety margin | Expected error dollars |
| What a state gets | Readable if-then rules in an Excel workbook per state | A scoring model per state |
| What our comparison scores | **The rule lists** (the rules a state receives) | **Per-case predictions** (boosted trees' expected error dollars) |
| Older and disabled households | A feature in the rules; precision ranking reaches them | An explicit floor on their share of reviews |
| Dollars | Converted to 2026 prices | As recorded |

**How they are similar:**
- **Same question, same source:** the same public file, and per-state tools learned mostly from national data. Both find national data is the backbone: tuning on one state's cases alone didn't beat their national ordering, and our pooled models beat state-only ones (2.70× against 2.27×, better in 46 of 53, rechecked without the leak).
- **Same discipline:** both judge only on held-out later years and warn that training numbers overstate.
- **Same blind spot in the data:** the public file leaves out ineligible cases, so each state sees only part of its errors (43–91% by giannella's count).

**How they differ:**
- **Inputs, the difference that mattered:** giannella rebuilt the facts a state had before review. We used the reviewer's facts and, until October 26, put the issued benefit beside them. That leak inflated every published ranker figure: the top-20% lift is 2.7×, not the published 4.0×.
- **Ranking:** we now count errors the same way, but they find the cases most likely to have one, and we find the most error dollars. That is why older households fare differently under each.
- **Form:** rules a reviewer can read and edit against a score.
- **What the head-to-head measures:** our per-case predictions against their rule lists, not model against model. giannella reports that its own boosted-tree models give numbers matching ours. The gap below is mostly what is given up by turning predictions into readable rules.

**Head to head, like-for-like** (FY2024, their test, 49 states, 10% budget, both tools on their rebuilt pre-review inputs; experiment 109; our predictions against their rule lists):
- **Dollars:** our tool catches more of the over-tolerance error dollars, about $2.6B a year against $2.2B, and more in 35 of 49 states.
- **Precision:** slightly higher (0.34 against 0.30; higher in 37 of 49).
- **What the reviewer's values were worth:** on the reviewer's corrected values instead, our dollar figures read about 17% higher. The first comparison ($3.5B against $2.2B) was flattered by that.

**What each project gave the other:**
- **What we took from them:** their published numbers exposed our leak, and their rebuild of pre-review values is the better way to use the public file.
- **What we can offer them:** the dollar view, the fairness floor, and the cost-share scenarios.

## Summary

In October we compared our SNAP error-ranking tool with an independent project on the same problem: [giannella/snap_qc](https://github.com/giannella/snap_qc), which turns the same federal quality-control (QC) data into ranked lists of if-then rules for each state. The comparison did what independent checks are for. It found a serious flaw in our own work, and it showed that the corrected tool is still useful.

1. **Our published ranker figures were inflated by a data leak.**
   - **The fields:** in the federal QC file, the "reported" income, deduction and household-size fields are what the **QC reviewer recorded**, which for an error case are the corrected facts.
   - **The leak:** our models used those fields next to the benefit the agency actually issued. A model that sees both can spot an error by noticing they disagree, something no state can do before a review.
   - **How it showed:** on giannella's test, our model flagged errors with 100% precision, which no honest model achieves when only 12% of cases have an error.
2. **Corrected, the tool still works, at a lower level.** Without the issued benefit:

   | Median of 53 | Published | Corrected (leak-free) | Today (also official error definition) |
   |---|---|---|---|
   | Top 20% of the review queue vs random | 4.0× | **2.7×** | **3.0×** |
   | Top 10% vs random | 6.4× | **3.3×** | **4.1×** |
   | FY2028 cost share avoided, central scenario | $6.05 billion | $3.42 billion | **$4.47 billion** |

   The last column counts only errors over the federal tolerance, the ones the payment error rate counts. The cost share now uses the lift on those dollars (experiments 110–112).

3. **On the same test and the same inputs, our tool's predictions find more error dollars than giannella's rule lists.** Trained on FY2022–23 and tested on each state's FY2024 cases, under their error definition, both tools on their rebuilt pre-review inputs (experiment 109), paired over 49 states at a 10% review budget:
   - **Dollars:** it finds about **$2.6 billion a year** in error dollars against their $2.2 billion, and more in 35 of 49 states.
   - **Precision:** a flagged case has an error slightly more often (0.34 against 0.30 at 10%; 0.39 against 0.32 at 5%).
   - **What changed from the first comparison:** our first figures ($3.5 billion, more in 39 states) used the reviewer's corrected values as inputs, which flattered our dollars by about 17%.
   - **Predictions against rules, not model against model:** we scored our model's per-case predictions against the rule lists giannella delivers. giannella reports that its own boosted-tree models give numbers matching ours, so the gap is mostly what is given up by turning predictions into rules.
   - **Their advantages:** their lists are interpretable rules a state can read and edit, built on inputs closer to what a state has; ours is a score.
4. **The comparison confirmed some of our findings and changed others.**
   - **Agreed:** pooling across states beats state-only models; the public file misses part of each state's errors; and training numbers overstate real performance.
   - **Changed:** the fairness floor that protects older and disabled households turned out to cost about 7–10% of the tool's gain in the median state, not 1%.
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
| Compare like-for-like | Ran giannella's own data-preparation script and trained our model on its rebuilt pre-review inputs | Ours still finds more in 35 of 49 states; the reviewer's values had flattered our dollars by about 17% |
| Match the official definition | Trained and scored on errors over the federal tolerance, which is what the error rate counts | Lift on those dollars up (2.47× → 2.96×, once the label used the reviewer's own finding); cost share restated to $4.47 billion |
| Correct everything | Rebuilt the models, papers, briefs and dashboard; made leak-free the default | Corrected October 26 |

## The two projects

| | giannella/snap_qc | This project |
|---|---|---|
| What a state gets | A ranked list of if-then rules per state, in an Excel workbook | A scoring model per state that ranks cases by expected error dollars |
| How cases are ranked | By how often a rule's flagged cases have an error (precision), with a statistical safety margin | By expected error dollars (chance of an error × likely dollars) |
| What counts as an error | A payment off by more than the federal tolerance ($56 in FY2024), the official definition: about 12% of cases | The same since October 26 (experiments 111–112); before, any error found by the reviewer: about 38% of cases |
| Data | FY2017–19 and FY2022–24; dollars converted to 2026 prices | FY2020–24; nominal dollars |
| Inputs | Rebuilt pre-review values: starting from the reviewer's values and the error codes, the field in error is shifted until the benefit formula gives the benefit the agency issued | The reviewer's recorded values, plus the issued benefit (until October 26) |

That last row is the whole story:
- **giannella:** they treated the file's facts as the reviewer's and rebuilt the values a state would have had. Their inputs agree with one another and can't reveal an error.
- **Us:** we treated the reviewer's values as the agency's and put the issued benefit beside them. The two disagreed exactly when there was an error.

## How the leak was found

**The comparison test.** giannella publishes, per state, how its lists did a year ahead: mined on FY2022–23, scored on FY2024. We trained our model the same way, applied their exclusions and their error definition, and matched their test frame exactly (a median of 847 cases per state, the same 12.4% error rate).

| Median of 49 states, FY2024 | Our published model | giannella's lists |
|---|---|---|
| Precision at a 5% review budget | **1.00** | 0.32 |
| Share of error dollars caught at a 5% budget | 0.59 | 0.14 |

**Why that's impossible.** A 5% budget flags about 42 cases in the median state, and errors occur in 12% of cases. Flagging only errors, in every state, means the model can see the answer.

**What the fields hold.** The QC technical documentation says the raw file "is generated from the monthly reviews"; QC reviewers "gather financial and demographic information from the sampled unit's case file, reinterview the participants, and then determine whether the SNAP unit received the correct SNAP benefit amount." We checked the 5,809 FY2024 cases with an over-threshold error:

| Field our models used | Equals the reviewer's calculated value |
|---|---|
| Reported gross income (`RAWGROSS`) | 98.9% |
| Earned-income deduction (`RAWERND`) | 98.1% |
| Certified household size (`CERTHHSZ`) | 100% |
| Shelter deduction (`SHELDED`) | 91.9% |
| Net income (`RAWNET`) | 86.0% |

Applying the benefit formula to the reported net income reproduces the **reviewer's** corrected benefit in 79.8% of these cases, and the benefit the agency **issued** in 0.8%.

**Why it was missed.** In early October we removed four fields that are explicitly the reviewer's (`FSEARN` and others) and called the rest "agency-side". That check looked at clean cases, where the agency's and the reviewer's values are the same. It never looked at error cases, the only place the difference shows. The September pilots had in fact flagged the issued benefit as a post-decision field and dropped it (the PA7, UT7, ID7 and SD7 audits). It came back as an "agency-side" input when the rankers moved to real records (exp58).

## The corrected tool

We removed the two inputs built from the issued benefit and reran everything with the same data, splits, seeds and settings (experiments 106 and 107). The rerun matched the published results exactly when the two inputs were put back, so the change comes from those inputs alone.

| Median of 53 jurisdictions | Published | Corrected: leak-free (exp107) | **Today: leak-free, official definition (exp112)** |
|---|---|---|---|
| Top 20% of the queue vs random review | 3.97× | 2.70× (range 1.98–3.67) | **2.96×** (range 2.18–3.90) |
| Top 10% | 6.38× | 3.31× | **4.07×** |
| Trained 2020–22, tested 2023–24 | 3.80× | 2.61× | **2.95×** |
| Dollar forecast within 20% of actual | 52 of 53 | 43 of 53 | **38 of 53** |
| Older households' review ratio, ranking by dollars (1.0 = in proportion to risk) | 0.61 | 0.33 | **0.56** |
| Cost of the fairness floor (median state) | about 1.5% of the gain | about 10% | **about 4%** |
| Underpayment ranker vs main ranker (underpayment dollars) | 3.4× vs 1.5× | 1.8× vs 1.5× | **1.7× vs 1.3×** |
| FY2028 cost share avoided: central (low–high) | $6.05B ($0.39–10.06B) | $3.42B ($0.21–6.63B) | **$4.47B ($0.21–8.24B)** |

The first two columns count every error the reviewer found. The last counts only errors over the federal tolerance, the ones the payment error rate (and so the cost share) counts. On those dollars the exp107 model scored 2.47×; training on them raised it to 2.61× (experiment 110), and to 2.96× once the label used the reviewer's own finding rather than the benefit gap, which contradicts the reviewer in about 30% of cases (experiment 112). The $3.42 billion had used the lift on all error dollars; on the dollars the rate counts, the same model gives $2.62 billion.

**What held up:**
- **The tool finds more error dollars than random review in every state:** at least 2.0 times in all 53 on today's models (the lowest, Kansas, 2.18 times).
- **Ranking by dollars under-reviews older households.** It does so even more clearly without the leak, under either error definition.
- **The fairness floor fixes most of it.** On today's models it leaves 8 jurisdictions below 0.8 for older households.

**What didn't:**
- **The headline numbers.** About a third of the published gain was the leak.
- **The floor's cost.** It is no longer nearly free.
- **The separate underpayment ranker.** It is now only slightly better than the main one.

## The corrected tool against giannella's lists

**Like-for-like (experiment 109).** We ran giannella's own data-preparation script (unchanged except for leaving dollars in nominal terms) and trained our model on its rebuilt pre-review inputs. The test cases matched theirs exactly in all 49 states.

| Median of 49 states, FY2024, their error definition | Ours, on the reviewer's values | **Ours, on their rebuilt inputs** | giannella | Rebuilt: ours higher / lower |
|---|---|---|---|---|
| Precision, 5% budget | 0.39 | **0.39** | 0.32 | 33 / 11 |
| Precision, 10% budget | 0.32 | **0.34** | 0.30 | 37 / 11 |
| Share of error dollars caught, 5% budget | 0.25 | **0.21** | 0.14 | 34 / 15 |
| Share of error dollars caught, 10% budget | 0.38 | **0.32** | 0.27 | 35 / 13 |

**Two results:**
- **The reviewer's values flattered our dollars, not our precision.** Dollar recall falls by about 17% on rebuilt inputs, while precision barely moves. Any dollar figure computed from the public file's reported values is likely optimistic by about that much.
- **Like-for-like, ours still wins in most states,** by a smaller margin than first reported.

Both "ours" columns use our default model (official error label). The any-error model gives nearly the same results (exp109).

**In dollars, summed over the 49 states:**

| Per year | giannella | Ours |
|---|---|---|
| Over-threshold error dollars | $8.31B | $8.31B |
| Found at a 5% review budget | $1.18B | $1.64B |
| Found at a 10% review budget | $2.21B | $2.62B |
| FY2028 cost share avoided (central scenario, each tool's own lift) | $2.83B | $3.21B |

**Why some states show double the cost share avoided.** The rules set a state's share in steps (0%, 5%, 10% or 15% of benefits by error-rate band), so cost share avoided jumps by whole steps. Where the two tools' error rates after review land in different bands, the totals diverge sharply:
- **Exactly double:** in Arizona and Colorado our lift drops the rate two bands and theirs one.
- **Ours against nothing:** in 5 states ours crosses a band line and theirs doesn't (Florida, North Carolina, North Dakota, Oregon, Rhode Island).
- **The other way:** in Texas theirs crosses and ours doesn't ($343M against $0). California is a state where their lists find more dollars than ours (3.6× against 2.9× at 10%), though both land in the same band.
- **Everywhere else:** in the other 41 states both land in the same band and avoid the same amount.

The underlying difference is about 1.2 times the error dollars found; the band steps magnify it. A state-level "double" or "$0" can flip with a small change in lift, so read the dollars found as the steadier comparison.

**What their lists offer that ours doesn't:**
- **Inputs closer to a state's own:** pre-review values rebuilt from the reviewer's, rather than the reviewer's values themselves.
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
- **Ours:** a dollar-ranked tool reviews them less than random selection would under either definition (leak-free any-error models: 0.33 of their share of any-error risk, 0.50 under the official definition; today's models, trained on the official definition: 0.56).

The fairness concern belongs to dollar ranking specifically, and the floor fixes it.

## What changed, and what we still need to check

**Changed (October 26):**
- **Models:** all 53 state models were rebuilt without the issued benefit.
- **Documents:** every paper, state brief, the replication guides and the state-map dashboard now carry the corrected figures and a correction note.
- **Code:** the leak-free inputs are the default (`SNAPQC_FEATURES=leakfree`); the old inputs remain only to reproduce the published results.
- **Error definition (the same day, experiments 110–112):** the models now learn and are scored on errors the reviewer found whose amount is over the federal tolerance (`SNAPQC_LABEL=official`, the default). All 53 were repackaged, and the cost share uses the lift on those dollars: $4.47 billion central. An interim version labelled errors by the benefit gap ($3.15 billion), which contradicts the reviewer's finding in about 30% of cases.

**Rechecked the same day (experiment 108).** Four further results used models with the same inputs. Each was rerun both ways; the old inputs reproduced every published figure.
1. **Flag cards' "check first" coverage holds** (83–89% leak-free against 86–88%). But a fixed list of each state's three most common error locations covers about 79–80%, so most of it is base rate.
2. **The cards' odds calibration holds** (error 0.12–0.22 → 0.05–0.08).
3. **The retraining simulation does not.** A ranker retrained only on its own flags lost about 15% in four years with the leak and nothing measurable without it (2.40× against 2.29× for retraining on every case). That finding is withdrawn.
4. **The early household tests hold on today's models.** Older households are reviewed at 0.20–0.29 of their error rate, and 62–71% of those reviewed have an error.

**A limit we haven't removed yet.** For error cases our inputs are still the reviewer's corrected values, while a state's tool would see its own uncorrected values.
- **What giannella does about it:** they rebuild approximate pre-review values: from the reviewer's values and the error codes, the field in error is shifted until the formula gives the issued benefit. That is closer to what a state has.
- **Us:** we haven't rebuilt our own inputs yet. Experiment 109 measured what that costs: on their rebuilt inputs our dollar recall is about 17% lower. Our corrected figures are likely optimistic by about that much.
- **Next step:** port the rebuild to our pipeline and train the packaged models on it.

The only real test of either tool is a pilot on a state's own pre-review case records.

## The lesson

Before using any field from the QC file, ask: would a state agency have this value, as is, before a QC review? The fields that fail that test:
- the `FS*` fields;
- the reported `RAW*` fields, except the issued benefit;
- the error amount and finding;
- the error codes.

Combining a value the agency had with one only the reviewer had is the specific trap. giannella's answer, rebuilding what the agency had from the reviewer's values and the issued benefit, is the better way to use this file. We found the trap because someone else built the same thing differently and published their numbers. That is an argument for publishing, and for comparing.

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
# the official error definition (exp110 test; exp112 is the default rebuild: rerun exp83/93/79/107 above with no SNAPQC_LABEL; SNAPQC_LABEL=gap reproduces exp111)
python3 experiments/exp110_official_error_definition.py --workers 8
# like-for-like on giannella's rebuilt inputs: their munging script in a scratch copy (R + dplyr, tidyr, haven, here, ranger,
# yardstick, ggplot2, scales, arrow), then our model on its frame
(cd /path/to/scratch/copy/of/giannella-snap_qc && Rscript /path/to/experiments/exp109_export_frame.R)
python3 experiments/exp109_rebuilt_inputs.py --frame /path/to/scratch/copy/of/giannella-snap_qc/exp109_frame.parquet
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
- **Test:** each tool trained or mined on FY2022–23 and scored on the state's FY2024 QC cases, under giannella's error definition (over the $56 tolerance), both on giannella's rebuilt pre-review inputs (ours: the default model; experiment 109).
- **Error dollars a year:** FY2024 cases weighted to the caseload, times 12.
- **Found:** each tool's share of error dollars caught at the budget, times that total.
- **Dollar lift:** dollars caught at 10% ÷ 0.10.
- **Cost share avoided:** the central scenario (2% of cases reviewed a month, 80% of found errors fixed, errors lasting 6 months) with each tool's own lift.

These are scenario estimates on one test year, not forecasts.

<!-- DOLLAR-TABLE:START -->
| State | Over-threshold error $ a year | Found at 5%: giannella | Found at 5%: ours | Found at 10%: giannella | Found at 10%: ours | 10% dollar lift: giannella / ours | FY2025 rate | FY2028 cost share avoided: giannella | ours |
|---|---|---|---|---|---|---|---|---|---|
| Alabama (AL) | $127.9M | $16.7M | $25.2M | $32.3M | $39.6M | 2.52× / 3.10× | 9.52% | $85.4M | $85.4M |
| Arizona (AZ) | $162.1M | $18.7M | $38.8M | $45.1M | $66.8M | 2.78× / 4.12× | 10.80% | $97.8M | $195.5M |
| Arkansas (AR) | $29.6M | $4.9M | $6.5M | $9.0M | $9.2M | 3.04× / 3.11× | 8.81% | $24.1M | $24.1M |
| California (CA) | $1,197.5M | $261.8M | $190.6M | $430.1M | $345.4M | 3.59× / 2.88× | 10.93% | $595.8M | $595.8M |
| Colorado (CO) | $123.8M | $16.7M | $37.9M | $27.5M | $52.3M | 2.22× / 4.23× | 10.09% | $63.3M | $126.5M |
| Connecticut (CT) | $88.1M | $10.7M | $18.4M | $21.5M | $31.0M | 2.44× / 3.52× | 9.08% | $44.8M | $44.8M |
| Delaware (DE) | $19.7M | $3.0M | $3.0M | $4.9M | $4.4M | 2.49× / 2.21× | 16.00% | $0.0M | $0.0M |
| District of Columbia (DC) | $47.6M | $6.1M | $4.3M | $10.1M | $10.1M | 2.12× / 2.12× | 18.66% | $0.0M | $0.0M |
| Florida (FL) | $665.1M | $97.6M | $166.1M | $151.8M | $233.1M | 2.28× / 3.50× | 12.97% | $0.0M | $324.7M |
| Georgia (GA) | $351.3M | $33.8M | $60.3M | $79.9M | $111.0M | 2.27× / 3.16× | 15.21% | $0.0M | $0.0M |
| Idaho (ID) | $21.5M | $5.4M | $9.0M | $9.7M | $12.1M | 4.52× / 5.60× | 3.85% | $0.0M | $0.0M |
| Illinois (IL) | $474.8M | $53.6M | $118.8M | $85.7M | $170.2M | 1.80× / 3.58× | 14.67% | $0.0M | $0.0M |
| Indiana (IN) | $103.8M | $17.5M | $14.9M | $31.4M | $28.0M | 3.02× / 2.70× | 9.77% | $70.0M | $70.0M |
| Iowa (IA) | $28.7M | $6.0M | $4.1M | $10.4M | $7.0M | 3.60× / 2.44× | 5.34% | $0.0M | $0.0M |
| Kansas (KS) | $20.9M | $4.1M | $2.3M | $5.4M | $5.8M | 2.61× / 2.76× | 9.44% | $18.8M | $18.8M |
| Kentucky (KY) | $84.2M | $27.5M | $27.5M | $40.1M | $40.5M | 4.75× / 4.81× | 4.70% | $0.0M | $0.0M |
| Louisiana (LA) | $145.1M | $22.5M | $15.5M | $40.4M | $27.5M | 2.78× / 1.90× | 8.14% | $92.8M | $92.8M |
| Maine (ME) | $27.9M | $6.9M | $4.7M | $9.2M | $9.0M | 3.31× / 3.24× | 10.81% | $17.4M | $17.4M |
| Maryland (MD) | $154.7M | $15.6M | $29.1M | $35.9M | $45.5M | 2.32× / 2.94× | 13.08% | $0.0M | $0.0M |
| Massachusetts (MA) | $293.2M | $39.6M | $75.5M | $78.2M | $113.6M | 2.67× / 3.87× | 12.49% | $128.9M | $128.9M |
| Michigan (MI) | $324.2M | $42.5M | $70.9M | $88.6M | $108.2M | 2.73× / 3.34× | 9.89% | $149.6M | $149.6M |
| Minnesota (MN) | $96.3M | $18.0M | $27.2M | $29.0M | $36.7M | 3.01× / 3.81× | 12.58% | $43.1M | $43.1M |
| Mississippi (MS) | $60.3M | $9.2M | $12.7M | $17.4M | $20.4M | 2.89× / 3.38× | 9.51% | $39.7M | $39.7M |
| Missouri (MO) | $75.8M | $13.1M | $18.7M | $26.9M | $25.7M | 3.55× / 3.39× | 8.67% | $72.6M | $72.6M |
| Montana (MT) | $12.7M | $2.7M | $3.4M | $3.3M | $4.1M | 2.60× / 3.22× | 8.86% | $8.0M | $8.0M |
| Nebraska (NE) | $16.4M | $1.8M | $3.7M | $3.0M | $5.8M | 1.84× / 3.53× | 5.90% | $0.0M | $0.0M |
| Nevada (NV) | $90.1M | $20.3M | $22.3M | $29.5M | $39.0M | 3.28× / 4.33× | 6.22% | $50.8M | $50.8M |
| New Hampshire (NH) | $11.6M | $2.2M | $2.3M | $3.5M | $3.4M | 3.00× / 2.92× | 8.85% | $7.6M | $7.6M |
| New Jersey (NJ) | $113.7M | $12.5M | $13.5M | $36.2M | $36.2M | 3.18× / 3.18× | 6.86% | $92.2M | $92.2M |
| New Mexico (NM) | $102.1M | $15.4M | $18.5M | $25.6M | $33.7M | 2.51× / 3.30× | 16.81% | $0.0M | $0.0M |
| New York (NY) | $677.5M | $36.0M | $118.7M | $136.7M | $182.0M | 2.02× / 2.69× | 13.18% | $0.0M | $0.0M |
| North Carolina (NC) | $271.4M | $31.6M | $48.8M | $60.0M | $79.7M | 2.21× / 2.93× | 7.36% | $0.0M | $140.7M |
| North Dakota (ND) | $7.5M | $0.9M | $1.6M | $1.6M | $3.1M | 2.14× / 4.19× | 9.89% | $0.0M | $5.4M |
| Ohio (OH) | $173.5M | $47.3M | $37.8M | $67.6M | $44.4M | 3.90× / 2.56× | 6.76% | $151.7M | $151.7M |
| Oklahoma (OK) | $156.7M | $17.2M | $29.8M | $33.8M | $50.7M | 2.16× / 3.23× | 11.04% | $75.0M | $75.0M |
| Oregon (OR) | $191.4M | $22.0M | $45.7M | $62.0M | $86.7M | 3.24× / 4.53× | 14.14% | $0.0M | $78.6M |
| Pennsylvania (PA) | $399.4M | $56.1M | $128.8M | $131.1M | $181.8M | 3.28× / 4.55× | 9.21% | $208.8M | $208.8M |
| Rhode Island (RI) | $43.5M | $5.0M | $10.1M | $9.3M | $16.1M | 2.13× / 3.70× | 12.42% | $0.0M | $16.9M |
| South Carolina (SC) | $95.9M | $12.9M | $12.3M | $26.2M | $22.8M | 2.73× / 2.37× | 8.80% | $62.8M | $62.8M |
| South Dakota (SD) | $7.2M | $1.5M | $1.2M | $1.9M | $1.2M | 2.62× / 1.65× | 2.47% | $0.0M | $0.0M |
| Tennessee (TN) | $81.0M | $9.8M | $12.6M | $18.9M | $19.4M | 2.34× / 2.40× | 9.44% | $76.4M | $76.4M |
| Texas (TX) | $670.0M | $69.9M | $59.3M | $123.6M | $78.7M | 1.84× / 1.17× | 9.34% | $342.6M | $0.0M |
| Utah (UT) | $15.4M | $2.1M | $3.4M | $3.5M | $4.8M | 2.25× / 3.13× | 5.54% | $0.0M | $0.0M |
| Vermont (VT) | $8.7M | $1.9M | $1.5M | $3.2M | $3.0M | 3.66× / 3.46× | 5.38% | $0.0M | $0.0M |
| Virginia (VA) | $155.0M | $26.9M | $19.4M | $41.1M | $52.7M | 2.65× / 3.40× | 12.32% | $85.7M | $85.7M |
| Washington (WA) | $138.8M | $20.3M | $32.3M | $37.4M | $70.6M | 2.70× / 5.09× | 6.98% | $95.1M | $95.1M |
| West Virginia (WV) | $56.3M | $8.0M | $11.8M | $15.2M | $16.9M | 2.70× / 3.01× | 6.69% | $25.2M | $25.2M |
| Wisconsin (WI) | $88.0M | $4.6M | $22.6M | $11.8M | $29.5M | 1.35× / 3.35× | 5.72% | $0.0M | $0.0M |
| Wyoming (WY) | $4.4M | $0.4M | $0.7M | $1.0M | $1.4M | 2.21× / 3.22× | 3.96% | $0.0M | $0.0M |
| **Total, 49 states** | **$8.31B** | **$1.18B** | **$1.64B** | **$2.21B** | **$2.62B** | | | **$2.83B** | **$3.21B** |
<!-- DOLLAR-TABLE:END -->
