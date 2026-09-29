"""Calibrate injection so REALIZED rates match the empirical FY2024 targets.

Phase 1 — injection coin per earner status: the retry loop loses a fraction
of injections (no-op draws exhaust the budget), and the loss differs by
earner status. p_inject(type) = empirical_P(err | type) /
P(materialize | inject, type).

Phase 2 — 97-resolution coin per bucket: timing-nature (97) variances are
directionally ambiguous, so the generator resolves each 97 into an
over- or under-direction corruption. Over-direction deduction corruptions
materialize less often than under-direction ones (the excess-shelter cap
absorbs increases), so resolving with the raw empirical P(over|bucket,97)
realizes too few overs. Measure P(materialize | forced-over/under) per
bucket and solve for the coin that lands realized P(over|bucket,97) on the
empirical target: c = t*m_u / (t*m_u + (1-t)*m_o).

Writes experiments/inject.json. Re-run whenever the sampler, corruptors, or
retry budget change — same maintenance story as eff.json.

Usage: python experiments/calibrate_injection.py [--n 6000] [--n97 4000] [--max-attempts 12]
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import errors as E  # noqa: E402
from synth import household  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

ROOT = Path(__file__).resolve().parent


def calibrate_97_direction(dist, n=4000, seed=21):
    rng = random.Random(seed)
    targets = dist.get("p_over_97_given_bucket", {})
    coins = {}
    for bucket, t in sorted(targets.items()):
        rates = {}
        for force in ("over", "under"):
            m = nsum = 0
            for _ in range(n):
                f = household.sample_household(rng)
                if bucket == "medical" and not f["senior_disabled"]:
                    continue
                agency = dict(f)
                truth = dict(f)
                tc, _ = E._apply_one(agency, truth, bucket, 97, rng, dist,
                                     _force_97_dir=force)
                if tc:
                    truth.update(tc)
                nsum += 1
                b0 = benefit_mod.compute(truth)["benefit"]
                b1 = benefit_mod.compute(agency)["benefit"]
                if b1 != b0:
                    m += 1
            rates[force] = m / max(nsum, 1)
        mo, mu = rates["over"], rates["under"]
        denom = t * mu + (1 - t) * mo
        c = (t * mu / denom) if denom > 0 else t
        coins[bucket] = round(min(0.99, max(0.01, c)), 4)
        print(f"  {bucket:10s} target={t:.3f} m_over={mo:.3f} "
              f"m_under={mu:.3f} -> coin={coins[bucket]:.3f}")
    return coins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--n97", type=int, default=4000)
    ap.add_argument("--max-attempts", type=int, default=12)
    args = ap.parse_args()

    dist = load_dist(ROOT / "dist.json")
    # force injection: coin = 1 regardless of earner status. Note inject()
    # prefers dist["injection_rate"] when present, so override that too.
    d2 = dict(dist, error_rate=1.0, error_rate_given_earner=1.0,
              error_rate_given_no_earner=1.0,
              injection_rate={"earner": 1.0, "no_earner": 1.0})

    print("phase 1: injection coin per earner status")
    rng = random.Random(11)
    trials = {"earner": 0, "no_earner": 0}
    materialized = {"earner": 0, "no_earner": 0}
    for _ in range(args.n):
        f = household.sample_household(rng)
        key = "earner" if f["earned"] > 0 else "no_earner"
        case = E.inject(f, rng, d2, max_attempts=args.max_attempts)
        trials[key] += 1
        if case["finding"] != 1:
            materialized[key] += 1

    out = {}
    for key in ("earner", "no_earner"):
        m = materialized[key] / trials[key]
        empirical = dist[f"error_rate_given_{key}"]
        coin = min(empirical / m, 1.0)
        out[key] = round(coin, 4)
        print(f"{key}: P(materialize|inject)={m:.3f} empirical_P(err)={empirical:.3f} "
              f"-> coin={coin:.3f} (n={trials[key]})")

    print("phase 2: 97-resolution coin per bucket")
    out["p_over_97_resolve"] = calibrate_97_direction(dist, n=args.n97)

    out["_note"] = ("Injection coin per earner status, corrected for retry-loop "
                    "attrition so realized P(error|status) matches FY2024 QC. "
                    "p_over_97_resolve corrects the 97 direction coin for "
                    "directional materialization asymmetry (shelter cap).")
    json.dump(out, open(ROOT / "inject.json", "w"), indent=1)
    print("wrote", ROOT / "inject.json")


if __name__ == "__main__":
    main()
