"""Experiment 11: senior-conditioned bucket mixes.

Hypothesis (north-star gate: calibration). The medical element residual
(0.11x) is a DRAW problem, not a materialization problem: the bucket mix is
conditional on earner status only, but real P(medical variance) is 0.109 on
(no-earner, senior/disabled) vs 0.048 on (no-earner, non-senior). Conditioning
the draw on senior/disabled status should move medical toward ~1.0x without
regressing the finding mix.

Method:
  1. Measure the real FY2024 bucket mix in 4 strata:
     (earner/no-earner) x (senior-or-disabled / neither), from held-out QC
     microdata (never committed).
  2. Store as bucket_probs_given_{earner,no_earner}_{senior,nonsenior} in
     dist.json; _applicable_buckets picks the stratum from facts.
  3. Regenerate (persistent mode, seed 7) and compare the medical element
     ratio and finding-mix L1 against the pre-change run.

Usage: python3 experiments/exp11_senior_bucket_mix.py
"""
import argparse
import csv
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth.codebook import element_bucket  # noqa: E402

REAL = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
SSI_COLS = [f"SSI{i}" for i in range(1, 9)]
EL_COLS = [f"ELEMENT{i}" for i in range(1, 10)]


def measure_strata(path):
    """Real bucket shares in 4 strata. Returns dict key->Counter."""
    strata = Counter()
    totals = Counter()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            earner = float(row["FSEARN"] or 0) > 0
            senior = int(row["FSNELDER"] or 0) > 0 or any(
                int(row[c] or 0) > 0 for c in SSI_COLS)
            key = ("earner" if earner else "no_earner",
                   "senior" if senior else "nonsenior")
            totals[key] += 1
            for c in EL_COLS:
                e = (row[c] or "").strip()
                if e:
                    strata[(key, element_bucket(int(e)))] += 1
    # normalize to shares within stratum
    out = {}
    for key in totals:
        tot = sum(v for (k, _), v in strata.items() if k == key)
        out["_".join(key)] = {b: strata[(key, b)] / tot
                              for (k, b) in strata if k == key}
    return out, totals


def gen(n, seed, dist_path):
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        path = tf.name
    cmd = [sys.executable, "-m", "synth.generate", "--n", str(n),
           "--seed", str(seed), "--dist", str(dist_path),
           "--max-attempts", "12", "--out", path]
    subprocess.run(cmd, cwd=ROOT / "src", check=True, capture_output=True)
    return path


def finding_mix(path):
    c = Counter()
    for line in open(path):
        line = line.strip()
        if line:
            c[json.loads(line)["finding"]] += 1
    tot = sum(c.values())
    return {k: c[k] / tot for k in (1, 2, 3)}


def element_mix(path):
    c = Counter()
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        for v in json.loads(line).get("variances", []):
            c[v["element_bucket"]] += 1
    tot = sum(c.values())
    return {k: v / tot for k, v in c.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dist", default=str(ROOT / "experiments/dist.json"))
    args = ap.parse_args()

    print("measuring real 4-stratum bucket mix...", flush=True)
    strata, totals = measure_strata(REAL)
    for k in sorted(strata):
        ek, sk = k.split("_", 1) if "_" in k else (k, "")
        # k is like "earner_senior"; recover tuple key
        tkey = ("no_earner" if k.startswith("no_earner") else "earner",
                "senior" if k.endswith("senior") else "nonsenior")
        print(f"  {k}: n_cases={totals[tkey]}")
        top = sorted(strata[k].items(), key=lambda kv: -kv[1])[:4]
        print("    " + ", ".join(f"{b}={p:.3f}" for b, p in top))

    dist = json.load(open(args.dist))
    # restrict to the 8 buckets the generator models (drop assets,
    # childsupport, income_total, other, reporting, standard) and renormalize
    keep = set(dist["bucket_probs_given_earner"].keys())
    new_keys = {}
    for stratum, mix in strata.items():
        filt = {b: p for b, p in mix.items() if b in keep}
        tot = sum(filt.values())
        filt = {b: p / tot for b, p in filt.items()}
        key = f"bucket_probs_given_{stratum}"
        new_keys[key] = filt
        print(f"  {key}: medical={filt.get('medical', 0):.3f}")
    dist.update(new_keys)
    dist_path = Path(args.dist)
    json.dump(dist, open(dist_path, "w"), indent=1)
    print(f"wrote {len(new_keys)} stratum keys to dist.json")

    print("regenerating (persistent mode)...", flush=True)
    spath = gen(args.n, args.seed, dist_path)
    fm = finding_mix(spath)
    em = element_mix(spath)
    real_fm = {1: 0.603, 2: 0.239, 3: 0.158}
    l1 = sum(abs(fm[k] - real_fm[k]) for k in real_fm)
    print(f"finding mix: {fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f}  L1={l1:.3f}")
    print(f"medical share of variances: {em.get('medical', 0):.4f}")


if __name__ == "__main__":
    main()
