# Experiment 22 — Second-variance structure and the residual transfer edge
**Date:** 2026-09-29 · **Code:** `experiments/exp22_second_variance_transfer.py`

## Hypothesis
North star gate: **transfer**. Exp 19 falsified exp9's distinct-count
mechanism: at count parity the retry loop still wins element macroF1
(0.304 vs 0.287), and the persistent generator had *more* distinct medical
(310 vs 264) and sua (781 vs 738) cases yet worse F1 (0.181 vs 0.279; 0.079
vs 0.163). Two candidates survived for the residual edge:

1. **Multi-variance structure.** The retry loop records a drawn second
   variance unconditionally whenever the draw set materializes, so its
   error cases carry far more second variances (exp19 scratch check: sua
   0.27 vs 0.09, medical 0.26 vs 0.11 per error case). The persistent flow
   keeps a second variance only if it individually moves the benefit. The
   richer multi-variance cases may give the classifier more realistic
   co-occurrence signal — real QC cases also carry multiple variances.
2. **Household selection.** The retry loop redraws variance draws until one
   materializes (up to 12 attempts), which filters households: its error
   set admits "hard" households where only some corruptions move the
   benefit, a selected subpopulation whose error signatures may be more
   prototypical of real errors.

We hypothesized that giving the persistent generator the retry loop's
multi-variance structure (per-bucket matched second-variance rates) and/or
its selected household population would close the transfer gap. If neither
moves the needle, the residual edge is something else entirely (e.g. the
retry loop's label noise — its recorded first variance need not be the one
that moved the benefit — or an interaction neither ablation isolates).

(Metric definitions in `terms.md`: accuracy = fraction of cases where the
predicted element bucket is exactly right; macroF1 = per-bucket F1
averaged plainly, so rare buckets count as much as common ones — the
headline metric for element classification transfer. "Second variance" =
an error case carrying 2 recorded variances; the training label is always
the *first* variance's element bucket.)

## Method
Exp 19's battery, re-run on the current generator: element task only,
v1 features (9 raw), `HistGradientBoostingClassifier(random_state=0)`,
`class_weight="balanced"`, 20k synth baselines (seed 7, same command flags:
`--max-attempts 12`; retry-loop arms pass `--no-persistent-buckets`
explicitly — the generate.py default is persistent, no regression of that
fix), the same real FY2024 QC test split (17,318 test rows after exp9's
bucket filter; the test set is never touched). Real QC microdata is used
for the test split and for aggregate reference rates only — never trained
on, never written into the repo.

Arms:
- **(b)** persistent + balanced — exp19 replication (0.478/0.288)
- **(c)** retry-loop + balanced — exp19 replication, the bar (0.437/0.304)
- **(h)** persistent + second variances injected at retry-loop per-bucket
  rates + balanced. For each persistent error case labeled bucket b with a
  single variance, inject one retry-style second variance (drawn from the
  retry loop's 1/eff-weighted applicable mix via the generator's own
  `_apply_one`/`_draw_nature` machinery, applied to the agency facts,
  recorded unconditionally like the retry loop; redrawn if it exactly
  offsets variance 1) with probability sized so the final per-bucket
  second-variance rate lands on the retry loop's rate. Labels (variances[0])
  never change; only the agency-view features change.
- **(i)** retry-loop, single-variance cases only + balanced — the ablation
  direction: if multi-variance structure is the mechanism, removing it
  should cost the retry loop its edge. (Caveat: also drops 19% of training
  rows, concentrated on hard households — see verdict.)
- **(j)** persistent generator run on retry-selected households + balanced —
  the selection test: for each retry-loop error household, run the
  persistent injection (shared phase-1 coin forced on so only the
  materialization screen differs) and keep it iff it yields an error. Same
  generator as (b); only the household population differs.

**Replication note (important).** The first run of this battery on the
working tree did NOT replicate exp19: (b) 0.283 but (c) 0.273 — the retry
edge was gone, and baseline class counts drifted (e.g. retry hhcomp 468
vs exp19's 735). Root cause: exp24's *uncommitted* rebaseline changed the
generator after exp19 ran — `ZERO_BASE_WEIGHT` emptied (adopting exp21's
audit) and `_inject_persistent` switched from the scalar 1/eff_b correction
to a per-(bucket, stratum) materialization matrix (`--legacy-materialization`
restores the old path). The retry loop's applicable mix changed too via the
emptied weights. Verified: a pristine tree (`git archive HEAD src`,
`/tmp/pristine/src`) reproduces exp19's 20k counts *exactly* (persistent
420/262/310/72, retry 735/508/264/82 across hhcomp/arithmetic/medical/
depcare) and its transfer numbers ((b) 0.478/0.288, (c) 0.437/0.304).
The battery below ran against the pristine pre-exp24 generator
(`--synth-src /tmp/pristine/src`; dist.json/eff.json/inject.json are
tracked and unmodified, so the same files serve both). A second run on the
current working tree is reported separately — its headline is that the
retry edge no longer exists there.

Key comparisons: (h) vs (b) and (h) vs (c) — does injected structure lift
persistent / close the gap; (c) vs (i) — what removing multi-variance costs
the retry loop; (j) vs (b) and (j) vs (c) — does the retry household
population lift persistent / close the gap. Gap attribution: each
mechanism's macroF1 delta as a share of the (c)−(b) gap.

Also measured: (1) per-bucket second-variance rates in both generators'
20k training pools plus the real QC reference (ELEMENT1–ELEMENT9 arrays);
(3a) observable feature distributions (income, household size, earner
status, etc.) of retry-selected vs persistent-selected households, with
standardized mean differences, and the screen asymmetry P(retry screen |
persistent error household) vs P(persistent screen | retry error
household) with the shared coin forced on.

## Results

All numbers below are the pristine pre-exp24 run (replication OK on all
four rare buckets; (b)/(c) reproduce exp19 exactly). The working-tree run
is reported at the end.

### Second-variance rates (fraction of error cases with >= 2 variances)

| bucket | persistent | retry-loop | real QC (n) |
|---|---|---|---|
| earned | 0.098 | 0.155 | 0.278 (5,057) |
| shelter | 0.105 | 0.226 | 0.143 (5,570) |
| unearned | 0.087 | 0.150 | 0.303 (3,879) |
| sua | 0.093 | 0.280 | 0.181 (1,058) |
| medical | 0.103 | 0.288 | 0.225 (719) |
| hhcomp | 0.055 | 0.156 | 0.423 (544) |
| arithmetic | 0.042 | 0.165 | 0.120 (274) |
| depcare | 0.083 | 0.195 | 0.327 (217) |
| overall | 0.093 | 0.190 | 0.236 |

The retry loop carries ~2x the persistent rate in every bucket, and is
closer to the real QC rate (0.190 vs 0.093 vs real 0.236) — but real cases
are more multi-variance than *either* generator in most buckets (earned
0.278, unearned 0.303, hhcomp 0.423, depcare 0.327): a calibration gap for
future generator work. Arm (h)'s injection hit its per-bucket targets
(achieved 0.152–0.284 vs targets 0.150–0.288).

### Transfer battery (synth→real, element, v1, balanced)

| arm | acc | macroF1 | train rows |
|---|---|---|---|
| (b) persistent + balanced | 0.478 | 0.288 | 7,703 |
| (c) retry-loop + balanced | 0.437 | **0.304** | 7,772 |
| (h) persistent + 2nd-var at retry rates | 0.464 | 0.288 | 7,703 |
| (i) retry-loop, single-variance only | 0.434 | 0.292 | 6,299 |
| (j) persistent on retry-selected households | 0.469 | **0.302** | 4,846 |

Per-bucket F1s:

| bucket | (b) | (c) retry | (h) inject | (i) retry-1var | (j) retry-hh |
|---|---|---|---|---|---|
| earned | 0.665 | 0.662 | 0.697 | 0.619 | 0.689 |
| shelter | 0.573 | 0.471 | 0.526 | 0.516 | 0.529 |
| unearned | 0.376 | 0.374 | 0.380 | 0.378 | 0.371 |
| sua | 0.092 | 0.163 | 0.088 | 0.132 | 0.134 |
| medical | 0.175 | 0.279 | 0.182 | 0.202 | 0.201 |
| hhcomp | 0.165 | 0.185 | 0.154 | 0.193 | 0.155 |
| arithmetic | 0.089 | 0.130 | 0.067 | 0.117 | 0.159 |
| depcare | 0.171 | 0.168 | 0.208 | 0.179 | 0.183 |

### Gap attribution (macroF1; gap = (c)−(b) = 0.0159)

| mechanism | delta | share of gap |
|---|---|---|
| (h)−(b): 2nd-variance injection into persistent | −0.0006 | −3.5% (no lift) |
| (c)−(i): removing multi-variance from retry | +0.0122 | 76.6% of gap removed |
| (j)−(b): retry-selected household population | +0.0142 | **89.3% of gap closed** |

### Household selection measurements

Screen asymmetry (shared coin forced on, n=3,000 each):
P(retry screen passes | persistent error household) = 0.975;
P(persistent screen passes | retry error household) = 0.612.
The retry screen admits a superset: 38% of retry error households would be
*clean* under the persistent generator — the "hard" households.

Observable differences, retry-error (A) vs persistent-error (B)
households (standardized mean differences):

| observable | mean A | mean B | SMD(A−B) |
|---|---|---|---|
| unearned | 587 | 697 | −0.211 |
| senior_disabled | 0.321 | 0.364 | −0.090 |
| n_elderly | 0.204 | 0.227 | −0.055 |
| shelter | 669 | 637 | +0.056 |
| medical_exp | 13.1 | 16.1 | −0.050 |
| hh_size | 2.15 | 2.20 | −0.035 |
| earned | 504 | 519 | −0.020 |

Both error sets are enriched for earners vs the household population
(SMD ≈ +0.26); the retry screen additionally admits lower-unearned,
less-senior households. Arm (j) kept 4,846 of 7,772 retry error
households (62%) as persistent errors.

Calibration of the training subsets: element-mix L1 vs real — (b) 0.163,
(c) 0.293, (h) 0.163, (i) 0.283, **(j) 0.124** (most faithful);
direction-mix L1 vs real — (b) 0.068, (c) 0.048, (h) 0.069, (i) 0.042,
(j) 0.102.

### Working-tree (post-exp24) run — the retry edge is gone

Same battery on the current working tree (exp24's rebaseline):

| arm | acc | macroF1 |
|---|---|---|
| (b) persistent + balanced | 0.479 | **0.283** |
| (c) retry-loop + balanced | 0.440 | 0.273 |
| (h) persistent + 2nd-var | 0.459 | 0.275 |
| (i) retry single-var | 0.457 | 0.275 |
| (j) persistent on retry hh | 0.492 | 0.272 |

Baseline class counts drifted (retry hhcomp 468 vs 735; persistent hhcomp
283 vs 420) because exp24 emptied `ZERO_BASE_WEIGHT` (both generators'
applicable mix) and re-weighted persistent draws with the materialization
matrix. Neither mechanism arm moves transfer here — consistent with there
being no gap left to explain.

## Verdict

Hypothesis **partially supported: the residual edge is household
selection, not multi-variance structure.**

- **Structure rejected.** Injecting retry-rate second variances into
  persistent cases (h) leaves macroF1 exactly flat (0.288 → 0.288) and
  lifts no rare bucket — sua 0.088 vs 0.092, medical 0.182 vs 0.175,
  arithmetic *worse* at 0.067 vs 0.089. Richer co-occurrence signal does
  not transfer the edge. (This also fits exp19's inverted-U: more
  distortion past the optimum hurts.)
- **Selection supported.** Training the persistent generator on
  retry-selected households (j) closes 89% of the gap (0.288 → 0.302 vs
  the (c) bar of 0.304) — with 37% *fewer* training rows (4,846 vs 7,703),
  so this is population, not size. The retry loop's redraw-until-
  materialize admits "hard" households (38% would be clean under the
  persistent screen) whose error signatures transfer better; the (j)
  population also has the most faithful element mix of any training subset
  (L1 0.124).
- **The (i) ablation is consistent, with a caveat.** Dropping
  multi-variance cases from retry costs 76.6% of the gap (0.304 → 0.292) —
  but (i) also drops 19% of rows, concentrated on the hard households, so
  structure-removal and selection-removal are confounded there. (h)'s clean
  null says structure *alone* isn't the mechanism; the (i) drop is better
  read as losing hard-household signal than as losing co-occurrence signal.
  Note (i) at 0.292 still beats (b) at 0.288: single-variance retry cases
  on retry-selected households retain most of the edge — again selection.

Per-bucket nuance: selection ((j)−(b)) over-explains arithmetic (0.159 vs
(c)'s 0.130) but under-explains medical (0.201 vs (c)'s 0.279 — only ~25%
of the medical F1 gap). Medical's remainder is still unexplained (structure
adds ~7%); candidates are the retry loop's label noise (its recorded first
variance need not be the one that moved the benefit) or its nature mix.

Precision note on the mechanism: the retry loop does not "redraw
households" — it redraws *variance draws* on a fixed household (up to 12
attempts); the household filter is the emergent effect. The phase-1
injection coin is shared by both generators, so only the materialization
screen differentiates them.

Doctrine update: on the current (post-exp24) generator the retry edge no
longer exists — persistent + balanced (0.283) beats retry + balanced
(0.273) — so exp19's "retry-loop + class balancing" training recipe does
not survive the rebaseline. The selection finding suggests the better
recipe direction is a generation-time "hard-household" bias inside the
persistent generator (which stays the data product), not the retry loop.

## Next steps

1. (Recommended) Re-derive the classifier-training recipe on the current
   post-exp24 generator (exp19's next-step #3, now live): confirm
   persistent + balanced is the best of the simple recipes, and test a
   generation-time hard-household knob — e.g. oversample
   retry-materializable households in the persistent pool — which the
   selection result predicts should lift transfer *and* element-mix
   fidelity without the retry loop's distortion.
   - **Done →** [exp25](exp25_training_recipe.md): Recipe re-derived on the post-exp24 generator.
2. Disentangle the (i) ablation: subsample (c) to (i)'s 6,299 rows while
   holding the multi-variance rate fixed, to separate structure-removal
   from the size/hard-household confound.
3. Probe medical's residual: selection closes ~25% and structure ~7% of
   the retry loop's medical F1 edge (0.279 vs 0.175) — test whether the
   retry loop's label noise (first variance not necessarily the
   materializing one) or its nature mix carries the rest.
4. Generator calibration follow-up (independent of transfer): real QC
   cases are more multi-variance than either generator (overall 0.236 vs
   retry 0.190 vs persistent 0.093; hhcomp 0.423, depcare 0.327) — the
   draw-time multi-variance rate is a fidelity gap even though (h) shows
   naive injection doesn't buy transfer.
