"""Exp 7 — per-bucket persistence in the retry loop.

Exp 6's residual: hhcomp at 2.96x and arithmetic at 3.33x of their real
shares. Diagnosis: the retry loop redraws the *bucket* on every attempt, so
buckets whose corruptions always materialize (hhcomp: hh_size +/-1; arithmetic:
direct benefit noise) win the retry lottery, while buckets whose corruptions
often no-op (shelter cap absorption, medical threshold) get filtered out.
The bucket-level effectiveness upweighting compensates on average but cannot
undo the selection — it just inflates the draw weights.

Fix: draw each variance's bucket ONCE from the empirical (conditional,
zero-base-scaled) mix and retry *natures within that bucket* until one moves
the benefit (--persistent-buckets). This removes the cross-bucket lottery
structurally: recorded P(bucket) ~= drawn P(bucket). Direction-level nature
weights are kept (the within-bucket nature mix still needs correction).

Compares persistent mode against the exp6 baseline on the same seed:
finding mix L1, element ratios, nature ratios. Success: hhcomp/arithmetic
ratios near 1.0x with the finding mix L1 staying ~0.01.

Usage: python experiments/exp7_per_bucket_persistence.py [--n 20000] [--seed 7]
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from exp1_calibration import real_marginals, synth_marginals, show  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def gen(n, seed, persistent):
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        path = tf.name
    cmd = [sys.executable, "-m", "synth.generate", "--n", str(n),
           "--seed", str(seed), "--dist", str(ROOT / "experiments/dist.json"),
           "--max-attempts", "12", "--out", path]
    if persistent:
        cmd.append("--persistent-buckets")
    else:
        cmd.append("--no-persistent-buckets")
    subprocess.run(cmd, cwd=ROOT / "src", check=True, capture_output=True)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    print("loading real marginals...", flush=True)
    rf, rb, rn, rc, ra, r_n = real_marginals()
    r1 = rf["1"] / r_n
    print(f"REAL:  correct={r1:.3f} over={rf['2']/r_n:.3f} under={rf['3']/r_n:.3f}")

    print("generating baseline (exp6 retry loop)...", flush=True)
    base_path = gen(args.n, args.seed, persistent=False)
    print("generating persistent-bucket mode...", flush=True)
    persist_path = gen(args.n, args.seed, persistent=True)

    for label, path in (("EXP6 baseline", base_path),
                        ("EXP7 persistent", persist_path)):
        sf, sb, sn, sc, sa, s_n = synth_marginals(path)
        s1 = sf["1"] / s_n
        l1 = abs(s1 - r1) + abs(sf["2"] / s_n - rf["2"] / r_n) + abs(sf["3"] / s_n - rf["3"] / r_n)
        print(f"\n{label}: correct={s1:.3f} over={sf['2']/s_n:.3f} "
              f"under={sf['3']/s_n:.3f}")
        print(f"  realized error rate: {1 - s1:.3f} (real: {1 - r1:.3f})")
        print(f"  L1 distance to real finding mix: {l1:.3f}")
        print("  == element bucket (real vs synth ratio) ==")
        show("element bucket", rb, sb, r_n, s_n, top=12)
        print("  == nature (real vs synth ratio) ==")
        show("nature", rn, sn, r_n, s_n, top=12)


if __name__ == "__main__":
    main()
