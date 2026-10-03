# snap-qc-per-experiments

Experiments toward a **small, domain-specific language model for SNAP payment
accuracy** — a QC copilot trained on synthetic QC-style cases with
deterministic ground truth, validated against real QC public-use files.

Read [`NORTH_STAR.md`](NORTH_STAR.md) first: it defines the goal, the
synthetic-first data strategy, and the three validation gates (calibration,
transfer, LM eval) every experiment here must move.

## Repo map

- `src/synth/` — synthetic QC case generator: household sampler, deterministic
  benefit math (a stand-in for the QC Minimodel), and a variance injector that
  samples element/nature/cause from empirical QC distributions.
  Parameters are approximations, documented in `src/synth/params.py`.
- `experiments/` — one script + one chronicle doc per experiment.
  `build_dist.py` / `measure_effectiveness.py` are shared tooling;
  `dist.json` and `eff.json` are committed so the repo runs without the
  21MB real-data download.
- `experiments/TEMPLATE.md` — chronicle template. Every experiment gets:
  hypothesis (tied to the north star) → method → results → verdict → next
  steps.
- `terms.md` — glossary: evaluation metrics (L1, F1, macro F1, AUC) and
  generator vocabulary (finding, variance, element/nature/cause, materialize,
  importance weights, coins).

## Experiment index

| # | Experiment | Gate | Verdict |
|---|---|---|---|
| 1 | [Synthetic generator calibration](experiments/exp1_calibration.md) | Calibration | Partially held — taxonomy close, over-issuances underproduced |
| 2 | [Synthetic→real transfer test](experiments/exp2_transfer.md) | Transfer | Held, with headroom — AUC 0.656; element acc 0.422 vs 0.614 real→real |
| 3 | [Calibration v2: income-variance direction fix](experiments/exp3_calibration_v2.md) | Calibration | Held — was a sign bug; finding mix L1 0.30→0.19 |
| 4 | [Transfer v2: richer shared features](experiments/exp4_transfer_v2.md) | Transfer | Held, with a surprise — binary macroF1 0.616 (prior fixed); element v1 0.493 beats v2 0.451 (derived features embed generator assumptions) |
| 4b | [Transfer v3: the persistent generator](experiments/exp4_transfer_v3.md) | Transfer | Did not hold — element acc fell 0.493→0.442 on the faithful mix (class starvation); binary improved 0.616→0.639. Lesson: calibration fidelity ≠ transfer utility; rebalance classes when training |
| 5 | [Calibration v3: omission-coherence fix](experiments/exp5_omission_coherence.md) | Calibration | Partially held — under moved 9.4%→10.9%; problem is *who* gets errors |
| 6 | [Calibration v4: eligibility-screen injection](experiments/exp6_eligibility_screen.md) | Calibration | Held decisively — finding mix L1 = 0.009; realized error 0.396 vs 0.397 |
| 6b | [Calibration methodology: attrition-corrected injection](experiments/exp6_calibration_methodology.md) | Calibration | Load-bearing — phase-1 coins, stochastic-97 coins, two-level effectiveness |
| 7 | [Per-bucket persistence: hybrid single-draw-and-drop](experiments/exp7_per_bucket_persistence.md) | Calibration | Held — hhcomp 2.86x→1.27x, arithmetic 3.47x→1.42x; finding L1 0.010→0.044 (within-direction 57 residual) |
| 8a | [RAWBEN validation for rules recovery](experiments/exp8a_rawben_validation.md) | Rules recovery | Held with filters — AMTERR == |FSBEN−RAWBEN| in 85% exact / 92% within $1; RAWBEN is the issued benefit; drop recoupment-type rows for fitting |
| 8b | [Parameter fitting for rules recovery](experiments/exp8b_parameter_fitting.md) | Rules recovery | Held weakly — national effective params match FY2024 statute exactly (30% rate 0.2995, $672 cap point mass); no misconfiguration signal in 22-state scan. Individual-engine fingerprinting blocked: no vendor IDs, error rows carry reviewer values |
| 9 | [Class-balanced element transfer](experiments/exp9_class_balanced_transfer.md) | Transfer | Did not hold — retry-loop + balanced (0.458/0.274) beats persistent + balanced (0.443/0.252); mechanism is distinct example counts, not priors. Doctrine: train classifiers on retry-loop + balancing, keep persistent generator for the data product |
| 10 | [Statutory parameter refresh (research)](experiments/exp10_statutory_parameter_refresh.md) | Calibration | Partially falsified — benefit math matches FY2024 statute exactly; income-eligibility limits ~6% too high (later-year table), a frame-contamination blindspot. Apply step staged |
| 11 | [Senior-conditioned bucket mixes](experiments/exp11_senior_bucket_mix.md) | Calibration | Partially held — medical 0.11x→0.67x via 4-stratum mixes + removing double-counted zero-base suppression; hhcomp regressed 1.16x→1.91x |
| 12 | [Kid-conditioned depcare](experiments/exp12_kid_depcare.md) | Calibration | Held — depcare 0.03x→0.56x via n_kids + kid-gating; all 8 elements now 0.56x–1.56x |
| 13 | [Per-nature weights for 57](experiments/exp13_nature57_weights.md) | Calibration | Held — nature 57 0.50x→1.04x via 1/m importance weights measured in persistent flow (0.8 damping) |
| 14 | [Bucket materialization correction](experiments/exp14_materialization_correction.md) | Calibration | Did not hold — re-measuring eff_b under stratum mixes improved finding L1 (0.042→0.036) but hhcomp/arithmetic stuck at ~1.5x; scalar eff_b insufficient |
| 15 | [Cause-mix calibration audit](experiments/exp15_cause_audit.md) | Calibration | Held — conditional cause mix L1 = 0.014 (agency/client/other track at ~1.0x); only gap is 12.5% blank causes on nature 97, a labeling rule not yet implemented |
| 16 | [Dollar-error distribution re-check](experiments/exp16_dollar_error.md) | Calibration | Did not hold — dollar marginal drifted: p50 $31 real vs $74 synth, low tail starved (69% ≤ $56 real vs 37% synth), over/under asymmetry inverted, extreme over-tail thin. Corruption mechanics too coarse |
| 17 | [QC-variance eval set design](experiments/exp17_qc_variance_eval_design.md) | LM gate (prep) | Design delivered — 1,200 items, 6 tasks, stratified off the natural prior, composite scoring vs dummy/base/ceiling; 7 open questions for reviewer judgment |
| 18 | [Dollar-error mechanisms](experiments/exp18_dollar_mechanisms.md) | Calibration | Partially held — small-error mode (nature-97 conditioning) + whole-unit ineligibility (p=0.0125) verified; asymmetry mostly fixed (still inverted at p90); finding mix regressed pending recalibration |
| 19 | [Retry-loop + oversampling transfer](experiments/exp19_retry_oversample_transfer.md) | Transfer | Did not hold — exp9's count mechanism falsified: gap survives at count parity (0.287 vs 0.304); second-variance structure the live candidate |
| 20 | [Per-(bucket,stratum) materialization matrix](experiments/exp20_materialization_matrix.md) | Calibration | Partially held — mechanism works (keep rates invariant to draw weights) but not shippable; exposed ZERO_BASE_WEIGHT double-count on the draw side |
| 21 | [Zero-base-weight audit](experiments/exp21_zerobase_audit.md) | Calibration | Largely held — removing the double-count: finding L1 0.036→0.024, hhcomp 1.59→1.11x, arithmetic 1.51→1.10x; stale exp20 matrix does not transfer (re-measure on corrected draw) |
| 22 | [Second-variance structure transfer](experiments/exp22_second_variance_transfer.md) | Transfer | Held — residual edge is household selection (89.3% of gap), not multi-variance structure; on the post-exp24 generator the retry edge no longer exists |
| 23 | [Merge dollar mechanisms + recalibrate](experiments/exp23_merge_recalibrate.md) | Calibration | Partially held — dollar marginal fixed (share ≤$56: 0.36→0.67 vs 0.70 real; p90 inversion fixed) but finding mix not recovered: whole-unit overs double-counted (already coded as earned income); phase-1 coin is direction-blind |
| 24 | [Adopt draw fix + re-baseline](experiments/exp24_adopt_rebaseline.md) | Calibration + Transfer | Partially held — new defaults: finding L1 0.036→0.025 (0.019 retry); macroF1 −0.007…−0.031 — the calibration win and macroF1 loss are the same event (fewer distinct rare examples) |
| 25 | [Training recipe re-derivation](experiments/exp25_training_recipe.md) | Transfer | Did not hold — faithful persistent + balanced remains the best recipe; retry loop has no remaining role. Recipe question closed |
| 26 | [Combine dollar mechanisms with new defaults](experiments/exp26_combine_dollar.md) | Calibration | Held — finding L1 0.016; share ≤$56 0.69 vs 0.70 real; p90 inversion fixed; whole-unit recoded as earned-income zeroing, direction-aware phase-1 coin |
| 27 | [Earned-bucket audit](experiments/exp27_earned_audit.md) | Calibration | Partially held — dominant constraint is the first-variance bucket mix (real M1 earned-richer than marginal); M1/M2 fix → 0.972x but L1 0.037, staged pending direction recalibration |
| 28 | [Shares-game residuals](experiments/exp28_shares_game.md) | Calibration | Partially held — nature-57 1.16x→1.03x (weights re-measured under corrected draw), depcare 0.44x→0.89x (kid-gate dilution fix); medical stuck 0.55x (FSNDIS mis-slicing, blocked on sampler senior-rate fix) |
| 29 | [Sampler base-positivity gaps](experiments/exp29_sampler_positivity.md) | Calibration | Held — worst |real−synth| 0.009 per stratum; finding L1 0.026; materialization matrix + 97-coins re-derived for the new sampler |
| 30 | [QC-variance eval pilot](experiments/exp30_eval_pilot.md) | LM gate (prep) | Package delivered — 1,400 frozen items, scorer + bootstrap gate, Mac Studio runbook; dummy baselines green; LM discrimination pending the Mac Studio run |
| 31 | [Adopt dollar mechanisms as default](experiments/exp31_adopt_dollar.md) | Calibration + Transfer | Adopted — finding L1 0.019, share ≤$56 0.69, p90 inversion fixed; `--dollar-mechanisms` default on; recalibration baked into the module (seed-stable); transfer macroF1 cost −0.003 (acceptable) |
| 32 | [Medical senior-rate fix](experiments/exp32_medical_senior.md) | Calibration | Does not hold (clean partial) — senior-rate fix P(senior) 0.365→0.403, medical 0.64x→0.71x, finding L1 0.008; re-sliced mixes NOT adoptable (hit wrong stratum marginals); remaining senior gap is the household size mix — staged follow-up |
| 33 | [State-level heterogeneity](experiments/exp33_state_heterogeneity.md) | Calibration | Held — state payment error rates span 2.39% (SD) to 17.64% (DC), rankings persistent; variance lives in error size, not frequency; state dimension warranted via per-state error-rate offsets fit from microdata |
| 34 | [Temporal drift FY2020–2024](experiments/exp34_temporal_drift.md) | Calibration | Partially held — finding mix + dollar scale genuinely drift (error rate 0.346→0.397); the big FY2024 nature/cause shifts are codebook changes, not behavior; year-conditioning warranted but must not launder new conventions |
| 35 | [Discriminator diagnostic](experiments/exp35_discriminator_diagnostic.md) | Calibration | Held emphatically — synth-vs-real GBM AUC 0.981; shelter deduction is the biggest leak (shuffling it drops AUC 0.30); even "correct" cases separate at 0.974 |
| 36 | [Transfer scaling curve](experiments/exp36_transfer_scaling.md) | Transfer | Partially held — macroF1 plateaus 0.28–0.30 at N≈5–10k; rare-bucket tail does NOT saturate (medical/hhcomp keep climbing); arithmetic F1 declines with N — fidelity, not volume |
| 37 | [Transfer across model classes](experiments/exp37_transfer_model_classes.md) | Transfer | Did not hold as stated — persistent pool is weakly model-agnostic, but class_weight="balanced" is GBM-specific and harmful for logreg (0.175→0.485 accuracy when removed); transformer probe needed before locking the LM recipe |
| 38 | [Rare-rule mass audit](experiments/exp38_rare_rule_mass.md) | Calibration | Clean negative — student/ABAWD/elderly rules carry ≤1.4% of element-marginal L1; 98.6% of the gap is share mismatches in modeled buckets; no dedicated mechanisms warranted |
| 39 | [Household joint-distribution realism](experiments/exp39_joint_distributions.md) | Calibration | Held — synth mean benefit $423.8 vs real $341.1 is compositional, not a math bug; P(earner\|hhsize) is flat in synth vs 0.14→0.69 real; sampler needs empirical conditional tables |
| 40 | [Published-rate calibration](experiments/exp40_published_rate_calibration.md) | Calibration | Held — generator within ~1pp of microdata-implied dollar rate; published rates run 2–3pp higher, all in the over component (procedural errors); do NOT tune toward published rates |
| 41 | [Policy-QA bridge](experiments/exp41_policy_qa_bridge.md) | LM gate (prep) | Held — benefit calculator scores 21/22 (20/20 in-scope) as a QA oracle; found the $23-minimum eligibility-screen bug; child-support deduction out-of-scope |
| 42 | [Depcare/medical deep dive](experiments/exp42_depcare_medical_deepdive.md) | Calibration | Held — medical residual is the medexp>0 cell under-drawn 2.34x (projection →1.00x); depcare needs kids×earner interaction (projection →0.83x); nature-57 over-drawn 4–7x |
| 43 | [Transformer transfer probe](experiments/exp43_transformer_transfer_probe.md) | Transfer | Staged — design + runnable script + Mac Studio runbook; 4 arms (pool × loss-weight) × 3 seeds on a tiny feature-tokenizer transformer; pre-registered decision bar locks or re-opens the LM recipe's pool and reweighting choices |
| 44 | [Household size-mix fit + re-sliced mixes re-trial](experiments/exp44_size_mix.md) | Calibration | Partially held — size fix is safe (hhcomp/arithmetic →1.0x, L1 ≤0.015, dollars flat) but medical is seed-dependent (0.76x/0.64x); re-sliced mixes are a clean negative (miss every bar, hhcomp blows to 1.23–1.27x); binding constraint re-named to the earner×senior joint (earner_senior 0.019 vs 0.042 real) |
| 45 | [M1/M2 direction recalibration for earned](experiments/exp45_m1m2_direction.md) | Calibration | Staged — [F4] harness reproduction on the current tree + direction-residual decomposition (bucket×97/non-97) + secant fit of direction-balance boosts in the M1/M2 regime; bars: earned ≥0.90x and finding L1 ≤0.030; falsification named (rails/insufficient instrument → reject M1/M2) |
| 46 | Shelter-deduction audit | Calibration | Staged — design only, no chronicle/script yet; exp35 follow-up: v1-vs-v2 discriminator ablation on 9 raw features to test whether the shelter leak is a feature-recipe artifact; if raw AUC stays high, audit the shelter marginal/cap/shelter\|income joint |
| 47 | [Household-type review burden](experiments/exp47_household_type_burden.md) | Fairness | Informative (no gate) — dollar rankers are dollar-efficient (within-type marginal check passes in every type) but risk-regressive: elderly/disabled under-reviewed relative to error risk (rev/base-error ratios 0.22–0.35), childless adults over-reviewed (1.41–1.45), both states, all budgets; PA reproduction shifted $6,074→$5,483 by the exp44 household-mix adoption |

Recommended next run: earner×senior joint experiment (exp44 named it the binding constraint for
medical: earner_senior 0.019 vs 0.042 real, no_earner_nonsenior 0.342 vs 0.273) — exp44's size-mix
fix is done (partially held) and exp28's re-sliced mixes are retired. Then: exp45's M1/M2 direction
recalibration for earned (staged); exp46's shelter-deduction audit (staged); re-derive the
classifier-training recipe on the adopted defaults; run exp30's pilot on
the Mac Studio for the first LM-gate data point, then the human label audit. Standing
rules learned: joint matrix+effectiveness re-measurement under mechanisms-ON (never the
matrix alone — exp32's 2x2); re-fit dollar constants on any future draw/matrix/sampler
change (procedure in exp31).

Second-coordinator findings to fold in: prototype state-conditioned error-rate offsets
(exp33); add a `--year` knob with per-FY finding/direction/dollar slices, nature/cause
pinned to the FY2024 convention (exp34); audit shelter-deduction modeling — the biggest
discriminator leak (exp35; staged as exp46); replace the household sampler's flat conditionals with
empirical tables starting with P(earner|hhsize) (exp39); run a transformer-class transfer
probe before locking the LM recipe (exp37); record the training target as the
microdata-implied substance rate, not the published series (exp40); use exp41's
22-question set as the LM-gate regression golden set and fence QA generation with an
explicit scope manifest (exp41/exp42 follow-ups: medical medexp-conditioned draw,
depcare kid×earner strata).

## PA experiment index

Pennsylvania POC track (STATE=42, n=3,268 FY2020–2024). Files named `paN_*`;
kept separate from the main index per project convention.

| # | Experiment | Gate | Verdict |
|---|---|---|---|
| 8c | [PA engine deviations](experiments/exp8c_pa_deviations.md) | Rules recovery | Clean PA engine (informative negative) — every param = statute every FY; statutory formula predicts RAWBEN exactly 99.7–100%. Fixed two statute-table errors (FY2021 min $19, FY2022 std ded 177/177/177/184/215/246) |
| PA1 | [PA-conditioned generator](experiments/pa1_pa_generator.md) | Calibration | Held — finding L1 0.028 (target ≤0.03), element L1 0.065, cause L1 0.050; national output byte-identical; key fix was fitting cause ratios on non-97 variances (national 97-cause blanking distorted the draw) |
| PA2 | [PA-filtered transfer](experiments/pa2_pa_transfer.md) | Transfer | **PASS (conditional)** — PA synth predicts real PA errors: element acc 0.567 vs 0.453 baseline, macroF1 0.208 vs 0.062; PA-conditioning beats national on element (+0.03–0.09); unweighted GBM beats class-balanced on PA's shelter-heavy mix; finding needs calibrated ranking (binary AUC 0.645), not hard classification |
| PA3 | [PA error anatomy](experiments/pa3_pa_anatomy.md) | Calibration | Held — shelter deduction errors ~2x national (omitted 2.30x, included 1.95x), medical-included 1.93x, newly-employed wages 1.51x ($258 median); computation errors 0.12x national corroborate the clean-engine finding; PA codes cause "Other" 3.5x national |
| PA4 | [Prioritization simulation](experiments/pa4_prioritization.md) | Transfer | **Conditional PASS** — calibrated ranking beats random review but only at triage margins: precision@10% 0.50 (lift 1.17x), precision@20% 0.48 (1.14x); reviewing the riskiest half catches 67% of errors with half the reviews (57 vs 43 errors per 100). Caught errors skew small-dollar (median $12 vs $25), so count gains overstate dollar gains |
| PA5 | [Dollar-impact ranking](experiments/pa5_dollar_ranking.md) | Transfer | **Conditional PASS (weak)** — two-part P(error)×E[dollars] wins: lift 1.40x/1.58x/1.28x at top-10/20/30%; top-20% recovers $6,074 vs $3,851 random ($75/hr vs $47/hr, ~$28/hr marginal). Surprise: P(error)-only is *worse* than random at top-10% (0.43x) — it chases small-dollar shelter errors while dollars sit in earned/unearned. Synth captures ~1/3 of the real-trained headroom (5.00x/3.15x/2.46x) |
| PA7 | [Feature sanity audit](experiments/pa7_feature_audit.md) | Transfer | **PASS** — top features are shelter deduction, earned income, unearned income: exactly PA3's deduction/income patterns, nothing suspicious. One leakage feature found (issued benefit = the caseworker's decision); removing it barely moves the numbers (acc 0.559 vs 0.567, macroF1 0.200 vs 0.208). The model learned PA's real process-layer patterns, not a cheat |
| PA6 | [Temporal stability](experiments/pa6_temporal.md) | Transfer | **PASS** — signal holds year-to-year: refit-on-2020–22 scores 0.506/0.214 on held-out 2023–24 vs 0.522/0.186 same-period (1.6pp decay, macroF1 up); buying test years' marginals gains only ~2.7pp. No annual refitting needed for the element model; the P(error) prior needs per-era attention, plus an unearned-bucket watch |
| PA8 | [Pristine transfer rerun](experiments/pa8_pristine_rerun.md) | Transfer | **PASS** — PA2's conclusions survive pristine fitting (offsets refit excluding all 817 holdout rows): pristine PA 0.556/0.188 vs national 0.530/0.170; gap narrows (+0.026 acc, was +0.037) but holds. Contamination premium was real but small (~0.011 acc). Finding AUC 0.691 (vs 0.645) — not inflated |

PA track complete: 8c + PA1–PA8 all landed. Verdict summary: validated signal — PA-conditioned synthetic predicts real PA errors, beats national (+0.026–0.09 acc), and the ranking produces real review-dollar value ($75/hr vs $47/hr). The production ranker should train the two-part P(error)×E[dollars] structure on real PA QC features; see PA verdict below.

**PA verdict (POC complete, 2026-09-29).** Does the POC have validated signal? Yes — with conditions. Decision point 1 (PA2, PA8): PA-conditioned synthetic predicts real PA error elements (pristine: acc 0.556 vs 0.453 baseline, macroF1 0.188 vs 0.062; PA beats national by +0.026 acc — the gap survives holdout-clean refitting, so it is real). Decision point 2 (PA4, PA5): the ranking is a triage tool, not a hit list. Precision@10% 0.50 (lift 1.17x); reviewing the riskiest half catches 67% of errors with half the reviews (57 vs 43 errors per 100). CIO-ready dollars: two-part P(error)×E[dollars] ranking at top-20% recovers $6,074 vs $3,851 random — $75/hr vs $47/hr review time (~$28/hr marginal, ~$2.2k extra per 163 reviews). Over/under split $4,239/$1,835 (70/30): savings-only $52/hr vs $47/hr. Caveats to state honestly: ranking by P(error) alone is *worse* than random at top-10% (0.43x) — dollars live in earned/unearned, not the frequent shelter errors; synth captures only ~1/3 of the real-trained headroom (5.00x/3.15x/2.46x lift); caught errors skew small-dollar; the model is clean of material leakage (one post-decision feature found, removal changes nothing). **Recommended next step:** train the two-part ranker structure on real PA QC features (the (b-r) headroom recipe — a defensible production pilot); the synthetic ranker serves as the cold-start. Keep the 8-feature clean set, threshold-tune P(error) on a recent real slice, and watch the unearned bucket.


## NY experiment index

New York POC track (STATE=36, n=3,257 FY2020–2024). Files named `nyN_*`; mirrors the PA chain.

| # | Experiment | Gate | Verdict |
|---|---|---|---|
| 8c | [NY engine deviations](experiments/ny8c_ny_engine_cleanliness.md) | Rules recovery | Clean NY engine — statutory formula predicts RAWBEN exactly 94.3–98.3% (fleet 97.4–98.5%; 97.6–98.3% artifact-excluded); zero uncapped-shelter cases all 5 FYs. Found two confounds: FY2020–21 RAWNET==RAWGROSS recording artifact (field stale, benefit correct) and 2 legitimate FY2021 prorated rows |
| NY1 | [NY-conditioned generator](experiments/ny1_ny_generator.md) | Calibration | Held — finding L1 0.020, element L1 0.044, cause L1 0.074; case-error rate exact (0.3651 vs 0.3655); national output byte-identical. NY empiricals: error rate lower than national (0.3655 vs 0.3878), 97-share 1.16–2.62x national, dollar tail fatter (p90 $201 vs $183). Honest residual: dollar p50 shape (97 vs non-97 sizes) and +0.027 p(over|err) |
| NY2 | [NY-filtered transfer](experiments/ny2_ny_transfer.md) | Transfer | **MIXED** — element: NY synth 0.435 acc / 0.168 macroF1 vs majority 0.274/0.033 (real signal) but national-trained 0.468/0.151 wins on element (NY's signature sits in the rare medical/sua/hhcomp tail the generator can't place). Finding: NY wins binary AUC 6/6 across seeds (0.657 vs 0.611 at s7) — NY-conditioning transfers on the finding/dollar tasks, not fine-grained element. Unweighted GBM wins everywhere |
| NY3 | [NY error anatomy](experiments/ny3_ny_anatomy.md) | Calibration | Held — NY's process failure is *timing*: nature 97 at 62% (1.56x national), vs PA's deduction-construction story. Medical 1.79x, SUA 1.51x, hhcomp 1.32x above national; shelter 0.83x, earned 0.90x below. Computation errors 0.20x / arithmetic 0.54x corroborate the clean engine. Cause 15 (failed follow-up) 2.47x, 22 (budgeted wrong amount) 2.54x — NY codes specific agency causes honestly (no cause-99 distortion) |
| NY4 | [Prioritization simulation](experiments/ny4_prioritization.md) | Transfer | **Conditional PASS** — calibrated AUC 0.669; precision@10% 0.51 (lift 1.40x), precision@20% 0.49 (1.34x); riskiest half catches 66.2% of errors with half the reviews (49 vs 37 errors per 100). Same flat-topped shape as PA: value is deprioritizing the safe half. No small-dollar skew (caught median $26 vs $30 holdout-wide) |
| NY5 | [Dollar-impact ranking](experiments/ny5_dollar_ranking.md) | Transfer | **Conditional PASS** — winner is **(c) direct expected-dollar** (diverges from PA's two-part): top-20% recovers $6,958 vs $4,574 random (1.52x; $85/hr vs $56/hr, ~$29/hr marginal), captures 30.4% of holdout error dollars; over/under $4,751/$2,207 (68/32), savings-only $58/hr vs $56/hr. PA5's surprise confirms: P(error)-only is *worse* than random at top-10% (0.74x) — it chases small-dollar timing errors while dollars sit in earned/sua. Synth captures ~half the real-trained headroom (1.52x vs 2.72x) |
| NY7 | [Feature sanity audit](experiments/ny7_feature_audit.md) | Transfer | **PASS** — top features earned/shelter/unearned plus elevated medical and senior_disabled — exactly NY3's timing/deduction patterns, nothing suspicious. One leakage feature (issued benefit); removing it moves acc +0.017 / macroF1 −0.021 (immaterial). Clean 8-feature set adopted |
| NY6 | [Temporal stability](experiments/ny6_temporal.md) | Transfer | **PASS** — refit-on-2020–22 beats pooled fit on held-out 2023–24 (element acc +0.089, macroF1 up; both cross-period swings are mix/prior stories). No annual refitting needed. Watch medical (only real F1 decay, 0.237→0.105) and hhcomp (sparsity guard drops its 1.585x adjustment in pre-2023 refits); 97-cause blanking drifts per-FY (mild cause-task caveat) |
| NY8 | [Pristine transfer rerun](experiments/ny8_ny_pristine_rerun.md) | Transfer | **PASS** — NY2's verdict stands under pristine fitting (2,442 rows, holdout excluded): element gap −0.007/−0.000 (no NY advantage, unchanged); finding AUC 0.626 vs national 0.611 (edge +0.016). Contamination premium ~0 on element, ~+0.02 on finding AUC — small |

NY track complete: 8c + NY1–NY8 all landed. Verdict summary: validated signal with one NY-specific qualification — NY-conditioned synthetic transfers on finding/ranking (AUC 0.657 vs 0.611, pristine 0.626) and dollars ($85/hr vs $56/hr), but does not beat national on element buckets (NY's signature lives in the rare medical/SUA tail). Microdata-implied NY payment error rate 8.54% vs 8.58% national (rank 35/53).

**NY verdict (POC complete, 2026-09-29).** Decision point 1 (NY2, NY8): NY-conditioned synthetic carries real signal above baseline — element acc 0.435 vs 0.274 majority (NY7-corrected 0.452), finding AUC 0.657 vs 0.611 national, and the finding edge survives pristine refitting (0.626 vs 0.611). But NY-conditioning does not beat the nationally trained model on element buckets (0.468 vs 0.435): NY's most distinctive errors are rare-tail medical/SUA, which the generator's mechanics cannot yet place on features — the honest qualification that separates NY from PA. Decision point 2 (NY4, NY5): the ranking is a triage tool. Calibrated P(error) AUC 0.669; precision@10% 0.51 (1.40x lift); riskiest half catches 66.2% of errors with half the reviews. CIO-ready dollars: direct expected-dollar ranking at top-20% recovers $6,958 vs $4,574 random — $85/hr vs $56/hr review time (~$29/hr marginal, ~$2.4k extra per 163 reviews, 30.4% of error dollars). Over/under $4,751/$2,207 (68/32): savings-only $58/hr vs $56/hr. Caveats to state honestly: P(error)-alone is *worse* than random at top-10% (0.74x) — dollars live in earned/sua income errors, not the frequent timing errors; the winner is the direct dollar model, not PA's two-part structure; synth captures ~half the real-trained headroom (1.52x vs 2.72x). **Recommended next step:** train the direct expected-dollar structure on real NY QC features (the (c-r) headroom recipe); the synthetic ranker serves as the cold-start. Keep the 8-feature clean set, re-tune P(error) on a recent real slice, watch the medical bucket.

## Data

Real QC public-use files (FY2020–2024, `~/workspace/snap-qc-data/`) are
**held-out validation only** — never training. They are not committed here.
