"""Exp 6 — calibration v4: income-eligibility screen on the sampler.

Exp 5's residual: realized error rate stuck at 30.2% vs 39.7% real, correct
at 69.8% vs 60.3%. Diagnosis: the sampler drew households that would fail
SNAP gross/net income tests (high earners) — essentially absent from real QC
(4/44,891 FY2024 cases with $0 issued benefit). Their corruptions cannot
materialize against the benefit floor, so injection attempts exhaust retries
and decay into clean cases, inflating "correct" and starving both error
directions (under especially: the floor absorbs under-direction moves).

Fix: the sampler now rejects draws failing the FY2024 gross/net income
limits (harness approximations in params.py) and resamples; the $23 minimum
benefit applies to all eligible 1-2 person households. Earnings were refit to
real FSEARN medians by household size since the old wage distribution mostly
failed the new screen.

Compares against exp 5 (69.8/19.3/10.9, quoted) and the real file.

Usage: python experiments/exp6_eligibility_screen.py [--n 20000] [--seed 7]
"""
import argparse
import json
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
    print(f"REAL:  correct={r1:.3f} over={rf['2']/r_n:.3f} under={rf['3']/r_n:.3f}")
    print("EXP5 (omission coherence): correct=0.698 over=0.193 under=0.109, "
          "realized err=0.302")

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
    print(f"\nEXP6 (eligibility screen): correct={s1:.3f} over={s2:.3f} under={s3:.3f}")
    err = 1 - s1
    print(f"  realized error rate: {err:.3f} (real: {1 - r1:.3f})")
    print(f"  over share of errors: {s2/err:.3f} (real: {(rf['2']/r_n)/(1-r1):.3f})")
    l1 = abs(s1 - r1) + abs(s2 - rf["2"]/r_n) + abs(s3 - rf["3"]/r_n)
    print(f"  L1 distance to real finding mix: {l1:.3f} (exp5: 0.191)")

    # sampler base rates after screening
    n = 0
    base = {"earned": 0, "unearned": 0, "shelter": 0, "zero_ben": 0}
    for line in open(path):
        n += 1
        c = json.loads(line)
        f = c["facts"]
        if f["earned"] > 0: base["earned"] += 1
        if f["unearned"] > 0: base["unearned"] += 1
        if f["shelter"] > 0: base["shelter"] += 1
        if c["correct_benefit"] == 0: base["zero_ben"] += 1
    print("  base rates: " + ", ".join(f"{k}={v/n:.3f}" for k, v in base.items()))
    print("  real:        earned=0.273, unearned=0.618, shelter=0.632, zero_ben~=0.000")

    r_var, s_var = sum(rb.values()), sum(sb.values())
    show("element bucket", rb, sb, r_var, s_var, top=10)
    show("nature", rn, sn, r_var, s_var, top=10)
    show("cause bucket", rc, sc, r_var, s_var, top=6)


if __name__ == "__main__":
    main()
