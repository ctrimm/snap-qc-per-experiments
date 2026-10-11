# Experiment 81 — loop 3, tier A: automatic calibration of the PA generator

**Date:** 2026-10-10 · **Code:** `experiments/exp81_generator_autocal_pa.py` (pre-registered in its docstring) · **Results:** `experiments/exp81_results.json`, `exp81_log.json`

### Question

Can an automatic search over the PA generator's 13 numeric knobs (coin calibration, earner/non-earner coin ratios, 8 bucket ratios, over/under dollar scales) match or beat the hand-built PA1 generator on the transfer test it was built for? The PA2 holdout stays locked until a single final check.

### Method

(1+6) evolution strategy over knob multipliers ([1/3, 3]); each candidate generates 8,000 PA synthetic cases (seed 7) and is scored by element macro-F1 of a classifier trained on them and tested on real PA dev rows, with finding-mix and element-mix constraints. 60 generations (360 candidates, about 11 minutes). Final check: PA1 vs the best knobs on 3 fresh seeds and on the locked holdout.

### Results

| | PA1 (hand-built) | Best knobs found |
|---|---|---|
| Dev, search seed 7 | 0.178 | 0.239 |
| **Dev, fresh seeds 11–13 (mean)** | **0.207** | 0.183 |
| **Locked holdout, element macro-F1** | **0.213** | 0.202 |
| Locked holdout, finding accuracy | 0.362 | 0.409 |

Verdict rule: not met (holdout element macro-F1 lower, fresh-seed dev lower).

### Verdict

Did not hold, for an instructive reason: the search chased noise. PA1's own score moves from 0.178 to 0.207 just by changing the generator's random seed, a swing larger than the gains the search found, so optimizing one seed selected knobs that were lucky on that seed. (Finding accuracy on the holdout did rise, 0.362 → 0.409, but it wasn't the objective and isn't a reason to adopt.) Generator defaults were not changed.

### Next steps

exp81b: the same loop with each candidate scored as the mean over 3 seeds, a stricter improvement threshold (0.005), and a 5-seed final check.
