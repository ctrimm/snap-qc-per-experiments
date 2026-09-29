"""Experiment 28: fix the shares-game residuals as a group.

North-star gate: calibration. Exp24's draw fix left three interacting
residuals (after-persistent): medical 0.53x, depcare 0.41x (shares-game
costs of removing the zero-base suppression on earned/unearned/shelter),
nature-57 1.16x (its exp13 importance weights were measured pre-draw-fix).

Findings (this experiment):
1. nature-57: m_{b,57} = P(recorded 57 | drawn 57) improved under the
   corrected draw (shelter 0.474 -> 0.552, earned 0.500 -> 0.789: more
   zero-base draws, where 57 always materializes via truth correction),
   so exp13's 1/m weights overshoot. Refit with exp13's 0.8 damping:
   medical 2.86 -> 2.85, shelter 1.69 -> 1.45, earned 1.60 -> 1.01,
   depcare 1.00 -> 1.21. 57 share 1.16x -> 1.02x.
2. depcare: the exp12 kid-gate dilutes the draw -- depcare is drawn only
   on kid households but with the *unconditional* empirical weight, so the
   recorded share undershoots by ~P(kid | stratum) (synth P(kid) is
   0.51/0.52/0.35/0.30 vs real 0.44/0.74/0.10/0.37). Fix: per-stratum draw
   multiplier 1/P_synth(kid | s), undoing the generator-side gating
   dilution (the empirical mix has no such gating, so no double-counting).
   Depcare 0.44x -> ~1.0x. Depcare senior-strata matrix cells re-measured
   (0.667 -> 0.549, 0.500 -> 0.632; they rest on 3-4 draws in exp24).
3. medical: 204/206 real "nonsenior" medical variances sit on FSNDIS>0
   households, which the generator calls senior. Exp11's real-side senior
   definition (FSNELDER>0 or SSI) mis-sliced the empirical stratum mixes.
   Re-slicing with senior = FSNELDER>0 | SSI1-8>0 | FSNDIS>0 is correct in
   principle but EXPOSES a sampler composition gap -- the generator's
   senior rate is 36.2% vs real 49.6% -- so the re-sliced mixes blow up
   finding L1 (0.026 -> 0.049) and hhcomp/arithmetic (1.42x/1.32x). The
   re-sliced values are saved to exp28_resliced_mixes.json for the
   coordinator (dist.json is committed -- not touched here); adopting them
   needs the sampler senior-rate fix first (recommended follow-up, in the
   sampler's lane). Medical therefore stays ~0.55x: partial credit, with
   the binding constraint identified.

Workspace hygiene: another worker (exp29) has uncommitted BASE_POSITIVITY
changes in src/synth/household.py. Every run below restores the committed
(legacy) values in-process, so the baseline is exp24's adopted defaults.

Method (single run): [0] real aggregates under both senior definitions +
write the re-sliced mix artifact; [1] T0 baseline (20k, seed 7, legacy
sampler, hooked for drawn/recorded per (bucket, stratum) and drawn-57 per
bucket); [2] focused measurements (m57 for earned/depcare with correct
drawn distributions; keep re-measurement for the flagged matrix cells);
[3] trials T1 (57 refit) and T4 (57 refit + depcare kid-weight); [4] apply
the winners to src/synth/errors.py (delimited, uncommitted); [5] fresh
re-verify from a reloaded module.

Verdict rule: holds iff medical >= 0.75x AND depcare >= 0.60x AND
nature-57 in 0.90-1.10x AND finding L1 <= 0.030, no other bucket regressing
more than 0.10x.

Usage: python3 experiments/exp28_shares_game.py
"""
import copy
import csv
import importlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import errors, household  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402
from synth.distutil import load_dist  # noqa: E402
from synth import benefit as benefit_mod  # noqa: E402

QC = Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
SSI_COLS = [f"SSI{i}" for i in range(1, 9)]

BUCKETS = ["earned", "unearned", "shelter", "sua", "medical", "depcare",
           "hhcomp", "arithmetic"]
STRATA = ["no_earner_nonsenior", "earner_nonsenior",
          "no_earner_senior", "earner_senior"]
N = 20000
SEED = 7

# Committed (pre-exp29) sampler values; the working tree carries exp29's
# uncommitted BASE_POSITIVITY experiment, so every run below restores these
# in-process (the file documents they reproduce the old sampler exactly).
LEGACY_POSITIVITY = {
    "unearned": {"no_earner_nonsenior": 0.50, "earner_nonsenior": 0.50,
                 "no_earner_senior": 0.85, "earner_senior": 0.85},
    "shelter": {s: 0.63 for s in STRATA},
    "sua": {s: 0.72 for s in STRATA},
}


def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def real_stratum(row, use_dis):
    earner = fnum(row["FSEARN"]) > 0
    senior = (fnum(row["FSNELDER"]) > 0 or
              any(fnum(row[c]) > 0 for c in SSI_COLS) or
              (use_dis and fnum(row["FSNDIS"]) > 0))
    return ("earner" if earner else "no_earner") + "_" + \
           ("senior" if senior else "nonsenior")


def real_aggregates(use_dis):
    n_case, n_err, finding = Counter(), Counter(), Counter()
    per_case_all = Counter()
    per_case = Counter()
    kid = Counter()
    n57, n57_tot = Counter(), 0
    n = 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            s = real_stratum(row, use_dis)
            n_case[s] += 1
            st = int(row["STATUS"])
            finding[st] += 1
            if st != 1:
                n_err[s] += 1
            if fnum(row["FSNKID"]) > 0:
                kid[s] += 1
            for i in range(1, 10):
                e = (row[f"ELEMENT{i}"] or "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                per_case[(s, b)] += 1
                per_case_all[b] += 1
                if (row[f"NATURE{i}"] or "").strip() == "57":
                    n57[b] += 1
                    n57_tot += 1
    v_all = sum(per_case_all.values())
    return {
        "n": n,
        "finding": {k: finding[k] / n for k in (1, 2, 3)},
        "p_stratum": {s: n_case[s] / n for s in STRATA},
        "per_case": {(s, b): per_case[(s, b)] / n_case[s]
                     for s in STRATA for b in BUCKETS},
        "per_case_all": {b: per_case_all[b] / n for b in BUCKETS},
        "p_kid": {s: kid[s] / n_case[s] for s in STRATA},
        "n57_share": n57_tot / v_all,
    }


def resliced_mixes():
    """Re-slice the empirical 4-stratum bucket mixes with the corrected
    senior definition (exp11's procedure otherwise). For the coordinator's
    dist.json application -- NOT applied here (see findings)."""
    strata, totals = Counter(), Counter()
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            s = real_stratum(row, use_dis=True)
            totals[s] += 1
            for i in range(1, 10):
                e = (row[f"ELEMENT{i}"] or "").strip()
                if e:
                    strata[(s, element_bucket(int(e)))] += 1
    out = {}
    for s in STRATA:
        filt = {b: strata[(s, b)] for b in BUCKETS if (s, b) in strata}
        tot = sum(filt.values())
        out[f"bucket_probs_given_{s}"] = \
            {b: filt.get(b, 0) / tot for b in BUCKETS}
    return out


# ---------------- generation ----------------

def gen_cases(n, seed, dist, hooked=False):
    drawn57 = Counter()
    orig_dn = errors._draw_nature
    orig_ip = errors._inject_persistent
    rec_drawn, rec_recorded = Counter(), Counter()

    def counting_dn(facts, bucket, dist_, dir_w, rng):
        nature, cause = orig_dn(facts, bucket, dist_, dir_w, rng)
        if nature == 57:
            drawn57[bucket] += 1
        return nature, cause

    def counting_ip(facts, rng, dist_, applicable, dir_w, max_attempts,
                    stats=None, **kwargs):
        s = errors._stratum_key(facts)
        local = {"drawn": Counter(), "recorded": Counter()}
        out = orig_ip(facts, rng, dist_, applicable, dir_w, max_attempts,
                      stats=local, **kwargs)
        for b, c in local["drawn"].items():
            rec_drawn[(s, b)] += c
        for b, c in local["recorded"].items():
            rec_recorded[(s, b)] += c
        return out

    rng = random.Random(seed)
    try:
        if hooked:
            errors._draw_nature = counting_dn
            errors._inject_persistent = counting_ip
        cases = [errors.inject(household.sample_household(rng), rng, dist,
                               max_attempts=12, persistent_buckets=True)
                 for _ in range(n)]
    finally:
        errors._draw_nature = orig_dn
        errors._inject_persistent = orig_ip
    return cases, {"drawn57": drawn57}


def mixes(cases, real):
    f = Counter(c["finding"] for c in cases)
    n = len(cases)
    b = Counter()
    n57_tot = 0
    for c in cases:
        for v in c["variances"]:
            b[v["element_bucket"]] += 1
            if v["nature"] == 57:
                n57_tot += 1
    v = sum(b.values())
    fm = {k: f[k] / n for k in (1, 2, 3)}
    rf = real["finding"]
    return {
        "finding": fm,
        "finding_l1": sum(abs(fm[k] - rf[k]) for k in (1, 2, 3)),
        "ratio": {bkt: (b[bkt] / n) / real["per_case_all"][bkt]
                  for bkt in BUCKETS},
        "n57_ratio": (n57_tot / v) / real["n57_share"] if v else 0,
    }


def report(name, mm):
    print(f"    [{name}] L1={mm['finding_l1']:.3f} "
          f"57={mm['n57_ratio']:.2f}x " +
          " ".join(f"{b}={mm['ratio'][b]:.2f}x" for b in BUCKETS),
          flush=True)


# ---------------- focused measurements ----------------

def m57_forced_bucket(dist, bucket, n, seed):
    """m57 with the bucket draw forced (stratum/nature/household natural);
    depcare respects the kid gate like the real flow."""
    rng = random.Random(seed)
    dir_w = (dist.get("effectiveness") or {}).get("dir_weight", {})
    drawn57 = rec57 = got = guard = 0
    while got < n and guard < n * 100:
        guard += 1
        facts = household.sample_household(rng)
        if bucket == "depcare" and facts.get("n_kids", 0) == 0:
            continue
        got += 1
        nature, _ = errors._draw_nature(facts, bucket, dist, dir_w, rng)
        if nature != 57:
            continue
        drawn57 += 1
        agency = copy.deepcopy(facts)
        truth = facts
        c_issued = benefit_mod.compute(agency)["benefit"]
        c_correct = benefit_mod.compute(truth)["benefit"]
        tcorr, _ = errors._apply_one(agency, truth, bucket, 57, rng, dist)
        if tcorr:
            truth = {**truth, **tcorr}
        t_issued = max(0, int(round(benefit_mod.compute(agency)["benefit"])))
        t_correct = benefit_mod.compute(truth)["benefit"]
        if (t_issued, t_correct) != (c_issued, c_correct) and \
                t_issued != t_correct:
            rec57 += 1
    return rec57 / drawn57 if drawn57 else float("nan"), drawn57


def m57_earned_stratified(dist, stratum_w, n, seed):
    """m57 for earned with households matched to the drawn-earned stratum
    mix (earned 57s are too rare for the 20k-run count, n=8)."""
    rng = random.Random(seed)
    strata, ws = zip(*stratum_w.items())
    rec = got = guard = 0
    while got < n and guard < n * 100:
        guard += 1
        s = rng.choices(strata, weights=ws)[0]
        facts = household.sample_household(rng)
        if errors._stratum_key(facts) != s:
            continue
        got += 1
        agency = copy.deepcopy(facts)
        truth = facts
        c_issued = benefit_mod.compute(agency)["benefit"]
        c_correct = benefit_mod.compute(truth)["benefit"]
        tcorr, _ = errors._apply_one(agency, truth, "earned", 57, rng,
                                     dist)
        if tcorr:
            truth = {**truth, **tcorr}
        t_issued = max(0, int(round(benefit_mod.compute(agency)["benefit"])))
        t_correct = benefit_mod.compute(truth)["benefit"]
        if (t_issued, t_correct) != (c_issued, c_correct) and \
                t_issued != t_correct:
            rec += 1
    return rec / got if got else float("nan"), got


def keep_focused(dist, bucket, stratum, n, seed, kid_only=False):
    """Keep rate for one (bucket, stratum) cell with the natural
    within-stratum household mix (kid_only for the gated depcare)."""
    rng = random.Random(seed)
    dir_w = (dist.get("effectiveness") or {}).get("dir_weight", {})
    drawn = recorded = got = guard = 0
    while got < n and guard < n * 80:
        guard += 1
        facts = household.sample_household(rng)
        if errors._stratum_key(facts) != stratum:
            continue
        if kid_only and facts.get("n_kids", 0) == 0:
            continue
        got += 1
        drawn += 1
        nature, _ = errors._draw_nature(facts, bucket, dist, dir_w, rng)
        agency = copy.deepcopy(facts)
        truth = facts
        c_issued = benefit_mod.compute(agency)["benefit"]
        c_correct = benefit_mod.compute(truth)["benefit"]
        noise = 0.0
        if bucket == "arithmetic":
            noise = rng.choice([-1, 1]) * rng.uniform(10, 60)
        else:
            tcorr, nover = errors._apply_one(agency, truth, bucket, nature,
                                             rng, dist)
            if tcorr:
                truth = {**truth, **tcorr}
            if nover is not None:
                nature = nover
        t_issued = max(0, int(round(benefit_mod.compute(agency)["benefit"]
                                   + noise)))
        t_correct = benefit_mod.compute(truth)["benefit"]
        if (t_issued, t_correct) != (c_issued, c_correct) and \
                t_issued != t_correct:
            recorded += 1
    return recorded / drawn if drawn else float("nan"), drawn


# ---------------- main ----------------

def main():
    household.BASE_POSITIVITY = copy.deepcopy(LEGACY_POSITIVITY)
    dist = load_dist(ROOT / "experiments/dist.json")
    assert errors.ZERO_BASE_WEIGHT == {}, "exp24 default expected"

    print("[0] real aggregates + re-sliced mix artifact (held-out; "
          "aggregate-only)...", flush=True)
    real = real_aggregates(use_dis=False)
    real_new = real_aggregates(use_dis=True)
    print(f"    real finding mix: {real['finding'][1]:.3f}/"
          f"{real['finding'][2]:.3f}/{real['finding'][3]:.3f}")
    new_mixes = resliced_mixes()
    art = ROOT / "experiments/exp28_resliced_mixes.json"
    art.write_text(json.dumps({
        "_note": "Re-sliced empirical 4-stratum bucket mixes, senior = "
                 "FSNELDER>0 | SSI1-8>0 | FSNDIS>0 (exp11 procedure "
                 "otherwise). Exp28 measured in-process only: adopting needs "
                 "the sampler senior-rate fix first (generator senior rate "
                 "36.2% vs real 49.6%; see exp28 chronicle). For the "
                 "coordinator to apply to dist.json. Aggregates only; never "
                 "microdata.",
        "mixes": new_mixes,
    }, indent=1) + "\n")
    print(f"    wrote {art}")

    print(f"\n[1] T0 BASELINE: {N} cases, seed {SEED} (hooked)...",
          flush=True)
    cases0, hk0 = gen_cases(N, SEED, dist, hooked=True)
    m0 = mixes(cases0, real)
    report("T0 baseline", m0)

    # P(kid|s) in the generator
    pkid, nstr = Counter(), Counter()
    for c in cases0:
        s = errors._stratum_key(c["facts"])
        nstr[s] += 1
        if c["facts"].get("n_kids", 0) > 0:
            pkid[s] += 1
    pkid = {s: pkid[s] / nstr[s] for s in STRATA}
    kid_w = {s: round(1.0 / pkid[s], 3) for s in STRATA}
    print("    P_synth(kid>0|s):",
          {s: round(pkid[s], 3) for s in STRATA},
          "-> kid_w:", kid_w, flush=True)

    # m57 from the 20k run (medical/shelter have adequate samples)
    rec57 = Counter()
    for c in cases0:
        for v in c["variances"]:
            if v["nature"] == 57:
                rec57[v["element_bucket"]] += 1
    m57_20k = {}
    for bkt in ["medical", "shelter"]:
        d = hk0["drawn57"][bkt]
        m57_20k[bkt] = rec57[bkt] / d
        print(f"    m57[{bkt}] 20k-run: {m57_20k[bkt]:.3f} (n={d})",
              flush=True)

    print("\n[2] focused measurements...", flush=True)
    m_dep57, dd = m57_forced_bucket(dist, "depcare", 20000, 99)
    print(f"    m57[depcare] forced-bucket (kid-gated): {m_dep57:.3f} "
          f"(n={dd})", flush=True)
    # stratum weights of drawn earned, for the stratified m57
    sw = Counter()
    rng = random.Random(SEED)
    orig_ip = errors._inject_persistent

    def sw_wrap(facts, rng_, dist_, applicable, dir_w, max_attempts,
                stats=None, **kw):
        s = errors._stratum_key(facts)
        local = {"drawn": Counter(), "recorded": Counter()}
        out = orig_ip(facts, rng_, dist_, applicable, dir_w, max_attempts,
                      stats=local, **kw)
        sw[s] += local["drawn"].get("earned", 0)
        return out

    errors._inject_persistent = sw_wrap
    try:
        for _ in range(N):
            errors.inject(household.sample_household(rng), rng, dist,
                          max_attempts=12, persistent_buckets=True)
    finally:
        errors._inject_persistent = orig_ip
    sw = {s: sw[s] / sum(sw.values()) for s in STRATA}
    m_earn57, dd = m57_earned_stratified(dist, sw, 4000, 99)
    print(f"    m57[earned] stratified forced: {m_earn57:.3f} (n={dd})",
          flush=True)
    k_med_es, dd = keep_focused(dist, "medical", "earner_senior", 10000,
                                101)
    print(f"    keep[medical/earner_senior]: {k_med_es:.3f} (n={dd}) vs "
          f"hard-coded {errors.MATERIALIZATION_MATRIX['medical']['earner_senior']:.3f}",
          flush=True)
    k_dep_ns, dd = keep_focused(dist, "depcare", "no_earner_senior", 4000,
                                102, kid_only=True)
    k_dep_es, dd2 = keep_focused(dist, "depcare", "earner_senior", 4000,
                                 103, kid_only=True)
    print(f"    keep[depcare/no_earner_senior] kid-filtered: {k_dep_ns:.3f} "
          f"(n={dd}) vs hard-coded "
          f"{errors.MATERIALIZATION_MATRIX['depcare']['no_earner_senior']:.3f}",
          flush=True)
    print(f"    keep[depcare/earner_senior] kid-filtered: {k_dep_es:.3f} "
          f"(n={dd2}) vs hard-coded "
          f"{errors.MATERIALIZATION_MATRIX['depcare']['earner_senior']:.3f}",
          flush=True)

    new_w57 = {
        "medical": round(min(5.0, 0.8 / m57_20k["medical"]), 2),
        "shelter": round(min(5.0, 0.8 / m57_20k["shelter"]), 2),
        "earned": round(min(5.0, 0.8 / m_earn57), 2),
        "depcare": round(min(5.0, 0.8 / m_dep57), 2),
    }
    print("    refit _NATURE_57_WEIGHT:", new_w57, flush=True)
    dep_cells = {"depcare": {
        "no_earner_senior": round(k_dep_ns, 6),
        "earner_senior": round(k_dep_es, 6)}}
    med_cells = {"medical": {"earner_senior": round(k_med_es, 6)}}

    # ---- [3] trials ----
    old_w57 = dict(errors._NATURE_57_WEIGHT)
    old_mat = {b: dict(v) for b, v in errors.MATERIALIZATION_MATRIX.items()}

    def trial(name, w57=None, kidweight=False, mat=None):
        if w57:
            errors._NATURE_57_WEIGHT.update(w57)
        if mat:
            for b, cells in mat.items():
                errors.MATERIALIZATION_MATRIX[b].update(cells)
        ab_orig = errors._applicable_buckets
        if kidweight:
            def ab_patched(facts, dist_, rng_):
                cands = ab_orig(facts, dist_, rng_)
                if "depcare" in cands and facts.get("n_kids", 0) > 0:
                    cands["depcare"] *= kid_w[errors._stratum_key(facts)]
                return cands
            errors._applicable_buckets = ab_patched
        try:
            cs, _ = gen_cases(N, SEED, dist)
        finally:
            errors._NATURE_57_WEIGHT.clear()
            errors._NATURE_57_WEIGHT.update(old_w57)
            for b, cells in old_mat.items():
                errors.MATERIALIZATION_MATRIX[b].clear()
                errors.MATERIALIZATION_MATRIX[b].update(cells)
            if kidweight:
                errors._applicable_buckets = ab_orig
        return mixes(cs, real)

    print(f"\n[3] trials ({N} cases, seed {SEED} each)...", flush=True)
    report("T0 baseline", m0)
    m1 = trial("T1 57-refit", w57=new_w57)
    report("T1 57-refit", m1)
    m4 = trial("T4 +depcare-kidw", w57=new_w57, kidweight=True,
               mat={**dep_cells, **med_cells})
    report("T4 +depcare-kidw", m4)

    # ---- [4] apply winners to src/synth/errors.py ----
    print("\n[4] applying winners to src/synth/errors.py...", flush=True)
    ep = ROOT / "src/synth/errors.py"
    src = ep.read_text()
    w57_block = '''_NATURE_57_WEIGHT = {
    # 1 / materialization rate, re-measured in the persistent flow under
    # the corrected draw (exp28; exp13's values were measured pre-draw-fix
    # and overshot the 57 share to 1.16x), scaled by exp13's 0.8 damping.
    # medical/shelter: 20k-run m = 0.281/0.552; earned: stratified forced
    # m = 0.789 (n=4000); depcare: forced-bucket kid-gated m = 0.661
    # (n=1467 drawn 57s).
    "medical": %(medical)s,
    "shelter": %(shelter)s,
    "earned": %(earned)s,
    "depcare": %(depcare)s,
}''' % new_w57
    import re
    src = re.sub(r"_NATURE_57_WEIGHT = \{[^}]*\}",
                 w57_block, src, count=1)
    # depcare kid-dilution weight table + hook in _applicable_buckets
    kid_block = '''
# Exp28: depcare kid-dilution correction. Depcare is drawn only on kid
# households (exp12 gate) but with the *unconditional* empirical weight,
# so the recorded share undershoots by ~P(kid | stratum). Multiplying the
# depcare draw weight by 1/P_synth(kid | stratum) undoes the
# generator-side gating dilution (the empirical mix has no such gating,
# so this is not double-counting). P_synth(kid | s) measured on the
# committed sampler (20k, seed 7); re-measure if the sampler's kid rates
# change.
_DEPCARE_KID_WEIGHT = {
    "no_earner_nonsenior": %(nens)s,
    "earner_nonsenior": %(ens)s,
    "no_earner_senior": %(nes)s,
    "earner_senior": %(es)s,
}
''' % {"nens": kid_w["no_earner_nonsenior"],
       "ens": kid_w["earner_nonsenior"],
       "nes": kid_w["no_earner_senior"],
       "es": kid_w["earner_senior"]}
    # depcare kid-dilution weight table, inserted just before the
    # (rewritten) _NATURE_57_WEIGHT statement so both exp28 additions sit
    # together and clearly delimited.
    stmt = "_NATURE_57_WEIGHT = {"
    assert src.count(stmt) == 1
    src = src.replace(stmt, kid_block + stmt, 1)
    # hook the weight into _applicable_buckets, after the zero-base
    # scaling so it multiplies the final w (not overwritten by it)
    old_gate = '''        # depcare variances occur exclusively on kid households (exp12)
        if bucket == "depcare" and facts.get("n_kids", 0) == 0:
            continue
        field = _BASE_FIELD.get(bucket)
        if field is not None:
            base = facts[field]
            base_pos = (base == 1) if bucket == "sua" else (base > 0)
            if not base_pos:
                w = ZERO_BASE_WEIGHT.get(bucket, 1.0)'''
    new_gate = old_gate + '''
        # exp28: undo the kid-gating dilution (see _DEPCARE_KID_WEIGHT).
        # Placed after the zero-base scaling so it multiplies the final w
        # rather than being overwritten by it.
        if bucket == "depcare":
            w *= _DEPCARE_KID_WEIGHT[f"{earner}_{senior}"]'''
    assert old_gate in src
    src = src.replace(old_gate, new_gate, 1)
    # corrected matrix cells (focused re-measurement; exp24's depcare
    # senior cells rested on 3-4 draws, medical/earner_senior was stale)
    for (b, s), val in [(("depcare", "no_earner_senior"), k_dep_ns),
                        (("depcare", "earner_senior"), k_dep_es),
                        (("medical", "earner_senior"), k_med_es)]:
        old_v = errors.MATERIALIZATION_MATRIX[b][s]
        pat = re.compile(r'("%s":\s*\{[^}]*?"%s":\s*)([0-9.]+)' % (b, s))
        src, n_sub = pat.subn(r"\g<1>%.6f" % val, src, count=1)
        assert n_sub == 1, (b, s)
        print(f"    matrix {b}/{s}: {old_v:.6f} -> {val:.6f}", flush=True)
    ep.write_text(src)
    print("    wrote", ep, flush=True)

    # ---- [5] fresh re-verify from the reloaded module ----
    print("\n[5] fresh re-verify (reloaded errors.py)...", flush=True)
    importlib.reload(errors)
    household.BASE_POSITIVITY = copy.deepcopy(LEGACY_POSITIVITY)
    dist2 = load_dist(ROOT / "experiments/dist.json")
    cases_f, _ = gen_cases(N, SEED, dist2)
    mf = mixes(cases_f, real)
    report("FINAL applied", mf)
    # verdict
    ok57 = 0.90 <= mf["n57_ratio"] <= 1.10
    okL1 = mf["finding_l1"] <= 0.030
    okmed = mf["ratio"]["medical"] >= 0.75
    okdep = mf["ratio"]["depcare"] >= 0.60
    reg = {b: m0["ratio"][b] - mf["ratio"][b] for b in BUCKETS
           if b not in ("medical", "depcare")}
    okreg = all(v <= 0.10 for v in reg.values())
    print(f"    verdict checks: 57in[0.9,1.1]={ok57} L1<=0.030={okL1} "
          f"medical>=0.75x={okmed} ({mf['ratio']['medical']:.2f}x) "
          f"depcare>=0.60x={okdep} ({mf['ratio']['depcare']:.2f}x) "
          f"no-reg>0.10x={okreg}", flush=True)
    if not okreg:
        print("    regressions:",
              {b: round(v, 3) for b, v in reg.items() if v > 0.10},
              flush=True)
    print("    DONE", flush=True)


if __name__ == "__main__":
    main()
