# Experiment ID3: Idaho error anatomy

**Date:** 2026-10-04 · **Code:** `experiments/id3_id_anatomy.py`
(results: `/tmp/id3out/anatomy.json`, scratch)

## Hypothesis

Tied to the north star (the whitepaper's "The problem" section and the
copilot attention order): Idaho's process-failure fingerprint vs national
— which elements, natures, and causes define it, in one line each.

## Method

Port of `experiments/sd3_sd_anatomy.py` with STATE="16" (string —
csv.DictReader path). Pooled FY2020-2024 ID rows (n=3,839; 1,292 weighted
error cases) vs all-US. Finding/direction mixes; dollar-error quantiles
(AMTERR); element / nature / cause mixes as ID-vs-national ratios
(FYWGT-weighted, primary variance slot 1); top element×nature patterns;
FY trend table.

## Results

**Idaho's fingerprint, one line each:**
- **Timing (nature 97):** 62.4% of ID variances at **1.57x** national
  (39.7%) — a timing/reporting shop, same shape as NY's 1.56x.
- **Shelter:** 43.6% of ID variances at **1.40x** national — the dominant
  element, and shelter×97 alone is 28.9% of all ID variances (1.76x).
- **Earned income:** 24.6% at 0.92x national — the second element;
  earned×97 is 18.2% of ID variances (1.70x), median error $22.
- **Unearned income:** 0.69x national — below.
- **Medical:** 0.66x national — below (the mirror of NY's 1.79x).
- **SUA:** 0.86x national — slightly below.
- **Household composition:** 0.45x; **arithmetic:** 0.34x — well below.
- **Cause:** client-caused **1.66x** national, agency-caused **0.42x** —
  Idaho codes client-caused errors far more honestly/often than the
  national mix (which leans agency); no_fault 1.61x.
- **Direction:** over 61.4% / under 38.6% — identical to national
  (61.5%/38.5%). No directional skew.
- **Dollars:** p50 $15 overall ($18 over / $12 under), p90 $64 — vs
  national p50 $28 / p90 $186. **No big-dollar tail** (cf. SD's p90 $70):
  the fact that makes the ID5 P-alone question live.

**Finding mix:** ID correct/over/under 0.666/0.205/0.129 vs US
0.614/0.238/0.149 — ID errs less often (33.4% vs 38.6%).

**FY trend:** the shelter-heavy, timing-heavy profile is stable across
FY2020-2024 (shelter 40-44% of variances every year; the FY2020 file
shows a higher "standard"-deduction share, 7.5%, a partial-year coding
note consistent with the fitting-window exclusion).

**Coding-practice notes:** cause-99 distortion absent — Idaho codes
specific causes (1 "information not reported" at 1.69x, 2 at 1.71x, 4 at
1.51x national). No non-codebook nature-code quirk of note (unlike NY's
~4%).

## Verdict

**Held.** Idaho's story is process-layer (timing/verification: 62% of
variances are nature-97 at 1.57x national; shelter deduction timing is the
single biggest pattern), not computation-layer — corroborating ID8c's
clean engine. The anatomy paragraph for the whitepaper: timing-heavy
(1.57x), shelter-heavy (1.40x), client-coded (1.66x), small-dollar (p90
$64). The ratios table is the calibration spec ID1 already used.

## Next steps

- The 2–3 defining ratios (timing 1.57x, shelter 1.40x, client-cause 1.66x)
  go in the whitepaper's "The problem" section.
- ID7 cross-checks that the model's top features match this anatomy.
