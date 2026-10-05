"""UT6 — temporal stability: does the UT transfer signal hold year to year?

Refit the UT conditioning on FY2022 UT microdata only (UT1's offsets were
fit FY2022-2024), generate UT-conditioned synthetic with the refit
offsets, train element + finding classifiers per UT2's recipe
(UT-conditioned synthetic + GBM, clean 8 features), and test on FY2023-2024
real UT cases held out entirely from fitting and training.

Comparison arms:
  T_refit: FY2022-fit UT synth, tested on FY2023-24 real UT (clean
           temporal test) AND on FY2022 real UT (train-period reference).
  T_pooled: FY2022-24-fit UT synth (UT1 as-is), tested on the same two
           sets (does refitting on the older year matter?).
  train-period check: per-bucket F1 decay diagnosis on the T_refit arm
           (FY2022 -> FY23-24) with test-set ns.

There is no excl21 arm: FY2020-21 are already excluded from the UT track's
fitting basis (UT1, NY6 lesson), so the partial-year sensitivity question
does not arise. The refit uses FY2022 alone (n=1,007) — the earliest
full-year file.

Year filtering: ut1_ut_generator's `fit` CLI subcommand has no --fys flag
(it always fits FY2022-2024). This script applies the filter by calling
fit_ut_targets(qc_dir, fys=[2022]) directly and documenting the gap here.

Refit pipeline (mirrors UT1's it2 recipe, bucket step only):
  1. pure-empirical FY2022 offset ratios (same guards as UT1:
     sparsity guard UT unweighted n<25 -> 1.0);
  2. one-step realized-output bucket calibration x real_UT_share/synth_share
     on a 20k-case pilot (UT1's it2 bucket step);
  3. UT_COIN_CAL line search over {0.95, 1.00, 1.05, 1.10} against
     the marginal UT FY2022 case-error rate on 8k-case pilots;
  4. final 20k generation, seed 7 (UT2's n/seed conventions).
  The 97-share/dir/97-ratio blocks use pure-empirical period values (no
  realized recalibration) — conservative; the bucket step + coin cal carry
  the first-order mix shifts. UT_P_UNIT is recomputed from the refit
  period's near-full|over ratio (UT1's derivation).

Refit constants are installed by monkey-patching src.synth.ut_state module
attributes (no src file is modified; all generator functions read these
globals at call time). The pooled arm is generated first, before any
patching, so it is UT1's as-is output.

exp34 codebook caution handled: nature/cause offsets are pinned to the
FY2024 dist.json convention (the generator's national base), and UT's
per-FY nature-97 cause-blank rate is checked for labeling breaks (UT1
found UT blanks 84.0% of 97-causes FY2022-24 — checked per-FY here). The
element/finding labels (STATUS, ELEMENT codes) are stable across the
window.

Usage (from repo root):
    python3 experiments/ut6_temporal.py
Results -> /tmp/ut6out/ut6_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at snap-qc-data/ next to the
repo checkout.
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

from src.synth import ut_state  # noqa: E402
import ut1_ut_generator as ut1  # noqa: E402
import ut2_ut_transfer as ut2  # noqa: E402
from src.synth.codebook import element_bucket  # noqa: E402

QC_DIR = str(ROOT.parent / "snap-qc-data" / "raw")
DIST = str(ROOT / "experiments" / "dist.json")
OUT = Path("/tmp/ut6out")
OUT.mkdir(exist_ok=True)
N_SYNTH = 20000
SEED = 7
SUPPORTED = ut1.SUPPORTED
COIN_GRID = (0.95, 1.00, 1.05, 1.10)  # UT1's neighborhood (chosen 1.05)

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402


def gbm():
    return HistGradientBoostingClassifier(random_state=0)


# ---------------------------------------------------------------- helpers

def fit_to_constants(t):
    """Convert fit_ut_targets output (FY-filtered) into ut_state constant
    overrides with the same guards UT1 used. Pure-empirical (no realized-
    output calibration, no coin scalar).

    UT1's it2b lesson is baked in: the fit's pure non-97 cause ratios are
    vs the national NON-97 mix, but apply_ut_offsets multiplies them onto
    the dist's MIXED cause basis. Rebase here as UT_non97_mix/dist_basis —
    the numerator is reconstructed from the fit's cause_non97 ratios times
    the national non-97 mix is NOT available, so instead recompute the
    rebased ratios directly from the refit-period empirical UT non-97 mix
    (recomputed below from the fit counters is overkill) — simpler: reuse
    UT1's it2b rebasing formula with the refit's own UT non-97 mix.
    The UT_CAUSE_RATIO block is intentionally omitted here: the refit
    installs it2b-style rebased ratios (UT non-97 mix / dist mixed basis)
    computed by rebased_cause_ratios() below, since the fit output does not
    carry the refit-period UT non-97 mix."""
    R = t["ratios"]
    return {
        "UT_COIN_RATIO": {s: R["coin"][s] for s in ("earner", "no_earner")},
        "UT_BUCKET_RATIO": {b: R["bucket"][b] for b in SUPPORTED},
        "UT_97_RATIO": {b: R["p97"][b] for b in SUPPORTED},
        "UT_97_SHARE_RATIO": {b: R["nature97share"][b] for b in SUPPORTED},
        "UT_DIR_RATIO": {b: {"over": R["naturedir"][b]["over"],
                             "under": R["naturedir"][b]["under"]}
                         for b in SUPPORTED},
        "UT_97_CAUSE": {b: {str(c): v for c, v in mix.items()}
                        for b, mix in R["cause97"].items()},
        "UT_S_OVER": R["s_over"],
        "UT_S_UNDER": R["s_under"],
        "UT_CAUSE97_BLANK": t["ut_cause97_blank"],
        # UT_P_UNIT recomputed from the refit period's near-full|over
        # (UT1's derivation: P_UNIT_DEFAULT x ut/nat near-full|over).
        "UT_P_UNIT": 0.0125 * (t["ut"]["near_full_given_over"]
                               / t["nat"]["near_full_given_over"]),
    }


# Clean v1: SD7's 8-feature set (issued_benefit dropped as leakage).
CLEAN8 = ["hh_size", "earned", "unearned", "shelter", "sua",
          "medical_exp", "depcare", "senior_disabled"]


def install_constants(const, coin_cal=1.0):
    """Monkey-patch ut_state module constants (read at call time)."""
    for name, val in const.items():
        setattr(ut_state, name, copy.deepcopy(val))
    ut_state.UT_COIN_CAL = coin_cal


def rebased_cause_ratios(qc_dir, fys):
    """it2b-style rebased cause ratios for a refit period: UT non-97
    empirical cause mix (coarse, FYWGT) / dist mixed cause basis.
    Sparsity guard: buckets with UT unweighted non-97 n < 25 keep 1.0."""
    from src.synth.codebook import cause_bucket
    mix = Counter(); tot = Counter(); nunw = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "49" or row["STATUS"].strip() not in ("2", "3"):
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


def as_Xy8(rows, y_idx):
    return [[r[0][k] for k in CLEAN8] for r in rows], [r[y_idx] for r in rows]


def gen_ut(out, n=N_SYNTH, seed=SEED):
    ut_state.generate_ut(n=n, seed=seed, dist=DIST, out=str(out))
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


def real_ut_var_shares(qc_dir, fys):
    """Real UT variance-level bucket shares, FYWGT-weighted, SUPPORTED only,
    on the generator's recorded basis (FY-filtered port of UT1's
    _real_ut_var_mixes)."""
    bucket = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "49" or row["STATUS"].strip() not in ("2", "3"):
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


def ut_cause97_blank_by_fy(qc_dir, fys):
    """FYWGT-weighted share of UT nature-97 variances with blank AGENCY,
    per FY (exp34 labeling-break check)."""
    out = {}
    for fy in fys:
        blank = tot = 0.0
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "49" or row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = ut1.fnum(row.get("FYWGT"), 1.0)
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


def load_ut_real(qc_dir, fys):
    """UT rows across the given FY files. Key: (fy, ut-relative row idx).
    Mirrors sd2_ut_transfer.load_ut_real with STATE='49'. Features are
    sd2's v1 dict (a superset of CLEAN8); the battery selects CLEAN8."""
    rows = {}
    for fy in fys:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")), None)
        if path is None:
            raise FileNotFoundError(f"no csv under qcfy{fy}_csv")
        with open(path, newline="") as fh:
            ut_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != "49":
                    continue
                status = row["STATUS"].strip()
                e1 = row.get("ELEMENT1", "").strip()
                bucket = element_bucket(int(e1)) if (e1 and status != "1") else None
                rows[(fy, ut_idx)] = (
                    ut2.real_row_features(row),
                    int(status),
                    bucket,
                )
                ut_idx += 1
    return rows


def refit_recipe(t_fit, name, log):
    """Run UT1's it2 recipe (bucket step) on a fit output: pure-empirical
    constants -> 20k pilot -> realized-output bucket calibration ->
    UT_COIN_CAL line search on 8k pilots. Returns (final_bucket, cal,
    chosen_coin_cal, final_path, refit_finding_l1, const)."""
    const = fit_to_constants(t_fit)
    # it2b-style rebased cause ratios for the refit period (not the pooled
    # UT1 values — the FY2024 no-fault coding shift must not leak back).
    const["UT_CAUSE_RATIO"] = rebased_cause_ratios(QC_DIR, FIT_FYS[name])
    log(f"  [{name}] pure-empirical bucket ratios:",
        {b: round(const["UT_BUCKET_RATIO"][b], 3) for b in SUPPORTED})
    log(f"  [{name}] rebased cause ratios:",
        {b: const["UT_CAUSE_RATIO"][b] for b in SUPPORTED
         if const["UT_CAUSE_RATIO"][b] != {"client": 1.0, "agency": 1.0, "no_fault": 1.0, "other": 1.0}})
    log(f"  [{name}] UT_P_UNIT refit: {const['UT_P_UNIT']:.5f}")

    install_constants(const, coin_cal=1.0)
    pilot_path = gen_ut(OUT / f"ut_{name}_pilot.jsonl")
    synth_sh = synth_bucket_shares(pilot_path)
    real_sh = real_ut_var_shares(QC_DIR, FIT_FYS[name])
    cal = {}
    for b in SUPPORTED:
        if const["UT_BUCKET_RATIO"][b] == 1.0:
            cal[b] = 1.0  # same sparsity guard as UT1 (guarded -> 1.0)
        else:
            cal[b] = real_sh[b] / synth_sh[b] if synth_sh[b] > 0 else 1.0
    final_bucket = {b: const["UT_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}
    log(f"  [{name}] calibration multipliers:",
        {b: round(cal[b], 3) for b in SUPPORTED if cal[b] != 1.0})
    log(f"  [{name}] calibrated bucket ratios:",
        {b: round(final_bucket[b], 3) for b in SUPPORTED})

    ut_state.UT_BUCKET_RATIO = copy.deepcopy(final_bucket)
    target = t_fit["ut"]["finding_mix"]
    target_err = t_fit["ut"]["case_err_rate"]
    best = None
    for scal in COIN_GRID:
        ut_state.UT_COIN_CAL = scal
        p = gen_ut(OUT / f"ut_{name}_coin_{scal:.2f}.jsonl", n=8000)
        l1, sm = finding_l1(p, target)
        err = sm[2] + sm[3]
        log(f"  [{name}] cal={scal:.2f}: finding L1={l1:.4f} "
            f"synth_err={err:.4f} (target {target_err:.4f})")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"  [{name}] chosen UT_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f})")

    install_constants(const, coin_cal=coin_cal)
    ut_state.UT_CAUSE_RATIO = copy.deepcopy(const["UT_CAUSE_RATIO"])
    ut_state.UT_BUCKET_RATIO = copy.deepcopy(final_bucket)
    final_path = gen_ut(OUT / f"ut_{name}.jsonl")
    l1, sm = finding_l1(final_path, target)
    log(f"  [{name}] refit finding L1 vs real UT "
        f"{'/'.join(str(f) for f in FIT_FYS[name])}: {l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f})")
    return final_bucket, cal, coin_cal, final_path, l1, const


# UT6 refit basis: FY2022 only. There is no excl21 arm — FY2020-21 are
# already excluded from the UT track's fitting basis (UT1, NY6 lesson), so
# the partial-year sensitivity question does not arise.
FIT_FYS = {
    "refit": [2022],
}


def main():
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    # --- Stage 0: fits ------------------------------------------------------
    log("stage 0: fitting targets (FY2022 refit / FY2023-24 ref)...")
    t_fit = ut1.fit_ut_targets(QC_DIR, fys=FIT_FYS["refit"])
    t_ref = ut1.fit_ut_targets(QC_DIR, fys=[2023, 2024])
    log(f"  UT rows: refit FY2022 n={t_fit['n_ut_rows']}, "
        f"ref FY2023-24 n={t_ref['n_ut_rows']}")
    for label, t in (("refit FY2022 ", t_fit),
                     ("test  FY23-24", t_ref)):
        p, q = t["ut"], t["nat"]
        log(f"  {label}: UT finding c/o/u "
            f"{p['finding_mix']['1']:.4f}/{p['finding_mix']['2']:.4f}/"
            f"{p['finding_mix']['3']:.4f} "
            f"case_err {p['case_err_rate']:.4f} p_over|err {p['p_over_given_err']:.4f} "
            f"cause97_blank {t['ut_cause97_blank']:.4f} "
            f"near_full|over {p['near_full_given_over']:.4f} "
            f"(nat case_err {q['case_err_rate']:.4f})")

    # --- Stage 0b: per-FY labeling-break check --------------------------------
    log("stage 0b: UT nature-97 cause-blank rate per FY...")
    blanks = ut_cause97_blank_by_fy(QC_DIR, [2020, 2021, 2022, 2023, 2024])
    log("  per-FY blank share:", blanks)

    # --- Stage 1a: pooled arm first (unpatched, NY1 as-is) -------------------
    log("stage 1a: generating pooled-fit UT synth (n=20000, seed 7)...")
    pooled_path = gen_ut(OUT / "ut_pooled.jsonl")

    # --- Stages 1b-3: refit recipes ------------------------------------------
    log("stage 1b-3: refit recipe on FY2022 fit...")
    final_bucket, cal, coin_cal, refit_path, l1_refit, const = \
        refit_recipe(t_fit, "refit", log)

    # --- Stage 4: real UT test sets -----------------------------------------
    log("stage 4: loading real UT microdata...")
    real = load_ut_real(QC_DIR, [2020, 2021, 2022, 2023, 2024])
    log(f"  UT rows loaded: {len(real)}")
    test_2324 = {k: v for k, v in real.items() if k[0] in (2023, 2024)}
    test_2022 = {k: v for k, v in real.items() if k[0] == 2022}
    log(f"  test FY23-24: {len(test_2324)} rows, "
        f"test FY2022: {len(test_2022)} rows")

    # --- Stage 5: transfer battery ------------------------------------------
    log("stage 5: training GBM (no class_weight) on synth arms...")
    refit_synth = ut2.load_synth(refit_path)
    pooled_synth = ut2.load_synth(pooled_path)
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
        # clean-8 features (SD7); ut2's dicts are a superset of CLEAN8
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
                            ("T_pooled (UT1 as-is)", pooled_synth)):
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

    # --- Stage 6: per-bucket decay diagnosis (refit arm, FY20-22 vs FY23-24) -
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
        "n_ut_rows_fit": t_fit["n_ut_rows"],
        "n_ut_rows_ref": t_ref["n_ut_rows"],
        "UT_COIN_CAL": coin_cal,
        "UT_P_UNIT": const["UT_P_UNIT"],
        "UT_BUCKET_RATIO": {b: round(v, 4) for b, v in final_bucket.items()},
        "UT_CAUSE_RATIO": const["UT_CAUSE_RATIO"],
        "calibration_multipliers": {b: round(v, 4) for b, v in cal.items()},
        "pure_empirical_bucket_ratios":
            {b: round(v, 4) for b, v in const["UT_BUCKET_RATIO"].items()},
        "fit_finding_mix": {k: round(v, 4) for k, v in
                             t_fit["ut"]["finding_mix"].items()},
        "test_finding_mix": {k: round(v, 4) for k, v in
                              t_ref["ut"]["finding_mix"].items()},
        "cause97_blank_per_fy": blanks,
        "refit_finding_L1": round(l1_refit, 4),
        "elapsed_s": round(time.time() - t0, 1),
    }
    outp = OUT / "ut6_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
