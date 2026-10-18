# Replicating the FY2028 cost-share figure

The headline: ranker-guided reviews, with the fairness floor on, would avoid an estimated **$6.05B a year** of FY2028 SNAP state cost share across all 53 jurisdictions. That is the central scenario. Random reviews of the same volume would avoid $1.03B. This guide shows how to reproduce that number, how to get one state's figure, and how to run the calculation for any state with its own inputs.

Source experiment: [exp93](experiments/exp93_cost_share_current_models.md), which reran [exp69](experiments/exp69_cost_share_scenarios.md)'s scenario model on the deployed rankers. It is a scenario model, not a forecast. Quote the range, not the central figure alone.

## Quick start

From the repo root, with Python 3 and no other dependencies:

```bash
python3 experiments/cost_share_replicate.py              # national, all scenarios
python3 experiments/cost_share_replicate.py --state PA   # one state, every step shown
```

Expected national output:

| Scenario | Ranker, floor on | Random reviews |
|---|---|---|
| Low | $0.39B | $0.16B |
| **Central** | **$6.05B** | $1.03B |
| High | $10.06B | $2.39B |
| Central, top-20% lift basis (conservative) | $4.06B | — |

That is out of **$10.56B a year** the 53 jurisdictions would owe at FY2028 rules on their FY2025 error rates.

The script reads three committed files and fits no models:
- `experiments/exp93_results.json`: per-state lifts, benefits and caseloads;
- `experiments/exp69_published_per.json`: official FY2025 error rates;
- the scenario parameters below.

To rebuild those inputs from raw data, see [Full rebuild](#full-rebuild-from-raw-data).

## The model

### 1. What a state owes (H.R. 1, P.L. 119-21, Sec. 10105)

From FY2028, a state pays a share of its SNAP benefit costs set by its payment error rate (PER):

| PER | State share of benefits |
|---|---|
| under 6% | 0% |
| 6% to under 8% | 5% |
| 8% to under 10% | 10% |
| 10% or more | 15% |

**Cost share = share(PER) × annual benefits.**

For FY2028 a state may use its FY2025 or FY2026 PER. Later years use the PER from three years earlier. A state whose PER × 1.5 is 20% or more can delay to FY2029 or FY2030. The model uses FY2025 rates and does not model the delay option.

### 2. How reviews lower the error rate

Errors sit in the active caseload until the case is recertified, on average **m** months. Each month, reviews find and correct a share **c** of the caseload's error dollars:

```
c = R × L × f
```

| Symbol | Meaning |
|---|---|
| **R** | share of the caseload reviewed each month |
| **L** | the ranker's lift: error dollars found per review, as a multiple of a random review (random = 1) |
| **f** | share of found errors actually fixed going forward |
| **m** | months an error would otherwise persist |

In steady state, error dollars and the PER fall by the factor 1 / (1 + c × m):

```
PER_after = PER_now / (1 + R × L × f × m)
```

The PER is assumed to fall in proportion because the federal QC sample is a random draw from the same caseload.

### 3. Dollars avoided

```
avoided = (share(PER_now) − share(PER_after)) × annual benefits
```

The national figure is the sum over the 53 jurisdictions. Savings only happen when a state drops a bracket, so a small rate change can be worth nothing, and a change across a threshold is worth 5 to 15% of the state's benefits.

### 4. Scenario parameters (fixed in exp69 before any results)

| Scenario | R (reviewed a month) | L | f | m |
|---|---|---|---|---|
| Low | 1% | top-20% lift | 0.6 | 4 |
| Central | 2% | top-10% lift | 0.8 | 6 |
| High | 3% | top-10% lift | 0.9 | 8 |

Staffing is 30 minutes a review and 140 productive hours per FTE-month:
- reviews a month = R × households;
- FTEs = reviews a month × 0.5 / 140.

## Inputs and where they come from

| Input | Value used | Source |
|---|---|---|
| PER per state | Official FY2025 rates (national 10.62%) | USDA FNA, [FY2025 PER PDF](https://www.fna.usda.gov/sites/default/files/resource-files/snap-qcfy25-per.pdf) (dated June 24, 2026), transcribed in `experiments/exp69_published_per.json` |
| Annual benefits | Σ FYWGT × RAWBEN × 12 over each state's FY2024 QC records ($91.0B nationally) | `qc_pub_fy2024.csv` from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles) |
| Households | Σ FYWGT over the same records | same file |
| Lift L | Each state's deployed ranker, fairness floor on, measured on its own held-out QC cases (exp93; median top-10% lift 6.17×, top-20% 3.93×) | `experiments/exp93_results.json` → `measured.<STATE>.top10.floor_lift` / `top20.floor_lift` |

## Worked example: Pennsylvania (central scenario)

| Step | Calculation | Result |
|---|---|---|
| FY2025 PER | from the FNA table | 9.21% |
| Share now | 8–10% bracket | 10% |
| Annual benefits | FY2024 QC microdata | $4.18B |
| Cost share now | 10% × $4.18B | $418M a year |
| Lift (floor on, top 10%) | exp93 | 6.52× |
| c | 0.02 × 6.52 × 0.8 | 0.1043 |
| PER after | 9.21 / (1 + 0.1043 × 6) | 5.66% |
| Share after | under 6% | 0% |
| **Avoided** | (10% − 0%) × $4.18B | **$418M a year** |
| Random reviews, same volume | 9.21 / (1 + 0.02 × 1 × 0.8 × 6) = 8.40% | still 10%, $0 avoided |
| Effort | 2% × 1.05M households | about 21,000 reviews a month, 75 FTEs |

The same steps for California: 10.93% → 7.25%, the share drops from 15% to 5%, and it avoids **$1.19B a year**.

## Any state

**A state already in the 53:**

```bash
python3 experiments/cost_share_replicate.py --state CA
```

**With newer or its own numbers.** For example, a state's FY2026 PER, current benefits, a different review volume, or a lift from its own pilot:

```bash
python3 experiments/cost_share_replicate.py --state PA --per 8.7 --benefits 4.3e9 --R 0.015 --lift 5.0
```

Any flag left out keeps the committed value. `--R` overrides all three scenarios; the other scenario parameters stay as set.

**Without a trained ranker.** The script uses the 53-jurisdiction median floor-on lift (6.17× top 10%, 3.93× top 20%):

```bash
python3 experiments/cost_share_replicate.py --state XX --per 9.5 --benefits 2.0e9 --households 500000
```

**By hand or in a spreadsheet**, four cells per state: PER, benefits, households, lift. Then apply the three formulas above:

```
PER_after = PER / (1 + R*L*f*m)
share(x)  = IF(x<6,0, IF(x<8,0.05, IF(x<10,0.10,0.15)))
avoided   = (share(PER) - share(PER_after)) * benefits
```

**What to measure in a pilot.** m (how long a found error would otherwise persist) and f (the fix rate) move the answer more than the ranker does (exp73). A pilot should measure both and rerun with `--lift` from its own reviews.

## Full rebuild from raw data

This reproduces the lifts in `exp93_results.json` instead of reading them.

1. **Data:** download the FY2020–FY2024 SNAP QC public-use CSVs from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles) into `../snap-qc-data/raw/qcfy20XX_csv/`. The folder names are what the code expects.
2. **Holdouts and rankers:** the held-out cases are fixed in `experiments/exp68_holdouts.json` (25% per state, stratified, seed 68 + state code). The adopted model per state is recorded in `exp80_results.json` and `exp82_results.json`.
3. **Run:**

   ```bash
   python3 experiments/exp93_cost_share_current_models.py --workers 6
   ```

   This refits each jurisdiction's deployed ranker and measures its lift at top 10% and top 20%, with and without the fairness floor.

   It has a gate: every lift must match `exp83_results.json` exactly, or the script stops. On October 15 all 53 matched.
4. **Recompute:**

   ```bash
   python3 experiments/cost_share_replicate.py
   ```

   It should print $6.05B central.

## What the model leaves out

Treat the result as the size of the opportunity, not a forecast:
- **Timing:** whether corrections reach the cases the federal sample draws.
- **Procedural errors outside the public microdata:** published rates run 2–3 points above microdata-implied rates (exp40).
- **Behavior changes.**
- **The delay option.**
- **Review costs** beyond the FTE count.

The range across scenarios ($0.39B to $10.06B) is driven mostly by review volume and how long errors persist. Sensitivity analysis is in [exp73](experiments/exp73_cost_sensitivity.md). The fairness floor costs about $0.77B of the central figure at the top-10% basis ($6.82B without the floor).
