# Experiment 34 — temporal drift FY2020–2024
**Date:** 2026-09-29 · **Code:** `experiments/exp34_temporal_drift.py`

## Hypothesis
The finding/element/dollar mixes drifted materially across FY2020–2024
(COVID-era waivers through unwinding), enough to warrant a time-conditioned
generator. Ties to the north star's **calibration gate**: if the real target
moves by year, a single FY2024-calibrated `dist.json` misrepresents other
years, and the synthetic pretraining data should carry a year conditioning.

## Method
1. Loaded the five QC public-use files (held-out; read-only, nothing from the
   microdata is written into the repo):
   `../snap-qc-data/raw/qcfyYYYY_csv/qc_pub_fyYYYY.csv`.
   FY2021 covers Jul–Sep only (n = 9,832 rows vs 27k–45k for other years).
   Unweighted microdata, the same convention as exp16.
2. Per FY, in one pandas pass: finding mix from STATUS (1 = correct,
   2 = over, 3 = under); variance-level element-bucket mix from
   ELEMENT1–9 via `src/synth/codebook.py` (`element_bucket`); raw nature
   mix from NATURE1–9; coarse cause mix from AGENCY1–9 via `cause_bucket`
   (client / agency / no_fault / other / blank); dollar-error quantiles
   p10/p25/p50/p90/p99 of |AMTERR|, over vs under separately.
3. Drift metric: L1 distance (sum of absolute share differences; 0 =
   identical — see terms.md) between every FY pair on each mix; report the
   max pair and the max adjacent-year pair, plus the largest
   single-category shifts between consecutive years.
4. Synth side: `python3 -m src.synth.generate --n 15000 --seed 7 --dist
   experiments/dist.json --out /tmp/exp34_synth.jsonl` (dist.json is the
   single current national dist, FY2024-calibrated; persistent buckets on,
   default). Same metrics; L1 from synth to each FY.
5. Policy timeline (grounded via web search): emergency allotments ran
   Mar 2020 – Feb 2023 (Consolidated Appropriations Act, 2023 ended the
   authority; 18 states opted out earlier, some as early as Apr 2021); the
   federal public health emergency ended May 11, 2023; recertification and
   interview waivers unwound through 2023.

Reproducibility:
- `git rev-parse HEAD` → `f515930843d66d784ee1b95288e600de22353bfa`
- `git status --short` at run time: modified
  `experiments/inject.json`, `src/synth/dollar_mech.py`,
  `src/synth/errors.py`, `src/synth/household.py` (another researcher's
  uncommitted work; src/ treated as read-only here) plus untracked
  `experiments/exp26`, `exp27`, `exp28`, `exp30`, `exp33`, `exp34`,
  `exp38`, `exp39`, `exp42`, `eval_pilot/` files.

## Results
Row/variance counts per FY (2020 … 2024): 27,112 / 9,832 / 41,391 /
43,776 / 44,891 rows; 12,177 / 4,488 / 20,620 / 22,534 / 23,726 variances.
Synth: 15,000 cases, 6,529 variances.

### Finding mix (case-level shares)

| cat     | 2020  | 2021  | 2022  | 2023  | 2024  |
|---------|-------|-------|-------|-------|-------|
| correct | 0.654 | 0.646 | 0.622 | 0.613 | 0.603 |
| over    | 0.216 | 0.214 | 0.229 | 0.231 | 0.239 |
| under   | 0.131 | 0.140 | 0.149 | 0.156 | 0.158 |

Error rate (over + under) drifts monotonically 0.346 → 0.397.

### Element bucket mix (variance-level shares)

| cat        | 2020  | 2021  | 2022  | 2023  | 2024  |
|------------|-------|-------|-------|-------|-------|
| arithmetic | 0.024 | 0.024 | 0.033 | 0.033 | 0.017 |
| depcare    | 0.021 | 0.019 | 0.014 | 0.013 | 0.016 |
| earned     | 0.237 | 0.210 | 0.226 | 0.243 | 0.243 |
| hhcomp     | 0.023 | 0.022 | 0.023 | 0.026 | 0.026 |
| medical    | 0.048 | 0.047 | 0.047 | 0.042 | 0.046 |
| shelter    | 0.314 | 0.336 | 0.307 | 0.309 | 0.313 |
| sua        | 0.075 | 0.074 | 0.076 | 0.079 | 0.078 |
| unearned   | 0.224 | 0.240 | 0.234 | 0.216 | 0.222 |

### Nature mix (variance-level, selected codes)

| code | 2020  | 2021  | 2022  | 2023  | 2024  |
|------|-------|-------|-------|-------|-------|
| 97 (timing) | 0.413 | 0.379 | 0.399 | 0.408 | 0.389 |
| 53 (deduction wrongly included) | 0.126 | 0.131 | 0.112 | 0.100 | 0.073 |
| 52 (deduction omitted) | 0.072 | 0.077 | 0.081 | 0.082 | 0.060 |
| 38 (more income than budgeted) | 0.075 | 0.080 | 0.083 | 0.081 | 0.074 |
| 99 (other) | 0.062 | 0.067 | 0.069 | 0.066 | 0.035 |
| **56 (deduction budgeted too much)** | 0.000 | 0.000 | 0.000 | 0.000 | **0.068** |
| **57 (deduction budgeted too little)** | 0.000 | 0.000 | 0.000 | 0.000 | **0.034** |
| 58 | 0.000 | 0.000 | 0.000 | 0.000 | 0.004 |
| 35 (unreported income source) | 0.046 | 0.052 | 0.044 | 0.051 | 0.061 |

### Cause mix (variance-level, coarse)

| cat      | 2020  | 2021  | 2022  | 2023  | 2024  |
|----------|-------|-------|-------|-------|-------|
| agency   | 0.323 | 0.342 | 0.340 | 0.325 | 0.338 |
| blank    | 0.355 | 0.327 | 0.342 | 0.337 | 0.125 |
| client   | 0.238 | 0.246 | 0.226 | 0.245 | 0.228 |
| no_fault | 0.000 | 0.000 | 0.000 | 0.001 | 0.239 |
| other    | 0.084 | 0.085 | 0.093 | 0.092 | 0.071 |

### Dollar-error quantiles (|AMTERR|, over vs under)

| stat    | 2020  | 2021  | 2022  | 2023  | 2024  |
|---------|-------|-------|-------|-------|-------|
| over p10 | 3    | 3    | 3    | 4    | 4    |
| over p25 | 9    | 9    | 11   | 14   | 14   |
| over p50 | 24   | 28   | 30   | 36   | 38   |
| over p90 | 168  | 194  | 201  | 235  | 244  |
| over p99 | 404  | 460  | 477  | 561  | 603  |
| under p50| 15   | 19   | 19   | 23   | 23   |
| under p90| 95   | 119  | 117  | 130  | 128  |
| under p99| 264  | 323  | 350  | 327  | 361  |

### Drift: pairwise L1 between FY mixes

| mix      | max L1 (pair)      | max adjacent-year L1 (pair) |
|----------|--------------------|-----------------------------|
| finding  | 0.103 (2020–2024)  | 0.049 (2021–2022)           |
| element  | 0.136 (2021–2023)  | 0.092 (2021–2022)           |
| nature   | 0.324 (2021–2024)  | 0.281 (2023–2024)           |
| cause    | 0.508 (2020–2024)  | 0.501 (2023–2024)           |

Largest single-category consecutive-year shifts: cause no_fault +0.238 and
blank −0.212 (2023→2024); nature 56 +0.068, 57 +0.034, 99 −0.030
(2023→2024); finding correct −0.024 (2021→2022); element shelter −0.030
(2021→2022), earned −0.026 (2020→2021).

### Where the synth point sits (L1 from synth to each FY)

| mix      | 2020  | 2021  | 2022  | 2023  | 2024  |
|----------|-------|-------|-------|-------|-------|
| finding  | 0.099 | 0.083 | 0.039 | 0.035 | 0.023 |
| element  | 0.156 | 0.115 | 0.148 | 0.166 | 0.152 |
| nature   | 0.336 | 0.381 | 0.362 | 0.319 | 0.118 |
| cause    | 0.490 | 0.490 | 0.513 | 0.489 | 0.043 |

Synth dollar quantiles vs FY2024 real: over p50 73 vs 38; over p25 42 vs 14;
under p25 45 vs 9 — synth is noticeably heavier at the low end than any
real year (see caveat below).

## Verdict
**Partially held — the real mixes move, but the two biggest "drifts" are
codebook changes, not behavior.**

1. **Finding mix drift is real and behavioral.** Error rate climbs
   monotonically 0.346 → 0.397 (L1 0.103 across the window, 0.049 in a
   single year). Direction: both over and under shares grow while correct
   shrinks — consistent with the EA unwind (Mar 2023: households returned
   from max-allotment to computed benefits, more room for payment error)
   and rising allotment levels. A single pooled error rate is off by up to
   ~0.10 L1 for FY2020/2021 cases.
2. **Dollar-error scale drift is real.** Over-issuance p50 rises 58%
   (24 → 38) and p90 45% (168 → 244); under p50 rises 53%. Policy
   explanation: larger computed benefits after EA ended + COLA-driven
   allotment growth means every variance carries more dollars.
3. **The nature and cause "drifts" are FY2024 labeling changes.**
   Natures 56/57 (deduction amount budgeted too much/too little) appear
   from zero in FY2024 while 53 and 99 fall — the FY2024 QC technical
   documentation added deduction-amount natures that earlier years coded
   as 53/99. Cause `no_fault` (cause code 26, "change not required to be
   reported/acted upon") jumps 0.001 → 0.239 while blank falls 0.337 →
   0.125: in FY2020–2023, timing (nature-97) variances were recorded with
   blank cause; FY2024 records them as cause 26. (Consistent with exp15's
   FY2024 measurement: blank on ~32% of nature-97 ≈ 0.124 overall.)
4. **Element mix drift is small.** Max adjacent-year L1 0.092, most
   single-category moves ≤ 0.03; FY2021 is noisier (quarter-year sample).

The synth (FY2024-calibrated) sits closest to FY2024/2023 on finding,
nature, and cause by construction, and ~0.08–0.10 farther from FY2020/2021
on finding. Its element mix is roughly equally distant from all FYs
(0.115–0.166) — a generator-side residual, not year-specific.

**Caveat (not exp34's question):** synth low-end dollar quantiles run
heavy vs real (over p25: 42 synth vs 14 real FY2024; under p25: 45 vs 9).
This predates exp34 and belongs to the exp16 dollar-mechanism thread.

**Conditioning design.** A year-conditioned dist IS warranted, but not as
naive per-FY dist files: those would bake the FY2024 codebook break into
the "real" target and launder a reporting change into pretraining labels.
Recommended: (a) a `--year` knob on the generator that swaps the **finding
mix (error rate 0.346–0.397), direction mix, and dollar-error scale** from
per-FY slices, while keeping a **pooled element mix** (drift too small to
matter); (b) pin nature/cause to the FY2024 labeling convention (the
modern, most granular one) rather than chasing it as drift; (c) generate
per-FY slices with a reslicer script in the style of exp28's
`exp28_resliced_mixes.json` rather than hand-editing dist.json.

## Next steps
1. **(Recommended)** Build `exp35` reslicer: emit per-FY (or per-era:
   2020–2022 vs 2023–2024) slices of error_rate, direction_given_error,
   and the dollar-mechanism scale parameters; add `--year` to
   `generate.py` and re-run the finding/dollar calibration (exps 16/24)
   per era. One experiment, additive only.
2. Check the FY2023 vs FY2024 QC technical documentation (chapter V) to
   confirm the nature-56/57 introduction and the nature-97 cause-26
   convention are documented codebook changes, not reviewer behavior
   shifts — one read, no code.
3. The synth low-end dollar overweight (p25 ~3x real) deserves its own
   pass in the dollar-mechanism thread; verify whether it is the
   benefit-noise term or the dollar_mech uncommitted edits before
   re-tuning.
