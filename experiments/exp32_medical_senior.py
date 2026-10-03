#!/usr/bin/env python3
"""Experiment 32 — unblock medical via the senior-rate path (exp28's diagnosis).

exp28 left medical stuck at 0.55x (gate 0.75x): the empirical re-slice that
would fix medical's draw rate (senior = FSNELDER>0 | SSI1-8>0 | FSNDIS>0)
could not be adopted because the sampler's senior rate (36.2%) sits far below
real (49.6%) — concentrating the empirical mass in senior strata blew up
hhcomp/arithmetic (T2: L1 0.026 -> 0.049).

This experiment:
  [0] Confirms the senior-rate gap on the current tree (exp29/exp31 changed
      the sampler and defaults since exp28 measured 36.2% vs 49.6%) and
      decomposes it: senior-age draw vs disability flag (FSNDIS>0).
  [1] Trials, paired seeds 7/8, 20k cases, current defaults (dollar
      mechanisms ON):
        A  exp31 baseline: legacy senior tables + committed dist/matrix
        B  A + senior fix (src/synth/household.py exp32 tables)
        C  B + re-sliced empirical mixes (in-process; dist.json untouched)
        D  C + real size-mix weights (diagnostic only: is the size mix the
           remaining blocker for the overall 49.6%?)
      B-vs-A isolates the rate change; C-vs-B isolates the mix change.
  [2] Interaction check: the senior fix shifts stratum composition, so
      re-measure the materialization matrix with the senior-fix effect
      ISOLATED ((b) senior-fix + mech ON vs (a) legacy-senior + mech ON;
      the (a)-vs-committed gap is the dollar-mechanism confound, already
      absorbed by exp31's effectiveness re-fit). Adopt iff >=15/32 cells
      shift >=0.05 on the isolated effect (exp29's rule). Also re-measure
      _DEPCARE_KID_WEIGHT (documented maintenance: re-run whenever the
      sampler changes; pure sampler property, unconfounded).
  [3] Final validation of the winner on seeds 7/8.

Verdict bars: medical >= 0.75x AND finding L1 <= 0.030 AND no other bucket
regressing more than 0.10x vs the exp31 baseline (arm A).

Real QC microdata is held-out validation: aggregates are read, nothing
per-row is committed. Committed dist.json/eff.json/inject.json are never
touched (re-sliced mixes applied in-process only).
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

REAL = (Path.home() / "workspace/snap-qc-data/raw/qcfy2024_csv"
        / "qc_pub_fy2024.csv")
BUCKETS = ["earned", "shelter", "unearned", "sua", "medical",
           "hhcomp", "arithmetic", "depcare"]
STRATA = ["no_earner_nonsenior", "earner_nonsenior",
          "no_earner_senior", "earner_senior"]
SEEDS = (7, 8)
N_CASES = 20000

# Legacy (pre-exp32) senior tables, for the in-process arm-A comparison.
LEGACY_ELDERLY = {1: 0.28, 2: 0.08, 3: 0.08}
LEGACY_DISABLED = {1: 0.12, 2: 0.12, 3: 0.12}

# Real FY2024 post-screen size mix (diagnostic arm D only; 7+ pooled into 6).
REAL_SIZE_W = [0.597, 0.158, 0.103, 0.071, 0.040, 0.031]
SIZE_POP = [1, 2, 3, 4, 5, 6]
SIZE_W_OLD = [0.45, 0.25, 0.14, 0.09, 0.04, 0.03]


# --------------------------------------------------------------------------
# aggregates
# --------------------------------------------------------------------------
def fnum(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def real_aggregates(path):
    finding, bucket, nat57, nvar = Counter(), Counter(), 0, 0
    signed = []
    n = 0
    eld = dis = sen = 0
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
                    nvar += 1
                nn = (row[f"NATURE{i}"] or "").strip()
                if nn == "57":
                    nat57 += 1
            e = fnum(row["FSNELDER"]) > 0
            d = fnum(row["FSNDIS"]) > 0 or any(
                fnum(row[f"SSI{i}"]) > 0 for i in range(1, 9))
            eld += e
            dis += (d and not e)
            sen += (e or d)
    v = sum(bucket.values())
    ab = sorted(abs(x) for x in signed)
    return {
        "finding": {1: finding["1"] / n, 2: finding["2"] / n,
                    3: finding["3"] / n},
        "per_case": {b: bucket[b] / n for b in BUCKETS},
        "elem_share": {b: bucket[b] / v for b in BUCKETS},
        "s57": nat57 / nvar,
        "le56": sum(1 for x in ab if x <= 56) / len(ab),
        "d_med": statistics.median(ab),
        "senior": {"p_elderly": eld / n, "p_dis_given_not_eld": dis / (n - eld),
                   "p_senior": sen / n},
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
    b, n57, nv = Counter(), 0, 0
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
            nv += 1
            if v["nature"] == 57:
                n57 += 1
    v = sum(b.values())
    ab = sorted(abs(x) for x in d_all)
    return {
        "finding": {k: f[k] / n for k in (1, 2, 3)},
        "per_case": {k: b[k] / n for k in BUCKETS},
        "elem_share": {k: b[k] / v for k in BUCKETS} if v else {},
        "s57": n57 / nv if nv else 0.0,
        "le56": sum(1 for x in ab if x <= 56) / len(ab) if ab else 0.0,
        "d_med": statistics.median(ab) if ab else 0.0,
        "n": n,
    }


def l1(a, b):
    return sum(abs(a[k] - b.get(k, 0.0)) for k in a)


# --------------------------------------------------------------------------
# in-process patches (all restored via try/finally)
# --------------------------------------------------------------------------
class legacy_senior:
    """Arm A: restore the pre-exp32 senior draw tables in-process."""

    def __enter__(self):
        self._e = household._P_ELDERLY_BY_SIZE
        self._d = household._P_DISABLED_BY_SIZE
        household._P_ELDERLY_BY_SIZE = dict(LEGACY_ELDERLY)
        household._P_DISABLED_BY_SIZE = dict(LEGACY_DISABLED)

    def __exit__(self, *a):
        household._P_ELDERLY_BY_SIZE = self._e
        household._P_DISABLED_BY_SIZE = self._d


def resliced_dist(dist):
    """dist copy with exp28's re-sliced 4-stratum mixes (in-process only)."""
    rs = json.load(open(EXP_DIR / "exp28_resliced_mixes.json"))["mixes"]
    d = copy.deepcopy(dist)
    for k, v in rs.items():
        d[k] = dict(v)
    return d


_ORIG_CHOICES = random.Random.choices


class real_size_mix:
    """Arm D (diagnostic): draw household size from the real FY2024
    post-screen mix instead of the sampler's weights."""

    def __enter__(self):
        def _patched(self, population, weights=None, *, cum_weights=None,
                     k=1):
            if (weights is not None and list(population) == SIZE_POP
                    and list(weights) == SIZE_W_OLD):
                weights = REAL_SIZE_W
            return _ORIG_CHOICES(self, population, weights,
                                 cum_weights=cum_weights, k=k)
        random.Random.choices = _patched

    def __exit__(self, *a):
        random.Random.choices = _ORIG_CHOICES


def synth_senior_rate(n=60000, seed=5):
    rng = random.Random(seed)
    e = d = s = 0
    for _ in range(n):
        f = household.sample_household(rng)
        e += f["n_elderly"]
        d += f["n_disabled"]
        s += f["senior_disabled"]
    return {"p_elderly": e / n, "p_dis_given_not_eld": d / (n - e),
            "p_senior": s / n}


# --------------------------------------------------------------------------
# stage 0: confirm the senior-rate gap on the current tree
# --------------------------------------------------------------------------
def stage0(real):
    print("== [0] senior-rate gap: real vs synth ==")
    rs = real["senior"]
    print(f"  real FY2024: P(elderly)={rs['p_elderly']:.4f} "
          f"P(dis|~eld)={rs['p_dis_given_not_eld']:.4f} "
          f"P(senior)={rs['p_senior']:.4f}")
    with legacy_senior():
        pre = synth_senior_rate()
    post = synth_senior_rate()
    for label, s in (("legacy tables (arm A)", pre),
                     ("exp32 tables  (arm B)", post)):
        print(f"  synth {label}: P(elderly)={s['p_elderly']:.4f} "
              f"P(dis|~eld)={s['p_dis_given_not_eld']:.4f} "
              f"P(senior)={s['p_senior']:.4f}")
    print("  driver decomposition (real - legacy-synth, post-screen):")
    print(f"    elderly draw gap:      {rs['p_elderly'] - pre['p_elderly']:+.4f}")
    print(f"    disability-flag gap:   "
          f"{rs['p_dis_given_not_eld'] - pre['p_dis_given_not_eld']:+.4f}")
    return pre, post


# --------------------------------------------------------------------------
# stage 1: trials A/B/C/D
# --------------------------------------------------------------------------
def show_trial(label, m, real, base_m=None):
    fm = m["finding"]
    print(f"  {label}: finding {fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f} "
          f"L1={l1(fm, real['finding']):.3f}  s57={m['s57'] / real['s57']:.2f}x"
          f"  le56={m['le56']:.2f} d_med={m['d_med']:.0f}")
    for b in BUCKETS:
        r = m["per_case"][b] / real["per_case"][b]
        tag = ""
        if base_m is not None:
            rb = base_m["per_case"][b] / real["per_case"][b]
            tag = f" (A: {rb:.2f}x)"
        print(f"    {b:10s} {r:.2f}x{tag}")


def stage1(real, dist):
    print(f"\n== [1] trials A/B/C/D: {N_CASES} cases, seeds {SEEDS}, "
          "dollar mechanisms ON ==")
    res = {}
    for sd in SEEDS:
        print(f"\n-- seed {sd} --")
        d_mech = dollar_mech.enable_adopted(dist)
        try:
            with legacy_senior():
                a = mixes(gen_cases(N_CASES, sd, d_mech))
            print("  A (exp31 baseline):")
            show_trial("A", a, real)
            b = mixes(gen_cases(N_CASES, sd, d_mech))
            print("  B (A + senior fix):")
            show_trial("B", b, real, a)
            d_rs = dollar_mech.enable_adopted(resliced_dist(dist))
            c = mixes(gen_cases(N_CASES, sd, d_rs))
            print("  C (B + re-sliced mixes):")
            show_trial("C", c, real, a)
            with real_size_mix():
                d = mixes(gen_cases(N_CASES, sd, d_rs))
            print("  D (C + real size mix, diagnostic):")
            show_trial("D", d, real, a)
        finally:
            dollar_mech.disable()
        res[sd] = {"A": a, "B": b, "C": c, "D": d}
        # ablation decomposition: rate change (B-A) vs mix change (C-B)
        for x, y, nm in (("A", "B", "rate change B-A"),
                         ("B", "C", "mix change C-B")):
            mx, my = res[sd][x], res[sd][y]
            print(f"  ablation {nm}: dL1={l1(my['finding'], real['finding']) - l1(mx['finding'], real['finding']):+.3f} "
                  f"d(medical)={(my['per_case']['medical'] - mx['per_case']['medical']) / real['per_case']['medical']:+.2f}x "
                  f"d(hhcomp)={(my['per_case']['hhcomp'] - mx['per_case']['hhcomp']) / real['per_case']['hhcomp']:+.2f}x "
                  f"d(arith)={(my['per_case']['arithmetic'] - mx['per_case']['arithmetic']) / real['per_case']['arithmetic']:+.2f}x")
    return res


# --------------------------------------------------------------------------
# stage 2: interaction checks under the new composition
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
    """exp21 procedure under the senior-fix composition (committed mixes:
    keep rates are conditional on drawn bucket+stratum, so the draw mix does
    not matter). Dollar mechanisms ON, committed matrix active."""
    _KR_DRAWN.clear()
    _KR_RECORDED.clear()
    d_mech = dollar_mech.enable_adopted(dist)
    errors._inject_persistent = _kr_ip
    try:
        gen_cases(n, seed, d_mech)
    finally:
        errors._inject_persistent = _ORIG_IP
        dollar_mech.disable()
    mat, draws = {}, {}
    for b in BUCKETS:
        mat[b], draws[b] = {}, {}
        for s in STRATA:
            d = _KR_DRAWN[(b, s)]
            r = _KR_RECORDED[(b, s)]
            draws[b][s] = d
            mat[b][s] = round(min(1.0, max(0.02, r / d if d else 1.0)), 6)
    return mat, draws


def stage2_matrix(real, dist):
    print("\n== [2a] materialization matrix: isolate the senior-fix effect ==")
    print("  (b) senior-fix + mech ON vs (a) legacy-senior + mech ON, 150k, "
          "seed 11; the (a)-vs-committed gap is the dollar-mechanism confound")
    committed = dict(errors.MATERIALIZATION_MATRIX)
    new_mat, draws = remeasure_matrix(dist)          # (b)
    with legacy_senior():                            # (a)
        amat, _ = remeasure_matrix(dist)
    n_ba = n_ac = 0
    print(f"  {'bucket':<10}" + "".join(f"{s:>24}" for s in STRATA))
    for b in BUCKETS:
        row = f"  {b:<10}"
        for s in STRATA:
            dba = new_mat[b][s] - amat[b][s]
            dac = amat[b][s] - committed[b][s]
            if abs(dba) >= 0.05:
                n_ba += 1
            if abs(dac) >= 0.05:
                n_ac += 1
            flag = "*" if abs(dba) >= 0.05 else " "
            row += f"{new_mat[b][s]:>10.3f}(b-a{dba:>+6.3f}){flag}"
        print(row)
    print(f"  cells |b-a|>=0.05 (senior-fix effect): {n_ba}/32 "
          f"(adoption bar: >= 15/32)")
    print(f"  cells |a-committed|>=0.05 (mechanism confound): {n_ac}/32")
    adopted = None
    if n_ba >= 15:
        adopted = {}
        pooled = []
        for b in BUCKETS:
            adopted[b] = {}
            for s in STRATA:
                if draws[b][s] >= 200:
                    adopted[b][s] = new_mat[b][s]
                else:
                    adopted[b][s] = committed[b][s]
                    pooled.append(f"{b}/{s}")
        print(f"  ADOPTING re-measured matrix; pooled (<200 draws): {pooled}")
        json.dump({"matrix": adopted, "draws": draws,
                   "_note": "exp32 re-measurement under the senior-fix "
                            "composition (150k cases, seed 11); >=200-draw "
                            "cells take the new value, tiny-sample cells pool "
                            "the committed exp29 value."},
                  open(EXP_DIR / "exp32_matrix.json", "w"), indent=1)
        _rewrite_matrix_block(adopted)
    else:
        print("  senior-fix effect below the bar: keeping the committed "
              "matrix. (The (b)-vs-committed shift is the dollar-mechanism "
              "effect, already absorbed by exp31's effectiveness re-fit; "
              "re-measuring the matrix alone double-counts it.)")
    return adopted


def _rewrite_matrix_block(new_mat):
    p = EXP_DIR.parent / "src" / "synth" / "errors.py"
    src = p.read_text()
    lines = ["MATERIALIZATION_MATRIX = {"]
    for b in BUCKETS:
        cells = ", ".join(f'"{s}": {new_mat[b][s]:.6f}' for s in STRATA)
        lines.append(f'    "{b}": {{{cells}}},')
    lines.append("}")
    block = "\n".join(lines)
    import re
    new_src, n = re.subn(r"MATERIALIZATION_MATRIX = \{.*?\n\}",
                         block + "\n", src, count=1, flags=re.DOTALL)
    assert n == 1, "matrix block regex did not match exactly once"
    note = ("# exp32: re-measured under the senior-fix composition (150k, "
            "seed 11); >=200-draw cells take the new value, tiny-sample "
            "cells pool the exp29 value (see experiments/exp32_medical_"
            "senior.py).\n")
    new_src = new_src.replace("MATERIALIZATION_MATRIX = {",
                              note + "MATERIALIZATION_MATRIX = {", 1)
    p.write_text(new_src)
    print("  wrote re-measured MATERIALIZATION_MATRIX to src/synth/errors.py")


def stage2_kidweight():
    print("\n== [2b] _DEPCARE_KID_WEIGHT re-measurement under the senior fix ==")
    rng = random.Random(5)
    nstr, pkid = Counter(), Counter()
    for _ in range(100000):
        f = household.sample_household(rng)
        s = errors._stratum_key(f)
        nstr[s] += 1
        if f["n_kids"] > 0:
            pkid[s] += 1
    old_w = errors._DEPCARE_KID_WEIGHT
    new_w, shifted = {}, False
    print(f"  {'stratum':<20}{'P(kid|s)':>9}{'old w':>8}{'new w':>8}")
    for s in STRATA:
        p = pkid[s] / nstr[s]
        w = round(1.0 / p, 3)
        new_w[s] = w
        ds = abs(w - old_w[s]) / old_w[s]
        if ds > 0.03:
            shifted = True
        print(f"  {s:<20}{p:>9.3f}{old_w[s]:>8.3f}{w:>8.3f}"
              f"{' *' if ds > 0.03 else ''}")
    if shifted:
        print("  ADOPTING re-measured kid weights (>3% shift on a stratum)")
        _rewrite_kidweight_block(new_w)
    else:
        print("  shifts <= 3%: keeping the committed weights; noting it.")
    return new_w if shifted else None


def _rewrite_kidweight_block(new_w):
    p = EXP_DIR.parent / "src" / "synth" / "errors.py"
    src = p.read_text()
    lines = ["_DEPCARE_KID_WEIGHT = {"]
    for s in STRATA:
        lines.append(f'    "{s}": {new_w[s]:.3f},')
    lines.append("}")
    block = "\n".join(lines)
    import re
    new_src, n = re.subn(r"_DEPCARE_KID_WEIGHT = \{.*?\n\}",
                         block + "\n", src, count=1, flags=re.DOTALL)
    assert n == 1, "kid-weight block regex did not match exactly once"
    note = ("# exp32: re-measured P_synth(kid|s) under the senior-fix sampler "
            "(100k households, seed 5); the senior fix shifts the size mix "
            "within senior strata (see experiments/exp32_medical_senior.py).\n")
    new_src = new_src.replace("_DEPCARE_KID_WEIGHT = {",
                              note + "_DEPCARE_KID_WEIGHT = {", 1)
    p.write_text(new_src)
    print("  wrote re-measured _DEPCARE_KID_WEIGHT to src/synth/errors.py")


# --------------------------------------------------------------------------
# stage 3: final validation
# --------------------------------------------------------------------------
def verdict_table(label, m, real, base_m):
    fm = m["finding"]
    l1v = l1(fm, real["finding"])
    print(f"  {label}: finding {fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f} "
          f"L1={l1v:.3f} (bar <= 0.030)  s57={m['s57']/real['s57']:.2f}x  "
          f"le56={m['le56']:.2f} (A: {base_m['le56']:.2f}) d_med={m['d_med']:.0f}")
    worst_reg = 0.0
    for b in BUCKETS:
        r = m["per_case"][b] / real["per_case"][b]
        rb = base_m["per_case"][b] / real["per_case"][b]
        reg = abs(r - 1) - abs(rb - 1)
        worst_reg = max(worst_reg, reg)
        flag = " REGRESS" if reg > 0.10 else ""
        print(f"    {b:10s} {r:5.2f}x  (A {rb:5.2f}x, d| r-1|={reg:+.2f}){flag}")
    return l1v, worst_reg


def pick_winner(res, real):
    """C if it clears all bars on both seeds; else B; else None (with the D
    diagnostic reported for the mechanism)."""
    for cand in ("C", "B"):
        ok = True
        for sd in SEEDS:
            m, a = res[sd][cand], res[sd]["A"]
            med = m["per_case"]["medical"] / real["per_case"]["medical"]
            l1v = l1(m["finding"], real["finding"])
            worst_reg = max(
                (abs(m["per_case"][b] / real["per_case"][b] - 1)
                 - abs(a["per_case"][b] / real["per_case"][b] - 1))
                for b in BUCKETS if b != "medical")
            if not (med >= 0.75 and l1v <= 0.030 and worst_reg <= 0.10):
                ok = False
        if ok:
            return cand
    return None


def stage3(real, dist, winner, res):
    print(f"\n== [3] final validation: winner={winner}, seeds {SEEDS} ==")
    d_final = (dollar_mech.enable_adopted(resliced_dist(dist))
               if winner == "C" else dollar_mech.enable_adopted(dist))
    try:
        for sd in SEEDS:
            m = mixes(gen_cases(N_CASES, sd, d_final))
            a = res[sd]["A"]
            print(f"-- seed {sd} --")
            l1v, worst_reg = verdict_table(f"winner {winner}", m, real, a)
            med = m["per_case"]["medical"] / real["per_case"]["medical"]
            held = (med >= 0.75 and l1v <= 0.030 and worst_reg <= 0.10)
            print(f"  medical={med:.2f}x (>=0.75) L1={l1v:.3f} (<=0.030) "
                  f"worst other-bucket regression={worst_reg:+.2f} (<=0.10) "
                  f"-> {'HOLDS' if held else 'DOES NOT HOLD'}")
    finally:
        dollar_mech.disable()


def main():
    dist = load_dist(str(EXP_DIR / "dist.json"))
    print("loading real FY2024 aggregates (held-out; aggregates only)...")
    real = real_aggregates(str(REAL))
    print(f"real: n={real['n']} finding "
          f"{real['finding'][1]:.3f}/{real['finding'][2]:.3f}/"
          f"{real['finding'][3]:.3f} le56={real['le56']:.2f} "
          f"d_med={real['d_med']:.0f}")

    stage0(real)
    res = stage1(real, dist)
    winner = pick_winner(res, real)
    print(f"\nwinner by verdict bars: {winner}")

    # interaction checks run under the senior-fix composition regardless
    # (keep rates / kid rates are properties of the sampler, not the mixes)
    stage2_matrix(real, dist)
    stage2_kidweight()

    if winner:
        # reload modules so the adopted matrix/kid-weights are live
        import importlib
        importlib.reload(errors)
        stage3(real, dist, winner, res)
    else:
        print("\nno arm clears the bars: validating the KEPT change (arm B, "
              "senior fix + committed mixes) under the final matrix/"
              "kid-weights.")
        import importlib
        importlib.reload(errors)
        d_final = dollar_mech.enable_adopted(dist)
        try:
            for sd in SEEDS:
                m = mixes(gen_cases(N_CASES, sd, d_final))
                a = res[sd]["A"]
                print(f"-- seed {sd} --")
                l1v, worst_reg = verdict_table("B-final", m, real, a)
                med = m["per_case"]["medical"] / real["per_case"]["medical"]
                print(f"  medical={med:.2f}x L1={l1v:.3f} "
                      f"worst other-bucket regression={worst_reg:+.2f}")
        finally:
            dollar_mech.disable()
        print("\nD-diagnostic (size-mix mechanism) for the record:")
        for sd in SEEDS:
            m, a = res[sd]["D"], res[sd]["A"]
            med = m["per_case"]["medical"] / real["per_case"]["medical"]
            print(f"  seed {sd} D: medical={med:.2f}x "
                  f"L1={l1(m['finding'], real['finding']):.3f}")


if __name__ == "__main__":
    main()
