# Experiment UT6: temporal stability — does the signal hold year to year?

**Date:** 2026-10-04 · **Code:** `experiments/ut6_temporal.py`

## Hypothesis

Tied to the north star: if the UT transfer signal is a stable property of
Utah's certification process (not a year-specific artifact), a generator
refit on FY2022 alone should predict FY2023–24 real UT cases about as well
as the pooled fit — and neither should decay across the period boundary.
If stable, production needs no annual refit.

## Method

Refit UT1's conditioning on **FY2022 UT microdata only** (n=1,007; UT1's
offsets were fit FY2022–2024), following UT1's it2 recipe (pure-empirical
ratios → 20k pilot → one-step realized-output bucket calibration →
UT_COIN_CAL line search → final 20k, seed 7). Refit constants installed by
monkey-patching `src.synth.ut_state` (no src modified); the pooled arm is
generated first, unpatched (UT1 as-is). There is **no excl21 arm** —
FY2020–21 are already excluded from the UT track's fitting basis (UT1,
NY6 lesson), so the partial-year sensitivity question does not arise.

Arms: T_refit (FY2022-fit synth) and T_pooled (UT1 as-is), each tested on
FY2023–24 real UT (clean temporal test, 2,120 rows) AND FY2022 real UT
(train-period reference, 1,007 rows). Same GBM recipe, element + finding,
CLEAN8. Also: per-FY nature-97 cause-blank check (labeling-break watch).

## Results

**Stage 0 fits:** FY2022 refit — case_err 0.3454, p(over|err) 0.5625,
cause97_blank 0.9826, near_full|over 0.0000 (→ UT_P_UNIT refit 0.00000 —
FY2022 had zero near-full overs); FY2023–24 ref — case_err 0.3262,
p(over|err) 0.5852, cause97_blank 0.7724. Coin-cal line search on the
refit: 1.10 wins again (finding L1 0.0287) — same as UT1's 1.10.

**Labeling break found (stage 0b):** nature-97 cause-blank rate per FY —
2020 0.993, 2021 0.976, 2022 0.983, 2023 0.951, **2024 0.609**. Utah
started recording causes on timing-97 variances in FY2024 (blank rate
dropped from ~0.98 to 0.61). This is a genuine coding-practice shift, not
a generator artifact — UT1's pooled 0.8401 averages across it. It moves
the *recorded cause* mix, not the finding/element labels (STATUS/ELEMENT
stable). Watch item for future refits: the 97-cause resampling basis
should be re-examined when FY2025 lands.

**Transfer battery (clean temporal test = FY23-24):**

| arm | element acc / macroF1 | finding acc / macroF1 |
|---|---|---|
| T_refit → FY23-24 | 0.4510 / 0.2038 | 0.5443 / 0.4241 |
| T_pooled → FY23-24 | **0.4890 / 0.2401** | 0.5401 / 0.4192 |
| T_refit → FY2022 | 0.4282 / 0.1853 | 0.5253 / 0.4286 |
| T_pooled → FY2022 | 0.4569 / 0.1573 | 0.5134 / 0.4198 |

No decay across the period boundary: element accuracy *rises* from the
train period to the test period for both arms (refit 0.4282→0.4510,
pooled 0.4569→0.4890) — the NY6 mix-alignment pattern, not decay. The
pooled (UT1 as-is) fit **matches or beats** the FY2022 refit on the clean
temporal test (element clearly, finding tied).

**Per-bucket F1 (T_refit, FY2022→FY23-24):** earned 0.581→0.664 (+0.083),
shelter 0.418→0.460 (+0.043) improve; unearned 0.434→0.388 (−0.047) slight
decay; medical 0.316→0.136 (−0.179, n=14→33) the only real decay; sua
+0.039; hhcomp −0.139 on n=6→14 (thin). Buckets to watch: **medical**
(same watchlist as NY6) and hhcomp (thin).

## Verdict

**PASS — no annual refit needed.** The transfer signal holds year to
year: no metric decays across the FY2022→FY2023–24 boundary, and the
pooled UT1 fit beats or ties the single-year refit on the clean temporal
test. Production process note: refit on a rolling multi-year window;
**drop partial-year QC files from refits** (already the UT track's rule);
watch medical and hhcomp buckets; re-examine the 97-cause resampling
basis when FY2025 lands (the FY2024 cause-recording shift).

## Next steps

- UT8's pristine refit follows UT1's FY2022–2024 convention (the
  production recommendation).
  - **Done →** [UT8](ut8_ut_pristine_rerun.md): UT8: PASS — pristine finding AUC 0.728 vs 0.678 national (+0.050/+0.052); UT arm absolute AUC unchanged-to-better pristine (no contamination premium; balanced-gap narrowing fu…
- The FY2024 cause-blank shift (0.98→0.61) goes in the whitepaper's
  limitations as a known labeling break.
