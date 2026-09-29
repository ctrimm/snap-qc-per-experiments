# North Star

**A small, domain-specific language model that works as a QC copilot for SNAP
payment accuracy** — reading a case record the way a QC reviewer does and
predicting the error finding (correct / overissuance / underissuance), the
variance taxonomy (element, nature, cause), and the dollar impact.

## Why synthetic-first

The real QC public-use files are a *validation* resource, not a training one:
~45k cases/year is thin for LM pretraining, and the cases carry no
natural-language reasoning traces. The bet is that **synthetic QC-style cases
with deterministic ground truth** (a benefit calculator standing in for the QC
Minimodel) can teach a small model the mechanics of SNAP errors — how income,
deductions, household composition, and timing move benefits — and that those
mechanics transfer to real cases.

## Validation gates

Every experiment in this repo must move one of these gates or be recorded as
not moving it:

1. **Calibration gate** — the synthetic marginals (finding mix, element/nature/
   cause mix, dollar-error distribution) stay near the real QC distributions.
   If the generator's priors drift, anything trained on it inherits the drift.
2. **Transfer gate** — models trained *only* on synthetic cases predict *real*
   QC labels above baseline. This is the core thesis test: signal must cross
   the synthetic→real gap.
3. **LM eval gate** (future) — the pretrained small LM beats its base on a
   QC-variance eval and the CalFresh MCQ benchmark.

## Non-goals (for now)

- No GPU training runs; no model weights in this repo.
- Real QC microdata never enters training — held-out validation only.
- The generator is a harness, not the Minimodel: parameters are approximations,
  documented as such in `src/synth/params.py`.
