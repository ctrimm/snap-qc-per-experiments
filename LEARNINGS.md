# What we've learned so far

Plain-language synthesis across exp1–exp45 and the PA/NY POC tracks.
As of 2026-10-02. Details live in the per-experiment chronicles indexed in
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

## What's still open

Whether a language model trained on these fake cases actually reviews cases
better. The exp30 run now going is the first step: it checks that the eval
can measure that. The real test comes when a domain-tuned model goes through
it.
