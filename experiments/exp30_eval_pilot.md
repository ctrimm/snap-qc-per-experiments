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

### Results — Mac Studio base-model run (2026-10-02 → 10-04)

`google/gemma-4-31b` (dense) via LM Studio, temperature 0, `max_tokens` 400 (runner default), all four conditions on the 1,200 test items; 41 h wall (11–19 s/prompt vs the 2–4 s estimate). Predictions: `experiments/eval_pilot/preds_base_*.jsonl`; scores: `score_base_*.json`.

| | zero/jargon | zero/plain | few/jargon | few/plain |
|---|---|---|---|---|
| composite | 0.074 | 0.045 | 0.101 | 0.108 |
| composite, test_2024 | 0.065 | 0.022 | 0.107 | 0.119 |
| T1 macroF1 | 0.489 | 0.435 | 0.559 | 0.565 |
| T2 macroF1 | 0.296 | 0.270 | 0.348 | 0.374 |
| T3 macroF1 | 0.062 | 0.044 | 0.049 | 0.045 |
| T4 macroF1 | 0.024 | 0.032 | 0.036 | 0.026 |
| T5 macroF1 | 0.139 | 0.133 | 0.135 | 0.135 |
| T6 direction acc | 0.309 | 0.238 | 0.179 | 0.121 |
| classification no-answer | 17% | 22% | 0% | 0% |
| dollar no-answer | 13% | 36% | 36% | 65% |

Paired bootstrap (10k): few/jargon − zero/jargon +0.028 [+0.016, +0.040]; few/plain − zero/jargon +0.034 [+0.022, +0.047]; few/plain − few/jargon +0.007 [−0.003, +0.016] (tie).

Findings:
- **Truncation at 400 tokens** is the largest distortion. Missing answers score as wrong. Few-shot eliminates classification truncation — this is all of its T1 gain (T1 accuracy on answered items 0.573 zero/jargon vs 0.572 few/jargon) and part of T2 (0.338 → 0.379 on answered items) — but raises dollar truncation (13% → 36–65%).
- **T6 as designed is near-unanswerable:** with RAWBEN withheld (leakage rule) the model must rebuild the agency's benefit; it answers $0 on 1,042/1,048 finished zero/jargon items. Under few/jargon only 20 of 143 nonzero answers have the right sign.
- **Over/under confusion:** true overissuances predicted underissuance 193× vs overissuance 51× (zero/jargon); 209 vs 46 under few/jargon. A model weakness the eval measures correctly.
- **T3 far below the 0.214 floor** in every condition (best 0.062); medical, childsupport, assets, reporting F1 = 0 in all four.
- No FY2024 year shift.
- Bugs fixed (no score changes): `score.py` now normalizes the runner's `"UNPARSEABLE"` string to `None` (it crashed on T6); `run_lm.py` now flags a dollar answer with no `T6:` line as `parse_ok: false` (it was hiding truncation in parse-rate counts).

### Verdict

Hypothesis partially confirmed. The eval discriminates: every condition beats the dummy and the bootstrap resolves ~0.03 composite differences with CIs excluding zero, which is the resolution the gate needs. A 31B general model gets ~10% of the way from dummy to ceiling (best composite 0.108). Condition choice (Q6): few-shot beats zero-shot; jargon vs plain is a statistical tie under few-shot — **lock few/jargon** on the tie-break (36% vs 65% dollar truncation; plain is clearly worse zero-shot). Two design defects block trusting gate decisions yet: the 400-token cap and T6's unanswerability. T3's 0.214 floor looks unreachable if a 31B model sits at ~0.06.

### Results — v1.1 cap test (2026-10-04 → 10-05)

few/jargon on a stratified 300-item subset (`eval_pilot/subset_300.txt`: 250 test_main + 50 test_2024, stratified by finding, seed 30; v1 few/jargon scores 0.095 on it vs 0.101 on all 1,200). New runner/scorer flags: `run_lm.py --max-tokens --ids`, `score.py --ids`. Driver: `run_cap_test.sh`.

| | dummy | 31b @400 (v1) | 31b @1500 | e4b @400 | e4b @1500 |
|---|---|---|---|---|---|
| composite | 0.000 | 0.095 | 0.095 | 0.006 | 0.006 |
| T1 macroF1 | 0.400 | 0.539 | 0.539 | 0.352 | 0.352 |
| T2 macroF1 | 0.182 | 0.371 | 0.371 | 0.207 | 0.207 |
| T3 macroF1 | 0.014 | 0.034 | 0.034 | 0.005 | 0.005 |
| T6 direction acc | 0.333 | 0.173 | 0.280 | 0.007 | 0.323 |
| dollar no-answer | — | 36% | 0% | 97% | 9% |

- The cap fixes truncation only. 31b classification answers are identical to v1 on 300/300 items (few-shot classification was never truncated; temperature 0). T6 recovers 0.173 → 0.280 but stays below the always-$0 dummy, and the composite clips below-dummy tasks to zero gain, so the composite is unchanged.
- gemma-4-e4b (untuned, ~4B) sits at the dummy floor: composite 0.006, predicts "correct" on 259/300 (T1 below dummy), T3 0.005. Its dollar answers run ~4,000 chars median, so 400 tokens truncates 97% and 1,500 still truncates 9%.
- Decision: adopt `max_tokens` 1,500 as eval v1.1 (v1 results stand as recorded). If e4b is the candidate family, its base is near zero on every task: the composite/win-count legs of the gate become easy and the T3 ≥ 0.214 floor is the binding, likely unreachable, constraint.

### Next steps
1. Eval v1.1: `max_tokens` 1,500 (adopted on the cap-test evidence above).
2. Decide T6: even fully answered, a 31B model can't beat always-$0 with RAWBEN withheld. Expose the issued amount, drop T6 from the composite, or rebuild the task.
3. Re-derive the T3 floor (31b 0.034–0.062, e4b 0.005 vs 0.214).
4. Full 1,200-item e4b base run under v1.1 once T6 and the T3 floor are settled.
5. Human label audit (Q1) on a dev-set sample; T6 band calibration (Q4).
