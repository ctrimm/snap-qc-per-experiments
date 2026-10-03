"""Experiment 23 - merge dollar mechanisms + recalibrate (calibration gate).

North-star gate: **calibration**. exp18 verified two dollar-error mechanisms
as in-script patches — (1) 97-conditional small-error mode, (2) whole-unit
ineligibility at p_unit=0.0125 — but left two gaps: the finding mix
regressed (L1 0.039 -> 0.067, an under shortfall from small unders being
absorbed by the $23 minimum-benefit floor) and the p90 over/under asymmetry
stayed inverted (coarse under magnitudes oversized vs real per-nature
medians). This experiment:

  1. formalizes the mechanisms as src/synth/dollar_mech.py, applied via
     --dollar-mechanisms (additive, default off; src/synth/errors.py is
     NOT edited);
  2. adds a fourth mechanism: rescale coarse under magnitudes per real
     per-nature medians (nature 44 -> $43, 57 -> $18, 52 -> $59), with the
     scales fitted in-script from a pre-pass;
  3. re-derives eff.json/dir-weights and the 97-resolution coin under the
     new attrition profile — in-memory ports of measure_effectiveness.py
     and calibrate_injection.py (the committed eff.json/inject.json are
     NOT rewritten);
  4. compares before/after: dollar marginal stats, over/under asymmetry,
     finding-mix L1, element ratios. If the mix doesn't recover, the
     script prints the per-status and per-bucket diagnosis.

Usage:
    python3 experiments/exp23_merge_recalibrate.py \
        --real ../snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv \
        --dist experiments/dist.json --dollar-mechanisms

Without --dollar-mechanisms only the stock baseline runs. Real microdata is
held-out validation: aggregates are read, nothing per-row is committed.
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
SEEDS = (1000, 1001, 1002)

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
    """Median AMTERR by (STATUS, nature) on single-variance error cases.

    AMTERR is one number per case, so multi-variance cases can't be
    attributed cleanly; restricting to exactly one recorded variance keeps
    the aggregate honest. STATUS 2 = overissuance, 3 = underissuance.
    """
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
    under nature, clipped to [0.25, 1.0] (never upscale — exp18 showed the
    coarse overs are correctly large; only unders are oversized)."""
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


# --------------------------------------------------------------------------
# in-memory recalibration (ports of measure_effectiveness.py /
# calibrate_injection.py; committed eff.json/inject.json NOT rewritten)
# --------------------------------------------------------------------------

def measure_eff(dist, n, seed=11):
    """Port of measure_effectiveness.py: P(corruption moves the benefit |
    bucket, direction-class) under the CURRENTLY INSTALLED corruptors."""
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
        b = rng.choice(buckets)
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


def calibrate_phase1(dist, eff, n, seed, p_unit):
    """Port of calibrate_injection.py phase 1 (persistent mode), extended
    for mechanism 2: the unit draw happens before the injection coin, so the
    coin targets the RESIDUAL error rate:
        coin = (empirical - p_unit) / ((1 - p_unit) * m)
    where m = P(inject-forced materializes | status)."""
    d2 = dict(dist, error_rate=1.0, error_rate_given_earner=1.0,
              error_rate_given_no_earner=1.0,
              injection_rate={"earner": 1.0, "no_earner": 1.0})
    d2["effectiveness"] = eff
    rng = random.Random(seed)
    inj_trials = {"earner": 0, "no_earner": 0}
    inj_mat = {"earner": 0, "no_earner": 0}
    for _ in range(n):
        f = household.sample_household(rng)
        key = "earner" if f["earned"] > 0 else "no_earner"
        case = dollar_mech.inject_case(f, rng, d2, p_unit=p_unit,
                                       max_attempts=12, persistent_buckets=True)
        if case.get("unit_ineligible"):
            continue  # always materializes; absorbed by the p_unit term
        inj_trials[key] += 1
        if case["finding"] != 1:
            inj_mat[key] += 1
    out = {}
    print("\nphase-1 recalibration (persistent mode, unit-aware):")
    for key in ("earner", "no_earner"):
        m = inj_mat[key] / inj_trials[key]
        empirical = dist[f"error_rate_given_{key}"]
        coin = (empirical - p_unit) / ((1 - p_unit) * m)
        clipped = coin > 1.0
        out[key] = round(min(coin, 1.0), 4)
        print(f"  {key}: P(mat|inject)={m:.3f} empirical={empirical:.3f} "
              f"-> coin={out[key]:.4f} (n={inj_trials[key]})"
              + ("  [CLIPPED: target unreachable]" if clipped else ""))
    return out


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
    ap.add_argument("--dollar-mechanisms", action="store_true",
                    help="enable src/synth/dollar_mech.py (mechanisms 1, 2, "
                         "4) and recalibrate under them. Default off: "
                         "baseline only, stock behavior unchanged.")
    ap.add_argument("--n", type=int, default=20000,
                    help="eval cases per seed")
    ap.add_argument("--pre-n", type=int, default=30000,
                    help="pre-pass cases for mechanism-4 scale fitting")
    ap.add_argument("--eff-n", type=int, default=20000)
    ap.add_argument("--cal-n", type=int, default=6000)
    ap.add_argument("--cal-n97", type=int, default=4000)
    args = ap.parse_args()

    real = load_real(args.real)
    r = summarize(real["signed"])
    real_meds = real_per_nature_medians(args.real)
    print(f"real: {real['n']} rows, {r['n_error']} errors "
          f"(over {r['n_over']}, under {r['n_under']}); "
          f"full-unit share of overs: {real['full_unit_share_of_over']:.3f}")
    print("real per-nature medians (single-variance error cases):")
    for (st, nat), (med, cnt) in sorted(real_meds.items()):
        if cnt >= 200:
            print(f"  {st:>5} nature {nat:>2}: n={cnt:>5} p50={med:6.0f}")

    dist = load_dist(args.dist)
    mech = args.dollar_mechanisms

    # ---- baseline: stock generator, committed weights -------------------
    print("\n=== baseline (stock, --dollar-mechanisms off) ===")
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
    print(f"{'':>10} {'p10':>6} {'p25':>6} {'p50':>6} {'p90':>6} {'p99':>6} "
          f"{'mean':>6} {'<=56':>6}")
    print(f"{'real':>10} {r['p10']:6.0f} {r['p25']:6.0f} {r['p50']:6.0f} "
          f"{r['p90']:6.0f} {r['p99']:6.0f} {r['mean']:6.0f} "
          f"{r['share_le56']:6.2f}")
    print(f"{'baseline':>10} {b['p10']:6.0f} {b['p25']:6.0f} {b['p50']:6.0f} "
          f"{b['p90']:6.0f} {b['p99']:6.0f} {b['mean']:6.0f} "
          f"{b['share_le56']:6.2f}")
    print(f"baseline finding mix ok/over/under: "
          f"{b_mix[0]:.3f}/{b_mix[1]:.3f}/{b_mix[2]:.3f} "
          f"(real {real['n_correct']/real['n']:.3f}/"
          f"{real['n_over']/real['n']:.3f}/{real['n_under']/real['n']:.3f}) "
          f"L1={statistics.fmean(s['finding_l1'] for s in base_stats):.3f}")
    element_report(base_cases_all, dist, "baseline")

    if not mech:
        print("\n--dollar-mechanisms not passed; baseline only.")
        return 0

    # ---- treatment ------------------------------------------------------
    print("\n=== treatment: mechanisms 1+2+4, recalibrated ===")
    dollar_mech.enable()  # mechanisms 1 (+2 via inject_case); 4 off for now
    pre = gen_cases(args.pre_n, 5000, dist, mech=True)
    scales = fit_under_scales(pre, real_meds)

    print("\nre-deriving effectiveness under the mechanisms ...")
    # The effectiveness weights must be measured under the FINAL mechanism
    # set (1+2+4): mechanism 4 shrinks under deltas, which lowers keep rates
    # for under-heavy buckets (more $23-floor absorption), so weights
    # measured without it mis-record the bucket mix.
    dollar_mech.enable(under_scale=scales)  # add mechanism 4
    eff_new = measure_eff(dist, args.eff_n)
    print("new eff bucket:", json.dumps(eff_new["bucket"]))
    print("new dir_weight (under):",
          json.dumps({b: w["under"] for b, w in eff_new["dir_weight"].items()}))

    coins1 = calibrate_phase1(dist, eff_new, args.cal_n, 11, P_UNIT)
    coins97 = calibrate_97(dist, args.cal_n97)

    dist2 = load_dist(args.dist)
    dist2["effectiveness"] = eff_new
    inj = dict(dist2["injection_rate"])
    inj["persistent"] = coins1
    inj["p_over_97_resolve"] = coins97
    dist2["injection_rate"] = inj

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
        s.update({"finding_l1": l1, "finding_mix": mix,
                  "cases": cases})
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
    rr = (real["n_correct"] / real["n"], real["n_over"] / real["n"],
          real["n_under"] / real["n"])
    b_l1 = statistics.fmean(s["finding_l1"] for s in base_stats)
    print(f"  real     {rr[0]:.3f}/{rr[1]:.3f}/{rr[2]:.3f}")
    print(f"  baseline {b_mix[0]:.3f}/{b_mix[1]:.3f}/{b_mix[2]:.3f} L1={b_l1:.3f}")
    print(f"  treat    {t_mix[0]:.3f}/{t_mix[1]:.3f}/{t_mix[2]:.3f} L1={t_l1:.3f}")
    print(f"  under shortfall: real {rr[2]:.3f} vs treat {t_mix[2]:.3f} "
          f"(baseline {b_mix[2]:.3f})")

    # post-scale per-nature medians (mechanism-4 check)
    t_meds = synth_per_nature_medians(treat_cases_all)
    print("\npost-scale per-nature medians, under (single-variance cases):")
    for nature in UNDER_NATURES_FIT:
        r_med, r_n = real_meds.get(("under", nature), (float("nan"), 0))
        s_med, s_n = t_meds.get(("under", nature), (float("nan"), 0))
        print(f"  nature {nature}: real p50={r_med:.0f} (n={r_n}) "
              f"treat p50={s_med:.0f} (n={s_n}) scale={scales.get(nature, 1.0)}")

    # element ratios: recorded bucket shares vs empirical
    element_report(treat_cases_all, dist, "treatment")
    n_unit = sum(1 for c in treat_cases_all if c.get("unit_ineligible"))
    print(f"  whole-unit cases: {n_unit}/{len(treat_cases_all)} "
          f"({n_unit/len(treat_cases_all):.4f}, target p_unit={P_UNIT})")

    # diagnosis: per-status realized rates + 97 direction realization
    print("\ndiagnosis (treatment, pooled seeds):")
    for key, pred in (("earner", lambda f: f["earned"] > 0),
                      ("no_earner", lambda f: f["earned"] == 0)):
        sub = [c for c in treat_cases_all if pred(c["facts"])]
        rate = sum(1 for c in sub if c["finding"] != 1) / len(sub)
        print(f"  P(error|{key}): synth {rate:.3f} "
              f"empirical {dist[f'error_rate_given_{key}']:.3f}")
    tgt97 = dist.get("p_over_97_given_bucket", {})
    sv = [c for c in treat_cases_all
          if len(c["variances"]) == 1 and c["variances"][0]["nature"] == 97]
    by_b = defaultdict(list)
    for c in sv:
        by_b[c["variances"][0]["element_bucket"]].append(c["finding"] == 2)
    print("  realized P(over | nature=97) by bucket (single-variance):")
    for bucket in sorted(by_b):
        xs = by_b[bucket]
        print(f"    {bucket:>9}: synth {sum(xs)/len(xs):.3f} "
              f"target {tgt97.get(bucket, float('nan')):.3f} (n={len(xs)})")

    dollar_mech.disable()
    print("\nmechanisms disabled; stock behavior restored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
