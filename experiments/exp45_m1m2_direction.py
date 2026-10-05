#!/usr/bin/env python3
"""Experiment 45 — M1/M2 direction recalibration for earned.

Stages:
  [0] Reproduce exp27's [F4] (M1/M2 position-dependent draw mixes +
      recalibrated phase-1 coins) on the CURRENT tree with the dollar
      mechanisms ON, as a harness check.
  [1] Decompose the over/under direction residual by bucket x 97/non-97
      to pick the right instrument (dir_weight vs 97 coins).
  [2] Secant-fit (boost_over, boost_under) via
      dollar_mech.apply_direction_balance IN THE M1/M2 REGIME to targets
      (0.239, 0.158); rails [0.3, 3.0].
  [3] Joint validation on paired seeds 7/8.

Read-only: real QC aggregates stay in memory; dist.json/eff.json/inject.json
are never rewritten (all changes are in-process copies).
"""
import csv
import copy
import json
import os
import random
import sys
from collections import Counter

sys.path.insert(0, "src")
from synth import dollar_mech, errors, household, params
from synth.codebook import element_bucket
from synth.distutil import load_dist
from synth import benefit as benefit_mod

EXP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(EXP_DIR)
QC = os.path.join(os.path.dirname(ROOT), "snap-qc-data",
                   "raw", "qcfy2024_csv", "qc_pub_fy2024.csv")
EL_COLS = [f"ELEMENT{i}" for i in range(1, 10)]
NA_COLS = [f"NATURE{i}" for i in range(1, 10)]
BUCKETS = ["earned", "shelter", "unearned", "sua", "medical", "hhcomp",
           "arithmetic", "depcare"]
STRATA = ["earner_senior", "earner_nonsenior", "no_earner_senior",
          "no_earner_nonsenior"]

N_CASES = 20000
SEEDS = (7, 8)
TGT_OVER, TGT_UNDER = 0.239, 0.158
RAIL_LO, RAIL_HI = 0.3, 3.0


def fnum(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------
# real aggregates (held-out; recomputed, never trusted from a chronicle)
# --------------------------------------------------------------------------
def load_real():
    per_case = {s: Counter() for s in STRATA}
    err_rate = {s: [0, 0] for s in STRATA}  # [cases with >=1 variance, cases]
    share = Counter()
    m1 = {s: Counter() for s in STRATA}
    m2 = {s: Counter() for s in STRATA}
    fm = Counter()
    n = 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            earner = fnum(row["FSEARN"]) > 0
            senior = (fnum(row["FSNELDER"]) > 0 or
                      any(fnum(row[f"SSI{i}"]) > 0 for i in range(1, 9)))
            s = ("earner" if earner else "no_earner") + "_" + \
                ("senior" if senior else "nonsenior")
            share[s] += 1
            n += 1
            st = int(float(row["STATUS"] or 1))
            fm[st] += 1
            codes = [(row[ec] or "").strip() for ec in EL_COLS]
            nats = [(row[nc] or "").strip() for nc in NA_COLS]
            seen = set()
            err_rate[s][1] += 1
            for ci, code in enumerate(codes):
                if not code or code in seen:
                    continue
                seen.add(code)
                b = element_bucket(int(code))
                if b not in BUCKETS:
                    continue  # childsupport/assets/reporting/etc: outside
                    # the generator's 8-bucket support; dropped on both sides
                per_case[s][b] += 1
                if ci == 0:
                    m1[s][b] += 1
                    err_rate[s][0] += 1
                else:
                    m2[s][b] += 1
    return {
        "per_case": per_case, "share": {s: share[s] / n for s in STRATA},
        "m1": m1, "m2": m2, "n": n,
        "fm": {1: fm[1] / n, 2: fm[2] / n, 3: fm[3] / n},
        "err_rate": {s: err_rate[s][0] / err_rate[s][1] for s in STRATA},
    }


def position_mixes(real, dist):
    """Per-stratum empirical M1/M2 mixes; marginal fallback where degenerate."""
    M1, M2, MM = {}, {}, {}
    for s in STRATA:
        t1 = sum(real["m1"][s].values())
        t2 = sum(real["m2"][s].values())
        marg = dist[f"bucket_probs_given_{s}"]
        M1[s] = {b: (real["m1"][s][b] / t1 if t1 else marg[b]) for b in BUCKETS}
        M2[s] = {b: (real["m2"][s][b] / t2 if t2 else marg[b]) for b in BUCKETS}
        MM[s] = dict(marg)
    return M1, M2, MM


# --------------------------------------------------------------------------
# M1/M2 injector: faithful copy of the current errors._inject_persistent
# with ONE change -- the bucket draw mix depends on draw position.
# Dollar-mechanism corruptor patches compose through errors._apply_one,
# so mechanisms stay ON. Installed by rebinding errors._inject_persistent.
# --------------------------------------------------------------------------
_M1M2 = {"M1": None, "M2": None, "MM": None}


def _ip_m1m2(facts, rng, dist, applicable, dir_w, max_attempts,
             stats=None, legacy_materialization=False):
    M1, M2, MM = _M1M2["M1"], _M1M2["M2"], _M1M2["MM"]
    eff_b = (dist.get("effectiveness") or {}).get("bucket", {})
    stratum = errors._stratum_key(facts)
    mm = MM[stratum]

    def wmix_for(pos):
        mix = M1[stratum] if pos == 0 else M2[stratum]
        w = {}
        for b, p in applicable.items():
            if mm.get(b, 0) > 0 and mix.get(b, 0) > 0:
                w[b] = p * mix[b] / mm[b]
            else:
                w[b] = p  # degenerate cell: fall back to marginal
        if legacy_materialization:
            if eff_b:
                w = {b: x / max(eff_b.get(b, 1.0), 0.02)
                     for b, x in w.items()}
        else:
            w = {b: x * errors._matrix_weight(b, stratum, eff_b)
                 for b, x in w.items()}
        return w

    agency = copy.deepcopy(facts)
    truth = facts
    benefit_noise = 0.0
    variances = []
    n_var = 2 if rng.random() < 0.15 else 1

    def pair(a, t, noise):
        c = benefit_mod.compute(t)["benefit"]
        i = max(0, int(round(benefit_mod.compute(a)["benefit"] + noise)))
        return i, c

    for pos in range(n_var):
        bucket = errors._sample(rng, wmix_for(pos))
        if stats is not None:
            stats["drawn"][bucket] += 1
        c_issued, c_correct = pair(agency, truth, benefit_noise)
        nature, cause = errors._draw_nature(facts, bucket, dist, dir_w, rng)
        trial_noise = 0.0
        if bucket == "arithmetic":
            trial_noise = rng.choice([-1, 1]) * errors._u(rng, 10, 60)
        else:
            trial_agency = copy.deepcopy(agency)
            trial_truth = truth
            truth_corr, nature_override = errors._apply_one(
                trial_agency, trial_truth, bucket, nature, rng, dist)
            if truth_corr:
                trial_truth = {**trial_truth, **truth_corr}
            if nature_override is not None:
                nature = nature_override
        t_issued, t_correct = pair(
            trial_agency if bucket != "arithmetic" else agency,
            trial_truth if bucket != "arithmetic" else truth,
            benefit_noise + trial_noise)
        if ((t_issued, t_correct) != (c_issued, c_correct)
                and t_issued != t_correct):
            if bucket != "arithmetic":
                agency, truth = trial_agency, trial_truth
            benefit_noise += trial_noise
            if stats is not None:
                stats["recorded"][bucket] += 1
            variances.append({
                "element": errors.REPRESENTATIVE_ELEMENT[bucket],
                "element_bucket": bucket,
                "nature": nature,
                "cause": errors._recorded_cause(nature, cause, rng),
                "timing": "after" if nature == 97 else "at_action",
            })

    if not variances:
        return errors._clean_case(facts,
                                  benefit_mod.compute(facts)["benefit"])
    issued = max(0, int(round(benefit_mod.compute(agency)["benefit"] +
                              benefit_noise)))
    correct = benefit_mod.compute(truth)["benefit"]
    dollar = abs(correct - issued)
    return {
        "facts": truth,
        "issued_facts": agency,
        "correct_benefit": correct,
        "issued_benefit": issued,
        "finding": 2 if issued > correct else 3,
        "dollar_error": dollar,
        "reportable": dollar > params.QC_ERROR_THRESHOLD,
        "variances": variances,
    }


class m1m2_regime:
    """Rebind errors._inject_persistent to the M1/M2 copy (restored on exit)."""

    def __enter__(self):
        self._saved = errors._inject_persistent
        errors._inject_persistent = _ip_m1m2

    def __exit__(self, *a):
        errors._inject_persistent = self._saved


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------
def gen_cases(n, seed, dist):
    rng = random.Random(seed)
    out = []
    d_mech = dollar_mech.enable_adopted(dist)
    for _ in range(n):
        facts = household.sample_household(rng)
        s0 = errors._stratum_key(facts)
        c = dollar_mech.inject_case(facts, rng, d_mech, max_attempts=12,
                                    persistent_buckets=True)
        c["_s0"] = s0
        out.append(c)
    dollar_mech.disable()
    return out


def synth_mix(cases):
    per_case = {s: Counter() for s in STRATA}
    share = Counter()
    n = len(cases)
    for c in cases:
        s = c["_s0"]
        share[s] += 1
        for v in c["variances"]:
            per_case[s][v["element_bucket"]] += 1
    return {"per_case": per_case,
            "share": {s: share[s] / n for s in STRATA}}


def ratios(syn, real):
    out = {}
    for b in BUCKETS:
        rs = sum(real["per_case"][s][b] * real["share"][s] for s in STRATA)
        ss = sum(syn["per_case"][s][b] * syn["share"][s] for s in STRATA)
        out[b] = ss / rs if rs else 0.0
    return out


def finding_l1(cases, real_fm):
    n = len(cases)
    fm = {1: 0, 2: 0, 3: 0}
    for c in cases:
        fm[c["finding"]] += 1
    fm = {k: v / n for k, v in fm.items()}
    return sum(abs(fm[k] - real_fm[k]) for k in (1, 2, 3)), fm


def split(cases):
    """(over fraction, under fraction) of cases."""
    n = len(cases)
    o = sum(1 for c in cases if c["finding"] == 2) / n
    u = sum(1 for c in cases if c["finding"] == 3) / n
    return o, u


def le56(cases):
    n = len(cases)
    return sum(1 for c in cases
               if c["reportable"] and c["dollar_error"] <= 56) / n


# --------------------------------------------------------------------------
def main():
    dist = load_dist(os.path.join(EXP_DIR, "dist.json"))
    print("== real aggregates (held-out) ==", flush=True)
    real = load_real()
    print(f"  n={real['n']} over/under={real['fm'][2]:.3f}/{real['fm'][3]:.3f} "
          f"(targets {TGT_OVER}/{TGT_UNDER})", flush=True)

    M1, M2, MM = position_mixes(real, dist)
    _M1M2.update(M1=M1, M2=M2, MM=MM)
    print("  M1 earned share vs marginal mix per stratum:", flush=True)
    for s in STRATA:
        print(f"    {s:<20} M1 {M1[s]['earned']:.3f} vs marg "
              f"{MM[s]['earned']:.3f}; M2 earned {M2[s]['earned']:.3f}",
              flush=True)
    real_pc_earned = sum(real["per_case"][s]["earned"] * real["share"][s]
                         for s in STRATA)

    # ---- [0] [F4] reproduction: M1/M2 + phase-1 recal, mechanisms ON ----
    print("\n== [0] [F4] reproduction (M1/M2 + phase-1 recal) ==", flush=True)
    with m1m2_regime():
        probe = gen_cases(N_CASES, 7, dist)
    probe_err = {}
    for status in ("earner", "no_earner"):
        tot = sum(1 for c in probe if c["_s0"].startswith(status))
        err = sum(1 for c in probe
                  if c["_s0"].startswith(status) and c["variances"])
        probe_err[status] = err / tot
    real_err = {}
    for status in ("earner", "no_earner"):
        ss = [s for s in STRATA if s.startswith(status)]
        num = sum(real["share"][s] * real["err_rate"][s] for s in ss)
        den = sum(real["share"][s] for s in ss)
        real_err[status] = num / den
    dist_f4 = copy.deepcopy(dist)
    for status in ("earner", "no_earner"):
        old = dist_f4["injection_rate"]["persistent"][status]
        new = old * real_err[status] / probe_err[status]
        dist_f4["injection_rate"]["persistent"][status] = new
        print(f"  coin {status}: {old:.4f} -> {new:.4f} "
              f"(probe {probe_err[status]:.3f}, target {real_err[status]:.3f})",
              flush=True)
    with m1m2_regime():
        cases0 = gen_cases(N_CASES, 7, dist_f4)
    syn0 = synth_mix(cases0)
    r0 = ratios(syn0, real)
    l1_0, fm0 = finding_l1(cases0, real["fm"])
    o0, u0 = split(cases0)
    earned0 = (sum(syn0["per_case"][s]["earned"] * syn0["share"][s]
                   for s in STRATA) / real_pc_earned)
    print(f"  [F4] repro: earned {earned0:.3f}x (bar 0.90x)  "
          f"L1={l1_0:.3f} (bar 0.030)  split {o0:.3f}/{u0:.3f} "
          f"(tgt {TGT_OVER}/{TGT_UNDER})  le56={le56(cases0):.2f}", flush=True)

    # ---- [1] direction-residual decomposition: bucket x 97/non-97 ----
    print("\n== [1] direction-residual decomposition (arm [F4]) ==", flush=True)
    ex_over = Counter()   # (bucket, is97) -> over cases in excess of target
    tgt_o = TGT_OVER * N_CASES
    act_o = sum(1 for c in cases0 if c["finding"] == 2)
    # attribute each over case to its first variance's (bucket, 97?)
    for c in cases0:
        if c["finding"] != 2 or not c["variances"]:
            continue
        v = c["variances"][0]
        ex_over[(v["element_bucket"], v["nature"] == 97)] += 1
    print(f"  over cases: actual {act_o}, target {tgt_o:.0f}, "
          f"excess {act_o - tgt_o:.0f}", flush=True)
    tot_ex = max(act_o - tgt_o, 1)
    for key, cnt in ex_over.most_common(8):
        print(f"    {key[0]:<10} {'97' if key[1] else 'non97':<6} "
              f"{cnt:>5} ({cnt / tot_ex:>5.1%} of excess)", flush=True)

    # ---- [2] secant fit of (boost_over, boost_under) in the M1/M2 regime --
    print("\n== [2] direction-balance secant fit (M1/M2 regime) ==",
          flush=True)

    def measure(bo, bu):
        d = dollar_mech.apply_direction_balance(dist_f4, bo, bu)
        with m1m2_regime():
            cs = gen_cases(N_CASES, 7, d)
        return split(cs)

    bo, bu = 1.0, 1.0
    o, u = o0, u0
    hist = [(bo, bu, o, u)]
    print(f"  (1.0, 1.0): over={o:.4f} under={u:.4f}", flush=True)
    if abs(o - TGT_OVER) < 0.005 and abs(u - TGT_UNDER) < 0.005:
        print("  already within tolerance; no fit needed", flush=True)
    else:
        # sensitivity probes
        o_a, u_a = measure(0.8, 1.0)
        so = (o_a - o) / (0.8 - 1.0)
        o_b, u_b = measure(1.0, 1.2)
        su = (u_b - u) / (1.2 - 1.0)
        print(f"  sensitivities: dOver/dBo={so:.4f} dUnder/dBu={su:.4f}",
              flush=True)
        ok = False
        for it in range(4):
            nbo = min(RAIL_HI, max(RAIL_LO, bo + (TGT_OVER - o) / so)) \
                if abs(so) > 1e-6 else bo
            nbu = min(RAIL_HI, max(RAIL_LO, bu + (TGT_UNDER - u) / su)) \
                if abs(su) > 1e-6 else bu
            railed = (abs(nbo - RAIL_LO) < 1e-9 or
                      abs(nbo - RAIL_HI) < 1e-9 or
                      abs(nbu - RAIL_LO) < 1e-9 or
                      abs(nbu - RAIL_HI) < 1e-9)
            bo, bu = nbo, nbu
            o, u = measure(bo, bu)
            hist.append((bo, bu, o, u))
            print(f"  iter {it}: ({bo:.3f}, {bu:.3f}): over={o:.4f} "
                  f"under={u:.4f}{'  RAILED' if railed else ''}", flush=True)
            if abs(o - TGT_OVER) < 0.005 and abs(u - TGT_UNDER) < 0.005:
                ok = True
                break
            if railed:
                print("  fit hit rails -- instrument insufficient", flush=True)
                break
            # refresh local sensitivities around the new point
            o_a, _ = measure(bo * 0.95, bu)
            so = (o_a - o) / (bo * 0.95 - bo) if bo else so
            _, u_b = measure(bo, bu * 1.05)
            su = (u_b - u) / (bu * 1.05 - bu) if bu else su
        print(f"  fit {'CONVERGED' if ok else 'DID NOT CONVERGE'}: "
              f"({bo:.3f}, {bu:.3f}) -> over={o:.4f} under={u:.4f}",
              flush=True)

    # ---- [3] joint validation, paired seeds ----
    print("\n== [3] joint validation (M1/M2 + refit boosts) ==", flush=True)
    d_final = dollar_mech.apply_direction_balance(dist_f4, bo, bu)
    for seed in SEEDS:
        with m1m2_regime():
            cs = gen_cases(N_CASES, seed, d_final)
        syn = synth_mix(cs)
        r = ratios(syn, real)
        l1, fm = finding_l1(cs, real["fm"])
        o, u = split(cs)
        e = (sum(syn["per_case"][s]["earned"] * syn["share"][s]
                 for s in STRATA) / real_pc_earned)
        print(f"-- seed {seed} --", flush=True)
        print(f"  earned {e:.3f}x  L1={l1:.3f} (mix "
              f"{fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f})  "
              f"split {o:.3f}/{u:.3f}  le56={le56(cs):.2f}", flush=True)
        for b in BUCKETS:
            print(f"  {b:<10}{r[b]:>7.2f}x", flush=True)

    print("\n== verdict inputs ==", flush=True)
    print(f"  fitted boosts: ({bo:.3f}, {bu:.3f}); "
          f"history={[(round(h[0], 3), round(h[1], 3), round(h[2], 4), round(h[3], 4)) for h in hist]}",
          flush=True)
    print("done.", flush=True)


if __name__ == "__main__":
    main()
