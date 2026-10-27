# Experiment 115 — the synthetic generator against what exp106–exp113 established (audit)

**Date:** 2026-10-27 · **Type:** descriptive audit, no model fitting and no decision rule; findings feed proposals below · **Code:** `exp115_generator_audit.py` · **Results:** `exp115_results.json`

### Why

Since the generator was last calibrated (exp1–exp55), four things have been established:
1. **The public file's "reported" fields are the reviewer's values.** For error cases they hold the corrected facts (exp106).
2. **The target that matters is the official error.** That is an error the reviewer found with an amount over the federal tolerance, about 12% of cases. Not any error, which is about 38% (exp110, exp112).
3. **The issued-vs-correct benefit gap is not a reliable label.** About 30% of over-tolerance gaps contradict the reviewer's recorded amount (exp112).
4. **Rebuilt pre-review values exist.** giannella/snap_qc's frame (exp109, exp113) gives the first real-data view of what the agency had before review.

**The question:** does the generator match this understanding, and which of the work built on it assumed otherwise?

### How the generator is built (unchanged since exp55)

- **Two views per case:** `facts` (the truth, calibrated to the verified `FS*` fields: FSEARN medians, FSNELDER/FSNDIS shares, …) and `issued_facts` (what the agency budgeted on, the truth with injected errors). Each case also carries `correct_benefit`, `issued_benefit`, `dollar_error`, `finding` (any error) and `variances`.
- **Calibration targets** come from FY2024: the any-error rate 0.397 (STATUS 2/3), direction, and the bucket, nature and cause mix (`dist.json`; `dist_reportable.json` uses AMOUNT > 0 variances, exp55). There's also a dollar check, the share of errors at or under $56 (exp31).

### Results (FY2024, errors over $56; synthetic: 20,000 cases, seed 7, default settings)

| | Public file (RAW* vs FS*) | Rebuilt pre-review (giannella) vs FS* | **Synthetic** (issued vs truth) |
|---|---|---|---|
| Share of cases with an official error | 12.1% | — | **11.8%** |
| … among earner households / others | 22.6% / 8.2% | — | 20.2% / 9.0% |
| Overpaid share | 71.9% | — | 75.2% |
| Error dollars: median / 75th / 90th percentile | $141 / $237 / $348 | — | **$128 / $202 / $268** |
| Agency gross income equals verified | 88.6% | 45.5% | **47.3%** |
| Agency net income equals verified | 55.6% | 9.8% | 17.5% |
| Agency shelter deduction equals verified | 80.5% | 30.2% | 39.0% |
| Gross, net and household size all equal (exp52's measure) | 52.2% | **6.6%** | **10.1%** |

*(Public-file equality here counts a blank field as $0. Counting only non-blank fields, as exp106 did, gives the 98.9% / 86.0% / 91.9% figures quoted there.)*

### Findings

1. **The generator's core design matches reality, better than the public file does.**
   - **Its agency view is a real pre-review view.** It sits next to giannella's independently rebuilt values (gross equal in 47% against 46%), not next to the public file's reviewer-filled fields (89%).
   - **The generator never had our leak.** Its issued benefit is computed from the agency view, so the two always agree.
   - **The official-error rate already matches without being targeted:** 11.8% against 12.1%, with the right earner gradient.
2. **The view-identity calibration in exp52 points the wrong way for deployment.**
   - **What it did:** exp52 copies verified values into the agency view for enough synthetic error cases to reach the public file's ~54% identity. Unmodified, the generator gives about 10%; the rebuilt reality is 6.6%.
   - **Where that's right:** a language model evaluated on public-file cases.
   - **Where it's wrong:** it teaches the model that error cases usually look clean. A state's own records show the differences.
   - **The fix:** the QC language model (exp52, exp59, exp71 and the distilled flag-card models) should get a variant trained without it, or calibrated to rebuilt rates. It should also be evaluated on rebuilt-view records.
3. **Earlier generator-vs-real comparisons used the public file's reviewer-filled fields as "real agency" values.** These include the transfer probes (exp2–exp43), the discriminator (exp35: AUC 0.98, "the shelter deduction is the biggest giveaway") and the joint-distribution checks (exp39, exp44).
   - **Part of the gap was the comparison target.** Shelter, for example, is equal in 39% of synthetic error cases and 30% of rebuilt ones, against 81% in the public file.
   - **Those results aren't wrong about the generator's truth view.** But they likely overstate how unrealistic its agency view is.
4. **Two real gaps remain against rebuilt reality:**
   - **Errors leave net income and shelter untouched too often:** net equal in 17.5% against 9.8%, shelter 39% against 30%. Fewer synthetic errors change the deduction chain.
   - **The over-tolerance dollar tail is too thin:** the 90th percentile is $268 against $348. That matters now that the cost share counts over-tolerance dollars.
5. **The case label is still "any error."** `finding` is any error. Over-tolerance is derivable from `dollar_error`, but it isn't a recorded label or a tracked calibration target.

### Proposals (each a separate pre-registered experiment)

| # | Proposal | Measures |
|---|---|---|
| A | Add `official_error` (|dollar_error| > the year's tolerance) to every synthetic record, and track the official rate and over-tolerance dollar quantiles as calibration metrics | rate 11.8% vs 12.1%; p90 $268 vs $348 |
| B | Calibrate injection magnitudes per element against rebuilt pre-review deltas (rebuilt value minus FS*, by error element), not just the dollar error | net- and shelter-identity gaps; dollar tail |
| C | Re-run the exp35 discriminator and exp39/exp44 joint checks with the rebuilt frame as "real" | whether the 0.98 AUC and the shelter giveaway survive a fair comparison |
| D | QC language model: a training variant with no view-identity copying (or calibrated to the rebuilt 6.6%), evaluated on rebuilt-view real records beside the public-file eval | which one a deployment should use |
| E | (After B and C) retest synthetic-to-real transfer with rebuilt real records as the target | whether the synthetic data carries more real signal than the public-file probes showed |

**Not proposed:** changing the truth view, which is calibrated to the verified fields and is right as is.
