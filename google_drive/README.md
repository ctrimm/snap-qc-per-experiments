# Colab kit — exp52 round 5 (SFT 1,200 steps + eval)

Everything needed to run exp52's round 5 on a Colab GPU instead of the Mac
Studio: answer-only SFT of `google/gemma-4-E4B-it` on synthetic QC cases,
then scoring on synthetic validation, the 197 real dev cases, and the 1,200
real test cases, with the same scorer (including chance-corrected skill).

## How to run

1. Upload the contents of this folder to `MyDrive/Projects/snap-qc-finetune/` (≈49 MB),
   so the notebook sits at `MyDrive/Projects/snap-qc-finetune/exp52_round5_colab.ipynb`
   with `data/`, `eval/`, `src/` and `results/` beside it.
2. Accept the Gemma license for `google/gemma-4-E4B-it` on Hugging Face. The
   notebook reads your token from the Colab secret `HF_TOKEN` (key icon in the
   left sidebar, with notebook access switched on), or from an `HF_TOKEN`
   environment variable.
3. Open `exp52_round5_colab.ipynb` in Colab, pick an **A100** runtime, and run
   the cells top to bottom. Outputs land in `MyDrive/Projects/snap-qc-finetune/results/<run_name>/`.
   If you use a different folder, change `ROOT` in the first code cell.

Rough A100 estimates: training ~45–60 min, evals ~10–15 min. A T4 (16 GB)
can't hold the bf16 model for training; an L4 (24 GB) should work, more slowly.

## What's in here

| Path | What |
|---|---|
| `exp52_round5_colab.ipynb` | The run: config, LoRA setup, data encoding, training, three evals |
| `data/sft_train.jsonl`, `data/sft_valid.jsonl` | 4,000 / 200 synthetic SFT pairs (`prompt` = eval prompt, `completion` = gold answer block). Finding-balanced, view-calibrated. No real cases |
| `data/synthetic_valid.jsonl` | Synthetic validation cases with T1–T5 labels (in-distribution check) |
| `eval/items.json` | The frozen exp30 eval (dev + test), public-use QC values only |
| `eval/score.py`, `eval/labels.py`, `eval/run_lm.py` | Scorer, labels/rendering, prompt builder + parser (copies from `experiments/eval_pilot/`) |
| `eval/preds_base_e4b_mlx_bf16_{dev,test}.jsonl` | Untuned e4b answers from the Mac Studio (gate baseline) |
| `eval/preds_base_31b_test.jsonl` | Untuned Gemma 4 31B answers (informational reference) |
| `src/synth/codebook.py` | Code tables `labels.py` imports |
| `results/` | Notebook outputs (adapter checkpoints, predictions, gate JSON) |

## Matching the Mac Studio run

| Setting | MLX (Mac Studio) | This notebook |
|---|---|---|
| Model | `mlx-community/gemma-4-e4b-it-bf16` | `google/gemma-4-E4B-it` (same weights, bf16) |
| LoRA | rank 16, scale 20, dropout 0.05, last 16 layers | r 16, `lora_alpha` 320 (= scale × r), dropout 0.05, layers 26–41, same modules |
| Optimizer | Adam, lr 1e-5 constant, batch 4, 1,200 steps | AdamW wd 0, lr 1e-5 constant, batch 4, 1,200 steps |
| Prompt | thinking off, single user turn, prompt masked | same (asserted in the notebook) |
| Eval | greedy, 64 new tokens, stop at `<turn|>` | same |

Numerics differ slightly between MLX and PyTorch, so for a strictly matched
gate set `RUN_BASE = True` in the test cell; it regenerates base predictions
on Colab with the adapter disabled.

## Reference numbers (Mac Studio, real dev, n = 197)

| Run | Composite | Composite skill | T1 κ | T3 κ |
|---|---|---|---|---|
| Base | 0.014 | 0.019 | 0.037 | 0.003 |
| SFT 300 steps | 0.179 | 0.132 | 0.246 | 0.079 |
| SFT 600 steps | 0.256 | 0.200 | 0.424 | 0.219 |

## Rebuilding this folder

The data and eval files are copies (not tracked in git). From the repo root:

```bash
G=google_drive; D=../snap-qc-data/derived; E=experiments/eval_pilot
mkdir -p $G/data $G/eval $G/src/synth $G/results
cp $D/exp52_sft/train.jsonl $G/data/sft_train.jsonl
cp $D/exp52_sft/valid.jsonl $G/data/sft_valid.jsonl
cp $D/exp52_rlvr/valid.jsonl $G/data/synthetic_valid.jsonl
cp $E/{items.json,score.py,labels.py,run_lm.py} $G/eval/
cp $E/preds_e4b_bf16_base_few_jargon_class.jsonl $G/eval/preds_base_e4b_mlx_bf16_test.jsonl
cp $E/preds_base_few_jargon.jsonl $G/eval/preds_base_31b_test.jsonl
cp $D/exp52_rlvr/sweep/dev_base.jsonl $G/eval/preds_base_e4b_mlx_bf16_dev.jsonl
cp src/synth/codebook.py $G/src/synth/ && touch $G/src/synth/__init__.py
```
