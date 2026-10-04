# Cross-state synthesis: six-state POC panel (2026-10-04)

What six independent state tracks (PA, NY, TX, SD, ID, UT) jointly establish — and what they overturn.

## The panel at a glance

| State | Verdict | Finding AUC (pristine vs national) | Element transfer | Winning ranker (top-20%) | $/hr vs random | One-line anatomy |
|---|---|---|---|---|---|---|
| PA | Validated w/ conditions | 0.691 (PA8) | +0.026 acc vs national, holds pristine | Two-part P(err)×E[$] | $67 vs $47 (1.42x) | Deduction-construction: shelter ~2x national; clean engine (0.12x computation) |
| NY | Validated w/ conditions | 0.626 vs 0.611 (+0.016, 3/3 seeds) | Loses to national (rare medical/SUA tail) | Direct expected-dollar | $85 vs $56 (1.52x) | Timing: nature-97 62% of errors (1.56x); medical 1.79x (1.27x ex-pandemic) |
| TX | MIXED | 0.688 vs 0.670 (2/6 seeds) | Loses (0.407 vs 0.441; coding practice, structural) | Two-part | $67 vs $54 (1.25x, weakest) | "Other"-coding: nature-99 4.28x, shelter×99 4.45x; agency causes 58% |
| SD | Validated | 0.750 vs 0.680 (+0.071, best) | macroF1 0.277 vs 0.176 | P(error)-alone | $45 vs $22 (2.07x) | Most timing-heavy: nature-97 74.9% (1.89x); zero computation variances |
| ID | Mixed transfer, validated economics | +0.017 (noise) / element +0.054 | Passes on element | P(error)-alone | $31 vs $22 (1.40x; 1.77x at top-10%) | Timing-97 1.57x + shelter 1.40x; client-caused 1.66x |
| UT | Validated | 0.728 vs 0.678 (+0.050, 6/6) | Marginal pass | Two-part | $45 vs $26 (1.70x) | Wage-timing: earned×97 1.95x; shelter×53-over 2.21x |

## Finding 1: there is no universal ranking rule (refined)

PA→two-part, NY→direct-dollar, TX→two-part, SD→P-alone, ID→P-alone, UT→two-part. The rule follows each state's **error economics**, and the six-state panel pins the mechanism:

- **No dollar tail → P(error)-alone wins** (SD p90 $70, ID p90 $87). Where every error is small, multiplying a good P(error) by a miscalibrated E[dollar] only adds noise. ID is the extreme: two-part is *worse than random* at top-10% (0.61x, $14/hr).
- **Dollar tail present → dollar ranker wins, even at low PER** (UT: oracle top-20% of cases holds 93% of all error dollars; two-part 1.70x while P-alone manages 1.08x). Low payment-error rate alone does not imply the reversal.

P(error)-alone vs random at top-10%: PA 0.43x, NY 0.74x, TX 0.98x (three confirmations it can lose), SD/ID wins (2.07x/1.77x). The pilot implication: **re-derive the ranking rule per state from a short calibration run**; do not inherit it.

## Finding 2: the fairness caveat is scoped, not general

Risk-regressivity (elderly/disabled under-reviewed relative to error risk) is a property of **dollar-maximizing rankers**, confirmed at full strength in UT (review-to-risk 0.155 for elderly/disabled at top-20%) and absent-to-mild under P-alone (ID's P-alone winner is ~2x more proportional: 0.54–0.57x vs 0.22–0.35x under dollar rankers). Two mitigations now exist: per-type review floors (free — exp49: no $/hr cost, precision rises), and choosing a ranker that doesn't create the problem. Whitepapers should require the type-stratified burden analysis as a Phase-1 gate.

## Finding 3: transfer holds across the panel, with state-specific limits

State-conditioned synthetic beats national or baseline on the finding task in 5 of 6 states (TX the honest exception at 2/6 seeds). The *limits* differ by state, which is itself a finding: NY loses element on the rare medical/SUA tail the generator can't place; TX loses on coding practice unlearnable from agency-view features; ID's finding edge is noise while its element edge is real. The generator's failure modes are state-specific, not a single story — falsification is working as designed.

## Finding 4: the low-PER panel answers the rare-error question

SD (3.28% FY2024) and ID (3.85% FY2025) show transfer and ranking both hold where errors are rare — but UT (5.54%) shows the operative variable is the dollar tail, not the rate. "Does this work in well-run states?" → yes, with the ranker matched to the tail.

## Standing notes for future tracks

- Re-derive the ranking rule per state (all three structures + the winner); never inherit.
- Run the household-type burden analysis for the winning ranker as a Phase-1 gate.
- Stratify cause-mix work by FY — TX and UT both had FY2024 labeling breaks on timing-97 causes.
- Fit basis FY2022–24 (exclude partial FY2020–21) unless a state shows otherwise.
