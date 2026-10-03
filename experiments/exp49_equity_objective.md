# Exp49 — prototyping the equity fix: per-type floors vs equity-weighted ranking

**Date:** 2026-10-03
**Status:** Complete — decision: **GO on Variant A (error-proportional floors)**,
  see Verdict.
**Code:** `experiments/exp49_equity_objective.py`
**Deliverables:**
- `experiments/exp49_equity_objective.py` — ranker reproduction + both
  variants + tradeoff tables
- `experiments/exp49_equity_objective.md` — this chronicle
- Raw tables: `/tmp/exp49out/exp49_results.json` (scratch, not committed;
  includes per-variant selection index lists)

## Hypothesis

Exp47 showed the PA/NY dollar rankers under-review elderly/disabled
households relative to error risk (review-to-risk ratios 0.22–0.35) while
over-reviewing childless adults (1.41–1.45), because the dollar objective
deprioritizes frequent small-dollar errors. Two candidate fixes:

- **A — per-type floors:** reserve a fraction *f* of the review budget and
  allocate it across household types proportional to each type's share of
  *train* errors (floor_t = k·f·err_share_t), picking the top-by-dollar-score
  cases within each type; fill the rest of the budget by pure dollar rank.
  At f=1.0 the whole budget follows the error distribution (review-to-risk
  ratios constant across types by construction).
- **B — equity-weighted ranker:** rank by expected_$ × w_t, upweighting
  elderly and disabled_nonelderly, sweeping w ∈ {1.0, 1.5, 2.5, 4.0}.

Expected: both should trade headline $/hr for equity; the question is how
steep the tradeoff is and whether a simple fix closes most of the gap.

## Method

**Reproduction:** same as exp47 — PA two-part P(err)×E[$] (pa5 V1), NY direct
expected-$ (ny5 CLEAN8), pooled seed-7 synthetic, shared holdouts
(pa2 817 / ny2 815), same household taxonomy with MIN_TYPE_N=25 merges.
Budget: top-20% (k=163 both states). $/hr assumes 30-min reviews.

**Honesty fix vs the naive design:** floor weights are computed from the
*train* split's error shares (knowable at ranker-build time), never from
holdout labels. Within-type selection uses only model scores on the holdout.
A first run that used holdout error shares overstated the $/hr gain
(PA +9.7%, NY +23%); the reported numbers below use train shares.

**Baselines:** pure dollar ranker and analytic uniform-random review.

**Metrics per variant × state:** $/hr, share of total error $ recovered,
precision, and review-to-risk ratio (review_rate_t / base_error_rate_t) per
type; equity summarized by min ratio across types, CV of ratios, and
elderly/disabled review rates. Paired bootstrap (5,000 resamples, fixed
selection sets) for the $/hr deltas vs baseline.

## Results

### Tradeoff table, top-20% (k=163)

PA (baseline $5,483 / 28.4% / prec 0.491 / $67.3/hr):

| variant | $/hr | Δ$/hr 95% CI | share $ | prec | min ratio | CV |
|---|---|---|---|---|---|---|
| baseline dollar | 67.3 | — | 0.284 | 0.491 | 0.219 | 0.598 |
| random | 47.2 | — | 0.200 | 0.427 | 0.286 | 0.620 |
| floor f=0.50 | 67.3 | ≡ baseline | 0.284 | 0.491 | 0.219 | 0.598 |
| floor f=0.75 | 66.3 | −0.9 [−12.5, +9.3] | 0.280 | 0.522 | 0.250 | 0.539 |
| **floor f=1.00** | **68.9** | **+1.8 [−13.6, +16.4]** | **0.291** | **0.577** | **0.250** | **0.220** |
| weight w=1.5 | 69.3 | +2.0 [−12.1, +16.4] | 0.293 | 0.552 | 0.200 | 0.543 |
| weight w=2.5 | 64.0 | −3.1 [−22.0, +14.8] | 0.270 | 0.577 | 0.000 | 0.970 |
| weight w=4.0 | 59.3 | — | 0.251 | 0.589 | 0.000 | 1.513 |

NY (baseline $6,958 / 30.4% / prec 0.466 / $85.4/hr):

| variant | $/hr | Δ$/hr 95% CI | share $ | prec | min ratio | CV |
|---|---|---|---|---|---|---|
| baseline dollar | 85.4 | — | 0.304 | 0.466 | 0.336 | 0.585 |
| random | 56.1 | — | 0.200 | 0.367 | 0.330 | 0.320 |
| floor f=0.50 | 85.4 | ≡ baseline | 0.304 | 0.466 | 0.336 | 0.585 |
| floor f=0.75 | 86.8 | +1.4 [−20.1, +25.6] | 0.309 | 0.466 | 0.340 | 0.550 |
| **floor f=1.00** | **95.3** | **+10.0 [−14.5, +37.8]** | **0.340** | **0.546** | **0.421** | **0.253** |
| weight w=1.5 | 79.1 | −6.3 [−24.0, +10.2] | 0.282 | 0.472 | 0.300 | 0.609 |
| weight w=2.5 | 82.1 | −3.8 [−34.4, +28.0] | 0.293 | 0.497 | 0.000 | 0.791 |
| weight w=4.0 | 74.9 | — | 0.267 | 0.509 | 0.000 | 0.864 |

### What the fixes do to the type-level allocation (review rate | ratio)

PA baseline → floor f=1.0 → weight w=2.5:

| type | baseline | floor f=1.0 | weight w=2.5 |
|---|---|---|---|
| elderly | 0.104 / 0.219 | 0.199 / 0.418 | 0.280 / 0.589 |
| disabled_nonelderly | 0.179 / 0.330 | 0.286 / 0.527 | 0.357 / 0.659 |
| single_parent | 0.393 / 1.000 | 0.197 / 0.500 | 0.090 / 0.229 |
| married_with_kids | 0.267 / 0.533 | 0.267 / 0.533 | 0.033 / 0.067 |
| multiadult_with_kids | 0.364 / 0.522 | 0.273 / 0.391 | 0.091 / 0.130 |
| childless_adult | 0.209 / 1.409 | 0.081 / 0.545 | 0.013 / 0.091 |
| other_small (n=9) | 0.222 / 0.500 | 0.111 / 0.250 | 0.000 / 0.000 |

NY baseline → floor f=1.0 → weight w=2.5:

| type | baseline | floor f=1.0 | weight w=2.5 |
|---|---|---|---|
| elderly | 0.114 / 0.336 | 0.223 / 0.655 | 0.208 / 0.612 |
| disabled_nonelderly | 0.148 / 0.354 | 0.200 / 0.477 | 0.271 / 0.646 |
| single_parent | 0.274 / 0.520 | 0.242 / 0.460 | 0.084 / 0.160 |
| married_with_kids | 0.172 / 0.500 | 0.276 / 0.800 | 0.000 / 0.000 |
| childless_adult | 0.340 / 1.447 | 0.099 / 0.421 | 0.235 / 1.000 |
| other_small | 0.455 / 0.750 | 0.273 / 0.450 | 0.121 / 0.200 |

### Findings

1. **Variant A at f=1.0 closes most of the equity gap at no measurable
   $/hr cost.** Elderly review-to-risk ratios roughly double toward parity
   (PA 0.22→0.42, NY 0.34→0.66); disabled 0.33→0.53 / 0.35→0.48; the
   childless-adult over-review collapses (1.41→0.55 / 1.45→0.42). CV of
   ratios falls from ~0.59 to 0.22–0.25. The $/hr deltas are positive in
   point terms (PA +2.4%, NY +11.6%) but the bootstrap CIs include zero —
   the honest claim is *costs nothing we can measure*, not a gain.
2. **Why it can be free — the across-type miscalibration.** The pure dollar
   ranker's top-k contains many predicted-high-$ cases that realize $0
   (selected childless-adult precision: PA 0.097, NY 0.273). Forcing the
   budget into error-dense types swaps low-precision predicted dollars for
   high-precision realized dollars, so precision *rises* under floors
   (PA 0.491→0.577, NY 0.466→0.546). Exp47's marginal check still holds:
   within each type, floors pick the highest predicted-$ cases, so the
   dollar discipline survives *within* types — only the across-type
   allocation changes, and that allocation was where the miscalibration
   lived.
3. **Variant A has a threshold, not a slope.** f=0.50 reproduces the
   baseline exactly in both states; f=0.75 barely binds. Floors only bite
   when f·err_share_t exceeds the type's baseline selection share, so
   partial floors are dead parameters — the fix is all-or-nothing, and
   all-or-nothing is free. (Operationally this is convenient: one
   parameter value to defend.)
4. **Variant B is blunt and creates new inequities.** w=1.5 is a wash on
   equity (PA min ratio 0.200 vs 0.219 baseline) with noisy $/hr effects
   (NY w=1.5 *loses* $6.3/hr while w=2.5 loses only $3.8 — non-monotonic).
   At w≥2.5 it zeroes out whole types (PA: other_small, and single_parent/
   married/multia near-zero; NY: married_with_kids exactly zero) — robbing
   Peter to pay Paul. CV of ratios explodes to 0.79–1.51. Multiplicative
   upweighting cannot target "more for the vulnerable" without "none for
   someone else" under a fixed budget.
5. **The min-ratio metric needs a size qualifier.** At floor f=1.0 the
   binding min is PA's other_small (n=9, ratio 0.25) — noise in a 9-row
   type. Among types with n≥25, PA floor f=1.0 ratios span 0.39–0.55 and
   NY 0.42–0.80: near-parity for every policy-relevant group.

## Verdict

**GO on Variant A (full error-proportional floors, f=1.0); DROP Variant B.**
A simple fix closes most of the equity gap cheaply — more precisely, the
tradeoff is *flat, not steep*: elderly/disabled review-to-risk ratios
roughly double toward parity (PA 0.22/0.33→0.42/0.53, NY 0.34/0.35→0.66/0.48),
the childless-adult over-review is cut by ~2/3, and headline $/hr is
statistically unchanged (PA 67.3→68.9, NY 85.4→95.3; both Δ CIs include
zero). Precision rises as a side effect (fewer wasted reviews), which
matters for reviewer burden beyond $/hr. Variant B is not salvageable as a
primary mechanism: it manufactures zero-review types and its $/hr response
is non-monotonic. The mechanism is clean enough to state in one sentence:
keep the dollar ranking *within* household types, but allocate the review
budget *across* types by where the errors are.

## Next steps

- **For the pilot:** adopt f=1.0 floors as the default review-budget rule
  (sort by expected-$ within type, take the top floor_t per type). It needs
  no model change — only the selection step changes — and the only new
  input is per-type train error shares, refit whenever the QC sample
  refreshes.
- **Under-issuance arm (exp47's open question):** floors here are keyed to
  *all* errors. If the pilot goal is finding underpayments owed to
  elderly/disabled households, re-run with floors keyed to under-issuance
  error shares (or dollars) instead — expect the equity/$ tradeoff to look
  different, possibly steeper.
- **Robustness:** re-check on the FY2025 microdata when it lands
  (watch: `fy2025-qc-microdata-watch`) — the error mix by type may move,
  and the floors inherit whatever the train shares say. Also test at
  top-10%/30% budgets; the f=1.0 parity property is budget-independent by
  construction, but the $/hr flatness may not be.
- **Don't overclaim the $/hr point estimates:** the CIs are wide
  (±$14–38/hr). The supported claim is "no detectable cost," not "floors
  earn more." A larger holdout (or pooled-state evaluation) could tighten
  this.
- For the post: this is the "what we did about it" companion to exp47's
  uncomfortable finding — the tilt was a property of the objective, and
  changing the objective's budget rule fixed it without moving the model.
