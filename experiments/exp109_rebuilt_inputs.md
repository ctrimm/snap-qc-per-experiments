# Experiment 109 — our ranker on Better Government Lab's rebuilt pre-review inputs (the fair head-to-head)

**Date:** 2026-10-26 (pre-registered before running) · **Code:** `exp109_export_frame.R` (runs Better Government Lab's munging script in a scratch copy and exports the frame), `exp109_rebuilt_inputs.py` · **Results:** `exp109_leakfree_results.json`

### Why

The triple-check (exp106 correction) found that Better Government Lab's snap_qc does not use the QC reviewer's values as inputs. Their munging script rebuilds approximate **pre-review** values: starting from the reviewer's final values and the error codes, it shifts the field in error until the benefit formula gives the benefit the agency issued.

Our leak-free model still reads the reviewer's corrected values for error cases. So exp106 D1 (ours finds more over-threshold error dollars than their lists in 39 of 49 states) compared tools on different inputs.

This experiment answers two questions:
1. How much do the reviewer's corrected values flatter our model?
2. Does our model still beat their lists when both use rebuilt inputs?

### Design

**Their frame.** Better Government Lab's `1_data_munging_and_raw_variable_reconstruction_for_using_public_qc_data.R` at `eedb3f5`, run unmodified except for two changes:
- `cpi_inflate_vars <- FALSE`, so the rebuilt amounts stay in nominal dollars like our features. This step changes values, not rows.
- an export of the final frame to Parquet.

It runs in a scratch copy, so their clone is untouched. Frame rows link to the QC CSV rows by (fiscal year, `HHLDNO`), which is unique within a year.

**Inputs.** Our 20 leak-free features, computed by our unchanged `context_features`, with each field drawn from one of two sources:

| Our field | R arm (as now: reviewer-recorded) | B arm (rebuilt pre-review) |
|---|---|---|
| CERTHHSZ (unit size) | CERTHHSZ | `rawusize` |
| RAWHSIZE (people) | RAWHSIZE | `ctprhh` (Better Government Lab's own feature) |
| RAWGROSS | RAWGROSS | `rawgrinc` |
| RAWNET | RAWNET | `rawnet_capped` |
| RAWERND | RAWERND | `rawernded` |
| SHELDED | SHELDED | `rawsltded` |
| RENT, UTIL | RENT, UTIL | `rawrent`, `rawutil` |
| FSMEDEXP, FSDEPDED, FSCSEXP | as is | `rawmedded`, `rawdepded`, `rawcsded` |
| BENMAX | BENMAX | `rawbenmax` |
| SUA1, HOMEDED | as is | as is |

**Test (exp106 D1 protocol).**
- **Rows:** restricted to Better Government Lab's frame.
- **Training:** all jurisdictions' FY2022–23 frame rows, with each state's adopted variant weight (own ×10 for `C_ctx`), `fit_w`, `E56.DEFAULT`, and the any-error label with AMTERR dollars as deployed.
- **Testing:** each state's FY2024 frame rows, under their error definition (over the tolerance, dollars = |RAWBEN − FSBEN|).
- **Metrics:** precision and dollar recall at 5% and 10% budgets, for 49 states.

**Gate:** the FY2024 test count per state must equal Better Government Lab's benchmark `n_te` in all 49 states. If it doesn't, the frames differ and the comparison is reported as approximate.

**Secondary arm, B_over:** the B inputs with the over-threshold training label (as in exp110).

### Readouts and decision

- **R − B**, the median paired difference, measures how much the reviewer's corrected values flatter our model.
- **B vs Better Government Lab's v2.5.0 lists**, with the median paired difference and states higher/lower, is the fair head-to-head.
- **The decision:**
  - If B still beats their lists in a majority of states on dollar recall at 10%, the comparison paper keeps its conclusion with the B numbers.
  - If not, the paper says their lists are as good or better on like-for-like inputs.
  - Either way, all the comparison figures (paper, dollar table, README, vault) move to the B numbers.
- **Default inputs:** if B loses little against R (under 10% of the median dollar recall), we recommend rebuilding pre-review inputs as our default training inputs. That would be a later experiment.

### Results

<!-- AUTO-RESULTS:START -->
**The run.**
- **Better Government Lab's munging script ran unmodified** apart from the two pre-registered changes (R 4.x, Homebrew; packages in a scratch library; scratch copy of `eedb3f5`).
- **Frame:** 231,619 rows (FY2017–19 and FY2022–24), of which 115,559 are FY2022–24. All linked to QC rows by (year, `HHLDNO`).

**Gate passed:** the per-state FY2024 test count equals Better Government Lab's benchmark `n_te` in 49 of 49. Same cases, same error definition, same budgets.

**Column mapping used:**
- CERTHHSZ → `cert_HH_size_FS_n` (`rawusize`)
- RAWHSIZE → `people_in_HH_n` (`ctprhh`)
- RAWGROSS → `rawgross` (`rawgrinc`)
- RAWNET → `rawnet_capped`
- RAWERND → `rawernded`
- SHELDED → `rawsltded`
- RENT, UTIL → `rawrent`, `utilities`
- FSMEDEXP → `medical_deductions` (`rawmedded`)
- FSDEPDED, FSCSEXP → `rawdepded`, `rawcsded`
- BENMAX → `maximum_benefit_for_HH_size` (`rawbenmax`)

| Median of 49 states, FY2024, their error definition | R: our model, reviewer inputs | **B: our model, rebuilt pre-review inputs** | B_over | Better Government Lab lists |
|---|---|---|---|---|
| Precision, 5% budget | 0.391 | **0.385** | 0.386 | 0.318 |
| Precision, 10% budget | 0.323 | **0.341** | 0.341 | 0.298 |
| Dollar recall, 5% budget | 0.255 | **0.196** | 0.208 | 0.141 |
| Dollar recall, 10% budget | 0.381 | **0.331** | 0.323 | 0.265 |

**1. The reviewer's values flatter our model's dollars, not its precision.**
- **R − B, median paired:** dollar recall +0.049 (5%) and +0.065 (10%), about 17–19% of R's value.
- **Precision:** +0.024 at 5% and −0.024 at 10%, so no consistent effect.

**2. Like-for-like, our model still beats Better Government Lab's lists:**

| B vs Better Government Lab | Median paired difference | States higher / lower |
|---|---|---|
| Precision, 5% | +0.039 | 36 / 11 |
| Precision, 10% | +0.041 | 39 / 9 |
| Dollar recall, 5% | +0.049 | 40 / 9 |
| Dollar recall, 10% | +0.048 | 35 / 14 |

The margin is smaller than exp106 D1 reported (dollar recall at 10% 0.41 against 0.27, higher in 39) but consistent.

**3. The training label hardly matters here.** B_over is close to B on this one-year-ahead test, as in exp110.

### Verdict

- **Decision 1 (comparison):** B beats their lists in a majority of states on dollar recall at 10% (35 of 49), so the comparison paper keeps its conclusion with the B numbers. Every comparison figure (paper, dollar table, README, vault) moves to B.
- **Decision 2 (default inputs):** the rule (adopt rebuilt inputs if B loses under 10% of R's dollar recall) is **not met**: B loses 17%. Read the other way, the gap is an estimate of how much the reviewer's corrected values flatter any figure we compute from the public file. A deployed tool sees pre-review values, so B-style numbers are the more honest forecast. A Python port of the rebuild, to train our packaged models on it, is the next step worth testing.
<!-- AUTO-RESULTS:END -->
