# What this repo is — and what it is not

A short clarification, because the word "model" gets overloaded.

## What this repo is

A **synthetic data generator** for SNAP quality-control variance, calibrated
against federal QC public-use microdata (FY2020–2024), plus the experiments
that validate it. The generator produces synthetic household cases with
realistic error patterns: which cases have errors, what kind, which direction
(over/under), and how many dollars are involved. The experiments measure how
closely the synthetic output matches reality (calibration) and whether the
synthetic cases carry real predictive signal (transfer).

## The models we have trained so far

Small, classical machine-learning models — gradient-boosted decision trees,
a standard tabular-data algorithm, thousands of times smaller than a language
model. They are **diagnostic probes, not products**. Their job is the
transfer gate: train a probe *only* on synthetic cases, test it on real QC
cases it never saw. If it predicts real errors, the synthetic data carries
genuine signal; if it can't, the generator is producing plausible-looking
noise. That gate has held nationally and on Pennsylvania-only data.

The PA ranker from the Pennsylvania experiment set is the same idea pointed
at a product shape: a small tree-based ranker trained on PA-conditioned
synthetic cases, used to estimate review prioritization value. It is a
measurement of what a pilot could recover — not a deployed system.

## What this repo is not

It is **not** a domain-specific language model. No neural network has been
trained here. No model weights live in this repo, and none are planned for
it. The generator and the probes are classical all the way down.

## The domain LM: planned, not started

The small domain-specific language model — continued pretraining plus
fine-tuning of a 1.5–4B open-weight base on SNAP policy text and synthetic
QC-style cases — is the planned next build, not this one. Its data
prerequisites (the calibrated generator, the policy corpus) are what this
repo produces. Its cost and shape are scoped in `ESTIMATED_COSTS.md`; its
evaluation gates are the CalFresh MCQ benchmark and the QC-variance eval
pilot (`experiments/eval_pilot/`, awaiting a Mac Studio run).

In short: this repo builds and validates the **data**. The probes prove the
data is worth training on. The language model comes later.
