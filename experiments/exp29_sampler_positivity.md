# Experiment 29: closing the household-sampler base-positivity gaps

## Hypothesis

Exp21 found per-stratum base-positivity gaps between the real QC file and
the household sampler that are independent of the variance-injection
draw (the draw target is the marginal empirical mix either way):
unearned too low on senior strata (real P(une>0) 0.95/0.81), shelter too
low on earner/senior strata (real 0.88/0.91/0.95), and sua flat 0.72 in
the sampler vs a real 0.46-0.88 per-stratum spread. Exp24 staged this
sampler follow-up as next step 6.

Stratum-conditioning the sampler's P(unearned>0), P(shelter>0), P(sua>0)
to the real per-stratum aggregates closes all three gaps to within 0.05
absolute per stratum, keeps finding L1 <= 0.030, and does not regress
any per-case element ratio by more than 0.10x -- without touching
benefit math or the corruption mechanics.

## Method

The generator edit is `src/synth/household.py`'s `BASE_POSITIVITY`
tables: pre-screen draw probabilities per stratum, tuned so post-screen
P(base>0) matches the real FY2024 QC per-stratum aggregates. Strata are
`_stratum_key` (earner/no_earner x senior/nonsenior), knowable mid-sample
because earned and senior_disabled are fixed before these fields.

Tuning notes: the values are PRE-screen probabilities -- the income
screen attenuates unearned on earner strata (drawn unearned often fails
the net-income test), so earner_nonsenior needs pre-screen 0.492 to land
post-screen 0.260. The earner_senior unearned cell is steep enough to
need bisection (pre 0.913 -> post 0.809). Final table:

| stratum | unearned | shelter | sua |
|---|---|---|---|
| no_earner_nonsenior | 0.465 | 0.500 | 0.456 |
| earner_nonsenior | 0.492 | 0.876 | 0.811 |
| no_earner_senior | 0.953 | 0.909 | 0.823 |
| earner_senior | 0.913 | 0.908 | 0.886 |

Two dependent calibrations were re-derived under the new sampler, per
their documented maintenance rules ("re-run whenever the sampler
changes"):

1. The per-(bucket, stratum) materialization matrix in
   `src/synth/errors.py`: exp21's procedure, 150k cases, seed 11.
   Re-measurement showed 15/32 cells shifted >= 0.05
   (sua/earner_senior 0.525 -> 0.689, sua/no_earner_senior 0.380 ->
   0.507, shelter/no_earner_senior 0.426 -> 0.532), which triggered the
   task's conditional permission to re-measure. Adoption rule: >= 200
   draws take the new value, 8 tiny-sample cells pool the exp24 value.
2. The 97-resolution direction coins in `experiments/inject.json`
   (`p_over_97_resolve`): `calibrate_injection.py` phase 2, n=4000,
   seed 21, imported not duplicated. The new base positivity changed
   directional materialization asymmetry (shelter/sua 97s), so the
   attrition correction moved (shelter 0.5347 -> 0.4945, sua 0.6845 ->
   0.6288). Phase-1 persistent coins untouched (realized P(err|status)
   still on target).

A concurrent worker (exp28) landed `_DEPCARE_KID_WEIGHT` and new
`_NATURE_57_WEIGHT` in `src/synth/errors.py` mid-experiment and
temporarily overwrote the re-measured matrix (restored from
`experiments/exp28_exp29_matrix_backup.json`, verified identical to the
150k measurement). Those mechanisms are orthogonal to this hypothesis,
so all arms neutralize them in-process (kid-weight 1.0, exp13
57-weights); the AFTER arm measures exp29's changes only. The live repo
combines both experiments' adoptions; the coordinator merges.

Validation: `experiments/exp29_sampler_positivity.py`, 20k cases,
seed 7. Three arms, all paired (identical rng call order, in-process
patching): BEFORE (exp24 defaults exactly: legacy sampler + exp24
matrix + old 97 coins), MID (new sampler + old matrix + old coins, for
attribution), AFTER (exp29's new defaults: new sampler + re-measured
matrix + new 97 coins).

## Results

Base-positivity gaps, worst |real - synth| per stratum
(sampler P(base>0) measured on 100k households, seed 5):

| arm | unearned | shelter | sua |
|---|---|---|---|
| BEFORE worst | 0.140 | 0.269 | 0.269 |
| AFTER worst | 0.005 | 0.005 | 0.009 |

All three gaps close from up to 0.269 to at most 0.009.

Finding mix (correct / over / under) and finding L1 vs real
(0.603 / 0.239 / 0.158):

| arm | correct | over | under | L1 |
|---|---|---|---|---|
| BEFORE | 0.609 | 0.245 | 0.146 | 0.023 |
| MID | 0.598 | 0.259 | 0.143 | 0.039 |
| AFTER | 0.604 | 0.251 | 0.145 | 0.026 |

The MID arm shows the dependent-calibration interaction the task asked
to check: the new sampler with the stale matrix/coins degrades L1 from
0.023 to 0.039. The residual traced to direction mix -- shelter P(over)
0.478 -> 0.538 and sua P(over) 0.617 -> 0.650 -- because the 97 coins
were attrition-corrected under the old sampler's directional
materialization asymmetry. Re-measuring the matrix and re-deriving the
coins recovers L1 to 0.026, within the 0.030 bar.

Per-case element ratios (synth / real):

| bucket | BEFORE | AFTER | \|r-1\| change |
|---|---|---|---|
| earned | 0.79x | 0.77x | +0.02 |
| unearned | 0.89x | 0.90x | -0.01 |
| shelter | 0.86x | 0.91x | -0.06 |
| sua | 0.92x | 0.94x | -0.02 |
| medical | 0.55x | 0.59x | -0.04 |
| depcare | 0.44x | 0.41x | +0.03 |
| hhcomp | 0.99x | 1.08x | +0.07 |
| arithmetic | 1.01x | 0.98x | +0.01 |

Worst |r-1| regression: +0.067 (hhcomp), inside the 0.10 bar. Shelter and
sua improve (0.86 -> 0.91x, 0.92 -> 0.94x) as the base positivity feeds
more real shelter/sua cases into the draw.

Dollar marginals spot-check (error cases, absolute $): before mean
96.3 / median 76, after mean 96.2 / median 76 -- unchanged, as expected
(no dollar-mechanism change). The known over/under median asymmetry
(real 38/23 vs synth 73/83) persists; that is exp23 territory, not this
experiment's.

Stratum shares (real vs AFTER): 0.331/0.385, 0.238/0.251, 0.396/0.346,
0.035/0.018 -- the sampler's earner/senior draw rates were not touched,
so the pre-existing no_earner_senior under-share is unchanged by this
experiment.

## Verdict

| check | bar | result |
|---|---|---|
| base-positivity gaps <= 0.05 per stratum | 0.05 | PASS (worst 0.009) |
| finding L1 <= 0.030 | 0.030 | PASS (0.026) |
| no element ratio regresses > 0.10x | 0.10 | PASS (worst +0.067) |

**HOLDS.**

## Next steps

1. Coordinator: merge exp29's adoptions (household.py sampler,
   errors.py matrix, inject.json 97 coins) with exp28's
   (_DEPCARE_KID_WEIGHT, _NATURE_57_WEIGHT). Both are live in the
   working tree; the matrix conflict is resolved (exp29's re-measured
   table restored from exp28's backup; exp28's other changes kept).
   Note the final validation above neutralized exp28's mechanisms
   in-process, so a merged-state re-validation is the coordinator's
   call.
2. The realized P(err|earner) = 0.576 vs empirical 0.592 shortfall
   predates this change (old defaults also 0.578); out of scope here,
   candidate for a future injection experiment.
3. Stratum share mismatch (no_earner_nonsenior 0.385 vs real 0.331,
   no_earner_senior 0.346 vs 0.396) is a sampler composition question
   for a future experiment, not this one.
   - **Partly done →** [exp44](exp44_size_mix.md): Household size mix fitted to real (hhcomp/arithmetic → 1.0x); stratum composition via the earner×senior joint is still open.
