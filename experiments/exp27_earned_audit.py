"""Experiment 27: audit why the earned-income element bucket is stuck at
~0.8x of the real per-case rate despite every draw-side fix (exp21:
"likely keep-rate or nature-mix, not draw-side"; exp24: still 0.80x on
current defaults).

North-star gate: calibration.

Hypothesis: a single dominant constraint explains >= half of the 0.20x
gap. Candidates, each measured:
  1. Keep-rate side: earned P(materialize|drawn) per stratum under current
     defaults (the MATERIALIZATION_MATRIX is now the default correction --
     is the damped/capped weight under-correcting?).
  2. Nature-mix side: recorded nature mix within earned vs real (is a
     specific nature -- e.g. 35 unreported vs 38 miscalculated -- missing?).
  3. Sampler side: stratum shares synth vs real (earned variances
     concentrate on earner strata; too few earner households -> too
     little earned mass). Also P(error|stratum): the phase-1 coin is per
     earner *status*, blind to senior within status.
  4. Materialization mechanics: forced-earned trace -- what absorbs
     drawn-but-unmaterialized earned variances (benefit floor rounding,
     net-income floor at 0, small-earner deltas)?

Method (all in-process; only this script and its chronicle are written,
no repo files touched, nothing committed; generator defaults = post-exp24):
  [A] replicate baseline: 20k cases, seed 7 -> per-case earned ratio,
      finding L1.
  [B] real aggregates (held-out QC FY2024, aggregates only): per-stratum
      shares, P(error|stratum), earned variances per error case, all
      variances per error case, nature mix within earned.
  [C] same quantities on the synth run + instrumented drawn counts per
      (bucket, stratum) and drawn natures for earned.
  [D] Kitagawa-style attribution of the overall per-case gap into
      stratum-share / error-rate / earned-per-error-case components, then
      earned-per-error-case into drawn-share x keep.
  [E] forced-earned trace (30k households, seed 99): force bucket=earned,
      single draw+apply, tabulate P(materialize|nature), P(materialize|
      base-earned bin), and failure anatomy.
  [F] ONE targeted fix probe only if a single constraint dominates
      (>= half the 0.20x gap): re-run 20k seed 7 paired; success = earned
      >= 0.90x with finding L1 <= 0.030.
Real QC microdata is read for aggregate comparison only; no per-row data
is written anywhere.

Usage: python3 experiments/exp27_earned_audit.py [--n 20000] [--t 30000]
"""
import argparse
import copy
import csv
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import benefit as benefit_mod  # noqa: E402
from synth import errors, household  # noqa: E402
from synth import params as params_mod  # noqa: E402
from synth.codebook import element_bucket  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

QC_ERROR_THRESHOLD = params_mod.QC_ERROR_THRESHOLD

QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"
EL_COLS = [f"ELEMENT{i}" for i in range(1, 10)]
NTR_COLS = [f"NATURE{i}" for i in range(1, 10)]
STRATA = ["no_earner_nonsenior", "earner_nonsenior",
          "no_earner_senior", "earner_senior"]
BUCKETS = ["earned", "unearned", "shelter", "sua", "medical", "depcare",
           "hhcomp", "arithmetic"]


def stratum_of_facts(facts):
    earner = "earner" if facts.get("earned", 0) > 0 else "no_earner"
    senior = "senior" if facts.get("senior_disabled") else "nonsenior"
    return f"{earner}_{senior}"


# ---------------------------------------------------------------- real

def real_aggregates():
    """Aggregate-only read of the held-out QC file."""
    n = 0
    s_n = Counter()          # cases per stratum
    s_err = Counter()        # error cases (STATUS 2/3) per stratum
    s_earned = Counter()     # earned variances per stratum
    s_var = Counter()        # all variances per stratum
    s_bkt = {s: Counter() for s in STRATA}  # variances per bucket/stratum
    s_nat = {s: Counter() for s in STRATA}  # nature mix within earned
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            earner = float(row["FSEARN"] or 0) > 0
            senior = (float(row["FSNELDER"] or 0) > 0 or
                      any(float(row[f"SSI{i}"] or 0) > 0 for i in range(1, 19)))
            s = ("earner" if earner else "no_earner") + "_" + \
                ("senior" if senior else "nonsenior")
            s_n[s] += 1
            if int(row["STATUS"]) in (2, 3):
                s_err[s] += 1
            for ec, nc in zip(EL_COLS, NTR_COLS):
                e = (row[ec] or "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                s_var[s] += 1
                s_bkt[s][b] += 1
                if b == "earned":
                    s_earned[s] += 1
                    nc_raw = (row[nc] or "").strip()
                    s_nat[s][int(nc_raw) if nc_raw.isdigit() else nc_raw] += 1
    return {
        "n": n,
        "share": {s: s_n[s] / n for s in STRATA},
        "err_rate": {s: s_err[s] / s_n[s] for s in STRATA},
        "earned_per_case": {s: s_earned[s] / s_n[s] for s in STRATA},
        "earned_per_errcase": {s: s_earned[s] / s_err[s] for s in STRATA},
        "var_per_errcase": {s: s_var[s] / s_err[s] for s in STRATA},
        "nature": {s: dict(s_nat[s]) for s in STRATA},
        "bucket_per_case": {s: {b: s_bkt[s][b] / s_n[s] for b in BUCKETS}
                            for s in STRATA},
        "earned_total": sum(s_earned.values()),
        "var_total": sum(s_var.values()),
    }


# ------------------------------------------------- synth (instrumented)

_ORIG_IP = errors._inject_persistent
_ORIG_DN = errors._draw_nature
_DRAWN = Counter()      # (bucket, stratum) -> drawn
_RECORDED = Counter()   # (bucket, stratum) -> recorded
_EARNED_NATURE_DRAWN = Counter()  # (stratum, nature) -> drawn earned natures


# ------------------------------------------------- fix probe: p(2nd)
# Probe for [F]: raise the second-variance probability. n_var is the FIRST
# rng draw inside _inject_persistent, so a proxy that overrides only the
# first random() call per _inject_persistent invocation retargets p(2nd)
# without touching the generator or the rest of the rng stream.
_P2 = None  # None = no override; float = P(2 variances) for the probe


class _P2Proxy:
    def __init__(self, rng):
        self._rng = rng
        self._armed = True

    def random(self):
        v = self._rng.random()
        if self._armed:
            self._armed = False
            # force the n_var coin (< 0.15 in the generator) to land
            # "2 variances" with probability _P2
            return 0.0 if v < _P2 else 1.0
        return v

    def __getattr__(self, name):
        return getattr(self._rng, name)


def _measuring_ip(facts, rng, dist, applicable, dir_w, max_attempts,
                  stats=None, **kw):
    s = stratum_of_facts(facts)
    if _P2 is not None:
        rng = _P2Proxy(rng)  # armed: overrides the n_var draw only
    local = {"drawn": Counter(), "recorded": Counter()}
    out = _ORIG_IP(facts, rng, dist, applicable, dir_w, max_attempts,
                   stats=local, **kw)
    for b, c in local["drawn"].items():
        _DRAWN[(b, s)] += c
    for b, c in local["recorded"].items():
        _RECORDED[(b, s)] += c
    return out


def _measuring_dn(facts, bucket, dist, dir_w, rng):
    nature, cause = _ORIG_DN(facts, bucket, dist, dir_w, rng)
    if bucket == "earned":
        _EARNED_NATURE_DRAWN[(stratum_of_facts(facts), nature)] += 1
    return nature, cause


def gen_cases(n, seed, dist):
    """Replicates generate.py's loop (persistent mode, max_attempts=12),
    current generator defaults, with draw/record instrumentation."""
    _DRAWN.clear()
    _RECORDED.clear()
    _EARNED_NATURE_DRAWN.clear()
    errors._inject_persistent = _measuring_ip
    errors._draw_nature = _measuring_dn
    rng = random.Random(seed)
    out = []
    try:
        for _ in range(n):
            facts = household.sample_household(rng)
            # Stratum at sampling time: the injector may correct the truth
            # upward (zero-base omissions), which would migrate the case's
            # stratum if recomputed from final facts. Pin it here.
            s0 = stratum_of_facts(facts)
            case = errors.inject(facts, rng, dist, max_attempts=12,
                                 persistent_buckets=True)
            case["_s0"] = s0
            out.append(case)
    finally:
        errors._inject_persistent = _ORIG_IP
        errors._draw_nature = _ORIG_DN
    return out


def synth_aggregates(cases):
    n = len(cases)
    s_n = Counter()
    s_err = Counter()
    s_earned = Counter()
    s_var = Counter()
    s_bkt = {s: Counter() for s in STRATA}
    s_nat = {s: Counter() for s in STRATA}
    for c in cases:
        s = c["_s0"]
        s_n[s] += 1
        if c["variances"]:
            s_err[s] += 1
        for v in c["variances"]:
            s_var[s] += 1
            s_bkt[s][v["element_bucket"]] += 1
            if v["element_bucket"] == "earned":
                s_earned[s] += 1
                s_nat[s][int(v["nature"])] += 1
    syn = {
        "n": n,
        "share": {s: s_n[s] / n for s in STRATA},
        "err_rate": {s: s_err[s] / s_n[s] if s_n[s] else 0 for s in STRATA},
        "earned_per_case": {s: s_earned[s] / s_n[s] if s_n[s] else 0
                            for s in STRATA},
        "earned_per_errcase": {s: s_earned[s] / s_err[s] if s_err[s] else 0
                               for s in STRATA},
        "var_per_errcase": {s: s_var[s] / s_err[s] if s_err[s] else 0
                            for s in STRATA},
        "nature": {s: dict(s_nat[s]) for s in STRATA},
    }
    syn["bucket_per_case"] = {
        s: {b: s_bkt[s][b] / s_n[s] if s_n[s] else 0 for b in BUCKETS}
        for s in STRATA}
    return syn


def finding_l1(cases, real_fm):
    f = Counter(c["finding"] for c in cases)
    n = len(cases)
    fm = {k: f[k] / n for k in (1, 2, 3)}
    return sum(abs(fm[k] - real_fm[k]) for k in (1, 2, 3)), fm


# ------------------------------------------------------- forced trace

def trace_earned(t, seed, dist):
    """Force bucket=earned on sampled households: single draw + apply,
    measuring what materializes and what absorbs the rest."""
    eff = dist.get("effectiveness") or {}
    dir_w = eff.get("dir_weight", {})
    rng = random.Random(seed)
    rows = []
    for _ in range(t):
        facts = household.sample_household(rng)
        s = stratum_of_facts(facts)
        base = facts["earned"]
        nature_drawn, _cause = errors._draw_nature(facts, "earned", dist,
                                                  dir_w, rng)
        agency = copy.deepcopy(facts)
        truth_corr, nature_override = errors._apply_one(
            agency, facts, "earned", nature_drawn, rng, dist)
        trial_truth = {**facts, **truth_corr} if truth_corr else facts
        nature_rec = (nature_override if nature_override is not None
                      else nature_drawn)
        c_b = benefit_mod.compute(facts)["benefit"]
        t_issued = max(0, int(round(benefit_mod.compute(agency)["benefit"])))
        t_correct = benefit_mod.compute(trial_truth)["benefit"]
        mat = (t_issued != c_b or t_correct != c_b) and t_issued != t_correct
        d_agency = agency["earned"] - facts["earned"]
        d_truth = trial_truth["earned"] - facts["earned"]
        rows.append({
            "stratum": s, "nature_drawn": nature_drawn,
            "nature_rec": nature_rec if mat else None,
            "base": base, "d_agency": d_agency, "d_truth": d_truth,
            "d_benefit": (t_issued - c_b) if mat else 0.0,
            "raw_d_benefit": (benefit_mod.compute(agency)["benefit"] +
                              0 - c_b),
            "mat": mat, "c_benefit": c_b,
        })
    return rows


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--t", type=int, default=30000,
                    help="households for the forced-earned trace")
    args = ap.parse_args()

    dist = load_dist(ROOT / "experiments/dist.json")

    print("== [B] real aggregates (FY2024 QC, held-out, aggregates only) ==",
          flush=True)
    real = real_aggregates()
    print(f"  n={real['n']}  earned variances={real['earned_total']}  "
          f"all variances={real['var_total']}")
    print(f"  {'stratum':<20}{'share':>7}{'P(err|s)':>9}"
          f"{'earned/case':>12}{'earned/err':>11}{'var/err':>8}")
    for s in STRATA:
        print(f"  {s:<20}{real['share'][s]:>7.3f}"
              f"{real['err_rate'][s]:>9.3f}{real['earned_per_case'][s]:>12.4f}"
              f"{real['earned_per_errcase'][s]:>11.3f}"
              f"{real['var_per_errcase'][s]:>8.3f}")
    real_pc_earned = sum(real["earned_per_case"][s] * real["share"][s]
                         for s in STRATA)
    print(f"  overall real earned per-case rate: {real_pc_earned:.4f}")

    print(f"\n== [A] synth baseline: {args.n} cases, seed 7, current "
          f"defaults ==", flush=True)
    cases = gen_cases(args.n, 7, dist)
    syn = synth_aggregates(cases)
    real_fm = {1: 0.603, 2: 0.239, 3: 0.158}
    l1, fm = finding_l1(cases, real_fm)
    syn_pc_earned = sum(syn["earned_per_case"][s] * syn["share"][s]
                        for s in STRATA)
    print(f"  finding mix: {fm[1]:.3f}/{fm[2]:.3f}/{fm[3]:.3f}  L1={l1:.3f}")
    print(f"  synth earned per-case: {syn_pc_earned:.4f}  "
          f"ratio: {syn_pc_earned / real_pc_earned:.3f}x")

    # ---- [A2] validate the harness against exp24: the working tree has
    # an uncommitted exp29 sampler change (BASE_POSITIVITY in
    # household.py). Patching it back to the legacy flat rates should
    # reproduce exp24's AFTER numbers (finding L1 0.025, earned 0.80x).
    print("\n== [A2] legacy-sampler check (validates the harness) ==",
          flush=True)
    LEGACY_BP = {
        "unearned": {"no_earner_nonsenior": 0.50, "earner_nonsenior": 0.50,
                     "no_earner_senior": 0.85, "earner_senior": 0.85},
        "shelter": {s: 0.63 for s in STRATA},
        "sua": {s: 0.72 for s in STRATA},
    }
    old_bp = household.BASE_POSITIVITY
    household.BASE_POSITIVITY = LEGACY_BP
    try:
        cases_leg = gen_cases(args.n, 7, dist)
    finally:
        household.BASE_POSITIVITY = old_bp
    syn_leg = synth_aggregates(cases_leg)
    l1_leg, fm_leg = finding_l1(cases_leg, real_fm)
    pc_leg = sum(syn_leg["earned_per_case"][s] * syn_leg["share"][s]
                 for s in STRATA)
    print(f"  legacy sampler: finding mix "
          f"{fm_leg[1]:.3f}/{fm_leg[2]:.3f}/{fm_leg[3]:.3f}  L1={l1_leg:.3f} "
          f"(exp24 AFTER-persist: 0.608/0.247/0.146 L1=0.025)")
    print(f"  legacy sampler: earned per-case ratio "
          f"{pc_leg / real_pc_earned:.3f}x (exp24: 0.80x)")

    # ---- [D] decomposition ----
    print("\n== [D] per-stratum decomposition ==")
    print(f"  {'stratum':<20}"
          f"{'share S/R':>10}{'err S/R':>9}{'e/err S/R':>10}"
          f"{'keepS':>7}{'drawn/e S/R':>11}")
    for s in STRATA:
        d = _DRAWN[("earned", s)]
        e = _RECORDED[("earned", s)]
        keep = e / d if d else float("nan")
        # drawn earned per error case, synth vs the empirical mix-implied
        # target share (drawn share within stratum vs empirical mix)
        d_share = d / max(1, sum(_DRAWN[(b, s)] for b in BUCKETS))
        mix = dist[f"bucket_probs_given_{s}"]["earned"]
        print(f"  {s:<20}"
              f"{syn['share'][s] / real['share'][s]:>10.3f}"
              f"{syn['err_rate'][s] / real['err_rate'][s]:>9.3f}"
              f"{syn['earned_per_errcase'][s] / real['earned_per_errcase'][s]:>10.3f}"
              f"{keep:>7.3f}"
              f"{d_share / mix:>11.3f}")
    print("  (keepS = measured P(materialize|drawn) under current defaults; "
          "drawn/e S/R = drawn earned share within stratum / empirical mix)")

    # Kitagawa-style sequential attribution of the overall per-case gap
    gap = real_pc_earned - syn_pc_earned
    r_sh = sum(real["share"][s] * syn["err_rate"][s] *
               syn["earned_per_errcase"][s] for s in STRATA)
    r_er = sum(real["share"][s] * real["err_rate"][s] *
               syn["earned_per_errcase"][s] for s in STRATA)
    print("\n  sequential attribution of the "
          f"{gap:.4f} per-case gap (real - synth):")
    print(f"    stratum shares : {r_sh - syn_pc_earned:+.4f} "
          f"({(r_sh - syn_pc_earned) / gap * 100:+.1f}% of gap)")
    print(f"    P(error|s)     : {r_er - r_sh:+.4f} "
          f"({(r_er - r_sh) / gap * 100:+.1f}% of gap)")
    print(f"    earned/errcase : {real_pc_earned - r_er:+.4f} "
          f"({(real_pc_earned - r_er) / gap * 100:+.1f}% of gap)")

    # earned/errcase further into drawn-share x keep, per stratum
    print("\n  earned-per-errcase: drawn share vs empirical mix, keep vs "
          "matrix:")
    for s in STRATA:
        d = _DRAWN[("earned", s)]
        e = _RECORDED[("earned", s)]
        keep = e / d if d else float("nan")
        mat = errors.MATERIALIZATION_MATRIX["earned"][s]
        d_share = d / max(1, sum(_DRAWN[(b, s)] for b in BUCKETS))
        mix = dist[f"bucket_probs_given_{s}"]["earned"]
        print(f"    {s:<20} drawn_share/mix {d_share / mix:.3f}x  "
              f"keep {keep:.3f} (matrix {mat:.3f})")

    # ---- nature mix ----
    print("\n== [2] nature mix within earned: real vs synth recorded "
          "(overall) ==")
    real_nat_all = Counter()
    for s in STRATA:
        real_nat_all.update(real["nature"][s])
    syn_nat_all = Counter()
    for s in STRATA:
        syn_nat_all.update(syn["nature"][s])
    drawn_nat_all = Counter()
    for (s, nn), c in _EARNED_NATURE_DRAWN.items():
        drawn_nat_all[nn] += c
    r_tot = sum(real_nat_all.values())
    s_tot = sum(syn_nat_all.values())
    d_tot = sum(drawn_nat_all.values())
    from synth.codebook import NATURE_LABELS
    print(f"  {'nature':<7}{'label':<42}{'real%':>7}{'drawn%':>8}"
          f"{'rec%':>7}{'rec/real':>9}")
    for nn in sorted(set(list(real_nat_all) + list(syn_nat_all)),
                     key=lambda x: -real_nat_all.get(x, 0)):
        if not isinstance(nn, int):
            continue
        rp = real_nat_all.get(nn, 0) / r_tot
        dp = drawn_nat_all.get(nn, 0) / d_tot if d_tot else 0
        sp = syn_nat_all.get(nn, 0) / s_tot if s_tot else 0
        lab = NATURE_LABELS.get(nn, "?")[:41]
        rr = sp / rp if rp else 0
        print(f"  {nn:<7}{lab:<42}{rp:>7.3f}{dp:>8.3f}{sp:>7.3f}"
              f"{rr:>9.2f}x")

    print("\n  per-stratum recorded nature mix, synth rec% vs real% "
          "(top natures):")
    for s in STRATA:
        rt = sum(real["nature"][s].values())
        st = sum(syn["nature"][s].values())
        top = sorted(set(list(real["nature"][s]) + list(syn["nature"][s])),
                     key=lambda x: -(real["nature"][s].get(x, 0)))[:6]
        cells = "  ".join(
            f"{nn}:{syn['nature'][s].get(nn, 0) / st:.2f}"
            f"/{real['nature'][s].get(nn, 0) / rt:.2f}" for nn in top)
        print(f"    {s:<20} {cells}   (synth/real)")

    # recorded earned share per stratum vs the empirical mix (the draw
    # target): isolates whether the shortfall is in shares or in totals.
    print("\n  recorded earned share within stratum vs empirical mix:")
    for s in STRATA:
        rs = _RECORDED[("earned", s)]
        rt = sum(_RECORDED[(b, s)] for b in BUCKETS)
        mix = dist[f"bucket_probs_given_{s}"]["earned"]
        print(f"    {s:<20} recorded {rs / rt:.4f} vs mix {mix:.4f} "
              f"-> {(rs / rt) / mix:.3f}x   "
              f"(drawn {_DRAWN[('earned', s)]}, recorded {rs})")

    # ---- [D2] is it variances-per-error-case? recorded share vs mix for
    # every bucket, and synth vs real variances per error case ----
    print("\n== [D2] recorded share vs empirical mix, all buckets ==")
    print(f"  {'stratum':<20}" + "".join(f"{b:>10}" for b in BUCKETS))
    for s in STRATA:
        rt = sum(_RECORDED[(b, s)] for b in BUCKETS)
        row = f"  {s:<20}"
        for b in BUCKETS:
            mix = dist[f"bucket_probs_given_{s}"][b]
            r = (_RECORDED[(b, s)] / rt) / mix if rt and mix else 0
            row += f"{r:>10.2f}x"
        print(row)
    print("  (1.0x = recorded share lands on the empirical mix)")

    print("\n  variances per error case, synth S/R:")
    for s in STRATA:
        r = syn["var_per_errcase"][s] / real["var_per_errcase"][s]
        print(f"    {s:<20} synth {syn['var_per_errcase'][s]:.3f} vs "
              f"real {real['var_per_errcase'][s]:.3f} -> {r:.3f}x")
    print("  (synth n_var: 2 variances w.p. 0.15 -> 1.15/injection)")

    # definitional check: do real STATUS=1 (correct) cases carry variances?
    # and does earned concentrate in 2nd+ variances in real?
    print("\n== [D3] real-file structural checks (aggregates only) ==")
    n1_var = 0
    n1_cases = 0
    first_bucket = Counter()
    later_bucket = Counter()
    n_multi = 0
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            st = int(row["STATUS"])
            codes = [(row[ec] or "").strip() for ec in EL_COLS]
            codes = [c for c in codes if c]
            if st == 1:
                n1_cases += 1
                n1_var += len(codes)
            if codes:
                first_bucket[element_bucket(int(codes[0]))] += 1
                for c in codes[1:]:
                    later_bucket[element_bucket(int(c))] += 1
                if len(codes) > 1:
                    n_multi += 1
    print(f"  STATUS=1 cases: {n1_cases}, variances on them: {n1_var} "
          f"({n1_var / max(1, n1_cases):.4f}/case)")
    ft = sum(first_bucket.values())
    lt = sum(later_bucket.values())
    print(f"  cases with >=2 variances: {n_multi}")
    print(f"  {'bucket':<10}{'1st var%':>10}{'2nd+% var%':>11}")
    for b in BUCKETS:
        print(f"  {b:<10}{first_bucket[b] / ft:>10.3f}"
              f"{later_bucket[b] / lt if lt else 0:>11.3f}")

    # ---- [E] forced trace ----
    print(f"\n== [E] forced-earned trace: {args.t} households, seed 99 ==",
          flush=True)
    rows = trace_earned(args.t, 99, dist)
    print(f"  overall P(materialize|drawn, earned): "
          f"{sum(r['mat'] for r in rows) / len(rows):.3f}")
    print(f"  {'nature':<7}{'n':>7}{'P(mat)':>8}{'med|dAg|':>9}"
          f"{'med|dBn|fail':>13}{'%fail dBn<1':>11}")
    by_nat = {}
    for r in rows:
        by_nat.setdefault(r["nature_drawn"], []).append(r)
    for nn in sorted(by_nat, key=lambda x: -len(by_nat[x])):
        rs = by_nat[nn]
        fails = [x for x in rs if not x["mat"]]
        med_dag = sorted(abs(x["d_agency"]) + abs(x["d_truth"])
                         for x in rs)[len(rs) // 2]
        med_dbn_f = (sorted(abs(x["raw_d_benefit"]) for x in fails)
                     [len(fails) // 2] if fails else float("nan"))
        pct_small = (sum(1 for x in fails if abs(x["raw_d_benefit"]) < 1.0) /
                     len(fails) * 100 if fails else 0)
        print(f"  {nn:<7}{len(rs):>7}{sum(x['mat'] for x in rs) / len(rs):>8.3f}"
              f"{med_dag:>9.0f}{med_dbn_f:>13.2f}{pct_small:>11.1f}")
    print("  (med|dAg| = median |agency delta|+|truth delta| in $; "
          "med|dBn|fail = median |raw benefit delta| among failures; "
          "%fail dBn<1 = share of failures absorbed by the $1 floor)")

    # keep by base-earned bin
    print("\n  P(materialize) by base earned income bin:")
    bins = [(0, 0), (1, 200), (201, 500), (501, 1000), (1001, 2000),
            (2001, 1e9)]
    for lo, hi in bins:
        rs = [r for r in rows if lo <= r["base"] <= hi]
        if not rs:
            continue
        lab = "0" if hi == 0 else f"{lo}-{int(hi) if hi < 1e9 else 'inf'}"
        print(f"    base ${lab:<12} n={len(rs):<6} "
              f"P(mat)={sum(r['mat'] for r in rs) / len(rs):.3f}")

    # failure anatomy: where does the benefit go?
    fails = [r for r in rows if not r["mat"]]
    print(f"\n  failure anatomy (n={len(fails)} unmaterialized draws):")
    small = sum(1 for r in fails if abs(r["raw_d_benefit"]) < 1.0)
    print(f"    |raw benefit delta| < $1 (floor absorption): "
          f"{small}/{len(fails)} = {small / len(fails):.2f}")
    zbf = sum(1 for r in fails if r["c_benefit"] == 0)
    print(f"    correct benefit already $0 (floor, underissuance "
          f"absorbed): {zbf}/{len(fails)} = {zbf / len(fails):.2f}")
    nochange = sum(1 for r in fails
                   if r["d_agency"] == 0 and r["d_truth"] == 0)
    print(f"    facts unchanged by corruption: {nochange}/{len(fails)}")
    # net-income floor: corruption *reduces* income but net already 0
    print("    (net-income floor cases are inside the |dBn|<1 bucket: "
          "reducing income when net=0 moves nothing)")

    # ---- [F] fix probe: P(2nd variance) 0.15 -> 0.38 ----
    global _P2
    print("\n== [F] fix probe: P(2nd variance) 0.15 -> 0.38 "
          f"({args.n} cases, seed 7, paired) ==", flush=True)
    _P2 = 0.38
    try:
        cases_p2 = gen_cases(args.n, 7, dist)
    finally:
        _P2 = None
    syn_p2 = synth_aggregates(cases_p2)
    l1_p2, fm_p2 = finding_l1(cases_p2, real_fm)
    pc_p2 = sum(syn_p2["earned_per_case"][s] * syn_p2["share"][s]
                for s in STRATA)
    print(f"  finding mix: {fm_p2[1]:.3f}/{fm_p2[2]:.3f}/{fm_p2[3]:.3f}  "
          f"L1={l1_p2:.3f}  (rule: L1 <= 0.030)")
    print(f"  earned per-case ratio: {pc_p2 / real_pc_earned:.3f}x  "
          f"(rule: >= 0.90x)")
    print(f"  {'bucket':<10}{'base':>7}{'probe':>7}")
    for b in BUCKETS:
        r_base = (sum(syn["bucket_per_case"][s][b] * syn["share"][s]
                      for s in STRATA) /
                  sum(real["bucket_per_case"][s][b] * real["share"][s]
                      for s in STRATA))
        r_p2 = (sum(syn_p2["bucket_per_case"][s][b] * syn_p2["share"][s]
                    for s in STRATA) /
                sum(real["bucket_per_case"][s][b] * real["share"][s]
                    for s in STRATA))
        print(f"  {b:<10}{r_base:>7.2f}x{r_p2:>7.2f}x")
    print("  var/err per stratum, probe vs real:")
    for s in STRATA:
        print(f"    {s:<20} probe {syn_p2['var_per_errcase'][s]:.3f} vs "
              f"real {real['var_per_errcase'][s]:.3f}")

    # ---- [F2] same fix + phase-1 coins recalibrated ----
    # Raising P(2nd) lowers attrition -> more injections yield >=1 recorded
    # variance -> P(err|status) overshoots. Recalibrate the persistent
    # phase-1 coins so realized P(err|status) lands back on the empirical
    # targets (one coherent fix: a variance-count change entails rebalancing
    # the error rate; cf. calibrate_injection.py).
    print("\n== [F2] P(2nd)=0.38 + recalibrated phase-1 coins ==",
          flush=True)
    real_err_status = {}
    for status in ("earner", "no_earner"):
        ss = [s for s in STRATA if s.startswith(status)]
        num = sum(real["share"][s] * real["err_rate"][s] for s in ss)
        den = sum(real["share"][s] for s in ss)
        real_err_status[status] = num / den
    probe_err_status = {}
    for status in ("earner", "no_earner"):
        tot = sum(1 for c in cases_p2 if c["_s0"].startswith(status))
        err = sum(1 for c in cases_p2
                  if c["_s0"].startswith(status) and c["variances"])
        probe_err_status[status] = err / tot
    dist2 = copy.deepcopy(dist)
    for status in ("earner", "no_earner"):
        old = dist2["injection_rate"]["persistent"][status]
        new = old * real_err_status[status] / probe_err_status[status]
        dist2["injection_rate"]["persistent"][status] = new
        print(f"  coin {status}: {old:.4f} -> {new:.4f} "
              f"(probe realized {probe_err_status[status]:.3f}, "
              f"target {real_err_status[status]:.3f})")
    _P2 = 0.38
    try:
        cases_p2c = gen_cases(args.n, 7, dist2)
    finally:
        _P2 = None
    syn_p2c = synth_aggregates(cases_p2c)
    l1_p2c, fm_p2c = finding_l1(cases_p2c, real_fm)
    pc_p2c = sum(syn_p2c["earned_per_case"][s] * syn_p2c["share"][s]
                 for s in STRATA)
    print(f"  finding mix: {fm_p2c[1]:.3f}/{fm_p2c[2]:.3f}/{fm_p2c[3]:.3f}  "
          f"L1={l1_p2c:.3f}  (rule: L1 <= 0.030)")
    print(f"  earned per-case ratio: {pc_p2c / real_pc_earned:.3f}x  "
          f"(rule: >= 0.90x)")
    print(f"  {'bucket':<10}{'F2':>7}")
    for b in BUCKETS:
        r = (sum(syn_p2c["bucket_per_case"][s][b] * syn_p2c["share"][s]
                 for s in STRATA) /
             sum(real["bucket_per_case"][s][b] * real["share"][s]
                 for s in STRATA))
        print(f"  {b:<10}{r:>7.2f}x")

    # ---- [D4] position structure: is the count fix faithful? ----
    # Real 1st variances vs 2nd+ variances have different bucket mixes
    # ([D3]); the [F] probe drew 2nd variances from the marginal mix
    # (earned-rich), which flatters earned. Measure per-stratum M1/M2 for
    # earned and build the faithful counterfactual: synth 1st-variance
    # behavior + real later-variance COUNT and MIX.
    print("\n== [D4] faithful-count counterfactual (M1/M2 structure) ==")
    r_e1 = Counter()   # earned 1st-variances per stratum (real)
    r_l = Counter()    # all later variances per stratum (real)
    r_le = Counter()   # earned later variances per stratum (real)
    r_err = Counter()  # errcases per stratum (real)
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            earner = float(row["FSEARN"] or 0) > 0
            senior = (float(row["FSNELDER"] or 0) > 0 or
                      any(float(row[f"SSI{i}"] or 0) > 0 for i in range(1, 19)))
            s = ("earner" if earner else "no_earner") + "_" + \
                ("senior" if senior else "nonsenior")
            codes = [(row[ec] or "").strip() for ec in EL_COLS]
            codes = [c for c in codes if c]
            if not codes:
                continue
            r_err[s] += 1
            if element_bucket(int(codes[0])) == "earned":
                r_e1[s] += 1
            for c in codes[1:]:
                r_l[s] += 1
                if element_bucket(int(c)) == "earned":
                    r_le[s] += 1
    s_e1 = Counter()
    s_err2 = Counter()
    for c in cases:
        s = c["_s0"]
        if not c["variances"]:
            continue
        s_err2[s] += 1
        if c["variances"][0]["element_bucket"] == "earned":
            s_e1[s] += 1
    print(f"  {'stratum':<20}{'real m1e':>9}{'real m2e':>9}"
          f"{'syn m1e':>9}{'(later/err) R':>13}")
    cf_total = 0.0
    for s in STRATA:
        m1e_r = r_e1[s] / r_err[s]
        m2e_r = r_le[s] / r_l[s] if r_l[s] else 0
        later_per_err_r = r_l[s] / r_err[s]
        m1e_s = s_e1[s] / s_err2[s] if s_err2[s] else 0
        print(f"  {s:<20}{m1e_r:>9.3f}{m2e_r:>9.3f}{m1e_s:>9.3f}"
              f"{later_per_err_r:>13.3f}")
        # faithful counterfactual: synth 1st-variance earned rate +
        # real later-variance count x real later earned mix
        cf = (m1e_s + later_per_err_r * m2e_r)
        cf_total += syn["share"][s] * syn["err_rate"][s] * cf
    print(f"  faithful-count counterfactual earned per-case: {cf_total:.4f} "
          f"-> {cf_total / real_pc_earned:.3f}x (real {real_pc_earned:.4f})")
    print("  (synth 1st-variance behavior kept; only the later-variance "
          "count and mix set to real)")

    # ---- [F3] fix probe: position-dependent draw mixes (M1/M2) ----
    # The refined constraint: the generator draws EVERY variance from the
    # marginal bucket mix, but real 1st variances are earned-richer than
    # marginal (M1) and real later variances earned-poorer (M2). Probe:
    # draw the 1st variance from the per-stratum M1 mix and 2nd+ from M2
    # (both keep-corrected with the same matrix weights -- keep rates are
    # weight-invariant per exp24, so this is not double-counting; M1/M2
    # are a refinement of the draw target, measured from real).
    print("\n== [F3] fix probe: M1/M2 position-dependent draw mixes ==",
          flush=True)
    m1 = {s: Counter() for s in STRATA}
    m2 = {s: Counter() for s in STRATA}
    with open(QC, newline="") as fh:
        for row in csv.DictReader(fh):
            earner = float(row["FSEARN"] or 0) > 0
            senior = (float(row["FSNELDER"] or 0) > 0 or
                      any(float(row[f"SSI{i}"] or 0) > 0 for i in range(1, 19)))
            s = ("earner" if earner else "no_earner") + "_" + \
                ("senior" if senior else "nonsenior")
            codes = [(row[ec] or "").strip() for ec in EL_COLS]
            codes = [c for c in codes if c]
            if not codes:
                continue
            m1[s][element_bucket(int(codes[0]))] += 1
            for c in codes[1:]:
                m2[s][element_bucket(int(c))] += 1
    M1 = {}
    M2 = {}
    for s in STRATA:
        t1 = sum(m1[s].values())
        t2 = sum(m2[s].values())
        # fall back to the marginal mix where a position mix is degenerate
        marg = dist[f"bucket_probs_given_{s}"]
        M1[s] = {b: (m1[s][b] / t1 if t1 else marg[b]) for b in BUCKETS}
        M2[s] = {b: (m2[s][b] / t2 if t2 else marg[b]) for b in BUCKETS}
    print("  M1 (1st-variance) earned share per stratum vs marginal mix:")
    for s in STRATA:
        print(f"    {s:<20} M1 {M1[s]['earned']:.3f} vs marg "
              f"{dist[f'bucket_probs_given_{s}']['earned']:.3f}; "
              f"M2 earned {M2[s]['earned']:.3f}")

    _ip_orig = _ORIG_IP

    def _ip_m1m2(facts, rng, dist_a, applicable, dir_w, max_attempts,
                 stats=None, **kw):
        # Copy of errors._inject_persistent with ONE change: the bucket draw
        # mix depends on draw position (M1 for the 1st draw, M2 after),
        # keep-corrected with the same matrix weights. Everything else
        # (nature draws, corruption mechanics, recording rule) is identical.
        eff_b = (dist_a.get("effectiveness") or {}).get("bucket", {})
        stratum = errors._stratum_key(facts)
        base_w = {b: errors._matrix_weight(b, stratum, eff_b)
                  for b in BUCKETS}
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
            mix = M1[stratum] if pos == 0 else M2[stratum]
            wmix = {b: mix[b] * base_w[b] for b in BUCKETS if mix[b] > 0}
            # keep the depcare kid-gating + zero-base applicability of the
            # original: restrict to buckets applicable() allowed
            wmix = {b: w for b, w in wmix.items() if b in applicable}
            if not wmix:
                wmix = dict(applicable)
            bucket = errors._sample(rng, wmix)
            if stats is not None:
                stats["drawn"][bucket] += 1
            c_issued, c_correct = pair(agency, truth, benefit_noise)
            nature, cause = errors._draw_nature(facts, bucket, dist_a,
                                                dir_w, rng)
            trial_noise = 0.0
            if bucket == "arithmetic":
                trial_noise = rng.choice([-1, 1]) * errors._u(rng, 10, 60)
            else:
                trial_agency = copy.deepcopy(agency)
                trial_truth = truth
                truth_corr, nature_override = errors._apply_one(
                    trial_agency, trial_truth, bucket, nature, rng, dist_a)
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
            "reportable": dollar > QC_ERROR_THRESHOLD,
            "variances": variances,
        }

    # gen_cases dispatches through the module-global _ORIG_IP inside the
    # measuring wrapper: rebind it for the probe, restore after.
    _saved_orig_ip = globals()["_ORIG_IP"]
    globals()["_ORIG_IP"] = _ip_m1m2
    try:
        cases_m1m2 = gen_cases(args.n, 7, dist)
    finally:
        globals()["_ORIG_IP"] = _saved_orig_ip
    syn_m1m2 = synth_aggregates(cases_m1m2)
    l1_m1m2, fm_m1m2 = finding_l1(cases_m1m2, real_fm)
    pc_m1m2 = sum(syn_m1m2["earned_per_case"][s] * syn_m1m2["share"][s]
                  for s in STRATA)
    print(f"  finding mix: {fm_m1m2[1]:.3f}/{fm_m1m2[2]:.3f}/{fm_m1m2[3]:.3f}"
          f"  L1={l1_m1m2:.3f}  (rule: L1 <= 0.030)")
    print(f"  earned per-case ratio: {pc_m1m2 / real_pc_earned:.3f}x  "
          f"(rule: >= 0.90x)")
    print(f"  {'bucket':<10}{'F3':>7}")
    for b in BUCKETS:
        r = (sum(syn_m1m2["bucket_per_case"][s][b] * syn_m1m2["share"][s]
                 for s in STRATA) /
             sum(real["bucket_per_case"][s][b] * real["share"][s]
                 for s in STRATA))
        print(f"  {b:<10}{r:>7.2f}x")

    # ---- [F4] M1/M2 + recalibrated phase-1 coins ----
    print("\n== [F4] M1/M2 + recalibrated phase-1 coins ==", flush=True)
    probe_err_status = {}
    for status in ("earner", "no_earner"):
        tot = sum(1 for c in cases_m1m2 if c["_s0"].startswith(status))
        err = sum(1 for c in cases_m1m2
                  if c["_s0"].startswith(status) and c["variances"])
        probe_err_status[status] = err / tot
    dist3 = copy.deepcopy(dist)
    for status in ("earner", "no_earner"):
        old = dist3["injection_rate"]["persistent"][status]
        new = old * real_err_status[status] / probe_err_status[status]
        dist3["injection_rate"]["persistent"][status] = new
        print(f"  coin {status}: {old:.4f} -> {new:.4f} "
              f"(probe realized {probe_err_status[status]:.3f}, "
              f"target {real_err_status[status]:.3f})")
    _saved2 = globals()["_ORIG_IP"]
    globals()["_ORIG_IP"] = _ip_m1m2
    try:
        cases_m1m2c = gen_cases(args.n, 7, dist3)
    finally:
        globals()["_ORIG_IP"] = _saved2
    syn_m1m2c = synth_aggregates(cases_m1m2c)
    l1_m1m2c, fm_m1m2c = finding_l1(cases_m1m2c, real_fm)
    pc_m1m2c = sum(syn_m1m2c["earned_per_case"][s] * syn_m1m2c["share"][s]
                   for s in STRATA)
    print(f"  finding mix: {fm_m1m2c[1]:.3f}/{fm_m1m2c[2]:.3f}/"
          f"{fm_m1m2c[3]:.3f}  L1={l1_m1m2c:.3f}  (rule: L1 <= 0.030)")
    print(f"  earned per-case ratio: {pc_m1m2c / real_pc_earned:.3f}x  "
          f"(rule: >= 0.90x)")
    print(f"  {'bucket':<10}{'F4':>7}")
    for b in BUCKETS:
        r = (sum(syn_m1m2c["bucket_per_case"][s][b] * syn_m1m2c["share"][s]
                 for s in STRATA) /
             sum(real["bucket_per_case"][s][b] * real["share"][s]
                 for s in STRATA))
        print(f"  {b:<10}{r:>7.2f}x")

    print("\n== done ==")


if __name__ == "__main__":
    main()
