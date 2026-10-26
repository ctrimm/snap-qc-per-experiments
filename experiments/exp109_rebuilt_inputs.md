# Experiment 109 — our ranker on giannella's rebuilt pre-review inputs (the fair head-to-head)

**Date:** 2026-10-26 (pre-registered before running) · **Code:** `exp109_export_frame.R` (runs giannella's munging script in a scratch copy and exports the frame), `exp109_rebuilt_inputs.py` · **Results:** `exp109_leakfree_results.json`

### Why

The triple-check (exp106 correction) found that giannella/snap_qc does not use the QC reviewer's values as inputs. Their munging script rebuilds approximate **pre-review** values: starting from the reviewer's final values and the error codes, it shifts the field in error until the benefit formula gives the benefit the agency issued.

Our leak-free model still reads the reviewer's corrected values for error cases. So exp106 D1 (ours finds more over-threshold error dollars than their lists in 39 of 49 states) compared tools on different inputs.

This experiment answers two questions:
1. How much do the reviewer's corrected values flatter our model?
2. Does our model still beat their lists when both use rebuilt inputs?

### Design

**Their frame.** giannella's `1_data_munging_and_raw_variable_reconstruction_for_using_public_qc_data.R` at `eedb3f5`, run unmodified except for two changes:
- `cpi_inflate_vars <- FALSE`, so the rebuilt amounts stay in nominal dollars like our features. This step changes values, not rows.
- an export of the final frame to Parquet.

It runs in a scratch copy, so their clone is untouched. Frame rows link to the QC CSV rows by (fiscal year, `HHLDNO`), which is unique within a year.

**Inputs.** Our 20 leak-free features, computed by our unchanged `context_features`, with each field drawn from one of two sources:

| Our field | R arm (as now: reviewer-recorded) | B arm (rebuilt pre-review) |
|---|---|---|
| CERTHHSZ (unit size) | CERTHHSZ | `rawusize` |
| RAWHSIZE (people) | RAWHSIZE | `ctprhh` (giannella's own feature) |
| RAWGROSS | RAWGROSS | `rawgrinc` |
| RAWNET | RAWNET | `rawnet_capped` |
| RAWERND | RAWERND | `rawernded` |
| SHELDED | SHELDED | `rawsltded` |
| RENT, UTIL | RENT, UTIL | `rawrent`, `rawutil` |
| FSMEDEXP, FSDEPDED, FSCSEXP | as is | `rawmedded`, `rawdepded`, `rawcsded` |
| BENMAX | BENMAX | `rawbenmax` |
| SUA1, HOMEDED | as is | as is |

**Test (exp106 D1 protocol).**
- **Rows:** restricted to giannella's frame.
- **Training:** all jurisdictions' FY2022–23 frame rows, with each state's adopted variant weight (own ×10 for `C_ctx`), `fit_w`, `E56.DEFAULT`, and the any-error label with AMTERR dollars as deployed.
- **Testing:** each state's FY2024 frame rows, under their error definition (over the tolerance, dollars = |RAWBEN − FSBEN|).
- **Metrics:** precision and dollar recall at 5% and 10% budgets, for 49 states.

**Gate:** the FY2024 test count per state must equal giannella's benchmark `n_te` in all 49 states. If it doesn't, the frames differ and the comparison is reported as approximate.

**Secondary arm, B_over:** the B inputs with the over-threshold training label (as in exp110).

### Readouts and decision

- **R − B**, the median paired difference, measures how much the reviewer's corrected values flatter our model.
- **B vs giannella's v2.5.0 lists**, with the median paired difference and states higher/lower, is the fair head-to-head.
- **The decision:**
  - If B still beats their lists in a majority of states on dollar recall at 10%, the comparison paper keeps its conclusion with the B numbers.
  - If not, the paper says their lists are as good or better on like-for-like inputs.
  - Either way, all the comparison figures (paper, dollar table, README, vault) move to the B numbers.
- **Default inputs:** if B loses little against R (under 10% of the median dollar recall), we recommend rebuilding pre-review inputs as our default training inputs. That would be a later experiment.

### Results

<!-- AUTO-RESULTS:START -->
(pending)
<!-- AUTO-RESULTS:END -->
