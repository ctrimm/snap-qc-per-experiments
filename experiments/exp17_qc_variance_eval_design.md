# Experiment 17 — QC-variance eval set design (LM-gate prep, no training)
**Date:** 2026-09-29 · **Code:** (design document; no code yet — pilot build is a
follow-up)

## Hypothesis
North star gate: **LM eval gate** (gate 3). We hypothesize that this eval
design **discriminates QC competence** — i.e., a model that has actually
learned SNAP payment-error mechanics scores materially higher than a model
that hasn't, and a weak-but-better-than-base pretrained LM scores between the
two. If the eval can't separate (a) the un-tuned base LM, (b) the synthetic-
pretrained small LM, and (c) a strong reference, it cannot serve as the gate,
no matter how faithfully the generator calibrates.

## Method — the eval design

### 1. Eval purpose: what exactly it measures
The eval asks a language model to act like a QC reviewer: it reads one case
record (presented as structured text) and predicts the review outcome. It
measures whether the model connects case facts to payment-error mechanics —
e.g., that unreported wages move the benefit down, that a missed medical
deduction moves it up — rather than pattern-matching surface text. Six tasks,
three difficulty layers:

- **Layer 1 (detection):** Is there an error? (binary error / no-error)
- **Layer 2 (direction):** If there's an error, which way? (finding: correct /
  overissuance / underissuance)
- **Layer 3 (taxonomy + dollars):** What was wrong (element bucket), how it was
  wrong (nature code), who is responsible (cause bucket), and the dollar impact.

A model can score partial credit across layers: getting detection right but
element wrong still says something real about competence.

### 2. Input format: what the model sees per item (and the anti-leakage rules)
Each item is one real QC case rendered as structured text. The model sees
**two views of the same case**, mirroring what a real QC reviewer works with:

- **Agency view** — what the state agency budgeted: household size and
  composition, income sources and amounts as reported, deductions claimed
  (shelter, SUA, medical, dependent care, child support), allotment issued
  (FSBEN), state, sample month.
- **Verification view** — what the QC reviewer verified through
  documentation and collateral contacts: corrected income amounts, verified
  household members, verified shelter costs, etc.

Crucially, the **two views are the input; the label is the *difference* the
model must find**. The model must compare budgeted vs verified and work out
what the variance was.

**Excluded from the input (label leakage if included):**
- `STATUS` (encodes the finding directly), `AMTERR` (the dollar error),
  `ELEMENT1–9`, `NATURE1–9`, `AGENCY1–9` (the variance taxonomy labels),
  `DISCOV1–9`.
- `RAWBEN` (the QC recomputed benefit) — the issued-vs-recomputed gap *is*
  the dollar answer for the dollar task. For the classification tasks
  (finding/element/nature/cause), providing RAWBEN would hand the model the
  direction for free. Therefore: the **classification tasks see no benefit
  amounts at all** (neither FSBEN nor RAWBEN) — the model must infer
  direction from the income/deduction facts. The **dollar task** sees FSBEN
  but not RAWBEN, and must estimate the error magnitude.

Input rendering is deterministic: a fixed field order, one canonical text
template, dollar amounts as plain integers, codes expanded to their labels
from `src/synth/codebook.py` (e.g. "363 Shelter deduction") so the model is
tested on mechanics, not codebook memorization. Whether the template names
fields in agency jargon or plain English is itself a design choice — jargon
tests domain vocabulary, plain English tests mechanics. Recommendation: pilot
both, keep the one with better base-vs-reference separation.

### 3. Label schema: exact prediction targets and valid values
Each item carries one **primary variance** — defined as the reportable
variance with the largest absolute dollar impact (tie-break: lowest variance
index). Multi-variance cases are common (up to 9 recorded); the primary keeps
scoring unambiguous. A separate "multi-variance count" task can be added
later.

| Task | Target | Valid values |
|---|---|---|
| T1 detection | error / no-error | `error`, `correct` (a case is `error` if it carries ≥1 reportable variance) |
| T2 finding | review outcome | `correct`, `overissuance`, `underissuance` |
| T3 element | what was wrong | element buckets: `earned`, `unearned`, `depcare`, `shelter`, `sua`, `medical`, `childsupport`, `hhcomp`, `assets`, `arithmetic`, `reporting`, `standard`, `income_total`, `other` |
| T4 nature | how it was wrong | QC nature codes `35, 37, 38, 44, 52, 53, 54, 56, 57, 97, 98, 99` (labels in `codebook.py`) |
| T5 cause | who is responsible | `client`, `agency`, `no_fault`, `other` (from `CAUSE_BUCKETS`) |
| T6 dollar | dollar impact | signed integer dollars (overissuance positive, underissuance negative, 0 = correct); scored with partial credit (see §5) |

T2 is derived from the primary variance's direction, not read from STATUS, so
the label pipeline never touches the leaky field. T3–T5 are defined only for
error cases; correct cases contribute to T1/T2/T6 only. Non-reportable
(tolerance) variances are excluded from labels but remain *in the input
text* — a good reviewer ignores them, and so should the model.

### 4. Sampling plan
**Source: real QC microdata only.** The generator is synthetic-first for
training; the eval must be real to be a credible gate. This eval never
trains anything — it is held-out by construction (north star non-goal:
real QC microdata never enters training).

- **Size: 1,200 items.** Large enough for per-bucket discrimination (see
  stratification), small enough to run cheaply against an LM
  (~1,200 prompts × ~1k tokens is trivial).
- **Fiscal years: FY2021–FY2023 primary, plus a frozen FY2024 slice.** FY2024
  was used for generator calibration and transfer testing; mixing it into
  the eval risks rewarding generator overfit to FY2024 quirks. Drawing the
  bulk from FY2021–2023 (which no experiment has touched) keeps the eval
  honest. A small FY2024 slice (~200 items) is included to check year
  robustness, reported as a separate cut.
- **Stratification (deliberately NOT the natural prior):** exp4 v3 taught us
  that faithful priors starve rare classes of signal — that lesson applies to
  evals too. An eval that mirrors the real 60/24/16 finding mix spends most
  of its items confirming the model can say "correct". Instead:
  - T1/T2: ~400 correct / ~450 overissuance / ~350 underissuance.
  - T3/T4/T5: at least **50 items per element bucket**, oversampling rare
    buckets (`depcare`, `arithmetic`, `reporting`, `assets`, `childsupport`,
    `standard`) up to 50 and downsampling common ones (`earned`, `unearned`,
    `shelter`). Rare buckets are where generator mechanics are weakest
    (exp4 v3: sua/medical/depcare F1s 0.090/0.062/0.000) — the eval must be
    able to see them.
  - Within-bucket: stratify by nature code where counts allow (nature 97
    timing errors are a known hard slice — keep a dedicated 97 cut).
  - States: cap any single state's share (~10%) so a model can't ride
    one state's caseload.
- **Sampling mechanics:** one frozen sample, seed recorded, item IDs stored
  in the repo. Never re-sample on the fly — a moving eval can't be a gate.

### 5. Scoring
Report per-task metrics (definitions in `terms.md`: accuracy = fraction
exactly right; macroF1 = F1 averaged over classes, punishing ignored rare
classes; AUC = probability a random positive outranks a random negative):

| Task | Primary metric | Secondary | Reference points |
|---|---|---|---|
| T1 detection | macroF1 | acc, AUC | GBM synth→real 0.608/0.606/0.656; dummy ≈ 0.47 |
| T2 finding | macroF1 | accuracy | GBM synth→real 0.462/0.387; real→real 0.871/0.832 |
| T3 element | macroF1 | accuracy + per-bucket F1 | GBM synth→real 0.442/**0.214**; real→real 0.619/0.422; per-bucket F1s (earned 0.616 … depcare 0.000) |
| T4 nature | macroF1 | accuracy | no GBM baseline yet — dummy (most-frequent nature) floor |
| T5 cause | macroF1 | accuracy | no GBM baseline yet — dummy floor |
| T6 dollar | direction accuracy; MAE within tolerance bands | exact-match rate | bands: exact = full credit, within ±$10 = 0.5, within ±10% = 0.25, else 0; direction-only also reported |

**Aggregation:** no single blended score hides the taxonomy tasks — the
headline is a task table. For the gate decision, use a **composite**:
mean of per-task normalized scores, where each task's score is
(model − dummy) / (real→real ceiling − dummy), clipped to [0,1]. This puts
every task on "fraction of the way from guessing to the best tabular
model" and keeps T3/T4/T5 from being drowned by easy T1.

**Pass/fail bar for the LM gate:** the synthetic-pretrained LM passes iff
**all three** hold vs its own base model (same tokenizer, same prompt):
1. Composite score strictly higher, with a 95% paired-bootstrap confidence
   interval excluding zero (per-item score differences, 10k resamples).
2. Wins on at least 4 of 6 tasks individually (same bootstrap test).
3. T3 element macroF1 clears the GBM synth→real floor of **0.214** — the
   minimum-competency bar: a language model that reads the actual case facts
   should beat a GBM trained on synthetic tabular features at naming the
   error element. (T4/T5 have no GBM floor; their bar is beating base + a
   wide margin over the dummy.)

The CalFresh MCQ benchmark is the *other* half of gate 3 — an LM can pass
this eval and still fail the gate if MCQ doesn't move.

### 6. Train/eval leakage controls
1. **Eval case IDs are a denylist for all future training.** The pretraining
   corpus builder must exclude the 1,200 eval case IDs by (fiscal year, case
   identifier) hash. The exclusion list lives in the repo next to the eval.
2. **No eval-adjacent tuning.** Hyperparameters, prompt templates, and early-
   stopping decisions may not be selected on the eval set. A 200-item
   *development* slice (drawn with the same stratification, disjoint IDs)
   exists for prompt/format iteration; the remaining 1,000 are the locked
   test set, run only for gate decisions.
3. **Synthetic near-duplicates:** the generator doesn't copy real cases, but
   a synthetic case can randomly resemble an eval case. Mitigation: hash the
   eval cases' (bucket, nature, direction, dollar-band) signature; drop
   synthetic training cases with exact signature matches during corpus build.
   Cheap, conservative, documented.
4. **The generator's calibration used FY2024 marginals** — eval items from
   FY2024 are reported as a separate cut (§4) so FY2024-fitted priors can't
   silently inflate the headline.

### 7. Open questions (need Cory's or a reviewer's judgment)
1. **Human label audit.** QC labels are reviewer judgments, not ground
   truth — reviewers make errors too, and nature-97 vs 98 vs 99 boundaries
   are genuinely ambiguous. Proposal: a QC-expert audit of ~150 items
   (stratified to hard slices: nature 97, multi-variance cases, depcare/
   arithmetic) reporting inter-rater agreement (Cohen's kappa) between the
   file label and the auditor. If kappa < ~0.7 on the hard slices, those
   slices get reported separately or dropped from the gate. *Needs Cory:
   do we have access to a QC-knowledgeable reviewer, or is this aspirational?*
2. **Primary-variance rule.** "Largest |dollar| reportable variance" is
   simple, but on multi-variance cases the *first-recorded* variance may be
   what a reviewer would name. Does the choice change T3/T4 materially?
   Pilot should report agreement between the two rules.
3. **Nature-97 slice.** Timing/not-required-to-report cases are the
   philosophically hardest: the "error" is that no error was reportable at
   the time. Keep as a scored task, a diagnostic cut, or exclude? Leaning
   diagnostic cut — it tests a different skill (reporting rules, not
   mechanics).
4. **Dollar tolerance bands.** The ±$10 / ±10% partial-credit scheme is a
   guess. Too lenient and every model passes; too strict and it measures
   arithmetic, not QC judgment. The pilot should report the full error
   distribution so the bands can be set from data.
5. **FY2024 in the eval at all?** The design includes a 200-item FY2024 cut
   for year-robustness, but FY2024 fed calibration — even a separate cut may
   reward generator overfit. Alternative: FY2021–2023 only, 1,200 items.
   *Needs a call before the pilot samples.*
6. **Prompt format.** Zero-shot with the structured template vs few-shot
   with 2–3 worked examples (which then must come from the dev slice, never
   the test set). Few-shot inflates absolute scores but may compress the
   base-vs-pretrained gap — the pilot should run both and keep the format
   with better discrimination, per the hypothesis.
7. **Output parsing.** Free-form JSON vs constrained multiple-choice per
   task. JSON tests generation; MCQ is cheaper to score and harder to game
   with hedging. Recommendation: MCQ for T1–T5 (options = valid values),
   free-form integer for T6.

## Results
N/A — design stage. A pilot build would report: (a) the sampling table
(actual n per finding × element-bucket cell vs plan); (b) dummy/most-
frequent baselines per task; (c) base-LM zero-shot scores per task with the
composite; (d) prompt-format A/B (jargon vs plain-English, zero- vs few-
shot) with the discrimination gap; (e) the primary-variance rule agreement
check; (f) the dollar-error distribution to calibrate tolerance bands.
The pilot's real deliverable is the *discrimination check*: does the
composite separate dummy < base LM < reference? If not, the design — not the
model — is what failed.

## Verdict
Design is complete and internally consistent: six tasks across three
difficulty layers, real-only held-out items with deliberate rare-bucket
oversampling, a leakage-control regime, and a gate bar anchored to the GBM
transfer numbers (element macroF1 ≥ 0.214) and to beating the model's own
base. It is **not yet validated** — the hypothesis ("this eval discriminates
QC competence") is untested until the pilot runs a base LM through it. The
open questions above are genuine blockers for the pilot's sampling and
scoring choices, not polish.

## Next steps
1. (Recommended) Resolve open questions 5 (FY2024 inclusion) and 6/7
   (prompt/output format) — then build the pilot sampler: 1,200-item frozen
   sample + 200-item dev slice from `snap-qc-data/raw/` (beside the repo checkout)
   (FY2021–2023 ± FY2024), with the exclusion denylist.
2. Write the label pipeline (primary-variance rule, leakage field
   exclusion) and the scorer (per-task metrics + composite + paired
   bootstrap).
3. Run dummy baselines + one base LM through the pilot; check the
   discrimination ladder (dummy < base < reference).
4. Line up the human label audit (open question 1) — start recruiting the
   reviewer now; it has the longest lead time.
5. CalFresh MCQ stays the parallel half of gate 3; this eval does not
   replace it.
