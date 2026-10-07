"""Measure P(a drawn (bucket, nature-direction) corruption changes the
benefit), for retry-loop importance weighting.

The retry loop discards attempts that don't move the benefit, so the
RECORDED (bucket, nature) mix is skewed toward easy-to-materialize draws:
always-applicable hhcomp/arithmetic inflate ~3.4x, and over-direction
deduction natures (53, 56) deflate because the excess-shelter cap absorbs
increases. Two-level correction (both stored in eff.json):

  bucket level:    draw buckets with weight 1/eff_b, where eff_b is the
                   materialization rate under the weighted nature draw.
  direction level: within a bucket, draw natures with weight w_{b,d}
                   proportional to 1/m_{b,d} (m = P(materialize | bucket,
                   direction class)), normalized so the recorded
                   P(direction | bucket) reproduces the empirical mix.

Direction classes: over={35,37,38,53,56,7}, under={44,52,57,6,13},
other={97,99,40,...}. Nature 97 resolves stochastically (see errors.py), so
it lives in "other" with its blended rate.

eff_b (analytical, no second pass needed):
    eff_b = sum_d w_{b,d} * p_{b,d} * m_{b,d}

Re-run whenever the corruptors change. calibrate_injection.py and inject()
consume this file's output via distutil.
"""
import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth import benefit as benefit_mod, errors, household  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

ROOT = Path(__file__).resolve().parent

OVER_NATURES = {35, 37, 38, 53, 56, 7}
UNDER_NATURES = {44, 52, 57, 6, 13}


def dirclass(nature):
    if nature in OVER_NATURES:
        return "over"
    if nature in UNDER_NATURES:
        return "under"
    return "other"


def _sample(rng, probs):
    x = rng.random() * sum(probs.values())
    for k, v in probs.items():
        x -= v
        if x <= 0:
            return k
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--bundle", default=None,
                    help="read dist.json / write outputs in this directory instead of experiments/ "
                         "(exp55: a separately calibrated reportable-variance bundle)")
    args = ap.parse_args()
    global ROOT
    if args.bundle:
        ROOT = Path(args.bundle).resolve()

    dist = load_dist(ROOT / "dist.json")
    buckets = list(dist["bucket_probs"])
    # empirical P(direction | bucket) from the marginal nature mix
    p_dir = {}
    for b in buckets:
        tot = sum(dist["nature_given_bucket"][b].values())
        c = Counter()
        for ntr, p in dist["nature_given_bucket"][b].items():
            c[dirclass(ntr)] += p / tot
        p_dir[b] = dict(c)

    rng = random.Random(11)
    mat = defaultdict(Counter)   # mat[b][d] = materialized count
    tot = defaultdict(Counter)   # tot[b][d] = trial count
    for _ in range(args.n):
        f = household.sample_household(rng)
        b = rng.choice(buckets)
        # Draw from the earner-conditional mix, exactly as _draw_nature does
        # (minus the direction weights, which rescale whole direction classes
        # and therefore do not change the within-class materialization rate).
        # The old code drew from the marginal mix, which mis-measures m_d
        # whenever the conditional nature composition differs (deduction
        # buckets: shelter-over 0.178 -> 0.254, sua-under 0.558 -> 0.673).
        nkey = ("nature_given_bucket_earner" if f.get("earned", 0) > 0
                else "nature_given_bucket_no_earner")
        nmix = dist.get(nkey, {}).get(b) or dist["nature_given_bucket"][b]
        nature = _sample(rng, nmix)
        if b == "medical" and not f["senior_disabled"]:
            continue
        agency = dict(f)
        truth = dict(f)
        tc, _ = errors._apply_one(agency, truth, b, int(nature), rng, dist)
        if tc:
            truth.update(tc)
        d = dirclass(int(nature))
        tot[b][d] += 1
        b0 = benefit_mod.compute(truth)["benefit"]
        b1 = benefit_mod.compute(agency)["benefit"]
        if b1 != b0:
            mat[b][d] += 1

    eff_bucket = {}
    dir_mat = {}
    dir_w = {}
    for b in buckets:
        if b == "arithmetic":
            # Handled as direct benefit noise in inject(): always materializes.
            m = {"over": 1.0, "under": 1.0, "other": 1.0}
        else:
            m = {}
            for d in ("over", "under", "other"):
                m[d] = mat[b][d] / tot[b][d] if tot[b][d] else 1.0
                m[d] = min(1.0, max(0.02, m[d]))  # clip: avoid 1/0 blowups
        dir_mat[b] = {d: round(m[d], 3) for d in m}
        # w_{b,d} propto 1/m, normalized over the empirical dir mix
        z = sum(p_dir[b].get(d, 0) / m[d] for d in m)
        w = {d: (1 / m[d]) / z for d in m}
        dir_w[b] = {d: round(w[d], 3) for d in w}
        eff_bucket[b] = round(sum(w[d] * p_dir[b].get(d, 0) * m[d] for d in m), 3)

    out = {
        "bucket": eff_bucket,
        "dir_materialization": dir_mat,
        "dir_weight": dir_w,
        "_note": ("bucket: P(materialize|bucket) under the direction-weighted "
                  "nature draw. dir_weight: per-(bucket, direction-class) "
                  "importance weights reproducing the empirical nature mix."),
    }
    json.dump(out, open(ROOT / "eff.json", "w"), indent=1)
    print(json.dumps({"bucket": eff_bucket}, indent=1))
    print("dir_materialization:")
    print(json.dumps(dir_mat, indent=1))
    print("wrote", ROOT / "eff.json")


if __name__ == "__main__":
    main()
