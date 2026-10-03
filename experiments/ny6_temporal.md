# NY6 — temporal stability: does the NY transfer signal hold year to year?

**Date:** 2026-09-29 · **Code:** `experiments/ny6_temporal.py`

## Hypothesis

NY1's NY-conditioning offsets were fit on pooled FY2020–2024 NY microdata,
which launders recent-year marginals into the "training" side of any
temporal test. If the NY signal (which buckets, which directions, which
causes — NY3's timing-dominated profile) is genuinely process-layer, then
a model trained on FY2020–22-fit synthetic should predict FY2023–24 real NY
cases about as well as it predicts FY2020–22 cases, and refitting on old
years should cost little versus the pooled fit. If the signal is
year-specific, the temporal test will decay and the POC needs annual
refitting. Gate: transfer (the north star's transfer gate, extended across
time). NY1's NY3 documented one real FY trend — shelter's variance share
climbing 19.6% → 30.3% — so the test has genuine drift to survive.

## Method

**Refit (this experiment's work):** called NY1's `fit_ny_targets` with
`fys=[2020, 2021, 2022]` (the `fit` CLI subcommand has no `--fys` flag — it
always fits pooled; the year filter is applied by calling the fit function
directly from this script, documented here). NY rows: 1,516 (FY2020 399 /
FY2021 221 / FY2022 896 — the task brief's "1,716" was an arithmetic slip;
399+221+896 = 1,516, matching the fit's row count). Converted the fit output
to `ny_state` constant overrides with NY1's identical guards, installed by
monkey-patching the `src.synth.ny_state` module attributes (no src file
modified; every generator function reads these globals at call time), then
replicated NY1's it2 recipe:

1. pure-empirical FY2020–22 bucket ratios: earned 0.926, unearned 1.098,
   shelter 0.745, sua 1.560, medical 2.067; depcare/hhcomp/arithmetic guarded
   to 1.0 (NY unweighted n < 25 in the FY2020–22 window — **hhcomp loses its
   pooled-fit adjustment**, NY1 pooled had 1.585);
2. one-step realized-output bucket calibration × real_NY_share/synth_share
   on a 20k-case pilot (multipliers: earned 0.969, unearned 1.074,
   shelter 1.063, sua 0.811, medical 1.092; calibrated: earned 0.897,
   unearned 1.178, shelter 0.792, sua 1.264, medical 2.257);
3. NY_COIN_CAL line search over NY1's grid {0.90, 0.93, 0.96, 1.0} on 8k-case
   pilots — chosen **0.90** (not NY1's 0.96: the FY2020–22 target case-error
   rate 0.3602 is below the pooled 0.3655, so the downward correction needs
   to be bigger; the grid floor binds — 0.90 lands synth_err 0.3622, L1
   0.0327);
4. final generation n=20,000, seed 7 (NY2's n/seed conventions) → refit
   finding L1 vs real NY FY2020–22 = 0.0338 (synth c/o/u
   0.6441/0.2192/0.1368 vs real 0.6398/0.2065/0.1537).

exp34's codebook caution is handled: nature/cause offsets are pinned to the
FY2024 `dist.json` convention (the generator's national base), and NY's
nature-97 cause-blank rate was checked per FY: 2020 0.193, 2021 0.345,
2022 0.231, 2023 0.216, 2024 0.117. No labeling break — the generator's 97
resampling design (NY1) is not contradicted — but there is real drift in
review practice: FY2024 NY records 97 causes far more often than FY2021
does. The refit uses the FY20–22 value (0.2576); the FY23–24 drift is a
mild cause-task caveat. The element/finding labels (STATUS, ELEMENT codes)
are stable across the window.

**Arms (all: PA2's recipe — v1 features, sklearn
HistGradientBoostingClassifier(random_state=0), defaults, no class_weight;
NY2 does not exist yet, so there is no same-period NY reference — NY2 runs
in parallel and will supply it):**
- T_refit: FY2020–22-fit NY synth → tested on FY2023–24 real NY (clean
  temporal test, 1,741 rows, 653 error cases) AND on FY2020–22 real NY
  (train-period reference, 1,516 rows, 541 error cases).
- T_pooled: pooled-fit NY synth (NY1 as-is, generated before any patching)
  → same two test sets (does refitting on old years matter?).
- T_excl21: FY2020+2022-only-fit NY synth (FY2021 excluded) through the same
  recipe — the FY2021 partial-year sensitivity arm.

**Caveats (both directions):** the FY2020–22 test set for T_refit, and the
FY2023–24 test set for T_pooled, share their rows' *marginals* with the
respective offset fits (PA2's caveat, unchanged). This slightly favors the
pooled arm on the FY23–24 head-to-head and the refit arm on the FY20–22
head-to-head. Note the asymmetry this creates in the headline table below:
on FY23–24, T_pooled is the caveat-favored arm and still loses on element
accuracy.

## Results

### Headline: element + finding, both arms, both periods

| arm | test | element acc | element macroF1 | finding acc | finding macroF1 |
|---|---|---|---|---|---|
| T_refit (FY20–22 fit) | FY23–24 | 0.4824 | 0.1953 | 0.4773 | 0.4248 |
| T_refit (FY20–22 fit) | FY20–22 | 0.3937 | 0.1590 | 0.3701 | 0.3392 |
| T_pooled (NY1 as-is) | FY23–24 | 0.4502 | 0.1928 | 0.4474 | 0.3856 |
| T_pooled (NY1 as-is) | FY20–22 | 0.4122 | 0.1745 | 0.3615 | 0.3365 |
| T_excl21 (FY20+22 fit) | FY23–24 | 0.4717 | 0.1646 | 0.4750 | 0.3783 |
| T_excl21 (FY20+22 fit) | FY20–22 | 0.4233 | 0.2023 | 0.4334 | 0.3682 |

**Train-period vs test-period gap (T_refit):** element acc **+0.089**
(0.3937 → 0.4824), macroF1 +0.036. No decay on the gate metric — a rise.
Finding acc +0.107 / macroF1 +0.086 — also a rise.

**Does refitting on old years matter (T_refit vs T_pooled on FY23–24)?**
Element: refit +0.032 acc, macroF1 a wash (0.1953 vs 0.1928). Finding:
refit +0.030 acc, +0.039 macroF1 (0.4248 vs 0.3856). The refit arm wins the
clean temporal test on every metric even though the pooled arm had the
caveat advantage (its fit saw the FY23–24 marginals). No meaningful penalty
for fitting on 2020–2022 only — refitting on old years is at least as good.

### The cross-period swings are mix stories, not signal

**Element.** A follow-up diagnostic (true vs predicted bucket mixes on each
period) shows the synth-trained model is a shelter/unearned-biased
predictor: on the FY20–22 test it predicts shelter 0.338 / unearned 0.323
vs true 0.244 / 0.272. Between periods the true mix shifts toward the
model's biases — shelter 0.244 → 0.294, and sua 0.105 → 0.055, a bucket the
model essentially never predicts (pred 0.020/0.015, F1 0.059/0.130). The
+8.9pp accuracy "rise" is mix-alignment: NY3's shelter-climb trend hands
the model more of what it predicts best, and shrinks the bucket it can't
predict at all. Do not read it as transfer gain — and do not read the low
FY20–22 accuracy as signal decay either. The honest reading: per-bucket F1s
are the signal, and they are flat-to-rising in the dominant buckets (below).

**Finding.** Real NY case-error rate: 0.3602 (FY20–22) → 0.3728 (FY23–24),
+1.3pp; p(over|err) 0.5734 → 0.5773; finding-mix L1 between periods ≈ 0.025.
The refit synth's P(error) = 0.362 matches the *fit* period. PA2 showed the
synth-trained classifier predicts error too eagerly (below majority on hard
accuracy); on FY23–24 that bias is punished slightly less because the true
error rate is a touch higher. Same prior story as PA6's PA analysis, much
smaller drift: the +10.7pp finding-accuracy swing is prior-calibration, not
better signal.

### Per-bucket F1 decay diagnosis (T_refit, FY20–22 → FY23–24, element task)

| bucket | FY20–22 F1 | FY23–24 F1 | delta | test-set n |
|---|---|---|---|---|
| shelter | 0.406 | 0.549 | +0.142 | 132 → 192 |
| earned | 0.633 | 0.675 | +0.041 | 125 → 173 |
| unearned | 0.373 | 0.409 | +0.036 | 147 → 162 |
| sua | 0.059 | 0.130 | +0.072 | 57 → 36 |
| medical | 0.237 | 0.105 | **−0.132** | 44 → 38 |
| hhcomp | 0.000 | 0.000 | 0.000 | 16 → 26 |
| arithmetic/depcare/other/standard/reporting/childsupport | ≤0.333 | noisy | ± | ≤7 each |

The three dominant buckets (shelter, earned, unearned) all *rise*; sua
improves from a low base. The one real decay is **medical** (−0.132) — and
it was already poorly predicted in the train period (F1 0.237, the
mechanics-gap bucket exp4_v3/PA6 flagged, not a temporal story). It is also
NY's most over-represented bucket (1.79x national, NY3), so it stays the
bucket to watch. hhcomp is F1 0.000 both periods with n=16/26: the refit
lost NY1's pooled hhcomp adjustment (1.585) to the sparsity guard, and NY's
1.58x hhcomp over-representation is therefore *not* in the refit synth. For
the POC this is acceptable (hhcomp is 3–4% of test variances) but an annual
refit would silently drop it.

### FY2021 sensitivity (the partial-year file)

FY2021 is Jul–Sep only: 221 NY rows (14.6% of the fit). Excluding it moves
the fit: finding c/o/u 0.6398/0.2065/0.1537 → 0.6585/0.1930/0.1485,
case-error rate 0.3602 → 0.3415 (−1.9pp), p(over|err) 0.5734 → 0.5651.
Bucket ratios move modestly-to-materially (earned 0.926→1.042, unearned
1.098→1.010, shelter 0.745→0.746, sua 1.560→1.631, medical **2.067→1.663** —
the medical adjustment is the most FY2021-sensitive). The full exclusion
recipe chose the same NY_COIN_CAL=0.90, but that comparison is shallow: the
scalar sits at the grid floor in *both* fits, so the scalar test can't
distinguish the way PA6's did (PA: 1.00 vs >1.00). FY2021's influence shows
in the *target*, not the chosen scalar — a wider grid (e.g. 0.86) would
quantify it. T_excl21 on FY23–24 lands close to T_refit (element acc
0.4717 vs 0.4824, macroF1 0.1646 vs 0.1953; finding 0.4750/0.3783 vs
0.4773/0.4248) — including the partial year is harmless for transfer, but
it is still bad hygiene: a production refit cadence should drop partial
years (they move the medical bucket ratio and the error-rate target while
contributing only 15% of rows).

## Verdict

**The NY signal holds year-to-year well enough for the POC; annual
refitting is not required.** The element gate metric does not decay across
the period boundary (accuracy +8.9pp, macroF1 +3.6pp — a mix-alignment rise,
not a decay), per-bucket F1s are flat-to-rising in every dominant bucket
(shelter +0.142, earned +0.041, unearned +0.036), and the pooled fit —
which cheats by seeing the test marginals — loses to the FY20–22 refit on
the clean temporal test (element acc 0.4502 vs 0.4824; finding acc 0.4474
vs 0.4773, macroF1 0.3856 vs 0.4248). The finding task's cross-period
swings are prior-calibration artifacts (same mechanism PA6 named), not
signal decay: refit the P(error) prior per era (or threshold-tune on a
recent real slice), don't retrain the element model annually. Two process
notes for any future refit: (1) exclude partial-year files — FY2021's 221
rows moved the fitted error rate by 1.9pp and the medical bucket ratio by
20%; (2) the buckets to watch are **medical** (the only real F1 decay,
already the mechanics-gap bucket) and **hhcomp** (its 1.585x pooled
adjustment is silently dropped by the sparsity guard in any pre-2023
refit).

## Next steps

- **NY2** consumes `generate_ny` for the transfer experiment (NY1's API,
  unchanged); it supplies the missing same-period NY reference quoted here
  as unavailable.
- **Medical-bucket deep-dive** if NY2's transfer disappoints there: NY is
  1.79x national on medical and the only bucket with a real temporal F1
  decay (−0.132) — separate mechanics-gap from drift before tuning.
- If dollar-amount transfer underperforms, use NY1's defined lever: a
  97-vs-non97 (or per-bucket) dollar scale (NY1's structural limitation
  note) — the coin scalar can't fix it.
- Optional: widen the coin-cal grid below 0.90 to fully quantify FY2021's
  scalar influence (currently the grid floor binds in both fits).
- Refit-cadence rule for production (not POC): drop partial-year QC files,
  keep a standing medical/hhcomp watch. One-line change, no experiment.

## Reproduction

```bash
# full experiment (fits, refit recipe, excl21 sensitivity, transfer battery)
python3 experiments/ny6_temporal.py
# results -> /tmp/ny6out/ny6_results.json, synth files -> /tmp/ny6out/

# refit-target provenance (pure empirical FY20-22 targets):
python3 - <<'EOF'
import sys; sys.path.insert(0,'experiments')
from ny1_ny_generator import fit_ny_targets
t = fit_ny_targets('/home/hatch/workspace/snap-qc-data/raw', fys=[2020,2021,2022])
print(t['n_ny_rows'], round(t['ny']['case_err_rate'],4))
EOF
```

Timing: ~311s on CPU. Conventions honored: no emojis, FYWGT-weighted,
no model weights, synth to /tmp/ny6out (never the repo), seed 7, CPU only.
Nothing committed or pushed; no existing file modified.
