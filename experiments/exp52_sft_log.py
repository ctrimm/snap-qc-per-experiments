"""Append one row per exp52 SFT/GRPO-on-SFT trial to exp52_sft_results.tsv
from its eval.txt (real dev metrics + synthetic valid mean excess)."""
import re
import sys
from pathlib import Path

name, evalf, config = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
tsv = Path(__file__).with_name("exp52_sft_results.tsv")
t = evalf.read_text()
g = lambda pat: (re.search(pat, t).group(1) if re.search(pat, t) else "")  # noqa: E731
row = [name, config, g(r"composite \(T1-T5\): ([0-9.]+)"), g(r"composite skill \(chance-corrected\): ([0-9.]+)"),
       g(r"\nt1\s+([0-9.]+)"), g(r"\nt1(?:\s+[-0-9.]+){3}\s+([-0-9.]+)"),
       g(r"\nt2(?:\s+[-0-9.]+){3}\s+([-0-9.]+)"), g(r"\nt3(?:\s+[-0-9.]+){3}\s+([-0-9.]+)"),
       g(r"synthetic mean excess \(T1-T5\): ([-0-9.]+)"), g(r"changed_vs_base: ([0-9/]+)")]
if not tsv.exists():
    tsv.write_text("trial\tconfig\tdev_composite\tdev_skill\tdev_t1_f1\tt1_kappa\tt2_kappa\tt3_kappa\tsyn_mean_excess\tchanged_vs_base\n")
with open(tsv, "a") as fh:
    fh.write("\t".join(row) + "\n")
print("\t".join(row))
