# What this repo is, and what it is not

*Rewritten October 27, 2026. The September 29 version described an earlier stage: a synthetic-data generator with small diagnostic models, and a language model "planned, not started". All three parts have since been built and tested.*

## What this repo is

Research and working tools for **SNAP payment accuracy**, built from the federal QC public-use files (FY2020–2024, about 167,000 reviewed cases). It has three strands.

**1. Triage rankers: the deliverable.**
- **What they are:** a gradient-boosted model per jurisdiction (all 50 states, DC, Guam and the Virgin Islands), packaged in `deliverables/state_rankers/`.
- **What they do:** each scores cases by expected error dollars, so QC or second-party reviewers spend their hours where the dollars are. A state runs it on its own case records with `score_cases.py`.
- **What they learn:** the errors the official payment error rate counts, and only from information an agency has before review.
- **Fairness:** a fairness floor keeps older and disabled households' share of reviews in line with their share of errors.
- **Where the figures live:** the papers in `whitepaper/` (start with the project summary), the cost-share scenarios in `COST-SHARE-REPLICATE.md`, and a map dashboard.

**2. A synthetic-data generator and a QC language model: research.**
- **The generator:** calibrated against the real QC files, it produces realistic household cases with errors.
- **The model:** a small open model (Gemma 4 E4B, about 4 billion parameters), fine-tuned only on those synthetic cases, predicts real QC findings well above chance. It's a research result, not a product.
- **Flag cards:** short notes telling a reviewer why a case was flagged and what to check first. They are built from the rankers.

**3. Policy question answering: research.**
- **The benchmark:** open models answering SNAP policy questions, with and without a dated policy library and lookup tools, on Cornell's CalFresh quiz. The quiz is used for evaluation only.
- **The best result:** about 90% with Gemma 4 31B and policy lookup (`whitepaper/policy_qa_summary.pdf`).

## What it is not

- **Not a deployed system.** No state is running the rankers yet. Every figure comes from the public QC files, whose income and deduction fields are the reviewer's corrected values for error cases. Only a pilot on a state's own pre-review records can show real-world performance.
- **Not a decision-maker.** The tools prioritize and explain. Every determination stays with a reviewer.
- **Not a source of real case data.** QC microdata lives outside the repo (`../snap-qc-data/`) and is never committed. The CalFresh quiz's text and answers are never committed or trained on.

## How it got here, briefly

**September:**
- **The generator, and the first test of whether synthetic cases carry real signal.** They do.
- **State pilots on synthetic-trained rankers** (Pennsylvania, New York, Texas, South Dakota, Utah, Idaho).

**October:**
- **Rankers trained on real QC records** for all 53 jurisdictions.
- **The fine-tuned QC language model.**
- **Flag cards, and the policy-QA work.**

**October 26–27:**
- **An independent comparison exposed a leak** (Better Government Lab's snap_qc, exp106): our inputs paired the issued benefit with reviewer-corrected facts.
- **The models were rebuilt.** First without the leak (exp107), then on the official error definition (exp110–112).

The record of every experiment is the README index. `LEARNINGS.md` is the plain-language synthesis.
