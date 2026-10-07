# Experiment 58 — agency-side triage rankers, packaged per state

**Date:** 2026-10-07 · **Code:** `experiments/exp58_agency_rankers.py` · **Results:** `experiments/exp58_results.json` · **Deliverable:** `deliverables/state_rankers/`

### Hypothesis

The ranker line from PA2 through exp56 used FSEARN, FSUNEARN, FSNELDER and FSNDIS. In the QC public-use file those are QC-verified values: for an income error, FSEARN already holds the corrected income. A triage tool runs before review, so it can only see what the agency had. Rebuilding the rankers on agency-side fields only should cost some lift; the question is how much, and whether the honest version is still worth deploying.

### Method

Agency-side features only: certified and reported household size, reported gross and net income, the earned-income deduction (earned ≈ 5 × RAWERND) and the derived earned/unearned split, shelter deduction, rent, utilities, SUA used, claimed medical / dependent-care / child-support deductions, homeless flag, issued benefit, plus four ratios (20 features). Never inputs: AMTERR, STATUS, any variance field, or QC-verified FS* values.

Per state (PA, NY, TX, SD, UT, ID), using the exp56 procedures: two-part HistGradientBoosting P(error) × E[$ | error], nested 5-fold CV of untuned vs random-search tuned (30 draws), time split (FY2020–22 → FY2023–24), tuned only if it beats untuned in nested CV. Expected dollars are calibrated with exp57's winning method (isotonic regression of actual dollars on the out-of-fold score). Each state's existing holdout is the final check. Then a refit on all labeled rows is written to `deliverables/state_rankers/<ST>/` (model + model card).

The holdouts have now been scored by exp56, exp57 and exp58. They are no longer untouched, but no selection was made on them here.

### Results

Holdout, top 10% / top 20% lift over random review, and dollars found per review hour in the top 20%:

| state | exp56 (QC-verified fields) | **exp58 (agency-side only)** | nested-CV top-20% lift, 56 → 58 | expected ÷ actual, top 20% |
|---|---|---|---|---|
| PA | 5.19× / 3.33×, $158/hr | **5.43× / 3.48×, $165/hr** (random $47) | 3.34 → 3.40 | 0.96 |
| NY | 5.00× / 3.44×, $193/hr | **5.20× / 3.54×, $199/hr** (random $56) | 3.31 → 3.48 | 0.93 |
| TX | 2.82× / 2.68×, $143/hr | **3.60× / 2.70×, $144/hr** (random $54) | 2.41 → 2.46 | 0.89 |
| SD | 3.39× / 2.66×, $58/hr | **2.91× / 2.75×, $60/hr** (random $22) | 2.55 → 2.70 | 0.87 |
| UT | 3.21× / 2.32×, $61/hr | **3.74× / 2.63×, $69/hr** (random $26) | 2.76 → 2.71 | 1.11 |
| ID | 4.01× / 2.79×, $62/hr | **4.12× / 2.76×, $62/hr** (random $22) | 2.96 → 3.03 | 1.25 |

Time split (train FY2020–22, test FY2023–24), top-20% lift for the chosen arm: PA 3.28×, NY 3.32×, TX 2.32×, SD 2.27×, UT 2.52×, ID 2.51×. Tuning was chosen in 5 of 6 states; PA kept the defaults.

### Verdict

The leak was real but harmless: agency-side features match or beat the QC-verified set in every state (top-20% holdout lift within −0.03 to +0.31). The useful signal is in reported income, deductions and the issued benefit, not in the verified values. Packaged rankers find 2.6–3.5× the error dollars of random review on held-out cases, and hold up when trained on 2020–22 and tested on 2023–24. Expected dollars land within ~13% for PA, NY, TX and SD; UT and ID overstate their top 20% (by 11% and 25%), the same pattern as exp57.

### Next steps

1. Pilot one state (PA or NY, the highest lift and best calibration) on a current-month case list, then compare the found error dollars against the model's forecast.
2. Refit annually; the time-split results show a one-to-two-year-old model keeps most of its lift.
3. Over-issuance-weighted variant if a state targets program savings rather than total error dollars.
