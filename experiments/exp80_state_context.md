# Experiment 80 — state-context features for pooled small-jurisdiction models

**Date:** 2026-10-10 · **Code:** `experiments/exp80_state_context.py` (pre-registered in its docstring) · **Results:** `experiments/exp80_results.json`

### Hypothesis

exp75's pooling helped five small jurisdictions but not Hawaii or Guam, and Alaska and Wyoming still lost lift on later years, plausibly because their benefit levels differ from the mainland's. Giving the pooled model each case's maximum allotment (BENMAX, which varies by state, region and year) and the issued benefit as a share of it should let it tell states apart.

### Method

The 12 jurisdictions under 2,500 QC cases; exp75's variants with the two extra features (B_ctx pooled, C_ctx pooled with own rows ×10); the same holdout and time split. A context variant replaces the deployed model (exp75's choice) only if it beats it on both. Adopted models repackaged; `score_cases.py` now reads BENMAX for them.

### Results

| Jurisdiction | Deployed before: holdout / time split | Adopted context model | After |
|---|---|---|---|
| Guam | 2.66× / 2.95× (own) | C_ctx | **3.47× / 3.66×** |
| Virgin Islands | 3.70× / 2.71× (pooled) | B_ctx | **3.96× / 3.38×** |
| Wyoming | 3.47× / 1.71× (pooled) | B_ctx | **3.79× / 2.91×** |
| Alaska | 2.87× / 1.85× (pooled) | B_ctx | **2.96× / 3.40×** |
| Delaware | 3.38× / 3.29× (pooled) | B_ctx | **3.99× / 3.82×** |
| North Dakota | 2.88× / 2.82× (own) | B_ctx | **4.19× / 3.74×** |
| Hawaii | 2.68× / 2.51× (own) | C_ctx | **3.61× / 3.29×** |
| Maryland | 3.25× / 2.63× (own) | C_ctx | **3.47× / 3.42×** |
| New Jersey | 2.95× / 2.82× (own) | B_ctx | **4.17× / 3.80×** |
| New Hampshire | 3.17× / 2.80× (own) | B_ctx | **3.91× / 3.43×** |
| South Dakota | 2.75× / 2.50× (own) | C_ctx | **4.16× / 3.88×** |
| Montana | 3.44× / 2.92× (pooled) | B_ctx | **3.93× / 3.50×** |

### Verdict

Held, emphatically: adopted in all 12, each better on both readouts. The context features fixed exactly the cases pooling alone couldn't: Hawaii (2.68× → 3.61×), Guam, and Alaska's and Wyoming's later years (time split 1.85× → 3.40×, 1.71× → 2.91×). Pooled, context-aware models now beat own-case models even for mid-sized states such as New Jersey and North Dakota, which raises the question exp82 tests: does this help every jurisdiction? The holdouts were scored before (exp68, 72, 75); the adoption rule was fixed before this run.

### Next steps

exp82: the same comparison for the other 41 jurisdictions.
