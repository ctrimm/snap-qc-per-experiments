"""Exp 5 — calibration v3: omission-coherence fix.

Exp 3's residual: under-issuances stuck at 9.4% vs 15.8% real, correct at
70.2% vs 60.3%. Diagnosis: omission-type variances (income natures 35/37/38,
deduction natures 52/57) drawn on zero-base households no-op'd — the sampler
draws the truth first and the variance independently, so "agency omitted X"
was incoherent when the truth had no X. Real QC data confirms the pattern:
222 FY2024 under-issuance cases carry a shelter variance with agency-view
shelter = $0 (the truth had shelter costs the agency missed).

Fix: on a zero base, omission-type natures correct the truth upward (the
truth gains the omitted amount; the agency view stays at the omitted value)
instead of no-op'ing. Commission-type natures keep corrupting the agency
view (44: agency counted income that wasn't there; 53: agency claimed a
deduction that doesn't exist).

Compares the new finding mix against exp 3b (70.2/20.4/9.4, quoted from the
exp3 chronicle) and the real file (60.3/23.9/15.8).

Usage: python experiments/exp5_omission_coherence.py [--n 20000] [--seed 7]
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from exp1_calibration import real_marginals, synth_marginals, show  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    print("loading real marginals...", flush=True)
    rf, rb, rn, rc, ra, r_n = real_marginals()
    r1 = rf["1"] / r_n
    print(f"REAL:  correct={rf['1']/r_n:.3f} over={rf['2']/r_n:.3f} "
          f"under={rf['3']/r_n:.3f}")
    print("EXP3b (direction fix + retry 12): correct=0.702 over=0.204 under=0.094")

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        path = tf.name
    subprocess.run(
        [sys.executable, "-m", "synth.generate", "--n", str(args.n),
         "--seed", str(args.seed), "--dist", str(ROOT / "experiments/dist.json"),
         "--max-attempts", "12", "--out", path],
        cwd=ROOT / "src", check=True, capture_output=True,
    )
    sf, sb, sn, sc, sa, s_n = synth_marginals(path)
    s1, s2, s3 = sf["1"] / s_n, sf["2"] / s_n, sf["3"] / s_n
    print(f"\nEXP5 (omission coherence): correct={s1:.3f} over={s2:.3f} under={s3:.3f}")
    err = 1 - s1
    print(f"  realized error rate: {err:.3f} (real: {1 - r1:.3f})")
    print(f"  over share of errors: {s2/err:.3f} (real: {(rf['2']/r_n)/(1-r1):.3f})")
    l1 = abs(s1 - rf["1"]/r_n) + abs(s2 - rf["2"]/r_n) + abs(s3 - rf["3"]/r_n)
    print(f"  L1 distance to real finding mix: {l1:.3f} (exp3b: 0.198)")

    r_var, s_var = sum(rb.values()), sum(sb.values())
    show("element bucket", rb, sb, r_var, s_var, top=10)
    show("nature", rn, sn, r_var, s_var, top=10)
    show("cause bucket", rc, sc, r_var, s_var, top=6)


if __name__ == "__main__":
    main()
