# Experiment 1 — Synthetic generator calibration
**Date:** 2026-09-28 · **Code:** `experiments/exp1_calibration.py`
(iterations 1–7; later iterations supersede earlier ones)

## Hypothesis
North star gate: **calibration**. If the synthetic generator's variance
taxonomy and dollar-error distributions match the real FY2024 QC file, the
synthetic cases are a faithful-enough prior for downstream training. A
generator whose marginals are wildly off would bake false priors into any
model trained on it.

## Method
- Built the empirical distribution from the real FY2024 QC file
  (`experiments/build_dist.py` → `experiments/dist.json`): 44,891 cases;
  60.3% correct / 23.9% over-issuance / 15.8% under-issuance; per-case
  variance arrays (ELEMENT/NATURE/AGENCY); AMTERR dollar errors.
- Generated 50k synthetic cases (`src/synth/`), ran the calibration script,
  and compared: finding mix, nature mix, cause mix, element-bucket mix,
  dollar-error quantiles. Iterated 7 times on sampler base rates, variance
  injection, and dollar mechanics.

## Results
What matches (ratios = synthetic / real):
- Nature mix: 0.8–1.7x. Cause buckets: 1.0–1.3x.
- Element buckets: shelter 1.09x, unearned income 1.41x, SUA 1.52x,
  medical 0.74x. Dollar error p90: 77 vs 78 real; mean 19.9 vs 28.4.

Known gaps:
- **Finding mix 79/9/12 vs real 60/24/16** — over-issuances underproduced.
  Root cause: the max-allotment ceiling absorbs over-direction corruptions
  (synthetic at-max households 42% vs 37% real); only buckets that can move
  at-max cases (hhcomp, arithmetic) produce overs.
- **Earned-income bucket 0.31x** — wage errors barely move the needle at
  current earnings levels; real QC has more under-reported earnings mass.
- **hhcomp 2.7x / arithmetic 2.7x** — inflated precisely because they are the
  only buckets that move at-max households (see above); the two gaps are one
  mechanism.
- depcare 0.13x — near-absent in synthetic cases.

## Verdict
Hypothesis **partially held**. The taxonomy and dollar magnitudes are close
enough that a model could learn real-shaped priors — but the finding mix is
materially off (over-issuances starved), which is the single most important
marginal for a QC copilot. The generator is usable for transfer tests (exp2)
but not yet trusted as a training prior without the fixes below.

## Next steps
1. (Recommended) Rebalance at-max exposure: make max-allotment cases rarer
   in the sampler or give corruptions a path to push *through* the ceiling
   via income-side errors, so over-issuances reach ~24%.
2. Strengthen earned-income error mass (higher under-report rates at
   low earnings) to close the 0.31x gap.
3. Revisit SUA/medical/depcare mechanics — currently near-degenerate in the
   generator (also visible in exp2's per-bucket transfer F1).
