"""Experiment 26 - combine exp23's dollar mechanisms with exp24's defaults.

North-star gate: **calibration** (finding mix + dollar-error marginal).

exp23 merged the dollar mechanisms (97-conditional small-error mode,
whole-unit ineligibility, coarse-under rescale) and recalibrated, but ran
on PRE-exp24 defaults (old ZERO_BASE_WEIGHT + scalar materialization).
exp24 then changed the draw (ZERO_BASE_WEIGHT={} + per-(bucket,stratum)
MATERIALIZATION_MATRIX, finding L1 0.025). This combination is untested.
This experiment implements exp23's precise fix and re-measures + refits
the recalibration UNDER the exp24 defaults:

  (a) whole-unit mechanism recoded as earned-income zeroing ->
      (element 311, nature 35), matching how the real file codes
      near-full-benefit overs; the whole-unit mass is SUBTRACTED from the
      empirical earned draw weight first (apply_unit_bucket_correction),
      so it is not double-counted (exp23 diagnosis #3);
  (b) direction-aware phase-1: separate over/under residual targets
      (empirical targets minus the mechanical unit over mass) with
      direction-balance draw multipliers as the instrument, so the unit
      over-contribution can be offset;
  (c) small-error mode magnitude revisited for unders: direction- and
      pass-through-aware ranges (income U($20,$80), deduction U($6,$24))
      centering the benefit delta near the real 97-under median ($15)
      instead of the $1-9 that died at the $23 floor.

Effectiveness is re-measured AFTER mechanism 4's rescale is enabled
(exp23's subtlety), under the exp24 draw defaults. The committed
eff.json / inject.json / dist.json are NOT rewritten (in-memory only).

Usage:
    python3 experiments/exp26_combine_dollar.py \
        --real ../snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv \
        --dist experiments/dist.json

Real microdata is held-out validation: aggregates are read, nothing
per-row is committed.
"""
import argparse
import copy
import csv
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from synth import benefit as benefit_mod
from synth import dollar_mech, errors, household
from synth.distutil import load_dist

QUANTS = (0.10, 0.25, 0.50, 0.90, 0.99)
P_UNIT = dollar_mech.P_UNIT_DEFAULT
UNDER_NATURES_FIT = (44, 57, 52)  # under natures exp18 found oversized
SEEDS = (7, 8, 9)  # seed-7 convention, paired baseline/treatment

OVER_NATURES = {35, 37, 38, 53, 56, 7}
UNDER_NATURES = {44, 52, 57, 6, 13}


def dirclass(nature):
    if nature in OVER_NATURES:
        return "over"
    if nature in UNDER_NATURES:
        return "under"
    return "other"


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _sample(rng, probs):
    x = rng.random() * sum(probs.values())
    for k, v in probs.items():
        x -= v
        if x <= 0:
            return k
    return k


# --------------------------------------------------------------------------
# real aggregates (held-out; read only)
# --------------------------------------------------------------------------

def load_real(path):
    signed, overs, unders = [], [], []
    n = n_correct = n_over = n_full_unit = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            n += 1
            st = row["STATUS"].strip()
            if st == "1":
                n_correct += 1
                continue
            if st not in ("2", "3"):
                continue
            a = float(row["AMTERR"] or 0)
            if st == "2":
                signed.append(a)
                overs.append(a)
                n_over += 1
                if float(row["FSBEN"] or 0) == 0 and float(row["RAWBEN"] or 0) > 0:
                    n_full_unit += 1
            else:
                signed.append(-a)
                unders.append(a)
    return {
        "signed": signed, "overs": overs, "unders": unders,
        "n": n, "n_correct": n_correct,
        "full_unit_share_of_over": n_full_unit / n_over if n_over else 0.0,
        "n_over": n_over, "n_under": len(unders),
    }


def real_per_nature_medians(path):
    """Median AMTERR by (STATUS, nature) on single-variance error cases."""
    vals = defaultdict(list)
    counts = Counter()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            st = row["STATUS"].strip()
            if st not in ("2", "3"):
                continue
            nats = [row[f"NATURE{i}"].strip() for i in range(1, 10)
                    if row[f"NATURE{i}"].strip()]
            if len(nats) != 1:
                continue
            key = ("over" if st == "2" else "under", int(nats[0]))
            vals[key].append(float(row["AMTERR"] or 0))
            counts[key] += 1
    return {k: (pct(v, 0.5), counts[k]) for k, v in vals.items()}


def summarize(signed):
    ab = [abs(x) for x in signed]
    overs = [x for x in signed if x > 0]
    unders = [-x for x in signed if x < 0]
    s = {"n_error": len(signed), "n_over": len(overs), "n_under": len(unders)}
    for q in QUANTS:
        s[f"p{int(q*100)}"] = pct(ab, q)
    s["mean"] = statistics.fmean(ab) if ab else float("nan")
    s["share_le56"] = sum(1 for x in ab if x <= 56) / len(ab) if ab else float("nan")
    for tag, xs in (("over", overs), ("under", unders)):
        s[f"median_{tag}"] = pct(xs, 0.50)
        s[f"p90_{tag}"] = pct(xs, 0.90)
        s[f"p99_{tag}"] = pct(xs, 0.99)
        s[f"mean_{tag}"] = statistics.fmean(xs) if xs else float("nan")
    return s


def finding_mix_l1(cases, real):
    s_over = sum(1 for c in cases if c["finding"] == 2) / len(cases)
    s_under = sum(1 for c in cases if c["finding"] == 3) / len(cases)
    s_ok = 1 - s_over - s_under
    r_over = real["n_over"] / real["n"]
    r_under = real["n_under"] / real["n"]
    r_ok = real["n_correct"] / real["n"]
    return (abs(s_over - r_over) + abs(s_under - r_under) + abs(s_ok - r_ok),
            (s_ok, s_over, s_under))


def synth_per_nature_medians(cases):
    """Median |dollar| by (finding, recorded nature) on single-variance
    error cases — the synth mirror of real_per_nature_medians."""
    vals = defaultdict(list)
    for c in cases:
        if c["finding"] not in (2, 3) or len(c["variances"]) != 1:
            continue
        key = ("over" if c["finding"] == 2 else "under",
               c["variances"][0]["nature"])
        vals[key].append(abs(c["issued_benefit"] - c["correct_benefit"]))
    return {k: (pct(v, 0.5), len(v)) for k, v in vals.items()}


# --------------------------------------------------------------------------
# generation
# --------------------------------------------------------------------------

def gen_cases(n, seed, dist, mech):
    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        f = household.sample_household(rng)
        if mech:
            cases.append(dollar_mech.inject_case(
                f, rng, dist, p_unit=P_UNIT, persistent_buckets=True))
        else:
            cases.append(errors.inject(f, rng, dist, persistent_buckets=True))
    return cases


def fit_under_scales(cases, real_meds):
    """Mechanism 4 calibration: scale = real_median / synth_median per
    under nature, clipped to [0.25, 1.0] (never upscale)."""
    synth_meds = synth_per_nature_medians(cases)
    scales = {}
    print("\nmechanism-4 pre-pass: per-nature medians (single-variance cases)")
    print(f"{'nature':>7} {'real_med':>9} {'synth_med':>10} {'n_synth':>8} "
          f"{'scale':>6}")
    for nature in UNDER_NATURES_FIT:
        r_med, r_n = real_meds.get(("under", nature), (float("nan"), 0))
        s_med, s_n = synth_meds.get(("under", nature), (float("nan"), 0))
        if s_n < 30 or not (s_med > 0):
            print(f"{nature:>7} {r_med:9.0f} {s_med:10.0f} {s_n:>8} "
                  f"{'skip':>6}  (too few synth cases)")
            continue
        s = min(1.0, max(0.25, r_med / s_med))
        scales[nature] = round(s, 3)
        print(f"{nature:>7} {r_med:9.0f} {s_med:10.0f} {s_n:>8} {s:6.3f}  "
              f"(real n={r_n})")
    return scales


def small_under_check(cases, real_meds):
    """exp26 (c): all drawn-97 variances take the small mode, so
    single-variance nature-97 cases ARE the small-mode diagnostic."""
    meds = synth_per_nature_medians(cases)
    print("\nsmall-mode check (single-variance nature-97 cases):")
    for tag in ("over", "under"):
        r_med, r_n = real_meds.get((tag, 97), (float("nan"), 0))
        s_med, s_n = meds.get((tag, 97), (float("nan"), 0))
        print(f"  {tag:>5} 97: real p50={r_med:.0f} (n={r_n}) "
              f"synth p50={s_med:.0f} (n={s_n})")


# --------------------------------------------------------------------------
# in-memory recalibration under the exp24 defaults (committed eff.json /
# inject.json / dist.json NOT rewritten)
# --------------------------------------------------------------------------

def measure_eff(dist, n, seed=11):
    """Port of measure_effectiveness.py: P(corruption moves the benefit |
    bucket, direction-class) under the CURRENTLY INSTALLED corruptors
    (mechanisms 1+4 on, exp26 small-under ranges). exp23's subtlety: this
    must run AFTER mechanism 4 is enabled — the rescale changes
    materialization rates. Includes exp23's minor next-step-4 fix: the
    bucket is drawn from the applicable mix (matches the injector), not
    uniformly."""
    buckets = list(dist["bucket_probs"])
    p_dir = {}
    for b in buckets:
        tot = sum(dist["nature_given_bucket"][b].values())
        c = Counter()
        for ntr, p in dist["nature_given_bucket"][b].items():
            c[dirclass(ntr)] += p / tot
        p_dir[b] = dict(c)
    rng = random.Random(seed)
    mat = defaultdict(Counter)
    tot = defaultdict(Counter)
    for _ in range(n):
        f = household.sample_household(rng)
        app = errors._applicable_buckets(f, dist, rng)
        b = _sample(rng, app)
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
    eff_bucket, dir_mat, dir_w = {}, {}, {}
    for b in buckets:
        if b == "arithmetic":
            m = {"over": 1.0, "under": 1.0, "other": 1.0}
        else:
            m = {}
            for d in ("over", "under", "other"):
                m[d] = mat[b][d] / tot[b][d] if tot[b][d] else 1.0
                m[d] = min(1.0, max(0.02, m[d]))
        dir_mat[b] = {d: round(m[d], 3) for d in m}
        z = sum(p_dir[b].get(d, 0) / m[d] for d in m)
        w = {d: (1 / m[d]) / z for d in m}
        dir_w[b] = {d: round(w[d], 3) for d in w}
        eff_bucket[b] = round(sum(w[d] * p_dir[b].get(d, 0) * m[d] for d in m), 3)
    return {"bucket": eff_bucket, "dir_materialization": dir_mat,
            "dir_weight": dir_w}


def calibrate_97(dist, n, seed=21):
    """Port of calibrate_injection.py phase 2: per-bucket 97-resolution coin
    under the installed corruptors. c = t*m_u / (t*m_u + (1-t)*m_o)."""
    rng = random.Random(seed)
    targets = dist.get("p_over_97_given_bucket", {})
    coins = {}
    print("\nphase-2 recalibration (97-resolution coin per bucket):")
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
                tc, _ = errors._apply_one(agency, truth, bucket, 97, rng, dist,
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
              f"m_under={mu:.3f} -> coin={coins[bucket]:.4f}")
    return coins


def forced_dist(dist):
    """Injection coin forced to 1.0 (both strata, both modes): measures the
    direction split and per-stratum materialization conditional on the
    coin firing."""
    d = copy.deepcopy(dist)
    inj = dict(d.get("injection_rate") or {})
    inj["earner"] = 1.0
    inj["no_earner"] = 1.0
    inj["persistent"] = {"earner": 1.0, "no_earner": 1.0}
    d["injection_rate"] = inj
    return d


def measure_residual(d_forced, n, seed, p_unit):
    """Residual-pool rates with injection forced: population over/under
    rates (unit cases excluded) + per-stratum P(materialize | inject)."""
    rng = random.Random(seed)
    tot = over = under = 0
    trials = {"earner": 0, "no_earner": 0}
    mat = {"earner": 0, "no_earner": 0}
    so = {"earner": 0, "no_earner": 0}
    su = {"earner": 0, "no_earner": 0}
    for _ in range(n):
        f = household.sample_household(rng)
        s = "earner" if f["earned"] > 0 else "no_earner"
        case = dollar_mech.inject_case(f, rng, d_forced, p_unit=p_unit,
                                       persistent_buckets=True)
        if case.get("unit_ineligible"):
            continue  # always materializes; absorbed by the p_unit term
        tot += 1
        trials[s] += 1
        if case["finding"] != 1:
            mat[s] += 1
            if case["finding"] == 2:
                over += 1
                so[s] += 1
            else:
                under += 1
                su[s] += 1
    return {"n": tot, "over": over / tot, "under": under / tot,
            "m": {s: mat[s] / trials[s] for s in trials},
            "over_s": {s: so[s] / trials[s] for s in trials},
            "under_s": {s: su[s] / trials[s] for s in trials}}


def fit_direction_balance(dist_b, over_target, under_target, n, seed, p_unit):
    """exp26 (b): direction-aware phase-1. The unit draw contributes p_unit
    of pure over mechanically, so the injected (residual) pool must land
    on over_target = (emp_over - p_unit)/(1 - p_unit) and
    under_target = emp_under/(1 - p_unit). The instrument is a pair of
    draw-side multipliers folded into dir_weight; 2 multiplicative updates
    with a [0.5, 2.0] trust region per step. Returns the balanced dist,
    the final residual measurement, and the fitted boosts."""
    boosts = {"over": 1.0, "under": 1.0}
    print(f"\ndirection-balance fit (residual targets: over={over_target:.4f} "
          f"under={under_target:.4f}):")
    d = dist_b
    r = None
    for it in range(3):
        d = dollar_mech.apply_direction_balance(
            dist_b, boosts["over"], boosts["under"])
        r = measure_residual(forced_dist(d), n, seed + it, p_unit)
        print(f"  iter{it}: boost o={boosts['over']:.3f} u={boosts['under']:.3f} "
              f"-> residual over={r['over']:.4f} under={r['under']:.4f} "
              f"(m_earner={r['m']['earner']:.3f} m_no={r['m']['no_earner']:.3f}; "
              f"over|earner={r['over_s']['earner']:.3f} "
              f"over|no_earner={r['over_s']['no_earner']:.3f})")
        if it < 2:
            boosts["over"] *= min(2.0, max(0.5, over_target / r["over"]))
            boosts["under"] *= min(2.0, max(0.5, under_target / r["under"]))
    return d, r, boosts


def calibrate_phase1_dir(d_bal, dist_committed, r_final, p_unit):
    """Direction-aware phase-1 coins: per-stratum residual error targets
    (empirical minus the unit mass, renormalized to the residual pool)
    divided by the per-stratum materialization measured under the final
    direction balance. The direction split itself is owned by the boosts;
    the coin owns the volume."""
    out = {}
    print("\nphase-1 recalibration (direction-aware, unit-subtracted):")
    for s in ("earner", "no_earner"):
        emp = dist_committed[f"error_rate_given_{s}"]
        target = (emp - p_unit) / (1 - p_unit)
        m = r_final["m"][s]
        coin = target / m
        out[s] = round(min(coin, 1.0), 4)
        print(f"  {s}: P(mat|inject)={m:.3f} residual_target={target:.3f} "
              f"-> coin={out[s]:.4f}"
              + ("  [CLIPPED: target unreachable]" if coin > 1.0 else ""))
    return out


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def element_report(cases, dist, label):
    """Recorded element-bucket shares vs the empirical mix."""
    emp = dist["bucket_probs"]
    rec = Counter()
    for c in cases:
        for v in c["variances"]:
            rec[v["element_bucket"]] += 1
    tot_rec = sum(rec.values())
    print(f"\nelement-bucket ratios ({label}; recorded share vs empirical):")
    l1_el = 0.0
    for bucket in sorted(emp):
        rs = rec[bucket] / tot_rec if tot_rec else 0.0
        l1_el += abs(rs - emp[bucket])
        flag = " *" if abs(rs - emp[bucket]) > 0.01 else ""
        print(f"  {bucket:>9}: synth {rs:.3f} real {emp[bucket]:.3f}{flag}")
    print(f"  element L1: {l1_el:.3f}")
    return l1_el


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--dist", required=True)
    ap.add_argument("--n", type=int, default=20000,
                    help="eval cases per seed")
    ap.add_argument("--pre-n", type=int, default=30000,
                    help="pre-pass cases for mechanism-4 scale fitting")
    ap.add_argument("--eff-n", type=int, default=20000)
    ap.add_argument("--cal-n97", type=int, default=4000)
    ap.add_argument("--boost-n", type=int, default=10000,
                    help="cases per direction-balance iteration")
    args = ap.parse_args()

    real = load_real(args.real)
    r = summarize(real["signed"])
    real_meds = real_per_nature_medians(args.real)
    r_over = real["n_over"] / real["n"]
    r_under = real["n_under"] / real["n"]
    r_ok = real["n_correct"] / real["n"]
    print(f"real: {real['n']} rows, {r['n_error']} errors "
          f"(over {r['n_over']}, under {r['n_under']}); "
          f"mix {r_ok:.3f}/{r_over:.3f}/{r_under:.3f}; "
          f"full-unit share of overs: {real['full_unit_share_of_over']:.3f}")

    # residual (post-unit-subtraction) direction targets for the injected pool
    over_target = (r_over - P_UNIT) / (1 - P_UNIT)
    under_target = r_under / (1 - P_UNIT)
    print(f"residual direction targets (unit mass subtracted): "
          f"over={over_target:.4f} under={under_target:.4f}")

    dist = load_dist(args.dist)

    # ---- baseline: stock generator, committed weights -------------------
    print("\n=== baseline (stock, exp24 defaults) ===")
    base_stats = []
    base_cases_all = []
    for sd in SEEDS:
        cases = gen_cases(args.n, sd, dist, mech=False)
        base_cases_all.extend(cases)
        signed = [c["issued_benefit"] - c["correct_benefit"]
                  for c in cases if c["finding"] in (2, 3)]
        s = summarize(signed)
        l1, mix = finding_mix_l1(cases, real)
        s.update({"finding_l1": l1, "finding_mix": mix})
        base_stats.append(s)
    b = {k: statistics.fmean(s[k] for s in base_stats)
         for k in base_stats[0] if isinstance(base_stats[0][k], float)}
    b_mix = [statistics.fmean(s["finding_mix"][i] for s in base_stats)
             for i in range(3)]
    b_l1 = statistics.fmean(s["finding_l1"] for s in base_stats)
    print(f"baseline finding mix ok/over/under: "
          f"{b_mix[0]:.3f}/{b_mix[1]:.3f}/{b_mix[2]:.3f} L1={b_l1:.3f}")
    base_el_l1 = element_report(base_cases_all, dist, "baseline")

    # ---- treatment ------------------------------------------------------
    print("\n=== treatment: mechanisms 1+2(recoded)+4, recalibrated "
          "under exp24 defaults ===")
    dollar_mech.enable()  # mech 1 (+2 via inject_case, recoded); 4 off for now
    pre = gen_cases(args.pre_n, 5000, dist, mech=True)
    scales = fit_under_scales(pre, real_meds)
    small_under_check(pre, real_meds)
    v_per_case = (sum(len(c["variances"]) for c in pre) / len(pre))
    print(f"\nrecorded variances per case (pre-pass): {v_per_case:.3f}")

    print("\nre-deriving effectiveness under the mechanisms (mech 4 on) ...")
    dollar_mech.enable(under_scale=scales)  # add mechanism 4
    eff_new = measure_eff(dist, args.eff_n)
    print("new eff bucket:", json.dumps(eff_new["bucket"]))

    # (a) subtract the whole-unit mass from the empirical earned draw weight
    dist_b = dollar_mech.apply_unit_bucket_correction(dist, P_UNIT, v_per_case)
    dist_b["effectiveness"] = eff_new
    print("unit bucket correction factor: "
          f"{dist_b['_exp26']['unit_bucket_factor']}")

    coins97 = calibrate_97(dist_b, args.cal_n97)
    inj = dict(dist_b["injection_rate"])
    inj["p_over_97_resolve"] = coins97
    dist_b["injection_rate"] = inj

    # (b) direction-aware phase-1: fit the draw-side balance, then the coins
    d_bal, r_final, boosts = fit_direction_balance(
        dist_b, over_target, under_target, args.boost_n, 31, P_UNIT)
    coins1 = calibrate_phase1_dir(d_bal, dist, r_final, P_UNIT)

    dist2 = copy.deepcopy(d_bal)
    inj2 = dict(dist2["injection_rate"])
    inj2["persistent"] = coins1
    inj2["p_over_97_resolve"] = coins97
    dist2["injection_rate"] = inj2

    print("\n=== treatment eval ===")
    treat_stats = []
    treat_cases_all = []
    for sd in SEEDS:
        cases = gen_cases(args.n, sd, dist2, mech=True)
        treat_cases_all.extend(cases)
        signed = [c["issued_benefit"] - c["correct_benefit"]
                  for c in cases if c["finding"] in (2, 3)]
        s = summarize(signed)
        l1, mix = finding_mix_l1(cases, real)
        s.update({"finding_l1": l1, "finding_mix": mix})
        treat_stats.append(s)
    t = {k: statistics.fmean(s[k] for s in treat_stats)
         for k in treat_stats[0] if isinstance(treat_stats[0][k], float)}
    t_mix = [statistics.fmean(s["finding_mix"][i] for s in treat_stats)
             for i in range(3)]
    t_l1 = statistics.fmean(s["finding_l1"] for s in treat_stats)

    print(f"\n{'':>10} {'p10':>6} {'p25':>6} {'p50':>6} {'p90':>6} {'p99':>6} "
          f"{'mean':>6} {'<=56':>6}   (absolute $, error cases)")
    print(f"{'real':>10} {r['p10']:6.0f} {r['p25']:6.0f} {r['p50']:6.0f} "
          f"{r['p90']:6.0f} {r['p99']:6.0f} {r['mean']:6.0f} "
          f"{r['share_le56']:6.2f}")
    print(f"{'baseline':>10} {b['p10']:6.0f} {b['p25']:6.0f} {b['p50']:6.0f} "
          f"{b['p90']:6.0f} {b['p99']:6.0f} {b['mean']:6.0f} "
          f"{b['share_le56']:6.2f}")
    print(f"{'treat':>10} {t['p10']:6.0f} {t['p25']:6.0f} {t['p50']:6.0f} "
          f"{t['p90']:6.0f} {t['p99']:6.0f} {t['mean']:6.0f} "
          f"{t['share_le56']:6.2f}")

    print("\nover/under asymmetry (absolute $ within finding):")
    print(f"{'':>10} {'medO':>6} {'medU':>6} {'mnO':>6} {'mnU':>6} "
          f"{'p90O':>6} {'p90U':>6} {'p99O':>6} {'p99U':>6}  sign ok?")
    for label, s in (("real", r), ("baseline", b), ("treat", t)):
        signs = [s["median_over"] > s["median_under"],
                 s["mean_over"] > s["mean_under"],
                 s["p90_over"] > s["p90_under"],
                 s["p99_over"] > s["p99_under"]]
        print(f"{label:>10} {s['median_over']:6.0f} {s['median_under']:6.0f} "
              f"{s['mean_over']:6.0f} {s['mean_under']:6.0f} "
              f"{s['p90_over']:6.0f} {s['p90_under']:6.0f} "
              f"{s['p99_over']:6.0f} {s['p99_under']:6.0f}  "
              f"{' '.join('Y' if x else 'n' for x in signs)}")

    print("\nfinding mix (correct/over/under):")
    print(f"  real     {r_ok:.3f}/{r_over:.3f}/{r_under:.3f}")
    print(f"  baseline {b_mix[0]:.3f}/{b_mix[1]:.3f}/{b_mix[2]:.3f} L1={b_l1:.3f}")
    print(f"  treat    {t_mix[0]:.3f}/{t_mix[1]:.3f}/{t_mix[2]:.3f} L1={t_l1:.3f}")

    # post-scale per-nature medians (mechanism-4 + small-under check)
    t_meds = synth_per_nature_medians(treat_cases_all)
    print("\npost-scale per-nature medians (single-variance cases):")
    for tag, nature in (("under", 44), ("under", 57), ("under", 52),
                        ("under", 97), ("over", 97)):
        r_med, r_n = real_meds.get((tag, nature), (float("nan"), 0))
        s_med, s_n = t_meds.get((tag, nature), (float("nan"), 0))
        print(f"  {tag:>5} nature {nature:>2}: real p50={r_med:.0f} (n={r_n}) "
              f"treat p50={s_med:.0f} (n={s_n})")

    treat_el_l1 = element_report(treat_cases_all, dist, "treatment")
    print(f"\nelement L1: baseline {base_el_l1:.3f} -> treatment {treat_el_l1:.3f}")
    n_unit = sum(1 for c in treat_cases_all if c.get("unit_ineligible"))
    print(f"whole-unit cases: {n_unit}/{len(treat_cases_all)} "
          f"({n_unit/len(treat_cases_all):.4f}, target p_unit={P_UNIT})")

    # verdict inputs
    l1_seeds = [s["finding_l1"] for s in treat_stats]
    print("\nverdict inputs:")
    print(f"  finding L1: {t_l1:.3f} (bar: <= 0.030; per-seed "
          f"{min(l1_seeds):.3f}-{max(l1_seeds):.3f})")
    for s, pred in (("earner", lambda c: c["facts"]["earned"] > 0),
                    ("no_earner", lambda c: c["facts"]["earned"] == 0)):
        sub = [c for c in treat_cases_all if pred(c)]
        mo = sum(1 for c in sub if c["finding"] == 2) / len(sub)
        mu = sum(1 for c in sub if c["finding"] == 3) / len(sub)
        print(f"  treat residual direction | {s}: over={mo:.3f} under={mu:.3f} "
              f"(n={len(sub)})")
    print(f"  share <= $56: {t['share_le56']:.2f} (bar: >= 0.60)")
    p90_ok = t["p90_over"] > t["p90_under"]
    print(f"  p90 over/under: {t['p90_over']:.0f}/{t['p90_under']:.0f} "
          f"inversion fixed: {p90_ok} (real {r['p90_over']:.0f}/{r['p90_under']:.0f})")
    print(f"  p10: {t['p10']:.0f} (bar: <= 8; real {r['p10']:.0f})")

    dollar_mech.disable()
    print("\nmechanisms disabled; stock behavior restored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
