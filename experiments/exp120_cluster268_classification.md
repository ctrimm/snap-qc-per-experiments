## Experiment 120 — The +$268 cluster is mostly unreported earnings (the client side), with an agency minority
**Date:** 2026-11-03 · **Code:** `experiments/exp120_cluster268_classification.py` · **Results:** `experiments/exp120_results.json`

### Hypothesis

exp118 found 205 earnings cases whose issued benefit exceeded the
statutory prediction by exactly $268 — in 95.1% the full allotment was
issued where verified earnings implied the $23 minimum — and could not
split the cause: earnings the client never reported vs earnings the
agency had and failed to act on. Claim: the QC file itself records the
split. Every reviewed case carries up to nine variances coded by
ELEMENT (what), NATURE (how), and AGENCY (responsibility — the column
is literally named `AGENCY`), and exp118 already showed the reviewer's
corrected benefit (`BENFIX`) agrees with the statutory prediction in
99.5% of cluster cases, so a coded finding should exist for nearly
every one.

### Method

The exp118 frame (mainland+DC, sizes 1–4, earnings > 0, non-CAP,
complete: 9,690 cases), the statutory prediction recomputed exactly as
in exp118, cluster = issued `RAWBEN` − prediction = $268 exactly
(n = 205). For the cluster and for a comparison set (all other frame
cases where `BENFIX` ≠ `RAWBEN`, i.e. ordinary QC error cases,
n = 5,354): per case, read `ELEMENT1–9` / `NATURE1–9` / `AGENCY1–9`,
bucket elements and causes with the repo's codebook maps (agency =
cause codes 10–25, client = 1–4, per exp15's convention), and tally
first-variance and all-variance distributions.

### Results

- **The cluster is coded, almost to a case.** 204 of 205 cluster cases
  (99.5%) carry at least one recorded variance (mean 1.43 per case),
  and the median `AMTERR` in the cluster is exactly $268 — the
  reviewers found this specific error, at this specific size, in
  essentially every case. (Ordinary error cases carry a variance only
  ~86% of the time.)
- **First variance: earned income, 192 of 205 (93.7%).** The finding
  is about earnings in nearly every case; the remaining first
  variances are unearned income (4) and household composition (4).
- **First variance, by responsibility: client 170 (82.9%), agency 34
  (16.6%), other/no-fault 0.** Counting all variances rather than the
  first: client 217, agency 75, other/no-fault 2. The dominant single
  nature code is "unreported source of income" (139 variances),
  followed by nature 39, "employment status changed from unemployed
  to employed" (38) — a household member started a job and the
  earnings never entered the budget — and nature 29, "exceeds
  prescribed limit" (18).
- **The comparison set looks nothing like this.** Ordinary error
  cases split agency 32% / client 28% / other-or-no-fault 26% /
  unrecorded 14% on the first variance, and their modal nature is the
  no-fault "not required to be reported or acted upon" (2,880
  variances). The +$268 cluster is not a sample of ordinary error; it
  is a specific failure mode with a specific responsible side.

### Verdict

exp118's open question is answered, with the split quantified:
roughly **five-sixths client-side** — earnings that existed, were
verified at review, and had never been reported (nature 35/39
dominant) — and roughly **one-sixth agency-side** (34 cases whose
first variance is an agency cause: reported information disregarded,
policy misapplied, or follow-up not done). The policy read differs by
side and the file supports both: the client share is a reporting/
verification problem (the earnings were real and countable), and the
agency share — 34 cases at a median $268 — is the part a caseworker
tool could plausibly have caught, because the information was already
in the agency's hands. What this experiment cannot do is split the
client share further (never reported vs reported late vs reported to
a channel that did not reach the budget); the variance codes do not
carry that distinction.

### Next steps

- None queued for this cluster. The classification method (cluster by
  residual, then read the variance codes) is reusable for any future
  residual cluster this line finds.

## Repository note (2026-11-03)

This experiment lives in two repositories: **ctrimm/snap-qc-per-experiments**
(`experiments/`, the canonical home) and **ctrimm/weight-space-programming**
(`experiments/`, mirrored), as part of the formula-recovery line that runs
exp116 → exp117 → exp118/exp119 → exp120–exp122. The QC data it reads is
in neither repo; it lives in the project's snap-qc-data store (FY2024
public-use file). If you extend this line (exp123+), work in
snap-qc-per-experiments and re-mirror to weight-space-programming, or
update both copies.
