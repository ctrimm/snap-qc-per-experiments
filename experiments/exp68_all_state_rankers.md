# Experiment 68 — triage rankers for every state

**Date:** 2026-10-10 · **Code:** `experiments/exp68_all_state_rankers.py` · **Results:** `experiments/exp68_results.json` · **Deliverable:** `deliverables/state_rankers/<USPS>/`, map dashboard (`deliverables/state_rankers/map/`, published privately)

### Hypothesis

The exp58 agency-side ranker (2.6–3.5× random review in six POC states) generalizes to every SNAP jurisdiction, so any state can be shown its own numbers. Moves the production track from a six-state pilot to a national deliverable.

### Method

The exp58 pipeline unchanged (agency-side features; nested 5-fold CV of untuned vs random-search tuned, 30 draws; time split FY2020–22 → FY2023–24; holdout; exp57 isotonic dollar calibration; refit on all rows and package) for all 53 jurisdictions in the QC files: 50 states, DC, Guam, Virgin Islands. Holdouts: the six POC states kept their existing holdout files; every other jurisdiction got a fixed 25% holdout stratified by error status (seed 68 + state code), written to `exp68_holdouts.json` and committed before any model was fit. 8 states in parallel, 3 threads each (11:02–15:44).

### Results

- **Reproduction:** all six POC states match exp58 exactly (e.g., PA 3.475×, NY 3.540×, TX 2.696×).
- **Top-20% holdout lift:** median **3.25×**; **51 of 53** at 2.5× or better. Range: Alaska 1.26× and Wyoming 1.72× (both under 1,500 QC cases) up to Washington 3.84× and Massachusetts 4.04×.
- **Dollars per review hour (top 20%):** $48 (Wyoming) to $352 (DC).
- **Time split (train 2020–22, test 2023–24):** median 2.97×; lowest Wyoming 1.46×, Alaska 1.81×, Hawaii 2.08×.
- **Dollar forecasts (expected ÷ actual, top 20%):** median 1.03; 49 of 53 within ±20%. Outside: Alaska 1.85, West Virginia 1.26, Idaho 1.25, Montana 1.21.
- **Tuning chosen** in 25 of 53 jurisdictions.
- **Low-sample flag** (< 1,500 QC cases): Alaska, Guam, Virgin Islands, Wyoming.

### Verdict

Held. The ranker works nearly everywhere: in 51 of 53 jurisdictions the top fifth of the ranked queue holds at least 2.5× the error dollars of random review on held-out cases, and the lift survives a train-on-earlier, test-on-later split. The two exceptions are the smallest samples (Alaska, Wyoming), where five years of public QC data is too thin; a state's own case data would be needed there. Each state's holdout has now been looked at once (POC states several times); nothing was selected on it.

### Next steps

1. Cost-share scenarios on these lifts (exp69).
2. For low-sample jurisdictions, pool neighbouring states or use the state's own data before any pilot.
