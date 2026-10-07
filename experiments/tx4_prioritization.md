# TX4 — Prioritization simulation: the SECOND DECISION POINT of the TX POC track

**Date:** 2026-10-03 · **Code:** `experiments/tx4_prioritization.py`

## Hypothesis

TX2 showed the TX-synth finding signal ranks error vs correct above chance
(binary AUC 0.688) but hard classification loses to majority. If that
ranking signal is operationally useful, a calibrated P(error) ranker should
let reviewers find more errors per hour than random review order — the
CIO-facing triage metric. Plain-language terms: AUC (a ranking metric where
0.5 is chance and 1.0 is perfect); precision@k = share of the top-k ranked
cases that are actually errors; lift = precision@k divided by the base error
rate; isotonic/Platt = two ways to recalibrate raw model scores into
honest probabilities (chosen by 5-fold cross-validation Brier score —
Brier = mean squared error of probability forecasts, lower is better).

## Method

Shared TX2 holdout (865 real TX cases, seed 20260929). Retrain TX2's best
finding arm exactly (TX-conditioned synthetic n=20k seed 7 + GBM without
class_weight, 3-class correct/over/under, clean 8-feature set per TX7 —
`issued_benefit` dropped as leakage). P(error) = 1 − P(correct).
Recalibrate the error-eager scores on the real-TX **train split** (2,592
rows, the holdout complement — never the holdout), choosing isotonic vs
Platt by 5-fold stratified CV Brier score. Score the holdout once, rank by
calibrated P(error). Report precision@k, lift vs random, and
errors-per-100-reviews at 10/20/30/40/50% review budgets; the cumulative-
gains shape; what the ranker catches (direction mix, AMTERR median vs
holdout-wide).

## Results

Calibration on the real-TX train split (n=2,592): raw AUC 0.7189; CV Brier
isotonic 0.20069 vs Platt 0.20328 — **isotonic chosen**; in-sample Brier
0.19797. Holdout (n=865, 383 errors, base rate 44.3%): raw AUC 0.6977,
calibrated AUC **0.6999** (calibration is monotone: identical ranking).
TX8 pristine reference: **0.6854** — the calibrated 0.6999 clears it, so
the contamination-adjusted gate passes.

| Review budget | Precision | Lift | Caught | Share of errors | Errors/100 reviews |
|---|---|---|---|---|---|
| Top 10% (n=86) | 0.546 | 1.23 | 47/383 | 12.3% | 54.7 (base 44.3) |
| Top 20% (n=173) | 0.572 | 1.29 | 99/383 | 25.9% | 57.2 |
| Top 30% (n=260) | 0.561 | 1.27 | 146/383 | 38.1% | 56.2 |
| Top 40% (n=346) | 0.584 | 1.32 | 202/383 | 52.7% | 58.4 |
| Top 50% (n=432) | 0.579 | 1.31 | 250/383 | **65.3%** | 57.9 |
| Top 100% | 0.443 | 1.00 | 383/383 | 100% | 44.3 |

The gains curve is flat-topped (like PA4/NY4): precision barely moves from
10% to 50% (0.55-0.58). The value is deprioritizing the safe half, not
targeting the riskiest few.

**What the ranker catches (top-20% cut):** 99 errors — 47 over / 52 under
(47.5%/52.5%, vs holdout-wide 49.9%/50.1% — no direction skew); median
AMTERR **$21 vs $30 holdout-wide** — the ranker skews toward *smaller*-
dollar errors (unlike NY4's $26 vs $30 no-skew finding). Mean $45, p90
$108.

## Verdict

**CONDITIONAL PASS — the ranking beats random review at every budget, but
TX's lifts are the weakest of the three state POCs.** (The condition is
now satisfied: TX8 quantifies the contamination premium at +0.003 on the
finding AUC — negligible — and the calibrated 0.6999 clears TX8's pristine
0.6854 reference.) In executive numbers:
Texas reviewers today find errors in about **44 of every 100** cases they
review (TX's base rate is the highest of the three states). In the model's
ranked order, the first 100 reviews turn up about **57 errors instead of
44 — thirteen more errors per hundred** (29% lift), and reviewing the
riskiest half catches **65% of all errors (250 of 383) with half the
reviews**. That is triage, not targeting: the top-10% list is right barely
half the time (0.546), so it cannot serve as a short high-confidence hit
list — not at AUC 0.70.

Two honest caveats for the CIO: (1) this is **retrospective ranking on
QC-labeled cases**, not a live deployment; (2) the numbers carry TX2's
holdout-contamination caveat, quantified by TX8 as **+0.003 on the
finding AUC** (0.688 contaminated vs 0.6854 pristine) — negligible, and
the calibrated 0.6999 clears the pristine 0.6854 reference, so the gate
fully passes.
Unlike NY4, the caught errors **do skew small-dollar** (median $21 vs $30)
— error-count gains overstate dollars-recovered gains, which is TX5's
problem to solve with dollar-aware ranking.

## Next steps

- **TX5** tests whether dollar-aware ranking (P(error)×E[dollars], direct
  expected-dollar) fixes the small-dollar skew and what it earns per
  review hour.
  - **Done →** [TX5](tx5_dollar_ranking.md): TX5: Conditional PASS (weak) — winner is (b) two-part P(error)×E[dollars] (PA-style, not NY's direct): top-20% $5,798 vs $4,634 random (1.25x; $67/hr vs $54/hr, 30-min review…
- **TX8** supplies the pristine AUC reference; if the contamination
  premium exceeds ~0.02, the lifts above are flattered and the gate
  revisits.
  - **Done →** [TX8](tx8_tx_pristine_rerun.md): TX8: PASS — the MIXED verdict is not a contamination artifact: pristine refit excluding all 865 holdout rows confirms finding edge, contamination premium +0.003 on finding AUC…
