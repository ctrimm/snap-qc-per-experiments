# Experiment 27 — earned-income element audit

**Date:** 2026-09-29 · **Code:** `experiments/exp27_earned_audit.py`

## Hypothesis

The earned-income element bucket is stuck at ~0.8x of the real per-case rate
(exp21: "likely keep-rate or nature-mix, not draw-side"; exp24: 0.80x on
adopted defaults). A **single dominant constraint** explains at least half of
the gap. Finding it matters for the **calibration gate**: if the generator's
earned-income prior is wrong, anything trained on it inherits the drift, and
earned income is the largest single variance bucket in real QC data.

Verdict rule for this experiment: the hypothesis holds iff I can name the
constraint with measured numbers **and** a fix moves earned per-case to
>= 0.90x of real without regressing the finding mix beyond L1 = 0.030.

## Method

Measurement-first, then one targeted fix probe (plus its entailed
recalibration). All in `experiments/exp27_earned_audit.py`; no generator
source files were edited — probes are clearly-delimited in-process patches.

- **[B]** Real aggregates from the FY2024 QC public-use file (n = 44,891),
  held-out validation, aggregates only, never in the repo. Four strata:
  earner/no-earner x senior/nonsenior.
- **[A]** 20,000-case baseline, seed 7, current defaults, with
  draw/record instrumentation (drawn vs recorded per bucket per stratum).
- **[A2]** Legacy-sampler check: patches the uncommitted exp29
  `BASE_POSITIVITY` change back in-process to validate the harness against
  exp24.
- **[D]** Per-stratum Kitagawa-style attribution of the per-case gap into
  stratum shares / P(error|s) / earned-per-error-case; draw-vs-record
  reconciliation against the materialization matrix.
- **[2]** Nature-mix within earned: real vs drawn vs recorded.
- **[D2]/[D3]** Recorded-share vs empirical-mix for all buckets; real-file
  structural checks (STATUS=1 variance rate, multi-variance rate, 1st vs
  2nd+ variance bucket mix).
- **[E]** 30k-household forced-earned materialization trace (seed 99):
  P(materialize|drawn) by nature and by base earned-income bin, failure
  anatomy.
- **[F]** Fix probe 1: P(2nd variance) 0.15 -> 0.38 (paired, seed 7).
- **[F2]** Fix probe 1 + recalibrated phase-1 injection coins.
- **[D4]** Faithful-count counterfactual: synth 1st-variance behavior kept,
  later-variance count and mix set to real (tests whether the count
  shortfall alone explains the gap).
- **[F3]** Fix probe 2: position-dependent draw mixes — 1st variance from
  the per-stratum M1 mix, 2nd+ from M2 (both keep-corrected with the same
  matrix weights).
- **[F4]** Fix probe 2 + recalibrated phase-1 coins.

Caveat: the working tree carries uncommitted coworker changes (exp29
`BASE_POSITIVITY` in `household.py`, plus in-flight edits to `errors.py`,
`dollar_mech.py`, `inject.json`). Baseline numbers below are from the final
run on that tree; [A2] confirms the harness still reproduces exp24
(0.835x vs exp24's 0.80x — residual is the other tree changes, not this
experiment's code).

## Results

### Real baseline [B]

n = 44,891; earned variances = 5,774 of 23,726. Overall real earned
per-case rate: **0.1286**.

| stratum | share | P(err\|s) | earned/case | earned/errcase | var/errcase |
|---|---|---|---|---|---|
| no_earner_nonsenior | 0.331 | 0.192 | 0.0137 | 0.071 | 1.269 |
| earner_nonsenior | 0.238 | 0.584 | 0.4471 | 0.766 | 1.400 |
| no_earner_senior | 0.396 | 0.435 | 0.0032 | 0.007 | 1.268 |
| earner_senior | 0.035 | 0.647 | 0.4692 | 0.725 | 1.549 |

Real finding mix assumed: 0.603 / 0.239 / 0.158.

### Synth baseline [A] and harness check [A2]

| run | finding mix | L1 | earned per-case |
|---|---|---|---|
| [A] current defaults | 0.604 / 0.251 / 0.145 | 0.025 | 0.0992 (**0.771x**) |
| [A2] legacy sampler | 0.606 / 0.249 / 0.146 | 0.025 | 0.835x (exp24: 0.80x) |

### Decomposition [D]: the gap lives in earned-per-error-case

Per-case gap (real - synth) = 0.0294, attributed:

| component | contribution | share of gap |
|---|---|---|
| stratum shares | +0.0010 | 3.3% |
| P(error\|s) | +0.0026 | 8.7% |
| **earned per error case** | **+0.0259** | **88.0%** |

Per-stratum gap contributions: earner_nonsenior ~62%, earner_senior ~41%
(the no-earner strata net to ~zero). The two earner strata are the whole
story.

### Dead hypotheses

- **Keep-rate / materialization ([D], [E]).** Recorded earned share lands on
  the empirical mix (0.85–1.04x across strata); measured keep rates match
  the materialization matrix (0.64–0.82 vs matrix 0.70–0.78). The forced
  trace: P(materialize|drawn) is flat ~0.74 across all natures; 100% of
  failures are |benefit delta| < $1 floor absorption (small earners absorb:
  base $1–200: 0.43, $201–500: 0.44, $501–1000: 0.56, $1001–2000: 0.94,
  $2001+: 1.00 — a real phenomenon, correctly modeled).
- **Nature mix ([2]).** Recorded earned nature mix matches real on every
  major nature (97: 1.03x, 35: 0.97x, 44: 0.99x, 38: 0.87x, 37: 1.03x).

### The constraint, refined in two steps

**Step 1 — the count shortfall is real but secondary.** Synth error cases
carry 1.09–1.13 variances vs real 1.27–1.55 (0.73–0.87x). But [D4]: fixing
only the later-variance count, faithfully (real later mix M2), moves earned
to just **0.803x** — the count explains ~14% of the gap, not half.

**Step 2 — the dominant constraint is the first-variance mix.** Real
1st variances are earned-*richer* than the marginal mix the generator draws
every variance from (M1), and real later variances are earned-*poorer*
(M2). The generator's single-mix design cannot match both:

| stratum | real M1 earned | marginal mix | real M2 earned |
|---|---|---|---|
| earner_nonsenior | 0.675 | 0.571 | 0.228 |
| earner_senior | 0.614 | 0.479 | 0.203 |

On earner_nonsenior (62% of the gap): real earned/errcase 0.766 =
0.675 (M1) + 0.401 x 0.228 (later); synth 0.632 =
0.563 + 0.110 x 0.571. The M1 gap (-0.112) is ~80% of the stratum gap;
the later-variance gap (-0.028) ~20%. Analytic counterfactual with M1 for
the first draw: **0.924x** (~67% of the total gap).

Why other buckets masked this: their recorded shares float *above* the mix
(shelter 0.90–1.17x, sua 0.87–1.26x, hhcomp 0.97–1.75x) — inflated by the
medical mechanics-gap fallback, which dumps undrawable medical draws into
other buckets on nonsenior strata (medical records 0.00x there). Earned,
pinned ~1.0x to the mix by its well-measured keep rates, absorbs the full
shortfall alone.

### Fix probes

| probe | earned per-case | finding L1 | note |
|---|---|---|---|
| [A] baseline | 0.771x | 0.025 | — |
| [F] P(2nd) 0.15->0.38 | **0.940x** | 0.058 | passes earned, breaks L1 |
| [F2] + recalibrated coins | **0.936x** | **0.025** | passes both gates numerically |
| [F3] M1/M2 draw mixes | **0.935x** | 0.049 | passes earned, breaks L1 |
| [F4] M1/M2 + recalibrated coins | **0.972x** | 0.037 | earned best; L1 misses 0.030 |

- [F2] passes both gates but works for the wrong reason: [D4] proves the
  faithful count fix only reaches 0.80x — [F2]'s 0.94x comes from drawing
  2nd variances from the earned-rich *marginal* mix instead of the
  earned-poor real M2 (two wrongs making a right). It also unmasks
  other-bucket overshoots (sua 1.10x, hhcomp 1.15x, arithmetic 1.13x).
  **Not recommended for adoption.**
- [F4] is the faithful fix: earned 0.77x -> **0.97x** (closes 88% of the
  gap), finding correct-share nailed (0.602 vs 0.603). Residual L1 = 0.037
  is entirely the over/under *split* (0.258/0.140 vs real 0.239/0.158):
  M1's earned-richer 1st variances shift the direction balance, and the
  97-resolution/direction coins were calibrated for the marginal regime.

## Verdict

**Partially held.** The single dominant constraint is named with measured
numbers: the generator draws every variance from the marginal bucket mix,
but real first-variances are earned-richer than marginal (M1 0.675 vs
0.571 on earner_nonsenior) — that M1 gap is ~80% of the dominant stratum's
shortfall, while the multi-variance count shortfall (the exp21/exp24
suspect) explains only ~14% when fixed faithfully. Keep-rate and nature-mix
hypotheses are dead. The faithful fix (M1/M2 position-dependent draw mixes
+ the entailed phase-1 coin recalibration) moves earned 0.77x -> 0.97x, but
L1 lands at 0.037 against the 0.030 bar — the residual is an over/under
direction split that needs a direction recalibration companion. Staged, not
adopted.

## Next steps

1. **(Recommended next run)** Direction recalibration under M1/M2: re-fit
   the 97-resolution coins / direction weights in the M1/M2 regime
   (`calibrate_injection.py` territory) to fix the over/under split
   (0.258/0.140 vs 0.239/0.158) and bring L1 under 0.030 with M1/M2
   adopted. Small, well-scoped, unblocks the earned fix.
2. Medical mechanics-gap fallback: medical draws on nonsenior strata fall
   back to other buckets, inflating their recorded shares (1.05–1.26x)
   and masking count shortfalls. Fix the fallback so every bucket pins to
   ~1.0x of its mix; re-check all buckets after.
3. Depcare under-recording (0.41–0.58x of mix) — a separate mechanism,
   separate experiment.
4. Multi-variance rate: synth var/errcase is 0.73–0.87x of real, worst on
   earner_senior (1.125 vs 1.549). Raise per-stratum once the mix structure
   is faithful; real multi-variance cases are 4,211/17,836 error cases
   (~33% carry 2+).
