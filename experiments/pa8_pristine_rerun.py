"""PA8 — pristine transfer rerun: demanded by PA2's own fairness caveat.

PA2 noted PA1's offsets were fit on pooled FY2020-2024 PA microdata INCLUDING
the holdout rows, so the PA-synth arms weren't pristine vs the test set and
the PA-vs-national advantage could be partly inflated by the generator having
seen test-set marginals. PA8 tests the caveat:

  1. Refit PA offsets on PA microdata EXCLUDING every holdout row in
     experiments/pa2_holdout_idx.json (same pooled FY2020-2024 window).
  2. Regenerate PA-conditioned synthetic (n=20k, seed 7, PA2's recipe:
     PA1's it3 recipe = pure-empirical ratios + one-step realized-output
     bucket calibration + coin-cal line search) with the refit constants,
     installed by monkey-patching pa_state module attributes (PA6's
     pattern; no src edits). The national arm is regenerated identically
     (n=20k, seed 7) and verified byte-identical to PA2's national file.
  3. Retrain PA2's two key arms on the element task: (a) pristine-PA synth
     + GBM unweighted, (b) national synth + GBM unweighted. Evaluate both
     on the SAME holdout.
  4. Report element accuracy/macroF1 for (a) vs (b); the pristine
     PA-vs-national gap vs PA2's reported gap; how much absolute numbers
     moved. Sanity check: finding-task binary AUC for arm (a) vs PA2's 0.645.

Usage (from repo root):
    python3 experiments/pa8_pristine_rerun.py
Results -> /tmp/pa8out/pa8_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at ~/workspace/snap-qc-data.
"""
import copy
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from src.synth import pa_state  # noqa: E402
import pa1_pa_generator as pa1  # noqa: E402
import pa2_pa_transfer as pa2  # noqa: E402

QC_DIR = str(Path.home() / "workspace" / "snap-qc-data" / "raw")
HOLDOUT_JSON = str(ROOT / "experiments" / "pa2_holdout_idx.json")
DIST = str(ROOT / "experiments" / "dist.json")
OUT = Path("/tmp/pa8out")
OUT.mkdir(exist_ok=True)
N_SYNTH = 20000
SEED = 7
FYS = [2020, 2021, 2022, 2023, 2024]
SUPPORTED = pa1.SUPPORTED
GUARD_BUCKETS = {"depcare", "arithmetic"}  # PA1's sparsity guards

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402


def fit_pa_targets_excl(qc_dir=QC_DIR, fys=FYS, exclude=frozenset()):
    """Verbatim port of pa1.fit_pa_targets, with holdout exclusion.

    exclude: set of (fy, 0-based index among PA rows in that FY's CSV) —
    the PA2 holdout keys. PA indexing matches pa2.load_pa_real (STATE
    stripped, PA rows counted in CSV order per FY, including excluded ones
    so indices line up). Every other line of PA1's recipe is unchanged:
    FYWGT-weighted, microdata-implied rates, same guards.
    """
    from src.synth.codebook import element_bucket, cause_bucket

    finding = {"pa": Counter(), "nat": Counter()}
    err_cond = {"pa": defaultdict(float), "nat": defaultdict(float)}
    amterr = {"pa": [], "nat": []}
    w_amterr = {"pa": 0.0, "nat": 0.0}
    w_fsben = {"pa": 0.0, "nat": 0.0}
    near_full = {"pa": [0.0, 0.0], "nat": [0.0, 0.0]}
    bucket = {"pa": Counter(), "nat": Counter()}
    bucket_n = {"pa": Counter(), "nat": Counter()}
    nature = {"pa": Counter(), "nat": Counter()}
    nature_n = {"pa": Counter(), "nat": Counter()}
    p97 = {"pa": defaultdict(lambda: [0.0, 0.0]),
           "nat": defaultdict(lambda: [0.0, 0.0])}
    p97_n = {"pa": Counter(), "nat": Counter()}
    cause = {"pa": Counter(), "nat": Counter()}
    cause97 = {"pa": Counter(), "nat": Counter()}
    cause97_n = {"pa": Counter(), "nat": Counter()}
    causenon97 = {"pa": Counter(), "nat": Counter()}
    cause97blank = {"pa": [0.0, 0.0], "nat": [0.0, 0.0]}
    n_pa = 0

    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        pa_idx = 0  # PA-relative row index within this FY's CSV
        with open(path, newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                is_pa = row["STATE"].strip() == "42"
                if is_pa:
                    key = (fy, pa_idx)
                    pa_idx += 1
                    if key in exclude:  # <- PA8's only change
                        continue
                g = "pa" if is_pa else "nat"
                w = pa1.fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                n_pa += is_pa
                status = row["STATUS"].strip()
                finding[g][status] += w
                ek = "earner" if pa1.fnum(row.get("FSEARN")) > 0 else "no_earner"
                if status in ("2", "3"):
                    err_cond[g][(ek, "err")] += w
                err_cond[g][(ek, "tot")] += w
                am = pa1.fnum(row.get("AMTERR"))
                w_amterr[g] += w * am
                w_fsben[g] += w * pa1.fnum(row.get("FSBEN"))
                if status in ("2", "3"):
                    amterr[g].append((w, abs(am), status))
                    if status == "2":
                        raw = pa1.fnum(row.get("RAWBEN"))
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

    t = {"n_pa_rows": n_pa, "pa": {}, "nat": {}}
    for g in ("pa", "nat"):
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
    pa, nat = t["pa"], t["nat"]
    OVER = {35, 37, 38, 39, 53, 56, 7}
    UNDER = {44, 52, 57, 6, 13}
    t["ratios"] = {
        "coin": {s: pa[f"p_err_{s}"] / nat[f"p_err_{s}"]
                for s in ("earner", "no_earner")},
        "bucket": {},
        "nature97share": {},
        "naturedir": {},
        "cause_non97": {},
        "cause97": {},
        "p97": {},
        "s_over": pa["medO"] / nat["medO"],
        "s_under": pa["medU"] / nat["medU"],
    }
    tb_pa = sum(bucket["pa"].values())
    tb_nat = sum(bucket["nat"].values())
    for b in SUPPORTED:
        r = (bucket["pa"][b] / tb_pa) / (bucket["nat"][b] / tb_nat)
        t["ratios"]["bucket"][b] = r if bucket_n["pa"][b] >= 25 else 1.0
    for b in SUPPORTED:
        tot_pa = sum(v for (bb, _), v in nature["pa"].items() if bb == b)
        tot_nat = sum(v for (bb, _), v in nature["nat"].items() if bb == b)
        if p97_n["pa"][b] >= 5 and tot_pa > 0 and tot_nat > 0:
            r = (nature["pa"][(b, 97)] / tot_pa) / (nature["nat"][(b, 97)] / tot_nat)
            t["ratios"]["nature97share"][b] = r
        else:
            t["ratios"]["nature97share"][b] = 1.0
        nn97_pa = sum(v for (bb, n_), v in nature["pa"].items()
                      if bb == b and n_ != 97)
        nn97_nat = sum(v for (bb, n_), v in nature["nat"].items()
                       if bb == b and n_ != 97)
        dr = {}
        for k, nset in (("over", OVER), ("under", UNDER)):
            pk = sum(v for (bb, n_), v in nature["pa"].items()
                     if bb == b and n_ in nset) / nn97_pa if nn97_pa else 0
            qk = sum(v for (bb, n_), v in nature["nat"].items()
                     if bb == b and n_ in nset) / nn97_nat if nn97_nat else 0
            dr[k] = pk / qk if qk > 0 else 1.0
        nn97_n_pa = bucket_n["pa"][b] - p97_n["pa"][b]
        t["ratios"]["naturedir"][b] = dr if nn97_n_pa >= 25 else \
            {"over": 1.0, "under": 1.0}
    for b in SUPPORTED:
        tc_pa = sum(v for (bb, _), v in causenon97["pa"].items() if bb == b)
        tc_nat = sum(v for (bb, _), v in causenon97["nat"].items() if bb == b)
        for co in ("client", "agency", "no_fault", "other"):
            if bucket_n["pa"][b] < 25 or tc_pa == 0 or tc_nat == 0:
                r = 1.0
            else:
                p = causenon97["pa"][(b, co)] / tc_pa
                q = causenon97["nat"][(b, co)] / tc_nat
                r = p / q if q > 0 else 1.0
            t["ratios"]["cause_non97"][(b, co)] = r
    pool = Counter()
    for (b, c), w in cause97["pa"].items():
        pool[c] += w
    ptot = sum(pool.values())
    for b in SUPPORTED:
        nu = sum(v for (bb, _), v in cause97_n["pa"].items() if bb == b)
        tot = sum(v for (bb, _), v in cause97["pa"].items() if bb == b)
        if nu >= 5 and tot > 0:
            t["ratios"]["cause97"][b] = {
                c: v / tot for (bb, c), v in cause97["pa"].items() if bb == b}
        else:
            t["ratios"]["cause97"][b] = {c: v / ptot for c, v in pool.items()}
    for b in SUPPORTED:
        o_pa, tot_pa = p97["pa"][b]
        o_nat, tot_nat = p97["nat"][b]
        if p97_n["pa"][b] >= 5 and tot_nat > 0 and o_nat > 0:
            t["ratios"]["p97"][b] = (o_pa / tot_pa) / (o_nat / tot_nat)
        else:
            t["ratios"]["p97"][b] = 1.0
    t["pa_cause97_blank"] = pa["cause97_blank"]
    return t

def fit_to_constants(t):
    """Convert fit output into pa_state constant overrides (PA6's mapping)."""
    R = t["ratios"]
    return {
        "PA_COIN_RATIO": {s: R["coin"][s] for s in ("earner", "no_earner")},
        "PA_BUCKET_RATIO": {b: R["bucket"][b] for b in SUPPORTED},
        "PA_97_RATIO": {b: R["p97"][b] for b in SUPPORTED},
        "PA_97_SHARE_RATIO": {b: R["nature97share"][b] for b in SUPPORTED},
        "PA_DIR_RATIO": {b: {"over": R["naturedir"][b]["over"],
                             "under": R["naturedir"][b]["under"]}
                         for b in SUPPORTED},
        "PA_CAUSE_RATIO": {
            b: {co: R["cause_non97"][(b, co)]
                for co in ("client", "agency", "no_fault", "other")}
            for b in SUPPORTED},
        "PA_97_CAUSE": {b: {str(c): v for c, v in mix.items()}
                        for b, mix in R["cause97"].items()},
        "PA_S_OVER": R["s_over"],
        "PA_S_UNDER": R["s_under"],
        "PA_CAUSE97_BLANK": t["pa_cause97_blank"],
    }


def install_constants(const, coin_cal=1.0):
    """Monkey-patch pa_state module constants (read at call time). No src edits."""
    for name, val in const.items():
        setattr(pa_state, name, copy.deepcopy(val))
    pa_state.PA_COIN_CAL = coin_cal


def gen_pa(out, n=N_SYNTH, seed=SEED):
    pa_state.generate_pa(n=n, seed=seed, dist=DIST, out=str(out))
    return str(out)


def synth_bucket_shares(path):
    """Realized variance-level bucket shares (SUPPORTED only)."""
    bucket = Counter()
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            for v in c["variances"]:
                b = v["element_bucket"]
                if b in SUPPORTED:
                    bucket[b] += 1
    tot = sum(bucket.values())
    return {b: bucket[b] / tot for b in SUPPORTED}


def real_pa_var_shares_excl(qc_dir, fys, exclude):
    """Real PA variance-level bucket shares, FYWGT-weighted, SUPPORTED only,
    EXCLUDING holdout rows (PA8's pristine version of PA6's helper)."""
    from src.synth.codebook import element_bucket
    bucket = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        pa_idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != "42":
                    continue
                key = (fy, pa_idx)
                pa_idx += 1
                if key in exclude or row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = pa1.fnum(row.get("FYWGT"), 1.0)
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
                    if b in SUPPORTED:
                        bucket[b] += w
    tot = sum(bucket.values())
    return {b: bucket[b] / tot for b in SUPPORTED}


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


def main():
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    # --- Stage 0: holdout exclusion set -------------------------------------
    saved = json.loads(Path(HOLDOUT_JSON).read_text())
    exclude = {(k[0], k[1]) for k in saved["holdout_keys"]}
    log(f"stage 0: holdout keys loaded: {len(exclude)} "
        f"(expect 817; split_seed={saved['split_seed']}, n_pa_rows={saved['n_pa_rows']})")
    assert len(exclude) == 817, "holdout size changed — aborting"

    # --- Stage 1: pristine refit --------------------------------------------
    log("stage 1: refitting PA targets on PA microdata MINUS holdout rows...")
    t = fit_pa_targets_excl(QC_DIR, fys=FYS, exclude=exclude)
    log(f"  kept PA rows: {t['n_pa_rows']} (expect 2451 = 3268-817)")
    assert t["n_pa_rows"] == saved["n_pa_rows"] - len(exclude)
    p = t["pa"]
    m = p["finding_mix"]
    log(f"  PA minus-holdout: finding c/o/u "
        f"{m['1']:.4f}/{m['2']:.4f}/{m['3']:.4f} case_err {p['case_err_rate']:.4f} "
        f"p(over|err) {p['p_over_given_err']:.4f}")
    log("  (PA1 pooled basis was: 0.5875/0.2469/0.1656 case_err 0.4125 p(over|err) 0.5985)")
    log("  pure-empirical bucket ratios:",
        {b: round(t["ratios"]["bucket"][b], 4) for b in SUPPORTED})
    log("  (PA1 pooled pure-empirical: shelter 1.4420, medical 1.1623, "
        "hhcomp 0.9475, sua 0.6164, earned 0.9347, unearned 0.6846)")
    const = fit_to_constants(t)

    # --- Stage 2: PA1's it3 recipe on the pristine fit -----------------------
    # 2a. pilot with pure ratios -> one-step realized-output bucket calibration
    log("stage 2a: pilot with pure refit ratios (coin cal 1.0)...")
    install_constants(const, coin_cal=1.0)
    pilot_path = gen_pa(OUT / "pa8_pilot.jsonl")
    synth_sh = synth_bucket_shares(pilot_path)
    real_sh = real_pa_var_shares_excl(QC_DIR, FYS, exclude)
    cal = {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS or const["PA_BUCKET_RATIO"][b] == 1.0:
            cal[b] = 1.0  # same sparsity guard as PA1/PA6
        else:
            cal[b] = real_sh[b] / synth_sh[b] if synth_sh[b] > 0 else 1.0
    final_bucket = {b: const["PA_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}
    log("  calibration multipliers:",
        {b: round(cal[b], 4) for b in SUPPORTED if cal[b] != 1.0})
    log("  calibrated bucket ratios:",
        {b: round(final_bucket[b], 4) for b in SUPPORTED})
    log("  (PA1 pooled baked: shelter 1.5425, medical 1.5631, hhcomp 0.6117, "
        "sua 0.5368, earned 0.9492, unearned 0.6723)")

    # 2b. coin-cal line search against the pristine marginal case-error rate
    log("stage 2b: PA_COIN_CAL grid search (n=8000 pilots, calibrated buckets)...")
    pa_state.PA_BUCKET_RATIO = copy.deepcopy(final_bucket)
    target = t["pa"]["finding_mix"]
    target_err = t["pa"]["case_err_rate"]
    best = None
    for scal in (1.00, 1.04, 1.08, 1.12, 1.16):
        pa_state.PA_COIN_CAL = scal
        pp = gen_pa(OUT / f"pa8_coin_{scal:.2f}.jsonl", n=8000)
        l1, sm = finding_l1(pp, target)
        err = sm[2] + sm[3]
        log(f"  cal={scal:.2f}: finding L1={l1:.4f} synth_err={err:.4f} "
            f"(pristine target {target_err:.4f})")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"  chosen PA_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f}; PA1 used 1.08)")

    # 2c. final pristine-PA generation, PA2's n/seed
    log("stage 2c: final pristine-PA generation (n=20000, seed 7)...")
    install_constants(const, coin_cal=coin_cal)
    pa_state.PA_BUCKET_RATIO = copy.deepcopy(final_bucket)
    pa_path = gen_pa(OUT / "pa8_pa_pristine.jsonl")
    l1, sm = finding_l1(pa_path, target)
    log(f"  pristine PA synth finding L1 vs real PA minus-holdout: {l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f}; "
        f"PA1 validation reported 0.028 on pooled)")

    # --- Stage 3: national-arm byte-identity check ----------------------------
    nat_own = OUT / "nat_synth.jsonl"
    nat_pa2 = Path("/tmp/pa2out/nat_synth.jsonl")
    import hashlib
    own_md5 = hashlib.md5(nat_own.read_bytes()).hexdigest() if nat_own.exists() else None
    pa2_md5 = hashlib.md5(nat_pa2.read_bytes()).hexdigest() if nat_pa2.exists() else None
    log(f"stage 3: national regeneration md5: {own_md5}; PA2's file md5: {pa2_md5}")
    if own_md5 and pa2_md5 and own_md5 == pa2_md5:
        nat_path = str(nat_pa2)
        log("  byte-identical: reusing PA2's national file")
    elif own_md5:
        nat_path = str(nat_own)
        log("  NOT byte-identical (or PA2 file missing): using fresh regeneration")
    else:
        raise RuntimeError("national regeneration not finished — rerun after it lands")

    # --- Stage 4: transfer battery on PA2's holdout ---------------------------
    log("stage 4: loading real PA microdata + holdout...")
    real = pa2.load_pa_real(QC_DIR)
    holdout_keys = [tuple(k) for k in saved["holdout_keys"]]
    train_keys = [k for k in sorted(real.keys()) if k not in set(holdout_keys)]
    test_real = [real[k] for k in holdout_keys]

    def subset(rows, y_idx):
        if y_idx == 2:  # element: error cases with a labeled bucket
            return [r for r in rows if r[2] is not None]
        return rows

    test_element = subset(test_real, 2)
    test_finding = subset(test_real, 1)
    log(f"  test {len(test_real)} rows, test errors {len(test_element)}")

    log("stage 4: loading synthetic sets...")
    pa_synth = pa2.load_synth(pa_path)
    nat_synth = pa2.load_synth(nat_path)
    log(f"  pristine PA synth {len(pa_synth)}, national synth {len(nat_synth)}")

    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score  # noqa: E402

    def gbm():
        return HistGradientBoostingClassifier(random_state=0)  # no class_weight

    def run_task(train_rows, test_rows, y_idx, buckets_of_interest):
        sX, sy = pa2.as_Xy(train_rows, y_idx)
        rX, ry = pa2.as_Xy(test_rows, y_idx)
        clf = gbm()
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
        # finding-task binary AUC: P(error) = proba(2)+proba(3) vs correct(1)
        if y_idx == 1:
            proba = clf.predict_proba(rX)
            cls = list(clf.classes_)
            p_err = sum(proba[:, cls.index(c)] for c in (2, 3))
            y_bin = [0 if y == 1 else 1 for y in ry]
            m["binary_AUC"] = round(float(roc_auc_score(y_bin, p_err)), 4)
        return m

    results = {"arms": {}, "holdout": HOLDOUT_JSON,
               "pa_synth": pa_path, "nat_synth": nat_path,
               "n": N_SYNTH, "seed": SEED}
    buckets = ["shelter", "medical", "earned"]
    for arm_name, synth in (("a) pristine PA synth + GBM no-classweight", pa_synth),
                            ("b) national synth + GBM no-classweight", nat_synth)):
        results["arms"][arm_name] = {}
        log(f"\n== {arm_name} ==")
        for tname, test_rows, y_idx in (("element", test_element, 2),
                                       ("finding", test_finding, 1)):
            m_el = run_task(subset(synth, y_idx), test_rows, y_idx, buckets)
            results["arms"][arm_name][tname] = m_el
            line = (f"  {tname:8s}: acc={m_el['acc']:.4f} "
                    f"macroF1={m_el['macroF1']:.4f} (n_test={m_el['n_test']})")
            if y_idx == 2:
                pb = {b: m_el["per_bucket_F1"].get(b, 0.0) for b in buckets}
                line += (f" | shelter F1={pb['shelter']:.3f} "
                         f"medical F1={pb['medical']:.3f} earned F1={pb['earned']:.3f}")
            else:
                line += f" binary_AUC={m_el.get('binary_AUC', float('nan')):.3f}"
            log(line)

    # --- Stage 5: pristine-vs-PA2 comparison ----------------------------------
    A = results["arms"]["a) pristine PA synth + GBM no-classweight"]
    B = results["arms"]["b) national synth + GBM no-classweight"]
    pa2_a = {"element": {"acc": 0.567, "macroF1": 0.208},   # PA2 arm b
             "finding": {"binary_AUC": 0.645}}
    pa2_b = {"element": {"acc": 0.530, "macroF1": 0.170}}    # PA2 arm d
    comp = {
        "element": {
            "pristine_pa_acc": A["element"]["acc"], "pristine_pa_macroF1": A["element"]["macroF1"],
            "nat_acc": B["element"]["acc"], "nat_macroF1": B["element"]["macroF1"],
            "gap_acc_pristine": round(A["element"]["acc"] - B["element"]["acc"], 4),
            "gap_macroF1_pristine": round(A["element"]["macroF1"] - B["element"]["macroF1"], 4),
            "gap_acc_pa2": round(pa2_a["element"]["acc"] - pa2_b["element"]["acc"], 4),
            "gap_macroF1_pa2": round(pa2_a["element"]["macroF1"] - pa2_b["element"]["macroF1"], 4),
            "move_pa_acc": round(A["element"]["acc"] - pa2_a["element"]["acc"], 4),
            "move_pa_macroF1": round(A["element"]["macroF1"] - pa2_a["element"]["macroF1"], 4),
            "move_nat_acc": round(B["element"]["acc"] - pa2_b["element"]["acc"], 4),
        },
        "finding": {
            "pristine_pa_binary_AUC": A["finding"].get("binary_AUC"),
            "nat_binary_AUC": B["finding"].get("binary_AUC"),
            "pa2_pa_binary_AUC": pa2_a["finding"]["binary_AUC"],
        },
        "refit": {
            "PA_COIN_CAL": coin_cal,
            "PA_BUCKET_RATIO": {b: round(v, 4) for b, v in final_bucket.items()},
            "n_pa_rows_kept": t["n_pa_rows"],
        },
    }
    results["comparison"] = comp
    log("\n== comparison (pristine vs PA2) ==")
    log(json.dumps(comp, indent=2))
    outp = OUT / "pa8_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
