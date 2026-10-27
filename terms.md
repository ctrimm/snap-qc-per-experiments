# Glossary

Terms as used in this repo's experiments. Evaluation metrics first, then
domain and generator vocabulary.

## Evaluation metrics

- **L1 distance** — how far apart two distributions are. Sum over categories
  of the absolute difference between real and synthetic shares. Example:
  real finding mix 0.603 / 0.239 / 0.158 vs synthetic 0.604 / 0.235 / 0.161
  gives L1 = 0.001 + 0.004 + 0.003 = 0.009. Lower is better; 0 means
  identical. Intuition: the total probability mass you'd have to move to
  make the distributions match.
- **Accuracy** — fraction of predictions exactly right. Simple but
  misleading under class imbalance (always guessing the majority class can
  score high while learning nothing).
- **Precision** — of the cases the model flagged as X, how many truly were
  X. Punishes false alarms.
- **Recall** — of the cases that truly were X, how many the model caught.
  Punishes misses.
- **F1 score** — harmonic mean of precision and recall (2·P·R / (P+R)).
  A single number that punishes cheating on either side: flagging everything
  gives great recall but terrible precision, and F1 lands low. 0 to 1,
  higher is better.
- **Macro F1** — F1 computed separately per class, then plain-averaged.
  Treats rare classes equally, so a model that nails the common class but
  ignores rare error types gets punished. The headline metric for
  element/nature classification transfer.
- **AUC** (area under the ROC curve) — probability the model ranks a
  randomly chosen positive case above a randomly chosen negative one.
  0.5 is a coin flip, 1.0 is perfect. Used for the binary error/no-error
  transfer test.

## QC domain

- **Finding** — a case's review outcome: *correct* (no reportable error),
  *over-issuance* (household got too much), *under-issuance* (too little).
  The top-level calibration target.
- **Variance** — a single recorded error on a case: an (element, nature,
  cause, direction, dollar amount) tuple. A case can carry more than one.
- **Element** — *what* was wrong: earned income, unearned income, shelter
  deduction, SUA, medical deduction, household composition, etc.
- **Nature** — *how* it was wrong, as a QC code (e.g. 53 = income included
  when it shouldn't be, 52 = deduction omitted, 97 = timing error).
- **Cause** — *who* is responsible: agency error, client error, etc.
- **Direction** — over, under, or neither, derived from the dollar effect.
- **Reportable** — whether a variance counts toward the official error
  rate (small-dollar errors may not).
- **Realized error rate** — fraction of synthetic cases with at least one
  reportable variance. Calibrated to the real file's 0.397.

## Ranker and cost-share terms (October 2026)

- **Ranker** — a per-state model that scores each case by expected error dollars (chance of an error × likely dollars) so reviewers work the highest-scoring cases first. Packaged in `deliverables/state_rankers/`.
- **Lift** — dollars found by reviewing the top of the ranked queue, divided by what the same number of randomly chosen cases would find. "Top-20% lift 3.0×" means the top fifth of the queue holds three times the error dollars of a random fifth.
- **Dollar recall** — share of all error dollars caught at a given review budget (e.g. 5% or 10% of cases). giannella/snap_qc's main dollar metric.
- **Review budget** — the share of the caseload a state can review (5% or 10% in comparisons).
- **Federal tolerance (error threshold)** — the dollar amount below which a payment error doesn't count toward the official payment error rate: $56 in FY2024 ($38 FY2017, $37 FY2018–19, $38 FY2020, $39 FY2021, $48 FY2022, $54 FY2023).
- **Official error** — the rankers' training label since exp112 (`SNAPQC_LABEL=official`): an error the QC reviewer found (STATUS 2 or 3) whose amount (AMTERR) is above the tolerance. About 10–12% of cases a year.
- **Any error** — every error the reviewer found, however small (about 38% of cases); the label before exp110, kept as `SNAPQC_LABEL=any`.
- **Benefit gap** — |issued benefit − correct benefit| (RAWBEN − FSBEN). Not used as a label: about 30% of over-tolerance gaps contradict the reviewer's recorded error (exp112).
- **Reviewer-recorded values** — the QC file's "reported" fields (RAWGROSS, RAWNET, SHELDED, …) are what the reviewer recorded; for error cases, the corrected facts.
- **Leak / leak-free** — the October 26 finding (exp106) that pairing those values with the issued benefit let models see the error. Leak-free inputs (`SNAPQC_FEATURES=leakfree`, the default) leave the issued benefit out.
- **Rebuilt pre-review inputs** — giannella/snap_qc's reconstruction of what the agency had before review: start from the reviewer's values and shift the field in error until the formula gives the issued benefit (exp109, exp113).
- **Fairness floor** — a review-budget rule giving each household type (elderly, disabled, single parent, …) a share of reviews in line with its share of errors, then ranking by dollars within each type.
- **Review ratio** — a household type's share of reviews ÷ its share of errors; 1.0 means reviewed in proportion to risk.
- **Cost share (H.R. 1)** — from FY2028, states with payment error rates of 6% or more pay 5%, 10% or 15% of benefit costs depending on the rate band. "Cost share avoided" is the scenario estimate of how much ranked reviews could lower that bill.
- **Pooled model** — trained on every state's QC cases (plus the state's own maximum allotment), as opposed to state-only.
- **Holdout / later-years test** — cases set aside before training (25% per state), and a model trained on FY2020–22 tested on FY2023–24.

## Generator internals

- **Retry loop** — the original injection design: draw a bucket, draw a
  nature, apply the corruption; if the benefit doesn't move, redraw and try
  again (up to a cap). Creates selection bias: always-materializing buckets
  win the redraw lottery (exp 7).
- **Materialize** — a corruption counts only if it moves the computed
  benefit. Many don't (e.g. raising a shelter deduction already at the cap).
- **Attrition** — injected variances lost because they never materialize,
  or because the retry budget exhausts. Phase-1 coins correct for it.
- **Effectiveness (eff_b, m_d)** — P(a corruption moves the benefit |
  bucket), and P(moves | bucket, direction-class). Measured in
  `measure_effectiveness.py`, stored in `eff.json`.
- **Importance weights** — draw-time corrections (w ∝ 1/m) so the
  *recorded* mix matches the empirical mix despite differential
  materialization. Applied per bucket (1/eff_b) and per direction class
  (`dir_weight`).
- **Phase-1 / phase-2 coins** — calibrated probabilities in `inject.json`.
  Phase 1: per-stratum (earner / no-earner) coin deciding whether a case gets
  any variance. Phase 2: per-bucket coins resolving direction-ambiguous
  nature 97 into an over- or under-issuance.
- **Single-draw-and-drop** — the exp-7 persistent mode: the bucket is drawn
  once per variance and never redrawn; if the corruption doesn't
  materialize the variance is dropped, not retried.
