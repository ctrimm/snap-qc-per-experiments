# Exp51 — under-issuance-keyed review floors

**Date:** 2026-10-04
**Status:** Complete — decision: **GO WITH NUANCE** (see Verdict).
**Code:** `experiments/exp51_underissuance_floors.py`
**Deliverables:**
- `experiments/exp51_underissuance_floors.py` — taxonomy + ranker reproduction + floor variants + tradeoff tables
- `experiments/exp51_underissuance_floors.md` — this chronicle
- Raw tables: `/tmp/exp51out/exp51_results.json` (scratch, not committed)

## Hypothesis

Exp47 showed the dollar rankers under-review elderly/disabled households
relative to error risk. Exp48 refuted the compositional story (the missed
mix tracks each type's own over/under composition) but confirmed the
volumetric one: $2.1k (PA) / $2.6k (NY) of owed benefits go unreviewed in
elderly+disabled types. Exp49 went GO on error-share floors (Variant A,
f=1.0) at no measurable $/hr cost.

The open question: does keying the floors specifically to UNDER-ISSUANCE
dollars (owed benefits) — rather than base error rate (exp47's suggestion),
total error dollars, or error shares (exp49's GO) — move owed-benefit
recovery beyond what generic equity floors already buy? Expected: if
under-issuance has a distinct type signature from overall error dollars,
under-keying should recover more owed benefits, concentrated in
elderly/disabled types.

## Method

**Reproduction:** same taxonomy, holdouts, and ranker recipes as exp47/exp48
(pooled seed-7 synthetic; PA pa5 two-part P(err)×E[$] V1; NY ny5 direct
expected-$ CLEAN8). Top-20% review budget (k=163 both states), f=1.0
(exp49's GO value; partial floors are dead parameters).

**Reproduction check (gate):** PA $5,483 / NY $6,958 recovered at top-20%.
Both match exactly — proceeding.

**Floor mechanics** (exp49's procedure, reused): floor_t = largest-remainder
allocation of k by weights; within-type selection is top-by-dollar-score;
remainder filled by global dollar rank; floors capped at type n.

**Floor weights from the TRAIN split** (exp49's honesty fix — never holdout
labels). The task spec said "in the holdout"; we use train as the primary
(honest) analysis and run a holdout-keyed oracle as a labeled sensitivity to
bound the leakage, mirroring exp49's honesty check.

**Variants:**
| id | floors proportional to | source |
|---|---|---|
| V0 `dollar` | — (pure dollar rank) | baseline |
| V1 `floor_baseerr` | train base error rate | exp47's suggestion |
| V2 `floor_errdollar` | train total error dollars | — |
| V3 `floor_underdollar` | train under-issuance dollars | **hypothesis under test** |
| V4 `floor_errshare` | train error shares | exp49 Variant A (GO reference) |
| V3o `floor_underdollar_holdout` | HOLDOUT under-issuance dollars | oracle/upper bound (labeled, not decision-relevant) |

**Metrics per variant × state:** total $ recovered, $/hr (30-min reviews),
precision, per-type review_rate/base_error_rate ratios + CV + min ratio,
under-issuance $ recovered (overall and elderly+disabled), Δ$/hr vs baseline.

## Results

### Headline tradeoff table, top-20% (k=163)

PA (baseline $5,483 / $67.3/hr / prec 0.491):

| variant | rec $ | $/hr | Δ$/hr | prec | under $ | under eld/dis $ | CV | minR |
|---|---|---|---|---|---|---|---|---|
| V0 dollar | 5,483 | 67.3 | — | 0.491 | 1,449 | 238 | 0.598 | 0.219 |
| V1 floor_baseerr | 8,532 | 104.7 | **+37.4** | 0.552 | 2,615 | 148 | 0.769 | 0.171 |
| V2 floor_errdollar | 7,355 | 90.2 | +22.9 | 0.571 | 2,639 | 281 | 0.450 | 0.250 |
| V3 floor_underdollar | 7,033 | 86.3 | +19.0 | 0.564 | 2,570 | 281 | 0.514 | 0.308 |
| V4 floor_errshare | 5,618 | 68.9 | +1.6 | 0.577 | 1,299 | 331 | 0.220 | 0.250 |
| V3o oracle | 7,092 | 87.0 | +19.7 | 0.540 | 2,589 | 274 | 0.809 | 0.233 |

NY (baseline $6,958 / $85.4/hr / prec 0.466):

| variant | rec $ | $/hr | Δ$/hr | prec | under $ | under eld/dis $ | CV | minR |
|---|---|---|---|---|---|---|---|---|
| V0 dollar | 6,958 | 85.4 | — | 0.466 | 2,207 | 1,082 | 0.585 | 0.336 |
| V1 floor_baseerr | 9,196 | 112.8 | **+27.5** | 0.528 | 3,358 | 1,201 | 0.900 | 0.233 |
| V2 floor_errdollar | 7,715 | 94.7 | +9.3 | 0.534 | 2,899 | 1,406 | 0.155 | 0.457 |
| V3 floor_underdollar | 9,009 | 110.5 | +25.2 | 0.534 | 3,346 | 1,414 | 0.445 | 0.446 |
| V4 floor_errshare | 7,768 | 95.3 | +9.9 | 0.546 | 2,140 | 1,442 | 0.253 | 0.421 |
| V3o oracle | 9,788 | 120.1 | +34.7 | 0.552 | 3,774 | 1,577 | 0.706 | 0.353 |

### Reading

**1. V3 moves total owed-benefit recovery substantially.** Under-issuance $
recovered: PA 1,449 → 2,570 (+77%); NY 2,207 → 3,346 (+52%). It beats V4
(exp49's GO) on this metric by a wide margin (PA +98%, NY +56%). The
under-issuance type signature *is* distinct from the error-count signature —
keying to owed dollars finds owed dollars that error-share floors leave.

**2. But V3 does not specifically move elderly/disabled owed benefits beyond
V4.** Elderly/disabled under-$ recovered: PA V3 $281 vs V4 $331 (V4 wins);
NY V3 $1,414 vs V4 $1,442 (tie). Reason: under-issuance dollars concentrate
in single_parent (PA train under-weight 0.235) as well as elderly/disabled,
and per-case underpayments in elderly/disabled are small — so an
under-dollar key spreads the budget toward high-under-dollar-mass types,
not specifically toward vulnerable types. If the pilot goal is "owed
benefits to elderly/disabled," V4 remains the better floor.

**3. V3 has no $/hr cost — it is a $/hr gain.** PA +$19.0/hr, NY +$25.2/hr
vs baseline. Like exp49's finding, forcing the budget into high-precision
types swaps low-precision predicted dollars for realized dollars (precision
rises: PA 0.491→0.564, NY 0.466→0.534). The honest claim, per exp49's
standard: costs nothing we can measure; the point gains are not
bootstrap-tested here.

**4. V3 improves equity vs baseline, but V4 remains the equity champion.**
CV of review-to-risk ratios: PA 0.598→0.514, NY 0.585→0.445; min ratio:
PA 0.219→0.308, NY 0.336→0.446. V4's CV (0.220/0.253) is still far better.
V3 is a compromise: better dollars than V4, better equity than baseline.

**5. The V1 caution: flooring by pure base error rate is a $/hr monster
that destroys equity.** V1 gains +$37.4/hr (PA) and +$27.5/hr (NY) — the
largest dollar gains of any variant — by reviewing entire small high-rate
types (PA: all 33 multiadult, all 30 married_with_kids, all 9 other_small).
But CV explodes to 0.769/0.900 and min ratio *falls* below baseline
(PA 0.171 < 0.219). Keying floors to rates without regard to type size is
dollar-efficient and equity-regressive — the opposite of the intended fix.
Do not implement V1 as an equity measure.

**6. Oracle check: train-keying is honest; holdout-keying inflates
modestly.** V3o vs V3: PA $7,092 vs $7,033 (+$59, negligible); NY $9,788 vs
$9,009 (+$779, +8.6%). The leakage from holdout-keyed floors is real but
modest — the train-keyed V3 numbers above are the decision-relevant ones,
and the conclusion (V3 beats baseline and V4 on under-dollars) survives
under either keying.

### Floor allocations (counts, k=163)

PA V3 floors: elderly 45, disabled 43, single_parent 38, married 18,
multiadult 10, childless 7, other_small 2. (Baseline reviews: elderly 32,
disabled 30, single 48, married 8, multiadult 12, childless 31, other 2.)

NY V3 floors: elderly 59, disabled 29, single_parent 27, married 13,
childless 18, other_small 17. (Baseline: elderly 39, disabled 23, single 26,
married 5, childless 55, other 15.)

V3 shifts reviews from childless_adult (low precision, low under-dollar
mass) toward elderly/disabled/single_parent in both states.

## Verdict

**GO WITH NUANCE.** V3 (under-issuance-keyed floors) is deployable: it
beats the pure dollar ranker on every metric — more total dollars, higher
$/hr, 52–77% more owed benefits recovered, better review-to-risk parity —
at no measurable $/hr cost. If the pilot values total owed-benefit
recovery, V3 dominates V4 (exp49's GO).

The nuance: V3 does *not* specifically target elderly/disabled owed
benefits better than V4 does. Under-issuance dollars are not concentrated
enough in vulnerable types for the key to discriminate them. Recommendation
by pilot goal:
- Maximize total owed-benefit recovery → **V3**.
- Maximize vulnerable-type equity → **V4** (exp49's GO stands).
- V3 is the best single compromise if one variant must serve both.

Do not implement V1 (base-error-rate floors) as an equity fix: it is the
highest $/hr variant and the least equitable.

## Next steps

- For the pilot: choose V3 vs V4 by stated goal (owed dollars vs vulnerable
  equity), or run V3 as the default with V4 as the equity-sensitive
  alternative. Both dominate the pure ranker.
- Bootstrap the V3 Δ$/hr (exp49's 5,000-resample paired procedure) before
  quoting the +$19/+$25 as a gain; the honest claim remains "no measurable
  cost" until then.
- Optional: hybrid floors (e.g. 50% under-dollar weight + 50% error-share
  weight) to target both total owed dollars and vulnerable-type coverage —
  one experiment, same harness.
- Revisit after FY2025 microdata lands (watch: `fy2025-qc-microdata-watch`):
  type-level under-issuance composition may move.
