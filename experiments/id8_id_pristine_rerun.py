"""ID8 — pristine transfer rerun: demanded by ID2's own fairness caveat.

ID2 notes ID1's offsets were fit on pooled FY2020-2024 ID microdata INCLUDING
the holdout rows, so the ID-synth arms aren't pristine vs the test set and
the ID-vs-national advantage could be partly inflated by the generator having
seen test-set marginals. ID8 tests the caveat:

  1. Refit ID offsets on ID microdata EXCLUDING every holdout row in
     experiments/id2_holdout_idx.json (same pooled FY2020-2024 window), via a
     verbatim port of id1.fit_id_targets with one change: the exclusion.
  2. Regenerate ID-conditioned synthetic (n=20k, seed 7) per ID1's final
     (it3) recipe: pure-empirical ratios -> pilot -> one-step realized-output
     calibrations (bucket x real/synth share; 97-share x real/synth P(97|b);
     97-resolution coins x real/synth P(over|97,b); direction margins x
     real/synth on the non-97 slice; it2b-style rebased cause ratios =
     ID-non97-mix/dist-mixed-basis; ID_P_UNIT from pristine near-full|over)
     -> ID_COIN_CAL line search over {0.95, 1.00, 1.05, 1.10} against
     the pristine marginal case-error rate. Refit constants installed by
     monkey-patching id_state module attributes (PA6's pattern; no src edits).
     The national arm is regenerated identically (n=20k, seed 7) and verified
     byte-identical to ID2's national file (/tmp/id2out/nat_synth.jsonl).
     (ID1's it3 second 97-share push is NOT repeated: it hit a
     materialization ceiling with diminishing returns; one it2-style step.)
  3. Retrain ID2's key arms on element + finding: (a) pristine-ID synth,
     (b) national synth; evaluate both on the SAME holdout. GBM without
     class_weight='balanced' (ID2's finding-task winner: balanced wins AUC 3/3;
     --balanced is REQUIRED for ID), ID7's clean
     8-feature set (the production recipe; ID7 showed the v1->clean8 delta
     is disclosed: -0.028 acc / -0.016 macroF1 on element).
  4. Report element accuracy/macroF1 and finding binary AUC for (a) vs (b);
     the pristine ID-vs-national gap vs ID2's reported gap; how much
     absolute numbers moved (the contamination premium).

Usage (from repo root):
    python3 experiments/id8_id_pristine_rerun.py [--balanced]
Results -> /tmp/id8out/id8_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at ../snap-qc-data (beside the
repo checkout).
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

from src.synth import id_state  # noqa: E402
import id1_id_generator as id1  # noqa: E402
import id2_id_transfer as id2  # noqa: E402
from src.synth.codebook import cause_bucket, element_bucket  # noqa: E402

QC_DIR = str(ROOT.parent / "snap-qc-data" / "raw")
HOLDOUT_JSON = str(ROOT / "experiments" / "id2_holdout_idx.json")
DIST = str(ROOT / "experiments" / "dist.json")
OUT = Path("/tmp/id8out")
OUT.mkdir(exist_ok=True)
N_SYNTH = 20000
SEED = 7
FYS = [2022, 2023, 2024]  # ID1's fitting window (NY6 partial-year lesson)
SUPPORTED = id1.SUPPORTED
ID_STATE = id1.ID_STATE
# Sparsity-guard buckets keep the national value through calibration, per ID1.
GUARD_BUCKETS = {"depcare", "hhcomp", "arithmetic"}
# Behavioral direction classes (match id_state.ID_OVER/UNDER_NATURES)
OVER = {35, 37, 38, 39, 53, 56, 7}
UNDER = {44, 52, 57, 6, 13}

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

# Clean v1: ID7's 8-feature set (issued_benefit dropped as leakage).
CLEAN8 = ["hh_size", "earned", "unearned", "shelter", "sua",
          "medical_exp", "depcare", "senior_disabled"]


def as_Xy8(rows, y_idx):
    # id2's feature dicts are a superset of CLEAN8
    return [[r[0][k] for k in CLEAN8] for r in rows], [r[y_idx] for r in rows]


def fit_id_targets_excl(qc_dir=QC_DIR, fys=FYS, exclude=frozenset()):
    """Verbatim port of id1.fit_id_targets, with holdout exclusion.

    exclude: set of (fy, 0-based index among ID rows in that FY's CSV) — the
    ID2 holdout keys. ID indexing matches id2.load_id_real (STATE stripped,
    ID rows counted in CSV order per FY, including excluded ones so indices
    line up). Verified 2026-10-03 that no ID rows carry STATE whitespace, so
    strip-vs-no-strip counts identically. Every other line of ID1's recipe is
    unchanged: FYWGT-weighted, microdata-implied rates, same guards.
    """
    finding = {"id": Counter(), "nat": Counter()}
    err_cond = {"id": defaultdict(float), "nat": defaultdict(float)}
    amterr = {"id": [], "nat": []}
    w_amterr = {"id": 0.0, "nat": 0.0}
    w_fsben = {"id": 0.0, "nat": 0.0}
    near_full = {"id": [0.0, 0.0], "nat": [0.0, 0.0]}
    bucket = {"id": Counter(), "nat": Counter()}
    bucket_n = {"id": Counter(), "nat": Counter()}
    nature = {"id": Counter(), "nat": Counter()}
    nature_n = {"id": Counter(), "nat": Counter()}
    p97 = {"id": defaultdict(lambda: [0.0, 0.0]),
           "nat": defaultdict(lambda: [0.0, 0.0])}
    p97_n = {"id": Counter(), "nat": Counter()}
    cause = {"id": Counter(), "nat": Counter()}
    cause97 = {"id": Counter(), "nat": Counter()}
    cause97_n = {"id": Counter(), "nat": Counter()}
    causenon97 = {"id": Counter(), "nat": Counter()}
    cause97blank = {"id": [0.0, 0.0], "nat": [0.0, 0.0]}
    n_id = 0

    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        id_idx = 0  # ID-relative row index within this FY's CSV
        with open(path, newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                is_id = row["STATE"].strip() == ID_STATE
                if is_id:
                    key = (fy, id_idx)
                    id_idx += 1
                    if key in exclude:  # <- ID8's only change
                        continue
                g = "id" if is_id else "nat"
                w = id1.fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                n_id += is_id
                status = row["STATUS"].strip()
                finding[g][status] += w
                ek = "earner" if id1.fnum(row.get("FSEARN")) > 0 else "no_earner"
                if status in ("2", "3"):
                    err_cond[g][(ek, "err")] += w
                err_cond[g][(ek, "tot")] += w
                am = id1.fnum(row.get("AMTERR"))
                w_amterr[g] += w * am
                w_fsben[g] += w * id1.fnum(row.get("FSBEN"))
                if status in ("2", "3"):
                    amterr[g].append((w, abs(am), status))
                    if status == "2":
                        raw = id1.fnum(row.get("RAWBEN"))
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

    t = {"n_id_rows": n_id, "id": {}, "nat": {}}
    for g in ("id", "nat"):
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
    id, nat = t["id"], t["nat"]
    t["ratios"] = {
        "coin": {s: id[f"p_err_{s}"] / nat[f"p_err_{s}"]
                for s in ("earner", "no_earner")},
        "bucket": {},
        "nature97share": {},
        "naturedir": {},
        "cause_non97": {},
        "cause97": {},
        "p97": {},
        "s_over": id["medO"] / nat["medO"],
        "s_under": id["medU"] / nat["medU"],
    }
    tb_id = sum(bucket["id"].values())
    tb_nat = sum(bucket["nat"].values())
    for b in SUPPORTED:
        r = (bucket["id"][b] / tb_id) / (bucket["nat"][b] / tb_nat)
        t["ratios"]["bucket"][b] = r if bucket_n["id"][b] >= 25 else 1.0
    for b in SUPPORTED:
        tot_id = sum(v for (bb, _), v in nature["id"].items() if bb == b)
        tot_nat = sum(v for (bb, _), v in nature["nat"].items() if bb == b)
        if p97_n["id"][b] >= 5 and tot_id > 0 and tot_nat > 0:
            r = (nature["id"][(b, 97)] / tot_id) / (nature["nat"][(b, 97)] / tot_nat)
            t["ratios"]["nature97share"][b] = r
        else:
            t["ratios"]["nature97share"][b] = 1.0
        nn97_id = sum(v for (bb, n_), v in nature["id"].items()
                      if bb == b and n_ != 97)
        nn97_nat = sum(v for (bb, n_), v in nature["nat"].items()
                       if bb == b and n_ != 97)
        dr = {}
        for k, nset in (("over", OVER), ("under", UNDER)):
            pk = sum(v for (bb, n_), v in nature["id"].items()
                     if bb == b and n_ in nset) / nn97_id if nn97_id else 0
            qk = sum(v for (bb, n_), v in nature["nat"].items()
                     if bb == b and n_ in nset) / nn97_nat if nn97_nat else 0
            dr[k] = pk / qk if qk > 0 else 1.0
        nn97_n_id = bucket_n["id"][b] - p97_n["id"][b]
        t["ratios"]["naturedir"][b] = dr if nn97_n_id >= 25 else \
            {"over": 1.0, "under": 1.0}
    for b in SUPPORTED:
        tc_id = sum(v for (bb, _), v in causenon97["id"].items() if bb == b)
        tc_nat = sum(v for (bb, _), v in causenon97["nat"].items() if bb == b)
        for co in ("client", "agency", "no_fault", "other"):
            if bucket_n["id"][b] < 25 or tc_id == 0 or tc_nat == 0:
                r = 1.0
            else:
                p = causenon97["id"][(b, co)] / tc_id
                q = causenon97["nat"][(b, co)] / tc_nat
                r = p / q if q > 0 else 1.0
            t["ratios"]["cause_non97"][(b, co)] = r
    pool = Counter()
    for (b, c), w in cause97["id"].items():
        pool[c] += w
    ptot = sum(pool.values())
    for b in SUPPORTED:
        nu = sum(v for (bb, _), v in cause97_n["id"].items() if bb == b)
        tot = sum(v for (bb, _), v in cause97["id"].items() if bb == b)
        if nu >= 5 and tot > 0:
            t["ratios"]["cause97"][b] = {
                c: v / tot for (bb, c), v in cause97["id"].items() if bb == b}
        else:
            t["ratios"]["cause97"][b] = {c: v / ptot for c, v in pool.items()}
    for b in SUPPORTED:
        o_id, tot_id = p97["id"][b]
        o_nat, tot_nat = p97["nat"][b]
        if p97_n["id"][b] >= 5 and tot_nat > 0 and o_nat > 0:
            t["ratios"]["p97"][b] = (o_id / tot_id) / (o_nat / tot_nat)
        else:
            t["ratios"]["p97"][b] = 1.0
    t["id_cause97_blank"] = id["cause97_blank"]
    return t


def fit_to_constants(t):
    """Convert pristine fit output into id_state constant overrides."""
    R = t["ratios"]
    return {
        "ID_COIN_RATIO": {s: R["coin"][s] for s in ("earner", "no_earner")},
        "ID_BUCKET_RATIO": {b: R["bucket"][b] for b in SUPPORTED},
        "ID_97_RATIO": {b: R["p97"][b] for b in SUPPORTED},
        "ID_97_SHARE_RATIO": {b: R["nature97share"][b] for b in SUPPORTED},
        "ID_DIR_RATIO": {b: {"over": R["naturedir"][b]["over"],
                              "under": R["naturedir"][b]["under"]}
                         for b in SUPPORTED},
        "ID_CAUSE_RATIO": {
            b: {co: R["cause_non97"][(b, co)]
                for co in ("client", "agency", "no_fault", "other")}
            for b in SUPPORTED},
        "ID_97_CAUSE": {b: {str(c): v for c, v in mix.items()}
                        for b, mix in R["cause97"].items()},
        "ID_S_OVER": R["s_over"],
        "ID_S_UNDER": R["s_under"],
        "ID_CAUSE97_BLANK": t["id_cause97_blank"],
    }


def install_constants(const, coin_cal=1.0):
    """Monkey-patch id_state module constants (read at call time). No src edits."""
    for name, val in const.items():
        setattr(id_state, name, copy.deepcopy(val))
    id_state.ID_COIN_CAL = coin_cal


def gen_id(out, n=N_SYNTH, seed=SEED):
    id_state.generate_id(n=n, seed=seed, dist=DIST, out=str(out))
    return str(out)




def real_id_var_targets_excl(qc_dir, fys, exclude):
    """Pristine real-ID variance-level targets for ID1's it2 calibration.

    FYWGT-weighted, variance-level, SUPPORTED buckets only, holdout rows
    excluded: bucket shares; per-bucket P(97) nature share (the basis the
    97-share calibration multiplies); per-bucket P(over|97) (status basis,
    same as ID1's fit p97); per-bucket non-97 nature-direction shares
    (nature-code basis with ID1's behavioral OVER/UNDER classes).
    """
    bucket = Counter()
    share97 = defaultdict(lambda: [0.0, 0.0])  # b -> [97 w, tot w]
    p97 = defaultdict(lambda: [0.0, 0.0])      # b -> [over w, tot w]
    dr = defaultdict(lambda: [0.0, 0.0, 0.0])  # b -> [over w, under w, non97 w]
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        id_idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != ID_STATE:
                    continue
                key = (fy, id_idx)
                id_idx += 1
                if key in exclude or row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = id1.fnum(row.get("FYWGT"), 1.0)
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
    as real_id_var_targets_excl. 97 direction from the case finding (the
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
    """it2b-style rebased cause ratios on ID microdata MINUS holdout rows:
    ID non-97 empirical cause mix (coarse, FYWGT) / dist mixed cause basis.
    Sparsity guard: buckets with ID unweighted non-97 n < 25 keep 1.0."""
    from src.synth.codebook import cause_bucket
    mix = Counter(); tot = Counter(); nunw = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        id_idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != ID_STATE:
                    continue
                key = (fy, id_idx)
                id_idx += 1
                if key in exclude:
                    continue
                if row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = id1.fnum(row.get("FYWGT"), 1.0)
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
    """Regenerate the national arm exactly per ID2's recipe."""
    subprocess.run(
        [sys.executable, "-m", "synth.generate", "--n", str(N_SYNTH),
         "--seed", str(SEED), "--dist", "../experiments/dist.json",
         "--max-attempts", "12", "--out", str(out)],
        check=True, cwd=str(ROOT / "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--balanced", action="store_true",
                    help="use class_weight='balanced' in the battery (only if "
                         "ID2's seed-7 battery says balanced wins for ID)")
    args = ap.parse_args()
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    # --- Stage 0: holdout exclusion set -------------------------------------
    saved = json.loads(Path(HOLDOUT_JSON).read_text())
    exclude = {(k[0], k[1]) for k in saved["holdout_keys"]}
    log(f"stage 0: holdout keys loaded: {len(exclude)} "
        f"(split_seed={saved['split_seed']}, n_id_rows={saved['n_id_rows']})")

    # --- Stage 1: pristine refit --------------------------------------------
    log("stage 1: refitting ID targets on ID microdata MINUS holdout rows...")
    t = fit_id_targets_excl(QC_DIR, fys=FYS, exclude=exclude)
    # ID1's fitting window is FY2022-24 (3111 rows), but the holdout covers
    # all FY2020-2024 (960 rows). Expected kept = FY22-24 rows minus the
    # holdout rows that fall in FY2022-24 (781 of the 960; 179 are FY2020-21
    # and were never in the fit anyway).
    n_excl_in_window = sum(1 for (fy, _) in exclude if fy in FYS)
    expect_kept = 3111 - n_excl_in_window
    log(f"  kept ID rows: {t['n_id_rows']} (expect {expect_kept}; "
        f"{n_excl_in_window} holdout rows fall in FY2022-24)")
    assert t["n_id_rows"] == expect_kept
    p = t["id"]
    m = p["finding_mix"]
    log(f"  ID minus-holdout: finding c/o/u "
        f"{m['1']:.4f}/{m['2']:.4f}/{m['3']:.4f} case_err {p['case_err_rate']:.4f} "
        f"p(over|err) {p['p_over_given_err']:.4f}")
    log("  (ID1 pooled basis: 0.7535/0.1272/0.1193 case_err 0.2475 p(over|err) 0.5079)")
    log("  pure-empirical bucket ratios:",
        {b: round(t["ratios"]["bucket"][b], 4) for b in SUPPORTED})
    log("  (ID1 pooled pure-empirical: earned 1.35, unearned 0.99, "
        "shelter 0.91, sua 0.67, medical 1.41, depcare/hhcomp/arithmetic 1.0000)")
    const = fit_to_constants(t)

    # it2b-style rebased cause ratios on the pristine basis (ID6's recipe)
    const["ID_CAUSE_RATIO"] = rebased_cause_ratios_excl(QC_DIR, FYS, exclude)
    log("  rebased cause ratios:",
        {b: d for b, d in const["ID_CAUSE_RATIO"].items()
         if d != {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0}})
    # ID_P_UNIT from the pristine near-full|over (ID6's formula)
    const["ID_P_UNIT"] = 0.0125 * (t["id"]["near_full_given_over"]
                                   / t["nat"]["near_full_given_over"])
    log(f"  ID_P_UNIT: {const['ID_P_UNIT']:.5f} (ID1 pooled: 0.00050)")

    # pristine real targets for the it2 realized-output calibrations
    real_t = real_id_var_targets_excl(QC_DIR, FYS, exclude)

    # --- Stage 2: ID1's it2 recipe on the pristine fit -----------------------
    # 2a. pilot with pure ratios (coin cal 1.0) -> one-step realized-output
    #     bucket calibration
    log("stage 2a: pilot with pure refit ratios (coin cal 1.0)...")
    install_constants(const, coin_cal=1.0)
    pilot_path = gen_id(OUT / "id8_pilot.jsonl")
    synth_sh = synth_var_targets(pilot_path)
    Path(pilot_path).unlink()  # disk hygiene: /tmp is a 512MB shared tmpfs
    real_sh = real_t["bucket"]
    cal = {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS:  # same sparsity guard as ID1's it2
            cal[b] = 1.0
        else:
            cal[b] = real_sh[b] / synth_sh["bucket"][b] if synth_sh["bucket"][b] > 0 else 1.0
    final_bucket = {b: const["ID_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}
    log("  bucket calibration multipliers:",
        {b: round(cal[b], 4) for b in SUPPORTED if cal[b] != 1.0})
    log("  calibrated bucket ratios:",
        {b: round(final_bucket[b], 4) for b in SUPPORTED})
    log("  (ID1 pooled baked: earned 1.357, unearned 1.097, shelter 0.923, "
        "sua 0.586, medical 2.204, depcare/hhcomp/arithmetic 1.0)")

    # 2b. ID1's it2 realized-output calibrations for the 97-share margins,
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
    final_97share = {b: const["ID_97_SHARE_RATIO"][b] * share97[b]
                     for b in SUPPORTED}
    final_97 = {b: const["ID_97_RATIO"][b] * res97[b] for b in SUPPORTED}
    final_dir = {b: {"over": const["ID_DIR_RATIO"][b]["over"] * dir97[b]["over"],
                     "under": const["ID_DIR_RATIO"][b]["under"] * dir97[b]["under"]}
                 for b in SUPPORTED}
    log("  97-share calibration multipliers:",
        {b: round(share97[b], 4) for b in SUPPORTED if share97[b] != 1.0})
    log("  97-resolution calibration multipliers:",
        {b: round(res97[b], 4) for b in SUPPORTED if res97[b] != 1.0})
    log("  direction calibration multipliers:",
        {b: {k: round(v, 4) for k, v in dir97[b].items()}
         for b in SUPPORTED if dir97[b] != {"over": 1.0, "under": 1.0}})
    id_state.ID_BUCKET_RATIO = copy.deepcopy(final_bucket)
    id_state.ID_97_SHARE_RATIO = copy.deepcopy(final_97share)
    id_state.ID_97_RATIO = copy.deepcopy(final_97)
    id_state.ID_DIR_RATIO = copy.deepcopy(final_dir)

    # 2c. coin-cal line search against the pristine marginal case-error rate
    log("stage 2c: ID_COIN_CAL grid search (n=8000 pilots, calibrated ratios)...")
    target = t["id"]["finding_mix"]
    target_err = t["id"]["case_err_rate"]
    best = None
    for scal in (1.05, 1.10, 1.15, 1.20, 1.25):
        id_state.ID_COIN_CAL = scal
        pp = gen_id(OUT / f"id8_coin_{scal:.2f}.jsonl", n=8000)
        l1, sm = finding_l1(pp, target)
        Path(pp).unlink()  # disk hygiene: /tmp is a 512MB shared tmpfs
        err = sm[2] + sm[3]
        log(f"  cal={scal:.2f}: finding L1={l1:.4f} synth_err={err:.4f} "
            f"(pristine target {target_err:.4f})")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"  chosen ID_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f}; ID1 used 1.20)")

    # 2d. final pristine-ID generation, ID2's n/seed
    log("stage 2d: final pristine-ID generation (n=20000, seed 7)...")
    install_constants(const, coin_cal=coin_cal)
    id_state.ID_BUCKET_RATIO = copy.deepcopy(final_bucket)
    id_state.ID_97_SHARE_RATIO = copy.deepcopy(final_97share)
    id_state.ID_97_RATIO = copy.deepcopy(final_97)
    id_state.ID_DIR_RATIO = copy.deepcopy(final_dir)
    id_path = gen_id(OUT / "id8_id_pristine.jsonl")
    l1, sm = finding_l1(id_path, target)
    log(f"  pristine ID synth finding L1 vs real ID minus-holdout: {l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f}; "
        f"ID1 validation reported 0.0039 on pooled)")

    # --- Stage 3: national-arm byte-identity check ----------------------------
    nat_own = OUT / "nat_synth.jsonl"
    nat_id2 = Path("/tmp/id2out/nat_synth.jsonl")
    log("stage 3: regenerating the national arm (ID2's recipe)...")
    gen_national(nat_own)
    own_md5 = hashlib.md5(nat_own.read_bytes()).hexdigest()
    id2_md5 = hashlib.md5(nat_id2.read_bytes()).hexdigest() if nat_id2.exists() else None
    log(f"  fresh md5: {own_md5}; ID2's file md5: {id2_md5}")
    if id2_md5 and own_md5 == id2_md5:
        nat_path = str(nat_id2)
        log("  byte-identical: reusing ID2's national file")
    else:
        nat_path = str(nat_own)
        log("  NOT byte-identical (or ID2 file missing): using fresh regeneration")

    # --- Stage 4: transfer battery on ID2's holdout ---------------------------
    log("stage 4: loading real ID microdata + holdout...")
    real = id2.load_id_real(QC_DIR)
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
    id_synth = id2.load_synth(id_path)
    nat_synth = id2.load_synth(nat_path)
    log(f"  pristine ID synth {len(id_synth)}, national synth {len(nat_synth)}")

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
               "features": CLEAN8, "id_synth": id_path, "nat_synth": nat_path,
               "n": N_SYNTH, "seed": SEED}
    buckets = id2.BUCKETS_OF_INTEREST
    for arm_name, synth in (("a) pristine ID synth + GBM", id_synth),
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

    # --- Stage 5: pristine-vs-ID2 comparison ----------------------------------
    log("\n== stage 5: comparison vs ID2 (fill in ID2's reported numbers) ==")
    comp = {
        "element": {
            "pristine_id_acc": results["arms"]["a) pristine ID synth + GBM"]["element"]["acc"],
            "pristine_id_macroF1": results["arms"]["a) pristine ID synth + GBM"]["element"]["macroF1"],
            "nat_acc": results["arms"]["b) national synth + GBM"]["element"]["acc"],
            "nat_macroF1": results["arms"]["b) national synth + GBM"]["element"]["macroF1"],
        },
        "finding": {
            "pristine_id_binary_AUC":
                results["arms"]["a) pristine ID synth + GBM"]["finding"].get("binary_AUC"),
            "nat_binary_AUC":
                results["arms"]["b) national synth + GBM"]["finding"].get("binary_AUC"),
        },
        "refit": {
            "ID_COIN_CAL": coin_cal,
            "ID_P_UNIT": round(const["ID_P_UNIT"], 5),
            "ID_BUCKET_RATIO": {b: round(v, 4) for b, v in final_bucket.items()},
            "ID_97_SHARE_RATIO": {b: round(v, 4) for b, v in final_97share.items()},
            "ID_97_RATIO": {b: round(v, 4) for b, v in final_97.items()},
            "ID_DIR_RATIO": {b: {k: round(v, 4) for k, v in d.items()}
                             for b, d in final_dir.items()},
            "ID_CAUSE_RATIO": {b: d for b, d in const["ID_CAUSE_RATIO"].items()},
            "n_id_rows_kept": t["n_id_rows"],
            "pristine_finding_mix": {k: round(v, 4) for k, v in m.items()},
        },
    }
    results["comparison"] = comp
    log(json.dumps(comp, indent=2))
    outp = OUT / "id8_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
