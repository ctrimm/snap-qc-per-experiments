# What we've learned so far

Plain-language synthesis across exp1–exp113 and the state tracks.
Sections 1–5 as of 2026-10-02; sections 6–12 added 2026-10-27. Details live in the per-experiment chronicles indexed in
[`README.md`](README.md).

## 1. We can make realistic fake SNAP cases, and "realistic" has two meanings

The generator now matches real QC data closely on the overall picture: which
cases have errors, over vs. under, which element, the cause, and dollar sizes
(finding mix within about 2%). It's also within about 1 point of the real
dollar error rate (exp40).

But exp35 showed that a model can still tell fake cases from real ones almost
perfectly (AUC 0.98). The biggest giveaway is the shelter deduction, and
households don't yet hang together right: who works, who's a senior,
household size (exp39, exp44). Most current calibration work is about fixing
those combinations.

## 2. Models trained only on fake cases learn real things

Trained on synthetic cases and tested on real ones, models beat guessing
every time, but they reach only about half to two-thirds of what a model
trained on real data gets. More fake data stops helping past about 10k cases
(exp36). From there, gains come from making the cases more faithful, not from
making more of them.

## 3. Some recipe choices only work for one kind of model

For years of experiments, the rule was to train on the faithful pool and pay
extra attention to rare errors. exp37 and exp43 showed the second half only
helps tree models; for logistic regression and transformers it hurts. Recipe
settings need re-checking for each model type before they're trusted. The
language model will use the faithful pool with normal (uniform) weighting.

## 4. For an actual state, the value is in triage, not prediction

In both the Pennsylvania and New York pilots, the synthetic-trained model
predicted real state errors better than chance and held up across years
(PA6, NY6). The useful product is a ranking: review the riskiest half of
cases and you catch about two-thirds of errors (PA4, NY4).

Ranking by expected dollars, not error likelihood, roughly doubles the
dollars recovered per reviewer hour ($75 vs $47 in PA, $85 vs $56 in NY;
PA5, NY5). Ranking by error likelihood alone is worse than random at the
very top, because frequent errors tend to be small.

Each state also has its own error pattern: PA's errors are in how deductions
get built, NY's are about timing (PA3, NY3). That's why tailoring the
generator to a state helps in PA but only partly in NY (PA2, NY2).

## 5. The engines themselves are clean

State eligibility systems apply the benefit formula correctly 94–100% of the
time (exp8b, PA 8c, NY 8c). Errors come from the facts entered (wrong income,
missed changes, late updates), not from bad math. So a QC copilot should
check case facts, not recompute benefits.

## 6. Trained on real records, the ranker is the product

Once rankers were trained on the real QC records (each state's cases pooled with every other state's), they found two to three times the error dollars of random review in every jurisdiction.
- **Pooling:** it beats state-only models even without the leak (2.70× against 2.27×, better in 46 of 53; exp108).
- **Why it matters now:** H.R. 1 makes states with error rates of 6% or more pay part of benefit costs from FY2028, which gives the tool a concrete use.

## 7. An outside comparison found a leak we had missed

**What happened (exp106):** our rankers paired the issued benefit with income and deduction values that, in the QC file, are the reviewer's corrected facts. A model can then see an error as a mismatch.
- **How it showed:** on Better Government Lab's snap_qc test, our model flagged errors with 100% precision, which is impossible.
- **The size of it:** about a third of the published gain was the leak (4.0× → 2.7×; exp107).
- **Missed twice:** the September pilots had flagged the issued benefit and dropped it. It came back when the rankers moved to real data.

**The rule now:** before using a field, ask whether a state agency would have it, as is, before a review.

## 8. Define the target the way the money is defined

**The decision that counts:** the cost share is set by the official payment error rate, which counts only errors over the federal tolerance ($56 in FY2024). Training on that target, rather than every error, raised the lift on the dollars that count (exp110).

**How to build that label (exp112):** use the reviewer's own finding (an error found, with an amount over the tolerance). Not the gap between the issued and correct benefit: that gap contradicts the reviewer in about 30% of cases.

**What the label changed:**
- **Ranking:** the median top-20% lift is 2.96× on that target.
- **The cost-share scenario:** the central estimate is $4.47B a year avoided, range $0.21–8.24B. It had read $6.05B, $3.42B and $3.15B as each error was found.

## 9. The honest figures are lower, and still good

**Public data flatters us.** For error cases, the public file's reported fields are the reviewer's corrected values, while a state sees its own uncorrected ones. Better Government Lab's pipeline rebuilds approximate pre-review values.
- **One year ahead (exp109):** on those rebuilt inputs our dollar figures fall about 17%.
- **Across three windows (exp113):** the top-20% lift is about 2.6×, against 2.96× on reviewer values. That includes a second era (FY2019) and three years ahead (the gap a state actually faces).

**Expect real results about 10–15% below the public-data figures.** Only a pilot on a state's own records settles it.

## 10. Compared like-for-like, a score beats a rule list on dollars, but rules have their place

**The comparison:** on the same cases, the same inputs and the same budgets, our model catches more over-tolerance error dollars than Better Government Lab's rule lists. That holds in every window tested, and three years ahead it does better in 47 of 49 states (exp113).

**What their rules offer that our score can't:** a reviewer can read, question and edit them.

**What they taught us:**
- **The leak:** their comparison exposed it.
- **The pre-review rebuild:** it's the better way to use the file.
- **The gap between labels:** the benefit gap contradicts the reviewer's own finding.
- **The second-era test:** it showed our result isn't a one-year effect.

## 11. Fairness has to be built in, and checked every time the model changes

**Ranking by dollars under-reviews older households,** whose errors are frequent but small. Without a floor they get about half their share of reviews.
- **The fix:** a fairness floor gives each household type its share of reviews.
- **What it costs:** about 4% of the lift in the median state.
- **What it doesn't fix:** it still leaves 8 of 52 jurisdictions below 0.8 for older households on today's models. Every change of model or label has moved these numbers, so they need re-measuring each time.

## 12. Small findings that changed the advice

**Retraining on flagged cases only (exp108):** the "15% loss" was the leak, so that finding is withdrawn.

**Flag cards (exp108):** their "check first" lists mostly reflect where errors usually are. A fixed list of each state's three most common error locations covers about 80%. The model's value is in the ordering.

**Synthetic data and language models:**
- **Synthetic data carries real signal:** a 4-billion-parameter model fine-tuned only on synthetic cases predicts real QC findings well above chance.
- **Policy questions:** a larger model with policy lookup reaches about 90% on the CalFresh policy quiz. What's left is mostly reasoning, not missing rules.

## What's still open

- **A state pilot:** shadow mode, on the state's own pre-review case records. It is the only real test of the ranker's numbers.
- **Rebuilding our own inputs as pre-review values:** exp114 repackages the 53 models on them.
- **The fairness floor's remaining gaps:** 8 jurisdictions below 0.8 for older households.
- **The language model:** whether a domain-tuned model helps reviewers in practice, not just on benchmarks.
