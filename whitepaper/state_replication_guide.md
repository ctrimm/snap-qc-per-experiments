# Replicating the SNAP Error-Ranking Work for Your State

**October 23, 2026 · Replication guide · Cory Trimm**

## Who this is for

This guide is for a state SNAP team that wants to know what the error-ranking tool would do for their state, and then try it. It assumes one analyst comfortable running Python scripts, and a program or QC lead who can answer questions about case data and review practice. No machine-learning background is needed for levels 1 and 2.

The work behind it is described in the *Project Summary* and in short briefs for Pennsylvania, New York, Texas, South Dakota, Utah, Idaho and Wyoming. The code is open: [github.com/ctrimm/snap-qc-per-experiments](https://github.com/ctrimm/snap-qc-per-experiments).

**What you get, in four levels:**

| Level | Time | What you get |
|---|---|---|
| 1. Look up your state | An hour | Your state's measured results and cost-share scenarios from the published models |
| 2. Reproduce from public data | An afternoon | The same numbers, recomputed on your machine from the federal files |
| 3. Score your own cases | A few days | A ranked review queue for your current caseload, using the packaged model |
| 4. Pilot and refit | Three to six months | Measured dollars found in your state, and a model refit on your own data |

**In plain terms:** the tool reads a few fields your agency already records for every active case (income, deductions, housing costs, household size, the benefit paid). From those it estimates how many error dollars each case is likely to hold. Reviewers start at the top of that list instead of choosing at random. Across all 53 jurisdictions, the top fifth of the list held a median of four times the error dollars of a random fifth. Nothing about a household is decided by the tool; it only orders the review queue.

## What you need

- **A computer:** any laptop with Python 3.10 or newer. No GPU and no cloud service.
- **Software:** the repository plus numpy, joblib and scikit-learn 1.9.1 (exactly that version: the saved models are pickles tied to it, and other versions may refuse to load them or score differently).
- **Public data (levels 2–4):** the FY2020–2024 SNAP QC public-use CSV files from [snapqcdata.net/datafiles](https://snapqcdata.net/datafiles), unzipped beside the repository.
- **Your state's data (levels 3–4):** an extract of active cases with the fields in *Level 3, Step 1*, and later your own review findings.

```bash
git clone https://github.com/ctrimm/snap-qc-per-experiments.git
cd snap-qc-per-experiments
python3 -m pip install numpy joblib scikit-learn==1.9.1
# data layout the code expects (a sibling of the repository):
#   ../snap-qc-data/raw/qcfy2020_csv/qc_pub_fy2020.csv  ...  ../snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv
```

## Level 1: look up your state

Every jurisdiction's results are committed in the repository. Replace `XX` with your state's USPS code:

```bash
# held-out results of your state's deployed model: lift, $ per review hour, forecast check, fairness
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_results.json'))['XX'], indent=1))"
# FY2028 cost-share scenarios, every step shown
python3 experiments/cost_share_replicate.py --state XX
```

How to read the first output:

| Field | Meaning |
|---|---|
| `top20.lift` | Error dollars found in the top 20% of the queue, as a multiple of random review. 51 of 53 jurisdictions fall between 3 and 4.5 (median 3.97) |
| `top10.lift` | The same for the top 10%. 52 of 53 fall between 5 and 8 (median 6.38) |
| `top20.per_hour_$` (`random_per_hour_$`) | Error dollars found per review hour, assuming 30-minute reviews |
| `top20.expected_over_actual` | The model's dollar forecast divided by actual dollars; 1.0 is perfect |
| `fairness.baseline_ratio` | Each household type's share of reviews ÷ its share of error dollars, ranking by dollars only (1.0 = proportionate) |
| `fairness.floor_ratio`, `floor_lift` | The same with the fairness floor on, and the lift that remains |
| `variant` | `B_ctx`: pooled with every state plus state context; `C_ctx`: the same with your own cases weighted ten times |

**The cost-share script** reads your state's official FY2025 error rate and annual benefits, then shows the low, central and high scenarios. It gives the rate after ranked reviews, the share owed, dollars avoided, and the reviews and FTEs needed. To try your own assumptions:

```bash
python3 experiments/cost_share_replicate.py --state XX --per 8.7          # a newer error rate
python3 experiments/cost_share_replicate.py --state XX --R 0.015          # review 1.5% of cases a month
python3 experiments/cost_share_replicate.py --state XX --benefits 2.1e9   # current annual benefits
```

**Find your break-even review rate.** Savings happen only when the rate drops below a bracket line (6%, 8%, 10%). Raise `--R` until the central line's share drops: that's how much review it takes to cross the next line. `COST-SHARE-REPLICATE.md` explains the model and every parameter.

## Level 2: reproduce from public data

This refits every jurisdiction's deployed model from the federal files and checks it against the committed results:

```bash
python3 experiments/exp83_context_models_full_eval.py --workers 8
git diff --stat experiments/exp83_results.json     # empty = exact reproduction
```

**What the script does:**
- **Data split:** for each jurisdiction it trains on 75% of that state's QC cases pooled with all other states' cases, and scores the 25% set aside. The held-out cases are fixed in `experiments/exp68_holdouts.json`, so everyone gets the same split.
- **Models:** two gradient-boosted models, one for the chance of an error and one for its dollars. Expected dollars are calibrated by isotonic regression on out-of-fold predictions.
- **Reproducibility:** results are deterministic.

On a Mac Studio (M3 Ultra) it took about 8 minutes with 8 workers (about 2 CPU-hours in all) and reproduced `exp83_results.json` byte for byte on October 23, 2026. We haven't timed it on a laptop; at about 2 CPU-hours, a 4-core machine should need roughly 30–60 minutes.

**Cost-share inputs too:**

```bash
python3 experiments/exp93_cost_share_current_models.py --workers 6   # refits and measures lifts with the floor; stops unless all match
python3 experiments/cost_share_replicate.py
```

**Checking how a state's model was chosen:** the adoption rule is in `experiments/exp82_context_all_states.py` (41 larger jurisdictions) and `exp80_state_context.py` (12 small ones). A pooled variant replaced the state-only model only if it was better on both held-out cases and a later-years test (train 2020–22, test 2023–24). The results are in `exp80_results.json` and `exp82_results.json`.

## Level 3: score your own cases

### Step 1: build the input file

One row per active case, with these columns (QC public-use names). Blank values count as 0.

| Column | What it holds |
|---|---|
| `CERTHHSZ` | Certified household size (people in the SNAP unit) |
| `RAWHSIZE` | Number of people in the household |
| `RAWGROSS` | Gross countable monthly income |
| `RAWNET` | Net monthly income after deductions |
| `RAWERND` | Earned income deduction (20% of earnings) |
| `SHELDED` | Excess shelter deduction |
| `RENT` | Rent or mortgage |
| `UTIL` | Utility costs |
| `SUA1` | Standard utility allowance code; codes 3–8 mean an SUA was used |
| `FSMEDEXP` | Medical expense deduction |
| `FSDEPDED` | Dependent care deduction |
| `FSCSEXP` | Child support deduction |
| `HOMEDED` | 1 if the homeless shelter deduction was used |
| `RAWBEN` | Monthly benefit issued |
| `BENMAX` | Maximum allotment for the household's size |

Add any case ID column you want carried through. All fields are monthly dollar amounts or counts as recorded **before** any review. Never include review findings or corrected values. The QC technical documentation in the data download defines each field exactly, and your eligibility system's field definitions may differ slightly. Note the differences.

### Step 2: score

```bash
python3 deliverables/state_rankers/score_cases.py --state XX --input cases.csv --output ranked.csv --id-col CASE_ID
```

The output adds four columns:

| Column | Meaning |
|---|---|
| `p_error` | Chance the case has an error |
| `expected_dollars` | Expected error dollars, calibrated |
| `rank` | Position in the review queue |
| `in_top_pct` | Which top bucket the case is in: 10, 20, 30, 50 or 100 |

The script also prints the total expected error dollars in the top 20%. Quote it with a ±15–20% band.

### Step 3: sanity checks before anyone reviews

- **Spot-check the inputs:** compare the distribution of `RAWBEN`, `RAWGROSS` and household size with your caseload reports. A field mapped to the wrong unit (annual instead of monthly, cents instead of dollars) is the most common failure.
- **Look at the top 50 cases with a QC lead.** Do they look like cases that deserve review?
- **Turn on the fairness floor.** Check each household type's share of the top of the queue against its share of the caseload (see *Fairness* below).

**About the packaged models:** each `deliverables/state_rankers/XX/model.joblib` was refit on all five years of that state's cases plus every other state's, for the best possible model. Its held-out performance is the evaluation fit in `exp83_results.json`. The `evaluation` block inside `model_card.json` is from the earlier state-only model; use `exp83_results.json`.

## Level 4: pilot and refit

### A three-month shadow pilot

1. **Each month,** score active cases and give reviewers a sample from the top of the queue alongside their usual selection.
2. **Keep about 10% of reviews on randomly chosen cases.** This is your control, and it shows the model's blind spots.
3. **For every review, record:**
   - error yes or no;
   - over or under, and the dollars;
   - which part of the case (element);
   - roughly when the underlying change happened.
4. **Compare:**
   - dollars found per review hour, top of queue vs random slice vs usual selection;
   - dollars found vs `expected_dollars`;
   - each household type's share of reviews vs its share of errors.

### What to report

These are the two numbers that move the cost-share estimate most. Rerun `cost_share_replicate.py --state XX --lift <your measured lift>` with them in mind:

| Measure | How | Why it matters |
|---|---|---|
| Lift | Error dollars per review, top of queue ÷ random slice | The tool's actual value in your state |
| Error lifetime (m) | How long found errors had lasted, and would have lasted until recertification | Drives the cost-share range more than the lift |
| Fix rate (f) | Share of found errors corrected going forward | Same |
| Forecast accuracy | Σ expected ÷ Σ actual dollars, top 20% | Whether you can budget from the forecast |
| Fairness | Review share ÷ error share by household type | Whether the floor is working |

### Fairness

Ranking purely by dollars under-reviews elderly households (a review share below 0.8 of their error share) in 49 of 53 jurisdictions, and disabled households in 30 of 51 (current models, exp83). The fairness floor (exp72) guarantees each household type a share of reviews in line with its share of errors. With the floor on, no jurisdiction leaves elderly households below 0.8, and 2 leave disabled households below it. The median lift falls from 3.97× to 3.93× (about 1%). State by state the cost varies: the median state gives up 1.5% of its lift; Pennsylvania 3%, New York 6%, Wyoming 13%, Hawaii 15%. In 11 states the floor's lift comes out slightly higher than without it, a chance effect on the held-out cases. Each state's figure is in the appendix. Keep it on by default.

### Underpayments

The main ranker mostly finds overpayments. A second ranker trained on underpayments (exp79) finds a median of 3.4 times the underpayment dollars of random review, against 1.5 times for the main ranker, and does better in every jurisdiction. States with many underpayments (Wyoming: 54% of error dollars) should run both queues.

### Refitting on your own data

Your own review findings, from the pilot and from routine second-party reviews, can improve the model. Two rules, from a simulation over four years in six states (exp67):
- **Never retrain only on the cases the model flagged.** It stops learning about errors it doesn't flag, and lost about 15% of its edge in four years in that simulation. Always include the yearly federal QC sample (random and fully reviewed) and the pilot's random slice.
- **Refresh once a year,** when the new QC public-use file is released.

**The code change:** the training code reads cases in the QC public-use layout (`experiments/exp58_agency_rankers.py`, `load_state`; the year list `FY_FILES`). The input fields above plus `STATUS` (1 correct, 2 overpaid, 3 underpaid) and `AMTERR` (error dollars) are all it needs. Export your reviewed cases in that layout as an extra year's file, add it to `FY_FILES`, and rerun the fit for your state. This is a small change. Keep the federal years in, and hold out a recent slice of your own cases to test on before replacing the packaged model.

### Flag cards (optional)

A flag card tells the reviewer why a case was flagged and which parts to check first. Its top three items included the real error for 86–88% of flagged errors in Pennsylvania and New York. The card logic is in `experiments/exp62_*`, `exp65_*` and `exp74_*`. The "check first" model needs about 100–200 labelled error cases from your state to beat generic advice (exp63), which a pilot produces in a few months.

### Your state's policy library (optional)

Rule citations on flag cards, and any policy-lookup assistant, read from **state-policy-docs** ([github.com/ctrimm/state-policy-docs](https://github.com/ctrimm/state-policy-docs)). It is thorough for federal rules and California (755 California SNAP documents) but thin for most states (Pennsylvania 3 SNAP documents, New York 5, Wyoming 1).

**To add your state's manual:** follow `AGENTS.md` in that repository (`pipeline/ingest.py`). Each document becomes a Markdown file with front matter for jurisdiction and effective dates. Then link citations, check the links, and run the tests:

```bash
.venv/bin/python pipeline/link_citations.py
.venv/bin/python pipeline/check_links.py
.venv/bin/python -m unittest discover -s tests
```

**One lesson from California:** keep superseded or older guidance reachable by citation rather than in search (`STATE_POLICY_CITED_LETTERS=cite_only`). Mixing hundreds of old letters into search pushed current rules out of the top results.

## Checklist

| Step | Done when |
|---|---|
| Level 1 | You have your state's `exp83_results.json` entry and the cost-share output, and know your break-even review rate |
| Level 2 | `exp83_context_models_full_eval.py` reproduces `exp83_results.json` with an empty `git diff` |
| Level 3 | `score_cases.py` ranks a month of your cases, the inputs pass the sanity checks, and a QC lead has looked at the top 50 |
| Level 4 | Three months of shadow reviews with a random slice; lift, forecast accuracy, error lifetime, fix rate and fairness measured; cost share rerun with your lift |
| Refresh | Yearly refit including the new federal QC sample and your random-slice reviews |

## Cautions

- **The tool prioritizes; it doesn't decide.** Every determination about a household stays with a person.
- **Cost-share figures are scenarios, not forecasts.** They leave out:
  - timing relative to the federal sample month;
  - procedural errors outside the public file;
  - behavior changes;
  - the delay option;
  - the cost of reviews.
- **Small states:** with fewer than about 1,500 QC cases (Alaska, Guam, the Virgin Islands, Wyoming), held-out results are less certain. Check them against your own reviews before quoting forecasts.
- **Never touch the federal QC sample.** The tool is for a state's own reviews of active cases; the federal sample stays random by law.
- **`model.joblib` files are pickles.** Load only copies from this repository.

## Appendix: every jurisdiction

Generated from the committed results by `python3 whitepaper/state_numbers.py table`; rank 1 is best of 53.

| Column | Meaning |
|---|---|
| Top 20% / top 10% lift | Held-out results (exp83) |
| Later years | Trained on 2020–22, tested on 2023–24 (exp80/exp82) |
| With floor (cost) | Top-20% lift with the fairness floor, and the share of lift it gives up; negative means the floor came out slightly ahead by chance |
| QC cases | FY2020–24 (exp68) |
| Central: avoided a year | The FY2028 cost-share scenario (exp93); "—" means no bracket change, or a rate already under 6% |

<!-- STATE-TABLE:START -->
| Jurisdiction | Top 20% lift (rank) | Top 10% lift (rank) | Later years (rank) | With floor (cost) | Forecast ÷ actual | QC cases | FY2025 rate | Central: avoided a year |
|---|---|---|---|---|---|---|---|---|
| WA | 4.54× (1) | 7.84× (1) | 4.31× (1) | 4.51× (+0.7%) | 0.98 | 3,060 | 6.98% | $95M |
| IA | 4.35× (2) | 7.19× (2) | 3.81× (25) | 4.23× (+2.8%) | 0.94 | 3,892 | 5.34% | — |
| OR | 4.33× (3) | 7.11× (3) | 4.21× (3) | 4.26× (+1.5%) | 0.90 | 3,037 | 14.14% | $79M |
| MA | 4.32× (4) | 7.01× (5) | 4.29× (2) | 4.20× (+2.9%) | 1.06 | 3,483 | 12.49% | $258M |
| AZ | 4.32× (5) | 7.02× (4) | 4.20× (4) | 4.29× (+0.6%) | 1.08 | 3,352 | 10.80% | $196M |
| CO | 4.23× (6) | 6.97× (6) | 3.91× (15) | 4.12× (+2.8%) | 1.09 | 3,595 | 10.09% | $127M |
| IL | 4.22× (7) | 6.54× (18) | 4.12× (5) | 4.14× (+1.9%) | 0.96 | 3,246 | 14.67% | $221M |
| MS | 4.22× (8) | 6.72× (14) | 3.88× (18) | 4.07× (+3.5%) | 0.97 | 4,158 | 9.51% | $79M |
| AL | 4.21× (9) | 6.71× (15) | 3.99× (10) | 4.11× (+2.4%) | 1.05 | 4,163 | 9.52% | $171M |
| CT | 4.19× (10) | 6.72× (13) | 4.01× (8) | 4.16× (+0.8%) | 1.01 | 3,818 | 9.08% | $90M |
| ND | 4.19× (11) | 6.72× (12) | 3.74× (33) | 4.07× (+2.8%) | 0.99 | 1,691 | 9.89% | $5M |
| NY | 4.18× (12) | 6.96× (7) | 4.07× (6) | 3.94× (+5.8%) | 0.94 | 3,257 | 13.18% | $360M |
| NC | 4.17× (13) | 6.84× (10) | 3.91× (16) | 4.15× (+0.5%) | 1.06 | 3,983 | 7.36% | $141M |
| OH | 4.17× (14) | 6.94× (8) | 3.88× (19) | 4.14× (+0.7%) | 0.96 | 3,475 | 6.76% | $152M |
| NJ | 4.17× (15) | 6.84× (11) | 3.80× (28) | 3.95× (+5.3%) | 0.94 | 2,327 | 6.86% | $92M |
| SD | 4.16× (16) | 6.38× (27) | 3.88× (17) | 3.96× (+5.0%) | 1.10 | 2,365 | 2.47% | — |
| FL | 4.14× (17) | 6.49× (19) | 3.81× (24) | 4.11× (+0.7%) | 0.96 | 3,745 | 12.97% | $325M |
| WI | 4.09× (18) | 6.41× (26) | 3.95× (12) | 4.04× (+1.3%) | 1.11 | 3,979 | 5.72% | — |
| KY | 4.08× (19) | 6.86× (9) | 3.73× (34) | 4.12× (-1.1%) | 0.98 | 4,073 | 4.70% | — |
| PA | 4.08× (20) | 6.55× (17) | 3.82× (23) | 3.96× (+2.8%) | 0.99 | 3,268 | 9.21% | $418M |
| NM | 4.07× (21) | 6.47× (21) | 3.94× (13) | 3.87× (+5.0%) | 1.02 | 3,845 | 16.81% | — |
| RI | 4.05× (22) | 6.28× (28) | 3.97× (11) | 3.98× (+1.5%) | 0.96 | 3,435 | 12.42% | $34M |
| ME | 4.04× (23) | 6.42× (24) | 3.85× (20) | 3.95× (+2.2%) | 1.02 | 3,434 | 10.81% | $35M |
| TN | 4.01× (24) | 6.22× (31) | 3.80× (27) | 4.12× (-2.8%) | 1.05 | 3,807 | 9.44% | $153M |
| OK | 4.00× (25) | 6.16× (33) | 3.85× (21) | 3.82× (+4.6%) | 1.07 | 3,829 | 11.04% | $150M |
| DE | 3.99× (26) | 6.45× (22) | 3.82× (22) | 4.05× (-1.6%) | 0.91 | 1,652 | 16.00% | $12M |
| IN | 3.97× (27) | 6.12× (35) | 3.79× (29) | 3.75× (+5.5%) | 1.03 | 3,237 | 9.77% | $70M |
| VI | 3.96× (28) | 6.24× (29) | 3.38× (47) | 3.67× (+7.1%) | 1.15 | 998 | 5.36% | — |
| DC | 3.94× (29) | 5.66× (45) | 3.92× (14) | 3.72× (+5.7%) | 0.99 | 2,689 | 18.66% | — |
| GA | 3.94× (30) | 5.75× (43) | 3.99× (9) | 3.96× (-0.5%) | 0.94 | 3,902 | 15.21% | $152M |
| VT | 3.94× (31) | 6.22× (32) | 4.03× (7) | 3.93× (+0.3%) | 0.99 | 2,720 | 5.38% | — |
| MT | 3.93× (32) | 6.45× (23) | 3.50× (42) | 3.83× (+2.6%) | 1.06 | 2,421 | 8.86% | $16M |
| MN | 3.93× (33) | 6.48× (20) | 3.54× (40) | 4.03× (-2.5%) | 0.99 | 4,077 | 12.58% | $86M |
| MO | 3.92× (34) | 6.00× (37) | 3.79× (30) | 3.67× (+6.4%) | 1.02 | 2,933 | 8.67% | $145M |
| NH | 3.91× (35) | 5.88× (41) | 3.43× (44) | 3.92× (-0.3%) | 0.99 | 2,328 | 8.85% | $15M |
| SC | 3.88× (36) | 6.23× (30) | 3.79× (31) | 3.87× (+0.2%) | 0.99 | 3,737 | 8.80% | $126M |
| NE | 3.88× (37) | 5.92× (39) | 3.52× (41) | 3.66× (+5.6%) | 1.00 | 3,738 | 5.90% | — |
| UT | 3.88× (38) | 6.02× (36) | 3.61× (37) | 3.71× (+4.3%) | 1.00 | 4,101 | 5.54% | — |
| AR | 3.85× (39) | 6.60× (16) | 3.30× (51) | 3.83× (+0.6%) | 0.93 | 3,430 | 8.81% | $48M |
| MI | 3.83× (40) | 5.88× (40) | 3.75× (32) | 3.78× (+1.4%) | 1.06 | 3,460 | 9.89% | $150M |
| NV | 3.83× (41) | 6.42× (25) | 3.81× (26) | 3.90× (-1.9%) | 1.12 | 4,047 | 6.22% | $51M |
| WY | 3.79× (42) | 5.35× (51) | 2.91× (53) | 3.28× (+13.3%) | 0.90 | 1,191 | 3.96% | — |
| LA | 3.77× (43) | 5.95× (38) | 3.66× (36) | 3.77× (-0.2%) | 1.01 | 3,325 | 8.14% | $186M |
| VA | 3.75× (44) | 5.76× (42) | 3.48× (43) | 3.55× (+5.4%) | 0.96 | 2,942 | 12.32% | $86M |
| TX | 3.62× (45) | 5.69× (44) | 3.31× (50) | 3.62× (-0.2%) | 1.03 | 3,457 | 9.34% | $343M |
| HI | 3.61× (46) | 5.25× (52) | 3.29× (52) | 3.06× (+15.4%) | 1.03 | 2,009 | 10.92% | $69M |
| WV | 3.61× (47) | 5.57× (46) | 3.58× (39) | 3.47× (+4.0%) | 1.13 | 3,268 | 6.69% | $25M |
| KS | 3.61× (48) | 5.40× (49) | 3.36× (48) | 3.67× (-1.7%) | 0.96 | 3,698 | 9.44% | $19M |
| CA | 3.56× (49) | 5.49× (48) | 3.61× (38) | 3.56× (+0.1%) | 1.05 | 3,108 | 10.93% | $1192M |
| ID | 3.56× (50) | 5.53× (47) | 3.35× (49) | 3.52× (+0.9%) | 0.93 | 3,839 | 3.85% | — |
| MD | 3.47× (51) | 5.37× (50) | 3.42× (45) | 3.56× (-2.6%) | 1.08 | 2,279 | 13.08% | $73M |
| GU | 3.47× (52) | 6.15× (34) | 3.66× (35) | 3.47× (+0.0%) | 1.01 | 732 | 11.70% | $12M |
| AK | 2.96× (53) | 3.58× (53) | 3.40× (46) | 2.83× (+4.5%) | 1.39 | 1,367 | 23.15% | — |
| **Median** | 3.97× | 6.38× | 3.80× | 3.93× (+1.5%) | 1.00 | | | |
<!-- STATE-TABLE:END -->
