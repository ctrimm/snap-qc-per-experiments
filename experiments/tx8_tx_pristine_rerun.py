"""TX8 — pristine transfer rerun: demanded by TX2's own fairness caveat.

TX2 notes TX1's offsets were fit on pooled FY2020-2024 TX microdata INCLUDING
the holdout rows, so the TX-synth arms aren't pristine vs the test set and
the TX-vs-national advantage could be partly inflated by the generator having
seen test-set marginals. TX8 tests the caveat:

  1. Refit TX offsets on TX microdata EXCLUDING every holdout row in
     experiments/tx2_holdout_idx.json (same pooled FY2020-2024 window), via a
     verbatim port of tx1.fit_tx_targets with one change: the exclusion.
  2. Regenerate TX-conditioned synthetic (n=20k, seed 7) per TX1's final
     (it2) recipe: pure-empirical ratios -> pilot -> one-step realized-output
     calibrations (bucket x real/synth share; 97-resolution coins x
     real/synth P(over|97,b); direction margins x real/synth on the non-97
     slice) -> TX_COIN_CAL line search over {0.96, 0.98, 1.0, 1.02} against
     the pristine marginal case-error rate. Refit constants installed by
     monkey-patching tx_state module attributes (PA6's pattern; no src edits).
     The national arm is regenerated identically (n=20k, seed 7) and verified
     byte-identical to TX2's national file (/tmp/tx2out/nat_synth.jsonl).
  3. Retrain TX2's key arms on the element task: (a) pristine-TX synth,
     (b) national synth; evaluate both on the SAME holdout. GBM without
     class_weight (TX2's winning setting; --balanced flips it).
  4. Report element accuracy/macroF1 for (a) vs (b); the pristine
     TX-vs-national gap vs TX2's reported gap; how much absolute numbers
     moved; finding-task binary AUC for arm (a) vs TX2's.

Usage (from repo root):
    python3 experiments/tx8_tx_pristine_rerun.py [--balanced]
Results -> /tmp/tx8out/tx8_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at ~/workspace/snap-qc-data.
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

from src.synth import tx_state  # noqa: E402
import tx1_tx_generator as tx1  # noqa: E402
import tx2_tx_transfer as tx2  # noqa: E402
from src.synth.codebook import cause_bucket, element_bucket  # noqa: E402

QC_DIR = str(Path.home() / "workspace" / "snap-qc-data" / "raw")
HOLDOUT_JSON = str(ROOT / "experiments" / "tx_holdout_idx.json")
DIST = str(ROOT / "experiments" / "dist.json")
OUT = Path("/tmp/tx8out")
OUT.mkdir(exist_ok=True)
N_SYNTH = 20000
SEED = 7
FYS = [2020, 2021, 2022, 2023, 2024]
SUPPORTED = tx1.SUPPORTED
TX_STATE = tx1.TX_STATE
# Sparsity-guard buckets keep the national value through calibration, per TX1.
GUARD_BUCKETS = {"depcare", "arithmetic"}
# Behavioral direction classes (match tx_state.TX_OVER/UNDER_NATURES)
OVER = {35, 37, 38, 39, 53, 56, 7}
UNDER = {44, 52, 57, 6, 13}

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402


def fit_tx_targets_excl(qc_dir=QC_DIR, fys=FYS, exclude=frozenset()):
    """Verbatim port of tx1.fit_tx_targets, with holdout exclusion.

    exclude: set of (fy, 0-based index among TX rows in that FY's CSV) — the
    TX2 holdout keys. TX indexing matches tx2.load_tx_real (STATE stripped,
    TX rows counted in CSV order per FY, including excluded ones so indices
    line up). Verified 2026-09-29 that no TX rows carry STATE whitespace, so
    strip-vs-no-strip counts identically. Every other line of TX1's recipe is
    unchanged: FYWGT-weighted, microdata-implied rates, same guards.
    """
    finding = {"ny": Counter(), "nat": Counter()}
    err_cond = {"ny": defaultdict(float), "nat": defaultdict(float)}
    amterr = {"ny": [], "nat": []}
    w_amterr = {"ny": 0.0, "nat": 0.0}
    w_fsben = {"ny": 0.0, "nat": 0.0}
    near_full = {"ny": [0.0, 0.0], "nat": [0.0, 0.0]}
    bucket = {"ny": Counter(), "nat": Counter()}
    bucket_n = {"ny": Counter(), "nat": Counter()}
    nature = {"ny": Counter(), "nat": Counter()}
    nature_n = {"ny": Counter(), "nat": Counter()}
    p97 = {"ny": defaultdict(lambda: [0.0, 0.0]),
           "nat": defaultdict(lambda: [0.0, 0.0])}
    p97_n = {"ny": Counter(), "nat": Counter()}
    cause = {"ny": Counter(), "nat": Counter()}
    cause97 = {"ny": Counter(), "nat": Counter()}
    cause97_n = {"ny": Counter(), "nat": Counter()}
    causenon97 = {"ny": Counter(), "nat": Counter()}
    cause97blank = {"ny": [0.0, 0.0], "nat": [0.0, 0.0]}
    n_ny = 0

    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        tx_idx = 0  # TX-relative row index within this FY's CSV
        with open(path, newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                is_ny = row["STATE"].strip() == TX_STATE
                if is_ny:
                    key = (fy, tx_idx)
                    tx_idx += 1
                    if key in exclude:  # <- TX8's only change
                        continue
                g = "ny" if is_ny else "nat"
                w = tx1.fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                n_ny += is_ny
                status = row["STATUS"].strip()
                finding[g][status] += w
                ek = "earner" if tx1.fnum(row.get("FSEARN")) > 0 else "no_earner"
                if status in ("2", "3"):
                    err_cond[g][(ek, "err")] += w
                err_cond[g][(ek, "tot")] += w
                am = tx1.fnum(row.get("AMTERR"))
                w_amterr[g] += w * am
                w_fsben[g] += w * tx1.fnum(row.get("FSBEN"))
                if status in ("2", "3"):
                    amterr[g].append((w, abs(am), status))
                    if status == "2":
                        raw = tx1.fnum(row.get("RAWBEN"))
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

    t = {"n_tx_rows": n_ny, "ny": {}, "nat": {}}
    for g in ("ny", "nat"):
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
    ny, nat = t["ny"], t["nat"]
    t["ratios"] = {
        "coin": {s: ny[f"p_err_{s}"] / nat[f"p_err_{s}"]
                for s in ("earner", "no_earner")},
        "bucket": {},
        "nature97share": {},
        "naturedir": {},
        "cause_non97": {},
        "cause97": {},
        "p97": {},
        "s_over": ny["medO"] / nat["medO"],
        "s_under": ny["medU"] / nat["medU"],
    }
    tb_ny = sum(bucket["ny"].values())
    tb_nat = sum(bucket["nat"].values())
    for b in SUPPORTED:
        r = (bucket["ny"][b] / tb_ny) / (bucket["nat"][b] / tb_nat)
        t["ratios"]["bucket"][b] = r if bucket_n["ny"][b] >= 25 else 1.0
    for b in SUPPORTED:
        tot_ny = sum(v for (bb, _), v in nature["ny"].items() if bb == b)
        tot_nat = sum(v for (bb, _), v in nature["nat"].items() if bb == b)
        if p97_n["ny"][b] >= 5 and tot_ny > 0 and tot_nat > 0:
            r = (nature["ny"][(b, 97)] / tot_ny) / (nature["nat"][(b, 97)] / tot_nat)
            t["ratios"]["nature97share"][b] = r
        else:
            t["ratios"]["nature97share"][b] = 1.0
        nn97_ny = sum(v for (bb, n_), v in nature["ny"].items()
                      if bb == b and n_ != 97)
        nn97_nat = sum(v for (bb, n_), v in nature["nat"].items()
                       if bb == b and n_ != 97)
        dr = {}
        for k, nset in (("over", OVER), ("under", UNDER)):
            pk = sum(v for (bb, n_), v in nature["ny"].items()
                     if bb == b and n_ in nset) / nn97_ny if nn97_ny else 0
            qk = sum(v for (bb, n_), v in nature["nat"].items()
                     if bb == b and n_ in nset) / nn97_nat if nn97_nat else 0
            dr[k] = pk / qk if qk > 0 else 1.0
        nn97_n_ny = bucket_n["ny"][b] - p97_n["ny"][b]
        t["ratios"]["naturedir"][b] = dr if nn97_n_ny >= 25 else \
            {"over": 1.0, "under": 1.0}
    for b in SUPPORTED:
        tc_ny = sum(v for (bb, _), v in causenon97["ny"].items() if bb == b)
        tc_nat = sum(v for (bb, _), v in causenon97["nat"].items() if bb == b)
        for co in ("client", "agency", "no_fault", "other"):
            if bucket_n["ny"][b] < 25 or tc_ny == 0 or tc_nat == 0:
                r = 1.0
            else:
                p = causenon97["ny"][(b, co)] / tc_ny
                q = causenon97["nat"][(b, co)] / tc_nat
                r = p / q if q > 0 else 1.0
            t["ratios"]["cause_non97"][(b, co)] = r
    pool = Counter()
    for (b, c), w in cause97["ny"].items():
        pool[c] += w
    ptot = sum(pool.values())
    for b in SUPPORTED:
        nu = sum(v for (bb, _), v in cause97_n["ny"].items() if bb == b)
        tot = sum(v for (bb, _), v in cause97["ny"].items() if bb == b)
        if nu >= 5 and tot > 0:
            t["ratios"]["cause97"][b] = {
                c: v / tot for (bb, c), v in cause97["ny"].items() if bb == b}
        else:
            t["ratios"]["cause97"][b] = {c: v / ptot for c, v in pool.items()}
    for b in SUPPORTED:
        o_ny, tot_ny = p97["ny"][b]
        o_nat, tot_nat = p97["nat"][b]
        if p97_n["ny"][b] >= 5 and tot_nat > 0 and o_nat > 0:
            t["ratios"]["p97"][b] = (o_ny / tot_ny) / (o_nat / tot_nat)
        else:
            t["ratios"]["p97"][b] = 1.0
    t["tx_cause97_blank"] = ny["cause97_blank"]
    return t


def fit_to_constants(t):
    """Convert pristine fit output into tx_state constant overrides."""
    R = t["ratios"]
    return {
        "TX_COIN_RATIO": {s: R["coin"][s] for s in ("earner", "no_earner")},
        "TX_BUCKET_RATIO": {b: R["bucket"][b] for b in SUPPORTED},
        "TX_97_RATIO": {b: R["p97"][b] for b in SUPPORTED},
        "TX_97_SHARE_RATIO": {b: R["nature97share"][b] for b in SUPPORTED},
        "TX_DIR_RATIO": {b: {"over": R["naturedir"][b]["over"],
                              "under": R["naturedir"][b]["under"]}
                         for b in SUPPORTED},
        "TX_CAUSE_RATIO": {
            b: {co: R["cause_non97"][(b, co)]
                for co in ("client", "agency", "no_fault", "other")}
            for b in SUPPORTED},
        "TX_97_CAUSE": {b: {str(c): v for c, v in mix.items()}
                        for b, mix in R["cause97"].items()},
        "TX_S_OVER": R["s_over"],
        "TX_S_UNDER": R["s_under"],
        "TX_CAUSE97_BLANK": t["tx_cause97_blank"],
    }


def install_constants(const, coin_cal=1.0):
    """Monkey-patch tx_state module constants (read at call time). No src edits."""
    for name, val in const.items():
        setattr(tx_state, name, copy.deepcopy(val))
    tx_state.TX_COIN_CAL = coin_cal


def gen_tx(out, n=N_SYNTH, seed=SEED):
    tx_state.generate_tx(n=n, seed=seed, dist=DIST, out=str(out))
    return str(out)


def real_tx_var_targets_excl(qc_dir, fys, exclude):
    """Pristine real-TX variance-level targets for TX1's it2 calibration.

    FYWGT-weighted, variance-level, SUPPORTED buckets only, holdout rows
    excluded: bucket shares; per-bucket P(over|97) (status basis, same as
    TX1's fit p97); per-bucket non-97 nature-direction shares (nature-code
    basis with TX1's behavioral OVER/UNDER classes — the basis the direction
    margins act on in apply_tx_offsets).
    """
    bucket = Counter()
    p97 = defaultdict(lambda: [0.0, 0.0])   # b -> [over w, tot w]
    dr = defaultdict(lambda: [0.0, 0.0, 0.0])  # b -> [over w, under w, non97 w]
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        tx_idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != TX_STATE:
                    continue
                key = (fy, tx_idx)
                tx_idx += 1
                if key in exclude or row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = tx1.fnum(row.get("FYWGT"), 1.0)
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
                    if ni == 97:
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
        "p_over_97": {b: p97[b][0] / p97[b][1] for b in p97 if p97[b][1] > 0},
        "p_over_non97": {b: dr[b][0] / dr[b][2] for b in dr if dr[b][2] > 0},
        "p_under_non97": {b: dr[b][1] / dr[b][2] for b in dr if dr[b][2] > 0},
    }


def synth_var_targets(path):
    """Realized variance-level targets from a synth file, on the same basis
    as real_tx_var_targets_excl. 97 direction from the case finding (the
    resolution coin sets the realized direction while the recorded nature
    stays 97); non-97 direction from the recorded nature code (behavioral
    classes — the basis the direction margins act on)."""
    bucket = Counter()
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
        "p_over_97": {b: p97[b][0] / p97[b][1] for b in p97 if p97[b][1] > 0},
        "p_over_non97": {b: dr[b][0] / dr[b][2] for b in dr if dr[b][2] > 0},
        "p_under_non97": {b: dr[b][1] / dr[b][2] for b in dr if dr[b][2] > 0},
    }


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
    """Regenerate the national arm exactly per TX2's recipe."""
    subprocess.run(
        [sys.executable, "-m", "synth.generate", "--n", str(N_SYNTH),
         "--seed", str(SEED), "--dist", "../experiments/dist.json",
         "--max-attempts", "12", "--out", str(out)],
        check=True, cwd=str(ROOT / "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--balanced", action="store_true",
                    help="use class_weight='balanced' in the battery (only if "
                         "TX2's seed-7 battery says balanced wins for TX)")
    args = ap.parse_args()
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    # --- Stage 0: holdout exclusion set -------------------------------------
    saved = json.loads(Path(HOLDOUT_JSON).read_text())
    exclude = {(k[0], k[1]) for k in saved["holdout_keys"]}
    log(f"stage 0: holdout keys loaded: {len(exclude)} "
        f"(split_seed={saved['split_seed']}, n_tx_rows={saved['n_tx_rows']})")

    # --- Stage 1: pristine refit --------------------------------------------
    log("stage 1: refitting TX targets on TX microdata MINUS holdout rows...")
    t = fit_tx_targets_excl(QC_DIR, fys=FYS, exclude=exclude)
    log(f"  kept TX rows: {t['n_tx_rows']} (expect {saved['n_tx_rows'] - len(exclude)})")
    assert t["n_tx_rows"] == saved["n_tx_rows"] - len(exclude)
    p = t["ny"]
    m = p["finding_mix"]
    log(f"  TX minus-holdout: finding c/o/u "
        f"{m['1']:.4f}/{m['2']:.4f}/{m['3']:.4f} case_err {p['case_err_rate']:.4f} "
        f"p(over|err) {p['p_over_given_err']:.4f}")
    log("  (TX1 pooled basis: 0.6345/0.2101/0.1553 case_err 0.3655 p(over|err) 0.5750)")
    log("  pure-empirical bucket ratios:",
        {b: round(t["ratios"]["bucket"][b], 4) for b in SUPPORTED})
    log("  (TX1 pooled pure-empirical: earned 1.0080, unearned 1.0875, "
        "shelter 0.8105, sua 1.2056, medical 1.7477, hhcomp 1.5846)")
    const = fit_to_constants(t)

    # pristine real targets for the it2 realized-output calibrations
    real_t = real_tx_var_targets_excl(QC_DIR, FYS, exclude)

    # --- Stage 2: TX1's it2 recipe on the pristine fit -----------------------
    # 2a. pilot with pure ratios (coin cal 1.0) -> one-step realized-output
    #     bucket calibration
    log("stage 2a: pilot with pure refit ratios (coin cal 1.0)...")
    install_constants(const, coin_cal=1.0)
    pilot_path = gen_tx(OUT / "tx8_pilot.jsonl")
    synth_sh = synth_var_targets(pilot_path)
    real_sh = real_t["bucket"]
    cal = {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS:  # same sparsity guard as TX1's it2
            cal[b] = 1.0
        else:
            cal[b] = real_sh[b] / synth_sh["bucket"][b] if synth_sh["bucket"][b] > 0 else 1.0
    final_bucket = {b: const["TX_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}
    log("  bucket calibration multipliers:",
        {b: round(cal[b], 4) for b in SUPPORTED if cal[b] != 1.0})
    log("  calibrated bucket ratios:",
        {b: round(final_bucket[b], 4) for b in SUPPORTED})
    log("  (TX1 pooled baked: earned 1.0133, unearned 1.1821, shelter 0.8290, "
        "sua 1.0549, medical 2.0411, hhcomp 1.3287)")

    # 2b. TX1's it2b 97-share one-step (real/synth 97-share on the pilot).
    # TX1's 97-resolution-coin and direction-margin one-steps are DELIBERATELY
    # NOT replicated: on TX's mix both overshot (finding L1 0.0169 -> 0.0685),
    # so TX1 kept them at pure-empirical. The 97-share one-step is needed
    # because 97s materialize above their drawn share (pilot 0.41 vs 0.29
    # real), which otherwise inflates recorded no_fault (cause 26) and the
    # cause L1.
    def _synth_97_share(path):
        s97, stot = Counter(), Counter()
        with open(path) as fh:
            for line in fh:
                c = json.loads(line)
                if int(c["finding"]) not in (2, 3):
                    continue
                for v in c["variances"]:
                    b = v["element_bucket"]
                    if b in SUPPORTED:
                        stot[b] += 1
                        if v.get("nature") == 97:
                            s97[b] += 1
        return {b: (s97[b] / stot[b] if stot[b] else 0.0) for b in SUPPORTED}

    def _real_97_share_excl(qc_dir, fys, exclude):
        r97, rtot = Counter(), Counter()
        for fy in fys:
            path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
            tx_idx = 0
            with open(path, newline="") as fh:
                for row in csv.DictReader(fh):
                    if row["STATE"].strip() != TX_STATE:
                        continue
                    key = (fy, tx_idx)
                    tx_idx += 1
                    if key in exclude or row["STATUS"].strip() not in ("2", "3"):
                        continue
                    w = tx1.fnum(row.get("FYWGT"), 1.0)
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
                        rtot[b] += w
                        n = (row.get(f"NATURE{i}") or "").strip()
                        if n and int(float(n)) == 97:
                            r97[b] += w
        return {b: (r97[b] / rtot[b] if rtot[b] else 0.0) for b in SUPPORTED}

    synth_97sh = _synth_97_share(pilot_path)
    real_97sh = _real_97_share_excl(QC_DIR, FYS, exclude)
    share97 = {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS:
            share97[b] = 1.0
        else:
            s = synth_97sh[b]
            share97[b] = (real_97sh[b] / s) if s > 0 else 1.0
    final_97share = {b: const["TX_97_SHARE_RATIO"][b] * share97[b]
                     for b in SUPPORTED}
    log("  97-share calibration multipliers:",
        {b: round(share97[b], 4) for b in SUPPORTED if share97[b] != 1.0})
    log("  (TX1 pooled baked 97-share: earned 0.9601, unearned 0.6395, "
        "shelter 0.2859, sua 0.2808, medical 0.7728, depcare 0.4432, "
        "hhcomp 0.0993, arithmetic 0.0)")
    tx_state.TX_BUCKET_RATIO = copy.deepcopy(final_bucket)
    tx_state.TX_97_SHARE_RATIO = copy.deepcopy(final_97share)
    # TX_97_RATIO and TX_DIR_RATIO stay at const (pure-empirical) per TX1.

    # 2c. coin-cal line search against the pristine marginal case-error rate
    log("stage 2c: TX_COIN_CAL grid search (n=8000 pilots, calibrated ratios)...")
    target = t["ny"]["finding_mix"]
    target_err = t["ny"]["case_err_rate"]
    best = None
    for scal in (0.96, 0.98, 1.0, 1.02):
        tx_state.TX_COIN_CAL = scal
        pp = gen_tx(OUT / f"tx8_coin_{scal:.2f}.jsonl", n=8000)
        l1, sm = finding_l1(pp, target)
        err = sm[2] + sm[3]
        log(f"  cal={scal:.2f}: finding L1={l1:.4f} synth_err={err:.4f} "
            f"(pristine target {target_err:.4f})")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"  chosen TX_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f}; TX1 used 0.98)")

    # 2d. final pristine-TX generation, TX2's n/seed
    log("stage 2d: final pristine-TX generation (n=20000, seed 7)...")
    install_constants(const, coin_cal=coin_cal)
    tx_state.TX_BUCKET_RATIO = copy.deepcopy(final_bucket)
    tx_state.TX_97_SHARE_RATIO = copy.deepcopy(final_97share)
    tx_path = gen_tx(OUT / "tx8_tx_pristine.jsonl")
    l1, sm = finding_l1(tx_path, target)
    log(f"  pristine TX synth finding L1 vs real TX minus-holdout: {l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f}; "
        f"TX1 validation reported 0.0279 on pooled)")

    # --- Stage 3: national-arm byte-identity check ----------------------------
    nat_own = OUT / "nat_synth.jsonl"
    nat_tx2 = Path("/tmp/tx2out/nat_synth.jsonl")
    log("stage 3: regenerating the national arm (TX2's recipe)...")
    gen_national(nat_own)
    own_md5 = hashlib.md5(nat_own.read_bytes()).hexdigest()
    tx2_md5 = hashlib.md5(nat_tx2.read_bytes()).hexdigest() if nat_tx2.exists() else None
    log(f"  fresh md5: {own_md5}; TX2's file md5: {tx2_md5}")
    if tx2_md5 and own_md5 == tx2_md5:
        nat_path = str(nat_tx2)
        log("  byte-identical: reusing TX2's national file")
    else:
        nat_path = str(nat_own)
        log("  NOT byte-identical (or TX2 file missing): using fresh regeneration")

    # --- Stage 4: transfer battery on TX2's holdout ---------------------------
    log("stage 4: loading real TX microdata + holdout...")
    real = tx2.load_tx_real(QC_DIR)
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
    tx_synth = tx2.load_synth(tx_path)
    nat_synth = tx2.load_synth(nat_path)
    log(f"  pristine TX synth {len(tx_synth)}, national synth {len(nat_synth)}")

    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score  # noqa: E402

    def run_task(train_rows, test_rows, y_idx, buckets):
        sX, sy = tx2.as_Xy(train_rows, y_idx)
        rX, ry = tx2.as_Xy(test_rows, y_idx)
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
    log(f"stage 4: battery (GBM {setting})...")
    results = {"arms": {}, "holdout": HOLDOUT_JSON, "setting": setting,
               "tx_synth": tx_path, "nat_synth": nat_path,
               "n": N_SYNTH, "seed": SEED}
    buckets = tx2.BUCKETS_OF_INTEREST
    for arm_name, synth in (("a) pristine TX synth + GBM", tx_synth),
                            ("b) national synth + GBM", nat_synth)):
        results["arms"][arm_name] = {}
        log(f"\n== {arm_name} ({setting}) ==")
        for tname, test_rows, y_idx in (("element", test_element, 2),
                                       ("finding", test_finding, 1)):
            m_el = run_task(subset(synth, y_idx), test_rows, y_idx, buckets)
            results["arms"][arm_name][tname] = m_el
            line = (f"  {tname:8s}: acc={m_el['acc']:.4f} "
                    f"macroF1={m_el['macroF1']:.4f} (n_test={m_el['n_test']})")
            if y_idx == 2:
                pb = {b: m_el["per_bucket_F1"].get(b, 0.0) for b in buckets}
                line += " | " + " ".join(f"{b} F1={pb[b]:.3f}" for b in buckets)
            else:
                line += f" binary_AUC={m_el.get('binary_AUC', float('nan')):.3f}"
            log(line)

    # --- Stage 5: pristine-vs-TX2 comparison ----------------------------------
    log("\n== stage 5: comparison vs TX2 (fill in TX2's reported numbers) ==")
    comp = {
        "element": {
            "pristine_tx_acc": results["arms"]["a) pristine TX synth + GBM"]["element"]["acc"],
            "pristine_tx_macroF1": results["arms"]["a) pristine TX synth + GBM"]["element"]["macroF1"],
            "nat_acc": results["arms"]["b) national synth + GBM"]["element"]["acc"],
            "nat_macroF1": results["arms"]["b) national synth + GBM"]["element"]["macroF1"],
        },
        "finding": {
            "pristine_tx_binary_AUC":
                results["arms"]["a) pristine TX synth + GBM"]["finding"].get("binary_AUC"),
            "nat_binary_AUC":
                results["arms"]["b) national synth + GBM"]["finding"].get("binary_AUC"),
        },
        "refit": {
            "TX_COIN_CAL": coin_cal,
            "TX_BUCKET_RATIO": {b: round(v, 4) for b, v in final_bucket.items()},
            "TX_97_SHARE_RATIO": {b: round(v, 4) for b, v in final_97share.items()},
            "n_tx_rows_kept": t["n_tx_rows"],
            "pristine_finding_mix": {k: round(v, 4) for k, v in m.items()},
        },
    }
    results["comparison"] = comp
    log(json.dumps(comp, indent=2))
    outp = OUT / "tx8_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
