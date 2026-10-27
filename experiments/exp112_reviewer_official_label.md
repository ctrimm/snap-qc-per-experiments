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
**Gate passed:** under `SNAPQC_LABEL=gap`, exp83 reproduced `exp83_gap_results.json` byte for byte, so the refactor changed nothing but the label. **Packaged:** 53 of 53 model cards record `error_label: official`.

All lifts below are on the dollars the official payment error rate counts.

| Median of 53 jurisdictions | exp111 (gap label) | **exp112 (reviewer's finding over the tolerance)** |
|---|---|---|
| Top 20% vs random | 2.61× (Idaho 1.49× – Alaska 3.37×) | **2.96×** (Kansas 2.18× – Washington 3.90×) |
| Jurisdictions at 2.0× or better | 50 of 53 | **53 of 53** |
| Top 10% vs random | 3.37× | **4.07×** |
| Found per review hour, top 20% (random) | $142 ($52) | **$109 ($38)**; range $29–245 |
| Dollar forecast within 20% of actual | 43 of 53 (median 0.99) | **38 of 53** (median 1.06) |
| Later years (train 2020–22, test 2023–24) | 2.51× | **2.95×** (Kansas lowest, 2.20×) |
| With the fairness floor, top 20% | 2.45× (median cost 7%) | **2.79×** (median cost 4%; most Utah 45%, then Montana 27%; no cost in 18) |
| Older households' review ratio, dollar-only | 0.44 (50 of 52 below 0.8) | **0.56** (47 of 52 below 0.8) |
| With the floor | 1.02; 8 of 52 below 0.8 | **1.05; 8 of 52 below 0.8** (lowest 0.70) |
| Disabled households, dollar-only → floor | 0.79 (26 of 51 below 0.8) | **0.81** (23 of 51); 11 below 0.8 with the floor |
| Underpayment ranker vs main ranker | 1.91× vs 1.41× (better in 41) | **1.69× vs 1.34× (better in 33)** |

**Per state, top 20%:** the official label is higher than the gap label in 46 of 53.

**FY2028 cost share avoided a year (exp93 scenarios, top-10% floor-on lift):**

| Scenario | Floor on | Dollar-only | Random review |
|---|---|---|---|
| Low | $0.21B | $0.21B | $0.16B |
| **Central** | **$4.47B** (36 states drop a bracket) | $4.79B | $1.03B |
| High | $8.24B | $8.78B | $2.39B |
| Central, top-20% basis | $2.81B | | |

### Reading it

- **The cleaner label finds the official errors better everywhere it matters.** It removes about 30% noise from the training labels, cases where the benefit gap contradicted the reviewer's finding.
- **Lift:** up 2.61× → 2.96×, and every jurisdiction now reaches 2.0×.
- **The floor:** cheaper again ($0.32B of the central estimate, against $0.75B).
- **Per review hour:** the dollars are lower than exp111 ($109 against $142) because the gap label had counted dollars the reviewer didn't find.
- **Forecasts are less accurate** (38 of 53 within 20%, from 43). The dollar calibrator sees fewer, larger errors.
- **The floor still leaves 8 jurisdictions below 0.8** for older households.
- **The 17% caveat still applies:** for error cases the inputs are the reviewer's corrected values, which flattered dollar figures by about 17% in exp109.

### Verdict

Adopted; `SNAPQC_LABEL=official` (this definition) is the default. The cost share's central estimate is **$4.47B** (low $0.21B, high $8.24B), superseding exp111's $3.15B. Papers, briefs, guide and dashboard are restated on these figures.
<!-- AUTO-RESULTS:END -->
