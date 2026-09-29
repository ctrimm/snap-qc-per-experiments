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
from .distutil import load_dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dist", required=True, help="empirical distribution JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-attempts", type=int, default=12,
                    help="retry budget per error case in errors.inject")
    args = ap.parse_args()

    dist = load_dist(args.dist)

    rng = random.Random(args.seed)
    with open(args.out, "w") as out:
        for _ in range(args.n):
            facts = household.sample_household(rng)
            case = errors.inject(facts, rng, dist, max_attempts=args.max_attempts)
            out.write(json.dumps(case) + "\n")
    print(f"wrote {args.n} cases -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
