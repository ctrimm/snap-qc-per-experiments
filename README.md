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
| 5 | [Calibration v3: omission-coherence fix](experiments/exp5_omission_coherence.md) | Calibration | Partially held — under moved 9.4%→10.9%; problem is *who* gets errors |
| 6 | [Calibration v4: eligibility-screen injection](experiments/exp6_eligibility_screen.md) | Calibration | Held decisively — finding mix L1 = 0.009; realized error 0.396 vs 0.397 |
| 6b | [Calibration methodology: attrition-corrected injection](experiments/exp6_calibration_methodology.md) | Calibration | Load-bearing — phase-1 coins, stochastic-97 coins, two-level effectiveness |
| 4 | [Transfer v2: richer shared features](experiments/exp4_transfer_v2.md) | Transfer | Held, with a surprise — binary macroF1 0.616 (prior fixed); element v1 0.493 beats v2 0.451 (derived features embed generator assumptions) |
| 4b | [Transfer v3: the persistent generator](experiments/exp4_transfer_v3.md) | Transfer | Did not hold — element acc fell 0.493→0.442 on the faithful mix (class starvation); binary improved 0.616→0.639. Lesson: calibration fidelity ≠ transfer utility; rebalance classes when training |
| 7 | [Per-bucket persistence: hybrid single-draw-and-drop](experiments/exp7_per_bucket_persistence.md) | Calibration | Held — hhcomp 2.86x→1.27x, arithmetic 3.47x→1.42x; finding L1 0.010→0.044 (within-direction 57 residual) |
| 8a | [RAWBEN validation for rules recovery](experiments/exp8a_rawben_validation.md) | Rules recovery | Held with filters — AMTERR == |FSBEN−RAWBEN| in 85% exact / 92% within $1; RAWBEN is the issued benefit; drop recoupment-type rows for fitting |
| 9 | [Class-balanced element transfer](experiments/exp9_class_balanced_transfer.md) | Transfer | Did not hold — retry-loop + balanced (0.458/0.274) beats persistent + balanced (0.443/0.252); mechanism is distinct example counts, not priors. Doctrine: train classifiers on retry-loop + balancing, keep persistent generator for the data product |
| 10 | [Statutory parameter refresh (research)](experiments/exp10_statutory_parameter_refresh.md) | Calibration | Partially falsified — benefit math matches FY2024 statute exactly; income-eligibility limits ~6% too high (later-year table), a frame-contamination blindspot. Apply step staged |
| 15 | [Cause-mix calibration audit](experiments/exp15_cause_audit.md) | Calibration | Held — conditional cause mix L1 = 0.014 (agency/client/other track at ~1.0x); only gap is 12.5% blank causes on nature 97, a labeling rule not yet implemented |
| 16 | [Dollar-error distribution re-check](experiments/exp16_dollar_error.md) | Calibration | Did not hold — dollar marginal drifted: p50 $31 real vs $74 synth, low tail starved (69% ≤ $56 real vs 37% synth), over/under asymmetry inverted, extreme over-tail thin. Corruption mechanics too coarse |
| 17 | [QC-variance eval set design](experiments/exp17_qc_variance_eval_design.md) | LM gate (prep) | Design delivered — 1,200 items, 6 tasks, stratified off the natural prior, composite scoring vs dummy/base/ceiling; 7 open questions for reviewer judgment |
| 11 | [Senior-conditioned bucket mixes](experiments/exp11_senior_bucket_mix.md) | Calibration | Partially held — medical 0.11x→0.67x via 4-stratum mixes + removing double-counted zero-base suppression; hhcomp regressed 1.16x→1.91x |
| 12 | [Kid-conditioned depcare](experiments/exp12_kid_depcare.md) | Calibration | Held — depcare 0.03x→0.56x via n_kids + kid-gating; all 8 elements now 0.56x–1.56x |
| 13 | [Per-nature weights for 57](experiments/exp13_nature57_weights.md) | Calibration | Held — nature 57 0.50x→1.04x via 1/m importance weights measured in persistent flow (0.8 damping) |
| 14 | [Bucket materialization correction](experiments/exp14_materialization_correction.md) | Calibration | Did not hold — re-measuring eff_b under stratum mixes improved finding L1 (0.042→0.036) but hhcomp/arithmetic stuck at ~1.5x; scalar eff_b insufficient |
| 8b | [Parameter fitting for rules recovery](experiments/exp8b_parameter_fitting.md) | Rules recovery | Held weakly — national effective params match FY2024 statute exactly (30% rate 0.2995, $672 cap point mass); no misconfiguration signal in 22-state scan. Individual-engine fingerprinting blocked: no vendor IDs, error rows carry reviewer values |
| 8c | [PA engine deviations](experiments/exp8c_pa_deviations.md) | Rules recovery | Clean PA engine (informative negative) — every param = statute every FY; statutory formula predicts RAWBEN exactly 99.7–100%. Fixed two statute-table errors (FY2021 min $19, FY2022 std ded 177/177/177/184/215/246) |
| 18 | [Dollar-error mechanisms](experiments/exp18_dollar_mechanisms.md) | Calibration | Partially held — small-error mode (nature-97 conditioning) + whole-unit ineligibility (p=0.0125) verified; asymmetry mostly fixed (still inverted at p90); finding mix regressed pending recalibration |
| 19 | [Retry-loop + oversampling transfer](experiments/exp19_retry_oversample_transfer.md) | Transfer | Did not hold — exp9's count mechanism falsified: gap survives at count parity (0.287 vs 0.304); second-variance structure the live candidate |
| 20 | [Per-(bucket,stratum) materialization matrix](experiments/exp20_materialization_matrix.md) | Calibration | Partially held — mechanism works (keep rates invariant to draw weights) but not shippable; exposed ZERO_BASE_WEIGHT double-count on the draw side |
| 21 | [Zero-base-weight audit](experiments/exp21_zerobase_audit.md) | Calibration | Largely held — removing the double-count: finding L1 0.036→0.024, hhcomp 1.59→1.11x, arithmetic 1.51→1.10x; stale exp20 matrix does not transfer (re-measure on corrected draw) |
| 22 | [Second-variance structure transfer](experiments/exp22_second_variance_transfer.md) | Transfer | Held — residual edge is household selection (89.3% of gap), not multi-variance structure; on the post-exp24 generator the retry edge no longer exists |
| 23 | [Merge dollar mechanisms + recalibrate](experiments/exp23_merge_recalibrate.md) | Calibration | Partially held — dollar marginal fixed (share ≤$56: 0.36→0.67 vs 0.70 real; p90 inversion fixed) but finding mix not recovered: whole-unit overs double-counted (already coded as earned income); phase-1 coin is direction-blind |
| 24 | [Adopt draw fix + re-baseline](experiments/exp24_adopt_rebaseline.md) | Calibration + Transfer | Partially held — new defaults: finding L1 0.036→0.025 (0.019 retry); macroF1 −0.007…−0.031 — the calibration win and macroF1 loss are the same event (fewer distinct rare examples) |
| 25 | [Training recipe re-derivation](experiments/exp25_training_recipe.md) | Transfer | Did not hold — faithful persistent + balanced remains the best recipe; retry loop has no remaining role. Recipe question closed |

Recommended next run: combine exp23's dollar mechanisms with exp24's new defaults —
recode the whole-unit mechanism as earned-income zeroing (matching the file's coding),
subtract whole-unit mass from the empirical direction targets, and make the phase-1 coin
direction-aware; then re-run the golden calibration suite. Target the new residuals:
earned ~0.8x audit, medical/depcare deflation (0.53x/0.41x), nature-57 inflation (1.16x),
and exp21's household-sampler base-positivity gaps. Pilot exp17's QC-variance eval once
calibration settles — the first LM-gate data point.

## Data

Real QC public-use files (FY2020–2024, `~/workspace/snap-qc-data/`) are
**held-out validation only** — never training. They are not committed here.
