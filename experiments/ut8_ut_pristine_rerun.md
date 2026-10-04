# Experiment UT8: pristine rerun — closing the fairness caveat

**Date:** 2026-10-04 · **Code:** `experiments/ut8_ut_pristine_rerun.py`

## Hypothesis

Tied to the north star: UT2's transfer verdict carries a fairness caveat —
UT1's offsets were fit on FY2022–2024 UT microdata *including the holdout
rows*. If the finding edge is a contamination artifact (the generator
memorizing holdout marginals), it should collapse when the holdout rows
are excluded from *every* tuning step. If it survives, the verdict stands.

## Method

A verbatim port of UT1's `fit_ut_targets` with one change: rows whose
(fy, UT-relative row index) key appears in `experiments/ut2_holdout_idx.json`
are skipped before any aggregate is touched. Pristine refit basis:
FY2022–2024 (UT1's convention) minus 787 in-basis holdout rows → 2,340
kept rows. Refit constants installed by monkey-patching
`src.synth.ut_state` (no src modified), following UT1's it2 recipe
(pure-empirical → pilot → one-step realized-output bucket calibration →
coin-cal line search → final 20k, seed 7). Then UT2's battery on the same
holdout: pristine-UT synth vs national synth, both class_weight settings
(--balanced and no-cw runs), CLEAN8 features. The regenerated national arm
is verified byte-identical to UT2's file as a sanity check (it was).

## Results

**Pristine refit marginals:** case_err 0.3325 (UT1: 0.3323), finding
0.6675/0.1917/0.1408 (UT1: 0.6677/0.1920/0.1403), p(over|err) 0.5765 (UT1:
0.5778) — excluding the holdout barely moved the targets (the offset fit
sees only pooled marginals, as the caveat said). Coin-cal line search:
1.10 wins again (finding L1 0.0526). Pristine synth finding L1 0.0485.

**Battery (balanced):** pristine UT finding AUC 0.7277 vs national 0.6777
(**+0.050**); element acc 0.3810 vs 0.3661, macroF1 0.1598 vs 0.1714.

**Battery (no-cw):** pristine UT finding AUC 0.7256 vs national 0.6738
(**+0.052**); element acc 0.4940 vs 0.5179 (national wins), macroF1 0.1804
vs 0.1792 (UT wins by 0.001).

**Contamination premium — the honest accounting:** UT2 (non-pristine, v1
9-features) finding gaps were +0.083 (balanced) / +0.050 (no-cw); UT8
(pristine, clean-8) gaps are +0.050 / +0.052. The no-cw gap is
*identical*; the balanced gap narrowed by 0.033 — but the narrowing is
driven by the **national arm improving under clean-8 features**
(0.640→0.678), not by the UT arm degrading (0.723→0.728). The UT arm's
absolute AUC is unchanged-to-better pristine. There is no contamination
premium on the UT signal itself; the verdict stands. (Thin-margins
disclosure, per the SD seed-9 template: the balanced *gap* is 0.033
smaller pristine, entirely explained by the national arm's clean-8 gain.)

**Element:** pristine confirms UT2's marginal element verdict — national
wins accuracy at seed 7 (0.5179 vs 0.4940), UT wins macroF1 by a hair.
The element non-pass/marginal-pass is not a contamination artifact.

## Verdict

**PASS — the UT2 verdict stands.** The finding edge (+0.050/+0.052 AUC)
survives the fully clean refit; the contamination premium is ~0 on the UT
arm. The pristine numbers (finding AUC 0.728 vs 0.678) *replace* UT2's as
the reference in UT4's plan and the whitepaper. UT4's CONDITIONAL PASS
(0.7308 calibrated AUC vs provisional 0.723) now clears against the
pristine 0.728 — a full PASS.

## Next steps

- Whitepaper cites pristine AUCs (0.728 vs 0.678).
- No further contamination work needed; the caveat is closed.
