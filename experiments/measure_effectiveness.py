"""Measure per-bucket P(corruption moves the benefit | bucket), so the injector
can upweight buckets whose corruptions often no-op (ceiling/cap absorption)
and recover the empirical mix after retry-filtering.

Usage: python experiments/measure_effectiveness.py [--n 4000]
Writes experiments/eff.json
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit as benefit_mod, errors, household  # noqa: E402

ROOT = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    args = ap.parse_args()

    dist = json.load(open(ROOT / "dist.json"))
    for k in ("nature_given_bucket", "cause_given_bucket"):
        dist[k] = {b: {int(kk): v for kk, v in d.items()} for b, d in dist[k].items()}

    rng = random.Random(123)
    moved = Counter()
    tried = Counter()
    for _ in range(args.n):
        facts = household.sample_household(rng)
        correct = benefit_mod.compute(facts)["benefit"]
        applicable = errors._applicable_buckets(facts, dist, rng)
        for bucket in applicable:
            nature = int(errors._sample(rng, dist["nature_given_bucket"][bucket]))
            corrupted, _ = errors._apply_one(facts, bucket, nature, rng)
            noise = 0.0
            if bucket == "arithmetic":
                noise = rng.choice([-1, 1]) * rng.uniform(10, 60)
            issued = max(0, int(round(benefit_mod.compute(corrupted)["benefit"] + noise)))
            tried[bucket] += 1
            if issued != correct:
                moved[bucket] += 1

    eff = {b: max(moved[b] / tried[b], 0.02) for b in tried}
    json.dump(eff, open(ROOT / "eff.json", "w"), indent=1)
    print(json.dumps({b: round(eff[b], 3) for b in sorted(eff)}, indent=1))


if __name__ == "__main__":
    main()
