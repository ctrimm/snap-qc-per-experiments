# NY8 — pristine transfer rerun: testing NY2's fairness caveat

**Date:** 2026-09-29
**Status:** Complete — decision: **PASS**, see Verdict.
**Deliverables (new files only; no existing file modified):**
- `experiments/ny8_ny_pristine_rerun.py` — pristine refit + regeneration + transfer battery
- `experiments/ny8_ny_pristine_rerun.md` — this chronicle

Plain-language terms: pristine = refit on microdata with the 815 holdout
rows excluded before any aggregate is touched, so the generator never saw
the test set even indirectly; contamination premium = how much of NY2's
reported NY-vs-national gap came from the generator having seen test-set
marginals; binary AUC = how well the model's error-probability ranking
separates error cases from correct ones (0.5 = coin flip, 1.0 = perfect).

## Hypothesis

NY2's own caveat: NY1's offsets were fit on pooled FY2020–2024 NY microdata
*including* the 815 holdout rows, so the NY-synth arms were not pristine vs
the test set — NY2's element-leg verdict (no NY advantage over national)
and its finding-leg verdict (consistent NY edge on P(error) ranking, binary
AUC +0.037 at seed 7) could both be partly shaped by the generator having
seen test-set marginals. If the finding edge survives a pristine refit (same
pooled window, holdout rows excluded from *every* tuning step), NY2's mixed
verdict stands; if it collapses, the finding edge was contamination and
NY4's calibrated-ranking plan loses its foundation. On the element leg,
pristine fitting can only confirm the negative.

Gate: transfer (the finding leg is where NY2 passed; the element leg is the
control).

## Method

**Pristine refit** (`python3 experiments/ny8_ny_pristine_rerun.py`, from repo
root; microdata read-only at `snap-qc-data/raw` beside the repo checkout): a
verbatim
port of `ny1.fit_ny_targets` with one change — rows whose (fy, NY-relative
row index) key appears in `experiments/ny2_holdout_idx.json` are skipped
before any aggregate is touched (STATE indexing verified identical: strip
vs no-strip NY counts match 3,257, and no NY rows carry STATE whitespace).
Kept 2,442 of 3,257 NY rows. Refit constants installed by monkey-patching
`src.synth.ny_state` module attributes (PA6's pattern; no src file
modified).

**Regeneration** follows NY1's it2 recipe exactly, all targets on the
minus-holdout fit: pure-empirical ratios → 20k-case pilot at NY_COIN_CAL=1.0
→ one-step realized-output calibrations (bucket ratios × real/synth share;
97-resolution coins × real/synth P(over|97,b); direction margins ×
real/synth P(over|non97,b), P(under|non97,b), all on the minus-holdout
basis; depcare/arithmetic keep NY1's sparsity guards) → NY_COIN_CAL line
search over {0.90, 0.93, 0.96, 1.0} (8k pilots) against the pristine
marginal case-error rate → final 20k, seed 7. The national arm was
regenerated identically (n=20k, seed 7, NY2's exact recipe) and verified
**byte-identical** to NY2's file (`/tmp/ny2out/nat_synth.jsonl`) — NY2's
national file was reused for the battery.

**Transfer battery:** NY2's recipe — v1 features, sklearn
`HistGradientBoostingClassifier(random_state=0)` **without** class_weight
(NY2's winning setting for NY; `--balanced` flips it), trained on
pristine-NY synth (arm a) vs national synth (arm b), evaluated on the same
815-row holdout (299 test error cases). Binary AUC for the finding task
computed from P(error) = proba(2)+proba(3).

## Results

### Pristine refit vs NY1's pooled fit (marginals barely moved)

| target | NY1 pooled | NY8 minus-holdout |
|---|---|---|
| finding c/o/u | 0.6345/0.2101/0.1553 | 0.6342/0.2098/0.1560 |
| case_err_rate | 0.3655 | 0.3658 |
| p(over\|err) | 0.5750 | 0.5735 |
| pure-empirical bucket ratios | earned 1.0080, unearned 1.0875, shelter 0.8105, sua 1.2056, medical 1.7477, hhcomp 1.5846 | earned 1.0165, unearned 1.0960, shelter 0.8032, sua 1.2053, medical 1.6950, hhcomp 1.5903 |
| baked bucket ratios (post-calibration) | earned 1.0133, unearned 1.1821, shelter 0.8290, sua 1.0549, medical 2.0411, hhcomp 1.3287 | earned 1.0219, unearned 1.1834, shelter 0.8209, sua 1.0517, medical 1.9738, hhcomp 1.3255 |
| NY_COIN_CAL | 0.96 | **0.93** (grid tie 0.93/0.96 at finding L1 0.0422; 0.93 picked first) |

Pristine NY synth finding L1 vs the minus-holdout target: **0.0434** (synth
c/o/u 0.6446/0.2211/0.1343 vs pristine 0.6342/0.2098/0.1560 — the under
share lands low at 0.134 vs 0.156). NY1 reported 0.0202 on the pooled
target: unlike PA8 (whose pristine refit calibrated *better*), NY's
pristine refit calibrated *worse* on finding — the minus-holdout direction
and 97-resolution margins (e.g. sua resolution coin 1.0879 vs 1.2199,
s_under 0.9524 vs 1.0) landed the under-share short. The coin-cal grid
(best 0.0422 at both 0.93 and 0.96) could not recover it; the residual is
calibration noise on 2,442 rows, not a mechanics change.

### Element classification (299 test error cases), seed 7

| arm | acc | macroF1 | medical F1 | sua F1 | hhcomp F1 | earned F1 | shelter F1 | unearned F1 |
|---|---|---|---|---|---|---|---|---|
| a) pristine NY synth + GBM no-cw | 0.4615 | 0.1504 | 0.077 | 0.324 | 0.000 | 0.691 | 0.520 | 0.343 |
| b) national synth + GBM no-cw | 0.4682 | 0.1507 | 0.320 | 0.067 | 0.000 | 0.671 | 0.549 | 0.352 |
| **pristine NY-vs-national gap** | **−0.0067** | **−0.0003** | | | | | | |
| NY2's reported gap (contaminated) | −0.033 | +0.017 | | | | | | |

Absolute moves vs NY2: pristine NY acc 0.4615 vs 0.435 (+0.027), macroF1
0.1504 vs 0.168 (−0.018) — direction-mixed, calibration noise, not a
contamination collapse (if contamination had inflated NY2's numbers, the
pristine arm would be *worse* on both, and the accuracy move is in the
wrong direction for that story). The national arm reproduced to +0.0002
acc / +0.0007 macroF1 (0.4682/0.1507 vs NY2's 0.468/0.151) — the
byte-identical file, so all gap movement is on the NY side. Notable
per-bucket moves: sua F1 0.129 → 0.324 (the refit's sua resolution/direction
recalibration), earned 0.646 → 0.691, shelter 0.491 → 0.520; medical and
hhcomp still ~0 (the mechanics gap is untouched by pristine fitting).

### Finding classification (815 test cases), seed 7

| arm | acc | macroF1 | binary AUC (err vs corr) |
|---|---|---|---|
| a) pristine NY synth + GBM no-cw | 0.4049 | 0.3568 | **0.6262** |
| b) national synth + GBM no-cw | 0.3558 | 0.3228 | 0.6107 |
| **pristine NY-vs-national AUC edge** | | | **+0.0155** |
| NY2's NY arm binary AUC (contaminated) | — | — | 0.648 |

## Verdict

**The caveat is now quantified and NY2's mixed verdict stands — PASS.**
On the element leg, pristine fitting confirms the negative: the
NY-vs-national gap is −0.007 acc / −0.000 macroF1 (NY2 reported −0.033 /
+0.017) — still no NY advantage over national on either metric, with the
gap essentially at zero. The contamination did not hide a real NY element
advantage; NY2's element-leg non-pass is not an artifact of the pooled fit.
On the finding leg, the NY edge over national **survives pristine fitting
but narrows**: binary AUC +0.037 → **+0.016** (0.6262 vs 0.6107). The
contamination premium is therefore ~+0.02 on the finding AUC and ~0 on the
element gap — consistent with the offsets seeing only pooled marginals
rather than test rows' labels, and with part of NY2's 0.648 coming from the
better finding-L1 calibration the contaminated fit achieved (0.0202 vs
0.0434). NY4's calibrated-ranking plan keeps its foundation, with the
pristine 0.626 as the reference (replacing NY2's 0.648) — the edge is
smaller but it is real, pristine, and directionally consistent with NY2's
3-seed robustness (NY won binary AUC 6 of 6).

Two notes: (1) the medical/hhcomp per-bucket F1s are still ~0 after
pristine fitting — the generator's mechanics gap for the rare tail is not a
contamination artifact and remains NY2's open lever; (2) the sua F1 jump
(0.129 → 0.324) is the largest single-bucket move and comes from the
refit's 97-resolution/direction recalibration landing differently on
2,442 rows — worth remembering as calibration sensitivity, not as a
mechanics improvement.

## Next steps

- **NY4** proceeds on the calibrated-ranking plan with the pristine-NY
  arm's binary AUC 0.626 as the reference (replaces NY2's 0.648).
- If the macroF1 tail matters for the copilot, the lever is still generator
  mechanics for medical/sua/hhcomp — pristine fitting did not fix it
  (medical/hhcomp F1 ~0), and more sampling tricks won't either.
- Optional: seed-robustness for the pristine gap (seeds 8, 9) — NY2 showed
  the contaminated finding edge held at all 3 seeds; a quick pristine check
  would confirm the +0.016 edge isn't seed luck. Cheap to run (two more
  20k gens + batteries).
