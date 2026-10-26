# Replicating the SNAP Error-Ranking Work for Your State

**October 26, 2026 (corrected; first version October 23) · Replication guide · Cory Trimm**


> **Corrected October 26, 2026.** The October 23 version overstated the tool's results. The models used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure here comes from the leak-free rebuild (experiment 107); the packaged models no longer use the issued benefit. The leak-free feature set is the code's default (`SNAPQC_FEATURES=leakfree`).

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

**In plain terms:** the tool reads a few fields your agency already records for every active case (income, deductions, housing costs, household size, the household's maximum allotment). From those it estimates how many error dollars each case is likely to hold. Reviewers start at the top of that list instead of choosing at random. Across all 53 jurisdictions, the top fifth of the list held a median of 2.7 times the error dollars of a random fifth. Nothing about a household is decided by the tool; it only orders the review queue.

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
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_leakfree_results.json'))['XX'], indent=1))"
# FY2028 cost-share scenarios, every step shown
python3 experiments/cost_share_replicate.py --state XX
```

How to read the first output:

| Field | Meaning |
|---|---|
| `top20.lift` | Error dollars found in the top 20% of the queue, as a multiple of random review. 52 of 53 jurisdictions fall between 2.0 and 3.7 (median 2.70) |
| `top10.lift` | The same for the top 10%. Range 2.1 to 4.8 (median 3.31) |
| `top20.per_hour_$` (`random_per_hour_$`) | Error dollars found per review hour, assuming 30-minute reviews |
| `top20.expected_over_actual` | The model's dollar forecast divided by actual dollars; 1.0 is perfect |
| `fairness.baseline_ratio` | Each household type's share of reviews ÷ its share of cases with an error, ranking by dollars only (1.0 = reviewed in proportion to risk) |
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
git diff --stat experiments/exp83_leakfree_results.json     # empty = exact reproduction (leak-free is the default)
```

**What the script does:**
- **Data split:** for each jurisdiction it trains on 75% of that state's QC cases pooled with all other states' cases, and scores the 25% set aside. The held-out cases are fixed in `experiments/exp68_holdouts.json`, so everyone gets the same split.
- **Models:** two gradient-boosted models, one for the chance of an error and one for its dollars. Expected dollars are calibrated by isotonic regression on out-of-fold predictions.
- **Reproducibility:** results are deterministic.

On a Mac Studio (M3 Ultra) it took about 7–8 minutes with 8 workers (about 2 CPU-hours in all). The published pre-exp106 run reproduced `exp83_results.json` byte for byte on October 23, 2026 (now `SNAPQC_FEATURES=legacy`); the leak-free run reproduced exp106's leak-free figures in all 53 jurisdictions on October 26. We haven't timed it on a laptop; at about 2 CPU-hours, a 4-core machine should need roughly 30–60 minutes.

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

The script also prints the total expected error dollars in the top 20%. Quote it with a ±20% band: leak-free forecasts land within 20% of actual in 43 of 53 jurisdictions.

### Step 3: sanity checks before anyone reviews

- **Spot-check the inputs:** compare the distribution of `RAWGROSS`, `RAWNET` and household size with your caseload reports. A field mapped to the wrong unit (annual instead of monthly, cents instead of dollars) is the most common failure.
- **Look at the top 50 cases with a QC lead.** Do they look like cases that deserve review?
- **Turn on the fairness floor.** Check each household type's share of the top of the queue against its share of the caseload (see *Fairness* below).

**About the packaged models:** each `deliverables/state_rankers/XX/model.joblib` was refit on all five years of that state's cases plus every other state's, for the best possible model. Since exp107 they are leak-free: they do not use the issued benefit. Their held-out performance is the evaluation fit in `exp83_leakfree_results.json`. The `evaluation` block inside `model_card.json` is from the earlier state-only model; use `exp83_leakfree_results.json`.

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

Ranking purely by dollars under-reviews elderly households (a review share below 0.8 of their share of error cases) in all 53 jurisdictions (median 0.33), and disabled households in 47 of 51 (median 0.63; leak-free models, exp107). The fairness floor (exp72) guarantees each household type a share of reviews in line with its share of errors. With the floor on, no jurisdiction leaves elderly households below 0.8, and 2 leave disabled households below it. It is not free: the median lift falls from 2.70× to 2.42×, and the median state gives up about 10% of its lift. Pennsylvania gives up almost nothing, California 2%, New York 16%, Texas 17%, and five states more than 20% (Maine, Utah, Hawaii, Wyoming, Missouri; at most 32%). Each state's figure is in the appendix. We still recommend it on by default; a state that turns it off should know who loses review.

### Underpayments

The main ranker mostly finds overpayments. A second ranker trained on underpayments (exp79, leak-free) finds a median of 1.8 times the underpayment dollars of random review, against 1.5 times for the main ranker, and does better in 36 of 53 jurisdictions; the earlier figure of 3.4 times was mostly the leak. States with many underpayments (Wyoming: 54% of error dollars) should run both queues.

### Refitting on your own data

Your own review findings, from the pilot and from routine second-party reviews, can improve the model. Two rules:
- **Retrain on the yearly federal QC sample as well as your own findings.** It is random, fully reviewed and free. An early simulation (exp67) suggested that retraining only on flagged cases would lose about 15% of the tool's edge in four years; rechecked without the leak (exp108) it found no measurable loss, so treat this as good practice, not a measured safeguard. Keep the pilot's random slice to check the forecast.
- **Refresh once a year,** when the new QC public-use file is released.

**The code change:** the training code reads cases in the QC public-use layout (`experiments/exp58_agency_rankers.py`, `load_state`; the year list `FY_FILES`). The input fields above plus `STATUS` (1 correct, 2 overpaid, 3 underpaid) and `AMTERR` (error dollars) are all it needs. Export your reviewed cases in that layout as an extra year's file, add it to `FY_FILES`, and rerun the fit for your state. This is a small change. Keep the federal years in, and hold out a recent slice of your own cases to test on before replacing the packaged model.

### Flag cards (optional)

A flag card tells the reviewer why a case was flagged and which parts to check first. Its top three items included the real error for 83% (Pennsylvania) and 89% (New York) of flagged errors on the leak-free models (exp108). A fixed list of each state's three most common error locations would cover about 79–80%, so most of that coverage is base rate; the model's value is mostly in which item it lists first. The card logic is in `experiments/exp62_*`, `exp65_*` and `exp74_*`. The "check first" model needs about 100–200 labelled error cases from your state to beat generic advice (exp63, measured on the earlier models), which a pilot produces in a few months.

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
| Level 1 | You have your state's `exp83_leakfree_results.json` entry and the cost-share output, and know your break-even review rate |
| Level 2 | `exp83_context_models_full_eval.py` reproduces `exp83_leakfree_results.json` with an empty `git diff` |
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
| Top 20% / top 10% lift | Held-out results, leak-free (exp83 design, exp107) |
| Later years | Trained on 2020–22, tested on 2023–24 (exp107) |
| With floor (cost) | Top-20% lift with the fairness floor, and the share of lift it gives up; negative means the floor came out slightly ahead by chance |
| QC cases | FY2020–24 (exp68) |
| Central: avoided a year | The FY2028 cost-share scenario (exp93 design, leak-free); "—" means no bracket change, or a rate already under 6% |

<!-- STATE-TABLE:START -->
| Jurisdiction | Top 20% lift (rank) | Top 10% lift (rank) | Later years (rank) | With floor (cost) | Forecast ÷ actual | QC cases | FY2025 rate | Central: avoided a year |
|---|---|---|---|---|---|---|---|---|
| WA | 3.67× (1) | 4.77× (1) | 3.18× (2) | 3.31× (+9.6%) | 0.91 | 3,060 | 6.98% | $95M |
| MA | 3.21× (2) | 4.52× (5) | 3.17× (3) | 2.90× (+9.9%) | 0.87 | 3,483 | 12.49% | $129M |
| KY | 3.10× (3) | 4.38× (6) | 2.90× (8) | 2.78× (+10.2%) | 0.87 | 4,073 | 4.70% | — |
| AZ | 3.08× (4) | 4.64× (2) | 3.44× (1) | 2.98× (+3.2%) | 1.27 | 3,352 | 10.80% | $196M |
| NY | 3.05× (5) | 4.28× (7) | 3.14× (4) | 2.55× (+16.4%) | 1.01 | 3,257 | 13.18% | $360M |
| VI | 3.00× (6) | 4.60× (3) | 2.79× (12) | 3.25× (-8.1%) | 0.92 | 998 | 5.36% | — |
| OH | 2.98× (7) | 3.63× (19) | 2.65× (22) | 2.45× (+17.9%) | 0.87 | 3,475 | 6.76% | $152M |
| CT | 2.98× (8) | 4.17× (8) | 2.82× (11) | 2.76× (+7.3%) | 0.92 | 3,818 | 9.08% | $45M |
| NC | 2.98× (9) | 4.52× (4) | 2.49× (33) | 2.76× (+7.3%) | 0.96 | 3,983 | 7.36% | $141M |
| NV | 2.97× (10) | 3.77× (16) | 2.68× (20) | 2.61× (+12.3%) | 1.03 | 4,047 | 6.22% | $51M |
| OR | 2.95× (11) | 4.13× (9) | 3.09× (5) | 2.67× (+9.3%) | 1.14 | 3,037 | 14.14% | — |
| IN | 2.93× (12) | 3.90× (12) | 2.77× (15) | 2.81× (+3.9%) | 1.06 | 3,237 | 9.77% | $70M |
| CO | 2.91× (13) | 4.10× (10) | 2.77× (14) | 2.86× (+1.7%) | 0.80 | 3,595 | 10.09% | $127M |
| MO | 2.85× (14) | 3.08× (34) | 2.66× (21) | 1.94× (+31.9%) | 1.00 | 2,933 | 8.67% | $73M |
| NM | 2.85× (15) | 3.12× (31) | 2.72× (17) | 2.40× (+15.7%) | 1.19 | 3,845 | 16.81% | — |
| SD | 2.82× (16) | 2.59× (50) | 2.63× (25) | 2.50× (+11.1%) | 0.83 | 2,365 | 2.47% | — |
| AL | 2.81× (17) | 3.66× (18) | 2.69× (19) | 2.37× (+15.7%) | 0.99 | 4,163 | 9.52% | $85M |
| WI | 2.80× (18) | 3.32× (26) | 2.47× (35) | 2.40× (+14.6%) | 0.99 | 3,979 | 5.72% | — |
| MS | 2.80× (19) | 3.83× (15) | 2.69× (18) | 2.55× (+8.8%) | 0.85 | 4,158 | 9.51% | $40M |
| IL | 2.79× (20) | 3.47× (25) | 2.84× (10) | 2.71× (+3.1%) | 0.89 | 3,246 | 14.67% | — |
| IA | 2.76× (21) | 4.01× (11) | 2.93× (7) | 2.48× (+10.0%) | 0.82 | 3,892 | 5.34% | — |
| ND | 2.76× (22) | 3.02× (37) | 2.31× (42) | 2.23× (+19.0%) | 1.08 | 1,691 | 9.89% | $5M |
| DE | 2.74× (23) | 3.48× (24) | 2.78× (13) | 2.60× (+5.1%) | 0.96 | 1,652 | 16.00% | — |
| NJ | 2.73× (24) | 3.53× (22) | 2.49× (32) | 2.21× (+19.2%) | 0.95 | 2,327 | 6.86% | $92M |
| DC | 2.70× (25) | 3.83× (14) | 2.95× (6) | 2.42× (+10.4%) | 1.23 | 2,689 | 18.66% | — |
| VT | 2.70× (26) | 3.09× (33) | 2.58× (29) | 2.48× (+8.4%) | 1.21 | 2,720 | 5.38% | — |
| PA | 2.70× (27) | 3.67× (17) | 2.58× (28) | 2.69× (+0.1%) | 1.08 | 3,268 | 9.21% | $209M |
| GA | 2.69× (28) | 3.86× (13) | 2.87× (9) | 2.57× (+4.3%) | 1.11 | 3,902 | 15.21% | — |
| HI | 2.67× (29) | 3.02× (38) | 2.48× (34) | 1.91× (+28.5%) | 1.04 | 2,009 | 10.92% | $35M |
| VA | 2.63× (30) | 3.31× (27) | 2.32× (41) | 2.17× (+17.5%) | 0.87 | 2,942 | 12.32% | — |
| SC | 2.63× (31) | 3.60× (20) | 2.62× (26) | 2.47× (+5.8%) | 1.06 | 3,737 | 8.80% | $63M |
| MD | 2.60× (32) | 2.74× (43) | 2.45× (37) | 2.33× (+10.6%) | 1.23 | 2,279 | 13.08% | — |
| ME | 2.53× (33) | 2.71× (47) | 2.12× (51) | 1.94× (+23.2%) | 0.80 | 3,434 | 10.81% | $17M |
| OK | 2.53× (34) | 3.55× (21) | 2.73× (16) | 2.47× (+2.3%) | 1.20 | 3,829 | 11.04% | $75M |
| MT | 2.53× (35) | 2.94× (39) | 2.19× (48) | 2.03× (+19.6%) | 1.02 | 2,421 | 8.86% | $8M |
| RI | 2.51× (36) | 3.05× (35) | 2.40× (38) | 2.37× (+5.8%) | 0.96 | 3,435 | 12.42% | $17M |
| NE | 2.50× (37) | 3.17× (29) | 2.38× (39) | 2.27× (+9.3%) | 1.16 | 3,738 | 5.90% | — |
| WV | 2.49× (38) | 3.24× (28) | 2.31× (43) | 2.35× (+5.7%) | 1.18 | 3,268 | 6.69% | $25M |
| LA | 2.49× (39) | 3.03× (36) | 2.57× (30) | 2.56× (-3.1%) | 1.00 | 3,325 | 8.14% | $93M |
| MN | 2.48× (40) | 3.17× (30) | 2.26× (45) | 2.10× (+15.4%) | 0.87 | 4,077 | 12.58% | — |
| CA | 2.46× (41) | 3.12× (32) | 2.63× (24) | 2.42× (+1.6%) | 1.34 | 3,108 | 10.93% | $596M |
| FL | 2.42× (42) | 2.75× (42) | 2.53× (31) | 2.17× (+10.5%) | 1.06 | 3,745 | 12.97% | — |
| TN | 2.39× (43) | 3.49× (23) | 2.46× (36) | 2.09× (+12.3%) | 1.35 | 3,807 | 9.44% | $76M |
| AR | 2.33× (44) | 2.93× (40) | 2.29× (44) | 2.15× (+7.8%) | 0.96 | 3,430 | 8.81% | $24M |
| GU | 2.30× (45) | 2.62× (48) | 2.61× (27) | 2.59× (-12.7%) | 1.28 | 732 | 11.70% | $6M |
| MI | 2.25× (46) | 2.73× (44) | 2.63× (23) | 2.08× (+7.8%) | 1.05 | 3,460 | 9.89% | $150M |
| AK | 2.21× (47) | 2.61× (49) | 2.22× (47) | 1.98× (+10.5%) | 1.25 | 1,367 | 23.15% | — |
| NH | 2.21× (48) | 2.73× (45) | 2.08× (52) | 1.98× (+10.7%) | 1.22 | 2,328 | 8.85% | $8M |
| TX | 2.21× (49) | 2.90× (41) | 2.16× (49) | 1.83× (+17.3%) | 0.92 | 3,457 | 9.34% | $343M |
| UT | 2.17× (50) | 2.10× (53) | 2.37× (40) | 1.62× (+25.3%) | 1.20 | 4,101 | 5.54% | — |
| KS | 2.13× (51) | 2.71× (46) | 1.97× (53) | 2.24× (-4.9%) | 0.99 | 3,698 | 9.44% | $19M |
| ID | 2.02× (52) | 2.38× (51) | 2.23× (46) | 1.77× (+12.6%) | 1.19 | 3,839 | 3.85% | — |
| WY | 1.98× (53) | 2.11× (52) | 2.15× (50) | 1.36× (+31.1%) | 1.02 | 1,191 | 3.96% | — |
| **Median** | 2.70× | 3.31× | 2.61× | 2.42× (+10.0%) | 1.02 | | | |
<!-- STATE-TABLE:END -->
