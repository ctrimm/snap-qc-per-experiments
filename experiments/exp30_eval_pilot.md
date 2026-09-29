# Experiment 30 — QC-variance eval pilot

**Date:** 2026-09-29 · **Code:** `experiments/eval_pilot/` (`sample.py`, `labels.py`, `run_lm.py`, `score.py`, `baselines.json`, `README.md`)

### Hypothesis

A real-data QC-variance eval discriminates QC competence: a domain-tuned small LM should beat most-frequent baselines by a margin the pilot can measure, and the pilot itself should be runnable end-to-end with zero dependence on raw microdata. This moves the north-star gate that the planned 1.5–4B domain model must clear before we trust its QC-review judgment.

### Method

- **Labels** (`labels.py`): deterministic, never-trained label pipeline over real QC public-use files (FY2021–2024). Case id = `(STATE, YRMONTH, HHLDNO)` hashed to sha256[:32]. Reportable variance = ELEMENT recorded AND AMOUNT>0; primary = largest |AMOUNT|, tie-break lowest index. T1 = STATUS≠1 (not "≥1 variance", because 8,053 FY2024 error cases have no AMOUNT>0 variance). T2 = STATUS finding. T3/T4/T5 from the primary (element bucket / nature / cause bucket from `src/synth/codebook.py`); T4 defined only when the primary's nature code is one of the 12 standard codes (35/37/38/44/52/53/54/56/57/97/98/99); 16.6% of primaries carry non-12 nature codes (64, 39, 41, 7, 12…) and fall out of T4 only. T6 = signed AMTERR (+over/−under/0 correct).
- **Input rendering** (deterministic, two views): AGENCY VIEW = reported/agency fields, VERIFICATION VIEW = QC-verified fields. Leakage exclusions enforced: STATUS, AMTERR, ELEMENT*/NATURE*/AGENCY*/DISCOV*/E_FINDG, RAWBEN never appear; classification view sees no benefit amounts; dollar view sees FSBEN only. AMOUNT=0 tolerance variances never enter input text. Verified zero leak violations across all 1,400 sampled items.
- **Sampling** (`sample.py`, seed 30): test_main 1,000 (FY21–23), test_2024 200 (FY24 held-out-year), dev 200 (FY21–23, few-shot examples only). Per-bucket quota up to 50/item-type with nature-97 top-up ≥40 in test; per-state cap 10%.
- **LM runner** (`run_lm.py`): two prompts per item (classification T1–T5 MCQ + dollar T6 free-form integer), zero/few × jargon/plain conditions, `QC_EVAL_BASE_URL` (default `http://localhost:1234/v1`) + `QC_EVAL_MODEL`, resume-safe, `--dry-run` verified. items.json ships de-identified input fields — the Mac run needs no raw data.
- **Scoring** (`score.py`): per-task primaries — macro-F1 for T1–T5 (T4/T5 over applicable items), T6 direction accuracy + band/MAE/exact-match secondaries. Composite = mean of dummy-normalized gains vs the most-frequent dummy, capped to ceiling targets (T2 0.832, T3 0.422 real→real; 1.0 elsewhere, flagged provisional). Promotion gate: tuned beats base on composite (95% CI excludes 0) AND ≥4/6 task wins AND T3 macro-F1 ≥ 0.214 (50% of the 0.422 ceiling) — paired bootstrap, 10k resamples, stdlib only, ~1m45s for 1,200 items.
- **Sandbox has no local LM** (no torch/transformers/ollama/LM Studio), so the LM side is packaged for Cory's Mac Studio (zero-questions README). All runnable parts were run here: sampler, labels, dummy baselines, parser round-trips, perfect-model gate check.

### Results

Sampling — actual vs plan (all quotas hit except rare-bucket pools, taken in full):

| split | correct | over | under | n |
|---|---|---|---|---|
| test_main | 333 | 375 | 292 | 1000 |
| test_2024 | 67 | 75 | 58 | 200 |
| dev | 67 | 75 | 58 | 200 |

Per-bucket counts in test (main+2024): earned 74, unearned 67, depcare 59, shelter 78, sua 59, medical 60, childsupport 59, hhcomp 61, **assets 4, reporting 19, income_total 15** (take-all — pools exhausted), other 62. nature97 dedicated cut: 121. Max state share 6.1% (cap 10%).

Most-frequent baselines on the 1,200 test items:

| task | primary (macro-F1 / dir-acc) | n |
|---|---|---|
| T1 | 0.400 | 1200 |
| T2 | 0.182 | 1200 |
| T3 | 0.014 | 733 |
| T4 | 0.036 | 718 |
| T5 | 0.170 | 733 |
| T6 | 0.333 | 1200 |
| composite | 0.000 | — |

End-to-end smoke (perfect predictions vs dummy, real bootstrap): composite diff +0.995 [+0.980,+1.000], wins 6/6, T3 1.000 ≥ 0.214 → gate PASS. Parser gold round-trip 700/700.

Empirical side-findings (for the open design questions):

- **Q2 (primary rule):** largest-dollar vs first-recorded agreement = 0.677 on multi-reportable test items (n=130); was 0.855 on unweighted FY2022. Kept largest-dollar (it defines the label the eval scores against; the agreement number is the documented alternative).
- **Q5 (FY2024):** kept the 200-item FY2024 cut as a separately-reported split — year-shift is exactly what we want to detect.
- **Q6 (conditions):** runner supports all four (zero/few × jargon/plain); keep the one with best discrimination vs dummy, not highest absolute score.
- **Q7 (format):** MCQ for T1–T5, free-form integer for T6; one classification prompt + one dollar prompt per item.
- Dollar-error calibration (Q4 input): test p50 $36, p90 $195, p99 $493, max $1,190; T6 bands provisional, flagged for human-label calibration.

### Verdict

Hypothesis partially confirmed: the pilot package is delivered, baselines are green (dummy composite = 0.000 by construction; perfect model → 1.000, gate passes), and the whole pipeline runs without raw data on the Mac side. LM discrimination itself is **pending** — no LM runs exist yet. I claim nothing unrun.

### Next steps

1. **Mac Studio LM run** (the blocker): 4 base conditions (~1.5–2.5h each) + tuned run per `experiments/eval_pilot/README.md`.
2. Human label audit (Q1) on a dev-set sample before trusting T3/T4/T5 taxonomy labels as ground truth.
3. T6 band calibration (Q4) against auditor judgments.
4. Then exp31: train the 1.5–4B domain model candidate and put it through this gate.
