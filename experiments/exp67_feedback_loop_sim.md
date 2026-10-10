# Experiment 67 — simulating the pilot feedback loop, with random reviews

**Date:** 2026-10-10 · **Code:** `experiments/exp67_feedback_loop_sim.py` · **Results:** `experiments/exp67_results.json`

## Pre-registration (committed before the run)

### Question

In a pilot, the ranker is retrained each year on what reviewers find, but reviewers only see the cases it flags, so the model could lock in its own blind spots. The proposed safeguard is to spend a share of the review budget (epsilon) on random cases. How much does that cost in dollars found now, and how much does it protect the model's quality later?

### Fixed in advance

- States: PA, NY, TX, SD, UT, ID; agency-side features (exp58), default ranker settings.
- Cold start: train on all FY2020 cases (the state's past QC records).
- Each year FY2021–24: score that year's cases; review 20%, of which (1 − eps) are top-scored and eps random among the rest; add **only reviewed cases** to training; retrain.
- eps = 0, 0.1, 0.2 (10 random seeds for eps > 0); reference "all labels" retrains on every past case.
- Metrics, prospective each year: share of the year's error dollars found by the reviews done; the current model's pure top-20% lift (its quality). Report 2021–24 means and the 2024 lift, per state and averaged.
- Caveat stated in advance: QC samples are 470–900 cases a state a year, so per-state results are noisy; the six-state average is the headline.

## Results

_Pending._
