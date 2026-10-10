# Experiment 75 — pooling other states' cases for the small jurisdictions

**Date:** 2026-10-10 · **Code:** `experiments/exp75_small_state_pooling.py` (pre-registered in its docstring) · **Results:** `experiments/exp75_results.json`

### Hypothesis

Alaska (1.26×) and Wyoming (1.72×) had the weakest exp68 rankers, and both have few QC cases. Training on their own cases pooled with every other jurisdiction's should help small samples, provided the patterns carry across states.

### Method

Targets: the 12 jurisdictions with fewer than 2,500 QC cases. Variants: A, own cases only (= exp68); B, own + all other jurisdictions' cases; C, as B with own cases weighted ×10. Readouts on the target only: exp68 holdout top-20% lift, and a time split (train FY2020–22, test the target's FY2023–24). Rule fixed in advance: B or C replaces A only if it beats A on both. Adopted variants were refit on all rows, dollar-calibrated on out-of-fold scores of the target's own cases, and packaged over the exp68 versions.

### Results

| Jurisdiction (QC cases) | A own: holdout / time split | B pooled | C pooled, own ×10 | Adopted |
|---|---|---|---|---|
| Guam (732) | 2.66× / 2.95× | 2.58× / 2.56× | 2.90× / 2.24× | A |
| Virgin Islands (998) | 3.31× / 2.51× | 3.57× / 2.58× | **3.70× / 2.71×** | C |
| Wyoming (1,191) | 1.72× / 1.51× | 3.03× / 1.87× | **3.47× / 1.71×** | C |
| Alaska (1,367) | 1.26× / 1.64× | 2.29× / 1.85× | **2.87× / 1.85×** | C |
| Delaware (1,652) | 3.17× / 2.88× | **3.38× / 3.29×** | 3.19× / 3.32× | B |
| North Dakota (1,691) | 2.88× / 2.82× | 3.83× / 2.54× | 3.92× / 2.61× | A |
| Hawaii (2,009) | 2.68× / 2.51× | 2.31× / 2.31× | 2.47× / 2.40× | A |
| Maryland (2,279) | 3.25× / 2.63× | 3.22× / 2.94× | 3.23× / 3.07× | A |
| New Jersey (2,327) | 2.95× / 2.82× | 3.67× / 2.69× | 3.69× / 2.71× | A |
| New Hampshire (2,328) | 3.17× / 2.80× | 3.04× / 2.66× | 3.35× / 2.75× | A |
| South Dakota (2,365) | 2.75× / 2.50× | 3.56× / 2.19× | 3.54× / 2.39× | A |
| Montana (2,421) | 2.86× / 2.74× | 3.33× / 2.88× | **3.44× / 2.92×** | C |

(For Delaware, B and C both qualified; the rule took the higher holdout lift, B.)

### Verdict

Held for the weakest: Wyoming 1.72× → 3.47× and Alaska 1.26× → 2.87× on the holdout, with smaller gains on the time split (1.51× → 1.71×, 1.64× → 1.85×). Five jurisdictions adopted a pooled model. With them, **all 53 jurisdictions now reach at least 2.5× on held-out cases** (lowest 2.61×). Pooling raised the holdout lift but not the time split in North Dakota, New Jersey and South Dakota, so the rule kept their own models. Hawaii got worse, plausibly because its benefit levels differ from the mainland's. The targets' holdouts had been scored in exp68 and exp72; the adoption rule was fixed before this run.

### Next steps

1. Alaska and Wyoming still lose much of their lift on the later years (time split 1.71–1.85×); a pilot there should use the state's own case data.
2. Add a state-context feature (allotment levels) so pooled models fit Alaska, Hawaii and Guam better.
