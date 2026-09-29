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

Recommended next run: richer shared features for exp2 (close the 0.422→0.614
gap), in parallel with exp1's over-issuance calibration fix.

## Data

Real QC public-use files (FY2020–2024, `~/workspace/snap-qc-data/`) are
**held-out validation only** — never training. They are not committed here.
