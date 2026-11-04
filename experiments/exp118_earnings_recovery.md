## Experiment 118 — Earnings cases: the parameters hold, the facts do not
**Date:** 2026-11-03 · **Code:** `experiments/exp118_earnings_recovery.py` · **Results:** `experiments/exp118_results.json`

### Hypothesis

exp117 found the issued function running statutory parameters on the
no-earnings slice ($198 / 0.30, 61.6% exact). Earnings cases are where
that could break: the 20% earned-income deduction might be applied
differently in production, and earnings are the most volatile fact in
the file. Claim: the effective earned treatment recovered from issued
benefits (`RAWBEN`) will match the statutory treatment (20%, and a
standard deduction of $198), while the exact-match share falls well
below exp117's — because the deviation is in the earnings facts, not
the formula. Adjacent prior work: exp27 audited earned-income error
mechanics on the generator side; this is the real-data counterpart.

### Method

FY2024 QC public file, mainland + DC, sizes 1–4, `FSEARN > 0`,
non-CAP, complete fields: 9,690 cases. Same statutory prediction as
exp117, now including each case's `FSERNDED`. T1 vs the minimodel
(`FSBEN`), T2 vs corrected (`BENFIX`), T3 vs issued (`RAWBEN`).
Joint fit of (standard deduction, earned-deduction structure) on the
2,440-case sub-slice with no other deductions: structure candidates
`floor(r·E)` and smooth `r·E`, r ∈ 0.10–0.30, fit against all three
targets with `FSBEN` as control.

### Results

| Test | Exact | Weighted | Over / under |
|---|---|---|---|
| T1 pred vs FSBEN | **99.85%** | 99.90% | 0.15% / 0.0% |
| T2 pred vs BENFIX | 79.68% | 78.80% | 10.5% / 9.8% |
| T3 pred vs RAWBEN | **37.0%** | 36.2% | **40.0% / 23.0%** |

- Earnings cases deviate far more than no-earnings cases (37.0% vs
  61.6% exact) and asymmetrically toward overissuance. Per-state T3
  exact ranges from 18.7% (Illinois) to 46.4% (Iowa).
- **The modal residual is a fingerprint: +$268, in 205 cases.** 195 of
  them are size-1; in 95.1% the household was issued the *full*
  allotment ($291) while the statutory prediction, from QC-verified
  earnings (median $2,752/month in this cluster), is the $23 minimum —
  hence 291 − 23 = 268. The minimodel agrees with the prediction in
  100% of these cases and the corrected benefit in 99.5%: QC treats
  them as overissuances in which the earnings effectively never
  reached the issued benefit. They are spread across states (IL 21,
  DC 20, MA 17, NY 11 are the largest counts), not one state's defect.
  Whether the cause is unreported earnings or agency failure to act
  is a variance-code question the fields used here cannot answer.
- **Fits:**

| Target | Std | Earned structure | Rate | Match |
|---|---|---|---|---|
| FSBEN (control) | $198 | **floor** | 0.20 | 81.8% (smooth runner-up 77.9%) |
| BENFIX | $198 | smooth* | 0.20 | 70.8% |
| RAWBEN | $198 | smooth* | 0.20 | 32.3% (floor 31.6%) |

  *At RAWBEN/BENFIX noise levels the floor-vs-smooth distinction
  (worth at most $0.30 of benefit) is below the noise floor; the two
  are statistically indistinguishable there. On the minimodel's own
  outputs the staircase wins clearly — the same structure exp116
  recovered from the synth oracle, now confirmed in real minimodel
  data. The parameters — $198 and 20% — are recovered identically
  from every target.

- The +$54 minimodel residual cluster from exp117 recurs (9 cases
  here, 28 there). Still unexplained; now clearly a persistent
  minimodel-side treatment, not a slice artifact.

### Verdict

Hypothesis holds. With earnings in play, the issued function still
runs the statutory parameters — $198 standard deduction, 20% earned
deduction — and the earned staircase is real in the minimodel. What
changes is the deviation surface: bigger, asymmetric toward
overissuance, and dominated by cases where earnings never made it
into the issued benefit at all. Combined with exp117, the picture
across both slices is consistent: **the formula layer is not where
SNAP payment error lives; the fact layer is, and earnings facts are
the worst of it.**

Scope: sizes 1–4, FY2024, mainland; deductions conditioned on the
minimodel's calculated fields as in exp117; mid-period reporting
rules mean some issued benefits lawfully rest on older facts, which
is one reason the corrected benefit (T2, 79.7%) — not the raw issued
benefit — is the cleaner error measure, and why the +$268 cluster's
BENFIX agreement (99.5% corrected to the prediction) matters: those
are not the lawful-staleness cases.

### Next steps

- Classify the +$268 cluster with the file's variance fields
  (element / nature / cause): unreported earnings vs agency failure
  to act is the policy-relevant split, and the fields exist.
- Identify the +$54 minimodel treatment (37 cases across exp117/118
  now) — the one place the reconstruction is not exact.
- exp119 covers the territory tables this frame excludes.

## Repository note (2026-11-03)

This experiment lives in two repositories: **ctrimm/snap-qc-per-experiments**
(`experiments/`, the canonical home) and **ctrimm/weight-space-programming**
(`experiments/`, mirrored), as part of the formula-recovery line that runs
exp116 → exp117 → exp118/exp119. The QC data it reads is in neither repo;
it lives in the project's snap-qc-data store (FY2024 public-use file).
If you extend this line (exp120+), work in snap-qc-per-experiments and
re-mirror to weight-space-programming, or update both copies.
