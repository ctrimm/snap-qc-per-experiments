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
| 7 | [Per-bucket persistence: hybrid single-draw-and-drop](experiments/exp7_per_bucket_persistence.md) | Calibration | Held — hhcomp 2.86x→1.27x, arithmetic 3.47x→1.42x; finding L1 0.010→0.044 (within-direction 57 residual) |

Recommended next run: exp 4 transfer re-run on the persistent generator —
does the faithful element mix lift element accuracy past 0.493? Then
per-nature importance weights for the 57 residual and senior-conditioned
bucket mixes for medical.

## Data

Real QC public-use files (FY2020–2024, `~/workspace/snap-qc-data/`) are
**held-out validation only** — never training. They are not committed here.
