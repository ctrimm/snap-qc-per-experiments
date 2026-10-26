# Replicating the SNAP Error-Ranking Work for Your State

**October 26, 2026 (corrected; first version October 23) · Replication guide · Cory Trimm**


> **Corrected October 26, 2026.** The October 23 version overstated the tool's results. The models used the benefit the agency issued alongside income, deduction and household-size values that, in the federal QC file, are what the QC reviewer recorded, so they could partly see the error (experiment 106). Every model figure here comes from the leak-free rebuild (experiment 107); the packaged models no longer use the issued benefit. The same day they were rebuilt on the official error definition: they learn and are scored on errors over the federal tolerance, the ones the payment error rate counts (experiment 111). Both are the code's defaults (`SNAPQC_FEATURES=leakfree`, `SNAPQC_LABEL=official`).

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
python3 -c "import json; print(json.dumps(json.load(open('experiments/exp83_official_results.json'))['XX'], indent=1))"
# FY2028 cost-share scenarios, every step shown
python3 experiments/cost_share_replicate.py --state XX
```

How to read the first output:

| Field | Meaning |
|---|---|
| `top20.lift` | Error dollars found in the top 20% of the queue, as a multiple of random review. Counts errors over the federal tolerance. 50 of 53 jurisdictions fall between 2.0 and 3.4 (median 2.61) |
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
git diff --stat experiments/exp83_official_results.json     # empty = exact reproduction (leak-free inputs, official label: the defaults)
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

**About the packaged models:** each `deliverables/state_rankers/XX/model.joblib` was refit on all five years of that state's cases plus every other state's, for the best possible model. Since exp107 they are leak-free: they do not use the issued benefit. Their held-out performance is the evaluation fit in `exp83_official_results.json`. The `evaluation` block inside `model_card.json` is from the earlier state-only model; use `exp83_official_results.json`.

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

Ranking purely by dollars under-reviews elderly households (a review share below 0.8 of their share of error cases) in 50 of 52 measurable jurisdictions (median 0.44), and disabled households in 26 of 51 (median 0.79; exp111 models, errors over the tolerance). The fairness floor (exp72) guarantees each household type a share of reviews in line with its share of errors. With the floor on, 8 jurisdictions still leave elderly households below 0.8 (lowest 0.66), and 8 leave disabled households below it: over-tolerance errors are rarer, so the floor's shares rest on fewer cases. It is not free: the median lift falls from 2.61× to 2.45×, and the median state gives up about 7% of its lift. California gives up 1%, New York 10%, Pennsylvania 17%, Texas 27%, and six states more than 20% (Maine, Hawaii, Kansas, Texas, Utah, Alabama; at most 35%); nine give up nothing. Each state's figure is in the appendix. We still recommend it on by default; a state that turns it off should know who loses review.

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
| Level 1 | You have your state's `exp83_official_results.json` entry and the cost-share output, and know your break-even review rate |
| Level 2 | `exp83_context_models_full_eval.py` reproduces `exp83_official_results.json` with an empty `git diff` |
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
| Central: avoided a year | The FY2028 cost-share scenario (exp93 design, exp111 models, lift on over-tolerance dollars); "—" means no bracket change, or a rate already under 6% |

<!-- STATE-TABLE:START -->
| Jurisdiction | Top 20% lift (rank) | Top 10% lift (rank) | Later years (rank) | With floor (cost) | Forecast ÷ actual | QC cases | FY2025 rate | Central: avoided a year |
|---|---|---|---|---|---|---|---|---|
| AK | 3.37× (1) | 6.18× (1) | 2.88× (8) | 3.12× (+7.2%) | 1.03 | 1,367 | 23.15% | — |
| WA | 3.35× (2) | 4.57× (4) | 3.04× (4) | 3.17× (+5.4%) | 0.98 | 3,060 | 6.98% | $95M |
| MA | 3.27× (3) | 4.64× (3) | 3.19× (1) | 3.08× (+5.7%) | 0.83 | 3,483 | 12.49% | $129M |
| NY | 3.21× (4) | 4.53× (6) | 3.17× (2) | 2.89× (+10.2%) | 1.01 | 3,257 | 13.18% | $360M |
| CT | 3.15× (5) | 4.56× (5) | 2.95× (7) | 3.08× (+2.4%) | 0.97 | 3,818 | 9.08% | $45M |
| GU | 3.12× (6) | 5.48× (2) | 3.11× (3) | 3.38× (-8.4%) | 0.56 | 732 | 11.70% | $12M |
| OR | 3.00× (7) | 4.33× (7) | 3.02× (5) | 2.80× (+6.9%) | 1.08 | 3,037 | 14.14% | — |
| DC | 2.98× (8) | 4.08× (13) | 2.84× (9) | 2.83× (+5.0%) | 1.11 | 2,689 | 18.66% | — |
| MO | 2.92× (9) | 3.99× (14) | 2.75× (15) | 2.54× (+12.9%) | 0.91 | 2,933 | 8.67% | $73M |
| IN | 2.92× (10) | 4.23× (9) | 2.50× (28) | 2.65× (+9.3%) | 0.88 | 3,237 | 9.77% | $70M |
| NM | 2.84× (11) | 3.63× (20) | 2.75× (14) | 2.54× (+10.5%) | 1.17 | 3,845 | 16.81% | — |
| MS | 2.83× (12) | 3.91× (15) | 2.74× (16) | 2.76× (+2.3%) | 0.85 | 4,158 | 9.51% | $40M |
| AL | 2.83× (13) | 3.41× (26) | 2.55× (26) | 2.20× (+22.2%) | 1.02 | 4,163 | 9.52% | $85M |
| WV | 2.82× (14) | 4.13× (11) | 2.28× (41) | 2.98× (-5.8%) | 0.88 | 3,268 | 6.69% | $25M |
| CO | 2.81× (15) | 4.32× (8) | 2.79× (11) | 2.70× (+4.0%) | 0.90 | 3,595 | 10.09% | $127M |
| NC | 2.79× (16) | 3.55× (22) | 2.34× (36) | 2.52× (+9.3%) | 0.98 | 3,983 | 7.36% | $141M |
| VT | 2.75× (17) | 2.34× (49) | 2.63× (22) | 2.57× (+6.7%) | 1.32 | 2,720 | 5.38% | — |
| OH | 2.75× (18) | 3.44× (24) | 2.32× (38) | 2.56× (+6.8%) | 0.85 | 3,475 | 6.76% | $152M |
| GA | 2.74× (19) | 4.14× (10) | 2.83× (10) | 2.61× (+4.6%) | 0.99 | 3,902 | 15.21% | — |
| ME | 2.72× (20) | 2.62× (44) | 2.19× (44) | 1.77× (+34.8%) | 0.66 | 3,434 | 10.81% | $17M |
| SC | 2.65× (21) | 3.77× (17) | 2.66× (19) | 2.51× (+5.3%) | 0.97 | 3,737 | 8.80% | $63M |
| NE | 2.64× (22) | 3.55× (21) | 2.31× (39) | 2.49× (+5.8%) | 0.91 | 3,738 | 5.90% | — |
| IL | 2.63× (23) | 3.88× (16) | 2.78× (12) | 2.64× (-0.2%) | 0.93 | 3,246 | 14.67% | — |
| FL | 2.63× (24) | 3.23× (34) | 2.35× (35) | 2.17× (+17.6%) | 1.07 | 3,745 | 12.97% | — |
| PA | 2.62× (25) | 3.43× (25) | 2.67× (18) | 2.18× (+16.7%) | 1.13 | 3,268 | 9.21% | $209M |
| AZ | 2.61× (26) | 4.11× (12) | 3.00× (6) | 2.40× (+8.1%) | 1.38 | 3,352 | 10.80% | $196M |
| DE | 2.61× (27) | 3.23× (33) | 2.57× (25) | 2.39× (+8.3%) | 0.91 | 1,652 | 16.00% | — |
| HI | 2.61× (28) | 2.88× (40) | 2.44× (30) | 1.72× (+34.0%) | 0.96 | 2,009 | 10.92% | $35M |
| IA | 2.58× (29) | 3.64× (19) | 2.58× (24) | 2.33× (+9.6%) | 0.79 | 3,892 | 5.34% | — |
| NV | 2.55× (30) | 3.24× (31) | 2.68× (17) | 2.08× (+18.4%) | 1.04 | 4,047 | 6.22% | $51M |
| MD | 2.55× (31) | 2.90× (39) | 2.35× (34) | 2.39× (+6.2%) | 1.12 | 2,279 | 13.08% | — |
| WI | 2.54× (32) | 2.98× (37) | 2.18× (45) | 2.45× (+3.7%) | 0.99 | 3,979 | 5.72% | — |
| RI | 2.54× (33) | 3.25× (30) | 2.36× (33) | 2.46× (+3.0%) | 1.04 | 3,435 | 12.42% | $17M |
| VA | 2.53× (34) | 3.19× (35) | 2.30× (40) | 2.31× (+8.7%) | 1.05 | 2,942 | 12.32% | $86M |
| LA | 2.50× (35) | 3.36× (28) | 2.33× (37) | 2.26× (+9.8%) | 0.87 | 3,325 | 8.14% | $93M |
| CA | 2.48× (36) | 3.74× (18) | 2.61× (23) | 2.45× (+1.3%) | 1.25 | 3,108 | 10.93% | $596M |
| NJ | 2.46× (37) | 3.50× (23) | 2.66× (20) | 2.62× (-6.6%) | 1.08 | 2,327 | 6.86% | $92M |
| OK | 2.44× (38) | 3.18× (36) | 2.63× (21) | 2.43× (+0.2%) | 1.15 | 3,829 | 11.04% | $75M |
| ND | 2.40× (39) | 2.75× (42) | 2.51× (27) | 2.47× (-2.8%) | 1.06 | 1,691 | 9.89% | $5M |
| TX | 2.40× (40) | 2.69× (43) | 2.11× (47) | 1.75× (+27.2%) | 0.80 | 3,457 | 9.34% | — |
| MI | 2.39× (41) | 2.95× (38) | 2.76× (13) | 2.21× (+7.5%) | 1.09 | 3,460 | 9.89% | $150M |
| MN | 2.37× (42) | 2.49× (47) | 2.09× (48) | 1.91× (+19.4%) | 0.99 | 4,077 | 12.58% | — |
| KY | 2.36× (43) | 3.36× (29) | 2.23× (42) | 2.31× (+2.2%) | 0.81 | 4,073 | 4.70% | — |
| AR | 2.33× (44) | 2.60× (45) | 2.15× (46) | 2.69× (-15.3%) | 0.94 | 3,430 | 8.81% | $24M |
| SD | 2.25× (45) | 2.35× (48) | 1.75× (52) | 1.88× (+16.6%) | 0.84 | 2,365 | 2.47% | — |
| VI | 2.11× (46) | 3.37× (27) | 2.45× (29) | 2.44× (-15.4%) | 1.12 | 998 | 5.36% | — |
| MT | 2.05× (47) | 2.54× (46) | 1.83× (51) | 1.84× (+10.2%) | 1.07 | 2,421 | 8.86% | $8M |
| KS | 2.02× (48) | 1.62× (53) | 1.72× (53) | 1.36× (+32.8%) | 0.93 | 3,698 | 9.44% | — |
| TN | 2.02× (49) | 3.24× (32) | 2.22× (43) | 2.03× (-0.3%) | 1.43 | 3,807 | 9.44% | $76M |
| UT | 2.01× (50) | 1.85× (51) | 2.42× (31) | 1.51× (+24.8%) | 1.17 | 4,101 | 5.54% | — |
| NH | 1.67× (51) | 1.68× (52) | 1.99× (50) | 1.55× (+7.1%) | 1.46 | 2,328 | 8.85% | $8M |
| WY | 1.64× (52) | 2.82× (41) | 2.02× (49) | 1.38× (+15.8%) | 1.42 | 1,191 | 3.96% | — |
| ID | 1.49× (53) | 1.89× (50) | 2.41× (32) | 1.36× (+8.7%) | 1.28 | 3,839 | 3.85% | — |
| **Median** | 2.61× | 3.37× | 2.51× | 2.45× (+7.1%) | 0.99 | | | |
<!-- STATE-TABLE:END -->
