# Older Adults in SNAP Error Review

**October 26, 2026 (corrected; first version October 23) · Whitepaper · Cory Trimm**


> **Corrected October 26, 2026.** The October 23 version's review ratios and cost figures came from ranking models whose inputs let them partly see errors: the issued benefit beside values recorded by QC reviewers (experiment 106). They are replaced here with the October 26 rebuild: leak-free inputs (experiment 107), trained and scored on the errors that count toward the official payment error rate, those over the federal tolerance (experiment 111). The conclusion is unchanged and stronger: dollar ranking under-reviews older households. Figures computed directly from the QC data (error rates, error types, income sources, medical deductions, Medicare counts) were not affected.

## Summary

About three in ten SNAP households include someone aged 60 or older. This paper looks at those households alone: how often their benefits are paid in error, what kind of errors they are, and how they fare when a state uses a data-driven tool to choose which cases to review. A companion paper covers older adults and people with disabilities together. Every figure here is computed from federal SNAP quality-control (QC) data, FY2020–2024, and checked against the experiment that produced it.

1. **Older households have more payment errors than other households, but smaller ones.**
   - **How often:** 42% of reviewed households with a member aged 60+ had an error, against 36% of other households.
   - **How large:** the typical (median) error was $18, against $31 for others.
   - **What kind:** most involve the shelter deduction, Social Security amounts, the utility allowance or medical deductions. Wages carry only 10% of older households' error dollars, against 44% for other households.
2. **A review tool that chases error dollars sends reviewers away from older households.**
   - **Today's models:** counting the errors the official rate counts (over the federal tolerance), they review older households at less than 0.8 of their share of that error risk in 50 of 52 measurable jurisdictions (median 0.44). In all 52 that is less than random selection would give them (median 1.35).
   - **A definitional twist:** older households have more errors than others overall, but fewer over the tolerance, because their errors are small. Random review therefore over-reviews them on this measure, and dollar ranking still pushes them well below it.
   - **The cause is error size, not missed detection:** when older households are reviewed, errors are found in most of them (62% of reviewed cases in Pennsylvania and 71% in New York; exp108, measured on the any-error models before the switch).
3. **A simple budget rule fixes it.**
   - **What it does:** a fairness floor gives each household type a share of the review budget matching its share of errors, then picks the highest-dollar cases within each type.
   - **Effect:** it brings older households to a median of 1.02. It still leaves 8 of 52 jurisdictions below 0.8, because errors over the tolerance are rarer and the floor's shares rest on fewer cases.
   - **Cost:** about 7% of the tool's effectiveness in the median state.
4. **Medical deductions are the error most specific to older households.** Among older households with medical expenses on file (about one in seven), **24%** have a medical-deduction error, against 2.5% of older households without.
5. **Underpayments owed to older households are not being hidden, but many go unreviewed.** Their errors lean toward overpayments about as much as everyone else's. Underpayments are 27% of their error dollars, against 28% for other households, and the ranker's skipped errors follow that same mix.
6. **Many older SNAP households likely qualify for Medicare cost help.** About 22% of all SNAP households have a member aged 65+ with income low enough for Medicare Savings Programs or Extra Help.

All of this is analysis of federal public-use QC data. No state has used the tool, and no household has been affected by it.

## What we tried, in plain terms

| Question | What we did | What we found |
|---|---|---|
| Are older households' benefits paid correctly? | Compared error rates and error sizes for households with and without a member aged 60+ | More errors, but smaller ones |
| What goes wrong? | Looked at which part of the case each error was in | Housing costs, Social Security amounts, utility allowances and medical deductions, rarely wages |
| Who gets reviewed when a tool picks the cases with the most likely error dollars? | Compared older households' share of reviews with their share of errors, in every state | Fewer reviews than their errors warrant, and fewer than random selection would give |
| Is the tool missing their errors? | Checked how often reviews of older households found an error | No: two in three reviewed cases had one. Their errors are just smaller |
| Can a simple rule fix it? | Gave each household type a share of the review budget matching its share of errors | Yes, in every state, for about 10% of the tool's effectiveness in the median state |
| Are underpayments owed to older households being missed? | Compared the over/under mix of reviewed and skipped errors | Skipped errors aren't mostly underpayments |
| Who might qualify for other help? | Counted SNAP households with a low-income member aged 65+ | About 22% of all SNAP households likely qualify for Medicare cost help |

## Who older SNAP households are

**Who counts as elderly:** SNAP counts a household member as elderly at **60 or older**. Medicare cost-help programs start at 65.

**Different rules:** households with an elderly (or disabled) member get different budget rules:
- a deduction for out-of-pocket medical costs above $35 a month;
- no cap on the shelter deduction;
- only the net income test.

**In the QC data (FY2020–2024, 167,002 reviewed households):**

| | Households with a member aged 60+ | Other households |
|---|---|---|
| Share of reviewed households | 30% (FY2024: 31%; 33% weighted to the caseload) | 70% |
| Have Social Security income | 74% | 16% |
| Have SSI | 33% | 19% |
| Have earnings | 5% | 30% |
| Have medical expenses on file | 14% | — |

Older households live mostly on Social Security and SSI. That matters for the errors they have, and for how a review tool sees them.

## Finding 1: more errors, but smaller ones

| FY2020–2024, reviewed households | Members aged 60+ | Other households |
|---|---|---|
| Households with a payment error | **42%** | 36% |
| Median error | **$18** | $31 |
| 90th percentile error | $119 | $206 |
| Error dollars that are underpayments | 27% | 28% |
| Errors coded as reporting or timing issues | 47% | 39% |

**Where older households' errors are:**

| Part of the case | Share of older households' error dollars | Share of their error cases | For comparison: other households' error dollars |
|---|---|---|---|
| Shelter deduction | 31% | 48% | 12% |
| Social Security (RSDI) amounts | 15% | 14% | 3% |
| Standard utility allowance | 12% | 7% | 5% |
| Wages | 10% | 4% | 44% |
| Medical expense deductions | 9% | 9% | 1% |

**What this shows:**
- **The errors match the income.** Older households' errors follow their income and expenses: housing costs, Social Security cost-of-living changes, utility allowances and medical costs.
- **Timing:** nearly half carry the reporting or timing code: something changed and the case wasn't updated in time.
- **Size:** these errors are frequent but small.
- **Other households are different:** their largest errors are in earnings, which are larger and change more often.

**It holds in almost every state.** Older households' error rate is higher than the overall rate in 48 of 53 jurisdictions. It's equal in Maine and Virginia, and lower in North Carolina, Texas and Wisconsin (Appendix A).

## Finding 2: a dollar-chasing review tool under-reviews older households

The triage ranker scores each case on information the agency already has: reported income, deductions, rent and utilities, household size and the household's maximum allotment (not the benefit issued, which in the federal QC data would let it see the error; experiment 106). It orders the review queue by expected error dollars. Its top 20% of cases holds a median **2.7 times** the error dollars of a random 20%, across 53 jurisdictions. Because older households' errors are small, their cases sit lower in that queue.

**The measure:** older households' share of reviews divided by their share of cases with an error. **1.0** means they are reviewed in proportion to their risk. Random selection gives the overall error rate divided by their error rate (below 1.0, because they have more errors than average).

| Today's models, 52 measurable jurisdictions (exp111) | Older households |
|---|---|
| Median review ratio, ranking by dollars (errors over the tolerance) | **0.44** |
| Median ratio random selection would give | 1.35 |
| Jurisdictions below 0.8 | **50 of 52** (Wyoming can't be measured) |
| Jurisdictions below what random selection would give | **52 of 52** |
| Pennsylvania / New York | 0.58 / 0.76 (random: 1.22 / 1.72) |

**The same pattern appeared in the first tests,** on early rankers trained on synthetic cases. They used a slightly different measure: a group's review rate divided by its error rate.
- **Pennsylvania:** the tool reviewed older households at **0.22** of their error rate. Random review would have given 0.42, so it treated the highest-risk group worse than a lottery would. Childless adults, the lowest-risk group (15% error rate), were reviewed at 1.41.
- **New York:** older households 0.34.
- **Utah:** **0.155**, about one-sixth. Ranking on the chance of an error alone, without the dollar term, raised it to 0.37.
- **Idaho:** a ranker using only the chance of an error gave 0.57.

**This is not a detection failure.** When older households' cases were reviewed, errors were found in 62% of them in Pennsylvania and 71% in New York on the leak-free any-error models (exp108; 66% and 44% in the early tests). On those models the dollar-only queue reviews them at 0.20 (Pennsylvania) and 0.29 (New York) of their error rate, close to the early tests' 0.22 and 0.34. The tool picks the right cases *within* each group. It deprioritizes older households because their errors are worth fewer dollars, not because it can't find them.

## Finding 3: the fairness floor

**The fix:** split the review budget across household types in proportion to each type's share of errors, then take the highest-dollar cases within each type. A second idea, giving older households' scores extra weight, was rejected: at higher weights it gave some other household types no reviews at all.

| | Early tests: Pennsylvania (exp49) | Early tests: New York (exp49) | Today's models, 52 measurable jurisdictions (exp111) |
|---|---|---|---|
| Older households' review ratio, dollars only | 0.22 | 0.34 | median 0.44 |
| With the floor | **0.42** | **0.66** | **median 1.02**; 8 of 52 below 0.8 |
| Dollars found per review hour | $67.3 → $68.9 | $85.4 → $95.3 | — |
| Cost to the tool's lift | none measurable | none measurable | median 2.61× → 2.45×; the median state gives up about 7% |

**Why it was free in the early tests:** the dollar-only queue contained many cases with high predicted dollars and no actual error, mostly childless adults. Swapping those for older households' cases, which reliably have errors, raised the share of reviews that found an error (Pennsylvania 49% → 58%). On today's models the gain is smaller (68% → 71% in Pennsylvania, 74% → 76% in New York; exp108), because the queue holds fewer error-free cases to swap out.

**The FY2028 cost share:** from FY2028, under H.R. 1, states with error rates of 6% or more pay 5–15% of benefit costs.
- **With the floor on:** ranker-guided reviews avoid an estimated **$3.15 billion a year** nationally in the central scenario, against $1.03 billion for random reviews of the same volume.
- **What the floor costs:** without it the central figure would be $3.90 billion, so protecting older and disabled households' share of reviews costs about $0.75 billion a year in avoided cost share.

**Default:** we recommend the floor on by default. Age is never used to score a household. It is used only to check that each group gets its fair share of reviews.

## Finding 4: medical deductions

| Older households (FY2020–2024) | Share with a medical-deduction error |
|---|---|
| With medical expenses on file (7,170 households, 14% of older households) | **24.0%** |
| Without medical expenses on file | 2.5% |
| For comparison: households with no elderly or disabled member | 0.02% |

**The medical deduction is the error most specific to older households.** It applies only to elderly and disabled members, it requires tracking out-of-pocket costs that change, and the costs must exceed $35 a month. Combined with disabled households, small claims are the most error-prone: 35% of claims of $35 a month or less had an error (exp42).

**This is the biggest gap in our AI work:**
- **Training data:** the synthetic cases used to train our models produce medical errors at only about 0.71–0.76 times the real rate (elderly and disabled households together). Two fixes are designed but not run.
- **Language model:** in its first evaluation it couldn't identify medical errors at all.
- **Flag cards:** they already tell reviewers to check "out-of-pocket medical costs for elderly or disabled members, with receipts or recurring bills" and "current award letters or data matches for Social Security, SSI, unemployment and child support received".

## Finding 5: underpayments owed to older households

- **No hidden underpayments:** older households' errors are underpayments for 27% of error dollars, about the same as other households (28%). In the early Pennsylvania and New York tests, the errors the ranker skipped in older households followed that same mix (1.14 and 0.90 times their own mix, where 1.0 is the same).
- **Volume:** because older households are under-reviewed, their underpayments go unreviewed with everything else. Older households held 25% (Pennsylvania) and 24% (New York) of all unreviewed underpayment dollars in those tests, while making up 38% and 42% of cases.
- **A separate underpayment ranker** finds a median 3.36 times the underpayment dollars of random review, against 1.55 times for the main ranker (exp79). It hasn't been broken out by household type.

## Finding 6: Medicare cost help (exp64)

**The test:** a household member aged **65+** with gross income at or below 150% of poverty. That stands in for eligibility for Medicare Savings Programs and Extra Help. It uses FY2024 data, weighted to monthly caseloads.

**The count:** about **22%** of the 21.6 million SNAP households nationally fit that test, about 4.8 million households:

| PA | NY | TX | SD | UT | ID |
|---|---|---|---|---|---|
| 20% | 30% | 22% | 18% | 14% | 19% |

**What it means:** these are counts of likely eligibility, not unmet need. The QC file doesn't show who is already enrolled.

**Next step:** match a state's SNAP cases against its Medicare Savings Program enrollment, which needs state data and a check of consent rules.

## Open questions

1. **Age in a real deployment.** The analysis groups households by the QC file's elderly flag (`FSELDER`). In a pilot, the floor needs the state's own record of each member's age, which is usually reliable at intake.
3. **The underpayment ranker for older households.** Does it reach them better than the main ranker?
4. **The medical-data fixes,** then a medical-specific score for the language model.
5. **The FY2025 QC file,** when it is released: rerun everything above.
6. **A pilot:** shadow mode in Pennsylvania or New York, with the floor on and older households' share of reviews reported every month.

## Talking points

- About three in ten SNAP households include someone 60 or older. Their benefits have errors more often than other households', but the errors are small: housing costs, Social Security changes, utilities, medical deductions.
- A review tool that chases error dollars sends reviewers elsewhere. In all 53 states and territories, it reviews older households less than random selection would.
- When reviewers do look at older households, they find errors in most cases. The issue is where the tool points, not what reviewers can find.
- A simple budget rule fixes it everywhere, for about a tenth of the tool's effectiveness in the median state. We recommend it on by default.
- Age is never used to score a household, only to check that older households get their fair share of reviews.
- One in four older households claiming medical expenses has a medical-deduction error. That's where our AI work is weakest.
- About one in five SNAP households likely qualifies for Medicare cost help; confirming who is enrolled needs a state partner.

## Appendix A: older households in every jurisdiction

Columns, from left:
- **Elderly share:** households with a member aged 60+, as a share of reviewed cases (FY2020–2024).
- **Elderly error rate and all households' error rate:** the shares of those cases with a payment error.
- **Underpayment share:** underpayments as a share of older households' error dollars.
- **Review ratio, dollars only and with the floor:** from today's models (leak-free inputs, official error definition) on each jurisdiction's held-out cases (exp83 design, exp111). Wyoming's held-out cases have no elderly errors over the tolerance, so it has no ratio.
- **Random review would give:** the ratio random selection would give on the same held-out cases.

<!-- OLDER-TABLE:START -->
| Jurisdiction | Elderly share of reviewed cases | Elderly error rate | All households' error rate | Underpayment share of elderly error dollars | Review ratio, dollars only | With the floor | Random review would give |
|---|---|---|---|---|---|---|---|
| Alabama (AL) | 27% | 44% | 34% | 14% | 0.34 | 1.46 | 1.54 |
| Alaska (AK) | 31% | 39% | 35% | 43% | 0.46 | 0.69 | 0.90 |
| Arizona (AZ) | 26% | 33% | 31% | 31% | 0.42 | 1.20 | 1.35 |
| Arkansas (AR) | 28% | 35% | 33% | 34% | 1.03 | 1.91 | 3.40 |
| California (CA) | 36% | 53% | 41% | 23% | 0.60 | 1.10 | 1.11 |
| Colorado (CO) | 29% | 41% | 35% | 22% | 0.35 | 1.00 | 1.29 |
| Connecticut (CT) | 35% | 42% | 40% | 26% | 0.47 | 0.97 | 1.33 |
| Delaware (DE) | 29% | 41% | 38% | 18% | 0.42 | 0.94 | 1.23 |
| District of Columbia (DC) | 29% | 50% | 43% | 47% | 0.51 | 1.03 | 1.17 |
| Florida (FL) | 39% | 44% | 41% | 16% | 0.41 | 1.09 | 1.20 |
| Georgia (GA) | 29% | 53% | 51% | 19% | 0.44 | 0.91 | 1.68 |
| Guam (GU) | 27% | 51% | 47% | 25% | 0.33 | 0.99 | 1.05 |
| Hawaii (HI) | 40% | 46% | 44% | 32% | 0.62 | 1.29 | 1.55 |
| Idaho (ID) | 29% | 35% | 34% | 21% | 0.46 | 1.02 | 1.29 |
| Illinois (IL) | 29% | 41% | 35% | 11% | 0.35 | 1.08 | 1.01 |
| Indiana (IN) | 24% | 44% | 39% | 34% | 0.46 | 1.15 | 1.93 |
| Iowa (IA) | 25% | 33% | 33% | 29% | 0.68 | 1.68 | 2.47 |
| Kansas (KS) | 26% | 46% | 42% | 20% | 0.30 | 0.77 | 0.99 |
| Kentucky (KY) | 28% | 32% | 30% | 38% | 0.35 | 0.73 | 1.16 |
| Louisiana (LA) | 27% | 46% | 42% | 33% | 0.35 | 0.95 | 0.99 |
| Maine (ME) | 36% | 41% | 41% | 23% | 0.49 | 1.45 | 1.78 |
| Maryland (MD) | 33% | 38% | 38% | 49% | 0.52 | 1.00 | 1.40 |
| Massachusetts (MA) | 36% | 44% | 37% | 20% | 0.61 | 1.17 | 1.33 |
| Michigan (MI) | 29% | 50% | 44% | 24% | 0.27 | 0.76 | 1.01 |
| Minnesota (MN) | 29% | 48% | 38% | 40% | 0.23 | 0.77 | 1.00 |
| Mississippi (MS) | 26% | 38% | 37% | 27% | 0.34 | 0.92 | 1.82 |
| Missouri (MO) | 27% | 48% | 40% | 26% | 0.22 | 0.68 | 1.05 |
| Montana (MT) | 33% | 49% | 42% | 29% | 0.33 | 0.76 | 1.00 |
| Nebraska (NE) | 24% | 40% | 35% | 33% | 0.23 | 1.15 | 2.15 |
| Nevada (NV) | 26% | 43% | 33% | 15% | 0.51 | 1.40 | 1.41 |
| New Hampshire (NH) | 31% | 34% | 34% | 62% | 0.27 | 0.98 | 1.30 |
| New Jersey (NJ) | 43% | 33% | 32% | 45% | 0.65 | 1.49 | 2.26 |
| New Mexico (NM) | 23% | 57% | 48% | 12% | 0.29 | 1.16 | 1.45 |
| New York (NY) | 43% | 38% | 37% | 29% | 0.76 | 1.31 | 1.72 |
| North Carolina (NC) | 28% | 33% | 36% | 27% | 0.61 | 1.01 | 1.66 |
| North Dakota (ND) | 25% | 42% | 38% | 39% | 0.22 | 0.66 | 1.48 |
| Ohio (OH) | 31% | 41% | 38% | 31% | 0.50 | 1.62 | 1.98 |
| Oklahoma (OK) | 21% | 46% | 41% | 22% | 0.27 | 0.99 | 1.42 |
| Oregon (OR) | 30% | 45% | 40% | 9% | 0.46 | 0.93 | 1.13 |
| Pennsylvania (PA) | 35% | 47% | 43% | 25% | 0.58 | 0.94 | 1.22 |
| Rhode Island (RI) | 36% | 56% | 48% | 22% | 0.31 | 0.94 | 1.07 |
| South Carolina (SC) | 32% | 38% | 36% | 26% | 0.33 | 1.36 | 1.78 |
| South Dakota (SD) | 26% | 27% | 26% | 41% | 0.78 | 1.75 | 2.93 |
| Tennessee (TN) | 25% | 41% | 35% | 31% | 0.45 | 1.06 | 1.48 |
| Texas (TX) | 29% | 41% | 44% | 43% | 0.17 | 1.04 | 1.20 |
| Utah (UT) | 20% | 37% | 33% | 27% | 0.45 | 1.34 | 1.94 |
| Vermont (VT) | 38% | 47% | 35% | 34% | 0.89 | 1.29 | 1.59 |
| Virgin Islands (VI) | 34% | 48% | 42% | 27% | 0.48 | 0.96 | 1.35 |
| Virginia (VA) | 31% | 46% | 46% | 25% | 0.58 | 1.16 | 1.50 |
| Washington (WA) | 30% | 28% | 26% | 23% | 0.36 | 0.82 | 1.03 |
| West Virginia (WV) | 32% | 39% | 38% | 22% | 0.58 | 1.09 | 1.32 |
| Wisconsin (WI) | 27% | 31% | 33% | 23% | 0.34 | 0.89 | 1.57 |
<!-- OLDER-TABLE:END -->

## Appendix B: data, definitions and reproduction

**Data:** SNAP Quality Control public-use files, FY2020–2024, from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles) (167,002 reviewed households).

**Definitions:**
- **Older household:** `FSELDER` = 1, a member aged 60 or older. Elderly is checked before disability, as in exp47 and exp72.
- **Error case:** `STATUS` 2 (overissuance) or 3 (underissuance).
- **Error dollars:** `AMTERR`.
- **Part of the case:** the first variance's element (`ELEMENT1`).
- **Timing:** nature code 97.
- **Medical-deduction error:** any variance with element 365. As a check, this method reproduces exp42's figure for elderly-or-disabled households with medical expenses on file exactly (n = 9,514, 24.15%).
- **Income sources:** the verified income fields (`FSSOCSEC`, `FSSSI`, `FSWAGES`), used here only to describe households. The ranker never uses them.
- **Weighting:** unweighted, five years pooled, except the FY2024 weighted share.

**Fairness ratios:**
- **Today's models (exp111):** a type's share of reviews ÷ its share of cases with an error over the federal tolerance, in the top 20% of each jurisdiction's held-out queue. Random review gives the overall over-tolerance error rate ÷ the type's.
- **Random-review ratio:** the overall error rate ÷ older households' error rate, on the same held-out cases (`experiments/exp68_holdouts.json`).
- **The early tests (exp47, exp49, Utah, Idaho):** a group's review rate ÷ its error rate, on rankers trained on synthetic cases.

**Reproduce:**

```bash
python3 whitepaper/older_adults_numbers.py                 # every figure in this paper, and Appendix A
python3 experiments/exp83_context_models_full_eval.py --workers 8   # today's fairness ratios (reproduces exp83_results.json)
python3 experiments/exp47_household_type_burden.py         # early household-type test
python3 experiments/exp49_equity_objective.py              # the fairness floor, early test
python3 experiments/cost_share_replicate.py                # FY2028 cost share, floor on
```

**Related:**
- *Older Adults and People with Disabilities in SNAP Error Review* (`whitepaper/older_adults_disabled_whitepaper.pdf`), the combined paper with its corrections appendix.
- Experiments exp42, exp47–49, exp64, exp72, exp79, exp83 and exp93 in `experiments/`.
