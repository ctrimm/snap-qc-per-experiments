# Older Adults and People with Disabilities in SNAP Error Review

**October 26, 2026 (corrected; versions of October 15 and 23) · Executive summary · Cory Trimm**


> **Corrected October 26, 2026.** The review ratios, floor costs and cost-share figures from today's models are replaced with the leak-free rebuild (experiment 107). The earlier models' inputs let them partly see errors: the issued benefit beside values recorded by QC reviewers (experiment 106). The conclusion is unchanged and stronger. The direct data profiles were not affected. The early tests (exp47–49) used early rankers; their within-state detail was rechecked on today's models for Pennsylvania and New York (experiment 108) and holds, with the precision figures corrected below. The Utah and Idaho tests were not rechecked.

## Summary

This paper covers where older adults and people with disabilities show up in the SNAP quality-control (QC) research of September 28 – October 23, 2026: what we found, what we changed, and what is still open. It was first written for a conversation with AARP. Every figure has since been checked against its source experiment, and the corrections are listed at the end.

1. **Elderly and disabled households have the highest error rates of any large group, and a review tool that chases dollars sends reviewers away from them.**
   - **Pennsylvania test set:** 48% of elderly households had a payment error, against 15% of childless adults.
   - **Today's models (all 53 jurisdictions):** ranking cases by expected dollars reviews elderly households at a median **0.33** of their share of the error risk, below 0.8 in **all 53** jurisdictions.
   - **Against random review:** in Pennsylvania and New York, random selection would give elderly households about 0.90 and 1.08 on the same measure. The dollar ranking gives 0.42 and 0.54, so it reviews them less than random selection would.
2. **The reason is error size, not missed detection.**
   - **Small but frequent:** older households' errors are frequent but small: medical deductions, Social Security and SSI changes, rent and utility timing.
   - **Larger elsewhere:** errors on earnings are larger, so a list sorted by dollars puts working households first.
   - **Found when reviewed:** when older and disabled households' cases are reviewed, reviewers find errors at high rates (62% and 69% in Pennsylvania, 71% and 76% in New York, on today's models).
3. **A fairness floor fixes it, cheaply.**
   - **What it does:** it splits the review budget across household types in proportion to where errors are, then sorts by dollars within each type.
   - **Early test (PA and NY):** it roughly doubled elderly review relative to risk, with no measurable loss in dollars found, and reviewers spent fewer reviews on error-free cases.
   - **Today's models:** it brings the median elderly ratio to **1.00** and leaves no jurisdiction below 0.8. It costs the median state about **10%** of its lift.
   - **Default:** it is on by default in our pilot recommendation.
4. **The tool doesn't hide money owed to older households, but it leaves much of it unreviewed.** The errors the ranker skips are not disproportionately underpayments. But because few older and disabled households get reviewed, they hold about **half of all unreviewed underpayment dollars** (PA 51%, NY 47%).
5. **Medical deductions are the biggest gap in our AI work.**
   - **The data:** among elderly and disabled households with medical expenses on file, **24%** have a medical-deduction error, against 2% without.
   - **The training data:** our synthetic data still produces these errors at only about 0.7–0.8 times the real rate.
   - **The fixes:** two are designed but not run.
6. **There's a second opportunity beyond error review.** About **22% of SNAP households** nationally have a low-income member aged 65 or older who likely qualifies for Medicare cost help. That work is paused until a state can share enrollment data.

Everything here is analysis of federal public-use QC data (FY2020–2024). No state has run the tool, and no household has been affected by it.

## What we tried, in plain terms

| Question | What we did | What we found |
|---|---|---|
| Who gets reviewed when a tool picks the cases with the most likely error dollars? | Compared each household type's share of reviews with its share of errors | Elderly and disabled households get far fewer reviews than their errors warrant; childless adults get far more |
| Is the tool missing their errors? | Checked how often reviews of these households found an error | No: when reviewed, two in three had an error. Their errors are just smaller |
| Can a simple rule fix it? | Gave each household type a share of the review budget matching its share of errors | Yes, everywhere, for about 10% of the tool's effectiveness in the median state |
| What about extra weight for older households? | Multiplied their dollar scores by 1.5–4 | Rejected: it gave some other household types no reviews at all |
| Are underpayments owed to older households being missed? | Compared the over/under mix of reviewed and skipped errors | Skipped errors aren't mostly underpayments, but half of all unreviewed underpayment dollars sit with these households |
| Can our AI tools catch medical-deduction errors? | Checked the training data and the language model | Not yet: the training data under-produces them, and the model couldn't identify them |
| Who might qualify for other help? | Counted SNAP households with a low-income member aged 65+ | About 22% likely qualify for Medicare cost help |

## Background: older households in SNAP and in the data

**Who counts:** SNAP counts a household member as elderly at **60 or older**.

**Different rules:** households with an elderly or disabled member get different budget rules:
- a deduction for out-of-pocket medical costs above $35 a month;
- no cap on the shelter deduction;
- only the net income test.

**Income sources:** their income is often Social Security, SSI or a pension.

**Share of the caseload:** in the FY2024 QC sample, **31%** of households have an elderly member and **50%** have an elderly or disabled member. Weighted to the caseload, those are 33% and 50%.

**Why states will care more:** the QC system reviews a random sample of cases each year, which sets each state's payment error rate. From FY2028, under H.R. 1, that rate also sets how much of benefit costs the state pays. States will have a strong financial reason to aim their own reviews where the error dollars are, and that is where older households lose out.

**The tools:**
- **The triage ranker:** scores each case using information the agency already has (reported income, deductions, rent and utilities, household size, maximum allotment; not the benefit issued). Its top 20% of cases holds a median **2.7 times** the error dollars of a random 20%, across 53 jurisdictions.
- **Flag cards:** short plain-language notes for each picked case.
- **The fairness floor:** a setting on the ranker.

## Two ways the research measured fairness

The findings below use two related measures. Their numbers are not interchangeable.

| | Early tests (exp47, exp49, Utah and Idaho pilots) | All 53 jurisdictions (exp72, exp83) |
|---|---|---|
| Measure | A type's review rate ÷ its error rate | A type's share of reviews ÷ its share of cases with an error |
| 1.0 means | A type is reviewed at the same rate as it has errors | A type gets reviews in proportion to its error risk |
| Random review gives | The budget ÷ the type's error rate (Pennsylvania elderly: 0.42) | The overall error rate ÷ the type's error rate (Pennsylvania elderly: about 0.90) |
| Rankers measured | The early rankers trained on synthetic cases (Sept 29 – Oct 4) | The rankers trained on real QC records (exp68 earlier, exp83 today) |

On both measures, the same pattern holds: elderly and disabled households score low under dollar ranking, below what random selection would give them, and a floor raises them.

## Finding 1: dollar ranking under-reviews the highest-risk households

**The first test (exp47):** it split the Pennsylvania and New York test sets by household type and compared each type's review rate with its error rate. Elderly came first, then disabled members under 60, then family makeup. The rankers were the early ones trained on synthetic cases.

| Top 20% of queue (exp47) | PA error rate | PA review rate ÷ error rate | NY error rate | NY review rate ÷ error rate |
|---|---|---|---|---|
| Elderly | 48% | **0.22** (random: 0.42) | 34% | **0.34** |
| Disabled, under 60 | 54% | **0.33** | 42% | **0.35** |
| Single parent | 39% | 1.00 | 53% | 0.52 |
| Childless adult | 15% | **1.41** | 24% | **1.45** |

**The pattern:**
- **Childless adults** were the group least likely to have an error, yet they got the most review relative to risk, and those reviews mostly came up empty (Pennsylvania precision 10%).
- **Elderly and disabled households** were found to have an error in 66% and 70% of their reviewed cases in Pennsylvania (44% and 65% in New York) in the early tests. On today's leak-free models: 62% and 69% (Pennsylvania), 71% and 76% (New York) (exp108).
- **The chronicle's summary:** the ranker is "dollar-efficient and risk-regressive at the same time."

**This is the objective, not a bug.** Within each household type, the ranker picks the highest-dollar cases correctly. The tilt comes from sorting everyone on one dollar scale.

**It replicated everywhere it was tested:**
- **Utah (early ranker):** the starkest case. Elderly and disabled households were each reviewed at **0.155** of their error rate, about one-sixth. Ranking on the chance of an error alone, with no dollar term, raised that to 0.37 for elderly and 0.66 for disabled households. The dollar term drives the tilt.
- **Idaho (early ranker):** this ranker used only the chance of an error. Idaho's elderly ratio was 0.57, still short but far better than the dollar rankers.
- **All 53 jurisdictions (exp72, exp83):** these use the second measure (below 0.8 counts as under-reviewed).

  | Models | Elderly under-reviewed | Disabled under-reviewed | Median elderly ratio |
  |---|---|---|---|
  | Earlier models (exp72) | 51 of 53 jurisdictions | 22 of 51 | 0.57 |
  | Today's models (leak-free, exp107) | **53 of 53** | **47 of 51** | **0.33** |

  Today's Pennsylvania and New York elderly ratios are 0.42 and 0.54, against about 0.90 and 1.08 for random review.

## Finding 2: the fairness floor, and where to sit on the trade-off

### What was tried (exp49, Pennsylvania and New York, early rankers)

- **A, per-type floors:** split the review budget across household types by each type's share of errors in the training data, then take the highest-dollar cases within each type.
- **B, extra weight for elderly and disabled cases:** multiply their dollar score by 1.5, 2.5 or 4.

| PA, top 20% | Dollars per review hour | Elderly review ÷ error rate | Disabled review ÷ error rate | Share of reviews finding an error |
|---|---|---|---|---|
| Rank by dollars | $67.3 | 0.22 | 0.33 | 49% |
| Random review | $47.2 | 0.42 | 0.37 | 43% |
| **Floor (A)** | **$68.9** | **0.42** | **0.53** | **58%** |
| Weighting ×2.5 (B) | $64.0 | 0.59 | 0.66 | 58% |

**New York was similar.** The floor took elderly from 0.34 to 0.66 and disabled from 0.35 to 0.48, at $85.4 → $95.3 per review hour.

**This is where "1.4 to 1.9 times" comes from.** Elderly review relative to risk rose about 1.9 times in both states (0.22 → 0.42; 0.34 → 0.66). Disabled review rose 1.6 times in Pennsylvania and 1.35 times in New York. The dollar changes were positive in point terms (bootstrap estimates PA +$1.8 an hour, 95% interval −$13.6 to +$16.4; NY +$10.0, −$14.5 to +$37.8), but the intervals include zero. The supported claim is "no measurable loss", not a gain.

**Why it can be free:** the dollar-only queue was full of cases with high predicted dollars that turned out to have no error, mostly childless adults. The floor swaps those for older and disabled households' cases, which reliably have errors. The share of reviews finding an error rose from 49% to 58%, so reviewers spent less time on clean cases. On today's models the gain is smaller (68% → 71% in Pennsylvania, 74% → 76% in New York; exp108).

**Weighting was dropped.** At ×2.5 and above it gave whole household types no reviews at all (married couples with children in New York, for example). It just moved the unfairness onto someone else.

### The trade-off

Every queue rule sits somewhere on a trade-off between dollars found and how evenly review tracks risk. exp49 found the curve **flat near the dollar-only end**: moving to proportional review cost nothing measurable.
- **The floor works like a switch, not a dial.** Floors set at 50% of the budget changed nothing, and 75% barely mattered. Only the full floor moved review, so there is one setting to defend.
- **Its cost has stayed small as the models improved:**

| Test | Scope | Cost of the floor |
|---|---|---|
| exp49 | PA, NY, early rankers | None measurable in dollars per hour |
| exp72 | 53 jurisdictions, earlier models | Median lift 3.25× → 3.18× (about 2%). Largest: Wyoming 1.72× → 1.02×, New York 3.54× → 3.13× |
| exp83 / exp107 | 53 jurisdictions, today's (leak-free) models | Median lift 2.70× → 2.42×; the median state gives up about 10%. Largest: Missouri −0.91×, Hawaii −0.76× |
| exp78 | FY2028 cost share, earlier models, top-20% basis | $3.85B → $3.49B a year avoided (central), about 9% |
| exp93 / exp107 | FY2028 cost share, today's (leak-free) models | Central $3.55B → **$3.42B** a year avoided on the top-10% basis (about 4%); $2.88B → $2.79B on the top-20% basis (about 3%) |

**For decision makers, it's a policy choice.** On current models, full proportional review for older households costs the median state about 10% of the dollars found. In avoided FY2028 cost share it costs about $0.13B a year in the central scenario.

**With the floor on,** ranker-guided reviews still avoid an estimated **$3.42B a year** (central). That's about 3.3 times what random review avoids ($1.03B), or $2.79B on the more conservative top-20% basis. The $6.05B, $5.28B and $3.49B figures in older notes all used earlier models and are superseded.

## Finding 3: underpayments owed to older households

**The ranker doesn't hide them (exp48).** The hypothesis was that the errors skipped in elderly and disabled households would be mostly underpayments. That was largely refuted. The skipped mix tracks each group's own mix of over- and underpayments: 0.90 to 1.33 times, where 1.0 is the same mix. The one place to watch is Pennsylvania's disabled households, where skipped errors lean toward underpayments (1.33 times), on a small sample.

**The issue is volume.** Because so few are reviewed, elderly and disabled households hold 51% of Pennsylvania's and 47% of New York's unreviewed underpayment dollars. In New York, 51% of disabled households' error dollars are underpayments.

**Two tools target underpayments:**
- **Floors keyed to underpayment dollars (exp51)** recovered 52–77% more underpayment dollars overall than dollar ranking (New York +52%, Pennsylvania +77%). They didn't reach elderly and disabled households better than the standard floor, though. The chronicle's advice, for equity toward older and disabled households: use the standard floor.
- **A separate underpayment ranker (exp79, leak-free)** finds a median 1.8 times the underpayment dollars of random review, better in 36 of 53 jurisdictions. The main ranker manages 1.54 times, and is worse than random in 6 jurisdictions (Alaska 0.64 times). It hasn't been broken out by household type.

## Finding 4: medical deductions and the AI models

**What the federal data shows (exp42 and the state analyses):**
- **Error rate:** elderly or disabled households with medical expenses on file have a medical-deduction error in **24.2%** of cases (n = 9,514). Without medical expenses on file, the rate is 2.0%.
- **Small claims:** small medical claims are the most error-prone: 35% for claims of $35 a month or less, 23% above $100.
- **Size and cause:** the median medical error is $46. About **48%** are caused by the agency, 6% by the client.
- **State patterns differ:**

  | State | Pattern | vs national | Direction |
  |---|---|---|---|
  | New York | Medical-expense changes the agency wasn't yet required to act on | 3.4× | 58% underpayments |
  | Pennsylvania | Medical deductions included when they shouldn't have been | 1.9× | — |
  | Pennsylvania | SSI the agency knew about but left off the budget | 1.5× | 99% overpayments |
  | Pennsylvania | SSI lower than budgeted | 1.4× | 88% underpayments |

**What our models can do:**
- **The language model:** in the first evaluation (exp30), no setup could identify medical errors (a score of zero). The trained model passed its overall checks (exp59), but no medical-specific score was reported.
- **The synthetic training data** under-produces medical errors. The fixes so far corrected the share of elderly and disabled households (exp32), then fitted the household-size mix (exp44). Medical errors are still at about **0.71–0.76 times** the real rate, varying by random seed.
- **Two fixes are designed but not run:**
  - exp42 projected that tying medical errors to whether a household has medical expenses would bring the rate to about 1.00 times real.
  - Modelling older household members who also work: 4.2% of real households, against 1.9% in the synthetic data.
- **The flag cards** already point reviewers at the checks that matter for older households:
  - "current award letters or data matches for Social Security, SSI, unemployment and child support received";
  - "out-of-pocket medical costs for elderly or disabled members, with receipts or recurring bills".

## Finding 5: Medicare cost help (exp64)

**The test:** a household member aged 65+ with gross income at or below 150% of poverty. That stands in for eligibility for Medicare Savings Programs and Extra Help. It uses FY2024 data, weighted to monthly caseloads.

**The count:** about **22%** of the 21.6 million SNAP households nationally fit that test:

| PA | NY | TX | SD | UT | ID |
|---|---|---|---|---|---|
| 20% | 30% | 22% | 18% | 14% | 19% |

**What it means:** these are counts of **likely eligibility, not unmet need**. The file doesn't show who's already enrolled, and the age-65 test misses people under 65 who get Medicare because of a disability.

**Next step:** match a state's SNAP cases against its Medicare Savings Program enrollment. That needs state data and a check of consent rules. **Paused October 10.**

## Open questions

1. **Age and disability flags in a real deployment.**
   - **What the analysis used:** the QC file's elderly and disabled flags (`FSELDER`, `FSDIS`) to group households.
   - **A caution:** exp58 found that the related counts (`FSNELDER`, `FSNDIS`) hold the reviewer's corrected values. The ranker doesn't use them, but the floor needs a state's own intake fields.
   - **Before a pilot:** age at intake is usually reliable; disability status may be less so. Map these fields first.
2. **The underpayment ranker by household type.** Does it reach older and disabled households better than the main ranker? Also test exp79's suggested 80/20 budget split between the two rankers.
3. **The two medical-data fixes,** then a medical-specific score for the language model.
4. **Re-checks:**
   - Pennsylvania's disabled underpayments, the one place exp48 saw skipped errors leaning toward money owed;
   - the early-ranker household tests (exp47–51) on today's models;
   - all of the above once the FY2025 QC file lands.
5. **Medicare Savings Program matching,** which needs a state partner.
6. **A real pilot:** shadow mode in Pennsylvania or New York, floor on by default, reporting the elderly and disabled review share every month.

## Talking points

- Older and disabled SNAP households have the highest error rates, yet a review tool that chases dollars sends reviewers elsewhere: it reviews them less than random selection would.
- Their errors are frequent but small: medical deductions, Social Security and SSI changes, rent timing. When reviewers do look at these households, they find errors in about two of three cases.
- A simple budget rule fixes it in every state and territory, for about a tenth of the tool's effectiveness in the median state. It's on by default in our recommendation.
- Age is never used to score a household. It's used only to check that each group gets its fair share of reviews.
- One in four older or disabled households claiming a medical deduction has an error in it. That's where our AI work is weakest, and the fixes are designed but not run.
- About one in five SNAP households likely qualifies for Medicare cost help. Matching that against enrollment needs a state partner.

## Appendix A: corrections to the October 15 version

| October 15 note said | Checked against | Corrected to |
|---|---|---|
| Today's models bring elderly review to "1.00 of fair share in every jurisdiction" | exp83 | The median is 1.00; individual jurisdictions range from 0.82 to 1.35, none below 0.8 |
| Reviewers found errors in "62–73%" of reviewed elderly and disabled cases in PA | exp47 table | 66% (elderly) and 70% (disabled); the chronicle's prose range didn't match its own table |
| exp47's 0.22 and exp72/83's ratios presented on one scale | exp47, exp72 code | Two different measures, defined in the table above. On today's measure (leak-free) PA elderly is 0.42 against about 0.90 at random |
| The exp47/49/Utah/Idaho results described as "a dollar-chasing review tool" without saying which | exp47, exp49, `ut_fairness`, `idf` | Labeled as the early rankers trained on synthetic cases; the 53-jurisdiction results use the real-data models |
| Early-test precision (66%/44% elderly) and the floor's precision gain (49% → 58%) quoted as current | exp108 | Early rankers only. On today's leak-free models: elderly 62% (PA) and 71% (NY); with the floor 68% → 71% and 74% → 76% |
| "Idaho and South Dakota use a ranker based only on chance of error" | Pilot papers, exp82 | They did in the October 4 pilots; today every jurisdiction uses the expected-dollar model |
| exp72's floor cost "about 2–3%" | exp72 | About 2% (3.25× → 3.18×) |
| PA SSI patterns "mostly underpayments" | PA anatomy | SSI left off the budget is 99% overpayments; SSI lower than budgeted is 88% underpayments |
| Synthetic medical errors "about 0.7×" | exp32, exp44 | 0.71–0.76×, seed-dependent |
| A flag-card quote ("medical expenses: receipts or recurring bills") | `exp62_flag_cards.py` | The template's wording: "out-of-pocket medical costs for elderly or disabled members, with receipts or recurring bills" |
| "$6.1B … ($1.0B) … $4.1B" | exp93 | $6.05B, $1.03B, $4.06B on October 23; superseded October 26 by the leak-free $3.42B, $1.03B, $2.79B (exp107) |
| Floor cost "$4.21B → $4.06B" on the top-20% basis | exp93 formula | Correct; $4.21B is computed with exp93's formula and inputs (it reproduces the published $4.06B with the floor on) but isn't printed in exp93 |

Everything else in the October 15 note matched its sources: the error rates, the ratios within each experiment, the floor's effects, the underpayment shares, the medical figures, the caseload shares (31% and 50%, recomputed from the FY2024 file) and the Medicare counts.

## Appendix B: sources and reproduction

**Data:** SNAP QC public-use files, FY2020–2024, from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles). Household types follow exp47: elderly first, then disabled members under 60, then family composition, from the `FSELDER`, `FSDIS` and composition fields.

**Code and write-ups** are in [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments) (`experiments/`):

| Topic | Experiments |
|---|---|
| Household-type tests | exp47, exp48, exp49, exp51; `ut_fairness`, `idf_id_household_burden` |
| 53 jurisdictions | exp72 (earlier models), exp83 (today's models) |
| Cost share | exp78, exp93 |
| Underpayment ranker | exp79 |
| Medical deductions and synthetic data | exp30, exp32, exp42, exp44; state analyses `pa3_pa_anatomy`, `ny3_ny_anatomy` |
| Medicare cost help | exp64 |
| Flag cards | exp62, exp65 |

```bash
# today's fairness ratios and floor costs for every jurisdiction (reproduces exp83_results.json exactly)
python3 experiments/exp83_context_models_full_eval.py --workers 8
python3 -c "import json; e=json.load(open('experiments/exp83_results.json')); print({s: v['fairness'] for s, v in e.items() if s in ('PA','NY')})"
# the early household-type tests
python3 experiments/exp47_household_type_burden.py
python3 experiments/exp49_equity_objective.py
# cost share with the floor on (central $3.42B, leak-free) and per state
python3 experiments/cost_share_replicate.py
```
