# Exp43 runbook — Mac Studio

Staged experiment: transformer-class transfer probe. The CPU sandbox cannot
run Stage 2 (no torch, 2 cores, 7 GB RAM), so the full run happens here.

## 0. What this decides

Whether the transfer recipe (faithful persistent pool + class-rebalancing)
ports to transformer-class models before the LM pretraining recipe is
locked. Pre-registered decision bar is in
`experiments/exp43_transformer_transfer_probe.md` and printed by the
script. Do not reinterpret the bar after seeing results.

## 1. Environment

The repo lives at `~/workspace/snap-qc-per-experiments` on the sandbox;
sync it to the Mac Studio (git pull `ctrimm/snap-qc-per-experiments`
main, or copy the tree). You need:

- Python 3.10+ with `scikit-learn`, `numpy`, `torch` (MPS backend on
  Apple silicon: the plain `pip install torch` wheel includes MPS support;
  no CUDA needed).
- The generator's Python deps (whatever `src/` already needs — if the
  sandbox runs `python3 -m synth.generate`, mirror that env).
- Real QC microdata for the eval split: the script expects
  `../snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv`
  (the data lives in `snap-qc-data/` next to the repo checkout, e.g.
  `~/Documents/GitHub/snap-qc-data` on the Mac Studio; adjust the `QC`
  constant at the top of the script if your checkout lives elsewhere).
  It's vendored in this repo gzipped at
  `data/raw/qcfy2024_csv/qc_pub_fy2024.csv.gz` (88MB uncompressed;
  committed 2026-10-02 per Cory's instruction) — unpack it from the repo
  root with:
  `mkdir -p ../snap-qc-data/raw/qcfy2024_csv && gunzip -c data/raw/qcfy2024_csv/qc_pub_fy2024.csv.gz > ../snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv`
  The original source is https://snapqcdata.net/datafiles
  (`qcfy2024_csv.zip`; the site returns 403 to `curl` without a browser
  User-Agent). Held-out only — never train on it, and never let it into
  any training corpus.

Install: `pip install torch scikit-learn numpy`

## 2. Stage 1 — regenerate the pools (Mac Studio, ~10–20 min)

```bash
cd <repo>
python3 experiments/exp43_transformer_transfer_probe.py --stage data --out /tmp/exp43
```

This regenerates the persistent and retry pools with the exp25/exp37
protocol (n=20000, seed 7, max-attempts 12), extracts the clean 8-feature
set, standardizes on the persistent pool's train rows, and writes
`/tmp/exp43/exp43_pools.npz` + `/tmp/exp43/exp43_meta.json`.
Sanity numbers to expect: ~7.9k persistent error rows, ~8.2k retry error
rows, 17,318 test rows. If the class counts differ wildly from those,
stop — the generator defaults drifted.

(You may instead generate the pools in the sandbox and copy the .npz
over; the runbook path above is self-contained and preferred.)

## 3. Stage 2 — validate the torch path (~2 min)

```bash
python3 experiments/exp43_transformer_transfer_probe.py --stage train \
  --pools /tmp/exp43 --smoke-train
```

One arm, one seed, two epochs. If this prints `smoke-train OK`, the torch
path (MPS device, model build, training loop) works.

## 4. Stage 2 — full battery (~30–60 min on M3 Ultra)

```bash
python3 experiments/exp43_transformer_transfer_probe.py --stage train \
  --pools /tmp/exp43 --seeds 7,8,9
```

12 trainings (4 arms × 3 seeds). Expected per-arm wall time is a few
minutes on MPS. The script prints per-seed acc/macroF1, per-arm
mean ± range, and the pre-registered decision bar.

## 5. Reading the result

- **Guard first.** If no arm beats macroF1 0.244 (exp37's logreg-unweighted
  reference), the probe is underpowered — do not interpret the arms;
  widen tuning (d_model 64→128, layers 2→4, LR sweep) and re-run.
- **Pool question:** persistent/uniform ≥ retry/uniform − 0.01 → lock the
  persistent pool for LM pretraining data.
- **Reweighting question:** balanced-loss ≥ uniform − 0.01 on the
  persistent pool → loss reweighting ports; < uniform − 0.02 → it does not
  (use uniform loss; resampling becomes the follow-up probe).
- Record the outcome in the chronicle: fill in Results/Verdict, change
  STAGED → the verdict, push.

## 6. If something looks off

- `torch.backends.mps.is_available()` False → the script falls back to
  CPU automatically (slower but fine); check the torch install.
- Wildly different pool sizes vs §2 → `git log` the generator; the
  exp31 dollar-mechanisms defaults are on — that is expected and fine,
  but note it in the chronicle since exp37 ran pre-adoption.
- NaNs in loss → halve the LR (`--lr` is not a flag; edit the
  `AdamW(lr=5e-4` line — note the change in the chronicle).
