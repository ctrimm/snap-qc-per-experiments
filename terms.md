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
