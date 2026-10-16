# Finding SNAP Payment Errors Faster: Synthetic Data, Language Models and Triage Rankers

**October 11, 2026 · Executive whitepaper · Cory Trimm**

## Executive summary

States lose money and federal standing when SNAP benefits are paid in the wrong amount. Quality control (QC) reviewers can only examine a small sample of cases, so the cases they choose matter. This project asked whether machine learning could help them choose better, and whether a small, specialized language model could act as a copilot for QC reviewers.

In under two weeks and more than 100 experiments (including rankers for every state), using five years of federal QC data (FY2020–2024, about 167,000 reviewed cases), we reached four findings:

1. **A ranking tool is ready to pilot in any state.** We built a model for every state, DC, Guam and the Virgin Islands (53 jurisdictions) that ranks cases by expected error dollars, using only information the agency has before review. Each model learns from every state's QC cases plus its own state's benefit levels, which beat state-only models everywhere. On cases it never saw, reviewing the top 20% of its queue finds a median **4.0 times the error dollars of random selection** (at least 3.0 times in every jurisdiction), and the top 10% finds 6.4 times. In Pennsylvania that is about $190 of errors found per review hour, against $47 at random. Its dollar forecasts land within 20% of actual in 52 of 53 jurisdictions.
2. **Realistic synthetic cases can teach a model real skills.** We built a generator that produces fake SNAP cases with known errors, calibrated to the federal data. Models trained only on these synthetic cases predict errors in real cases well above chance.
3. **A small language model can learn part of the QC task from synthetic data alone.** An open model of about 4 billion parameters, trained only on synthetic cases, went from guessing to passing all three of our quality checks on 1,200 fresh real QC cases, under rules fixed before the cases were drawn. It outperformed a conventional classifier trained on the same data and, on our original test set, an untrained model eight times its size. It spots errors, their direction and their location well above chance, but can barely tell the type of mistake and can't tell whose mistake it was. It also kept its SNAP policy knowledge: 74% on a 500-question CalFresh benchmark, against 73% before training. Giving small models search tools over a state policy corpus did not raise that score (about 2–3 points lower, within noise): they searched every question but rarely opened the policy documents.
4. **It could matter a great deal under the new federal cost-sharing rules.** From FY2028, states with payment error rates of 6% or more pay 5–15% of their SNAP benefit costs. At FY2025's official rates, 43 jurisdictions would pay about $10.6 billion a year. In a central scenario (reviewing 2% of cases a month), ranker-guided reviews with the fairness floor on could avoid about $6.1 billion of that a year, about six times what random reviews of the same volume would. The low and high scenarios give $0.4–10.1 billion, a range set mostly by review volume and how long errors would otherwise last.

**The ranker does the heavy lifting.** It is the tool that decides which cases a state reviews before the federal QC sample ever happens, and it is the part ready to use. The language model is, at most, a helper for the reviewer once a case is open.

**Recommendation:** pilot the ranking tool in one state (Pennsylvania or New York, where it is strongest and most accurate), with the fairness floor on by default. Keep the language model as a research track until it adds something the ranking tool can't, such as written explanations for reviewers.

## The problem

Every year, each state's QC staff review a random sample of SNAP cases and record whether the benefit was correct, overpaid or underpaid, by how much, and why. That sample sets the state's official payment error rate, which carries federal financial consequences.

Beyond the official sample, states run their own internal reviews to catch errors early. Reviewer time is the scarce resource. If reviewers could start with the cases most likely to hold large errors, the same staff would find more dollars of error and fix the causes sooner.

The federal government publishes the QC review data each year with personal details removed. It shows each sampled household's reported income, deductions, household makeup and benefit, plus what the reviewer found. That is enough to learn from, but with limits: up to about 45,000 cases a year nationally, only about 470–820 a year per state, and no written reasoning.

## How the pieces fit

The federal QC sample is random by law, and no tool should touch it. The opportunity is everything a state does **before** that sample is drawn: its own second-party and supervisory reviews of active cases. That is where the ranker works.

| Step | Who or what | What happens |
|---|---|---|
| 1. Every month | **The ranker** | Scores every active case using only what the agency has on file, and estimates its expected error dollars |
| 2. Choose cases | **The ranker** | Puts the cases most likely to hold large errors at the top of the state's review queue |
| 3. Review | **State reviewers** (optionally helped by the language model) | Work the top of the queue, correct errors, and log their causes |
| 4. Fix causes | **State program staff** | Fix the policies, notices or system issues behind repeated errors |
| 5. Federal QC | **Federal and state QC staff** | Review the usual random sample. Errors already corrected early, and causes already fixed, are errors that sample is less likely to find |

The ranker carries steps 1 and 2, which is where the dollars-per-hour gains in this paper come from. The language model has no role in choosing cases. Its possible role is in step 3, explaining a case to the reviewer who opens it.

## Approach

The project ran in three tracks, each building on the one before.

### 1. A synthetic case generator

Real QC data is too small to train a language model and can't be shared freely. So we built a generator that creates realistic fake households, computes their correct benefit using the federal benefit rules, and then injects errors: wrong income, missed deductions, household-composition mistakes and timing errors. Each error comes with the exact right answer.

We tuned the generator, experiment by experiment, until its output matched the real data on what matters: how often errors occur, overpayment versus underpayment, which part of the case is wrong, why, and how many dollars are involved. The overall error mix now matches the real data to within about 2%, and the dollar error rate to within about one percentage point. We also built versions tuned to individual states.

The test that matters is **transfer**: train a model only on synthetic cases, then test it on real ones. Across many experiments, synthetic-trained classifiers beat chance on real cases every time, reaching about half to two-thirds of what a model trained on real data achieves. Adding more synthetic data stopped helping past about 10,000 cases; making the cases more realistic was what moved results.

### 2. A small language model for QC review

The original goal was a small, specialized language model that reads a case the way a reviewer does. To measure that, we built an evaluation of 1,400 real QC cases written as reviewer-style case summaries, with up to six questions per case (the detail questions apply only to cases with errors):

| Question | What the model must say |
|---|---|
| T1 | Is there an error? |
| T2 | Correct, overpaid, or underpaid? |
| T3 | Which part of the case is wrong (income, shelter, household size…)? |
| T4 | What kind of mistake (e.g. unreported wages)? |
| T5 | Whose mistake (agency or client)? |
| T6 | How many dollars? |

We set three pass/fail checks before training anything. One was revised after early results, so the final test was rerun on fresh cases under rules committed in advance (see Results). The trained model must (1) beat the untrained model by a clear statistical margin, (2) beat it on at least four of the five category questions, and (3) identify the error's location (T3) at least as well as a conventional classifier trained on the same synthetic data. The dollar question proved nearly unanswerable from case text for every model and was dropped from scoring.

We fine-tuned Google's Gemma 4 E4B (about 4 billion parameters) on a Mac Studio. The method that worked was supervised fine-tuning: showing the model synthetic cases with correct answers, and stopping training early. Reinforcement learning on its own taught the model only to guess the most common answers. With supervised fine-tuning first, it learned real skill.

### 3. Triage rankers for individual states

In parallel, we asked a more practical question: if the goal is finding error dollars, what is the simplest tool that does it? The answer is a conventional machine-learning model (gradient-boosted decision trees, a standard method for spreadsheet-style data) with two parts. One part estimates the chance a case has an error. The other estimates how many dollars the error would be. Multiplying them gives expected error dollars, and cases are reviewed in that order.

We trained these rankers on each state's own QC records and tuned them with standard cross-validation. Each was tested three ways: on held-out cases from the same years, on a later time period (train on 2020–22, test on 2023–24), and against random selection.

## Results

### The language model learned the task from synthetic data alone

Scores on 1,200 fresh real QC cases that no model had been tested on, under pass/fail rules written down and committed before the cases were drawn. "Skill" is the average score above what lucky guessing would get, where 0% means no better than guessing:

| Model | Overall score | Skill above chance | Finds error location (T3) | Passes all checks? |
|---|---|---|---|---|
| Gemma 4, 4B, untrained | 0.5% | 0.5% | 1% | — |
| Conventional classifier, same synthetic data | 24% | 15% | 18% | — |
| **Gemma 4, 4B, trained on synthetic cases** | **33%** | **28%** | **24%** | **Yes** |

The bar for the location check was 21%, fixed in advance. The trained model beat the untrained one on all five questions (overall gain +33 points, 95% interval +31 to +35), and passed on the most recent fiscal year on its own (overall 38%). On the original test set it had scored 30%, so the fresh result is slightly higher. On that original set, an untrained Gemma 4 eight times larger scored 13%.

A model half the size (Gemma 4 E2B), trained the same way and tested the same way, scored 25% overall and missed the location bar (19%). That's about the level of the conventional classifier, so the 4B model is the smallest that clears all three checks.

It is still well short of a human reviewer. It is clearly better than chance at spotting an error, its direction and its location. It is only slightly better than chance at naming the type of mistake (T4), and no better at saying whose mistake it was (T5).

### Every state: a median 4 times the error dollars of random review

The same pipeline, run for all 53 jurisdictions on held-out cases, top 20% of each queue:

| | Result |
|---|---|
| Median lift over random review | 4.0× (lowest Alaska 3.0×, highest Washington 4.5×); top 10% of the queue 6.4× |
| Jurisdictions at 3.0× or better | 53 of 53 (Alaska 2.96× rounds to 3.0×) |
| Error dollars found per review hour | $79 to $366 |
| Train on 2020–22, test on 2023–24 | median 3.8× (lowest Wyoming 2.9×) |
| Dollar forecast within 20% of actual | 52 of 53 |

Each jurisdiction's model is trained on its own cases pooled with every other state's, plus two inputs that tell it the state's benefit levels: the case's maximum allotment and the issued benefit as a share of it. Both are known to the agency before review. Five years of one state's QC sample is about 3,000 cases; pooling lets each state borrow the error patterns that are shared across states. This beat a state-only model in all 53 jurisdictions on both the held-out cases and the later-years test (for example Pennsylvania 3.5× → 4.1×, Texas 2.7× → 3.6×, Alaska 1.3× → 3.0×). The six original pilot states' state-only results are reproduced exactly in the tables below for comparison.

### What it could mean for FY2028 cost share

H.R. 1 (2025) makes states pay part of SNAP benefit costs from FY2028 if their payment error rate is 6% or more: 5% of benefits at 6–8%, 10% at 8–10%, and 15% at 10% or more. At USDA's official FY2025 rates (national 10.62%), 43 jurisdictions would pay about $10.6 billion a year.

We modelled ranker-guided reviews of active cases as removing a share of the caseload's error dollars each month, and compared them with random reviews of the same volume. Assumptions were fixed before the results existed.

| All jurisdictions, per year | Ranker-guided reviews | Random reviews | Reviewer FTEs |
|---|---|---|---|
| Low (1% of cases reviewed a month) | $0.4B avoided | $0.2B | about 770 |
| **Central (2% a month)** | **$6.1B avoided** | **$1.0B** | about 1,540 |
| High (3% a month) | $10.1B avoided | $2.4B | about 2,310 |

In the central scenario Pennsylvania's rate falls from 9.21% to about 5.7% (cost share 10% → none, about $418 million a year), and New York's from 13.18% to about 8.2% (15% → 10%, about $360 million). How many cases get reviewed and how long a found error would otherwise have lasted drive the range; the ranker's own accuracy matters least. At every setting tried, ranker-guided reviews avoided 3–15 times what random reviews did. These are the size of the opportunity, not a forecast (see Limitations). They use the pooled models now in the package, with the fairness floor on. Without the floor the central figure would be $6.8 billion, so protecting elderly and disabled households' share of reviews costs about $0.8 billion of it. Measured on the top 20% of the queue instead of the top 10%, a more conservative reading, the central figure is $4.1 billion.

### The six pilot states in detail

Results on held-out cases each model never saw, reviewing the top 20% of its queue. Reviews are assumed to take 30 minutes each.

| State | Error dollars found vs. random | Found per review hour (random) | Top 10% of queue vs. random | Dollar forecast vs. actual (top 20%) |
|---|---|---|---|---|
| Pennsylvania | 3.5× | $165 ($47) | 5.4× | 4% under |
| New York | 3.5× | $199 ($56) | 5.2× | 7% under |
| Texas | 2.7× | $144 ($54) | 3.6× | 11% under |
| South Dakota | 2.7× | $60 ($22) | 2.9× | 13% under |
| Utah | 2.6× | $69 ($26) | 3.7× | 11% over |
| Idaho | 2.8× | $62 ($22) | 4.1× | 25% over |

These replace the figures in the earlier state pilot whitepapers (for example, $67 per hour in Pennsylvania). Those rankers were trained on synthetic cases, to test the synthetic data. These are trained on each state's real QC records, which is what a deployed tool would do, and they find about two and a half times as many dollars per review hour.

Three things make these numbers usable:

- **They hold over time.** Trained on 2020–22 and tested on 2023–24, the rankers kept most of their edge (2.3–3.3× random). A once-a-year refresh is enough.
- **The dollar forecasts are calibrated.** The raw model underestimated error dollars by 36–49%. A standard calibration step, fit on predictions for cases each model hadn't trained on, corrected that, so a state can say "the top fifth of this month's queue likely holds about $X of errors" with a ±15–20% band.
- **They use only pre-review information.** An audit found that earlier versions used four fields that contain the QC reviewer's corrected values, which a real tool wouldn't have until after review. Rebuilt without them, the rankers did as well or better in every state (Idaho within 0.03×). The useful signals are what the agency already records: reported income, deductions, housing costs, household size and the benefit issued.

### What else we learned

- **Each state's errors look different.** Pennsylvania's errors cluster in how deductions are calculated, especially shelter costs; New York's are mostly about timing. That's why each state needs its own model.
- **Some states don't record dollar amounts per error.** In 22 of 53 states, most error cases leave that field blank (Texas almost all of them), while Pennsylvania and New York fill it in. Tools that explain *where* the error was depend on states that record it.
- **Fairness can be built in cheaply.** Ranking purely by dollars gives elderly households less review than their share of errors in 49 of 53 jurisdictions, and disabled households in 30 of 51. A per-household-type floor brings review into proportion almost everywhere, for a median cost of about 1% of the lift with the current models (4.0× → 3.9×).
- **A second ranker can find households being shorted.** The main ranker targets total error dollars, mostly overpayments, and finds underpayments at only about 1.5 times random. A ranker trained on underpayments finds 3.4 times the underpayment dollars of random review, better in all 53 jurisdictions, so a state can give part of its review budget to it.
- **Ranking doesn't need a language model.** The conventional ranker already does the job well, trained on each state's own records, and costs almost nothing to run. The language model's potential lies in reading and explaining cases.

## Methodology notes

- **Data:** federal SNAP QC public-use files, FY2020–2024, about 167,000 reviewed cases nationally. Rankers used each jurisdiction's own 732–4,163 cases (five small ones pooled with other states'). Error rates are USDA's official FY2025 figures. Each state set aside about a quarter of its cases for final testing.
- **Synthetic generator:** a household sampler, the federal benefit formula, and an error injector whose rates come from the real data. Calibration and transfer were checked after every change, with each experiment recorded as hypothesis, method, result, verdict.
- **Language model:** Gemma 4 E4B (about 4 billion parameters), fine-tuned with LoRA adapters on synthetic cases only (supervised fine-tuning, about 400 steps). Reinforcement learning (GRPO) was tested and set aside. Training ran locally on a Mac Studio; a Google Colab version was also built. Scoring used macro-averaged F1 relative to guessing, with bootstrap confidence intervals and chance-corrected agreement (Cohen's kappa).
- **Rankers:** two-part gradient-boosted models (scikit-learn), probability of error times expected dollars, trained on each state's cases pooled with all others (own cases weighted 1× or 10×, chosen per state) with two state-context inputs; adopted only where they beat the state-only model on both held-out cases and a later-years test. Expected dollars are calibrated with isotonic regression on out-of-fold predictions. They are evaluated on held-out cases and on a later time period.
- **Cost-share scenarios:** a stock-and-flow model of error dollars in the active caseload (errors last until recertification; reviews correct a share each month = cases reviewed × the state's measured lift × share fixed), applied proportionally to the official rate. Three scenarios plus one-factor sensitivity, run on the pooled models with the fairness floor on (exp93).
- **Rigor:** pass/fail criteria were set before training, the one later revision was confirmed on fresh cases under rules committed before they were drawn, the real test cases were never used for training or tuning, and every result, including failures, is recorded in the project's experiment log.

## Limitations

- **Public data only.** The models were built from the federal public-use files, which omit some case detail and identifiers. A state's own case-management data would likely do better, and would need a short adaptation step.
- **Small per-state samples.** Pooling across states removed most of the small-sample weakness, but Alaska's dollar forecasts still run high (about 40% over) and its later-years lift is the lowest; a pilot there should use the state's own data.
- **The cost-share figures are scenarios.** They don't model whether corrections land before the federal sample month, procedural errors outside the public file (published rates run 2–3 points above what the public file implies), behaviour changes, the option some states have to delay, or the full cost of reviews.
- **The language model is a research result, not a product.** It passed a pre-registered test on fresh cases, but only on one kind of task (classifying public-use case records), and it is well short of a human reviewer on the details of an error.
- **The rankers prioritize; they don't decide.** They rank cases for human review. They don't make determinations about any household.

## Recommendations

1. **Pilot the ranker in one state.** Start with Pennsylvania or New York, where results and dollar forecasts are strongest. Score a current month's cases, have reviewers work the top of the queue, and compare the dollars found against the forecast.
2. **Refresh annually on the federal QC sample plus the pilot's own findings.** A simulation over FY2021–24 in six states showed that a ranker retrained only on the cases it flagged loses about 15% of its effectiveness within four years, because it never learns about errors it doesn't flag. The yearly federal QC sample is already a random, fully reviewed set of cases, and adding it closes most of that gap. Keep about 10% of pilot reviews on randomly chosen cases to watch for blind spots.
3. **Turn on the fairness floor by default** so elderly and disabled households keep a proportionate share of reviews; show each state the small cost in dollars found.
4. **Measure what drives the cost-share estimate:** realistic review volume and how long a found error would otherwise have lasted. Those two numbers settle most of its range.
5. **Offer the underpayment ranker as a second queue** for states that want to find households being shorted, not only overpayments.
6. **Continue the language model as research** aimed at what the ranker can't do: plain-language explanations of why a case looks risky. Flag cards built on the ranker are in testing: they name the part of the case to check first (the real error is among their top three for 86–88% of flagged errors in Pennsylvania and New York), with odds recalibrated to be honest. Model-written notes still need a check that they state those odds correctly.

## Project timeline

| When | Milestone |
|---|---|
| Sept 28–29 | Project started. Synthetic generator built and calibrated over ~45 experiments, and the language-model evaluation designed; first proof that synthetic-trained models predict real errors. Pennsylvania and New York pilots, each with its own whitepaper. |
| Oct 2–3 | Fairness analysis: how dollar-focused ranking affects elderly, disabled and other household types, and a review floor that fixes it. |
| Oct 4 | Pilots for Texas, South Dakota, Utah and Idaho, each with its own whitepaper. Language model evaluation run on two Gemma 4 models: the untrained small model scored near zero; the larger one only slightly better. |
| Oct 5–6 | Small model trained on synthetic cases: reinforcement learning alone failed; supervised fine-tuning worked. A conventional classifier on the same data scored similarly. |
| Oct 7 | Training data made consistent with how the evaluation labels cases; best language model passes all checks on the original test set. Triage rankers tuned for six states, dollar forecasts calibrated, rebuilt on pre-review data only, and packaged for a pilot. |
| Oct 9 | Pre-registered confirmation on 1,200 fresh real cases: the language model passes all three checks (overall 33%, location 24% vs a 21% bar). |
| Oct 9 | A half-size model (E2B) trained the same way scores 25% and misses the location check: the 4B model is the smallest that passes. |
| Oct 10 | Rankers for all 53 jurisdictions, pooled models for the smallest, a fairness audit across all of them, and FY2028 cost-share scenarios on USDA's official FY2025 error rates. Policy knowledge check passed. |
| Oct 10–11 | Pooled, state-context models beat state-only models in all 53 jurisdictions (median 4.0×); underpayment ranker; fairness floor now costs about 1%. Automatic generator tuning and policy-search tools for small models tested and set aside. |
| Oct 15 | FY2028 cost-share scenarios re-run on the pooled models with the fairness floor on: $6.1 billion a year avoided in the central scenario. |
