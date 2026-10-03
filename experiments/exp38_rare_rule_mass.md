# Experiment 38 — Rare-rule mass audit
**Date:** 2026-09-29 · **Code:** `experiments/exp38_rare_rule_mass.py`

### Hypothesis
The generator is missing structural error mass from SNAP rules it doesn't model — student eligibility (element 111), ABAWD time limits (element 161) and the wider work-rule cluster (160–166), and elderly/disabled special provisions — and that missing mass is quantitatively material. Ties to the **calibration gate**: if these rules carry real error mass, the element marginal can't calibrate without dedicated mechanisms.

### Method
Code mapping (FY2024 QC Technical Documentation, Chapter V codebook, cross-checked against FNS Handbook 310 §850.7):
- **Student:** element 111 = Student status.
- **Work-rule:** 160 Employment & training programs, 161 Time-limited participation (= ABAWD 3-in-36-months rule, confirmed in Handbook 310), 162 Work registration, 163 Voluntary quit, 164 Workfare, 165 Employment status/job availability, 166 Acceptance of employment.
- **Elderly/disabled:** the QC variance taxonomy has **no dedicated elderly/disabled element**. The nearest candidates are 810 (SNAP simplification project — includes ESAP, the Elderly Simplified Application Project, a state waiver) and 820 (demonstration projects). The substantive elderly provisions (medical deduction 365, separate-household determinations under 150, higher asset limits) flow through elements the generator already models.
- Context (not hypothesis): 130 citizenship, 140 residency, 151 disqualification, 170 SSN, 362 homeless shelter deduction, 530 transitional benefits.

Real side: FY2020–2024 QC public-use microdata, held out (read from `~/workspace/snap-qc-data/raw/`, never copied into the repo). Per FY and target set: FYWGT-weighted variance share, weighted share of error cases (STATUS 2/3) carrying ≥1 target variance, and weighted dollar share = Σ(FYWGT·|AMTERR|) over target-carrying error cases ÷ all error cases (microdata has no per-variance dollar field, so dollars are attributed at case level — a mild overstatement when cases have multiple variances, negligible here since case shares are <1%).

Synth side: `python3 -m src.synth.generate --n 20000 --seed 7 --dist experiments/dist.json --out /tmp/exp38_synth.csv`; checked emitted element codes and computed the element-marginal L1 vs real FY2024, with the target sets' contribution.

Reproducibility: `git rev-parse HEAD` → `f515930843d66d784ee1b95288e600de22353bfa`; `git status --short` shows uncommitted in-flight edits in `src/synth/dollar_mech.py`, `src/synth/errors.py`, `src/synth/household.py` plus unrelated exp26–exp30 files — src/ treated as read-only per standing rules. `dist.json` samples only 8 buckets (`arithmetic, earned, unearned, shelter, medical, hhcomp, depcare, sua`); rare codes are dropped, not redistributed by mechanism.

### Results

Real QC mass of the three rule areas (weighted):

| set | FY | variances | var share | case share | dollar share | mean $/case | status (over/under) |
|---|---|---|---|---|---|---|---|
| student (111) | 2020 | 55 | 0.56% | 0.72% | 1.73% | 125 | 35/20 |
| student (111) | 2021 | 14 | 0.35% | 0.45% | 0.98% | 135 | 8/6 |
| student (111) | 2022 | 47 | 0.29% | 0.38% | 0.91% | 151 | 25/22 |
| student (111) | 2023 | 61 | 0.36% | 0.46% | 1.24% | 190 | 29/32 |
| student (111) | 2024 | 80 | 0.45% | 0.60% | 1.44% | 183 | 58/22 |
| workrule (160–166) | 2020 | 21 | 0.17% | 0.22% | 0.58% | 136 | 11/10 |
| workrule (160–166) | 2021 | 7 | 0.09% | 0.11% | 0.26% | 145 | 3/4 |
| workrule (160–166) | 2022 | 30 | 0.19% | 0.25% | 0.72% | 183 | 13/17 |
| workrule (160–166) | 2023 | 20 | 0.10% | 0.13% | 0.26% | 139 | 12/8 |
| workrule (160–166) | 2024 | 46 | 0.17% | 0.22% | 0.53% | 184 | 33/12 |
| elderly_demo (810/820) | 2020 | 40 | 0.18% | 0.23% | 0.18% | 40 | 25/15 |
| elderly_demo (810/820) | 2021 | 11 | 0.12% | 0.15% | 0.09% | 37 | 6/5 |
| elderly_demo (810/820) | 2022 | 40 | 0.13% | 0.16% | 0.10% | 37 | 15/25 |
| elderly_demo (810/820) | 2023 | 18 | 0.10% | 0.13% | 0.13% | 75 | 12/6 |
| elderly_demo (810/820) | 2024 | 23 | 0.06% | 0.08% | 0.04% | 38 | 12/11 |

Notes: FY2021 covers Jul–Sep only, so its counts are small. FY2021 work-rule mass is depressed (nationwide ABAWD waivers). Student + work-rule variances are mostly binary eligibility flips — nature 7 "ineligible person included" (student: 55 of 80 in FY2024; work-rule: 23 of 46) and nature 6 "eligible person excluded" (20 and 19) — at ~$135–190/case.

Other unmodeled elements, FY2024 (context): citizenship 130 — 0.29% var / 0.93% dollar share; homeless shelter 362 — 0.13%/0.14%; disqualification 151 — 0.07%/0.29%; SSN 170 — 0.05%/0.17%; residency 140 — 0.02%/0.06%; transitional 530 — 0.04%/0.08%.

Synth side (20,000 cases, 8,789 variances): emitted elements are only 363, 331, 311, 364, 150, 365, 520, 323. **Zero** variances carry 111, 160–166, 810, or 820 — confirmed the generator produces none of them.

Calibration payoff (element-marginal L1; L1 = Σ|p_real − p_synth|, 0 = identical):
- Total L1, real FY2024 vs synth: **0.4917**
- Contribution of the three hypothesis sets: **0.0068** (1.4% of L1)
- Contribution of ALL unmodeled elements (incl. citizenship etc.): **0.0128** (2.6% of L1)

### Verdict
**Clean negative.** The generator indeed produces none of these codes, but the missing mass is not material:
1. **Student eligibility** — the largest of the three, and the only one above 1% on any metric (1.44% of FY2024 error dollars, declining from 1.73% in 2020). Still two orders of magnitude below what would move calibration.
2. **ABAWD/work rules** — ≤0.2% variance share, ≤0.7% dollar share in every FY; depressed further by waivers in FY2021. ABAWDs are ~4–9% of participants but generate almost no recorded QC variance mass.
3. **Elderly/disabled** — no dedicated element exists in the taxonomy; the elderly-tinged waiver elements (810/820) are negligible (0.04% of FY2024 dollars). The substantive elderly provisions the generator cares about (medical deduction 365, unit composition 150) are already modeled.

A perfect dedicated mechanism for all three areas would cut the element-marginal L1 by at most ~0.007 of 0.49 — i.e., calibration's problem is elsewhere (98.6% of the L1 sits in modeled-bucket share mismatches, not missing codes). No mechanism is warranted on calibration grounds; student-eligibility would rank first if one were ever built, on dollar share alone. Negative result, as data.

### Next steps
- None for these rule areas. If the element-marginal L1 is to move, the work is inside the 8 modeled buckets (share rebalancing), not new mechanisms.
- Caveat to record for the transfer gate: binary eligibility flips (nature 6/7 on persons) are structurally different from the income/deduction mechanics the generator does well — worth remembering if person-level errors ever matter downstream, but the mass doesn't justify it now.
- If the taxonomy ever gains an explicit elderly/disabled variance element (e.g., separate-household determinations split out of 150), re-run this audit; the current measurement can't isolate that channel.
