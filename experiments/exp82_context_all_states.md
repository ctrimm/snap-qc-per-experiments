# Experiment 82 — context-aware pooled models for every other jurisdiction

**Date:** 2026-10-10 · **Code:** `experiments/exp82_context_all_states.py` (pre-registered in its docstring) · **Results:** `experiments/exp82_results.json`

### Hypothesis

exp80's context-aware pooling (each state's cases plus every other state's, with the case's maximum allotment and the issued benefit's share of it as inputs) beat the deployed model in all 12 small jurisdictions. If the gain comes from learning shared patterns across states, it should help the 41 larger jurisdictions too, which currently use their own cases only.

### Method

As exp80 for the 41 jurisdictions not in it: B_ctx (pooled) and C_ctx (pooled, own cases ×10), default configuration, against the deployed exp68 model on the exp68 holdout and the FY2020–22 → FY2023–24 time split (the time split pools only FY2020–22 rows from every state, so no later data leaks in). Adopted only if better on both. Adopted models repackaged.

### Results

**Adopted in 41 of 41** (20 B_ctx, 21 C_ctx); every one better on both readouts.

| Example | Deployed (own cases): holdout / time split | Context-aware pooled |
|---|---|---|
| Pennsylvania | 3.48× / 3.14× | 4.08× / 3.82× |
| New York | 3.54× / 3.32× | 4.18× / 4.07× |
| Texas | 2.70× / 2.32× | 3.62× / 3.31× |
| California | 3.38× / 2.96× | 3.56× / 3.61× |
| Washington | 3.84× / 3.25× | 4.54× / 4.31× |
| Nebraska | 2.62× / 2.53× | 3.88× / 3.52× |

Holdout gain: median +0.73×, smallest DC +0.15× and California +0.18×, largest Arkansas, Utah and Nebraska (about +1.25×). With exp80, all 53 jurisdictions now run context-aware pooled models: **median 3.97× on held-out cases (lowest Alaska 2.96×, then Guam and Maryland 3.47×) and 3.80× on the later-years test (lowest Wyoming 2.91×, then Hawaii and Arkansas 3.29–3.30×)**. (Corrected 2026-10-10: an earlier summary in this chronicle said lowest 3.56× / 3.30×; it had left out the exp80 jurisdictions.)

### Verdict

Held, everywhere. One pooled model per state that knows the state's benefit levels beats a model trained on that state alone, in every jurisdiction and on both tests. Five years of one state's QC sample (about 3,000 cases) is thin; the error patterns that predict dollars (reported income and deductions relative to benefit levels) are largely shared across states, and the context features let the model adjust for each state's benefit scale. Checks against leakage: the later-years test pools only FY2020–22 data; each state's own holdout is never in its training data; both new inputs are agency-side. Each state's holdout had been scored before (exp68, 72, 75, 80); the adoption rule was fixed before this run.

### Next steps

1. exp83: re-measure the top-10% lift, dollar-forecast accuracy and household-type fairness for the adopted models.
2. Update the dashboard, the standalone map and the report. The exp69/78 cost-share scenarios used the older lifts, so they're conservative for the new models.
