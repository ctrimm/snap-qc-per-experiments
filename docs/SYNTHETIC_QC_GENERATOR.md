# Guide: The snap-qc Synthetic QC-Case Generator

> Setup and usage guide — October 30, 2026 (a copy also lives in the lab's Obsidian vault)
> Code: `src/synth/` · Tests: `tests/`
> Verified Oct 30: the national and Pennsylvania commands below were run on the Studio (Python 3.12) and wrote valid cases. Unit tests added the same day (`tests/`, 36 passing)
> Not to be confused with: govsynth (`synthetic-gov-data-kit`), which makes eligibility scenarios with explanations for a different job
> Related: `NORTH_STAR.md`, `LEARNINGS.md`, `experiments/exp6_calibration_methodology.md`, `experiments/exp115_generator_audit.md`

---

## What it's for

**It makes synthetic SNAP quality-control (QC) review cases: a certified household, plus the error a QC reviewer would find in it.**

- **Each case has:**
  - the correct facts and the facts the agency acted on;
  - the correct benefit and the issued benefit;
  - the finding (1 = correct, 2 = overpaid, 3 = underpaid);
  - the dollar error;
  - each variance's element, nature and cause, coded like the real QC file.
- **Use it to:**
  - train or test a QC-review model (exp52/59: E4B trained only on these cases passed the gate on 1,200 fresh real cases);
  - test ranker transfer from synthetic to real data;
  - produce shareable data that looks statistically like QC data without any real households.
- **Don't use it for:**
  - eligibility determinations or benefit reasoning with explanations (use govsynth, `synthetic-gov-data-kit`);
  - official benefit amounts (its benefit math is an FY2024 approximation, not the official QC Minimodel).

**What makes it trustworthy: it's calibrated to the real QC public-use file.** Over exp1–45 the error mix was tuned until it matched real data: finding-mix L1 0.009 at exp6, and in exp115 an official-error share of 11.8% synthetic against 12.1% real.

## Setup

1. **Python 3.10+.** The generator uses only the standard library, so no install and no virtual environment are needed.
2. **The repo:** `~/Documents/GitHub/snap-qc-per-experiments`. Run every command from its root.
3. **Calibration files (already committed):**
   - `experiments/dist.json`: error mix, buckets, natures and causes;
   - `experiments/eff.json`: injection effectiveness;
   - `experiments/dist_reportable.json`: the variant for amount-recording states (exp55).

   The generator runs without the real QC data.
4. **Only to recalibrate or validate:**
   - **Data:** the real QC files in `~/Documents/GitHub/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv` (FY2020–2024 are there, outside the repo, gitignored).
   - **Python packages:** numpy for the calibration scripts, and scikit-learn for the discriminator.
   - **Rebuilding `dist.json`:** `python3 experiments/build_dist.py`. This overwrites the committed file, so do it on a branch.

## Generate cases

**National mix:**
```
PYTHONPATH=src python3 -m synth.generate --n 20000 --seed 7 --dist experiments/dist.json --out data/synth.jsonl
```

**State-conditioned:**
```
python3 -m src.synth.pa_state --n 5000 --seed 7 --dist experiments/dist.json --out data/pa_synth.jsonl
```
- **Other states:** `ny_state`, `tx_state`, `ut_state`, `sd_state` and `id_state` work the same way.
- **What a state variant adds:** that state's offsets and coin calibration (PA1: `PA_COIN_CAL = 1.08`). It also adds a `state` field.

**Generator flags (`src/synth/generate.py`)** — the defaults are the adopted settings:

| Flag | Default | What it changes |
|---|---|---|
| `--n`, `--seed` | required, 7 is the house seed | Case count; same seed = same cases |
| `--dist` | required | Calibration file (`dist.json` or `dist_reportable.json`) |
| `--persistent-buckets` / `--no-persistent-buckets` | on (exp7) | Draw an error bucket once and drop it if the benefit doesn't move, vs the old retry loop |
| `--dollar-mechanisms` / `--no-dollar-mechanisms` | on (exp31) | Realistic dollar-error sizes: small nature-97 errors, whole-unit ineligibility |
| `--legacy-materialization` | off | The old single correction instead of the per-(bucket, stratum) matrix (exp24) |
| `--calibration` | none | A capture JSON to pair with `dist_reportable.json` (exp55) |
| `--max-attempts` | 12 | Retries per case on the retry-loop path |

## What a case looks like

One JSON object per line:
- **`facts` / `issued_facts`:**
  - household size and children;
  - earned and unearned income;
  - shelter, utility allowance, medical, dependent care;
  - elderly or disabled status;
  - review month.
- **`correct_benefit`, `issued_benefit`, `dollar_error`.**
- **`finding`:** 1 / 2 / 3.
- **`reportable`:** whether the error is over the $56 tolerance.
- **`variances[]`:** `element`, `element_bucket`, `nature`, `cause`, `timing`.

**Task labels (T1–T5) for model training aren't part of the generator.** `experiments/exp52_rlvr_dataset.py` generates its own cases and labels them in the QC-eval format:
```
python3 experiments/exp52_rlvr_dataset.py --n 30000 --train 4000 --valid 200 --balance finding --label-match --fy-coding
```
- **Output:** `../snap-qc-data/derived/exp52_rlvr` by default.
- **`--balance`:** `finding`, `errors`, `correct` or `natural`.
- **`--label-match`:** makes the labels follow the eval's rules (exp54).

## How it works (in order)

1. **Sample a household** (`src/synth/household.py`):
   - income and composition by stratum;
   - a size mix fitted in exp44;
   - an eligibility screen (exp6).
2. **Compute the correct benefit** (`benefit.py`, using `params.py`).
3. **Inject an error** (`errors.py`): pick a bucket (earned, unearned, shelter, utility, medical, dependent care, household composition, arithmetic) using `dist.json` and the materialization matrix. Then corrupt the matching fact and record its nature and cause.
4. **Shape the dollar error** (`dollar_mech.py`).
5. **Recompute the issued benefit and write the case.**

## Checking it

**Unit tests (`tests/`, 36 tests, about a second, no real data needed):**
```
uv run --no-project --with pytest pytest tests      # or: pip install pytest && pytest tests
```
- **`tests/test_benefit.py`:** the benefit math against hand-worked cases:
  - deductions;
  - the shelter cap;
  - elderly/disabled medical deduction and uncapped shelter;
  - the $23 minimum;
  - table extension past 8 people.
- **`tests/test_generator.py`:**
  - **Sampler:** deterministic per seed, with at least 99% of households passing the eligibility screen.
  - **Case invariants, in all four modes** (default, `--no-dollar-mechanisms`, retry loop, legacy materialization):
    - schema;
    - `dollar_error = |issued − correct|`;
    - finding 2/3 matches the direction;
    - `reportable` = over $56;
    - correct cases are clean;
    - error cases record variances;
    - the correct benefit can be recomputed from `facts` (except whole-unit ineligibility, which is checked separately).
  - **Determinism.**
  - **State hygiene:** the dollar mechanisms patch module state, and the tests check it is fully undone.
  - **A loose calibration guard:** finding mix, reportable share, and the share of errors at or under $56.
  - **The CLI and the PA variant.**
- **Add a test with any change to `src/synth/`.** If a change is meant to move the calibration, update the guard's bands in the same commit and cite the experiment.

**Calibration checks (need the real QC file):**
- **Calibration readout:** `experiments/exp31_adopt_dollar.py` (`rebaseline` stage). It reports finding L1, element ratios and the share of errors at or under $56.
- **Synthetic vs real:** `experiments/exp35_discriminator_diagnostic.py`. It trains a classifier to tell synthetic from real. Last result: AUC 0.981, with shelter costs the biggest giveaway.
- **Official error label:** `experiments/exp115_generator_audit.py`.
- **Before changing anything in `src/synth/`:**
  - save a baseline from all three on seed 7, n = 20,000;
  - rerun them after the change;
  - write the before and after in a new `experiments/expNN_*.md` with a README index row.

## Rules of the road

- **No leaky features in anything trained on real data.** This doesn't affect the generator itself, but models built next to it must follow the repo's `CLAUDE.md`: leak-free features, and the official error label by default.
- **Don't calibrate automatically without a locked holdout.** exp81/81b overfit their own seeds and lost to the hand-tuned PA1.
- **Cornell quiz data never goes into training sets.**
