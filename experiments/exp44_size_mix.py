#!/usr/bin/env python3
"""Experiment 43 — household size-mix fit + re-trial of the re-sliced medical mixes.

exp32 left medical at 0.71x (gate 0.75x) and named the binding constraint:
the household size mix (real 59.7% size-1 vs synth 46.8%). The re-sliced
empirical mixes (exp28_resliced_mixes.json, still staged) are correct as
conditionals but blow up hhcomp/arithmetic on the wrong stratum composition.

This experiment:
  [0] Measures the real FY2024 post-screen size mix fresh (aggregates only;
      sizes 7+ folded into 6).
  [1] Fits pre-screen size weights by fixed-point simulation so the
      post-screen mix lands on the real targets (exp32's senior-table
      technique). Patches household._SIZE_WEIGHTS in-process only.
  [1b] Blast-radius audit: re-measures _DEPCARE_KID_WEIGHT on the new
      sampler (documented maintenance); checks kid-count-by-size and the
      phase-1 per-type rates (diagnostics). The re-measured kid-weight is
      APPLIED in arms B/C (it is unconfounded sampler maintenance).
  [2] Trials, paired seeds 7/8, 20k, mechanisms ON:
        A  exp32 baseline (legacy size weights)
        B  A + fitted size weights (in-process)
        C  B + re-sliced mixes in-process (dist.json untouched)
      B-vs-A isolates the size-mix effect; C-vs-B isolates the mix change.
  [3] Matrix interaction check with the size-fix effect ISOLATED
      ((b) size-fix + mech ON vs (a) legacy-size + mech ON, 150k, seed 11,
      exp32's procedure). Adopt a re-measured matrix only if >=15/32 cells
      shift >=0.05 on the isolated effect (exp29's rule) -- and then only
      jointly with an effectiveness re-fit (exp31's rule: never the matrix
      alone; the joint re-fit would be a staged follow-up, not done here).
  [4] Final validation of the kept set on seeds 7/8 + dollar marginals.

Verdict bars: medical >= 0.75x AND finding L1 <= 0.030 AND no other bucket
regressing more than 0.10x vs arm A, AND dollar share <=$56 within +-0.02
of baseline.

Falsification: if C lands medical >= 0.75x but hhcomp stays > 1.30x, the
re-sliced mixes are wrong (not the composition) -> adopt B alone, keep the
mixes staged, say so.

Real QC microdata is held-out validation: aggregates are read, nothing
per-row is committed. Committed dist.json/eff.json/inject.json are never
touched. src/synth/household.py carries one behavior-neutral refactor
(_SIZE_WEIGHTS module constant); the experiment only patches it in-process.
"""
import copy
import csv
import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR.parent / "src"))          # synth package
from synth import dollar_mech, errors, household        # noqa: E402
from synth.codebook import element_bucket              # noqa: E402
from synth.distutil import load_dist                    # noqa: E402

REAL = (EXP_DIR.parent.parent / "snap-qc-data/raw/qcfy2024_csv"
        / "qc_pub_fy2024.csv")
BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]
STRATA = ["no_earner_nonsenior", "earner_nonsenior",
          "no_earner_senior", "earner_senior"]
SEEDS = (7, 8)
LEGACY_W = list(household._SIZE_WEIGHTS)  # committed values, restored after


def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def real_size_mix(path):
    """Real FY2024 post-screen size mix; sizes 7+ folded into 6."""
    c = Counter()
    n = 0
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            s = int(fnum(row["CERTHHSZ"]))
            c[min(s, 6)] += 1
    return [c[i] / n for i in range(1, 7)], n


def post_screen_mix(weights, n=60000, seed=5):
    """Synth post-screen size mix under candidate pre-screen weights."""
    household._SIZE_WEIGHTS = list(weights)
    rng = random.Random(seed)
    c = Counter()
    tot = 0
    for _ in range(n):
        f = household._sample_unscreened(rng)
        if household._income_eligible(f):
            c[f["hh_size"]] += 1
            tot += 1
    household._SIZE_WEIGHTS = LEGACY_W
    return [c[i] / tot for i in range(1, 7)]


def fit_size_weights(targets, tol=0.005, max_iter=15):
    """Fixed-point: pre-screen weights -> post-screen mix == targets."""
    w = list(targets)
    for it in range(max_iter):
        obs = post_screen_mix(w)
        err = max(abs(o - t) for o, t in zip(obs, targets))
        print(f"  iter {it}: max|obs-tgt|={err:.4f} "
              f"obs={[round(o, 4) for o in obs]}")
        if err < tol:
            break
        w = [wi * ti / max(oi, 1e-6) for wi, ti, oi in zip(w, targets, obs)]
        s = sum(w)
        w = [wi / s for wi in w]
    return [round(x, 4) for x in w]


def real_aggregates(path):
    finding, bucket = Counter(), Counter()
    signed = []
    n = 0
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            st = row["STATUS"].strip()
            finding[st] += 1
            amt = fnum(row["AMTERR"])
            if st == "2":
                signed.append(amt)
            elif st == "3":
                signed.append(-amt)
            for i in range(1, 10):
                e = (row[f"ELEMENT{i}"] or "").strip()
                if e:
                    bucket[element_bucket(int(e))] += 1
    ab = sorted(abs(x) for x in signed)
    return {
        "finding": {1: finding["1"] / n, 2: finding["2"] / n,
                    3: finding["3"] / n},
        "per_case": {b: bucket[b] / n for b in BUCKETS},
        "le56": sum(1 for x in ab if x <= 56) / len(ab),
        "n": n,
    }


def gen_cases(n, seed, dist):
    rng = random.Random(seed)
    return [dollar_mech.inject_case(household.sample_household(rng), rng,
                                    dist, max_attempts=12,
                                    persistent_buckets=True)
            for _ in range(n)]


def mixes(cases):
    f = Counter(c["finding"] for c in cases)
    n = len(cases)
    b = Counter()
    d_all = []
    for c in cases:
        if c["finding"] == 2:
            d_all.append(c["dollar_error"])
        elif c["finding"] == 3:
            d_all.append(-c["dollar_error"])
        else:
            continue
        for v in c["variances"]:
            b[v["element_bucket"]] += 1
    ab = sorted(abs(x) for x in d_all)
    return {
        "finding": {k: f[k] / n for k in (1, 2, 3)},
        "per_case": {k: b[k] / n for k in BUCKETS},
        "le56": sum(1 for x in ab if x <= 56) / len(ab) if ab else 0.0,
        "n": n,
    }


def l1(a, b):
    return sum(abs(a[k] - b.get(k, 0.0)) for k in a)


def resliced_dist(dist):
    """dist copy with exp28's re-sliced 4-stratum mixes (in-process only)."""
    rs = json.load(open(EXP_DIR / "exp28_resliced_mixes.json"))["mixes"]
    d = copy.deepcopy(dist)
    for k, v in rs.items():
        d[k] = dict(v)
    return d


class fitted_size:
    """Patch household._SIZE_WEIGHTS in-process (restored on exit)."""

    def __init__(self, weights):
        self.weights = list(weights)

    def __enter__(self):
        household._SIZE_WEIGHTS = list(self.weights)

    def __exit__(self, *a):
        household._SIZE_WEIGHTS = LEGACY_W


class fitted_sampler:
    """Size weights + re-measured _DEPCARE_KID_WEIGHT (documented
    maintenance: the weight bakes in P_synth(kid|s), a pure sampler
    property that the size fix shifts; unconfounded, cf. exp32)."""

    def __init__(self, weights, kid_weight):
        self.weights = list(weights)
        self.kid_weight = dict(kid_weight)
        self._saved = None

    def __enter__(self):
        household._SIZE_WEIGHTS = list(self.weights)
        self._saved = dict(errors._DEPCARE_KID_WEIGHT)
        errors._DEPCARE_KID_WEIGHT.update(self.kid_weight)

    def __exit__(self, *a):
        household._SIZE_WEIGHTS = LEGACY_W
        errors._DEPCARE_KID_WEIGHT.clear()
        errors._DEPCARE_KID_WEIGHT.update(self._saved)


def remeasure_kid_weight(n=100000, seed=5):
    """_DEPCARE_KID_WEIGHT = 1/P_synth(kid|s); pure sampler property."""
    rng = random.Random(seed)
    kid = Counter()
    tot = Counter()
    for _ in range(n):
        f = household.sample_household(rng)
        s = ("earner" if f["earned"] > 0 else "no_earner") + "_" + \
            ("senior" if f["senior_disabled"] else "nonsenior")
        tot[s] += 1
        if f.get("n_kids", 0) > 0:
            kid[s] += 1
    return {s: round(tot[s] / max(kid[s], 1), 3) for s in STRATA}


def show_trial(label, m, real, base_m=None):
    print(f"\n-- {label} --")
    print(f"  finding L1={l1(m['finding'], real['finding']):.3f} "
          f"(mix {[round(m['finding'][k], 3) for k in (1, 2, 3)]}) "
          f"le56={m['le56']:.2f}")
    for b in BUCKETS:
        r = m["per_case"][b] / real["per_case"][b] if real["per_case"][b] else 0
        tag = ""
        if base_m is not None:
            rb = base_m["per_case"][b] / real["per_case"][b] \
                if real["per_case"][b] else 0
            tag = f" (A: {rb:.2f}x)"
        print(f"  {b:10s} {r:.2f}x{tag}")


# --------------------------------------------------------------------------
# stage 3: matrix isolated-effect check (exp32's procedure)
# --------------------------------------------------------------------------
_ORIG_IP = errors._inject_persistent
_KR_DRAWN = Counter()
_KR_RECORDED = Counter()


def _kr_ip(facts, rng, dist, applicable, dir_w, max_attempts, stats=None,
           **kw):
    s = errors._stratum_key(facts)
    local = {"drawn": Counter(), "recorded": Counter()}
    out = _ORIG_IP(facts, rng, dist, applicable, dir_w, max_attempts,
                   stats=local, **kw)
    for b, c in local["drawn"].items():
        _KR_DRAWN[(b, s)] += c
    for b, c in local["recorded"].items():
        _KR_RECORDED[(b, s)] += c
    return out


def remeasure_matrix(dist, n=150000, seed=11):
    _KR_DRAWN.clear()
    _KR_RECORDED.clear()
    d_mech = dollar_mech.enable_adopted(dist)
    errors._inject_persistent = _kr_ip
    try:
        gen_cases(n, seed, d_mech)
    finally:
        errors._inject_persistent = _ORIG_IP
        dollar_mech.disable()
    mat = {}
    for b in BUCKETS:
        mat[b] = {}
        for s in STRATA:
            d = _KR_DRAWN[(b, s)]
            r = _KR_RECORDED[(b, s)]
            mat[b][s] = round(min(1.0, max(0.02, r / d if d else 1.0)), 6)
    return mat


def main():
    print("== [0] real FY2024 post-screen size mix ==")
    targets, n = real_size_mix(REAL)
    print(f"  n={n} targets={[round(t, 4) for t in targets]} "
          f"(sum={sum(targets):.4f})")
    legacy_obs = post_screen_mix(LEGACY_W)
    print(f"  legacy synth post-screen={[round(o, 4) for o in legacy_obs]}")

    print("\n== [1] fixed-point fit of pre-screen size weights ==")
    fitted = fit_size_weights(targets)
    print(f"  fitted pre-screen weights={fitted}")
    final_obs = post_screen_mix(fitted)
    print(f"  final post-screen={[round(o, 4) for o in final_obs]}")

    print("\n== [1b] blast radius: kid-weight re-measurement ==")
    with fitted_size(fitted):
        kw = remeasure_kid_weight()
    cur = dict(errors._DEPCARE_KID_WEIGHT)
    print(f"  committed kid-weight={cur}")
    print(f"  re-measured (new sampler)={kw}")
    print("  (applied in arms B/C via fitted_sampler)")

    print("\n== real aggregates (held-out) ==")
    real = real_aggregates(REAL)
    dist = load_dist(str(EXP_DIR / "dist.json"))

    print("\n== [2] trials ==")
    results = {}
    for seed in SEEDS:
        d_mech = dollar_mech.enable_adopted(dist)
        mA = mixes(gen_cases(20000, seed, d_mech))
        dollar_mech.disable()
        with fitted_sampler(fitted, kw):
            d_mech = dollar_mech.enable_adopted(dist)
            mB = mixes(gen_cases(20000, seed, d_mech))
            d_mech_rs = dollar_mech.enable_adopted(resliced_dist(dist))
            mC = mixes(gen_cases(20000, seed, d_mech_rs))
            dollar_mech.disable()
        results[seed] = (mA, mB, mC)
        show_trial(f"A baseline (seed {seed})", mA, real)
        show_trial(f"B +size mix (seed {seed})", mB, real, mA)
        show_trial(f"C +resliced mixes (seed {seed})", mC, real, mA)

    print("\n== [3] matrix isolated-effect check ==")
    mat_a = remeasure_matrix(dist)          # (a) legacy-size + mech ON
    with fitted_sampler(fitted, kw):
        mat_b = remeasure_matrix(dist)      # (b) size-fix + mech ON
    n_shift = sum(
        1 for b in BUCKETS for s in STRATA
        if abs(mat_b[b][s] - mat_a[b][s]) >= 0.05)
    print(f"  isolated size-fix effect: {n_shift}/32 cells shift >=0.05 "
          f"(bar: >=15 to trigger joint re-fit)")
    worst = max((abs(mat_b[b][s] - mat_a[b][s]), b, s)
                for b in BUCKETS for s in STRATA)
    print(f"  worst cell: {worst[1]}/{worst[2]} {worst[0]:.3f}")

    print("\n== [4] verdict inputs ==")
    for seed in SEEDS:
        mA, mB, mC = results[seed]
        med_c = mC["per_case"]["medical"] / real["per_case"]["medical"]
        l1_c = l1(mC["finding"], real["finding"])
        # worst other-bucket regression vs A (ratio points away from 1.0x)
        worst_reg = 0.0
        worst_b = None
        for b in BUCKETS:
            if b == "medical":
                continue
            ra = mA["per_case"][b] / real["per_case"][b]
            rc = mC["per_case"][b] / real["per_case"][b]
            # regression = moved away from 1.0x
            if abs(rc - 1.0) > abs(ra - 1.0) + 1e-9:
                d = abs(rc - 1.0) - abs(ra - 1.0)
                if d > worst_reg:
                    worst_reg, worst_b = d, b
        hh_c = mC["per_case"]["hhcomp"] / real["per_case"]["hhcomp"]
        print(f"  seed {seed}: C medical={med_c:.2f}x (bar 0.75) "
              f"L1={l1_c:.3f} (bar 0.030) worst-regression={worst_reg:.2f} "
              f"({worst_b}) hhcomp={hh_c:.2f}x "
              f"le56: A={mA['le56']:.2f} C={mC['le56']:.2f}")
    print(f"\n  fitted weights -> experiments/exp44_fitted_weights.json "
          f"(for the record; committed files untouched)")
    json.dump({"pre_screen_weights": fitted,
               "targets": [round(t, 4) for t in targets],
               "final_post_screen": [round(o, 4) for o in final_obs],
               "kid_weight_remeasured": kw,
               "kid_weight_committed": cur,
               "matrix_isolated_shifts_ge_0.05": n_shift},
              open(EXP_DIR / "exp44_fitted_weights.json", "w"), indent=1)
    household._SIZE_WEIGHTS = LEGACY_W  # belt and suspenders
    print("done.")


if __name__ == "__main__":
    main()
