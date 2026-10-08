# SNAP QC triage rankers, per state

A model per POC state that ranks SNAP cases by **expected payment-error dollars**, so QC or second-party reviewers spend their hours on the cases most likely to hold large errors. Built in exp58 (`experiments/exp58_agency_rankers.md`) from FY2020–2024 QC public-use data.

## What's here

| path | contents |
|---|---|
| `<ST>/model.joblib` | P(error) classifier, log-dollar regressor, and dollar calibrator (PA, NY, TX, SD, UT, ID) |
| `<ST>/model_card.json` | training rows, features, configuration, and held-out evaluation |
| `score_cases.py` | ranks a CSV of cases with one state's model |

## How well it works (held-out cases)

| state | top 20% finds | $/review-hour, top 20% (random) | top 10% finds | expected ÷ actual $, top 20% |
|---|---|---|---|---|
| PA | 3.5× random | $165 ($47) | 5.4× | 0.96 |
| NY | 3.5× | $199 ($56) | 5.2× | 0.93 |
| TX | 2.7× | $144 ($54) | 3.6× | 0.89 |
| SD | 2.7× | $60 ($22) | 2.9× | 0.87 |
| UT | 2.6× | $69 ($26) | 3.7× | 1.11 |
| ID | 2.8× | $62 ($22) | 4.1× | 1.25 |

Assumes 30 minutes of review per case. Quote expected dollars for one state's top of queue with a ±15–20% band. UT and ID tend to overstate.

## Input

One row per case, with QC public-use column names for the fields the agency has **before** review:

`CERTHHSZ, RAWHSIZE, RAWGROSS, RAWNET, RAWERND, SHELDED, RENT, UTIL, SUA1, FSMEDEXP, FSDEPDED, FSCSEXP, HOMEDED, RAWBEN`

Plus any ID column. Blank values count as 0. No outcome or QC-verified fields are used.

## Run

```bash
python3 score_cases.py --state PA --input cases.csv --output ranked.csv --id-col CASE_ID
```

The output adds `p_error`, `expected_dollars`, `rank` and `in_top_pct` (10/20/30/50/100), sorted by expected dollars.

## Requirements and cautions

- numpy, joblib, and scikit-learn matching `sklearn_version` in the model card (built with 1.9.1). Other versions may fail to load or score differently.
- `model.joblib` is a pickle: load only copies from this repository.
- Trained on QC samples, which are representative of each state's active caseload. Cases far outside that population (new programs, policy changes) need a refit.
- It ranks cases for review; it doesn't decide anything about a household. Refit yearly.
