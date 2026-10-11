# Audit — was any model trained on the CalFresh MCQ?

**Date:** 2026-10-11 · **Code:** `experiments/audit_mcq_contamination.py`

### Question

The 500-question CalFresh benchmark (Better Government Lab, `cornellbgl/SNAP_scenarios`) is the test set for exp70, exp84 and exp85. Its licence (CC-BY-NC-ND-4.0) allows evaluation only: no training use in any form, synthetic derivatives included, and copies must stay access-controlled. Did any model we trained, or any model we evaluated, see it in training?

### Findings

1. **No training script reads it.** Only evaluation code references the file: exp70, exp84 and exp85 here, and `evals/calfresh_mcq` in state-policy-docs.
2. **No training data contains its text.** The 10-word-sequence scan covered 14,506 data, code and notes files with zero matches:
   - this repo and `snap-qc-data` (every SFT, RLVR and distillation set, exp52 through exp77);
   - the earlier `snap-cot-finetune`, `throwaway-mlxlora` and `public-snap-datasets` projects (their Gemma 4 LoRA and GRPO training data);
   - the state-policy-docs sources and corpus;
   - the ecfr-markdown corpus.

   The positive control found all 500 questions in a copy of the CSV, and 20 questions planted in a fake training file.
3. **The evaluated weights are stock.**
   - exp84/85 loaded `google/gemma-4-e4b` in LM Studio, which is the lmstudio-community Q4_K_M GGUF of Google's release. The earlier project's fine-tunes live under separate `snap-cot/...` keys and weren't used.
   - exp70's tuned model is the exp52 QC adapter (step 400), trained on QC variance data with no quiz text.
4. **The answer key had been committed.** exp70's three prediction files carried each question's correct letter (`gold`), and correct predictions revealed it too. They are now trimmed to question id, correct (0/1) and difficulty, and the full files moved to `../snap-qc-data/derived/exp70_preds/` (not in git). `exp84_per_question.json` holds right/wrong only. No question text or Inspect log (which embeds questions) was ever committed to any repo. Both repos are private, but the earlier versions remain in git history.

### Verdict

Clean. No model trained here, or in the earlier fine-tuning project, saw the quiz, and the exp70/84/85 results are uncontaminated.
