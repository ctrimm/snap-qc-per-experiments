"""ID6 — temporal stability: does the ID transfer signal hold year to year?

Refit the ID conditioning on FY2022 ID microdata only (ID1's offsets are
pooled FY2022-2024 — FY2020/21 excluded per the NY6 partial-year lesson),
generate ID-conditioned synthetic with the refit offsets, train element +
finding classifiers per ID2's recipe (ID-conditioned synthetic + GBM with
class_weight="balanced" — ID2's finding-task winner — clean 8 features),
and test on FY2023-2024 real ID cases held out entirely from fitting and
training.

Comparison arms:
  T_refit: FY2022-fit ID synth, tested on FY2023-24 real ID (clean
           temporal test) AND on FY2022 real ID (train-period reference).
  T_pooled: pooled-fit ID synth (ID1 as-is, FY2022-24), tested on the same
           two sets (does refitting on the single earliest year matter?).
  (No T_excl21 arm: FY2021 is already excluded from all ID fitting per the
  NY6 lesson, so the partial-year sensitivity arm is moot.)
  train-period check: per-bucket F1 decay diagnosis on the T_refit arm
           (FY2022 -> FY2023-24) with test-set ns.

Year filtering: id1_id_generator's `fit` CLI subcommand fits the ID1
window (FY2022-2024). This script applies the filter by calling
fit_id_targets(qc_dir, fys=[2022]) directly and documenting the gap here.

Refit pipeline (mirrors ID1's it2 recipe, bucket step only):
  1. pure-empirical FY2022 offset ratios (same guards as ID1:
     sparsity guard ID unweighted n<25 -> 1.0);
  2. one-step realized-output bucket calibration x real_ID_share/synth_share
     on a 20k-case pilot (ID1's it2 bucket step);
  3. ID_COIN_CAL line search over {1.05, 1.10, 1.15, 1.20, 1.25} against
     the marginal ID FY2022 case-error rate on 8k-case pilots (ID1 chose
     1.20 on the pooled window);
  4. final 20k generation, seed 7 (ID2's n/seed conventions).
  The 97-share/dir/97-ratio blocks use pure-empirical period values (no
  realized recalibration) — conservative; the bucket step + coin cal carry
  the first-order mix shifts. ID_P_UNIT is recomputed from the refit
  period's near-full|over ratio (ID1's derivation).

Refit constants are installed by monkey-patching src.synth.id_state module
attributes (no src file is modified; all generator functions read these
globals at call time). The pooled arm is generated first, before any
patching, so it is ID1's as-is output.

exp34 codebook caution handled: nature/cause offsets are pinned to the
FY2024 dist.json convention (the generator's national base), and ID's
per-FY nature-97 cause-blank rate is checked for labeling breaks (ID1 found
ID blanks 50.2% of 97-causes pooled FY2022-24 — checked per-FY here). The
element/finding labels (STATUS, ELEMENT codes) are stable across the window.

Partial-year decision (documented per the runbook's shared rule): FY2020
(n=515) and FY2021 (n=213) are thin/partial-year files for ID and are
excluded from ALL ID fitting (ID1, ID6 refit, ID8 pristine). The ID2
holdout still covers all pooled FY2020-2024 rows.

Usage (from repo root):
    python3 experiments/id6_id_temporal.py
Results -> /tmp/id6out/id6_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at ../snap-qc-data (beside the
repo checkout).
"""
import copy
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from src.synth import id_state  # noqa: E402
import id1_id_generator as id1  # noqa: E402
import id2_id_transfer as id2  # noqa: E402
from src.synth.codebook import element_bucket  # noqa: E402

QC_DIR = str(ROOT.parent / "snap-qc-data" / "raw")
DIST = str(ROOT / "experiments" / "dist.json")
OUT = Path("/tmp/id6out")
OUT.mkdir(exist_ok=True)
N_SYNTH = 20000
SEED = 7
SUPPORTED = id1.SUPPORTED
COIN_GRID = (1.05, 1.10, 1.15, 1.20, 1.25)  # ID1 chose 1.20 on pooled FY22-24

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402


def gbm():
    # ID2's finding-task winner: balanced (ID4/ID5 use the balanced recipe).
    return HistGradientBoostingClassifier(random_state=0, class_weight="balanced")


# ---------------------------------------------------------------- helpers

def fit_to_constants(t):
    """Convert fit_id_targets output (FY-filtered) into id_state constant
    overrides with the same guards ID1 used. Pure-empirical (no realized-
    output calibration, no coin scalar).

    ID1's it2b lesson is baked in: the fit's pure non-97 cause ratios are
    vs the national NON-97 mix, but apply_id_offsets multiplies them onto
    the dist's MIXED cause basis. Rebase here as ID_non97_mix/dist_basis —
    the numerator is reconstructed from the fit's cause_non97 ratios times
    the national non-97 mix is NOT available, so instead recompute the
    rebased ratios directly from the refit-period empirical ID non-97 mix
    (recomputed below from the fit counters is overkill) — simpler: reuse
    ID1's it2b rebasing formula with the refit's own ID non-97 mix.
    The ID_CAUSE_RATIO block is intentionally omitted here: the refit
    installs it2b-style rebased ratios (ID non-97 mix / dist mixed basis)
    computed by rebased_cause_ratios() below, since the fit output does not
    carry the refit-period ID non-97 mix."""
    R = t["ratios"]
    return {
        "ID_COIN_RATIO": {s: R["coin"][s] for s in ("earner", "no_earner")},
        "ID_BUCKET_RATIO": {b: R["bucket"][b] for b in SUPPORTED},
        "ID_97_RATIO": {b: R["p97"][b] for b in SUPPORTED},
        "ID_97_SHARE_RATIO": {b: R["nature97share"][b] for b in SUPPORTED},
        "ID_DIR_RATIO": {b: {"over": R["naturedir"][b]["over"],
                             "under": R["naturedir"][b]["under"]}
                         for b in SUPPORTED},
        "ID_97_CAUSE": {b: {str(c): v for c, v in mix.items()}
                        for b, mix in R["cause97"].items()},
        "ID_S_OVER": R["s_over"],
        "ID_S_UNDER": R["s_under"],
        "ID_CAUSE97_BLANK": t["id_cause97_blank"],
        # ID_P_UNIT recomputed from the refit period's near-full|over
        # (ID1's derivation: P_UNIT_DEFAULT x id/nat near-full|over).
        "ID_P_UNIT": 0.0125 * (t["id"]["near_full_given_over"]
                               / t["nat"]["near_full_given_over"]),
    }


# Clean v1: ID7's 8-feature set (issued_benefit dropped as leakage).
CLEAN8 = ["hh_size", "earned", "unearned", "shelter", "sua",
          "medical_exp", "depcare", "senior_disabled"]


def install_constants(const, coin_cal=1.0):
    """Monkey-patch id_state module constants (read at call time)."""
    for name, val in const.items():
        setattr(id_state, name, copy.deepcopy(val))
    id_state.ID_COIN_CAL = coin_cal


def rebased_cause_ratios(qc_dir, fys):
    """it2b-style rebased cause ratios for a refit period: ID non-97
    empirical cause mix (coarse, FYWGT) / dist mixed cause basis.
    Sparsity guard: buckets with ID unweighted non-97 n < 25 keep 1.0."""
    from src.synth.codebook import cause_bucket
    mix = Counter(); tot = Counter(); nunw = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "16" or row["STATUS"].strip() not in ("2", "3"):
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


def as_Xy8(rows, y_idx):
    return [[r[0][k] for k in CLEAN8] for r in rows], [r[y_idx] for r in rows]


def gen_id(out, n=N_SYNTH, seed=SEED):
    id_state.generate_id(n=n, seed=seed, dist=DIST, out=str(out))
    return str(out)


def synth_bucket_shares(path):
    """Realized variance-level bucket shares (SUPPORTED only), unweighted."""
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


def real_id_var_shares(qc_dir, fys):
    """Real ID variance-level bucket shares, FYWGT-weighted, SUPPORTED only,
    on the generator's recorded basis (FY-filtered port of ID1's
    _real_id_var_mixes)."""
    bucket = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "16" or row["STATUS"].strip() not in ("2", "3"):
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
                    if b in SUPPORTED:
                        bucket[b] += w
    tot = sum(bucket.values())
    return {b: bucket[b] / tot for b in SUPPORTED}


def finding_l1(path, target_mix):
    """Finding L1 of a synth file vs a target {1:,2:,3:} mix."""
    find = Counter()
    n = 0
    with open(path) as fh:
        for line in fh:
            find[int(json.loads(line)["finding"])] += 1
            n += 1
    sm = {k: find[k] / n for k in (1, 2, 3)}
    tm = {1: target_mix["1"], 2: target_mix["2"], 3: target_mix["3"]}
    return sum(abs(sm[k] - tm[k]) for k in (1, 2, 3)), sm


def id_cause97_blank_by_fy(qc_dir, fys):
    """FYWGT-weighted share of ID nature-97 variances with blank AGENCY,
    per FY (exp34 labeling-break check)."""
    out = {}
    for fy in fys:
        blank = tot = 0.0
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "16" or row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = id1.fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                for i in range(1, 10):
                    n = (row.get(f"NATURE{i}") or "").strip()
                    if not n or n == "0":
                        continue
                    try:
                        ni = int(float(n))
                    except ValueError:
                        continue
                    if ni != 97:
                        continue
                    c = (row.get(f"AGENCY{i}") or "").strip()
                    tot += w
                    if not c or c == "0":
                        blank += w
        out[fy] = round(blank / tot, 4) if tot > 0 else None
    return out


def load_id_real(qc_dir, fys):
    """ID rows across the given FY files. Key: (fy, id-relative row idx).
    Mirrors id2_id_transfer.load_id_real with STATE='16'. Features are
    id2's v1 dict (a superset of CLEAN8); the battery selects CLEAN8."""
    rows = {}
    for fy in fys:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")), None)
        if path is None:
            raise FileNotFoundError(f"no csv under qcfy{fy}_csv")
        with open(path, newline="") as fh:
            id_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != "16":
                    continue
                status = row["STATUS"].strip()
                e1 = row.get("ELEMENT1", "").strip()
                bucket = element_bucket(int(e1)) if (e1 and status != "1") else None
                rows[(fy, id_idx)] = (
                    id2.real_row_features(row),
                    int(status),
                    bucket,
                )
                id_idx += 1
    return rows


def refit_recipe(t_fit, name, log):
    """Run ID1's it2 recipe (bucket step) on a fit output: pure-empirical
    constants -> 20k pilot -> realized-output bucket calibration ->
    ID_COIN_CAL line search on 8k pilots. Returns (final_bucket, cal,
    chosen_coin_cal, final_path, refit_finding_l1, const)."""
    const = fit_to_constants(t_fit)
    # it2b-style rebased cause ratios for the refit period (not the pooled
    # ID1 values — the FY2024 no-fault coding shift must not leak back).
    const["ID_CAUSE_RATIO"] = rebased_cause_ratios(QC_DIR, FIT_FYS[name])
    log(f"  [{name}] pure-empirical bucket ratios:",
        {b: round(const["ID_BUCKET_RATIO"][b], 3) for b in SUPPORTED})
    log(f"  [{name}] rebased cause ratios:",
        {b: const["ID_CAUSE_RATIO"][b] for b in SUPPORTED
         if const["ID_CAUSE_RATIO"][b] != {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0}})
    log(f"  [{name}] ID_P_UNIT refit: {const['ID_P_UNIT']:.5f}")

    install_constants(const, coin_cal=1.0)
    pilot_path = gen_id(OUT / f"id_{name}_pilot.jsonl")
    synth_sh = synth_bucket_shares(pilot_path)
    real_sh = real_id_var_shares(QC_DIR, FIT_FYS[name])
    Path(pilot_path).unlink()  # disk hygiene: /tmp is a 512MB shared tmpfs
    cal = {}
    for b in SUPPORTED:
        if const["ID_BUCKET_RATIO"][b] == 1.0:
            cal[b] = 1.0  # same sparsity guard as ID1 (guarded -> 1.0)
        else:
            cal[b] = real_sh[b] / synth_sh[b] if synth_sh[b] > 0 else 1.0
    final_bucket = {b: const["ID_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}
    log(f"  [{name}] calibration multipliers:",
        {b: round(cal[b], 3) for b in SUPPORTED if cal[b] != 1.0})
    log(f"  [{name}] calibrated bucket ratios:",
        {b: round(final_bucket[b], 3) for b in SUPPORTED})

    id_state.ID_BUCKET_RATIO = copy.deepcopy(final_bucket)
    target = t_fit["id"]["finding_mix"]
    target_err = t_fit["id"]["case_err_rate"]
    best = None
    for scal in COIN_GRID:
        id_state.ID_COIN_CAL = scal
        p = gen_id(OUT / f"id_{name}_coin_{scal:.2f}.jsonl", n=8000)
        l1, sm = finding_l1(p, target)
        Path(p).unlink()  # disk hygiene: /tmp is a 512MB shared tmpfs
        err = sm[2] + sm[3]
        log(f"  [{name}] cal={scal:.2f}: finding L1={l1:.4f} "
            f"synth_err={err:.4f} (target {target_err:.4f})")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"  [{name}] chosen ID_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f})")

    install_constants(const, coin_cal=coin_cal)
    id_state.ID_CAUSE_RATIO = copy.deepcopy(const["ID_CAUSE_RATIO"])
    id_state.ID_BUCKET_RATIO = copy.deepcopy(final_bucket)
    final_path = gen_id(OUT / f"id_{name}.jsonl")
    l1, sm = finding_l1(final_path, target)
    log(f"  [{name}] refit finding L1 vs real ID "
        f"{'/'.join(str(f) for f in FIT_FYS[name])}: {l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f})")
    return final_bucket, cal, coin_cal, final_path, l1, const


FIT_FYS = {
    "refit": [2022],
}


def main():
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    # --- Stage 0: fits ------------------------------------------------------
    log("stage 0: fitting targets (FY2022 refit / FY2023-24 test)...")
    t_fit = id1.fit_id_targets(QC_DIR, fys=FIT_FYS["refit"])
    t_ref = id1.fit_id_targets(QC_DIR, fys=[2023, 2024])
    log(f"  ID rows: refit FY2022 n={t_fit['n_id_rows']}, "
        f"test FY2023-24 n={t_ref['n_id_rows']}")
    for label, t in (("refit FY2022 ", t_fit), ("test FY23-24", t_ref)):
        p, q = t["id"], t["nat"]
        log(f"  {label}: ID finding c/o/u "
            f"{p['finding_mix']['1']:.4f}/{p['finding_mix']['2']:.4f}/"
            f"{p['finding_mix']['3']:.4f} "
            f"case_err {p['case_err_rate']:.4f} p_over|err {p['p_over_given_err']:.4f} "
            f"cause97_blank {t['id_cause97_blank']:.4f} "
            f"near_full|over {p['near_full_given_over']:.4f} "
            f"(nat case_err {q['case_err_rate']:.4f})")

    # --- Stage 0b: per-FY labeling-break check --------------------------------
    log("stage 0b: ID nature-97 cause-blank rate per FY...")
    blanks = id_cause97_blank_by_fy(QC_DIR, [2022, 2023, 2024])
    log("  per-FY blank share:", blanks)

    # --- Stage 1a: pooled arm first (unpatched, ID1 as-is) -------------------
    log("stage 1a: generating pooled-fit ID synth (n=20000, seed 7)...")
    pooled_path = gen_id(OUT / "id_pooled.jsonl")

    # --- Stages 1b-3: refit recipes ------------------------------------------
    log("stage 1b-3: refit recipe on FY2022 fit...")
    final_bucket, cal, coin_cal, refit_path, l1_refit, const = \
        refit_recipe(t_fit, "refit", log)

    # --- Stage 4: real ID test sets -----------------------------------------
    log("stage 4: loading real ID microdata...")
    real = load_id_real(QC_DIR, [2022, 2023, 2024])
    log(f"  ID rows loaded: {len(real)}")
    test_2324 = {k: v for k, v in real.items() if k[0] in (2023, 2024)}
    test_2022 = {k: v for k, v in real.items() if k[0] == 2022}
    log(f"  test FY23-24: {len(test_2324)} rows, "
        f"test FY2022: {len(test_2022)} rows")

    # --- Stage 5: transfer battery ------------------------------------------
    log("stage 5: training GBM (class_weight=balanced, ID2 recipe) on synth arms...")
    refit_synth = id2.load_synth(refit_path)
    pooled_synth = id2.load_synth(pooled_path)
    
    log(f"  refit synth {len(refit_synth)}, pooled synth {len(pooled_synth)}")

    def subset(rows, y_idx):
        if y_idx == 2:  # element: error cases with a labeled bucket
            return [r for r in rows if r[2] is not None]
        return rows

    results = {"arms": {}, "test_sets": {}}
    for tname, rows in (("FY23-24", test_2324), ("FY2022", test_2022)):
        rd = list(rows.values())
        te = subset(rd, 2)
        tf = subset(rd, 1)
        results["test_sets"][tname] = {
            "n": len(rd), "n_error": len(te),
            "element_labels": {b: sum(1 for r in te if r[2] == b)
                               for b in sorted({r[2] for r in te})},
            "finding_labels": {s: sum(1 for r in tf if r[1] == s) for s in (1, 2, 3)},
        }

    from sklearn.metrics import accuracy_score, f1_score  # noqa: E402

    def run_task(train_rows, test_rows, y_idx):
        # clean-8 features (ID7); id2's dicts are a superset of CLEAN8
        sX, sy = as_Xy8(train_rows, y_idx)
        rX, ry = as_Xy8(test_rows, y_idx)
        clf = gbm()
        clf.fit(sX, sy)
        pred = clf.predict(rX)
        labels = sorted(set(ry))
        per = f1_score(ry, pred, average=None, zero_division=0, labels=labels)
        return {
            "acc": round(float(accuracy_score(ry, pred)), 4),
            "macroF1": round(float(f1_score(ry, pred, average="macro",
                                           zero_division=0)), 4),
            "per_bucket_F1": {b: round(float(v), 4)
                              for b, v in zip(labels, per)},
            "n_test": len(ry), "n_train": len(train_rows),
        }

    for arm_name, synth in (("T_refit (FY2022 fit)", refit_synth),
                            ("T_pooled (ID1 as-is)", pooled_synth)):
        results["arms"][arm_name] = {}
        log(f"\n== {arm_name} ==")
        for tname, rows in (("FY23-24", test_2324), ("FY2022", test_2022)):
            rd = list(rows.values())
            m_el = run_task(subset(synth, 2), subset(rd, 2), 2)
            m_fi = run_task(subset(synth, 1), subset(rd, 1), 1)
            results["arms"][arm_name][tname] = {"element": m_el, "finding": m_fi}
            log(f"  [{tname}] element: acc={m_el['acc']:.4f} "
                f"macroF1={m_el['macroF1']:.4f} (n_test={m_el['n_test']})")
            log(f"  [{tname}] finding: acc={m_fi['acc']:.4f} "
                f"macroF1={m_fi['macroF1']:.4f} (n_test={m_fi['n_test']})")

    # --- Stage 6: per-bucket decay diagnosis (refit arm, FY2022 vs FY23-24) -
    log("\n== per-bucket F1: train-period (FY2022) vs test-period (FY23-24), "
        "T_refit ==")
    el_22 = results["arms"]["T_refit (FY2022 fit)"]["FY2022"]["element"]
    el_24 = results["arms"]["T_refit (FY2022 fit)"]["FY23-24"]["element"]
    ns_22 = results["test_sets"]["FY2022"]["element_labels"]
    ns_24 = results["test_sets"]["FY23-24"]["element_labels"]
    decay = []
    for b in sorted(set(el_22["per_bucket_F1"]) | set(el_24["per_bucket_F1"])):
        f22 = el_22["per_bucket_F1"].get(b, 0.0)
        f24 = el_24["per_bucket_F1"].get(b, 0.0)
        decay.append({"bucket": b, "F1_FY2022": f22, "F1_FY23-24": f24,
                      "delta": round(f24 - f22, 4),
                      "n_FY2022": ns_22.get(b, 0), "n_FY23-24": ns_24.get(b, 0)})
        log(f"  {b:18s} FY2022 F1={f22:.3f} (n={ns_22.get(b,0)})  "
            f"FY23-24 F1={f24:.3f} (n={ns_24.get(b,0)})  delta={f24 - f22:+.3f}")
    results["bucket_decay"] = decay

    results["refit_meta"] = {
        "n_id_rows_fit": t_fit["n_id_rows"],
        "n_id_rows_ref": t_ref["n_id_rows"],
        "ID_COIN_CAL": coin_cal,
        "ID_P_UNIT": const["ID_P_UNIT"],
        "ID_BUCKET_RATIO": {b: round(v, 4) for b, v in final_bucket.items()},
        "ID_CAUSE_RATIO": const["ID_CAUSE_RATIO"],
        "calibration_multipliers": {b: round(v, 4) for b, v in cal.items()},
        "pure_empirical_bucket_ratios":
            {b: round(v, 4) for b, v in const["ID_BUCKET_RATIO"].items()},
        "refit_finding_mix": {k: round(v, 4) for k, v in
                             t_fit["id"]["finding_mix"].items()},
        "test_finding_mix": {k: round(v, 4) for k, v in
                              t_ref["id"]["finding_mix"].items()},
        "cause97_blank_per_fy": blanks,
        "refit_finding_L1": round(l1_refit, 4),
        "elapsed_s": round(time.time() - t0, 1),
    }
    outp = OUT / "id6_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
