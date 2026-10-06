"""Print the config of the best stable exp52 sweep trial so far (autoresearch
"keep"): highest dev composite, ties broken by more answers changed vs base.
Rows that crashed or went NaN, and the untrained base row, never qualify.
Falls back to --fallback when no trial has finished cleanly."""
import argparse
import csv
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--tsv", default=str(Path(__file__).with_name("exp52_sweep_results.tsv")))
ap.add_argument("--fallback", default="LR=2e-6 GROUP=8 MAXC=64")
args = ap.parse_args()
best = None
for r in csv.DictReader(open(args.tsv), delimiter="\t"):
    if r["trial"] == "base":
        continue
    try:
        comp = float(r["dev_composite"])
        changed = int(r["changed_vs_base"].split("/")[0])
    except (ValueError, AttributeError):
        continue
    if r["t1"] in ("", "0.000") and comp == 0:  # collapsed output, not a real score
        continue
    key = (comp, changed)
    if best is None or key > best[0]:
        best = (key, r["config"])
print(best[1] if best else args.fallback)
