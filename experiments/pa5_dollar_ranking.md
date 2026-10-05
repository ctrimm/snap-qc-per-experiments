# PA5 — dollar-impact ranking for the Pennsylvania POC track

**Date:** 2026-09-29
**Status:** Complete — decision: **CONDITIONAL PASS**, see Verdict.
**Code:** `experiments/pa5_dollar_ranking.py`
**Deliverables (new files only; no existing file modified):**
- `experiments/pa5_dollar_ranking.py` — ranker training + top-k dollar evaluation
- `experiments/pa5_dollar_ranking.md` — this chronicle

## Hypothesis

A CIO cares about recovery per review hour, not classification accuracy. If
PA's synthetic signal transfers for dollars the way PA2 showed it transfers
for element buckets, then ranking held-out real PA cases by expected error
dollars should recover meaningfully more dollars per review hour than random
review order. The open question is *which* ranking rule transfers best:
P(error) alone, a two-part P(error) x E[dollars|features], or a direct
expected-dollar model — and whether the synth-trained winner is anywhere near
a real-trained headroom.

## Method

**Holdout:** the shared `experiments/pa2_holdout_idx.json` (817 real PA
cases, 349 errors, $19,303 total AMTERR). Never touched during training.
PA2's fairness caveat carries over: PA1's generator offsets were fit on
pooled FY2020-2024 PA microdata including the holdout rows, so the synth arms
are not pristine with respect to the test set; the advantage is small (pooled
marginals only, not test labels) but not zero.

**Models (PA2's recipe):** PA-conditioned synthetic, n=20,000, seed 7
(`cd src && python3 -m synth.pa_state --n 20000 --seed 7 --dist
../experiments/dist.json --out /tmp/pa5out/pa_synth.jsonl`), v1 features,
`HistGradientBoostingClassifier(random_state=0)` without class_weight.
AMTERR is never an input feature; it is the evaluation target only.

**Ranking rules (all evaluated on the holdout):**
- (a) **P(error)-only:** the PA2 classifier's P(error), calibrated with
  isotonic regression on the real PA train split (2,451 cases). Calibrated
  holdout AUC 0.68 (PA2 reported 0.645; same ranker, seed noise).
- (b) **two-part:** calibrated P(error) x E[AMTERR|features], the dollar
  regressor a `HistGradientBoostingRegressor` trained on PA-synth *error*
  cases with a log1p(AMTERR) target (expm1 back-transform, clipped at 0).
- (c) **direct:** one `HistGradientBoostingRegressor` on *all* PA-synth
  cases, target log1p(AMTERR) (0 for correct cases) — a single expected-dollar
  model.
- (b-r)/(c-r) **headroom:** the same two-part and direct structures trained
  on the real PA train split via 5-fold ensembling. Not a product — the
  transfer ceiling.

**Metric:** for top-k = 10%/20%/30% of the holdout (k = 82/163/245), actual
dollars recovered = sum of AMTERR over reviewed cases (correct cases carry
$0), dollars-per-hour = recovered / (k x hours-per-case), vs a random-order
baseline (expectation: k x mean AMTERR). **Review-cost assumption: 30 minutes
per case** — a documented assumption, not a measured number; sensitivity at
15 and 60 minutes shown below.

**Reproduction:**
```bash
cd src && python3 -m synth.pa_state --n 20000 --seed 7 \
    --dist ../experiments/dist.json --out /tmp/pa5out/pa_synth.jsonl
python3 experiments/pa5_dollar_ranking.py \
    --pa-synth /tmp/pa5out/pa_synth.jsonl \
    --qc-dir ../snap-qc-data/raw \
    --holdout-json experiments/pa2_holdout_idx.json
```

## Results

### Headline: expected recovery per review hour (30-min assumption)

| rule | top-10% (k=82) | top-20% (k=163) | top-30% (k=245) |
|---|---|---|---|
| random baseline | $1,937 rec / $47/hr | $3,851 / $47/hr | $5,789 / $47/hr |
| (a) P(error)-only | $836 / **$20/hr** (0.43x) | $2,379 / $29/hr (0.62x) | $5,989 / $49/hr (1.03x) |
| **(b) P(err) x synth-$** | **$2,708 / $66/hr (1.40x)** | **$6,074 / $75/hr (1.58x)** | **$7,403 / $60/hr (1.28x)** |
| (c) direct synth-$ | $2,056 / $50/hr (1.06x) | $3,479 / $43/hr (0.90x) | $4,923 / $40/hr (0.85x) |
| (b-r) real two-part (headroom) | $9,686 / $236/hr (5.00x) | $12,124 / $149/hr (3.15x) | $14,210 / $116/hr (2.46x) |
| (c-r) real direct-$ (headroom) | $9,023 / $220/hr (4.66x) | $11,798 / $145/hr (3.06x) | $13,430 / $110/hr (2.32x) |

Lift = recovered dollars / random baseline. "rec" = actual AMTERR recovered.

### The winner and the surprise

**(b) wins among the transfer arms at every top-k** (lift 1.40x/1.58x/1.28x),
capturing 14%/32%/38% of the holdout's $19,303 in error dollars. The
**surprise is (a): P(error)-only ranking is worse than random at top-10%
(0.43x)** — actively anti-ranking dollars. The mechanism is visible in the
oracle: ranking the holdout by *actual* dollars, the top 82 cases capture
73.6% of all error dollars and are dominated by **earned income (25) and
unearned income (14)** errors, with shelter only 20. P(error) ranking chases
PA's high-frequency small-dollar shelter errors (PA3: shelter timing median
$9) while the dollars live in income errors (PA3: newly-employed wages median
$258). Probability of error and size of error are nearly orthogonal in PA's
mix, so a pure P(error) ranker finds errors the program cannot profitably
chase. The direct model (c) splits the difference and lands at/below random
at 20%+.

### Over/under split (top-20%, k=163)

| rule | over-$ recovered | under-$ recovered | over share |
|---|---|---|---|
| (b) synth two-part | $4,239 | $1,835 | 70% |
| (b-r) real two-part | $10,372 | $1,752 | 86% |

Recovered **over-issuance dollars are program savings**; recovered
**under-issuance dollars mean households were underpaid** — finding them is
the honest QC outcome, but it costs the program money to make the household
whole rather than recovering any. Framed as savings only, (b) at top-20%
yields $52/hr of over-issuance recovery at the 30-min assumption (vs $47/hr
total under random order). Note the headroom model skews much harder toward
over-issuances (86%) than the synth model (70%): the real feature->dollar
mapping knows big-dollar errors are overwhelmingly over-issuances; the synth
mapping only partly does.

### Review-cost sensitivity (rule (b), top-20%)

| min/case | (b) $/hr | random $/hr | marginal $/hr |
|---|---|---|---|
| 15 | $149 | $95 | +$54 |
| **30 (assumption)** | **$75** | **$47** | **+$28** |
| 60 | $37 | $24 | +$14 |

The **lift ratio (1.58x) is invariant to review cost**; absolute $/hr scales
inversely with it. At the 30-min assumption, reviewing the top 20% (163
cases, ~82 review-hours) recovers ~$6.1k vs ~$3.9k under random order — an
extra ~$2.2k, i.e. ~$28 of marginal recovery per review hour. Whether that is
operationally meaningful depends on reviewer loaded cost (not measured here):
the ranking's marginal value is roughly half a reviewer's hourly cost in most
plausible ranges, on top of a review process that already pays for itself.

### Expected-vs-actual (calibration check)

The rankers' own expected-dollar estimates vs actual recovered at top-20%:
(b) expected $3,387 vs actual $6,074 (underestimates); (c) expected $4,782 vs
actual $3,479 (overestimates); headroom (b-r) expected $8,444 vs actual
$12,124 (underestimates). The log1p-target regressors systematically
underestimate the mean (Jensen's inequality, no smearing correction) — a
reporting caveat, not a ranking defect, since expm1 is monotone. Do not quote
these models' raw expected-dollar outputs as point forecasts without a
smearing correction.

## Verdict

**CONDITIONAL PASS — the transfer gate holds, but weakly.** Among the
synth-transfer arms (b) is the clear winner: P(error) x E[dollars|features]
beats P(error)-only (which is worse than random at the top of the list) and
beats the direct expected-dollar model at every top-k. But the transfer is
thin: (b)'s 1.58x lift at top-20% is roughly a third of the real-trained
headroom's 3.15x (and a third of its $/hr: $75 vs $149). The binding
constraint is the same one PA2 flagged on the finding task — **the
generator's conditional feature->dollar mapping does not match real PA**;
the real-trained ranker captures 50% of all holdout error dollars in the top
10% of reviews while the synth ranker captures 14%.

**Verdict in plain numbers:** rank by (b), calibrated P(error) x
synth-trained E[dollars|features]. At top-20% of cases reviewed and 30
minutes per review, expect ~1.6x the dollars of random review order — about
$75 recovered per review hour vs $47/hr random, ~$28/hr of marginal value
(~$2.2k extra per 163 reviews). About 70% of recovered dollars will be
over-issuances (program savings); 30% will be under-issuances (households
owed). Do not rank by P(error) alone — it recovers *fewer* dollars than
random at the top of the list. The lift ratio does not depend on the review-
cost assumption; the $/hr figures halve at 60 min/case and double at 15.

**Honesty notes:** retrospective on QC-labeled cases — AMTERR is
reviewer-verified and includes the +/-$1 rounding tolerance; whether the v1
features are available at prediction time in a live workflow is an open
question (the POC assumes agency-view facts are on hand when a review is
triaged). The synth arms carry PA2's holdout-contamination caveat (small).

## Next steps

- **For a production ranker, train the two-part structure on real PA QC
  features** (the (b-r) recipe: P(error) x E[AMTERR|features], 5-fold) — the
  POC's transferable asset is the ranking methodology, not the synth weights.
  The synth-trained (b) is a defensible cold-start ranker where real labels
  are unavailable, and it beats random by a real margin.
- **Smearing correction** for the log-target dollar regressors before any
  expected-dollar number is quoted to a stakeholder (currently biased low by
  ~40%).
- **Over-issuance-weighted ranking** as a follow-up: the headroom model's
  86%-over skew suggests a ranker trained with over-issuance dollars as the
  target (under-issuance dollars zeroed) would maximize the savings-relevant
  $/hr; evaluate whether the under-issuance recall cost is acceptable.
- The generator lever, if the synth path is pursued further: the dollar
  mechanisms reproduce PA's dollar *marginals* but not the feature->dollar
  conditional — PA3's income-error tail (newly-employed wages, median $258)
  is the specific conditional the generator needs to place on the right
  features.
