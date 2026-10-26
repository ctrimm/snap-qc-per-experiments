# Experiment 112 — the official error label, as the reviewer recorded it

**Date:** 2026-10-26 (pre-registered before running) · **Decision:** approved by the project lead the same day · **Code:** `SNAPQC_LABEL` in `exp58_agency_rankers.py` (`label()`); reruns of exp83, exp93, exp79, exp107_timesplit, exp107_package · **Results:** `*_official_results.json` (exp111's are renamed `*_gap_results.json`)

### Why

exp111 made the official error definition the default, but built the label from the benefit gap: |RAWBEN − FSBEN| above the tolerance. giannella/snap_qc's findings record (section 24) shows that gap often contradicts the error the reviewer recorded, and they exclude such rows. In our FY2020–24 data:
- **Contradictions:** 30% of the gap label's errors (33% of its dollars) disagree with AMTERR by more than $5.
- **No error found:** in 4,584 of them, STATUS = 1.
- **Rates:** the gap label marks 13.6–18.4% of cases a year. The reviewer-based definition marks 10.2–12.1%, in line with the official national rates (about 11–12%).

The payment error rate counts errors the reviewer found whose amount exceeds the tolerance, so that is the label.

### The label

**`SNAPQC_LABEL=official` (new default):**
- **Error:** STATUS 2 (overpaid) or 3 (underpaid), with |AMTERR| above the fiscal year's tolerance ($38 FY2020, $39 FY2021, $48 FY2022, $54 FY2023, $56 FY2024).
- **Dollars:** |AMTERR|.
- **Otherwise:** "1" and $0.

**Other values:**
- `gap` reproduces exp111;
- `any` reproduces exp107.

### Runs

| Step | Role |
|---|---|
| `SNAPQC_LABEL=gap` exp83 | **Gate:** must reproduce `exp83_gap_results.json` byte for byte (the refactor changed nothing else) |
| exp83, exp93, exp79, exp107_timesplit, exp107_package (default) | The rebuild; model cards record `error_label: official` |

### Readouts

- the same tables as exp111 (lift on over-tolerance AMTERR dollars, later years, floor, fairness, underpayments, cost share);
- the change against exp111.

No hypothesis on direction. Then every paper, brief, the guide and the dashboard are restated, and `state_numbers.py check` must pass.

### Results

<!-- AUTO-RESULTS:START -->
(pending)
<!-- AUTO-RESULTS:END -->
