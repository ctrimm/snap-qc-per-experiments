"""SD8 — pristine transfer rerun: demanded by SD2's own fairness caveat.

SD2 notes UT1's offsets were fit on pooled FY2020-2024 UT microdata INCLUDING
the holdout rows, so the UT-synth arms aren't pristine vs the test set and
the UT-vs-national advantage could be partly inflated by the generator having
seen test-set marginals. SD8 tests the caveat:

  1. Refit UT offsets on UT microdata EXCLUDING every holdout row in
     experiments/ut2_holdout_idx.json (same pooled FY2020-2024 window), via a
     verbatim port of ut1.fit_ut_targets with one change: the exclusion.
  2. Regenerate UT-conditioned synthetic (n=20k, seed 7) per UT1's final
     (it3) recipe: pure-empirical ratios -> pilot -> one-step realized-output
     calibrations (bucket x real/synth share; 97-share x real/synth P(97|b);
     97-resolution coins x real/synth P(over|97,b); direction margins x
     real/synth on the non-97 slice; it2b-style rebased cause ratios =
     UT-non97-mix/dist-mixed-basis; UT_P_UNIT from pristine near-full|over)
     -> UT_COIN_CAL line search over {0.95, 1.00, 1.05, 1.10} against
     the pristine marginal case-error rate. Refit constants installed by
     monkey-patching ut_state module attributes (PA6's pattern; no src edits).
     The national arm is regenerated identically (n=20k, seed 7) and verified
     byte-identical to SD2's national file (/tmp/sd2out/nat_synth.jsonl).
     (UT1's it3 second 97-share push is NOT repeated: it hit a
     materialization ceiling with diminishing returns; one it2-style step.)
  3. Retrain SD2's key arms on element + finding: (a) pristine-UT synth,
     (b) national synth; evaluate both on the SAME holdout. GBM without
     class_weight (SD2's winning setting; --balanced flips it), SD7's clean
     8-feature set (the production recipe; SD7 showed the v1->clean8 delta
     is immaterial: +0.013 acc / -0.000 macroF1 on element).
  4. Report element accuracy/macroF1 and finding binary AUC for (a) vs (b);
     the pristine UT-vs-national gap vs SD2's reported gap; how much
     absolute numbers moved (the contamination premium).

Usage (from repo root):
    python3 experiments/ut8_ut_pristine_rerun.py [--balanced]
Results -> /tmp/ut8out/ut8_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at snap-qc-data/ next to the
repo checkout.
"""
import argparse
import copy
import csv
import hashlib
import json
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from src.synth import ut_state  # noqa: E402
import ut1_ut_generator as ut1  # noqa: E402
import ut2_ut_transfer as ut2  # noqa: E402
from src.synth.codebook import cause_bucket, element_bucket  # noqa: E402

QC_DIR = str(ROOT.parent / "snap-qc-data" / "raw")
HOLDOUT_JSON = str(ROOT / "experiments" / "ut2_holdout_idx.json")
DIST = str(ROOT / "experiments" / "dist.json")
OUT = Path("/tmp/ut8out")
OUT.mkdir(exist_ok=True)
N_SYNTH = 20000
SEED = 7
# UT8 pristine refit basis: FY2022-2024, matching UT1's fit basis (NY6
# lesson — partial-year FY2020-21 excluded). The holdout spans all five
# FYs; rows whose key appears in the holdout are excluded from the fit.
FYS = [2022, 2023, 2024]
SUPPORTED = ut1.SUPPORTED
UT_STATE = ut1.UT_STATE
# Sparsity-guard buckets keep the national value through calibration, per UT1.
GUARD_BUCKETS = {"depcare", "hhcomp", "arithmetic"}
# Behavioral direction classes (match ut_state.UT_OVER/UNDER_NATURES)
OVER = {35, 37, 38, 39, 53, 56, 7}
UNDER = {44, 52, 57, 6, 13}

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

# Clean v1: SD7's 8-feature set (issued_benefit dropped as leakage).
CLEAN8 = ["hh_size", "earned", "unearned", "shelter", "sua",
          "medical_exp", "depcare", "senior_disabled"]


def as_Xy8(rows, y_idx):
    # sd2's feature dicts are a superset of CLEAN8
    return [[r[0][k] for k in CLEAN8] for r in rows], [r[y_idx] for r in rows]


def fit_ut_targets_excl(qc_dir=QC_DIR, fys=FYS, exclude=frozenset()):
    """Verbatim port of ut1.fit_ut_targets, with holdout exclusion.

    exclude: set of (fy, 0-based index among UT rows in that FY's CSV) — the
    SD2 holdout keys. UT indexing matches ut2.load_ut_real (STATE stripped,
    UT rows counted in CSV order per FY, including excluded ones so indices
    line up). Verified 2026-10-03 that no UT rows carry STATE whitespace, so
    strip-vs-no-strip counts identically. Every other line of UT1's recipe is
    unchanged: FYWGT-weighted, microdata-implied rates, same guards.
    """
    finding = {"ut": Counter(), "nat": Counter()}
    err_cond = {"ut": defaultdict(float), "nat": defaultdict(float)}
    amterr = {"ut": [], "nat": []}
    w_amterr = {"ut": 0.0, "nat": 0.0}
    w_fsben = {"ut": 0.0, "nat": 0.0}
    near_full = {"ut": [0.0, 0.0], "nat": [0.0, 0.0]}
    bucket = {"ut": Counter(), "nat": Counter()}
    bucket_n = {"ut": Counter(), "nat": Counter()}
    nature = {"ut": Counter(), "nat": Counter()}
    nature_n = {"ut": Counter(), "nat": Counter()}
    p97 = {"ut": defaultdict(lambda: [0.0, 0.0]),
           "nat": defaultdict(lambda: [0.0, 0.0])}
    p97_n = {"ut": Counter(), "nat": Counter()}
    cause = {"ut": Counter(), "nat": Counter()}
    cause97 = {"ut": Counter(), "nat": Counter()}
    cause97_n = {"ut": Counter(), "nat": Counter()}
    causenon97 = {"ut": Counter(), "nat": Counter()}
    cause97blank = {"ut": [0.0, 0.0], "nat": [0.0, 0.0]}
    n_ut = 0

    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        ut_idx = 0  # UT-relative row index within this FY's CSV
        with open(path, newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                is_ut = row["STATE"].strip() == UT_STATE
                if is_ut:
                    key = (fy, ut_idx)
                    ut_idx += 1
                    if key in exclude:  # <- SD8's only change
                        continue
                g = "ut" if is_ut else "nat"
                w = ut1.fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                n_ut += is_ut
                status = row["STATUS"].strip()
                finding[g][status] += w
                ek = "earner" if ut1.fnum(row.get("FSEARN")) > 0 else "no_earner"
                if status in ("2", "3"):
                    err_cond[g][(ek, "err")] += w
                err_cond[g][(ek, "tot")] += w
                am = ut1.fnum(row.get("AMTERR"))
                w_amterr[g] += w * am
                w_fsben[g] += w * ut1.fnum(row.get("FSBEN"))
                if status in ("2", "3"):
                    amterr[g].append((w, abs(am), status))
                    if status == "2":
                        raw = ut1.fnum(row.get("RAWBEN"))
                        near_full[g][1] += w
                        if raw > 0 and abs(am) / raw >= 0.9:
                            near_full[g][0] += w
                    for i in range(1, 10):
                        e = (row.get(f"ELEMENT{i}") or "").strip()
                        if not e or e == "0":
                            continue
                        try:
                            ei = int(float(e))
                        except ValueError:
                            continue
                        b = element_bucket(ei)
                        if b not in SUPPORTED:
                            continue
                        n = (row.get(f"NATURE{i}") or "").strip()
                        c = (row.get(f"AGENCY{i}") or "").strip()
                        ni = int(float(n)) if n and n != "0" else None
                        ci = int(float(c)) if c and c != "0" else None
                        bucket[g][b] += w
                        bucket_n[g][b] += 1
                        if ni is not None:
                            nature[g][(b, ni)] += w
                            nature_n[g][(b, ni)] += 1
                            if ni == 97:
                                p97[g][b][1] += w
                                p97_n[g][b] += 1
                                if status == "2":
                                    p97[g][b][0] += w
                                cause97blank[g][1] += w
                                if ci is None:
                                    cause97blank[g][0] += w
                                else:
                                    cause97[g][(b, ci)] += w
                                    cause97_n[g][(b, ci)] += 1
                            elif ci is not None:
                                causenon97[g][(b, cause_bucket(ci))] += w
                        if ci is not None:
                            cause[g][(b, cause_bucket(ci))] += w

    def wq(pairs, q):
        tot = sum(w for w, _ in pairs)
        tgt, acc = tot * q, 0.0
        for w, v in sorted(pairs, key=lambda t: t[1]):
            acc += w
            if acc >= tgt:
                return v
        return pairs[-1][1]

    t = {"n_ut_rows": n_ut, "ut": {}, "nat": {}}
    for g in ("ut", "nat"):
        tot = sum(finding[g].values())
        fm = {s: finding[g][s] / tot for s in ("1", "2", "3")}
        P = amterr[g]
        tw = sum(w for w, _, _ in P)
        qs = {q: wq([(w, v) for w, v, _ in P], q)
              for q in (0.10, 0.25, 0.50, 0.90)}
        over = [(w, v) for w, v, s in P if s == "2"]
        under = [(w, v) for w, v, s in P if s == "3"]
        t[g] = {
            "finding_mix": fm,
            "case_err_rate": (finding[g]["2"] + finding[g]["3"]) / tot,
            "dollar_rate": w_amterr[g] / w_fsben[g],
            "p_err_earner": err_cond[g][("earner", "err")] / err_cond[g][("earner", "tot")],
            "p_err_no_earner": err_cond[g][("no_earner", "err")] / err_cond[g][("no_earner", "tot")],
            "p_over_given_err": finding[g]["2"] / (finding[g]["2"] + finding[g]["3"]),
            "near_full_given_over": near_full[g][0] / near_full[g][1],
            "dollar_q": qs,
            "dollar_mean": sum(w * v for w, v, _ in P) / tw,
            "share_le56": sum(w for w, v, _ in P if v <= 56) / tw,
            "medO": wq(over, 0.50),
            "medU": wq(under, 0.50),
            "cause97_blank": cause97blank[g][0] / cause97blank[g][1],
        }
    ut, nat = t["ut"], t["nat"]
    t["ratios"] = {
        "coin": {s: ut[f"p_err_{s}"] / nat[f"p_err_{s}"]
                for s in ("earner", "no_earner")},
        "bucket": {},
        "nature97share": {},
        "naturedir": {},
        "cause_non97": {},
        "cause97": {},
        "p97": {},
        "s_over": ut["medO"] / nat["medO"],
        "s_under": ut["medU"] / nat["medU"],
    }
    tb_ut = sum(bucket["ut"].values())
    tb_nat = sum(bucket["nat"].values())
    for b in SUPPORTED:
        r = (bucket["ut"][b] / tb_ut) / (bucket["nat"][b] / tb_nat)
        t["ratios"]["bucket"][b] = r if bucket_n["ut"][b] >= 25 else 1.0
    for b in SUPPORTED:
        tot_ut = sum(v for (bb, _), v in nature["ut"].items() if bb == b)
        tot_nat = sum(v for (bb, _), v in nature["nat"].items() if bb == b)
        if p97_n["ut"][b] >= 5 and tot_ut > 0 and tot_nat > 0:
            r = (nature["ut"][(b, 97)] / tot_ut) / (nature["nat"][(b, 97)] / tot_nat)
            t["ratios"]["nature97share"][b] = r
        else:
            t["ratios"]["nature97share"][b] = 1.0
        nn97_ut = sum(v for (bb, n_), v in nature["ut"].items()
                      if bb == b and n_ != 97)
        nn97_nat = sum(v for (bb, n_), v in nature["nat"].items()
                       if bb == b and n_ != 97)
        dr = {}
        for k, nset in (("over", OVER), ("under", UNDER)):
            pk = sum(v for (bb, n_), v in nature["ut"].items()
                     if bb == b and n_ in nset) / nn97_ut if nn97_ut else 0
            qk = sum(v for (bb, n_), v in nature["nat"].items()
                     if bb == b and n_ in nset) / nn97_nat if nn97_nat else 0
            dr[k] = pk / qk if qk > 0 else 1.0
        nn97_n_ut = bucket_n["ut"][b] - p97_n["ut"][b]
        t["ratios"]["naturedir"][b] = dr if nn97_n_ut >= 25 else \
            {"over": 1.0, "under": 1.0}
    for b in SUPPORTED:
        tc_ut = sum(v for (bb, _), v in causenon97["ut"].items() if bb == b)
        tc_nat = sum(v for (bb, _), v in causenon97["nat"].items() if bb == b)
        for co in ("client", "agency", "no_fault", "other"):
            if bucket_n["ut"][b] < 25 or tc_ut == 0 or tc_nat == 0:
                r = 1.0
            else:
                p = causenon97["ut"][(b, co)] / tc_ut
                q = causenon97["nat"][(b, co)] / tc_nat
                r = p / q if q > 0 else 1.0
            t["ratios"]["cause_non97"][(b, co)] = r
    pool = Counter()
    for (b, c), w in cause97["ut"].items():
        pool[c] += w
    ptot = sum(pool.values())
    for b in SUPPORTED:
        nu = sum(v for (bb, _), v in cause97_n["ut"].items() if bb == b)
        tot = sum(v for (bb, _), v in cause97["ut"].items() if bb == b)
        if nu >= 5 and tot > 0:
            t["ratios"]["cause97"][b] = {
                c: v / tot for (bb, c), v in cause97["ut"].items() if bb == b}
        else:
            t["ratios"]["cause97"][b] = {c: v / ptot for c, v in pool.items()}
    for b in SUPPORTED:
        o_ut, tot_ut = p97["ut"][b]
        o_nat, tot_nat = p97["nat"][b]
        if p97_n["ut"][b] >= 5 and tot_nat > 0 and o_nat > 0:
            t["ratios"]["p97"][b] = (o_ut / tot_ut) / (o_nat / tot_nat)
        else:
            t["ratios"]["p97"][b] = 1.0
    t["ut_cause97_blank"] = ut["cause97_blank"]
    return t


def fit_to_constants(t):
    """Convert pristine fit output into ut_state constant overrides."""
    R = t["ratios"]
    return {
        "UT_COIN_RATIO": {s: R["coin"][s] for s in ("earner", "no_earner")},
        "UT_BUCKET_RATIO": {b: R["bucket"][b] for b in SUPPORTED},
        "UT_97_RATIO": {b: R["p97"][b] for b in SUPPORTED},
        "UT_97_SHARE_RATIO": {b: R["nature97share"][b] for b in SUPPORTED},
        "UT_DIR_RATIO": {b: {"over": R["naturedir"][b]["over"],
                              "under": R["naturedir"][b]["under"]}
                         for b in SUPPORTED},
        "UT_CAUSE_RATIO": {
            b: {co: R["cause_non97"][(b, co)]
                for co in ("client", "agency", "no_fault", "other")}
            for b in SUPPORTED},
        "UT_97_CAUSE": {b: {str(c): v for c, v in mix.items()}
                        for b, mix in R["cause97"].items()},
        "UT_S_OVER": R["s_over"],
        "UT_S_UNDER": R["s_under"],
        "UT_CAUSE97_BLANK": t["ut_cause97_blank"],
    }


def install_constants(const, coin_cal=1.0):
    """Monkey-patch ut_state module constants (read at call time). No src edits."""
    for name, val in const.items():
        setattr(ut_state, name, copy.deepcopy(val))
    ut_state.UT_COIN_CAL = coin_cal


def gen_ut(out, n=N_SYNTH, seed=SEED):
    ut_state.generate_ut(n=n, seed=seed, dist=DIST, out=str(out))
    return str(out)




def real_ut_var_targets_excl(qc_dir, fys, exclude):
    """Pristine real-UT variance-level targets for UT1's it2 calibration.

    FYWGT-weighted, variance-level, SUPPORTED buckets only, holdout rows
    excluded: bucket shares; per-bucket P(97) nature share (the basis the
    97-share calibration multiplies); per-bucket P(over|97) (status basis,
    same as UT1's fit p97); per-bucket non-97 nature-direction shares
    (nature-code basis with UT1's behavioral OVER/UNDER classes).
    """
    bucket = Counter()
    share97 = defaultdict(lambda: [0.0, 0.0])  # b -> [97 w, tot w]
    p97 = defaultdict(lambda: [0.0, 0.0])      # b -> [over w, tot w]
    dr = defaultdict(lambda: [0.0, 0.0, 0.0])  # b -> [over w, under w, non97 w]
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        ut_idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != UT_STATE:
                    continue
                key = (fy, ut_idx)
                ut_idx += 1
                if key in exclude or row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = ut1.fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                status = row["STATUS"].strip()
                for i in range(1, 10):
                    e = (row.get(f"ELEMENT{i}") or "").strip()
                    if not e or e == "0":
                        continue
                    try:
                        b = element_bucket(int(float(e)))
                    except ValueError:
                        continue
                    if b not in SUPPORTED:
                        continue
                    n = (row.get(f"NATURE{i}") or "").strip()
                    ni = int(float(n)) if n and n != "0" else None
                    bucket[b] += w
                    share97[b][1] += w
                    if ni == 97:
                        share97[b][0] += w
                        p97[b][1] += w
                        if status == "2":
                            p97[b][0] += w
                    elif ni is not None:
                        dr[b][2] += w
                        if ni in OVER:
                            dr[b][0] += w
                        elif ni in UNDER:
                            dr[b][1] += w
    tb = sum(bucket.values())
    return {
        "bucket": {b: bucket[b] / tb for b in bucket},
        "p97_share": {b: share97[b][0] / share97[b][1] for b in share97
                      if share97[b][1] > 0},
        "p_over_97": {b: p97[b][0] / p97[b][1] for b in p97 if p97[b][1] > 0},
        "p_over_non97": {b: dr[b][0] / dr[b][2] for b in dr if dr[b][2] > 0},
        "p_under_non97": {b: dr[b][1] / dr[b][2] for b in dr if dr[b][2] > 0},
    }


def synth_var_targets(path):
    """Realized variance-level targets from a synth file, on the same basis
    as real_ut_var_targets_excl. 97 direction from the case finding (the
    resolution coin sets the realized direction while the recorded nature
    stays 97); non-97 direction from the recorded nature code (behavioral
    classes — the basis the direction margins act on). The 97-share basis
    counts recorded nature-97 (what the 97-share margins act on)."""
    bucket = Counter()
    share97 = Counter()
    p97 = defaultdict(lambda: [0, 0])
    dr = defaultdict(lambda: [0, 0, 0])
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            f = int(c["finding"])
            for v in c["variances"]:
                b = v["element_bucket"]
                if b not in SUPPORTED:
                    continue
                n = v["nature"]
                bucket[b] += 1
                if n == 97:
                    share97[b] += 1
                    p97[b][1] += 1
                    if f == 2:
                        p97[b][0] += 1
                else:
                    dr[b][2] += 1
                    if n in OVER:
                        dr[b][0] += 1
                    elif n in UNDER:
                        dr[b][1] += 1
    tb = sum(bucket.values())
    return {
        "bucket": {b: bucket[b] / tb for b in bucket},
        "p97_share": {b: share97[b] / bucket[b] for b in bucket},
        "p_over_97": {b: p97[b][0] / p97[b][1] for b in p97 if p97[b][1] > 0},
        "p_over_non97": {b: dr[b][0] / dr[b][2] for b in dr if dr[b][2] > 0},
        "p_under_non97": {b: dr[b][1] / dr[b][2] for b in dr if dr[b][2] > 0},
    }


def rebased_cause_ratios_excl(qc_dir, fys, exclude):
    """it2b-style rebased cause ratios on UT microdata MINUS holdout rows:
    UT non-97 empirical cause mix (coarse, FYWGT) / dist mixed cause basis.
    Sparsity guard: buckets with UT unweighted non-97 n < 25 keep 1.0."""
    from src.synth.codebook import cause_bucket
    mix = Counter(); tot = Counter(); nunw = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        ut_idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != UT_STATE:
                    continue
                key = (fy, ut_idx)
                ut_idx += 1
                if key in exclude:
                    continue
                if row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = ut1.fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                for i in range(1, 10):
                    e = (row.get(f"ELEMENT{i}") or "").strip()
                    if not e or e == "0":
                        continue
                    try:
                        b = element_bucket(int(float(e)))
                    except ValueError:
                        continue
                    if b not in SUPPORTED:
                        continue
                    n = (row.get(f"NATURE{i}") or "").strip()
                    ni = int(float(n)) if n and n != "0" else None
                    c = (row.get(f"AGENCY{i}") or "").strip()
                    if ni is not None and ni != 97 and c and c != "0":
                        mix[(b, cause_bucket(int(float(c))))] += w
                        tot[b] += w
                        nunw[b] += 1
    d = json.load(open(DIST))
    basis = {}
    for b in SUPPORTED:
        m = d["cause_given_bucket"].get(b, {})
        coarse = Counter()
        for code, pr in m.items():
            coarse[cause_bucket(int(code))] += pr
        tb = sum(coarse.values())
        basis[b] = {k: v / tb for k, v in coarse.items()}
    out = {}
    for b in SUPPORTED:
        if nunw[b] < 25 or tot[b] <= 0:
            out[b] = {co: 1.0 for co in ("client", "agency", "no_fault", "other")}
            continue
        cells = {}
        for co in ("client", "agency", "no_fault", "other"):
            num = mix[(b, co)] / tot[b]
            den = basis[b].get(co, 0)
            cells[co] = round(num / den, 4) if den > 0 else (0.0 if num == 0 else 1.0)
        out[b] = cells
    return out


def finding_l1(path, target_mix):
    """Finding L1 of a synth file vs a target {"1":, "2":, "3":} mix."""
    find = Counter()
    n = 0
    with open(path) as fh:
        for line in fh:
            find[int(json.loads(line)["finding"])] += 1
            n += 1
    sm = {k: find[k] / n for k in (1, 2, 3)}
    tm = {1: target_mix["1"], 2: target_mix["2"], 3: target_mix["3"]}
    return sum(abs(sm[k] - tm[k]) for k in (1, 2, 3)), sm


def gen_national(out):
    """Regenerate the national arm exactly per SD2's recipe."""
    subprocess.run(
        [sys.executable, "-m", "synth.generate", "--n", str(N_SYNTH),
         "--seed", str(SEED), "--dist", "../experiments/dist.json",
         "--max-attempts", "12", "--out", str(out)],
        check=True, cwd=str(ROOT / "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--balanced", action="store_true",
                    help="use class_weight='balanced' in the battery (only if "
                         "SD2's seed-7 battery says balanced wins for UT)")
    args = ap.parse_args()
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    # --- Stage 0: holdout exclusion set -------------------------------------
    saved = json.loads(Path(HOLDOUT_JSON).read_text())
    exclude = {(k[0], k[1]) for k in saved["holdout_keys"]}
    log(f"stage 0: holdout keys loaded: {len(exclude)} "
        f"(split_seed={saved['split_seed']}, n_ut_rows={saved['n_ut_rows']})")

    # --- Stage 1: pristine refit --------------------------------------------
    log("stage 1: refitting UT targets on UT microdata MINUS holdout rows...")
    t = fit_ut_targets_excl(QC_DIR, fys=FYS, exclude=exclude)
    # UT8's fit basis is FY2022-2024 (UT1's convention): expected kept rows
    # = FY2022-24 UT rows minus the holdout keys that fall in FY2022-24.
    excl_in_basis = {k for k in exclude if k[0] in FYS}
    import csv as _csv
    n_basis = 0
    for fy in FYS:
        with open(f"{QC_DIR}/qcfy{fy}_csv/qc_pub_fy{fy}.csv", newline="") as fh:
            for row in _csv.DictReader(fh):
                if row["STATE"] == "49":
                    n_basis += 1
    log(f"  kept UT rows: {t['n_ut_rows']} (FY2022-24 basis n={n_basis}, "
        f"excluded in-basis holdout rows={len(excl_in_basis)})")
    assert t["n_ut_rows"] == n_basis - len(excl_in_basis), \
        "pristine fit row count mismatch"
    p = t["ut"]
    m = p["finding_mix"]
    log(f"  UT minus-holdout: finding c/o/u "
        f"{m['1']:.4f}/{m['2']:.4f}/{m['3']:.4f} case_err {p['case_err_rate']:.4f} "
        f"p(over|err) {p['p_over_given_err']:.4f}")
    log("  (UT1 FY2022-24 basis: 0.6677/0.1920/0.1403 case_err 0.3323 p(over|err) 0.5778)")
    log("  pure-empirical bucket ratios:",
        {b: round(t["ratios"]["bucket"][b], 4) for b in SUPPORTED})
    log("  (UT1 FY2022-24 pure-empirical: earned 1.27, unearned 0.91, "
        "shelter 1.01, sua 0.79, medical 1.03, depcare/hhcomp/arithmetic 1.0000)")
    const = fit_to_constants(t)

    # it2b-style rebased cause ratios on the pristine basis (SD6's recipe)
    const["UT_CAUSE_RATIO"] = rebased_cause_ratios_excl(QC_DIR, FYS, exclude)
    log("  rebased cause ratios:",
        {b: d for b, d in const["UT_CAUSE_RATIO"].items()
         if d != {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0}})
    # UT_P_UNIT from the pristine near-full|over (SD6's formula)
    const["UT_P_UNIT"] = 0.0125 * (t["ut"]["near_full_given_over"]
                                   / t["nat"]["near_full_given_over"])
    log(f"  UT_P_UNIT: {const['UT_P_UNIT']:.5f} (UT1 pooled: 0.00050)")

    # pristine real targets for the it2 realized-output calibrations
    real_t = real_ut_var_targets_excl(QC_DIR, FYS, exclude)

    # --- Stage 2: UT1's it2 recipe on the pristine fit -----------------------
    # 2a. pilot with pure ratios (coin cal 1.0) -> one-step realized-output
    #     bucket calibration
    log("stage 2a: pilot with pure refit ratios (coin cal 1.0)...")
    install_constants(const, coin_cal=1.0)
    pilot_path = gen_ut(OUT / "ut8_pilot.jsonl")
    synth_sh = synth_var_targets(pilot_path)
    real_sh = real_t["bucket"]
    cal = {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS:  # same sparsity guard as UT1's it2
            cal[b] = 1.0
        else:
            cal[b] = real_sh[b] / synth_sh["bucket"][b] if synth_sh["bucket"][b] > 0 else 1.0
    final_bucket = {b: const["UT_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}
    log("  bucket calibration multipliers:",
        {b: round(cal[b], 4) for b in SUPPORTED if cal[b] != 1.0})
    log("  calibrated bucket ratios:",
        {b: round(final_bucket[b], 4) for b in SUPPORTED})
    log("  (UT1 pooled baked: earned 1.357, unearned 1.097, shelter 0.923, "
        "sua 0.586, medical 2.204, depcare/hhcomp/arithmetic 1.0)")

    # 2b. UT1's it2 realized-output calibrations for the 97-share margins,
    #     the 97-resolution coins, and the non-97 direction margins
    share97, res97, dir97 = {}, {}, {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS:
            share97[b] = res97[b] = 1.0
            dir97[b] = {"over": 1.0, "under": 1.0}
            continue
        r = real_t["p97_share"].get(b)
        s = synth_sh["p97_share"].get(b)
        share97[b] = (r / s) if (r and s) else 1.0
        r = real_t["p_over_97"].get(b)
        s = synth_sh["p_over_97"].get(b)
        res97[b] = (r / s) if (r and s) else 1.0
        ro = real_t["p_over_non97"].get(b)
        so = synth_sh["p_over_non97"].get(b)
        ru = real_t["p_under_non97"].get(b)
        su = synth_sh["p_under_non97"].get(b)
        dir97[b] = {
            "over": (ro / so) if (ro and so) else 1.0,
            "under": (ru / su) if (ru and su) else 1.0,
        }
    final_97share = {b: const["UT_97_SHARE_RATIO"][b] * share97[b]
                     for b in SUPPORTED}
    final_97 = {b: const["UT_97_RATIO"][b] * res97[b] for b in SUPPORTED}
    final_dir = {b: {"over": const["UT_DIR_RATIO"][b]["over"] * dir97[b]["over"],
                     "under": const["UT_DIR_RATIO"][b]["under"] * dir97[b]["under"]}
                 for b in SUPPORTED}
    log("  97-share calibration multipliers:",
        {b: round(share97[b], 4) for b in SUPPORTED if share97[b] != 1.0})
    log("  97-resolution calibration multipliers:",
        {b: round(res97[b], 4) for b in SUPPORTED if res97[b] != 1.0})
    log("  direction calibration multipliers:",
        {b: {k: round(v, 4) for k, v in dir97[b].items()}
         for b in SUPPORTED if dir97[b] != {"over": 1.0, "under": 1.0}})
    ut_state.UT_BUCKET_RATIO = copy.deepcopy(final_bucket)
    ut_state.UT_97_SHARE_RATIO = copy.deepcopy(final_97share)
    ut_state.UT_97_RATIO = copy.deepcopy(final_97)
    ut_state.UT_DIR_RATIO = copy.deepcopy(final_dir)

    # 2c. coin-cal line search against the pristine marginal case-error rate
    log("stage 2c: UT_COIN_CAL grid search (n=8000 pilots, calibrated ratios)...")
    target = t["ut"]["finding_mix"]
    target_err = t["ut"]["case_err_rate"]
    best = None
    for scal in (0.95, 1.00, 1.05, 1.10):
        ut_state.UT_COIN_CAL = scal
        pp = gen_ut(OUT / f"ut8_coin_{scal:.2f}.jsonl", n=8000)
        l1, sm = finding_l1(pp, target)
        err = sm[2] + sm[3]
        log(f"  cal={scal:.2f}: finding L1={l1:.4f} synth_err={err:.4f} "
            f"(pristine target {target_err:.4f})")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"  chosen UT_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f}; UT1 used 1.05)")

    # 2d. final pristine-UT generation, SD2's n/seed
    log("stage 2d: final pristine-UT generation (n=20000, seed 7)...")
    install_constants(const, coin_cal=coin_cal)
    ut_state.UT_BUCKET_RATIO = copy.deepcopy(final_bucket)
    ut_state.UT_97_SHARE_RATIO = copy.deepcopy(final_97share)
    ut_state.UT_97_RATIO = copy.deepcopy(final_97)
    ut_state.UT_DIR_RATIO = copy.deepcopy(final_dir)
    ut_path = gen_ut(OUT / "ut8_ut_pristine.jsonl")
    l1, sm = finding_l1(ut_path, target)
    log(f"  pristine UT synth finding L1 vs real UT minus-holdout: {l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f}; "
        f"UT1 validation reported 0.0039 on pooled)")

    # --- Stage 3: national-arm byte-identity check ----------------------------
    nat_own = OUT / "nat_synth.jsonl"
    nat_ut2 = Path.home() / "workspace/scratch_ut/ut2out/nat_synth.jsonl"
    log("stage 3: regenerating the national arm (UT2's recipe)...")
    gen_national(nat_own)
    own_md5 = hashlib.md5(nat_own.read_bytes()).hexdigest()
    sd2_md5 = hashlib.md5(nat_ut2.read_bytes()).hexdigest() if nat_ut2.exists() else None
    log(f"  fresh md5: {own_md5}; UT2's file md5: {sd2_md5}")
    if sd2_md5 and own_md5 == sd2_md5:
        nat_path = str(nat_ut2)
        log("  byte-identical: reusing UT2's national file")
    else:
        nat_path = str(nat_own)
        log("  NOT byte-identical (or UT2 file missing): using fresh regeneration")

    # --- Stage 4: transfer battery on UT2's holdout ---------------------------
    log("stage 4: loading real UT microdata + holdout...")
    real = ut2.load_ut_real(QC_DIR)
    holdout_keys = [tuple(k) for k in saved["holdout_keys"]]
    test_real = [real[k] for k in holdout_keys]

    def subset(rows, y_idx):
        if y_idx == 2:  # element: error cases with a labeled bucket
            return [r for r in rows if r[2] is not None]
        return rows

    test_element = subset(test_real, 2)
    test_finding = subset(test_real, 1)
    log(f"  test {len(test_real)} rows, test errors {len(test_element)}")

    log("stage 4: loading synthetic sets...")
    ut_synth = ut2.load_synth(ut_path)
    nat_synth = ut2.load_synth(nat_path)
    log(f"  pristine UT synth {len(ut_synth)}, national synth {len(nat_synth)}")

    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score  # noqa: E402

    def run_task(train_rows, test_rows, y_idx, buckets):
        sX, sy = as_Xy8(subset(train_rows, y_idx), y_idx)
        rX, ry = as_Xy8(test_rows, y_idx)
        kw = {"random_state": 0}
        if args.balanced:
            kw["class_weight"] = "balanced"
        clf = HistGradientBoostingClassifier(**kw)
        clf.fit(sX, sy)
        pred = clf.predict(rX)
        labels = sorted(set(ry))
        per = f1_score(ry, pred, average=None, zero_division=0, labels=labels)
        m = {
            "acc": round(float(accuracy_score(ry, pred)), 4),
            "macroF1": round(float(f1_score(ry, pred, average="macro",
                                           zero_division=0)), 4),
            "per_bucket_F1": {b: round(float(v), 4)
                              for b, v in zip(labels, per)},
            "n_test": len(ry), "n_train": len(train_rows),
        }
        if y_idx == 1:  # finding: binary AUC from P(over)+P(under)
            proba = clf.predict_proba(rX)
            cls = list(clf.classes_)
            p_err = sum(proba[:, cls.index(c)] for c in (2, 3))
            y_bin = [0 if y == 1 else 1 for y in ry]
            m["binary_AUC"] = round(float(roc_auc_score(y_bin, p_err)), 4)
        return m

    setting = "balanced" if args.balanced else "no-classweight"
    log(f"stage 4: battery (GBM {setting}, clean-8 features)...")
    results = {"arms": {}, "holdout": HOLDOUT_JSON, "setting": setting,
               "features": CLEAN8, "ut_synth": ut_path, "nat_synth": nat_path,
               "n": N_SYNTH, "seed": SEED}
    buckets = ut2.BUCKETS_OF_INTEREST
    for arm_name, synth in (("a) pristine UT synth + GBM", ut_synth),
                            ("b) national synth + GBM", nat_synth)):
        results["arms"][arm_name] = {}
        log(f"\n== {arm_name} ({setting}) ==")
        for tname, test_rows, y_idx in (("element", test_element, 2),
                                       ("finding", test_finding, 1)):
            m_el = run_task(synth, test_rows, y_idx, buckets)
            results["arms"][arm_name][tname] = m_el
            line = (f"  {tname:8s}: acc={m_el['acc']:.4f} "
                    f"macroF1={m_el['macroF1']:.4f} (n_test={m_el['n_test']})")
            if y_idx == 2:
                pb = {b: m_el["per_bucket_F1"].get(b, 0.0) for b in buckets}
                line += " | " + " ".join(f"{b} F1={pb[b]:.3f}" for b in buckets)
            else:
                line += f" binary_AUC={m_el.get('binary_AUC', float('nan')):.3f}"
            log(line)

    # --- Stage 5: pristine-vs-SD2 comparison ----------------------------------
    log("\n== stage 5: comparison vs UT2 (fill in UT2's reported numbers) ==")
    comp = {
        "element": {
            "pristine_ut_acc": results["arms"]["a) pristine UT synth + GBM"]["element"]["acc"],
            "pristine_ut_macroF1": results["arms"]["a) pristine UT synth + GBM"]["element"]["macroF1"],
            "nat_acc": results["arms"]["b) national synth + GBM"]["element"]["acc"],
            "nat_macroF1": results["arms"]["b) national synth + GBM"]["element"]["macroF1"],
        },
        "finding": {
            "pristine_ut_binary_AUC":
                results["arms"]["a) pristine UT synth + GBM"]["finding"].get("binary_AUC"),
            "nat_binary_AUC":
                results["arms"]["b) national synth + GBM"]["finding"].get("binary_AUC"),
        },
        "refit": {
            "UT_COIN_CAL": coin_cal,
            "UT_P_UNIT": round(const["UT_P_UNIT"], 5),
            "UT_BUCKET_RATIO": {b: round(v, 4) for b, v in final_bucket.items()},
            "UT_97_SHARE_RATIO": {b: round(v, 4) for b, v in final_97share.items()},
            "UT_97_RATIO": {b: round(v, 4) for b, v in final_97.items()},
            "UT_DIR_RATIO": {b: {k: round(v, 4) for k, v in d.items()}
                             for b, d in final_dir.items()},
            "UT_CAUSE_RATIO": {b: d for b, d in const["UT_CAUSE_RATIO"].items()},
            "n_ut_rows_kept": t["n_ut_rows"],
            "pristine_finding_mix": {k: round(v, 4) for k, v in m.items()},
        },
    }
    results["comparison"] = comp
    log(json.dumps(comp, indent=2))
    outp = OUT / "ut8_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
