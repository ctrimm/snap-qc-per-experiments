"""PA6 — temporal stability: does the PA signal hold year to year?

Refit the PA conditioning on FY2020-2022 PA microdata only (PA1's offsets
were pooled FY2020-2024), generate PA-conditioned synthetic with the refit
offsets, train element + finding classifiers per PA2's recipe
(PA-conditioned synthetic + GBM without class_weight), and test on
FY2023-2024 real PA cases held out entirely from fitting and training.

Comparison arms:
  T_refit: FY2020-22-fit PA synth, tested on FY2023-24 real PA (clean temporal test)
  T_pooled: pooled-fit PA synth (PA1 as-is), tested on FY2023-24 real PA
           (does refitting on old years matter?)
  reference: PA2's same-period holdout numbers (pooled fit, stratified
             75/25 holdout of FY2020-2024) quoted from pa2_pa_transfer.md
  train-period check: both arms also tested on FY2020-22 real PA, giving the
             train-period vs test-period gap; per-bucket F1 decay diagnosis.

Year filtering: pa1_pa_generator's `fit` CLI subcommand has no --fys flag
(it always fits pooled). This script applies the filter by calling
fit_pa_targets(qc_dir, fys=[2020, 2021, 2022]) directly and documenting the
gap here.

Refit pipeline (mirrors PA1's it2->it3 recipe):
  1. pure-empirical FY2020-22 offset ratios (same guards as PA1);
  2. one-step realized-output bucket calibration x real_PA_share/synth_share
     (PA1's it3), measured on a 20k-case pilot at PA_COIN_CAL=1.0;
  3. PA_COIN_CAL line search (grid 1.00-1.16) against the marginal PA
     FY2020-22 case-error rate on 8k-case pilots;
  4. final 20k generation, seed 7 (PA2's n/seed conventions).

Refit constants are installed by monkey-patching src.synth.pa_state module
attributes (no src file is modified; all generator functions read these
globals at call time). The pooled arm is generated first, before any
patching, so it is byte-identical to PA1's as-is output.

exp34 caveat handled: nature/cause offsets are pinned to the FY2024
dist.json convention (the generator's national base); PA recorded a cause
on every nature-97 in all FYs (blank 0.000), so there is no PA-side
codebook break to launder. Element/finding labels (STATUS, ELEMENT codes)
are stable across the window.

Usage (from repo root):
    python3 experiments/pa6_temporal.py
Results -> /tmp/pa6out/pa6_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at ~/workspace/snap-qc-data.
"""
import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from src.synth import pa_state  # noqa: E402
import pa1_pa_generator as pa1  # noqa: E402
import pa2_pa_transfer as pa2  # noqa: E402

QC_DIR = str(Path.home() / "workspace" / "snap-qc-data" / "raw")
DIST = str(ROOT / "experiments" / "dist.json")
OUT = Path("/tmp/pa6out")
OUT.mkdir(exist_ok=True)
N_SYNTH = 20000
SEED = 7
SUPPORTED = pa1.SUPPORTED
GUARD_BUCKETS = {"depcare", "arithmetic"}  # PA1's sparsity guards

# PA2's training recipe (fixed): v1 features, GBM defaults, no class_weight.
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402


def gbm():
    return HistGradientBoostingClassifier(random_state=0)


def synth_bucket_shares(path):
    """Realized variance-level bucket shares (SUPPORTED only), like PA1's
    _synth_marginals but returning the raw share dict."""
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


def real_pa_var_shares(qc_dir, fys):
    """Real PA variance-level bucket shares, FYWGT-weighted, SUPPORTED only,
    on the generator's recorded basis (FY-filtered port of PA1's
    _real_pa_var_mixes)."""
    from src.synth.codebook import element_bucket
    bucket = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "42" or row["STATUS"].strip() not in ("2", "3"):
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


import csv  # noqa: E402  (after function defs using it is fine at runtime)


def fit_to_constants(t):
    """Convert fit_pa_targets output (FY-filtered) into pa_state constant
    overrides with the same guards PA1 used. Pure-empirical (no realized-
    output calibration, no coin scalar)."""
    R = t["ratios"]
    const = {
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
    return const


def install_constants(const, coin_cal=1.0):
    """Monkey-patch pa_state module constants (read at call time)."""
    for name, val in const.items():
        setattr(pa_state, name, copy.deepcopy(val))
    pa_state.PA_COIN_CAL = coin_cal


def gen_pa(out, n=N_SYNTH, seed=SEED):
    pa_state.generate_pa(n=n, seed=seed, dist=DIST, out=str(out))
    return str(out)


def main():
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    # --- Stage 0: fits ------------------------------------------------------
    log("stage 0: fitting targets (FY2020-22 fit / FY2023-24 reference)...")
    t_fit = pa1.fit_pa_targets(QC_DIR, fys=[2020, 2021, 2022])
    t_ref = pa1.fit_pa_targets(QC_DIR, fys=[2023, 2024])
    log(f"  PA rows: fit FY2020-22 n={t_fit['n_pa_rows']}, "
        f"reference FY2023-24 n={t_ref['n_pa_rows']}")
    for label, t in (("fit  FY20-22", t_fit), ("test FY23-24", t_ref)):
        p, q = t["pa"], t["nat"]
        log(f"  {label}: PA finding c/o/u "
            f"{p['finding_mix']['1']:.4f}/{p['finding_mix']['2']:.4f}/{p['finding_mix']['3']:.4f} "
            f"case_err {p['case_err_rate']:.4f} p_over|err {p['p_over_given_err']:.4f}")
        log(f"           nat case_err {q['case_err_rate']:.4f} "
            f"(pooled PA1 basis: PA 0.4125 / nat 0.3849)")
    const = fit_to_constants(t_fit)
    log("  pure-empirical FY20-22 bucket ratios:",
        {b: round(const["PA_BUCKET_RATIO"][b], 3) for b in SUPPORTED})

    # --- Stage 1a: pooled arm first (unpatched, PA1 as-is) -------------------
    log("stage 1a: generating pooled-fit PA synth (n=20000, seed 7)...")
    pooled_path = gen_pa(OUT / "pa_pooled.jsonl")

    # --- Stage 1b: pilot with pure ratios -> bucket calibration -------------
    log("stage 1b: pilot with pure FY20-22 ratios (coin cal 1.0)...")
    install_constants(const, coin_cal=1.0)
    pilot_path = gen_pa(OUT / "pa_refit_pilot.jsonl")
    synth_sh = synth_bucket_shares(pilot_path)
    real_sh = real_pa_var_shares(QC_DIR, [2020, 2021, 2022])
    cal = {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS or const["PA_BUCKET_RATIO"][b] == 1.0:
            cal[b] = 1.0  # same sparsity guard as PA1
        else:
            cal[b] = real_sh[b] / synth_sh[b] if synth_sh[b] > 0 else 1.0
    final_bucket = {b: const["PA_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}
    log("  calibration multipliers:",
        {b: round(cal[b], 3) for b in SUPPORTED if cal[b] != 1.0})
    log("  calibrated FY20-22 bucket ratios:",
        {b: round(final_bucket[b], 3) for b in SUPPORTED})

    # --- Stage 2: coin scalar line search (under calibrated buckets) -------
    log("stage 2: PA_COIN_CAL grid search (n=8000 pilots, calibrated buckets)...")
    pa_state.PA_BUCKET_RATIO = copy.deepcopy(final_bucket)
    target = t_fit["pa"]["finding_mix"]
    target_err = t_fit["pa"]["case_err_rate"]
    best = None
    for scal in (1.00, 1.04, 1.08, 1.12, 1.16):
        pa_state.PA_COIN_CAL = scal
        p = gen_pa(OUT / f"pa_coin_{scal:.2f}.jsonl", n=8000)
        l1, sm = finding_l1(p, target)
        err = sm[2] + sm[3]
        log(f"  cal={scal:.2f}: finding L1={l1:.4f} synth_err={err:.4f} "
            f"(target {target_err:.4f})")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"  chosen PA_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f})")

    # --- Stage 3: final refit generation ------------------------------------
    log("stage 3: final refit generation (n=20000, seed 7)...")
    install_constants(const, coin_cal=coin_cal)
    pa_state.PA_BUCKET_RATIO = copy.deepcopy(final_bucket)
    refit_path = gen_pa(OUT / "pa_refit.jsonl")
    l1, sm = finding_l1(refit_path, target)
    log(f"  refit finding L1 vs real PA FY20-22: {l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f})")

    # --- Stage 4: real PA test sets -----------------------------------------
    log("stage 4: loading real PA microdata...")
    real = pa2.load_pa_real(QC_DIR)
    log(f"  PA rows loaded: {len(real)}")
    test_2324 = {k: v for k, v in real.items() if k[0] in (2023, 2024)}
    test_2022 = {k: v for k, v in real.items() if k[0] in (2020, 2021, 2022)}
    log(f"  test FY23-24: {len(test_2324)} rows, "
        f"test FY20-22: {len(test_2022)} rows")

    # --- Stage 5: transfer battery ------------------------------------------
    log("stage 5: training GBM (no class_weight) on synth arms...")
    refit_synth = pa2.load_synth(refit_path)
    pooled_synth = pa2.load_synth(pooled_path)
    log(f"  refit synth {len(refit_synth)}, pooled synth {len(pooled_synth)}")

    def subset(rows, y_idx):
        if y_idx == 2:  # element: error cases with a labeled bucket
            return [r for r in rows if r[2] is not None]
        return rows

    all_buckets = sorted({r[2] for r in real.values() if r[2] is not None})
    results = {"arms": {}, "test_sets": {}}
    for tname, rows in (("FY23-24", test_2324), ("FY20-22", test_2022)):
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
        sX, sy = pa2.as_Xy(train_rows, y_idx)
        rX, ry = pa2.as_Xy(test_rows, y_idx)
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

    for arm_name, synth in (("T_refit (FY20-22 fit)", refit_synth),
                            ("T_pooled (PA1 as-is)", pooled_synth)):
        results["arms"][arm_name] = {}
        log(f"\n== {arm_name} ==")
        for tname, rows in (("FY23-24", test_2324), ("FY20-22", test_2022)):
            rd = list(rows.values())
            m_el = run_task(subset(synth, 2), subset(rd, 2), 2)
            m_fi = run_task(subset(synth, 1), subset(rd, 1), 1)
            results["arms"][arm_name][tname] = {"element": m_el, "finding": m_fi}
            log(f"  [{tname}] element: acc={m_el['acc']:.4f} "
                f"macroF1={m_el['macroF1']:.4f} (n_test={m_el['n_test']})")
            log(f"  [{tname}] finding: acc={m_fi['acc']:.4f} "
                f"macroF1={m_fi['macroF1']:.4f} (n_test={m_fi['n_test']})")

    # --- Stage 6: per-bucket decay diagnosis (refit arm, FY20-22 vs FY23-24) -
    log("\n== per-bucket F1: train-period (FY20-22) vs test-period (FY23-24), "
        "T_refit ==")
    el_22 = results["arms"]["T_refit (FY20-22 fit)"]["FY20-22"]["element"]
    el_24 = results["arms"]["T_refit (FY20-22 fit)"]["FY23-24"]["element"]
    decay = []
    for b in sorted(set(el_22["per_bucket_F1"]) | set(el_24["per_bucket_F1"])):
        f22 = el_22["per_bucket_F1"].get(b, 0.0)
        f24 = el_24["per_bucket_F1"].get(b, 0.0)
        decay.append({"bucket": b, "F1_FY20-22": f22, "F1_FY23-24": f24,
                      "delta": round(f24 - f22, 4)})
        log(f"  {b:18s} FY20-22 F1={f22:.3f}  FY23-24 F1={f24:.3f}  "
            f"delta={f24 - f22:+.3f}")
    results["bucket_decay"] = decay

    results["refit_meta"] = {
        "n_pa_rows_fit": t_fit["n_pa_rows"],
        "n_pa_rows_ref": t_ref["n_pa_rows"],
        "PA_COIN_CAL": coin_cal,
        "PA_BUCKET_RATIO": {b: round(v, 4) for b, v in final_bucket.items()},
        "calibration_multipliers": {b: round(v, 4) for b, v in cal.items()},
        "pure_empirical_bucket_ratios":
            {b: round(v, 4) for b, v in const["PA_BUCKET_RATIO"].items()},
        "fit_finding_mix": {k: round(v, 4) for k, v in
                             t_fit["pa"]["finding_mix"].items()},
        "test_finding_mix": {k: round(v, 4) for k, v in
                              t_ref["pa"]["finding_mix"].items()},
        "elapsed_s": round(time.time() - t0, 1),
    }
    outp = OUT / "pa6_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
