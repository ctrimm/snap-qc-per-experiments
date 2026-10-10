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

Run 2026-10-10 ~06:00, as specified.

| | eps = 0 | eps = 0.1 | eps = 0.2 | all labels |
|---|---|---|---|---|
| PA: found / 2024 lift | 60.4% / 3.49× | 59.1% / 3.47× | 59.3% / 3.48× | 60.8% / 3.64× |
| NY | 63.6% / 3.49× | 63.4% / 3.59× | 61.4% / 3.60× | 66.8% / 3.67× |
| TX | 40.3% / 2.26× | 39.5% / 2.28× | 39.3% / 2.25× | 43.4% / 2.63× |
| SD | 37.9% / 1.97× | 36.2% / 2.26× | 31.6% / 2.02× | 40.3% / 2.73× |
| UT | 44.4% / 1.97× | 44.9% / 2.24× | 44.2% / 2.25× | 52.1% / 2.67× |
| ID | 45.4% / 2.42× | 46.0% / 2.56× | 45.3% / 2.47× | 52.0% / 2.96× |
| **Mean** | **48.7% / 2.60×** | **48.2% / 2.73×** | **46.8% / 2.68×** | **52.6% / 3.05×** |

("found" = share of each year's error dollars found by the reviews actually done, FY2021–24 mean; "2024 lift" = the model's pure top-20% lift in its last year.)

### Verdict

Held, with a bigger lesson than expected.

1. **Training only on flagged reviews degrades the model.** By 2024 it reaches 2.60× against 3.05× for a model that sees every past case: about 15% less effective, and it finds about 4 points fewer error dollars a year (48.7% vs 52.6%).
2. **A 10% random slice helps a little and costs almost nothing:** 2024 lift 2.60× → 2.73×, for 0.5 points fewer dollars found on average. 20% costs more (−1.9 points) without further gain. Per-state results are noisy; the gain shows in SD, UT, ID and NY, not PA.
3. **The "all labels" arm is what a state already has.** Every year's federal QC sample is a random, fully reviewed sample of the caseload, exactly the unbiased data the loop needs. The best design isn't random pilot reviews; it's retraining each year on the state's federal QC sample **plus** the pilot's reviews, which closes most of the 2.60× → 3.05× gap.

### Next steps

1. Pilot design: retrain annually on the latest federal QC sample plus pilot findings; keep a small (about 10%) random slice of pilot reviews mainly to monitor for blind spots, not to train.
2. Add this to the whitepaper's "How the pieces fit" and recommendations.

