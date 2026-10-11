# Experiment 81b — automatic PA generator calibration, scored on several seeds

**Date:** 2026-10-10 · **Code:** `experiments/exp81_generator_autocal_pa.py --seeds 3` (pre-registered in its docstring) · **Results:** `experiments/exp81b_results.json`, `exp81b_log.json`

### Why

exp81 chased seed noise: PA1's own score moved more between generator seeds than the gains the search found. This rerun scores every candidate as the mean of 3 seeds, requires a gain above 0.005, and checks the winner on 5 fresh seeds plus the locked PA2 holdout.

### Results

| Element macro-F1 | PA1 (hand-built) | Best knobs found |
|---|---|---|
| Dev, search seeds 7–9 (mean) | 0.199 | 0.223 |
| Dev, fresh seeds 21–25 (mean) | 0.197 | **0.205** |
| **Locked holdout** | **0.213** | 0.181 |
| Locked holdout, finding accuracy | 0.362 | 0.395 |

Per fresh seed (PA1 / best): 0.215/0.213, 0.196/0.190, 0.180/0.208, 0.187/0.226, 0.206/0.187.

### Verdict

Did not hold. Multi-seed scoring fixed the noise-chasing on development data (the gain now holds on fresh seeds, +0.008), but the result doesn't carry to the held-out real cases (0.181 vs 0.213). With about 300 labeled error cases in each split, element macro-F1 on real PA data is itself noisy, and 13 knobs tuned against one split overfit it. The hand-built PA1 generator stays. Tier A automatic calibration isn't useful at this data size; a version with cross-validated dev scoring (rotating the real split) would be the next attempt, if any.

### Next steps

None planned. The generator's role in the product is now small: the shipped rankers train on real QC data (exp58 onward), and the language-model work uses the existing generator.
