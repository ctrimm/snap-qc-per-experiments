# Experiment 35 — discriminator diagnostic: where does the generator look synthetic?
**Date:** 2026-09-29 · **Code:** `experiments/exp35_discriminator_diagnostic.py`

### Hypothesis
A synthetic-vs-real classifier (the *discriminator*) separates best on
specific feature slices, revealing generator blindspots that marginal
checks miss. Ties to the **calibration gate**: if the discriminator is
near chance everywhere, the generator's joint distribution is faithful;
where it separates, the generator is detectably off.

### Method
- **Data:** 20k synthetic cases, `seed 7`, current default generator
  (persistent-bucket mode), generated with
  `python3 -m synth.generate --n 20000 --seed 7 --dist ../experiments/dist.json --out /tmp/exp35_synth.jsonl`.
  Real side: FY2024 QC public-use file only (same test population as
  exp4/exp19; pooling FY2020-2024 would mix in year-to-year policy
  shifts). 44,891 real rows + 20,000 synth rows.
- **Features:** shared v2 recipe from exp4/exp19 (19 features: raw facts +
  gross/net income, gap to max allotment, benefit fraction, review month,
  elderly/disabled counts, earned/unearned flags, earned share).
- **Model:** label synth=0, real=1; stratified 70/30 split
  (train 45,423 / test 19,468, real rate 0.692). Primary:
  `HistGradientBoostingClassifier` (GBM — an ensemble of decision trees,
  `random_state=0`); secondary: logistic regression (a linear classifier)
  on standardized features. Metric: **AUC** (terms.md: probability the
  model ranks a random real case above a random synth case; 0.5 = coin
  flip, 1.0 = perfect).
- **Slices:** element bucket (first variance; "correct" for clean cases),
  dollar-error band (zero / small <=$56 / large >$56; synth total from the
  case-level `dollar_error`, real from `|AMTERR|`), household type
  (earner vs non-earner; senior/disabled vs neither).
- **Importance:** GBM permutation importance on test (AUC drop when a
  feature is shuffled; big drop = the model relies on it) + LR
  standardized |coefficient| ranking.
- **Reproducibility (recorded by the script at run time):**
  `git rev-parse HEAD` = `411ddd761f1bc24f1709c434a42c1b8ea948956a`;
  `git status --short` = `M experiments/inject.json | M src/synth/dollar_mech.py
  | M src/synth/errors.py | M src/synth/household.py | ?? experiments/eval_pilot/
  | ?? experiments/exp26_combine_dollar.md | ... | ?? experiments/exp35_discriminator_diagnostic.py
  | ?? experiments/exp36_transfer_scaling.py | ?? experiments/exp37_transfer_model_classes.py
  | ?? experiments/exp40_published_rate_calibration.py | ?? experiments/exp41_policy_qa_bridge.md
  | ?? experiments/exp41_policy_qa_bridge.py` (other researchers' files
  in flight; src/ untouched by this experiment). Note: HEAD moved from
  `f515930` to `411ddd7` between session start and the run (another
  researcher committed); all numbers below are from the run at `411ddd7`.
  One script bug was found and fixed between runs: the synth dollar band
  first summed a nonexistent per-variance field (all error cases landed
  in "zero"); the fix uses the case-level `dollar_error`. Final numbers
  are from the fixed run.

### Results
Headline: the discriminator is **far from chance**. GBM test AUC 0.981,
LR test AUC 0.869 — the generator is highly detectable, and the
separation is largely nonlinear (GBM >> LR).

| model | test AUC |
|---|---|
| GBM (trees) | 0.981 |
| Logistic regression | 0.869 |
| Chance | 0.500 |

Slice AUCs (GBM; "P(real|syn)" = mean predicted real-probability for
synth rows in the slice — low means the model confidently calls them
synthetic):

| element bucket | n_syn | n_real | GBM AUC | LR AUC | P(real|syn) | P(real|real) |
|---|---|---|---|---|---|---|
| sua | 232 | 285 | 0.998 | 0.918 | 0.158 | 0.980 |
| shelter | 824 | 1,680 | 0.997 | 0.948 | 0.132 | 0.977 |
| medical | 77 | 221 | 0.995 | 0.914 | 0.141 | 0.963 |
| hhcomp | 90 | 175 | 0.993 | 0.859 | 0.198 | 0.972 |
| earned | 529 | 1,511 | 0.993 | 0.924 | 0.145 | 0.954 |
| depcare | 49 | 69 | 0.992 | 0.970 | 0.153 | 0.945 |
| unearned | 554 | 1,126 | 0.981 | 0.842 | 0.257 | 0.950 |
| correct | 3,596 | 8,166 | 0.974 | 0.846 | 0.181 | 0.894 |
| arithmetic | 49 | 90 | 0.943 | 0.901 | 0.288 | 0.922 |

| dollar band | n_syn | n_real | GBM AUC | LR AUC | P(real|syn) | P(real|real) |
|---|---|---|---|---|---|---|
| large (>$56) | 1,556 | 1,605 | 0.995 | 0.895 | 0.177 | 0.978 |
| small (<=$56) | 848 | 3,697 | 0.991 | 0.933 | 0.165 | 0.955 |
| zero (correct) | 3,596 | 8,166 | 0.974 | 0.846 | 0.181 | 0.894 |

| household slice | n_syn | n_real | GBM AUC | LR AUC |
|---|---|---|---|---|
| earner | 1,609 | 3,647 | 0.989 | 0.911 |
| non-earner | 4,391 | 9,821 | 0.977 | 0.853 |
| senior/disabled | 2,221 | 6,709 | 0.989 | 0.932 |
| neither | 3,779 | 6,759 | 0.972 | 0.811 |

Coverage gaps — real buckets the generator never emits (no synth
counterpart; AUC undefined, shown is GBM's mean P(real) on real rows):

| bucket | n_real (test) | P(real|real) |
|---|---|---|
| other | 73 | 0.921 |
| childsupport | 32 | 0.982 |
| unknown | 17 | 0.942 |
| standard | 14 | 0.989 |
| reporting | 6 | 0.983 |
| income_total | 2 | 0.855 |
| assets | 1 | 0.979 |

Top distinguishing features:

| GBM permutation importance (test AUC drop) | drop |
|---|---|
| shelter | +0.301 |
| gross | +0.108 |
| net | +0.106 |
| gap_to_max | +0.084 |
| unearned | +0.041 |
| senior_disabled | +0.023 |
| sua | +0.013 |
| medical_exp | +0.008 |

| LR standardized coefficient | coef |
|---|---|
| issued_benefit | -4.07 |
| hh_size | +3.99 |
| n_elderly | +3.28 |
| senior_disabled | -2.93 |
| net | -2.85 |
| n_disabled | +2.77 |
| gap_to_max | -2.69 |
| shelter | -2.19 |

### Verdict
Hypothesis holds, emphatically: the discriminator separates at 0.981,
and the blindspots rank cleanly. Ranked findings:

1. **Shelter deduction modeling is the biggest leak.** Shelter is the
   single strongest distinguishing feature (shuffling it alone drops AUC
   by 0.30), and shelter-error cases are near-perfectly separable (0.997).
2. **The income/benefit accounting identity is off.** Gross, net,
   gap_to_max, issued_benefit dominate both importance lists. These are
   mechanically linked, and for synth they are recomputed exactly from
   agency-view facts via `benefit.compute`, while real values carry
   recording noise (rounding, timing, policy quirks). Part of the 0.981
   may be "real data is messy, synth is exactly self-consistent" —
   a feature-recipe artifact, not pure generator infidelity.
3. **Large-dollar errors are the most detectable error slice** (0.995),
   then small (0.991), then correct cases (0.974). The error-size
   footprint is worst in the tail.
4. **Seven real element buckets have zero synth representation**
   (other, childsupport, standard, reporting, income_total, assets,
   unknown — 145 test rows). A pure coverage blindspot.
5. **Stratum conditioning is uneven:** earner (0.989) and
   senior/disabled (0.989) cases are more detectable than non-earner
   (0.977) / neither (0.972) — the generator's conditional facts are
   further off for exactly the strata the phase-1 coins stratify on.
6. **Even clean ("correct") cases separate at 0.974.** The clean-facts
   generator (household.py) itself differs from real households — this
   is not only about error injection.
7. Least detectable in-bucket: **arithmetic (0.943)** — the most
   faithful error mechanism; worth studying as the positive example.

Caveats: the 0.981 includes population mix differences (dist.json fit
mix vs FY2024 mix), not only conditional infidelity — in-slice AUCs are
the cleaner read. Deeper slices (depcare/medical/arithmetic) have small
n; treat their exact ranks as noisy.

### Next steps
1. **(recommended)** v1-vs-v2 discriminator ablation: retrain on the 9
   raw features only. If AUC collapses toward chance, the 0.981 is
   mostly the derived-feature consistency artifact (finding 2) and the
   fix belongs in the feature recipe / benefit recomputation, not the
   generator. If it stays high, the leak is in the raw facts.
2. Shelter deep-dive: compare the generator's shelter marginal, cap
   behavior, and shelter|income joint against real FY2024 (dist.json
   audit; follows exp16/exp18).
3. Large-error tail audit: compare dollar_mech's >$56 distribution shape
   vs real AMTERR tail (exp18 follow-up).
4. Coverage decision: extend the generator to emit the 7 missing
   buckets, or document them as out of scope — either way stop silently
   dropping them.
5. Per-stratum discriminator on earner and senior/disabled rows to
   localize which facts the stratum conditioning gets wrong.
6. Real-data consistency check: recompute gross/net/benefit from real
   recorded facts and measure how often they disagree with the file's
   FSGRINC/FSNETINC/RAWBEN — quantifies how much of finding 2 is real
   messiness the generator should replicate.
