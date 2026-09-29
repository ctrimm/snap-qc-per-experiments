# PA8 — pristine transfer rerun: testing PA2's fairness caveat

**Date:** 2026-09-29
**Status:** Complete — decision: **PASS**, see Verdict.
**Deliverables (new files only; no existing file modified):**
- `experiments/pa8_pristine_rerun.py` — pristine refit + regeneration + transfer battery
- `experiments/pa8_pristine_rerun.md` — this chronicle

## Hypothesis

PA2's own caveat: PA1's offsets were fit on pooled FY2020–2024 PA microdata
*including* the 817 holdout rows, so the PA-synth arms were not pristine vs
the test set — the PA-vs-national element gap (+0.037 acc, +0.038 macroF1 at
seed 7) could be partly inflated by the generator having seen test-set
marginals. If the advantage survives a pristine refit (same pooled window,
holdout rows excluded from *every* tuning step), PA2's decision stands; if
it collapses, PA2's PASS was contamination and the POC track's first
decision point must be redone.

Gate: transfer (the element gate is the transfer gate's currency, per PA2).

## Method

**Pristine refit** (`python3 experiments/pa8_pristine_rerun.py`, from repo
root; ran in a clean `git archive` checkout, microdata read-only at
`~/workspace/snap-qc-data/raw`): a verbatim port of `pa1.fit_pa_targets`
with one change — rows whose (fy, PA-relative row index) key appears in
`experiments/pa2_holdout_idx.json` are skipped before any aggregate is
touched (STATE indexing verified identical: strip vs no-strip PA counts
match 631/189/817/817/814 per FY). Kept 2,451 of 3,268 PA rows. Refit
constants installed by monkey-patching `src.synth.pa_state` module
attributes (PA6's pattern; no src file modified).

**Regeneration** follows PA1's it3 recipe exactly, all targets on the
minus-holdout fit: pure-empirical ratios → 20k-case pilot at PA_COIN_CAL=1.0
→ one-step realized-output bucket calibration × real-minus-holdout share /
synth share → PA_COIN_CAL line search (1.00–1.16 grid, 8k pilots) against the
pristine marginal case-error rate → final 20k, seed 7. The national arm was
regenerated identically (n=20k, seed 7) and verified **byte-identical** to
PA2's file (`/tmp/pa2out/nat_synth.jsonl`, md5 8a75b265ede3d337481ebeadb10c229f
both ways) — PA2's national file was reused for the battery.

**Transfer battery:** PA2's recipe — v1 features, sklearn
`HistGradientBoostingClassifier(random_state=0)` **without** class_weight
(PA2's winning setting), trained on pristine-PA synth (arm a) vs national
synth (arm b), evaluated on the same 817-row holdout (349 test error cases).
Binary AUC for the finding task computed from P(error) = proba(2)+proba(3).

## Results

### Pristine refit vs PA1's pooled fit (marginals barely moved)

| target | PA1 pooled | PA8 minus-holdout |
|---|---|---|
| finding c/o/u | 0.5875/0.2469/0.1656 | 0.5871/0.2449/0.1680 |
| case_err_rate | 0.4125 | 0.4129 |
| p(over\|err) | 0.5985 | 0.5931 |
| bucket ratios (pure empirical) | shelter 1.4420, medical 1.1623, hhcomp 0.9475, sua 0.6164, earned 0.9347, unearned 0.6846 | shelter 1.4513, medical 1.0972, hhcomp 0.9281, sua 0.6195, earned 0.9213, unearned 0.7058 |
| baked bucket ratios (post-calibration) | shelter 1.5425, medical 1.5631, hhcomp 0.6117, sua 0.5368, earned 0.9492, unearned 0.6723 | shelter 1.4724, medical 1.5389, hhcomp 0.6498, sua 0.5059, earned 0.9863, unearned 0.7204 |
| PA_COIN_CAL | 1.08 | **1.04** (grid best, finding L1 0.0117) |

Pristine PA synth finding L1 vs the minus-holdout target: **0.0098** (PA1
reported 0.028 on the pooled target — the pristine refit calibrated better,
partly because the coin search landed on 1.04 instead of 1.08).

### Element classification (349 test error cases), seed 7

| arm | acc | macroF1 | shelter F1 | medical F1 | earned F1 |
|---|---|---|---|---|---|
| a) pristine PA synth + GBM no-cw | 0.5559 | 0.1878 | 0.702 | 0.000 | 0.613 |
| b) national synth + GBM no-cw | 0.5301 | 0.1702 | 0.679 | 0.000 | 0.617 |
| **pristine PA-vs-national gap** | **+0.0258** | **+0.0176** | | | |
| PA2's reported gap (contaminated) | +0.037 | +0.038 | | | |

Absolute moves vs PA2: pristine PA acc 0.5559 vs 0.567 (−0.011), macroF1
0.1878 vs 0.208 (−0.020). The national arm reproduced to +0.0001 acc /
+0.0002 macroF1 (0.5301/0.1702 vs PA2's 0.530/0.170) — the byte-identical
file, so all gap movement is on the PA side. Most of the macroF1 drop is the
medical tail (F1 0.074 → 0.000; small-sample rare-bucket swing); shelter
0.741 → 0.702, earned 0.563 → 0.613.

### Finding classification (817 test cases), seed 7

| arm | acc | macroF1 | binary AUC (err vs corr) |
|---|---|---|---|
| a) pristine PA synth + GBM no-cw | 0.4345 | 0.4055 | **0.691** |
| b) national synth + GBM no-cw | 0.4039 | 0.3758 | 0.652 |
| PA2's PA arm binary AUC (contaminated) | — | — | 0.645 |

## Verdict

**The advantage survives pristine fitting — PA2's PASS stands, with the
caveat now quantified.** The element PA-vs-national gap narrows but does not
collapse: accuracy +0.037 → **+0.026**, macroF1 +0.038 → **+0.018**. PA2's
own guess was right in direction and size — the contamination advantage was
real but small (~0.01 acc, ~0.02 macroF1, roughly a third of the acc gap and
half the macroF1 gap), consistent with offsets seeing only pooled marginals
rather than test rows' labels. PA-conditioned synthetic still beats
national-trained on PA cases, on both element metrics, with the mechanism
intact (shelter-heavy test prior matched).

The finding-task sanity check kills the contamination story from the other
side: pristine binary AUC **0.691** is *higher* than PA2's contaminated 0.645
(and beats national's 0.652 by +0.039). PA2's 0.645 was not inflated — if
anything, the better finding-L1 calibration the pristine refit achieved
(0.0098 vs 0.028) improved the P(error) ranking. PA4's calibrated-ranking
plan keeps its foundation.

Two notes on absolute numbers: (1) the medical F1 collapse (0.074 → 0.000)
is a rare-bucket tail swing, not a mechanics change — the generator's
mechanics gap for medical/sua (per-bucket F1s near zero) remains PA2's open
lever; (2) the pristine coin cal of 1.04 vs PA1's 1.08 is a small line-search
difference on 8k pilots, not a signal about the no_earner ceiling.

## Next steps

- PA4 proceeds on the calibrated-ranking plan with the pristine-PA arm's
  binary AUC 0.691 as the reference (replaces PA2's 0.645).
- If the macroF1 tail matters for the copilot, the lever is still generator
  mechanics for medical/sua — pristine fitting did not fix it (medical F1
  0.000), and more sampling tricks won't either.
- Optional: seed-robustness for the pristine gap (seeds 8, 9) — PA2 showed
  the contaminated gap held at all 3 seeds; a quick pristine check would
  confirm the +0.026/+0.018 gap isn't seed luck. Cheap to run (two more
  20k gens + batteries).
