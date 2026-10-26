# Experiment 110 — training on the official error definition

**Date:** 2026-10-26 (pre-registered before running) · **Code:** `exp110_official_error_definition.py` · **Results:** `exp110_leakfree_results.json`

### Why

Our rankers learn "any error the reviewer found" (STATUS 2 or 3, about 38% of cases), weighted by AMTERR dollars. giannella/snap_qc, and the official payment error rate, count only errors above the federal tolerance: |RAWBEN − FSBEN| above $48 (FY2022), $54 (FY2023) or $56 (FY2024), about 12% of cases. exp106 only *scored* our any-error model on that definition. What happens if we *train* on it?

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

**D1 (giannella's one-year-ahead test, 49 states):** the OVER arm trained on FY2022–23 and tested on FY2024 with their exclusions. Precision and dollar recall at 5% and 10%, against exp106's ANY-trained D1 and giannella's v2.5.0 benchmark.

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
(pending)
<!-- AUTO-RESULTS:END -->
