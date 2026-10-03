# State POC replication runbook

**Purpose:** repeat the Pennsylvania / New York state-POC track for a new
state, end to end, and produce the state's pilot whitepaper.

**Scope:** state-conditioned synthetic generator (stage 1) → transfer
validation on real held-out cases (stage 2) → error anatomy (stage 3) →
prioritization simulation (stage 4) → dollar-impact ranking (stage 5) →
temporal stability (stage 6) → feature sanity audit (stage 7) → pristine
rerun (stage 8), plus the engine-cleanliness precursor (stage 8c), plus the
whitepaper (HTML + PDF), README index, and push.

**Conventions used below:** `<ST>` = the two-letter state code (e.g. TX),
`<st>` = its lowercase form (e.g. tx), `<SS>` = the QC `STATE` FIPS code
(e.g. `48`). All commands run from the repo root
`~/workspace/snap-qc-per-experiments` unless noted. Seed 7 everywhere unless
a stage says otherwise.

**Honest note on how this process actually works today:** the chain is
**copy-and-adapt, not parameterized.** The NY chain was built by copying
every PA script and module wholesale and adapting it (the NY1 script's own
docstring says it "mirrors pa1_pa_generator.fit_pa_targets"; `ny_state.py`
is a ~700-line line-for-line copy of `pa_state.py` with refit constants).
There is no `python3 run_state_poc.py --state TX`. The fragility this creates
is called out in each step and summarized in "Known fragilities" at the end.

---

## 1. Prerequisites

- **Microdata (read-only, never copied into the repo, never committed):**
  `../snap-qc-data/raw/qcfy{2020..2024}_csv/qc_pub_fy{FY}.csv` —
  `snap-qc-data/` sits beside the repo checkout. The stages take
  `--qc-dir ../snap-qc-data/raw` (or hardcode
  `QC_DIR = str(ROOT.parent / "snap-qc-data" / "raw")`, where `ROOT =
  Path(__file__).resolve().parent.parent`).
  Microdata is *held-out validation only* — nothing in this chain commits
  real case rows to the repo.
- **Python deps:** `pandas`, `numpy`, `scikit-learn`, plus stdlib. The
  transfer battery uses sklearn's `HistGradientBoostingClassifier` /
  `HistGradientBoostingRegressor` (GBM), `DummyClassifier` (majority
  baseline), `train_test_split`, `IsotonicRegression` / logistic (Platt)
  for calibration. **CPU only.** No GPU, no model weights anywhere (nothing
  in this chain writes a model to disk; NY4/NY7/NY8 retrain from the
  commands below plus the holdout JSON).
- **National base:** `experiments/dist.json` (the adopted-calibration
  national dist). The state generator loads it, applies `dollar_mech`'s
  adopted calibration, then the state's offset ratios — all in memory.
- **PDF toolchain:** `~/workspace/tooling/chrome-linux64/chrome`
  (stock Chrome for Testing). Verified: `--headless --no-sandbox
  --disable-gpu --print-to-pdf=... --print-to-pdf-no-header` on the
  whitepaper HTML produces a valid `%PDF-1.4` (~90 KB). Byte-exactness
  across Chrome versions is *not* guaranteed — content equivalence is what
  matters.
- **Push toolchain:** `~/workspace/tooling/smart_push.py`
  (`ctrimm/snap-qc-per-experiments`, branch `main`).

---

## 2. Step 0 — verify the FIPS code and count cases

Before anything else, confirm `<SS>` exists in the microdata and get the
per-FY case counts (the whitepaper's "The problem" section needs the total;
NY had 3,257 = 399/221/896/856/885; PA had 3,268):

```bash
python3 - <<'EOF'
import csv, glob
from collections import Counter
c = Counter()
for f in sorted(glob.glob('../snap-qc-data/raw/qcfy*_csv/qc_pub_fy*.csv')):
    with open(f) as fh:
        r = csv.DictReader(fh)
        for row in r:
            c[(row['STATE'], f.split('qcfy')[1][:4])] += 1
tot = sum(v for (s, _), v in c.items() if s == '<SS>')
print('total rows:', sum(c.values()))
print('<ST> (<SS>) total:', tot)
for fy in ('2020','2021','2022','2023','2024'):
    print(f'  FY{fy}:', c.get(('<SS>', fy), 0))
EOF
```

Record the counts in the new chain's Step-1 chronicle (NY1 recorded them in
its Method section).

---

## 3. Stage 8c — engine cleanliness (precursor)

**Goal:** prove the state's benefit engine matches statute, so the POC story
can attribute errors to the human process layer. The PA number was
99.7–100% exact match; NY was 94.3–98.3% per FY (97.6–98.3% excluding a
NY-specific recording artifact).

**How to build it:** copy `experiments/ny8c_ny_engine_cleanliness.py` to
`experiments/<st>8c_<st>_engine_cleanliness.py`. Change the state filter
(`df[df["STATE"] == 36]` → `<SS>` as an **integer** — the script loads with
pandas, which infers `STATE` as int; the csv.DictReader scripts in stages
1–7 compare the string `"<SS>"`. See Known fragilities), the output-side
holdout table, and the anomaly test for any state-specific pattern
(NY tested exp8b's uncapped-shelter anomaly; keep whatever anomaly the
state's anatomy suggests). `DATA` is hardcoded to
`<ROOT>.parent / "snap-qc-data" / "raw"` (`snap-qc-data/` beside the repo
checkout).

**Run (no arguments):**

```bash
python3 experiments/<st>8c_<st>_engine_cleanliness.py
```

**Outputs:** stdout report (parameter table per FY: 30% benefit-reduction
rate, ceiling-rounding exactness, 20% earned-income disregard, minimum
benefit, standard deduction, maximum allotments, shelter-cap behavior,
homeless deduction; uncapped-shelter test; output-side holdout exact-match
share per FY vs the national fleet) + chronicle
`experiments/<st>8c_<st>_engine_cleanliness.md`.

**Decision gate:** no state-specific parameter deviation that moves
benefits by more than $1 for a non-trivial share of cases (exp8b's
materiality bar), and no uncapped-shelter cases. The holdout exact-match %
vs fleet goes in the whitepaper's "The problem" section. **Watch for
state-specific recording artifacts** (NY found RAWNET==RAWGROSS rows in
FY2020–21 that broke the OLS slope and holdout on those rows — document
any such quirk; the engine is clean if benefits match the component-
recomputed net).

---

## 4. Stage 1 — state-conditioned generator

**Goal:** a `<ST>`-conditioned synthetic generator that reproduces the
state's finding mix, element mix, cause mix, case-error rate, and
directional profile, while leaving national output byte-identical.

### 4a. Build the fit harness

Copy `experiments/ny1_ny_generator.py` to
`experiments/<st>1_<st>_generator.py`. Change:

- `NY_STATE = "36"` → `"<SS>"` (string — the harness uses
  `csv.DictReader`, where STATE is a string; this must match the loader).
- every `NY_` constant prefix, `ny_state` import, and docstring reference
  to the `<ST>` form.

The harness has two subcommands:

```bash
python3 experiments/<st>1_<st>_generator.py fit        # recompute targets; prints baked constants
python3 experiments/<st>1_<st>_generator.py validate --qc ../snap-qc-data/raw --n 20000 --seed 7
```

The fit computes (FYWGT-weighted, pooled FY2020–2024, `<SS>` vs national):
finding mix, case-error rate, dollar rate, P(err|earner/no-earner),
P(over|err), near-full|over share, dollar p10/p25/p50/p90/mean, share ≤$56,
med-over/med-under, cause-97 blank rate, per-bucket element ratios, 97-share
ratios, direction-balance ratios, 97-resolution P(over|97) ratios, cause
ratios (fit on **non-97 variances only** — PA1 learned this the hard way
when pooled cause ratios blew up on the blanking interaction), and the
empirical cause mix *on* nature-97s per bucket.

**Sparsity guards (copy verbatim):** bucket cells with state unweighted
n < 25, 97-share/97-coin cells with 97-n < 5, direction cells with non-97
n < 25 keep the national value (ratio 1.0).

### 4b. Build the state module

Copy `src/synth/ny_state.py` to `src/synth/<st>_state.py`. Transcribe the
`fit` output into it, renaming every `NY_`-prefixed constant and function
to `<ST>_`, the state code to `"<SS>"`, the case tag to `"<ST>"`. The pieces:

1. `<ST>_OFFSETS` — empirical targets + national reference (documentation
   and sanity anchor).
2. `<ST>_COIN_RATIO` (earner / no_earner) + `<ST>_COIN_CAL` — the global
   coin calibration scalar, fit by line search over
   `{0.90, 0.93, 0.96, 1.0}` against the marginal case-error rate
   (PA chose 1.08 against a materialization ceiling; NY chose 0.96 —
   the direction is state-specific).
3. `<ST>_BUCKET_RATIO`, `<ST>_97_RATIO`, `<ST>_97_SHARE_RATIO`,
   `<ST>_DIR_RATIO`, `<ST>_CAUSE_RATIO` — per-bucket ratios. After the
   pure-empirical pass, do NY1's it2 **one-step realized-output calibration**
   (× real/synth share from a 20k-case pilot) if element/cause L1 needs it —
   document pure vs baked values in the code comments, as NY1 did.
4. `<ST>_97_CAUSE` — empirical cause mix on nature-97s per bucket.
5. `<ST>_S_OVER`, `<ST>_S_UNDER` — dollar-size relative scales (state
   median error / national median error per direction).
6. `<ST>_CAUSE97_BLANK`, `<ST>_P_UNIT` (None = national default).
7. The machinery below the constants is **identical across states** —
   copy verbatim, renaming only the constant references:
   `apply_<st>_offsets(dist)` (deep-copies the adopted dist; applies the
   five offset blocks; never mutates the input), the wrappers
   (`_draw_nature` resamples 97-causes from the state's 97-cause mix;
   `_recorded_cause` applies the state's 97-cause blank rate, consuming
   the rng draw to keep the stream aligned; `_wrap_corruptor` scales
   agency-side amount deltas by s_over/s_under per realized direction —
   installed during `generate_<st>` only, torn down in `finally`),
   `generate_<st>(n, seed, dist, out, ...)` (pipeline: load national dist
   → `dollar_mech.adopted_dist` → `apply_<st>_offsets` → generate with
   wrappers installed; tags cases `"state": "<ST>"`), and `main()`.

Shell generation (the command every downstream stage uses):

```bash
python3 -m src.synth.<st>_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out /tmp/<st>2out/<st>_synth.jsonl
```

National synth for the transfer battery:

```bash
cd src && python3 -m synth.generate --n 20000 --seed 7 \
    --dist ../experiments/dist.json --max-attempts 12 \
    --out /tmp/<st>2out/nat_synth.jsonl
```

### 4c. Decision gate (Stage 1 verdict)

Run the validation. NY1's gates: **finding L1 ≤ 0.06** (it1 was 0.0422,
final 0.0202), element L1 ≈ 0.044, cause L1 ≈ 0.074, case-error rate exact
(0.3651 vs 0.3655), and **national output byte-identical with/without the
module imported** (5k-case national run, md5-identical — replicate the
exact CLI path: the NY1 chronicle warns `errors.inject` defaults
`persistent_buckets=False`, so a hand-rolled check must pass the CLI flags
explicitly). Document structural residuals honestly (NY1's: dollar p50
18 vs 29 — a 97-vs-non97 shape fact the relative-offset architecture cannot
express — and +0.027 p(over|err)).

Write the chronicle `experiments/<st>1_<st>_generator.md` (hypothesis →
method → results → verdict → next steps) and the NY2 API block at the end
(python + shell copy-paste, fit/validate reproduction commands).

---

## 5. Stage 2 — transfer (the first decision point)

**Goal:** does state-conditioned synthetic signal predict real `<ST>` errors
above baseline, and does state-conditioning beat national-trained? The three
decision questions (NY2's framing):

1. Does `<ST>`-specific synthetic signal predict real `<ST>` errors above
   the majority baseline?
2. Does `<ST>`-conditioning beat national-trained on `<ST>` cases?
3. With or without `class_weight="balanced"` for GBM on the state mix?
   (NY2: no-classweight won all 12 comparisons — the balanced recipe was
   tuned on the national mix.)

**How to build it:** copy `experiments/ny2_ny_transfer.py` to
`experiments/<st>2_<st>_transfer.py`. Change state filters, module
references, and output paths (`/tmp/<st>2out/`).

**Holdout (your choice, documented):** NY2 used a stratified 75/25 split of
the 3,257 pooled rows (seed 20260929), stratified on a key where correct
cases form one stratum and error cases are stratified on finding × element
bucket, ultra-rare buckets merged into a "rare" stratum. Save to
`experiments/<st>2_holdout_idx.json`; row key = [fy, 0-based index among
state rows in that FY's CSV]; train = complement. **The same holdout file
serves stages 2, 4, 5, 7, and 8** — do not rebuild it per stage.

**Generation (exact):**

```bash
python3 -m src.synth.<st>_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out /tmp/<st>2out/<st>_synth.jsonl
cd src && python3 -m synth.generate --n 20000 --seed 7 \
    --dist ../experiments/dist.json --max-attempts 12 \
    --out /tmp/<st>2out/nat_synth.jsonl
# seed-robustness extras: repeat both with --seed 8 and --seed 9
# into <st>_synth_s8/s9.jsonl and nat_synth_s8/s9.jsonl
```

**Training/eval (exact):**

```bash
python3 experiments/<st>2_<st>_transfer.py \
    --ny-synth /tmp/<st>2out/<st>_synth.jsonl \
    --nat-synth /tmp/<st>2out/nat_synth.jsonl \
    --qc-dir ../snap-qc-data/raw \
    --holdout-json experiments/<st>2_holdout_idx.json \
    --<st>-synth-s8 /tmp/<st>2out/<st>_synth_s8.jsonl \
    --<st>-synth-s9 /tmp/<st>2out/<st>_synth_s9.jsonl \
    --nat-synth-s8 /tmp/<st>2out/nat_synth_s8.jsonl \
    --nat-synth-s9 /tmp/<st>2out/nat_synth_s9.jsonl
```

(Seed-robustness flags are optional but recommended; NY2's script accepts
them via the `--<st>-synth-s8/-s9`, `--nat-synth-s8/-s9` pattern.)
Features: **v1** (9 raw agency-view features — NY7 later drops one; see
Stage 7). Classifier: sklearn `HistGradientBoostingClassifier(random_state=0)`,
defaults, with and without `class_weight="balanced"`. Arms: (a/b) state
synth balanced/no-cw, (c/d) national synth balanced/no-cw, (e) REAL→REAL
ceiling, (f) majority baseline. Element task on test error cases (acc +
macroF1); finding task on all test cases (acc, macroF1, **binary AUC**).

**Fairness caveat (state it in the chronicle, NY2's wording):** the Stage-1
offsets were fit on pooled FY2020–2024 state microdata *including the
holdout rows*, so the state-synth arms are not pristine vs the test set;
the offset fit sees only pooled *marginals*, not test labels — the
advantage is small but not zero. Stage 8 quantifies it.

**Verdict scale and what MIXED means downstream — the NY2 worked example:**
NY2 came back **MIXED**: element leg no-pass (state synth 0.435 beats
majority 0.274, but national-trained 0.468 wins — NY's signature sits in
the rare medical/sua tail where the generator has a mechanics gap), finding
leg pass (NY wins binary AUC 6/6 across seeds, 0.657 vs 0.611). The MIXED
verdict *redirected the chain*: Stage 4's P(error) work used the state
arm's finding signal with threshold calibration (never hard classification);
the whitepaper stated the qualification plainly ("the transferable signal
is real, but it lives in the finding and dollar tasks, not in fine-grained
element prediction") and **dropped element claims**; Stage 8 confirmed the
negative was not a contamination artifact. A MIXED verdict does not stop
the chain — it re-scopes it.

**Deliverables:** script + chronicle + `experiments/<st>2_holdout_idx.json`.
No model weights written anywhere.

---

## 6. Stage 3 — error anatomy

**Goal:** the state's process-failure fingerprint vs national (feeds the
whitepaper's "The problem" section and the copilot attention order).

**How to build it:** copy `experiments/ny3_ny_anatomy.py` to
`experiments/<st>3_<st>_anatomy.py`. Change the state filter
(`row["STATE"] == "<SS>"` — string, csv.DictReader path).

**Run:**

```bash
python3 experiments/<st>3_<st>_anatomy.py --qc ../snap-qc-data/raw --out /tmp/<st>3out/anatomy.json
```

**Outputs:** finding/direction mixes; dollar-error quantiles (AMTERR);
element / nature / cause mixes as **NY-vs-national ratios** (FYWGT-weighted,
primary variance slot 1); top element×nature patterns in plain language;
FY trend table. NY3's headline numbers: timing (nature 97) 62% at 1.56x
national; medical 1.79x, SUA 1.51x, hhcomp 1.32x above; shelter 0.83x,
earned 0.90x below; computation errors 0.20x corroborating the clean
engine. Also record coding-practice notes (NY3: cause-99 distortion absent
— NY codes specific agency causes honestly — and ~4% non-codebook nature
codes, a state-specific quirk).

**Gate:** descriptive — verdict **Held** if the story is process-layer
(timing/verification) rather than computation-layer; the ratios table is
the calibration spec for future generator work and the whitepaper's anatomy
paragraph.

---

## 7. Stage 4 — prioritization simulation

**Goal:** a CIO-facing triage metric — errors found per reviewer-hour from
a ranked queue.

**How to build it:** copy `experiments/ny4_prioritization.py` to
`experiments/<st>4_prioritization.py`. **Feature set: use Stage 7's clean
feature set** (NY7 found `issued_benefit`/RAWBEN is a post-decision leakage
feature; NY4 trained on the clean 8-feature set from the start:
`hh_size, earned, unearned, shelter, sua, medical_exp, depcare,
senior_disabled`). If Stage 7 has not been run yet for the new state, run
it first or carry NY's clean-8 set with a documented assumption.

**Run (exact, from repo root):**

```bash
python3 -m src.synth.<st>_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out /tmp/<st>45out/<st>_synth.jsonl
python3 experiments/<st>4_prioritization.py \
    --ny-synth /tmp/<st>45out/<st>_synth.jsonl \
    --qc-dir ../snap-qc-data/raw \
    --holdout-json experiments/<st>2_holdout_idx.json
```

**Method (copy):** retrain Stage 2's winning arm exactly
(`HistGradientBoostingClassifier(random_state=0)`, no class_weight, 3-class
correct/over/under, P(error) = 1 − P(correct)); recalibrate the error-eager
scores on the real-state **train split** (the holdout complement — never the
holdout), choosing isotonic vs Platt by 5-fold stratified CV Brier score;
score the holdout once, rank by calibrated P(error).

**Report:** precision@k, lift vs random, and errors-per-100-reviews at
10/20/30/40/50% review budgets; the cumulative-gains shape (PA4/NY4 both
found flat-topped curves — the value is deprioritizing the safe half, not
targeting the riskiest few); what the ranker catches (direction mix,
AMTERR median vs holdout-wide — NY4's caught median $26 vs $30 showed no
small-dollar skew, unlike PA4).

**Gate:** **CONDITIONAL PASS** if the calibrated AUC clears Stage 8's
pristine reference and lift > 1 at every budget; frame the deliverable as
*triage* (NY: riskiest half catches 66.2% of errors with half the reviews),
never as a short high-confidence hit list. Caveats to state: retrospective
ranking on QC-labeled cases; the holdout-contamination caveat (quantified
small by Stage 8).

---

## 8. Stage 5 — dollar-impact ranking

**Goal:** the whitepaper's headline economics — error dollars recovered per
review hour vs random order.

**How to build it:** copy `experiments/ny5_dollar_ranking.py` to
`experiments/<st>5_dollar_ranking.py`.

**Run (exact):**

```bash
python3 -m src.synth.<st>_state --n 20000 --seed 7 \
    --dist experiments/dist.json --out /tmp/<st>45out/<st>_synth.jsonl
python3 experiments/<st>5_dollar_ranking.py \
    --ny-synth /tmp/<st>45out/<st>_synth.jsonl \
    --qc-dir ../snap-qc-data/raw \
    --holdout-json experiments/<st>2_holdout_idx.json
```

**Method (copy):** shared holdout (never touched during training; Stage 2's
fairness caveat carries over). Models: Stage 2's recipe on state synth,
n=20,000, seed 7, clean features (NY7), GBM without class_weight; **AMTERR
is the evaluation target only, never an input feature.** Ranking rules,
evaluated at top-10/20/30%:

- (a) **P(error)-only** (calibrated GBM);
- (b) **two-part:** calibrated P(error) × E[AMTERR|features] (dollar
  regressor = `HistGradientBoostingRegressor` on synth *error* cases,
  log1p(AMTERR) target, expm1 back-transform, clipped at 0);
- (c) **direct:** one `HistGradientBoostingRegressor` on *all* synth cases,
  log1p(AMTERR) (0 for correct cases);
- (b-r)/(c-r) **headroom:** same structures trained on the real-state train
  split via 5-fold ensembling — the transfer ceiling, not a product.

Metric: actual AMTERR recovered in top-k vs random-order expectation;
dollars-per-hour = recovered / (k × hours-per-case), **review-cost
assumption 30 min/case** (documented assumption, not measured; show
sensitivity at 15 and 60 — the lift ratio is invariant to it).

**Winner selection is empirical and state-specific — the key NY-vs-PA
divergence to watch for:** PA5's winner was (b) two-part (1.40x/1.58x/1.28x
lifts); NY5's winner was (c) direct (1.24x/1.52x/1.89x) because NY's
P(error) factor drags the product toward high-frequency small-dollar timing
errors while the direct model reaches the income-error tail. **Test PA5's
surprise on every state:** P(error)-alone was *worse than random* at
top-10% in both states (PA 0.43x, NY 0.74x) — probability of error and size
of error are nearly orthogonal in both mixes. Report over/under split at
top-20% (NY: $4,751/$2,207, 68/32; PA: $4,239/$1,835, 70/30) and the
savings-only $/hr (NY $58/hr vs $56/hr random; PA $52/hr vs $47/hr).

**Gate:** **CONDITIONAL PASS** if the winner beats random at top-20% with
lift ≥ ~1.5x. Honesty notes to carry: log-target regressors underestimate
the mean (Jensen, no smearing correction — ranking is unaffected, but never
quote raw expected-dollar outputs as point forecasts); synth captures only
part of the real-trained headroom (NY 1.52x vs 2.72x; PA 1.58x vs 3.15x) —
the generator's feature→dollar conditional is the binding constraint.

---

## 9. Stage 6 — temporal stability

**Goal:** does the transfer signal hold year to year, or does the POC need
annual refitting?

**How to build it:** copy `experiments/ny6_temporal.py` to
`experiments/<st>6_temporal.py`. The script imports Stage 1's fit function
as a module (`import <st>1_<st>_generator` — requires the
`sys.path.insert(0, str(ROOT / "experiments"))` lines the NY script has;
run from repo root), calls it with `fys=[2020,2021,2022]` (the `fit` CLI
has no `--fys` flag — the year filter is applied by calling the function
directly), converts the output to module-attribute overrides via
monkey-patching (PA6's pattern; no src file modified), and replicates
Stage 1's it2 recipe (pure-empirical ratios → pilot → one-step realized-
output calibration → coin-cal line search).

**Run (no arguments; QC_DIR hardcoded; ~311s on CPU):**

```bash
python3 experiments/<st>6_temporal.py
# results -> /tmp/<st>6out/<st>6_results.json, synth files -> /tmp/<st>6out/
```

**Arms:** T_refit (FY2020–22-fit synth) tested on FY2023–24 real state
(clean temporal test) AND on FY2020–22 (train-period reference); T_pooled
(Stage-1 as-is) on both; T_excl21 (FY2021 excluded — the partial-year
sensitivity arm). Same GBM recipe, element + finding.

**Gate:** **PASS** if the element gate metric does not decay across the
period boundary (NY6: +8.9pp acc — a mix-alignment rise, not decay) and the
refit arm beats or matches pooled on the clean temporal test. Process
notes for production: **drop partial-year QC files from refits** (NY's
FY2021: 221 rows moved the fitted error rate 1.9pp and the medical bucket
ratio 20%); name the buckets to watch (NY: medical — the only real F1
decay — and hhcomp, whose adjustment the sparsity guard silently drops in
pre-2023 refits).

---

## 10. Stage 7 — feature sanity audit (the "defend this to a CIO" check)

**Goal:** confirm the model learns legitimate certification-time process
signals, not post-decision fields or reviewer-coded label smuggling.

**How to build it:** copy `experiments/ny7_feature_audit.py` to
`experiments/<st>7_feature_audit.py`.

**Run:**

```bash
python3 experiments/<st>7_feature_audit.py \
    --ny-synth /tmp/<st>2out/<st>_synth.jsonl \
    --qc-dir ../snap-qc-data/raw \
    --holdout-json experiments/<st>2_holdout_idx.json
```

**Method (copy):** retrain Stage 2's best arm exactly (must reproduce to
~4 decimals — NY7 did: acc 0.4348, macroF1 0.1681 vs 0.435/0.168); two
importance measures on the same model — GBM gain shares and permutation
importance (20 repeats on the holdout, drop in acc and macroF1); then the
leakage audit: trace every v1 feature to its QC field and classify
known-at-certification vs post-decision/reviewer-coded (anything touching
AMTERR, RAWBEN, FSBEN, STATUS, or the ELEMENT/NATURE/CAUSE label arrays is
flagged); retrain with flagged features removed and report the delta.

**Gate:** **PASS** if (a) top features match Stage 3's anatomy (NY7: earned
/ shelter / unearned on top, medical elevated exactly where NY is most
distinctive at 1.79x national — "the cross-check passes with a state
accent"), and (b) no *material* leakage — NY7 found exactly one
post-decision feature (issued_benefit/RAWBEN); removing it moved acc +0.017
/ macroF1 −0.021 (immaterial), so the POC numbers stood with the corrected
figures. **Adopt the clean feature set for all downstream training**
(NY: 8 features, drop `issued_benefit`).

---

## 11. Stage 8 — pristine rerun (close the fairness caveat)

**Goal:** quantify Stage 2's contamination premium — does the verdict
survive when the holdout rows are excluded from *every* tuning step?

**How to build it:** copy `experiments/ny8_ny_pristine_rerun.py` to
`experiments/<st>8_<st>_pristine_rerun.py`. The script is a verbatim port
of Stage 1's `fit_<st>_targets` with one change: rows whose (fy, state-
relative row index) key appears in `experiments/<st>2_holdout_idx.json`
are skipped before any aggregate is touched. Refit constants are installed
by monkey-patching the `src.synth.<st>_state` module attributes (PA6's
pattern; no src file modified). It also imports Stage 1's module and Stage
2's module (`import <st>1_<st>_generator`, `import <st>2_<st>_transfer` —
the sys.path inserts are required). `HOLDOUT_JSON`, `QC_DIR`, and `OUT`
(`/tmp/<st>8out`) are hardcoded constants at the top; verify they point at
the new state's files before running.

**Run:**

```bash
python3 experiments/<st>8_<st>_pristine_rerun.py [--balanced]
```

(`--balanced` only if Stage 2's battery says balanced wins for the state;
NY8 ran without it.)

**Method (copy):** pristine refit → regenerate state synth following Stage
1's it2 recipe exactly (pure-empirical → pilot → one-step realized-output
calibrations on the minus-holdout basis → coin-cal line search → final
20k, seed 7) → Stage 2's battery: pristine-state synth vs national synth on
the same holdout. Verify the regenerated national arm is byte-identical to
Stage 2's file as a sanity check (NY8's was).

**Gate:** **PASS** if Stage 2's verdict stands: NY8's contamination premium
was ~+0.02 on finding AUC and ~0 on element — the finding edge survived
(0.626 vs 0.611 pristine) and the element non-pass was confirmed not to be
a contamination artifact. The pristine numbers *replace* Stage 2's numbers
as the reference in Stage 4's plan and the whitepaper (NY4's caveat section
does exactly this).

---

## 12. The whitepaper

**Template:** copy `whitepaper/ny_pilot_whitepaper.html` to
`whitepaper/<st>_pilot_whitepaper.html`. Same six sections, same CSS/callout
table/footer. Fill from the stage outputs:

| Section | Numbers to insert | Source stage |
|---|---|---|
| 1. Executive summary | transfer AUCs (state vs national, all seeds); pristine AUCs; top-20% winner: $ recovered vs random, $/hr vs random; riskiest-half catch % | 2, 8, 5, 4 |
| 2. The problem | case count FY2020–2024 (Step 0); engine-cleanliness % per FY + fleet (8c); the state's distinctive anatomy ratios — the 2–3 ratios that define its fingerprint (NY: timing 1.56x, medical 1.79x, SUA 1.51x) | 0, 8c, 3 |
| 3. What was built and validated | generator L1s (finding/element/cause); transfer numbers; **the honest qualification** (NY: element leg does not beat national — state it, cite the rare-tail mechanics gap); the dollar-aware ranking surprise (P(error)-alone < random at top-10%) | 1, 2, 8, 5 |
| Callout table | top-20% review budget: error dollars recovered (random vs winner), value per review hour, share of all error dollars captured; below the table: over-issuance $ (program savings) / under-issuance $ (households owed) split, savings-only $/hr vs random | 5 |
| 4. The pilot | same 3-phase text, state name swapped; 8–12 weeks | — |
| 5. Limitations and honest caveats | headroom (winner lift vs headroom lift, e.g. NY 1.52x vs 2.72x); **NY-vs-PA style divergence**: the winning rule was (c) direct, not PA's (b) two-part — name the winner and the mechanism; procedural-errors-invisible note (FNS-published rate vs microdata-implied rate, e.g. NY 12.68%/14.09% published vs 8.54% microdata); element qualification if MIXED; stability note + bucket to watch | 5, 2, 3, 6 |
| 6. The ask | same text, state name swapped | — |
| Footer | update the chronicle count (NY said "60+") | — |

**State-name sweep:** replace "New York"/"NY" in title, h1, all six sections,
and the meta line. Keep "no modifications to the eligibility system, no
automated determinations (the model prioritizes review — it never decides a
case), no data leaves the state's control" verbatim.

**Render the PDF** (verified working on a temp copy 2026-09-29):

```bash
~/workspace/tooling/chrome-linux64/chrome --headless --no-sandbox --disable-gpu \
    --print-to-pdf=whitepaper/<st>_pilot_whitepaper.pdf \
    --print-to-pdf-no-header \
    whitepaper/<st>_pilot_whitepaper.html
```

---

## 13. README index

Follow the NY block (after the PA verdict, before/after as the file
evolves): a `## <ST> experiment index` section — one-line state intro
("STATE=<SS>, n=<total> FY2020–2024. Files named `<st>N_*`; mirrors the PA
chain."), the 9-row table (`8c` + `<ST>1`–`<ST>8`, experiment | gate |
verdict), then a `<ST> track complete` paragraph and a bolded
**`<ST> verdict (POC complete, <date>)`** paragraph with the two decision
points and the recommended next step. (NY's block is at the `## NY
experiment index` heading — copy its shape.)

---

## 14. Commit and push

```bash
cd ~/workspace/snap-qc-per-experiments
git add -A   # stages write only NEW files; confirm with git status
git commit -m "<ST> POC track: 8c + <ST>1-<ST>8, whitepaper HTML+PDF, README index"
~/workspace/tooling/smart_push.py ctrimm/snap-qc-per-experiments main \
    "<ST> POC track: 8c + <ST>1-<ST>8, whitepaper HTML+PDF, README index" \
    --dir ~/workspace/snap-qc-per-experiments
```

Then **verify**: compare the remote blob count against the local tree
(`smart_push.py` reports the remote count; cross-check with
`git ls-tree -r HEAD | wc -l`). NY's push verified 174/174. The working tree
must be clean.

---

## 15. Known fragilities (where this process is copy-and-adapt today)

1. **Every stage is a full-file copy of the NY scripts**, with manual
   renames (`NY_` → `<ST>_`, `ny_state` → `<st>_state`, `ny2_holdout_idx` →
   `<st>2_holdout_idx`, `/tmp/nyNout` → `/tmp/<st>Nout`). Nothing is
   parameterized by state; a rename miss fails loudly (ImportError) or —
   worse — silently (a stale `36` in a filter). **Grep the new files for
   `36`, `ny_`, `NY`, `ny2` before running.**
2. **`STATE` column type differs by loader:** the csv.DictReader stages
   (1, 3) compare the *string* `"<SS>"`; the pandas Stage-8c script compares
   the *integer* `<SS>` (pandas infers int). Copy the comparison that matches
   the script's loader.
3. **Hardcoded paths and sys.path surgery:** `QC_DIR`,
   `experiments/dist.json`, `HOLDOUT_JSON`, `OUT=/tmp/<st>Nout`, and the
   `sys.path.insert(0, ...ROOT/"experiments")` lines that let stages 6/8
   `import <st>1_<st>_generator` / `import <st>2_<st>_transfer` as modules.
   **Stages 6 and 8 must run from the repo root.**
4. **The fit harness prints baked constants; transcription into
   `src/synth/<st>_state.py` is manual.** NY1's module docstring records the
   provenance (`python3 experiments/<st>1_<st>_generator.py fit`); keep that
   chain of custody in the chronicle.
5. **Monkey-patching in stages 6/8** (module-attribute overrides of the
   state module) instead of a parameterized generator — works because every
   generator function reads those globals at call time; breaks if the
   module is refactored to read them at import time.
6. **Seed-robustness is optional:** Stage 2's `--<st>-synth-s8/-s9` flags;
   NY2 ran seeds 7/8/9, NY8 ran seed 7 only (documented as an optional
   follow-up).
7. **Feature set:** Stage 7 must run before Stages 4/5 are finalized for a
   new state — NY4/NY5 used NY7's clean 8-feature set from the start; do not
   inherit PA4/PA5's 9-feature recipe blindly.
8. **PDF byte-exactness** across Chrome versions is not guaranteed;
   content equivalence is the bar.
9. **Stage numbering note:** the precursor engine check is numbered `8c`
   (it gates the track's premise, like exp8c did for PA); the main chain is
   1–8 in execution order 8c → 1 → 2 → 3, then 4–8 (7 may precede 4/5 for
   the feature set).
