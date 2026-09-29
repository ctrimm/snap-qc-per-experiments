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
    ap.add_argument("--persistent-buckets", action=argparse.BooleanOptionalAction,
                    default=True,
                    help="exp7 (default on): draw each variance's bucket once "
                         "and apply the nature once — recorded if the benefit "
                         "moves, else dropped (hybrid single-draw-and-drop; "
                         "kills the cross-bucket retry lottery). "
                         "--no-persistent-buckets restores the old retry loop.")
    # exp24: restores the pre-exp24 scalar 1/eff_b materialization
    # correction in persistent mode (reproducibility of old chronicles).
    # Default (off) uses the re-measured per-(bucket,stratum) keep-rate
    # matrix as the generator default. Does not touch the retry loop.
    ap.add_argument("--legacy-materialization", action="store_true",
                    default=False,
                    help="exp24: use the old scalar materialization "
                         "correction instead of the re-measured "
                         "per-(bucket,stratum) matrix (persistent mode).")
    args = ap.parse_args()

    dist = load_dist(args.dist)

    rng = random.Random(args.seed)
    with open(args.out, "w") as out:
        for _ in range(args.n):
            facts = household.sample_household(rng)
            case = errors.inject(facts, rng, dist, max_attempts=args.max_attempts,
                                 persistent_buckets=args.persistent_buckets,
                                 legacy_materialization=args.legacy_materialization)
            out.write(json.dumps(case) + "\n")
    print(f"wrote {args.n} cases -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
