"""Exp 3 — calibration v2: income-variance direction fix.

Exp 1 found the finding mix at 79/9/12 vs the real 60/24/16 (correct / over /
under). Root cause found on code review: the income corruption directions for
natures 38 ("more income than budgeted") and 44 ("less income than budgeted")
were swapped, and 35 ("unreported source") was inverted — so most synthetic
income variances materialized in the wrong direction. This script measures
whether the fix moves the finding mix toward the real distribution.

Variants (both with the direction fix):
  (a) retry budget 3  — isolates the direction fix (same budget as exp 1)
  (b) retry budget 12 — also lifts the realized error rate toward the real 40%
      (exp 2 noted the synthetic prior realized only 21% errors)

Compares against the real FY2024 QC file. Exp 1's pre-fix baseline (79/9/12)
is quoted from the exp1 chronicle.

Usage: python experiments/exp3_calibration_v2.py [--n 20000] [--seed 7]
"""
import argparse
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from exp1_calibration import real_marginals, synth_marginals, show  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def gen(n, seed, max_attempts):
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        path = tf.name
    subprocess.run(
        [sys.executable, "-m", "synth.generate", "--n", str(n),
         "--seed", str(seed), "--dist", str(ROOT / "experiments/dist.json"),
         "--max-attempts", str(max_attempts), "--out", path],
        cwd=ROOT / "src", check=True, capture_output=True,
    )
    return path


def finding_mix(finding, n):
    return {k: finding.get(k, 0) / n for k in ("1", "2", "3")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    print("loading real marginals...", flush=True)
    rf, rb, rn, rc, ra, r_n = real_marginals()
    r_mix = finding_mix(rf, r_n)
    print(f"REAL finding mix:  correct={r_mix['1']:.3f} over={r_mix['2']:.3f} "
          f"under={r_mix['3']:.3f}  (n={r_n})")
    print("EXP1 pre-fix baseline (chronicle): correct=0.79 over=0.09 under=0.12")

    for label, attempts in (("direction fix, retry=3", 3),
                            ("direction fix, retry=12", 12)):
        print(f"\n##### {label} #####")
        path = gen(args.n, args.seed, attempts)
        sf, sb, sn, sc, sa, s_n = synth_marginals(path)
        s_mix = finding_mix(sf, s_n)
        print(f"synth finding mix: correct={s_mix['1']:.3f} over={s_mix['2']:.3f} "
              f"under={s_mix['3']:.3f}  (n={s_n})")
        err_rate = 1 - s_mix["1"]
        print(f"  realized error rate: {err_rate:.3f} (real: {1 - r_mix['1']:.3f})")
        over_share = s_mix["2"] / err_rate if err_rate else 0
        print(f"  over share of errors: {over_share:.3f} "
              f"(real: {r_mix['2'] / (1 - r_mix['1']):.3f})")
        r_var, s_var = sum(rb.values()), sum(sb.values())
        show("element bucket", rb, sb, r_var, s_var, top=10)
        show("nature", rn, sn, r_var, s_var, top=10)


if __name__ == "__main__":
    main()
