# Cross-comparison: NY POC track vs NY OTDA targeting draft

**Date:** 2026-09-29
**Our side:** NY1–NY8 + NY8c experiment chain and `whitepaper/ny_pilot_whitepaper.html`
(`ctrimm/snap-qc-per-experiments`, private research repo).
**Their side:** "Targeting SNAP payment errors in New York" — draft for internal
review (not for distribution), prepared for the NY State Office of Temporary and
Disability Assistance by Nava PBC with analytical methods from the Better
Government Lab (Georgetown / Michigan), September 2026. Interpretive
threshold-rule approach: plain-language rules mined on FY2022–23 public QC data,
tested one year ahead on FY2024 NY cases.

Two independent methods reaching the same conclusions is converging evidence.
This note records where they agree, what each side adds, and the one genuine
tension.

## Agreements

- **Dollars live in income errors; frequency lives in shelter.** Draft (NY
  FY2022–24): wages/salaries 24% of errors by count but 41% of error dollars;
  shelter deduction 28% of errors but 11% of dollars. NY5 found the same
  structure from the other direction: ranking by P(error) alone recovers *fewer*
  dollars than random (0.74x at top-10%) because probability chases frequent
  small shelter/timing errors while dollars sit in income errors.
- **Targeting beats random by a similar margin.** Draft rules: 30% precision vs
  15% base rate (~2.0x yield) at 10% review volume, reaching 20% of visible
  error dollars. NY4 ranker: precision@10% 0.51, lift 1.40x. Different methods,
  same neighborhood. (Caveat: different test sets and base rates — see below.)
- **The invisible-errors gap, measured two ways.** Draft: ~62% of NY's error
  cases are visible in public data (ineligible determinations excluded). NY
  track: microdata implies an 8.54% error rate vs FNS-published 12.68%
  (≈67% visible). Same gap, independent measurement.
- **Timing is NY's process failure.** Draft rules lean on months-since-
  certification and benefit-at-maximum ingredients. NY3: nature-97 timing errors
  at 62% of NY errors, 1.56x the national rate.
- **Small samples, honestly flagged.** Draft: 67 flagged cases at 10% volume
  (precision SE ≈ ±0.06). NY track uses 3,257 NY cases FY2020–2024 with fixed
  holdout indices and flags the rare-tail weakness explicitly.

## What our track adds to the draft

- **Staleness bound (NY6).** The draft's limitation #2 (data ends FY2024, rules
  trained through FY2023) is real but bounded: refit-on-2020–22 beats pooled
  training on held-out 2023–24, and no annual refit was needed. The signal is
  year-to-year stable.
- **Engine cleanliness (NY8c).** NY's benefit-calculation engine matches statute
  94–98% — errors are process-layer. This strengthens the draft's "careful
  handling inside existing review" framing: no eligibility-system fix required.
- **Medical-tail blind spot.** NY's distinctive errors sit in the rare tail
  (medical 1.79x national, SUA 1.51x); the draft's element table doesn't list
  medical and its rules are earned-income-dominant. Correct priority for
  dollars, but the medical tail deserves a look — and our generator can't place
  it either (NY2 element leg: MIXED).

## What the draft adds to our track

- **A true prospective test.** Train FY2022–23, test one year ahead on FY2024 —
  the more deployment-honest design. Our NY2/NY5 use a random pooled
  FY2020–2024 holdout, and NY6 itself shows pooled training is worse than
  refit-on-old for forward generalization. Some of the gap between their 2.0x
  yield and our 1.4x precision lift may be our holdout flattering the ranker.
- **The certification-origin discount (0.49).** Only ~half of flagged errors
  arise at certification, which is what their prevention lever can touch. Our
  detection framing doesn't need this discount, but any prevention claim built
  on our numbers would.
- **Operational honesty on staff time.** The draft refuses to quote hours it
  can't measure (reports errors per 1,000 reviews: 146 random vs 299 targeted).
  Our $85/hr vs $56/hr rests on a 30-min/review assumption — documented, but an
  assumption.

## The tension: optimistic read vs planning read of the same reality

Both tracks work the same visible-only microdata (eligible households paid the
wrong amount; ineligible determinations absent from both). The draft then
applies three discounts to its payment-error-rate forecast (ceiling −2.7 pts →
mid −1.3 pts → conservative −0.3 pts at 10% volume, off a 13.18% FY2025 base):

1. **0.49 (arises at certification)** — prevention-specific. Correct for their
   lever; does not apply to a review ranker, which finds errors wherever they
   arose.
2. **0.37 (findable from the case record)** — should apply to *both*, currently
   only to theirs. Our ranker uses nine agency-view features; live, it can't see
   unreported income either. Our 30.4%-of-dollars figure is retrospective on
   QC-labeled cases, so the simulation never penalizes the model for errors no
   case-record model could find.
3. **0.62 (visible share)** — they apply it as an explicit haircut; our
   whitepaper states it as a caveat while the headline $85/hr runs undiscounted.

Further wrinkles: the 0.49 × 0.37 product assumes independence, but
certification-origin errors are disproportionately case-record-visible, so the
conservative band likely over-discounts. And their −2.7 pt ceiling treats every
prevented dollar equally, while our 68/32 over/under split says ~a third of
found dollars are under-issuances — correcting those cuts the error rate but
*costs* money (make-whole) rather than saving it.

## Recommendation

Reconcile on one shared test set: run both the threshold rules and the ranker
on the same FY2024 holdout; report precision lift *and* dollar lift for each;
apply the 0.37 findability discount to the ranker's dollar figure; keep the
0.49 certification-origin discount on the prevention story only. One number for
OTDA instead of two numbers that look comparable and aren't.
