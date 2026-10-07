# Experiment 8b — rules-recovery parameter fitting: what benefit formula does the agency fleet actually run?
**Date:** 2026-09-29 · **Code:** `experiments/exp8b_parameter_fitting.py`
(fitted aggregates in `experiments/exp8b_fitted_params.json`) · **Data:**
`snap-qc-data/raw/` (beside the repo checkout) FY2024 public-use file (read-only; nothing
from the microdata is written into the repo)

## Hypothesis
The production eligibility engines' effective benefit-formula parameters can
be recovered by fitting the statutory benefit formula to (facts → RAWBEN)
pairs, and deviations from published FY2024 statute flag candidate engine
misconfigurations. Ties to the north star two ways: (1) the rules-recovery
thread supports the Deloitte IE&E API-discovery goal — behavioral
reverse-engineering of production eligibility engines from observed data;
(2) if the real agency fleet systematically deviated from statute, the
synthetic generator's benefit calculator (`benefit.py`, audited against
statute in exp10) would carry a systematic bias versus real cases, which
matters for the transfer gate. Plain terms: we check whether the benefits
states actually paid look like they came out of the FY2024 rulebook, and if
not, where the rulebook and the machines disagree.

Terms: *fitting* = choosing parameter values that make the formula's
predictions match the observed RAWBEN as closely as possible. *OLS slope*
= the straight-line fit of (max allotment − benefit) against net income;
its slope is the effective 30%-rate. *Holdout* = cases the fit never saw,
used to test whether the fitted parameters generalize. *Point mass* = many
cases landing on exactly the same value (here, the shelter cap).

## Method
1. Loaded the FY2024 file, kept contiguous US + DC (48 states + DC; AK/HI/
   Guam/VI run on their own COLA tables), n = 43,299.
2. Built the exp8a cleaned observation set: keep STATUS=1 with
   RAWBEN==FSBEN (23,392) plus STATUS 2/3 where RAWBEN = FSBEN ± AMTERR
   within $1 (15,658); drop recoupment-type rows (STATUS=1, RAWBEN≠FSBEN,
   no variance, diff>$1: 1,712) and reporting anomalies
   (|FSBEN−RAWBEN| exceeding AMTERR by >$1: 3,206). Cleaned n = 39,050
   (90.2%). Split 50/50 train/holdout, seed 7.
3. Key design choice (learned the hard way in a first draft): the
   benefit-relevant household size is **not** RAWHSIZE — the reported size
   matches the benefit actually paid only 85% of the time. QC's BENMAX
   field implies the effective size exactly (agrees with FSUSIZE 99.8%),
   and on STATUS=1 rows agency and QC used the same size. All output-side
   fits use BENMAX directly, never a size mapping. Also excluded MN/MFIP
   (50% earnings disregard, no other deductions) and SSI-CAP
   standard-benefit cases from the deduction-identity fits.
4. Fitted on train, using the **reported (Origin=R) fields as the engine's
   inputs** — RAWGROSS, RAWERND, RAWNET, SHELDED, FSDEPDED, FSMEDEXP,
   FSCSDED — against RAWBEN as the engine's output, on rows where QC
   verified every input (STATUS=1, RAWBEN==FSBEN):
   - max allotments: median RAWBEN at RAWNET==0, by BENMAX;
   - 30% rate: OLS slope of (BENMAX−RAWBEN) on RAWNET on interior rows
     (benefit strictly between min and max), plus which rounding of the
     0.3×net product (ceil/round/floor) matches best;
   - minimum benefit: mode of RAWBEN for 1–2 person units where the
     formula predicts <$23;
   - earned-income disregard: median(RAWERND/FSEARN), plus its rounding;
   - standard deduction: residual of the reported net identity
     (net = gross − earned_ded − std − med − depcare − childsupport −
     shelter), median by size;
   - medical deduction: recorded FSMEDEXP vs the identity-implied
     deduction (the $35 threshold itself is netted out of the file — see
     below);
   - shelter cap: point mass of SHELDED at the cap for
     non-elderly/disabled households (restricted to RAWNET>0 so the cap
     binds materially), vs elderly/disabled (waiver);
   - SUA: not fitted — state-set, no single national value exists.
5. Misconfiguration scan: per-state OLS slope of the 30% rate (22 states
   with n≥50 interior clean rows); any state >0.02 off 0.30 gets flagged.
6. Holdout: predict RAWBEN from (BENMAX, RAWNET) with fitted vs statutory
   parameters, on clean rows and on error rows separately.

## Results
Every recoverable parameter matches FY2024 statute. Deviations are zero
or sub-rounding noise:

| Parameter | Fitted | Statutory (FY2024) | Deviation | Material? (> $1) |
|---|---|---|---|---|
| Max allotment, HH1–6 | 291/535/766/973/1155/1386 | same | 0 | no |
| Max allotment, HH7–8 / +person | n<30 at zero net | 1532/1751, +219 | unidentifiable (small n) | n/a |
| 30% benefit rate | 0.2995 | 0.30 | 0.0005 | no |
| 0.3×net rounding | ceil (95.7% exact) | round product up (FNS rule) | 0 | no |
| Minimum benefit (1–2 person) | $23 (mode share 1.000, n=1309) | $23 | 0 | no |
| Earned-income disregard | 0.2000 (n=1744) | 20% | 0 | no |
| Earned-deduction rounding | round() (95.8% exact) | — (unstated) | — | no |
| Standard deduction HH1–3/4/5/6+ | 198/198/208/244/279 (93.5–95.2% within $1) | same | 0 | no |
| Medical $35 threshold | **unidentifiable** — file records the post-threshold deduction | $35 | n/a | n/a |
| Shelter cap | point mass at $672 (43.8% of non-eld/dis recipients exactly at cap) | $672 | 0 | no |
| Cap waiver (eld/dis) | confirmed (max $2,230; 16.8% >$672) | waived | 0 | no |
| Homeless shelter deduction | $180 (100%, n=36) | $179.66 (recorded $180) | 0 | no |
| SUA tiers/values | **unidentifiable nationally** — state-set (tech doc Table F.7) | state-set | n/a | n/a |

- **Per-state 30% scan:** 22 states scanned, slopes 0.292–0.301, **zero
  states deviate >0.02 from 0.30.** No candidate engine misconfiguration
  anywhere in the scanned states.
- **Holdout (clean rows, n=9,864):** statutory formula
  (BENMAX − ceil(0.3×RAWNET), $23 floor for 1–2 person) predicts RAWBEN
  **98.58% exact, 99.24% within $1, MAE $1.41**. The *fitted* parameters do
  slightly worse (90.3% exact) — the fitted 0.2995 vs true 0.30 is pure
  noise, and ceil() amplifies it. The residual tail (75 cases >$1) is
  first-month prorated benefits (RAWNET=0, RAWBEN<max), not a parameter
  issue.
- **Holdout (error rows, n=7,701):** 0.7–1.9% exact, MAE ≈ $64. The
  formula on reported inputs does *not* reproduce RAWBEN for error cases —
  i.e. **the public-use file does not carry the agency's actual
  computation inputs when the agency erred** (the R fields are
  reviewer-verified values; the wrong inputs the engine used are
  unobserved).
- **Two flagged anomalies (not national deviations):**
  1. 103 cleaned cases (0.26%), concentrated in six New England states
     (CT/ME/MA/NH/NY/RI), record SHELDED > $672 with the uncapped value
     entering the net-income identity 1:1 — the cap did not bind in the
     recorded computation. 65% are error rows; 17–36 are QC-agreed.
     Either a recording convention in those states' QC extracts or genuine
     cap non-application. Worth a follow-up, not a national finding.
  2. ~5% tail on the standard-deduction residual is largely the
     child-support-paid deduction (FSCSDED), which has no unit-level
     field in older docs but exists in the file; including it lifts
     within-$1 agreement to 95.7%. Remainder is small recording noise.

## Verdict
Hypothesis **held in the weak sense, blocked in the strong sense.** The
effective parameters of the national agency fleet are recoverable from
(facts → RAWBEN) pairs and they match FY2024 statute essentially exactly —
no misconfiguration signal at the national level or in any of the 22
scanned states. For the north star this is good news for the transfer
gate: the generator's statutory benefit calculator is a faithful model of
real engine behavior; synthetic cases carry no systematic formula bias.

But the stronger ambition — behaviorally reverse-engineering *which*
engines deviate, for the Deloitte IE&E API-discovery thread — hits two
walls in the public-use file: (1) the agency's true computation inputs are
unobservable on exactly the cases where they'd be informative (error
rows carry reviewer-verified values, not what the engine saw); (2) the
file carries no engine/vendor identifier, so even a detected deviation
could not be attributed to a system. Rules-recovery from QC public-use
data can audit the *fleet* against statute (done here: clean); it cannot
fingerprint individual engines. That needs case-level pre-QC records or
per-state engine identification — both outside this file.

Also recorded for the record: the benefit formula rounds the 0.3×net
product **up** (ceil, 95.7% exact — matches the FNS rule as exp10 noted),
and the earned-income deduction rounds to nearest (95.8%), not down.

## Next steps
1. (Recommended for the thread) **Exp8c — PA fitting:** rerun this script's
   machinery on PA (STATE=42, n=3,268) and compare against PA's FY2024 SUA
   and policy docs; the national script already handles the size/BENMAX
   subtlety. The New England uncapped-shelter cluster is the one concrete
   anomaly to chase — check whether PA shows anything similar.
   - **Done →** [exp8c](exp8c_pa_deviations.md): PA fit: every parameter equals statute every FY; statutory formula predicts RAWBEN 99.7–100%.
2. Per-state max-allotment check (complement to the rate scan): median
   RAWBEN at RAWNET==0 by state×BENMAX would catch a state running last
   year's COLA table; needs n≥30 per cell, so only large states qualify.
3. Do not attempt deduction-parameter fitting on STATUS 2/3 rows from this
   file — the inputs are reviewer-verified, not the engine's (holdout MAE
   $64 proves it).
4. If the Deloitte thread needs true engine fingerprinting, the next data
   source is pre-QC case records (agency inputs as the engine saw them),
   not the public-use file.
