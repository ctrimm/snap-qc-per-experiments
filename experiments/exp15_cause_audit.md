# Experiment 15 — cause-mix calibration audit
**Date:** 2026-09-29 · **Code:** `experiments/exp15_cause_audit.py`
· **Config:** 20k cases, seed 7, `experiments/dist.json` (persistent mode,
the default) → `/tmp/exp15_synth.jsonl` · **Artifacts:**
`experiments/exp15_cause_audit_results.json` (aggregate shares only — no
microdata in the repo)

## Hypothesis
Every variance in the QC file carries a **cause**: *who* is responsible —
the agency (e.g. policy applied wrong, reported information disregarded,
failed to verify), the client (e.g. information not reported, incorrect
information provided), or neither/other (e.g. change not required to be
reported, collateral-contact error, "other"). The generator draws cause codes
from the empirical per-element-bucket conditional distribution in
`dist.json` (`cause_given_bucket`) with **no** importance weighting, then the
exp-7 persistent filter drops non-materializing variances. Two things could
have gone stale since exp 1 checked this ("cause buckets: 1.0–1.3x"): the
conditional mixes could have drifted under the new draw distributions, or the
materialization filter could distort cause shares (cause correlates with
nature 97, which has its own materialization behavior). If the recorded cause
mix is distorted, the calibration gate fails and the pretraining labels teach
the LM a wrong story about who causes errors. Expectation: the mix still
tracks at roughly exp-1 levels (~1.0–1.3x), with the blank-cause question as
the unknown.

North-star tie: calibration. Cause is one of the five recorded variance
attributes (element, nature, cause, direction, dollar); a mislabeled cause
mix poisons the LM pretraining data exactly like the element mix did before
exp 7.

## Method
Real side: streamed all 44,891 rows of the FY2024 QC public-use file
(held-out validation only; never committed). Per variance slot 1–9 with a
non-blank element, mapped the element code to a bucket via
`codebook.element_bucket` and the AGENCY code to a coarse bucket: **agency**
= codes 10–25 series (policy/verification/follow-up/computer errors),
**client** = codes 1, 2, 3, 4 (not reported / incomplete / withheld /
incorrect information), **other** = codes 7, 8, 26, 99
(collateral-contact / federal computer match / not required to be reported /
other), **unknown** = blank AGENCY field. (This differs slightly from
`codebook.CAUSE_BUCKETS`, which maps only codes 1/2/4 to client, a subset of
agency codes, and code 26 to `no_fault`; the three-way split follows the
codebook descriptions directly. The fine-grained per-code table below lets a
reader regroup as they like.)

Synth side: 20k cases from `src/synth/generate.py` (persistent default),
read back the recorded `(element_bucket, cause)` per variance, same mapping.

Compared real vs synth as shares of variances with ratios (synth / real),
plus L1 distance (terms.md: total probability mass to move to match).

## Results
20k cases → 8,614 synthetic variances vs 23,726 real variances.

### Overall cause mix
| cause | real | synth | ratio |
|---|---|---|---|
| agency | 0.366 | 0.413 | 1.13 |
| client | 0.247 | 0.289 | 1.17 |
| other | 0.262 | 0.298 | 1.14 |
| **unknown (blank)** | **0.125** | **0.000** | **0.00** |

L1 = 0.249 — but *all* of it is the unknown row. Conditional on a recorded
cause (the fair comparison, since the generator always records one):

| cause | real | synth | ratio |
|---|---|---|---|
| agency | 0.418 | 0.413 | 0.99 |
| client | 0.282 | 0.289 | 1.02 |
| other | 0.299 | 0.298 | 1.00 |

Known-conditional L1 = **0.014**. The recorded cause mix tracks the empirical
mix essentially exactly.

### Where the blank cause lives
100% of the real file's blank causes sit on **nature 97** ("not required to
be reported or acted upon" — a timing/reporting variance where no party is
at fault, so reviewers record no cause). P(blank cause | nature 97) = 0.320
(n = 9,231); every other nature code has zero blanks. The blank share varies
by bucket only because nature 97 concentrates there (shelter 0.154, earned
0.138, medical 0.134, unearned 0.118 vs arithmetic 0.049, hhcomp 0.027).

### Per element bucket (conditional on recorded cause)
| bucket | n_real / n_synth | agency | client | other |
|---|---|---|---|---|
| earned | 5,774 / 2,128 | 0.353/0.343 (0.97) | 0.313/0.309 (0.99) | 0.335/0.348 (1.04) |
| unearned | 5,268 / 2,167 | 0.504/0.513 (1.02) | 0.221/0.217 (0.98) | 0.275/0.270 (0.98) |
| shelter | 7,432 / 2,751 | 0.275/0.289 (1.05) | 0.353/0.346 (0.98) | 0.372/0.365 (0.98) |
| sua | 1,851 / 905 | 0.540/0.551 (1.02) | 0.284/0.261 (0.92) | 0.176/0.188 (1.07) |
| hhcomp | 619 / 350 | 0.485/0.506 (1.04) | 0.430/0.437 (1.02) | 0.085/0.057 (0.67) |
| arithmetic | 406 / 256 | 0.837/0.812 (0.97) | 0.047/0.066 (1.42) | 0.117/0.121 (1.04) |
| medical | 1,101 / 53 | 0.590/0.698 (1.18) | 0.078/0.057 (0.73) | 0.332/0.245 (0.74) |
| depcare | 385 / 4 | noise (n=4) | — | — |

All major buckets track at 0.92–1.07. The three outliers are noise: medical
agency 1.18 is 1.7σ (n_synth = 53 — the small n is the *known* medical
element-mix under-recording, exp 7's open item #3, not a cause problem);
hhcomp-other 0.67 is 1.7σ; arithmetic-client 1.42 is 1.0σ.

### Fine-grained cause codes (share of variances with recorded cause)
Every one of the top 15 codes lands at 0.87–1.15, most at 0.93–1.04: code 26
(no-fault) 1.00, code 1 (info not reported) 1.04, code 12 (reported info
disregarded) 1.00, code 10 (policy incorrectly applied) 0.94, code 4 (client
IPV) 0.99, code 2 (incomplete info) 1.04, code 16 (failed to verify) 0.96,
code 19 (mass change) 1.02, code 22 (budgeted wrong amount) 1.01, code 14
(no follow-up) 0.93, code 3 (withheld/IPV) 0.99, code 99 (other) 0.87,
code 15 0.98, code 18 0.94, code 20 1.15. No single code drives any gap —
the cause machinery has no residual worth tuning.

Note: the generator emits only the 8 buckets in `dist.json`; buckets
assets/childsupport/income_total/reporting/standard/other have zero synth
variances. That is element coverage, not cause — out of scope here.

## Verdict
Hypothesis **confirmed**: the cause mix tracks. Conditional on a recorded
cause, real vs synth is 0.418/0.282/0.299 vs 0.413/0.289/0.298 — ratios
0.99/1.02/1.00, L1 = 0.014 — and every element bucket and every individual
cause code lands at ~1.0x. The materialization filter does not distort cause
shares: cause is a recorded label only (it never influences the corruption),
so drawing it from the empirical conditional mix is enough. The only
"gap" is definitional, not calibration: the real file leaves 12.5% of
variances with a blank cause (entirely nature-97 timing variances), while the
generator always assigns one. The calibration gate passes as-is; the blank
question below is a fidelity choice, not a failure.

## Next steps
1. **Blank-cause rule for nature 97 (recommended).** When a recorded variance
   carries nature 97, leave its cause blank with P = 0.32 (the empirical
   P(blank | 97)); all other natures keep their drawn cause. This is a pure
   labeling change — cause never drives materialization, so finding/element/
   nature mixes are untouched — and it would bring the *unconditional*
   overall cause L1 from 0.249 to ~0.014 by construction. Cost: one
   probability, ~5 lines in `inject()`. Value: the pretraining labels match
   the real file's missingness pattern exactly, so the LM never learns to
   invent a cause where reviewers record none. Staged for a go-ahead.
   - **Done:** Implemented in commit 19414d0: the national generator blanks cause on 32% of nature-97 variances (exp52 training data: 36% "other" among nature-97 primaries).
2. Do nothing (acceptable alternative): keep the generator always recording
   a cause and document the 12.5% definitional gap; consumers can drop cause
   on nature-97 variances themselves.
3. No further cause-distribution work — the per-code table shows nothing left
   to tune. If a future transfer test finds the LM over-attributing agency
   blame on specific buckets, revisit with the per-bucket tables above as
   the baseline.
