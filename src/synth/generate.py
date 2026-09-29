"""CLI: generate synthetic QC-style labeled cases as JSONL.

Usage:
    python -m synth.generate --n 20000 --seed 7 --dist experiments/dist.json --out data/synth.jsonl
"""
import argparse
import json
import random
import sys
from pathlib import Path

from . import errors, household


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dist", required=True, help="empirical distribution JSON")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.dist) as fh:
        dist = json.load(fh)
    eff_path = Path(args.dist).parent / "eff.json"
    if eff_path.exists():
        with open(eff_path) as fh:
            dist["effectiveness"] = json.load(fh)
    # json keys are strings; normalize back to ints where needed
    dist["nature_given_bucket"] = {
        b: {int(k): v for k, v in d.items()} for b, d in dist["nature_given_bucket"].items()
    }
    dist["cause_given_bucket"] = {
        b: {int(k): v for k, v in d.items()} for b, d in dist["cause_given_bucket"].items()
    }
    dist["bucket_probs"] = {b: float(v) for b, v in dist["bucket_probs"].items()}

    rng = random.Random(args.seed)
    with open(args.out, "w") as out:
        for _ in range(args.n):
            facts = household.sample_household(rng)
            case = errors.inject(facts, rng, dist)
            out.write(json.dumps(case) + "\n")
    print(f"wrote {args.n} cases -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
