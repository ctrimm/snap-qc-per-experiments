# Experiment UT3: Utah SNAP QC error anatomy

**Date:** 2026-10-04 · **Code:** `experiments/ut3_ut_anatomy.py`
(microdata-only; read-only on the QC files)

## Hypothesis

Tied to the north star (state-conditioned synthetic training data for QC
error detection): Utah's process-failure fingerprint should differ from
the national mix in ways that explain the low payment error rate and that
the UT1 generator must reproduce. If UT's errors concentrate in
timing/verification (nature 97) rather than computation, the story stays
process-layer, consistent with a clean benefit engine (UT8c).

## Method

Utah (STATE=49) vs national across FY2022–2024 QC public-use files (UT
n=3,127 — the UT1 fit basis, per the NY6 lesson; the national comparison
is the same window). All rates FYWGT-weighted; primary variance slot 1.
Reports: finding mix, direction mix, dollar-error quantiles (AMTERR),
element/nature/cause mixes as UT-vs-national ratios, top
element×nature patterns in plain language, and FY trends within UT.

## Results

**Finding/direction:** UT finding correct/over/under 0.6677/0.1920/0.1403
(US 0.5988/0.2459/0.1553); case-error rate 0.3323 vs 0.4014 national.
p(over|err) 0.5778 vs 0.6129 — UT tilts slightly under relative to
national.

**Dollars:** UT errors are much smaller than national — p50 $22 vs $31,
p90 $99 vs $202, mean $42 vs $70; 85.5% ≤$56 vs 69.1%. Over-errors median
$25 (US $37); under-errors median $18 (US $23). No big-dollar tail (p90
$99) — the low-PER panel's small-error signature, same family as SD's
p90 $70.

**Element buckets (UT vs national ratios):** earned 1.24x, childsupport
1.40x, other 1.42x, standard 1.26x above; sua 0.56x, depcare 0.36x,
arithmetic 0.49x, hhcomp 0.63x below; shelter 1.03x, medical 1.09x,
unearned 0.85x near national. UT is wage-error heavy and sua-light — the
earned/sua split mirrors SD's (1.32x/0.67x) but milder.

**Nature:** timing-97 is 46.8% of UT variances vs 39.4% national (1.19x) —
timing-heavy, but far less extreme than SD's 1.8–3.1x. Notable: nature 99
(the "unknown/other" bucket) is 0.03x national (0.19% vs 5.6%) — UT codes
specific natures honestly, no cause-99 distortion (NY3's honest-coding
note applies to UT too). Non-codebook nature codes ~4% (same quirk class
as NY3).

**Cause:** client 1.56x, agency 0.75x, other 0.45x, no_fault 1.00x national.
UT's substantive errors are CLIENT-coded (unreported/underreported
income, missed deductions) — the opposite of SD's agency/no-fault coding
practice, and distinct from NY's no-fault=0.0 pattern only in degree (UT
also records zero no-fault on non-97 variances).

**Top element×nature patterns (plain language):**
1. earned×97 — wages, "not required to be reported or acted upon"
   (timing): 21.3% of UT error weight, 1.95x national. The single biggest
   pattern — wage timing.
2. shelter×97 — shelter deduction timing: 13.0%, 0.79x national.
3. shelter×53 — "deduction included that should not have been" (OVER):
   10.4%, 2.21x national. UT's most distinctive substantive pattern —
   shelter over-deductions.
4. unearned×97 — child support received, timing: 8.9%, 1.10x.
5. shelter×52 — "deduction that should have been included was not"
   (UNDER): 4.5%, 1.33x. Shelter errors cut both directions.

**FY trend (2022→2024):** case-error rate 0.345→0.319→~0.33 (stable);
finding mix stable; the earned share of errors holds ~0.34; no labeling
break visible (cause97-blank checked per-FY in UT6's stage 0b).

## Verdict

**Held — process-layer story.** UT's fingerprint is wage-timing errors
(earned×97 at 1.95x) plus bidirectional shelter-deduction errors
(53-over at 2.21x, 52-under at 1.33x), coded honestly (no 99-distortion)
and client-attributed (1.56x). Computation errors (arithmetic 0.49x) are
suppressed, corroborating the clean-engine premise UT8c tests directly.
The dollar anatomy — p90 $99, 85.5% ≤$56 — is the low-PER panel's
small-error signature: UT's errors are frequent enough to find (33.2%
case rate) but small, which is exactly the regime where the panel
question bites (does P(error)-alone beat dollar rankers when errors are
small?).

## Next steps

- The earned×97 / shelter×53 / shelter×52 patterns are the copilot
  attention order for the whitepaper: wage timing first, shelter
  deduction verification second.
- UT7's feature audit should show earned/shelter on top (cross-check).
  - **Done →** [UT7](ut7_feature_audit.md): UT7: PASS — clean-8 adopted; only leakage feature issued_benefit/RAWBEN, removal *improves* acc +0.021/macroF1 +0.017; top features (earned/shelter/unearned) match UT3's anato…
- The client-coding tilt (1.56x) vs SD's agency-coding is a panel
  contrast to name in the whitepaper's limitations.
