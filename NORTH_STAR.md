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

## Where this stands (October 27, 2026)

*The goal above is the September 28 statement, kept as written. This section records how the project has moved against it.*

**The copilot thesis held, as research:**
- **The calibration and transfer gates both held:** models trained only on synthetic cases predict real QC labels above baseline.
- **The language model:** a 4-billion-parameter model fine-tuned on synthetic cases passed its pre-registered test on fresh real cases.
- **Policy questions:** a larger open model with policy lookup reached about 90% on the CalFresh quiz.

**The working product is a different one.**
- **What it is:** case-ranking models trained on the real QC records, one per jurisdiction, packaged for states to pilot. They're trained on real QC data, a departure from the "real microdata never enters training" non-goal above. That non-goal applied to the language model; the language model still follows it.
- **The case for it:** this tool is the one with a near-term case, through the H.R. 1 cost-share rules from FY2028.

**What changed the numbers:**
- **The leak (October 26):** an independent comparison (giannella/snap_qc) exposed a leak in the rankers' inputs.
- **The rebuild:** the rankers were rebuilt without it, then retrained on the official error definition.
- **What's still open:** the inputs remain the reviewer's corrected values for error cases. Rebuilding them as pre-review values is under test (exp113).

**What still governs the work:**
- **Pre-registration:** every result is pre-registered and gated.
- **Evaluation-only data:** the CalFresh quiz is never trained on, and real microdata never enters the repo.
