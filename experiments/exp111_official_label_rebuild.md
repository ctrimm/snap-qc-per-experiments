# Experiment 111 — rebuilding the deployed rankers on the official error definition

**Date:** 2026-10-26 (pre-registered before running) · **Decision:** adopt exp110's OVER arm as the default (its pre-registered rule was met; approved by the project lead the same day) · **Code:** `SNAPQC_LABEL` in `exp58_agency_rankers.py`; reruns of exp83, exp93, exp79, exp107_timesplit, exp107_package · **Results:** `*_official_results.json`

### What changes

- **The new default label:** rankers now learn and are scored on the official payment-error definition (`SNAPQC_LABEL=official`, the default): |RAWBEN − FSBEN| above the fiscal year's federal tolerance ($38 FY2020, $39 FY2021, $48 FY2022, $54 FY2023, $56 FY2024).
- **The dollars:** that difference.
- **The status:** "2" overpaid, "3" underpaid.
- **Inputs:** unchanged and leak-free. RAWBEN and FSBEN enter the label only, never the inputs.
- **The old label:** `SNAPQC_LABEL=any` (any reviewer-found error, AMTERR dollars) reproduces exp107.

### Why

The official error rate, which sets the H.R. 1 cost share, counts only these errors. exp110 found that training on them:
- raises the median top-20% lift on over-threshold dollars (2.47× → 2.61×), and with the floor 2.10× → 2.45×;
- costs 1.7% of the lift on all error dollars;
- reviews older and disabled households closer to their share.

### Runs (same data, holdouts, seeds and settings as exp107)

| Script | Gate or role |
|---|---|
| `exp83_context_models_full_eval.py` | **Gate:** top-20% lift must equal exp110's OVER `lift_over` in 53 of 53 (same label, rows, order and seeds) |
| `exp93_cost_share_current_models.py` | Cost share; scenario lifts are now lifts on over-threshold dollars. **Check:** central ≈ $3.15B (exp110's estimate from a slightly different summation) |
| `exp79_underpayment_ranker.py` | Underpayment ranker; underpayment = over-threshold and RAWBEN < FSBEN |
| `exp107_timesplit.py` | Later-years test |
| `exp107_package.py` | All 53 packaged models; the model card records `error_label: official` |

### Then

**Papers, briefs, the replication guide and the dashboard** get the new figures, under a dated correction note:
- **The new headline:** lift on the dollars that count toward the official error rate.
- **The cost share:** restated; the central estimate becomes about $3.15B (exp110).
- **Checks:** `state_numbers.py check` must pass on the new sources.

### Results

<!-- AUTO-RESULTS:START -->
(pending)
<!-- AUTO-RESULTS:END -->
