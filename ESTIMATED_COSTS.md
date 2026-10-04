# Estimated Training Costs — SNAP QC Domain Model

*2026-09-29. Pricing basis: H100 ~$1.50–$3.00/hr on marketplace/specialist clouds
(RunPod, Nebius); hyperscalers (AWS/GCP/Azure) charge substantially more.
Spot/preemptible instances run 50–80% cheaper and suit checkpointed training.
A100 80GB from ~$0.68/hr. Prices move — re-check before budgeting.*

## From-scratch pretraining (for reference)

Training compute scales as ≈ 6 × parameters × tokens. Assumes H100 at $2.50/hr,
~45% hardware utilization. Single clean run; multiply by 3–5x for the real
project (failed runs, ablations, evals, data prep).

| Model | Tokens | H100-hours | Single-run cost |
|---|---|---|---|
| 1B | 100B (data-efficient recipe) | ~375 | ~$1,000 |
| 1B | 300B | ~1,100 | ~$3,000 |
| 1B | 1T (Llama-style overtraining) | ~3,750 | ~$9,000 |
| 4B | 500B | ~7,500 | ~$19,000 |
| 4B | 1T | ~15,000 | ~$38,000 |
| 4B | 2T | ~30,000 | ~$75,000 |

Field data points: a 1B model was recently trained from scratch for ~$1,500
on 40B curated tokens (16 GPUs, under 2 days), scoring competitively with
2–7B models on reasoning benchmarks. Practitioners peg a 1B run at $3k–$10k
all-in, with total project cost running 5–10x theoretical compute.

**Verdict: not the recommended path** (see below).

## Recommended path: open-weight base + continued pretraining

> **This is the approach to take.** Start from a current 1.5–4B open-weight
> base model and continue pretraining it on SNAP-domain data, then
> supervised fine-tune (SFT) on QC task formats.

**Why it wins:**

- **General reasoning comes free.** The base already handles language,
  math, and instruction-following from its trillion-token pretraining.
  From-scratch would re-buy all of that at full price just to re-learn it.
- **SNAP specialization is the small, cheap part.** What the base lacks is
  SNAP mechanics — benefit formulas, deduction schedules, variance
  taxonomy, error patterns. That is exactly what continued pretraining on
  the policy corpus (state-policy-docs, Handbook 310, FNS memos) plus the
  synthetic QC cases teaches, and it takes tens of billions of tokens,
  not trillions.
- **10–50x cheaper.** Continued pretraining a 3B base on ~30B domain
  tokens is a few hundred H100-hours — **under $1,000** for the run.
  The SFT stage on QC task formats is a few hundred dollars more.
- **Lower risk.** If the domain mix is wrong, you re-run a $1k
  continued-pretraining run, not a $40k from-scratch run. Iteration is
  the whole game at this stage.

**Base selection (decide at training time — the field moves fast):**
pick a current 1.5–4B open-weight model with strong reasoning scores,
a permissive license for the intended use, and a tokenizer that handles
the document formats in the corpus. Re-evaluate against whatever is
current when the data pipeline is ready; do not lock in a base now.

**Data legs for continued pretraining:**

1. SNAP policy corpus — state-policy-docs, Handbook 310, FNS QCPM memos
   and guidance (general language + domain knowledge).
2. Synthetic QC-style cases with deterministic ground-truth labels,
   calibrated to real QC variance distributions (the snap-qc-per-experiments
   generator output — mechanics of how income, deductions, household
   composition, and timing move benefits).
3. Real QC public-use files (FY2020–2024; FY2025 pending) as **held-out validation only**
   — never in training.

**Eval gates before spending:** CalFresh MCQ 500-question benchmark
(base should replicate ~85%+ control for setup validity) and the
QC-variance eval designed in `experiments/exp17_qc_variance_eval_design.md`.

## Hardware split

| Stage | Where | Why |
|---|---|---|
| Continued pretraining (~30B tokens) | Rented H100s (spot) | Needs datacenter throughput; ~$500–$1k |
| SFT / LoRA, ablations | Mac Studio M3 Ultra | Fits comfortably; iteration speed |
| Inference, eval harnesses | Mac Studio / LM Studio | Already the local setup |
| From-scratch pretraining | Nowhere in this plan | Not needed |

## What the six-state panel changes (2026-10-04)

The PA/NY/TX/SD/ID/UT tracks (`docs/CROSS_STATE_SYNTHESIS.md`) established three
things with cost implications. Net effect: the ~$3k–$7k envelope **stands** — the
lessons move work between budget lines (more CPU eval, same GPU spend); they add
no GPU line.

1. **No universal ranking rule — but re-deriving it is CPU-cheap.** The winning
   ranker differs by state (two-part, direct-dollar, or P-alone, depending on
   the state's dollar tail), so production needs a per-state calibration run.
   That run is gradient-boosted trees on synthetic cases plus held-out
   validation: minutes on CPU, ~$0 GPU spend. The cost is engineering time, not
   compute. Budget one calibration pass per deployment state; no new training
   runs.

2. **State-conditioning belongs in the data mix, not in separate pretraining
   runs.** State-conditioned synthetic beats national pools on transfer, but the
   LM doesn't need six pretraining runs — it needs state identifiers in the
   continued-pretraining mix (the generator already emits them). If deployment
   wants stronger per-state specialization, per-state LoRA adapters on the Mac
   Studio are the shape: cheap, swappable, no datacenter bill.

3. **The fairness gate is now a per-state eval requirement, not a research
   extra.** exp47–49: the household-type burden analysis must run for each
   deployment state's winning ranker (risk-regressivity is a property of
   dollar-maximizing rankers specifically — UT showed it at 0.155, ID's P-alone
   winner largely avoids it). Compute-cheap (same CPU harness); required before
   pilot sign-off.

## Budget envelope

| Item | Estimate |
|---|---|
| Continued pretraining run (3B, ~30B tokens) | $500–$1,000 |
| SFT + eval runs | $200–$500 |
| Experiments, failed runs, re-runs (3–5x) | $2,000–$5,000 |
| **Total project** | **~$3k–$7k** |

vs. $15k–$150k+ for an equivalent from-scratch program. The open-weight
base is doing the heavy lifting; the budget buys SNAP specialization.
