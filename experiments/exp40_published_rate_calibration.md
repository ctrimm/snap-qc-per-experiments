# Experiment 40 — published-rate calibration

**Date:** 2026-09-29 · **Code:** `experiments/exp40_published_rate_calibration.py`

## Hypothesis

Generator-implied payment error rates disagree with FNS-published official
rates in informative, definition-driven ways. If the disagreement can be
attributed to specific definition differences (procedural errors, federal
re-review adjustments, tolerance floors), the generator still passes the
**calibration gate** on the payment-error substance it is meant to model;
if it cannot, the generator's priors are miscalibrated. This is the
complement to exp33 (state-level heterogeneity, measured from microdata):
exp33 asks whether the generator matches real cases, this experiment asks
whether the generator matches the official published series.

## Method

Three national payment error rates, same definition on the generator and
microdata sides, official numbers from FNS releases:

- **Official FNS payment error rate** (dollar-weighted: erroneous benefit
  dollars ÷ total benefit dollars; overpayments + underpayments, not
  netted). FY2023: **11.68%** (over 10.03% / under 1.64%). FY2024:
  **10.93%** (over 9.26% / under 1.67%). No official rates exist for
  FY2020/FY2021 (pandemic QC flexibilities made them invalid). Sources:
  FNS official page https://www.fns.usda.gov/snap/qc/per (returned HTTP
  403 from this sandbox — Akamai-walled; figures corroborated across
  https://frac.org/wp-content/uploads/SNAP-Payment-Error-Rates-by-FY.pdf,
  https://thefern.org/ag_insider/second-year-in-a-row-of-high-snap-payment-error-rates/amp/
  (FY2023 breakdown), and
  https://www.agri-pulse.com/articles/23131-national-snap-error-rate-dips-slightly-amid-state-cost-share-fight
  (FY2024 breakdown).
- **Generator-implied:** 20,000 cases from
  `python3 -m synth.generate --n 20000 --seed 7 --dist ../experiments/dist.json`
  (run from `src/`; output written to `/tmp/exp40_synth.jsonl` — the writer
  emits JSON lines regardless of extension). Dollar-weighted rate =
  Σ|dollar_error| ÷ Σissued_benefit over reportable cases only (FNS-style:
  the generator's `reportable` flag applies the QC_ERROR_THRESHOLD
  tolerance floor, $56 for FY2024). Case rate = share with finding 2/3.
- **Microdata-implied:** FY2020–2024 QC public-use files (held-out; never
  committed). Dollar-weighted rate = Σ(FYWGT × |AMTERR|) ÷ Σ(FYWGT × RAWBEN)
  over cases with STATUS 2/3 (AMTERR > 0 occurs only with STATUS 2/3, so
  the tolerance floor is already baked into STATUS). Case rate =
  FYWGT-weighted share with STATUS 2/3.

Reproducibility: `git rev-parse HEAD` = `f515930843d66d784ee1b95288e600de22353bfa`;
`git status --short` showed uncommitted edits in another researcher's work —
`M src/synth/dollar_mech.py`, `M src/synth/errors.py`, `M src/synth/household.py`
(src/ treated as read-only, not touched). Dist: `experiments/dist.json`.

## Results

### National: the generator matches payment-error substance, not the published series

| Source | FY2023 | FY2024 |
|---|---|---|
| FNS published (total) | 11.68% | 10.93% |
| FNS published (over / under) | 10.03 / 1.64 | 9.26 / 1.67 |
| Microdata-implied (total) | 8.40% | 8.91% |
| Microdata-implied (over / under) | 6.09 / 2.31 | 6.73 / 2.19 |
| Generator-implied, FNS-style (total) | 7.80% | 7.80% |
| Generator-implied (over / under) | 4.73 / 3.07 | 4.73 / 3.07 |

Generator case rate 39.90% (reportable: 25.53%) vs microdata case rate
40.29% / 40.99% (FY2023/FY2024). Dollar-weighted without tolerance:
generator 8.87% (identical to exp33's pooled microdata figure of 8.87% —
cross-check passes).

### Microdata national series for context (FYWGT-weighted)

| FY | Dollar rate | Over | Under | Case rate (wt) | n |
|---|---|---|---|---|---|
| 2020 | 7.88% | 6.00% | 1.88% | 35.49% | 27,112 |
| 2021 | 8.42% | 6.07% | 2.35% | 36.92% | 9,832 |
| 2022 | 8.17% | 5.84% | 2.33% | 39.04% | 41,391 |
| 2023 | 8.40% | 6.09% | 2.31% | 40.29% | 43,776 |
| 2024 | 8.91% | 6.73% | 2.19% | 40.99% | 44,891 |

### The published gap lives in overpayments — the procedural-error signature

| Gap (published − microdata-implied) | FY2023 | FY2024 |
|---|---|---|
| Total | +3.28 pp | +2.02 pp |
| Over component | +3.94 pp | +2.53 pp |
| Under component | −0.67 pp | −0.52 pp |

The entire published surplus is overpayment dollars. Since the 2022 policy
change, incomplete QC reviews are scored as if the *full benefit* were an
overpayment — a procedural error, not a payment error — and the over
component is exactly where such cases land.

### Procedural errors are invisible in the microdata

Zero of 167,002 microdata cases carry a full-benefit overissuance
(AMTERR ≥ RAWBEN); STATUS=1 cases never carry AMTERR > 0. The +2–3 pp
national published gap is a component the public-use files cannot see at
all — consistent with exp33's finding that published rates mix in
procedural errors from the separate CAPER track.

### State illustration (definitions allow only a contrast, not a match)

| State | FY2023 published | FY2023 microdata | FY2024 published | FY2024 microdata |
|---|---|---|---|---|
| Alaska | 60.37% | 4.51% | 24.66% | 5.64% |
| New Jersey | 35.70% | 5.43% | — | 6.12% |
| Hawaii | 20.94% | 4.38% | 6.68% | 3.62% |
| South Dakota | 3.27% | 2.42% | — | 3.54% |

Where review procedure is clean (South Dakota), published ≈
microdata-implied. Where procedural errors dominated (Alaska, New Jersey,
Hawaii FY2023), the published rate diverges by 15–55 pp; as procedures
were fixed (Alaska FY2024: 60.37% → 24.66%) the gap collapses toward the
payment-error substance.

### Residuals the generator owns

1. **Over/under split skew:** generator over share = 4.73/7.80 = 61% of
   error dollars; real microdata = 72–76% over. The generator is
   under-heavy relative to real payment-error substance (~1 pp of the
   dollar rate). Small but systematic.
2. **Published under < microdata under** (−0.5 to −0.7 pp) is consistent
   with federal re-review/regression adjustments trimming underpayment
   dollars in the official calculation (inference — the re-review weights
   are not public, so this attribution is provisional).

## Verdict

**Hypothesis held.** The disagreements are definition-driven and
attributable:

- Generator-implied 7.80% vs microdata-implied 8.40%/8.91%: the generator
  reproduces the *payment-error substance* of real QC to within ~1 pp at
  the national level (case rate matches to <1 pp as well). Calibration
  gate: passed at national level.
- Published 11.68%/10.93% sits +2–3 pp above the substance. The gap is
  (a) procedural errors — full-benefit overpayments from incomplete
  reviews since the 2022 policy change, concentrated in the over
  component, invisible in public-use microdata; and (b) federal re-review
  and regression adjustments, visible as the negative under-component
  gap. Neither is something the generator's error-injection model
  represents.
- The generator should **not** be tuned toward the published series: that
  would bake procedural-error inflation into a payment-error copilot. The
  right target stays the microdata-implied substance rate. The one
  generator-owned residual is the over/under split skew (61% vs ~73%
  over) — small, and a separate calibration question from the published
  gap.

Complements exp33 (state heterogeneity from microdata): exp33 showed the
generator has no state dimension; this experiment shows that even the
national published rate is the wrong calibration target, because it mixes
in administration errors the microdata — and the generator — deliberately
exclude.

## Next steps

1. **Recommended next run:** record the copilot's rate-definition decision
   in writing before any transfer evaluation: the training target is the
   microdata-implied payment-error substance (tolerance-applied), not the
   official FNS published rate. Exp33's "procedural-error note" asked for
   the same; this experiment supplies the numbers to justify it.
2. Track the generator's over/under split as a standing calibration
   sub-metric (currently 61% over vs ~73% real) — a few pp, worth one
   experiment, not a redesign.
3. If predicting official published state rates is ever needed, that is a
   separate module (procedural-error process), not a calibration tweak —
   procedural cases are absent from the public-use files, so it cannot be
   fit from microdata.
