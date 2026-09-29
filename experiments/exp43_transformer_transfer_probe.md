# Experiment 43 — transformer transfer probe (STAGED)
**Date:** 2026-09-29 · **Code:** `experiments/exp43_transformer_transfer_probe.py` · **Runbook:** `experiments/exp43_runbook_mac_studio.md`

### Hypothesis
The exp25/exp37 transfer recipe has two components: (1) train on the
faithful persistent pool rather than the retry-loop pool, and (2) rebalance
classes during training. Exp37 showed component (2) — `class_weight=
"balanced"` — is GBM-specific and actively harmful for logistic regression,
while component (1) is weakly model-agnostic for the nonlinear models tried
(GBM, MLP). A transformer is a high-capacity nonlinear model class, so the
persistent-pool half is plausibly portable — but exp37's lesson is that
recipe components tuned on one model class do not port for free.

We hypothesize that for a transformer-class classifier trained with
cross-entropy loss: (a) the persistent pool matches or beats the retry pool
on element macroF1, and (b) inverse-frequency loss reweighting (the
cross-entropy analogue of `class_weight="balanced"`) is neutral-to-helpful
rather than harmful. If both hold, the LM pretraining recipe can inherit
the persistent pool + reweighting with confidence. If either fails, that
component must be re-derived for the LM rather than inherited.

Glossary (see terms.md for the rest): *transformer* — a neural-network
architecture built from self-attention layers; the model class behind modern
language models. *Feature tokenizer* — the scheme used here to feed tabular
data to a transformer: each numeric feature gets its own learned embedding,
plus a special [CLS] token whose final state is used for classification
(the FT-Transformer pattern). *Cross-entropy loss* — the standard training
objective for classification; the loss-reweighting arms multiply each
example's loss by its class's inverse frequency, which is the exact analogue
of `class_weight="balanced"` in a gradient-boosted tree.

### Method (STAGED — not yet run)
Two stages. Stage 1 runs anywhere (CPU sandbox OK); Stage 2 needs torch and
is staged for the Mac Studio (runbook: `exp43_runbook_mac_studio.md`).

**Stage 1 — data (sandbox-runnable).** Regenerate the two training pools
with the exact exp25/exp37 protocol: `python3 -m synth.generate --n 20000
--seed 7 --dist experiments/dist.json --max-attempts 12` from `src/`, once
with persistent buckets (default) and once with `--no-persistent-buckets`
(retry loop). Extract the **clean 8-feature set** — v1 minus
`issued_benefit`, dropped per PA7's post-decision-feature finding (its
removal was immaterial there: acc 0.559 vs 0.567, and a cleaner input set
is more defensible for a recipe decision). Features: hh_size, earned,
unearned, shelter, sua, medical_exp, depcare, senior_disabled.
Standardization stats are fit on the persistent pool's training rows only
and applied to every arm and to the test split, so no arm gets a
preprocessing advantage. Labels: the first variance's element bucket
(8 classes). Train on error rows only (~8k per pool), exactly as exp37.
Eval: the identical real FY2024 QC split as exp19/exp22/exp25/exp37 —
all real rows whose ELEMENT1 bucket is in the 8-bucket set (17,318 rows;
never trained on, never committed). Artifacts: `exp43_pools.npz` +
`exp43_meta.json` (kept out of the repo; regenerated or transferred to the
Mac Studio per the runbook).

**Stage 2 — training (Mac Studio).** A tiny feature-tokenizer transformer:
per-feature linear embeddings into d_model=64, learnable [CLS] token,
2 pre-norm transformer layers (4 heads, FFN 128, dropout 0.1), linear head
on [CLS] — roughly 65k parameters, deliberately small so the probe measures
model *class*, not scale. Four arms × 3 seeds (7, 8, 9; transformers are
seed-sensitive, and exp37's persistent-vs-retry deltas were ±0.002, i.e.
inside any single seed's noise):

| arm | pool | loss weights |
|-----|------|--------------|
| t1 | persistent | uniform |
| t2 | retry-loop | uniform |
| t3 | persistent | inverse-frequency (balanced analogue) |
| t4 | retry-loop | inverse-frequency (balanced analogue) |

AdamW (lr 5e-4, weight decay 1e-4), batch 256, up to 80 epochs with early
stopping on a stratified 10% synthetic validation split (val macroF1,
patience 15) and ReduceLROnPlateau. Metrics: element accuracy and macroF1
on the real split, reported as mean ± range over seeds.

**Decision bar** (printed by the script; what locks or reopens the recipe):
1. **Probe-validity guard.** The best arm's mean macroF1 must beat exp37's
   logreg-unweighted reference (0.244). If not, the probe is underpowered
   or mistuned — draw no conclusions, revisit tuning first.
2. **Pool question.** If mean(t1) ≥ mean(t2) − 0.01 → the persistent-pool
   half of the recipe holds for transformer-class → **lock** the pool
   choice for LM pretraining data.
3. **Reweighting question.** If mean(t3) < mean(t1) − 0.02 → balanced-style
   loss reweighting does **not** port (the logreg failure repeated) → the
   LM recipe uses uniform loss; any imbalance handling comes from
   resampling, tested separately. If mean(t3) ≥ mean(t1) − 0.01 →
   reweighting is safe to port.
4. Both hold → the full recipe ports; either fails → that component is
   re-derived for the LM, not inherited from GBM results.

Reference context (not re-run): exp37 GBM/persistent 0.452/0.279,
logreg/unweighted 0.485/0.244, MLP 0.347/0.244 — the transformer should
land in the nonlinear band (macroF1 ≈ 0.24–0.30) for the guard to pass.

### Results
STAGED. Stage 1 pipeline smoke-tested in the sandbox (`--stage data
--smoke`, 2×500 cases → features → npz round-trip OK). Full pools and
Stage 2 await the Mac Studio per the runbook.

### Verdict
STAGED — no verdict yet. The experiment is designed, scripted, and
runnable; the decision bar above is the pre-registered read of the
outcome.

### Compute assessment (honest)
This does **not** run in the CPU sandbox. The sandbox has no torch, 2 CPU
cores, and 7 GB RAM; 12 transformer trainings (4 arms × 3 seeds) would take
hours there, and transformers need a tuning pass to be interpretable — a
slow, fragile setup that risks an inconclusive answer. The Mac Studio
(M3 Ultra, MPS backend) trains each arm in minutes, and the LM work lives
there anyway. Staging it there is the right call, not a shortcut.

### Next steps
1. Mac Studio: follow `exp43_runbook_mac_studio.md` — install torch, run
   Stage 1 (full pools), `--stage train --smoke-train` to validate the
   torch path, then the full 12-run battery.
2. Read the verdict off the decision bar: lock or re-derive each recipe
   component for the LM pretraining plan.
3. If the reweighting question fails: follow-up probe on resampling
   (oversample rare buckets in the training mix) as the cross-entropy-safe
   alternative — do not assume it ports either.
4. If the probe-validity guard fails: widen the architecture/tuning
   (d_model, layers, LR) before concluding anything about the recipe.
