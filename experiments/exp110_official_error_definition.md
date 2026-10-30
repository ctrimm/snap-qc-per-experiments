# Experiment 110 — training on the official error definition

**Date:** 2026-10-26 (pre-registered before running) · **Code:** `exp110_official_error_definition.py` · **Results:** `exp110_leakfree_results.json`

### Why

Our rankers learn "any error the reviewer found" (STATUS 2 or 3, about 38% of cases), weighted by AMTERR dollars. Better Government Lab's snap_qc, and the official payment error rate, count only errors above the federal tolerance: |RAWBEN − FSBEN| above $48 (FY2022), $54 (FY2023) or $56 (FY2024), about 12% of cases. exp106 only *scored* our any-error model on that definition. What happens if we *train* on it?

### Design

Leak-free features (the default), the deployed pooled design (exp83: adopted variant, `fit_w`, `E56.DEFAULT`, exp68 holdouts), per jurisdiction. Two arms, identical except for the training label:
- **ANY (current):** label = any error; dollars = AMTERR. Gate: its top-20% lift on any-error dollars must reproduce `exp83_leakfree_results.json` in 53 of 53.
- **OVER:** label = over the tolerance (exp106's `over()`); dollars = |RAWBEN − FSBEN| on those cases, 0 otherwise. RAWBEN appears only in the label, never in the inputs.

**Readouts on the exp68 holdout (top 10% and 20%):**
- lift on any-error dollars;
- lift on over-threshold dollars;
- share of reviews with any error, and with an over-threshold error;
- elderly and disabled review ratios (exp106 measure) under the arm's own definition;
- floor-on lift. The floor shares are set from the arm's own training labels.

**D1 (Better Government Lab's one-year-ahead test, 49 states):** the OVER arm trained on FY2022–23 and tested on FY2024 with their exclusions. Precision and dollar recall at 5% and 10%, against exp106's ANY-trained D1 and Better Government Lab's v2.5.0 benchmark.

**Cost share:** the official error rate counts over-threshold errors, so the scenario lift should be the lift on over-threshold dollars. The exp106 cost-share function (exp69 central, high and low; top-10% floor-on lift) is computed three ways:
- ANY with any-error lift (as published);
- ANY with over-threshold lift;
- OVER with over-threshold lift.

### Readouts and decision

No hypothesis on direction.
- **Adopt OVER as the default** only if it raises the median top-20% lift on over-threshold dollars **and** costs no more than 5% of the median lift on any-error dollars. Otherwise report it as an option for states that care mainly about the official rate.
- **Fairness:** the elderly ratio under each arm is reported. It is not part of the decision; the floor stays on either way.

### Results

<!-- AUTO-RESULTS:START -->
**Gate passed:** the ANY arm reproduces `exp83_leakfree_results.json` top-20% lift in 53 of 53.

**Holdout (exp68), median of 53 jurisdictions:**

| | ANY (current) top 10% | OVER top 10% | ANY top 20% | OVER top 20% |
|---|---|---|---|---|
| Lift on any-error dollars | 3.31× | 3.36× | 2.70× | 2.65× |
| Lift on over-threshold dollars | 3.01× | **3.37×** | 2.47× | **2.61×** |
| With the floor, over-threshold dollars | 2.67× | **3.13×** | 2.10× | **2.45×** |
| Reviews with any error | 67% | 63% | 66% | 60% |
| Reviews with an over-threshold error | 35% | 37% | 31% | 32% |

**Paired, OVER vs ANY:**
- **Over-threshold lift:** OVER is higher in 37 of 53 at top 10% (median +0.15×) and 36 at top 20% (+0.09×).
- **With the floor:** OVER is higher in 41 and 44 of 53 (+0.25×, +0.20×).
- **Any-error lift at top 20%:** −0.08× (OVER higher in only 19 of 53). The median falls 1.7%, within the 5% allowance.

**Decision rule: met.** OVER raises the median top-20% lift on over-threshold dollars (2.47× → 2.61×) and costs 1.7% of the median any-error lift (limit 5%).

**Fairness** (each arm on its own error definition, top 20%, dollar-only):
- **Elderly:** ANY 0.33 (53 of 53 below 0.8); OVER 0.44 (50 of 52).
- **Disabled:** ANY 0.63; OVER 0.79.
- **Floor:** the floor is still needed under either label.

**One year ahead (Better Government Lab's D1 test, 49 states):** OVER does not help there.

| Median, FY2024 | OVER | ANY (exp106) | Better Government Lab |
|---|---|---|---|
| Precision, 5% / 10% | 0.40 / 0.30 | 0.40 / 0.32 | 0.32 / 0.30 |
| Dollar recall, 5% / 10% | 0.26 / 0.39 | 0.26 / 0.41 | 0.14 / 0.27 |

OVER beats Better Government Lab's lists on dollar recall at 10% in 40 of 49 states, against ANY in 21 of 49.

**FY2028 cost share avoided, a year (exp69 scenarios, top-10% floor-on lift):**

| | Low | Central | High |
|---|---|---|---|
| ANY with the any-error lift (as published) | $0.21B | $3.42B | $6.63B |
| **ANY with the over-threshold lift** | $0.21B | **$2.62B** | $6.48B |
| **OVER with the over-threshold lift** | $0.21B | **$3.15B** | $7.05B |

**A correction to the published cost share.** The official payment error rate counts only errors over the tolerance, so the scenario should use the tool's lift on over-threshold dollars. On the deployed model that lift is lower (2.67× with the floor, not 2.93×), so the central estimate is **$2.62B, not the published $3.42B**. Training on the official definition recovers most of it ($3.15B).

### Verdict

- **Training on the official definition** helps the dollars that move the payment error rate, especially with the floor on (+0.20–0.25×). It barely changes the any-error dollars, and it reviews older and disabled households closer to their share. By the pre-registered rule it should become the default.
- **The forward test is flat:** on Better Government Lab's one-year-ahead test it doesn't improve on the current model.
- **Next, not done here:**
  - repackage the 53 models with the OVER label;
  - restate the cost share on the over-threshold lift ($2.62B for the deployed models; $3.15B after repackaging) in every paper that quotes $3.42B.
<!-- AUTO-RESULTS:END -->
