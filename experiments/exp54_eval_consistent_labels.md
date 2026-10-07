# Experiment 54 — eval-consistent synthetic labels

**Date:** 2026-10-06/07 · **Code:** `experiments/exp54_label_targets.py`, `experiments/exp52_rlvr_dataset.py --label-match` · **Targets:** `experiments/exp54_label_targets.json`

### Hypothesis

The exp52 LLM shows no chance-corrected skill on T4 (nature) and T5 (fault) partly because synthetic labels follow different rules than the exp30 eval. Making the training labels eval-consistent should give T4/T5 real skill on held-out real cases. Moves gate 3 (LM eval).

### Method

Two mismatches, measured on FY2021–2024 QC public-use files with the eval's denylisted items excluded (aggregate shares only):

1. **Fiscal-year codebook.** Cause 26 (no-fault) and natures 56/57 occur only in FY2024; 5/6 of the eval is FY2021–23. Real no-fault share: 0% FY21–23, 14% FY24; exp52 synthetic training: 24%.
2. **Labeling rule.** `dist.json` counts every recorded variance, including zero-dollar tolerance variances (mostly nature 97): 44–47% nature 97. The eval labels the largest reportable variance (`labels.label_case`): nature 97 is 15–19% (FY21–23), 23% (FY24).

`--label-match`: each synthetic case gets an era at the eval's 5/6 pre-2024 share; pre-2024 cases re-draw cause 26 from real FY21–23 P(cause | element) and code natures 56/57 as 53. Error cases are drawn by weighted sampling without replacement, weight = Π over T3/T4/T5 of real share ÷ synthetic share (renormalized over labels synthetic can produce; capped at 10). Then SFT 600 steps, same settings as exp52's best (lr 1e-5, rank 16, batch 4), scored on 197 real dev items (checkpoints 300–600).

### Results

Label mix (train): T4 97 47% → 22% (target 19%); 53 5% → 15% (18%); T5 no-fault 24% → 2% (0%); agency/client 35/22% → 49/36% (47/38%); T3 shelter/earned/unearned 35/21/23% → 27/25/25% (27/27/24%).

| Dev (197) | Original SFT (seed 52) | Label-matched SFT |
|---|---|---|
| composite skill, step 600 | 0.200 | 0.141 |
| composite skill, best checkpoint | 0.271 (step 400) | 0.192 (step 400) |
| T2 κ, step 600 / 400 | 0.154 / 0.286 | 0.242 / 0.261 |
| T4 κ, step 600 | −0.030 | 0.034 (p 0.20) |
| T5 κ, step 600 | −0.001 | 0.033 (p 0.23) |
| error calls, step 600 (truth 131) | 155 | 91 |

The label-matched model drops the wrong priors (the original answered nature 97 on 95 of 155 error calls and fault "other" 95 times) but answers fault "agency" on all 91 of its error calls, the new majority. Its best checkpoint sits within the seed-noise band of the original recipe (seed 53 peaked at 0.167).

### Verdict

Partially confirmed. The labels were wrong and are now eval-consistent, which removes systematic mislabeling. But no chance-corrected T4/T5 skill appears: the case record most likely doesn't carry fault or nature signal (fields show amounts, not what went wrong procedurally). T2 improved. Not adopted as the default recipe on this evidence; keep `--label-match` available and treat T4/T5 as diagnostics until an input carries that signal.

### Next steps

1. Generator proper: record each variance's dollar amount and rebuild `dist.json` from reportable variances, so labels match by construction (needs the calibration chain re-fit).
2. Add the six T3 element buckets the generator never produces (~22% of T3 test items).
3. Raise the multi-variance rate (synthetic 0.73–0.87× of real).
4. Consider scoring T4/T5 as diagnostics outside the gate composite (an exp30 eval decision).
