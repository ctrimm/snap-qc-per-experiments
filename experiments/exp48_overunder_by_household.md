# Exp48 — over/under-issuance split of recovered and missed dollars by household type

**Date:** 2026-10-03
**Status:** Complete — decision: **HYPOTHESIS LARGELY REFUTED** (one modest exception), see Verdict.
**Code:** `experiments/exp48_overunder_by_household.py`
**Deliverables:**
- `experiments/exp48_overunder_by_household.py` — taxonomy + ranker reproduction + per-type over/under split
- `experiments/exp48_overunder_by_household.md` — this chronicle
- Raw tables: `/tmp/exp48out/exp48_results.json` (scratch, not committed)

## Hypothesis

Exp47 showed the dollar rankers systematically under-review elderly and
disabled households relative to their error risk (review-rate/base-error-rate
ratios 0.22–0.35 in both states). The pilot-relevant follow-up: are the
errors the ranker *skips* in those vulnerable types disproportionately
**under-issuances** — money owed to the household? If the skipped elderly/
disabled errors are mostly underpayments, the dollar objective isn't just
allocation-regressive, it actively hides money owed to vulnerable households.
Expected shape if true: the under-share of missed dollars in elderly/disabled
types >> their types' own under-share of error dollars (and >> the ~30%
aggregate baseline).

## Method

Same taxonomy, same holdouts, same ranker recipes as exp47, reproduced
exactly (pooled seed-7 synthetic; PA: pa5 two-part P(err)xE[$] V1; NY: ny5
direct expected-$ CLEAN8). Over/under coded from the QC `STATUS` field per
the pa5/ny5 field logic already used in those scripts: `"2"` = over-issuance,
`"3"` = under-issuance, `"1"` = correct; `AMTERR` carries the dollars
(reviewer-verified, +/-$1 rounding tolerance; $0 for correct cases).

Top-20% review budget (k=163) only. Per household type: recovered dollars
split over/under, missed dollars (unselected error dollars) split over/under,
the **under-share of missed dollars** = missed_under / missed_total, and the
type's own under-share of error dollars as the proportionality baseline
(random review would leave a missed mix matching the type's own mix; the
aggregate baselines are PA 0.283, NY 0.335).

Reproduction checks: PA recovered $5,483 and NY $6,958 match exp47 exactly;
NY over/under split ($4,751 / $2,207) matches the published NY5 numbers.

## Results

### PA top-20%

| type | n | rec_over $ | rec_under $ | rec under-share | miss_over $ | miss_under $ | **miss under-share** | type under-share |
|---|---|---|---|---|---|---|---|---|
| elderly | 307 | 1,046 | 155 | 0.129 | 2,864 | 1,003 | **0.259** | 0.229 |
| disabled_nonelderly | 168 | 1,277 | 83 | 0.061 | 2,089 | 1,053 | **0.335** | 0.252 |
| single_parent | 122 | 740 | 458 | 0.382 | 994 | 202 | 0.169 | 0.276 |
| married_with_kids | 30 | 21 | 331 | 0.940 | 1,012 | 1,347 | 0.571 | 0.619 |
| multiadult_with_kids | 33 | 454 | 255 | 0.360 | 1,671 | 139 | 0.077 | 0.156 |
| childless_adult | 148 | 225 | 155 | 0.408 | 1,168 | 263 | 0.184 | 0.231 |
| overall | 817 | 4,034 | 1,449 | 0.264 | 9,800 | 4,020 | 0.291 | 0.283 |

Missed-mix enrichment vs type's own mix: elderly 1.14x, disabled 1.33x.

### NY top-20%

| type | n | rec_over $ | rec_under $ | rec under-share | miss_over $ | miss_under $ | **miss under-share** | type under-share |
|---|---|---|---|---|---|---|---|---|
| elderly | 341 | 973 | 636 | 0.395 | 3,481 | 1,290 | **0.270** | 0.302 |
| disabled_nonelderly | 155 | 477 | 446 | 0.483 | 1,183 | 1,298 | **0.523** | 0.512 |
| single_parent | 95 | 1,841 | 690 | 0.273 | 1,787 | 1,193 | 0.400 | 0.342 |
| married_with_kids | 29 | 0 | 173 | 1.000 | 1,299 | 728 | 0.359 | 0.409 |
| childless_adult | 162 | 1,000 | 62 | 0.058 | 1,443 | 732 | 0.337 | 0.245 |
| overall | 815 | 4,751 | 2,207 | 0.317 | 10,457 | 5,456 | 0.343 | 0.335 |

Missed-mix enrichment vs type's own mix: elderly 0.90x, disabled 1.02x.

### Reading

**The ranker does not systematically hide underpayments in the cases it
skips.** The missed-dollar mix tracks each type's own over/under
composition within 0.5–1.4x — there is no gross distortion where the
skipped elderly/disabled errors turn out to be mostly underpayments.
PA elderly: 0.259 vs in-type 0.229 (1.14x, vs aggregate baseline 0.283).
NY elderly: 0.270 vs in-type 0.302 (0.90x — the ranker actually skips
*relatively more* over-issuance there, and recovers underpayments at
1.31x their mix). NY disabled: 0.523 vs in-type 0.512 (1.02x — the missed
mix mirrors the type; no enrichment at all).

**The one exception is PA disabled:** missed under-share 0.335 vs in-type
0.252 (1.33x enrichment) — the ranker's skipped disabled cases are modestly
underpayment-heavier than the type's own composition. Note PA disabled is
also where the ranker most under-recovers underpayments on the reviewed
side (recovered under-share 0.061 vs in-type 0.252, 0.24x): the reviewed
slice is skewed toward over-issuance, the missed slice toward under-issuance.
Small n (34 missed underpayment cases), so treat as a flag, not a finding.

**What is real is absolute, not proportional.** Because elderly/disabled
are under-reviewed in *volume* terms (exp47), the unreviewed underpayment
mass is large even at a fair mix: PA elderly+disabled leave **$2,056** of
underpayments unreviewed (54 + 34 cases); NY **$2,588** (40 + 28 cases).
And NY disabled is intrinsically underpayment-heavy — 0.512 of its error
dollars are owed to households, the highest of any type in either state —
so a volume under-review there is intrinsically an underpayment
under-review, no mix distortion required. Overall, elderly+disabled types
hold 51% of PA's and 47% of NY's unreviewed underpayments.

**Mechanism (consistent with exp47):** underpayments in these types are
small-dollar (medical-deduction and fixed-income timing errors), so a
dollar-maximizing objective deprioritizes them on *both* sides of the
queue — the reviewed slice recovers them below their mix (PA elderly
0.56x, PA disabled 0.24x, NY childless 0.24x), and the missed slice mirrors
the type's mix rather than concentrating them. The fairness cost is
measured in missed dollars, not a distorted missed mix.

## Verdict

**HYPOTHESIS LARGELY REFUTED.** The errors the ranker skips in
elderly/disabled households are not disproportionately underpayments: the
missed mix tracks each type's own over/under composition (enrichment
0.90–1.33x), and NY's elderly missed mix is actually *less*
underpayment-heavy than the type's mix (0.270 vs 0.302). The honest version
of the fairness concern is volumetric, not compositional: under-review at
exp47's ratios leaves $2.1k (PA) / $2.6k (NY) of owed benefits unreviewed
in elderly+disabled types, and NY's disabled type is 51%-underpayment by
composition, so any volume cut there cuts underpayments hardest.

## Next steps

- For the pilot narrative: frame exp48 as the exonerating check it is —
  the ranker doesn't hide underpayments; it leaves them on the table by
  reviewing too few vulnerable-type cases. That points to *type-aware
  review budgets* (exp47's recommendation), not an under-issuance-weighted
  objective, which the enrichment numbers don't justify except possibly in
  PA disabled.
- PA disabled nonelderly (1.33x missed-mix enrichment, 0.24x recovered
  under-share) is worth one targeted look: check whether medical-deduction
  underpayments there have predicted dollars near the selection margin.
- Revisit after FY2025 microdata lands (watch: `fy2025-qc-microdata-watch`):
  the type-level over/under composition, especially NY disabled's
  0.512 under-share, may have moved.
