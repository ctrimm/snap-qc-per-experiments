# Experiment 39 — household joint-distribution realism
**Date:** 2026-09-29 · **Code:** `experiments/exp39_joint_distributions.py`

## Hypothesis
The sampler draws each household attribute independently (or only coupled
through the income screen), so its *joint* distributions over household
attributes diverge from real QC in ways marginal checks miss — particularly
joints that feed the benefit computation. If true, the calibration gate
needs joint structure (e.g. conditional sampling tables), not just
better-tuned marginals. If the divergent joints are benefit-neutral, the
marginals are sufficient and this stays parked.

## Method
- **Generator state:** `git rev-parse HEAD` = `f515930843d66d784ee1b95288e600de22353bfa`;
  `git status --short` showed uncommitted edits under
  `src/synth/dollar_mech.py`, `src/synth/errors.py`, `src/synth/household.py`
  (another researcher's in-flight work — treated as read-only, measured
  against as-is). Only my two exp39 files were written.
- **Synth:** 20k cases, seed 7, `experiments/dist.json`,
  `cd src && python -m synth.generate --n 20000 --seed 7 --dist ../experiments/dist.json --out /tmp/exp39_synth.jsonl`.
  (The task's literal `python3 src/synth/generate.py` fails: generate.py uses
  relative imports, so it must run as a module from `src/`.) Uses
  `case["facts"]` (true facts, pre-injection) and `case["correct_benefit"]`.
- **Real:** FY2024 QC public-use microdata (held-out; never committed),
  weighted by HWGT (unweighted run as sensitivity check).
- **Comparable bins, both sides:**
  hhsize 1..5, 6+ (real CERTHHSZ grouped at 6+) · earner = any earnings
  (FSEARN>0 / earned>0) · income band = gross earnings+unearned in
  [<1k, 1-2k, 2-3k, 3k+] · shelter band = 0 / (0,700] / (700,1200] / >1200
  (real RENT+UTIL vs synth shelter cost) · senior/disabled flag (real
  FSNELDER>0 or FSNDIS>0) · medical-expense flag (FSMEDEXP>0 / medical_exp>0).
- **Joints compared:** A = hhsize x earner; B = income x shelter;
  C = hhsize x income x earner; D = senior/dis x medical x earner.
  Metric: **L1 distance** (sum of absolute cell-probability gaps; the mass
  you'd have to move to match), chi-square as secondary, cells ranked by
  |p_real - p_synth| contribution.
- **Benefit tracing:** importance reweighting — reweight each synthetic case
  by w = p_real(cell)/p_synth(cell) so the synthetic joint matches the real
  one, then recompute mean correct benefit. If the joint divergence is
  cosmetic, the mean barely moves; if material, it does. ESS = effective
  sample size after reweighting (how much usable data the weights leave).

## Results

Headline: the synthetic mean correct benefit is **$423.8 vs real FSBEN $341.1**
— an $82.7 gap — and reweighting the (hhsize x income x earner) joint closes
it to **$344.3** (unweighted sensitivity: $356.7 vs $354.5). The gap is
compositional, not a benefit-math bug: within cells, synth and real mean
benefits agree (see tables below).

Joint divergence and materiality:

| joint | L1 | chi2 (dof) | mean benefit unweighted -> reweighted | delta |
|---|---|---|---|---|
| A hhsize x earner | 0.425 | 4937 (11) | 423.8 -> 353.5 | **-70.4** |
| B income x shelter | 0.347 | 7907 (15) | 423.8 -> 424.6 | +0.8 (cosmetic) |
| C hhsize x income x earner | 0.528 | 8728 (47) | 423.8 -> 344.3 | **-79.5** |
| D senior/dis x medical x earner | 0.299 | 2204 (5) | 423.8 -> 405.0 | **-18.8** |

Top divergent cells (p_real vs p_synth, with per-cell mean benefit):

Joint A: `1xnoEarn` +0.167 (ben 203 vs 213) — real QC is 51.9% size-1
non-earners, synth 35.2%. Synth overproduces multi-person non-earner
households: `2xnoEarn` -0.068, `3xnoEarn` -0.047, `4xnoEarn` -0.032.

Joint C top cells: `1x<1kxnoEarn` +0.097, `2x<1kxnoEarn` -0.065,
`1x1-2kxnoEarn` +0.058 — same story at income resolution.

Joint D: `senDisxnoMedxnoEarn` +0.123 (real 40.4% vs synth 28.1%),
`nonSenxnoMedxnoEarn` -0.116. Real QC is 50% senior/disabled; synth 36.5%.

Joint B top cells (`<1kx>1200` -0.093, `1-2kx0` -0.046): real, but the
reweight delta is +$0.75 — pure cosmetic. Shelter/income coupling does not
survive the excess-shelter cap into benefit dollars.

Conditional diagnosis (what the sampler gets wrong):

| dim | marginal L1 | real | synth |
|---|---|---|---|
| hhsize | 0.275 | 1:60.2% 2:16.6% 3:10.3% 4:6.8% 5:3.5% 6+:2.5% | 1:46.5% 2:24.1% 3:13.7% 4:8.6% 5:4.1% 6+:3.0% |
| earner | 0.016 | 27.6% | 26.7% (marginal fine!) |
| income band | 0.185 | [<1k .523, 1-2k .324, 2-3k .102, 3k+ .051] | [.576, .363, .048, .013] |
| senior/dis | 0.270 | 50.0% | 36.5% |

The earner marginal matches but the conditional is badly wrong —
P(earner | hhsize):

| hhsize | 1 | 2 | 3 | 4 | 5 | 6+ |
|---|---|---|---|---|---|---|
| real | 0.138 | 0.349 | 0.524 | 0.588 | 0.656 | 0.688 |
| synth | 0.242 | 0.272 | 0.295 | 0.303 | 0.320 | 0.317 |

Real earner probability rises steeply with household size; the sampler draws
it flat (p_earn 0.65/0.13 by senior flag only). It over-earns size-1 and
massively under-earns large households. Similarly P(senior/dis | hhsize) is
wrong-shaped: real concentrates in small households (0.65 at size 1, ~0.18
at 3+); synth is flat-ish (0.47/0.28/0.26). And earners' incomes skew too
low at the top: P(income band | earner=1) is [.247,.330,.255,.169] real vs
[.269,.502,.181,.047] synth — the size-conditioned lognormal means
under-shoot and the income screen truncates the tail.

## Verdict
Hypothesis **confirmed, with a twist**: the joint divergences are real and
material, but not all of them — the income x shelter joint (L1=0.35) is
benefit-neutral and should be left alone. The sampler needs joint structure,
not just marginal tuning, in three places: (1) P(earner | hhsize) — the
biggest material lever, worth ~$70 of the $83 mean-benefit gap; (2)
P(senior/disabled | hhsize) plus the senior/dis marginal (real 50/50, synth
63.5/36.5); (3) earner income levels at the top of the distribution
(2-3k and 3k+ bands underproduced ~2-4x). Note the marginals are *also* off
(hhsize itself: 60% vs 47% size-1), so this is not purely an interaction
story — independent draws get both margins and conditionals wrong.
Recommendation: fit empirical conditional tables (hhsize target,
earner|hhsize, senior|hhsize, income quantiles | earner,size) rather than a
copula — the structure needed is coarse and tabular.

## Next steps
1. **(Recommended next run)** Fix only P(earner | hhsize) in the sampler
   (tabular draw, smallest change, biggest lever) and re-run this script:
   expect mean correct benefit to drop ~$60-70 toward $341 and joint-A L1
   under ~0.15. One experiment, clean before/after.
2. Refit the senior/disabled draw (P(senior|hhsize) table + disabled rate)
   and the hhsize weights to the post-screen certified frame.
3. Refit earner income: raise size-conditioned lognormal means / widen
   sigma so the 2-3k and 3k+ bands match among earners post-screen.
4. Do NOT add income-shelter coupling (cosmetic; reweight delta +$0.75).
   Leave joint B as is.
