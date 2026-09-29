# NY5 — dollar-impact ranking for the New York POC track

**Date:** 2026-09-29
**Status:** Complete — decision: **CONDITIONAL PASS**, see Verdict.
**Code:** `experiments/ny5_dollar_ranking.py`
**Deliverables (new files only; no existing file modified):**
- `experiments/ny5_dollar_ranking.py` — ranker training + top-k dollar evaluation
- `experiments/ny5_dollar_ranking.md` — this chronicle

## Hypothesis

A CIO cares about recovery per review hour, not classification accuracy. If
NY's synthetic signal transfers for dollars the way NY2 showed it transfers
for finding-rank, then ranking held-out real NY cases by expected error
dollars should recover meaningfully more dollars per review hour than random
review order. The open question is *which* ranking rule transfers best:
P(error) alone, a two-part P(error) x E[dollars|features], or a direct
expected-dollar model — and whether the synth-trained winner is anywhere near
a real-trained headroom. PA5's headline was that P(error)-only ranking was
*worse than random* at the top of the list; testing that surprise on NY's
different error mix is a named sub-goal.

## Method

**Holdout:** the shared `experiments/ny2_holdout_idx.json` (815 real NY
cases, 299 errors, **$22,871 total AMTERR**). Never touched during training.
NY2's fairness caveat carries over: NY1's generator offsets were fit on
pooled FY2020-2024 NY microdata including the holdout rows; NY8 quantified
the contamination premium at ~+0.02 on finding AUC and ~0 on element —
small but not zero.

**Models (NY2's recipe, clean features):** NY-conditioned synthetic, n=20,000,
seed 7 (`python3 -m src.synth.ny_state --n 20000 --seed 7 --dist
experiments/dist.json --out /tmp/ny45out/ny_synth.jsonl`; md5
`9cef4af3bd18f0436741aa1d329514c0`), clean-8 features per NY7 (no
`issued_benefit` — PA5's 9-feature recipe is deliberately not used),
`HistGradientBoostingClassifier(random_state=0)` without class_weight.
AMTERR is never an input feature; it is the evaluation target only. No
FYWGT is used (PA5 did not use it either).

**Ranking rules (all evaluated on the holdout):**
- (a) **P(error)-only:** a binary GBM on the NY synth (PA5's (a) structure),
  calibrated with isotonic regression on the real NY train split (2,442
  cases; isotonic won the CV-Brier choice 0.21772 vs Platt 0.22033, matching
  NY4's choice). Footnote: this is PA5's recipe, not NY4's exact 3-class
  model — the binary variant ranks slightly better on this holdout
  (calibrated AUC 0.6907 vs NY4's 3-class 0.6688), and using it keeps NY5
  structurally comparable to PA5.
- (b) **two-part:** calibrated P(error) x E[AMTERR|features], the dollar
  regressor a `HistGradientBoostingRegressor` trained on NY-synth *error*
  cases with a log1p(AMTERR) target (expm1 back-transform, clipped at 0).
- (c) **direct:** one `HistGradientBoostingRegressor` on *all* NY-synth
  cases, target log1p(AMTERR) (0 for correct cases) — a single expected-dollar
  model.
- (b-r)/(c-r) **headroom:** the same two-part and direct structures trained
  on the real NY train split via 5-fold ensembling. Not a product — the
  transfer ceiling.

**Metric:** for top-k = 10%/20%/30% of the holdout (k = 82/163/244), actual
dollars recovered = sum of AMTERR over reviewed cases (correct cases carry
$0), dollars-per-hour = recovered / (k x hours-per-case), vs a random-order
baseline (expectation: k x mean AMTERR). **Review-cost assumption: 30 minutes
per case** — a documented assumption, not a measured number; sensitivity at
15 and 60 minutes shown below.

**Reproduction:**
```bash
python3 -m src.synth.ny_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out /tmp/ny45out/ny_synth.jsonl
python3 experiments/ny5_dollar_ranking.py \
    --ny-synth /tmp/ny45out/ny_synth.jsonl \
    --qc-dir ~/workspace/snap-qc-data/raw \
    --holdout-json experiments/ny2_holdout_idx.json
```

## Results

### Headline: expected recovery per review hour (30-min assumption)

| rule | top-10% (k=82) | top-20% (k=163) | top-30% (k=244) |
|---|---|---|---|
| random baseline | $2,301 rec / $56/hr | $4,574 / $56/hr | $6,847 / $56/hr |
| (a) P(error)-only | $1,695 / **$41/hr** (0.74x) | $4,849 / $60/hr (1.06x) | $9,713 / $80/hr (1.42x) |
| (b) P(err) x synth-$ | $2,690 / $66/hr (1.17x) | $5,042 / $62/hr (1.10x) | $9,895 / $81/hr (1.45x) |
| **(c) direct synth-$** | **$2,847 / $69/hr (1.24x)** | **$6,958 / $85/hr (1.52x)** | **$12,905 / $106/hr (1.89x)** |
| (b-r) real two-part (headroom) | $7,461 / $182/hr (3.24x) | $12,727 / $156/hr (2.78x) | $14,496 / $119/hr (2.12x) |
| (c-r) real direct-$ (headroom) | $7,997 / $195/hr (3.48x) | $12,428 / $152/hr (2.72x) | $14,736 / $121/hr (2.15x) |

Lift = recovered dollars / random baseline. "rec" = actual AMTERR recovered.

### The winner, and the two NY divergences from PA5

**(c) direct wins among the transfer arms at every top-k** (lift
1.24x/1.52x/1.89x), capturing 12.4%/30.4%/56.4% of the holdout's $22,871 in
error dollars. This is the first divergence: in PA5 the *two-part* model won
everywhere (1.40x/1.58x/1.28x) and the direct model landed at/below random.
In NY the order flips — (b) manages only 1.17x/1.10x/1.45x. Mechanism: (b)
multiplies calibrated P(error) by a separately-trained E[dollars|error]
model; in NY's mix the P(error) factor drags the product toward NY's
high-frequency small-dollar timing errors (see below), while the direct
model (c) learns the feature→dollar mapping in one shot and reaches the
income-error tail. (b)'s top-163 list contains only 41 error cases against
(c)'s 76 — the two-part ranker spends most of its budget on cases it thinks
are likely errors that turn out small.

The **second result confirms PA5's surprise on NY**: (a) P(error)-only
ranking is **worse than random at top-10% (0.74x)** — actively anti-ranking
dollars — and barely above random at top-20% (1.06x). The mechanism is
visible in the oracle: ranking the holdout by *actual* dollars, the top 82
cases capture **78.6% of all error dollars** (top-20% captures 93.6%) and
are dominated by **earned income (30) and unearned income (14)** errors,
with shelter only 11 and sua 9, hhcomp 7. P(error) ranking chases NY's
high-frequency small-dollar timing errors — NY3: nature 97 at 62% of errors,
shelter/97 median $10, unearned/97 median $14 — while the dollars live in
income errors (NY3: earned/38 median $150, sua/53 median $115, dollar p90
$201). Probability of error and size of error are nearly orthogonal in NY's
mix, exactly as in PA. Do not rank by P(error) alone.

### Over/under split (top-20%, k=163)

| rule | over-$ recovered | under-$ recovered | over share |
|---|---|---|---|
| (c) synth direct | $4,751 | $2,207 | 68% |
| (c-r) real direct | $10,124 | $2,304 | 81% |

Recovered **over-issuance dollars are program savings**; recovered
**under-issuance dollars mean households were underpaid** — finding them is
the honest QC outcome, but it costs the program money to make the household
whole rather than recovering any. Framed as savings only, (c) at top-20%
yields **$58/hr of over-issuance recovery** at the 30-min assumption (vs
$56/hr total under random order). The headroom model again skews harder
toward over-issuances (81%) than the synth model (68%): the real
feature->dollar mapping knows big-dollar errors are overwhelmingly
over-issuances; the synth mapping only partly does.

### Review-cost sensitivity (rule (c), top-20%)

| min/case | (c) $/hr | random $/hr | marginal $/hr |
|---|---|---|---|
| 15 | $171 | $112 | +$59 |
| **30 (assumption)** | **$85** | **$56** | **+$29** |
| 60 | $43 | $28 | +$15 |

The **lift ratio (1.52x) is invariant to review cost**; absolute $/hr scales
inversely with it. At the 30-min assumption, reviewing the top 20% (163
cases, ~82 review-hours) recovers ~$7.0k vs ~$4.6k under random order — an
extra ~$2.4k, i.e. ~$29 of marginal recovery per review hour. Whether that is
operationally meaningful depends on reviewer loaded cost (not measured here).

### Expected-vs-actual (calibration check)

The rankers' own expected-dollar estimates vs actual recovered at top-20%:
(a) expected $6,113 vs actual $4,849 (overestimates); (b) expected $4,645
vs actual $5,042 (close, slight underestimate); (c) expected $4,208 vs
actual $6,958 (underestimates); headroom (b-r) expected $9,344 vs actual
$12,727, (c-r) $5,270 vs $12,428 (both underestimate). The log1p-target
regressors systematically underestimate the mean (Jensen's inequality, no
smearing correction) — a reporting caveat, not a ranking defect, since
expm1 is monotone. Do not quote these models' raw expected-dollar outputs as
point forecasts without a smearing correction.

## Verdict

**CONDITIONAL PASS — the transfer gate holds, but weakly, and the winner is
different than in PA.** Among the synth-transfer arms (c) is the clear
winner: the direct expected-dollar model beats the two-part model (which the
P(error) factor drags toward small-dollar timing errors) and beats
P(error)-only (which is worse than random at the top of the list) at every
top-k. But the transfer is thin: (c)'s 1.52x lift at top-20% is roughly half
of the real-trained headroom's 2.72x (and just over half its $/hr: $85 vs
$152). The binding constraint is the same one NY2/PA2 flagged — **the
generator's conditional feature→dollar mapping does not match real NY**;
the real-trained ranker captures 35% of all holdout error dollars in the top
10% of reviews while the synth ranker captures 12%.

**Verdict in plain numbers:** rank by (c), the direct synth-trained
expected-dollar model. At top-20% of cases reviewed and 30 minutes per
review, expect ~1.5x the dollars of random review order — about **$85
recovered per review hour vs $56/hr random, ~$29/hr of marginal value**
(~$2.4k extra per 163 reviews), capturing **30% of all error dollars**
($6,958 of $22,871). About 68% of recovered dollars will be
over-issuances (program savings); 32% will be under-issuances (households
owed). Do not rank by P(error) alone — it recovers *fewer* dollars than
random at the top of the list. The lift ratio does not depend on the
review-cost assumption; the $/hr figures halve at 60 min/case and double at
15.

**Honesty notes:** retrospective on QC-labeled cases — AMTERR is
reviewer-verified and includes the +/-$1 rounding tolerance; whether the
clean-8 features are available at prediction time in a live workflow is an
open question (the POC assumes agency-view facts are on hand when a review
is triaged). The synth arms carry NY2's holdout-contamination caveat,
quantified small by NY8 (~+0.02 on finding AUC). NY's dollar distribution is
fatter-tailed than PA's (p90 $201 vs $183; holdout mean $28.06 vs $23.63),
which is why random-baseline $/hr runs higher here ($56 vs $47).

## Next steps

- **For a production ranker, train the direct structure on real NY QC
  features** (the (c-r) recipe: expected-dollar regressor, 5-fold) — the
  POC's transferable asset is the ranking methodology, not the synth
  weights. The synth-trained (c) is a defensible cold-start ranker where
  real labels are unavailable, and it beats random by a real margin.
- **Smearing correction** for the log-target dollar regressors before any
  expected-dollar number is quoted to a stakeholder (currently biased low by
  up to ~40%).
- **Over-issuance-weighted ranking** as a follow-up: the headroom model's
  81%-over skew suggests a ranker trained with over-issuance dollars as the
  target (under-issuance dollars zeroed) would maximize the savings-relevant
  $/hr; evaluate whether the under-issuance recall cost is acceptable.
- The generator lever, if the synth path is pursued further: the dollar
  mechanisms reproduce NY's dollar *marginals* (p50 $29 vs $28) but not the
  feature→dollar conditional — NY3's income-error tail (earned/38, median
  $150; sua/53, median $115) is the specific conditional the generator needs
  to place on the right features.
