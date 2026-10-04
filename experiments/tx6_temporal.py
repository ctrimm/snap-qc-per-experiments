"""TX6 — temporal stability: does the TX transfer signal hold year to year?

Refit the TX conditioning on FY2020-2022 TX microdata only (TX1's offsets
were pooled FY2020-2024), generate TX-conditioned synthetic with the refit
offsets, train element + finding classifiers per PA2's recipe
(TX-conditioned synthetic + GBM without class_weight), and test on
FY2023-2024 real TX cases held out entirely from fitting and training.

Comparison arms:
  T_refit: FY2020-22-fit TX synth, tested on FY2023-24 real TX (clean
           temporal test) AND on FY2020-22 real TX (train-period reference).
  T_pooled: pooled-fit TX synth (TX1 as-is), tested on the same two sets
           (does refitting on old years matter?).
  reference: PA6-style approximate reference — quoted PA2/PA6 headline
           numbers (PA, not TX; NY2 does not exist yet) for orientation only.
  train-period check: per-bucket F1 decay diagnosis on the T_refit arm
           (FY20-22 -> FY23-24) with test-set ns.

Year filtering: tx1_tx_generator's `fit` CLI subcommand has no --fys flag
(it always fits pooled). This script applies the filter by calling
fit_tx_targets(qc_dir, fys=[2020, 2021, 2022]) directly and documenting the
gap here.

Refit pipeline (mirrors TX1's it2 recipe):
  1. pure-empirical FY2020-22 offset ratios (same guards as TX1:
     sparsity guard TX unweighted n<25 -> 1.0);
  2. one-step realized-output bucket calibration x real_TX_share/synth_share
     on a 20k-case pilot (TX1's it2);
  3. TX_COIN_CAL line search over TX1's grid {0.90, 0.93, 0.96, 1.0} against
     the marginal TX FY2020-22 case-error rate on 8k-case pilots;
  4. final 20k generation, seed 7 (NY2's n/seed conventions).

Refit constants are installed by monkey-patching src.synth.tx_state module
attributes (no src file is modified; all generator functions read these
globals at call time). The pooled arm is generated first, before any
patching, so it is TX1's as-is output.

exp34 codebook caution handled: nature/cause offsets are pinned to the
FY2024 dist.json convention (the generator's national base), and TX's
per-FY nature-97 cause-blank rate is checked for labeling breaks (TX1 found
TX blanks 21.9% of 97-causes pooled — checked per-FY here). The
element/finding labels (STATUS, ELEMENT codes) are stable across the window.

FY2021 sensitivity: FY2021 is a partial-year file (Jul-Sep, n=221, ~14.6%
of the fit). The fit is also recomputed excluding FY2021 (fys=[2020, 2022])
and run through the same refit recipe, quantifying its influence on the
coin scalar (PA6's analog).

Usage (from repo root):
    python3 experiments/tx6_temporal.py
Results -> /tmp/tx6out/tx6_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at ~/workspace/snap-qc-data.
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

from src.synth import tx_state  # noqa: E402
import tx1_tx_generator as tx1  # noqa: E402
import tx2_tx_transfer as tx2  # noqa: E402
from src.synth.codebook import element_bucket  # noqa: E402

QC_DIR = str(Path.home() / "workspace" / "snap-qc-data" / "raw")
DIST = str(ROOT / "experiments" / "dist.json")
OUT = Path("/tmp/tx6out")
OUT.mkdir(exist_ok=True)
N_SYNTH = 20000
SEED = 7
SUPPORTED = tx1.SUPPORTED
COIN_GRID = (0.94, 0.96, 0.98, 1.00, 1.02)  # TX1's grid (widened: TX1's it2 searched upward)

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402


def gbm():
    return HistGradientBoostingClassifier(random_state=0)


# ---------------------------------------------------------------- helpers

def fit_to_constants(t):
    """Convert fit_tx_targets output (FY-filtered) into tx_state constant
    overrides with the same guards TX1 used. Pure-empirical (no realized-
    output calibration, no coin scalar)."""
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
    """Monkey-patch tx_state module constants (read at call time)."""
    for name, val in const.items():
        setattr(tx_state, name, copy.deepcopy(val))
    tx_state.TX_COIN_CAL = coin_cal


def gen_tx(out, n=N_SYNTH, seed=SEED):
    tx_state.generate_tx(n=n, seed=seed, dist=DIST, out=str(out))
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


def real_tx_var_shares(qc_dir, fys):
    """Real TX variance-level bucket shares, FYWGT-weighted, SUPPORTED only,
    on the generator's recorded basis (FY-filtered port of TX1's
    _real_tx_var_mixes)."""
    bucket = Counter()
    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "48" or row["STATUS"].strip() not in ("2", "3"):
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


def tx_cause97_blank_by_fy(qc_dir, fys):
    """FYWGT-weighted share of TX nature-97 variances with blank AGENCY,
    per FY (exp34 labeling-break check)."""
    out = {}
    for fy in fys:
        blank = tot = 0.0
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"] != "48" or row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = tx1.fnum(row.get("FYWGT"), 1.0)
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


def load_tx_real(qc_dir, fys):
    """TX rows across the given FY files. Key: (fy, ny-relative row idx).
    Mirrors tx2_tx_transfer.load_pa_real with STATE='36'. v1 features are
    PA2's raw agency-view set (ported, state-agnostic)."""
    rows = {}
    for fy in fys:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")), None)
        if path is None:
            raise FileNotFoundError(f"no csv under qcfy{fy}_csv")
        with open(path, newline="") as fh:
            tx_idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != "48":
                    continue
                status = row["STATUS"].strip()
                e1 = row.get("ELEMENT1", "").strip()
                bucket = element_bucket(int(e1)) if (e1 and status != "1") else None
                rows[(fy, tx_idx)] = (
                    tx2.real_row_features(row),
                    int(status),
                    bucket,
                )
                tx_idx += 1
    return rows


def refit_recipe(t_fit, name, log):
    """Run TX1's it2 recipe on a fit output: pure-empirical constants ->
    20k pilot -> realized-output bucket calibration -> TX_COIN_CAL line
    search on 8k pilots. Returns (final_bucket, cal_multipliers,
    chosen_coin_cal, final_path, refit_finding_l1)."""
    const = fit_to_constants(t_fit)
    log(f"  [{name}] pure-empirical bucket ratios:",
        {b: round(const["TX_BUCKET_RATIO"][b], 3) for b in SUPPORTED})

    install_constants(const, coin_cal=1.0)
    pilot_path = gen_tx(OUT / f"tx_{name}_pilot.jsonl")
    synth_sh = synth_bucket_shares(pilot_path)
    real_sh = real_tx_var_shares(QC_DIR, FIT_FYS[name])
    cal = {}
    for b in SUPPORTED:
        if const["TX_BUCKET_RATIO"][b] == 1.0:
            cal[b] = 1.0  # same sparsity guard as TX1 (guarded -> 1.0)
        else:
            cal[b] = real_sh[b] / synth_sh[b] if synth_sh[b] > 0 else 1.0
    final_bucket = {b: const["TX_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}
    log(f"  [{name}] calibration multipliers:",
        {b: round(cal[b], 3) for b in SUPPORTED if cal[b] != 1.0})
    log(f"  [{name}] calibrated bucket ratios:",
        {b: round(final_bucket[b], 3) for b in SUPPORTED})

    tx_state.TX_BUCKET_RATIO = copy.deepcopy(final_bucket)
    target = t_fit["tx"]["finding_mix"]
    target_err = t_fit["tx"]["case_err_rate"]
    best = None
    for scal in COIN_GRID:
        tx_state.TX_COIN_CAL = scal
        p = gen_tx(OUT / f"tx_{name}_coin_{scal:.2f}.jsonl", n=8000)
        l1, sm = finding_l1(p, target)
        err = sm[2] + sm[3]
        log(f"  [{name}] cal={scal:.2f}: finding L1={l1:.4f} "
            f"synth_err={err:.4f} (target {target_err:.4f})")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"  [{name}] chosen TX_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f})")

    install_constants(const, coin_cal=coin_cal)
    tx_state.TX_BUCKET_RATIO = copy.deepcopy(final_bucket)
    final_path = gen_tx(OUT / f"tx_{name}.jsonl")
    l1, sm = finding_l1(final_path, target)
    log(f"  [{name}] refit finding L1 vs real TX "
        f"{'/'.join(str(f) for f in FIT_FYS[name])}: {l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f})")
    return final_bucket, cal, coin_cal, final_path, l1, const


FIT_FYS = {
    "refit": [2020, 2021, 2022],
    "excl21": [2020, 2022],
}


def main():
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    # --- Stage 0: fits ------------------------------------------------------
    log("stage 0: fitting targets (FY2020-22 fit / excl-FY2021 / FY2023-24 ref)...")
    t_fit = tx1.fit_tx_targets(QC_DIR, fys=FIT_FYS["refit"])
    t_excl = tx1.fit_tx_targets(QC_DIR, fys=FIT_FYS["excl21"])
    t_ref = tx1.fit_tx_targets(QC_DIR, fys=[2023, 2024])
    log(f"  TX rows: fit FY2020-22 n={t_fit['n_tx_rows']}, "
        f"excl21 n={t_excl['n_tx_rows']}, ref FY2023-24 n={t_ref['n_tx_rows']}")
    for label, t in (("fit  FY20-22", t_fit), ("excl FY21   ", t_excl),
                     ("test FY23-24", t_ref)):
        p, q = t["tx"], t["nat"]
        log(f"  {label}: TX finding c/o/u "
            f"{p['finding_mix']['1']:.4f}/{p['finding_mix']['2']:.4f}/"
            f"{p['finding_mix']['3']:.4f} "
            f"case_err {p['case_err_rate']:.4f} p_over|err {p['p_over_given_err']:.4f} "
            f"cause97_blank {t['tx_cause97_blank']:.4f} "
            f"(nat case_err {q['case_err_rate']:.4f})")

    # --- Stage 0b: per-FY labeling-break check --------------------------------
    log("stage 0b: TX nature-97 cause-blank rate per FY...")
    blanks = tx_cause97_blank_by_fy(QC_DIR, [2020, 2021, 2022, 2023, 2024])
    log("  per-FY blank share:", blanks)

    # --- Stage 1a: pooled arm first (unpatched, TX1 as-is) -------------------
    log("stage 1a: generating pooled-fit TX synth (n=20000, seed 7)...")
    pooled_path = gen_tx(OUT / "tx_pooled.jsonl")

    # --- Stages 1b-3: refit recipes ------------------------------------------
    log("stage 1b-3: refit recipe on FY20-22 fit...")
    final_bucket, cal, coin_cal, refit_path, l1_refit, const = \
        refit_recipe(t_fit, "refit", log)
    log("stage 1b-3: refit recipe excluding FY2021 (sensitivity arm)...")
    ex_bucket, ex_cal, ex_coin, ex_path, l1_ex, ex_const = \
        refit_recipe(t_excl, "excl21", log)

    # --- Stage 4: real TX test sets -----------------------------------------
    log("stage 4: loading real TX microdata...")
    real = load_tx_real(QC_DIR, [2020, 2021, 2022, 2023, 2024])
    log(f"  TX rows loaded: {len(real)}")
    test_2324 = {k: v for k, v in real.items() if k[0] in (2023, 2024)}
    test_2022 = {k: v for k, v in real.items() if k[0] in (2020, 2021, 2022)}
    log(f"  test FY23-24: {len(test_2324)} rows, "
        f"test FY20-22: {len(test_2022)} rows")

    # --- Stage 5: transfer battery ------------------------------------------
    log("stage 5: training GBM (no class_weight) on synth arms...")
    refit_synth = tx2.load_synth(refit_path)
    pooled_synth = tx2.load_synth(pooled_path)
    excl_synth = tx2.load_synth(ex_path)
    log(f"  refit synth {len(refit_synth)}, pooled synth {len(pooled_synth)}, "
        f"excl21 synth {len(excl_synth)}")

    def subset(rows, y_idx):
        if y_idx == 2:  # element: error cases with a labeled bucket
            return [r for r in rows if r[2] is not None]
        return rows

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
        sX, sy = tx2.as_Xy(train_rows, y_idx)
        rX, ry = tx2.as_Xy(test_rows, y_idx)
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
                            ("T_pooled (TX1 as-is)", pooled_synth),
                            ("T_excl21 (FY20+22 fit)", excl_synth)):
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
    ns_22 = results["test_sets"]["FY20-22"]["element_labels"]
    ns_24 = results["test_sets"]["FY23-24"]["element_labels"]
    decay = []
    for b in sorted(set(el_22["per_bucket_F1"]) | set(el_24["per_bucket_F1"])):
        f22 = el_22["per_bucket_F1"].get(b, 0.0)
        f24 = el_24["per_bucket_F1"].get(b, 0.0)
        decay.append({"bucket": b, "F1_FY20-22": f22, "F1_FY23-24": f24,
                      "delta": round(f24 - f22, 4),
                      "n_FY20-22": ns_22.get(b, 0), "n_FY23-24": ns_24.get(b, 0)})
        log(f"  {b:18s} FY20-22 F1={f22:.3f} (n={ns_22.get(b,0)})  "
            f"FY23-24 F1={f24:.3f} (n={ns_24.get(b,0)})  delta={f24 - f22:+.3f}")
    results["bucket_decay"] = decay

    results["refit_meta"] = {
        "n_tx_rows_fit": t_fit["n_tx_rows"],
        "n_tx_rows_excl21": t_excl["n_tx_rows"],
        "n_tx_rows_ref": t_ref["n_tx_rows"],
        "TX_COIN_CAL": coin_cal,
        "TX_COIN_CAL_EXCL21": ex_coin,
        "TX_BUCKET_RATIO": {b: round(v, 4) for b, v in final_bucket.items()},
        "calibration_multipliers": {b: round(v, 4) for b, v in cal.items()},
        "pure_empirical_bucket_ratios":
            {b: round(v, 4) for b, v in const["TX_BUCKET_RATIO"].items()},
        "fit_finding_mix": {k: round(v, 4) for k, v in
                             t_fit["tx"]["finding_mix"].items()},
        "excl_finding_mix": {k: round(v, 4) for k, v in
                              t_excl["tx"]["finding_mix"].items()},
        "test_finding_mix": {k: round(v, 4) for k, v in
                              t_ref["tx"]["finding_mix"].items()},
        "cause97_blank_per_fy": blanks,
        "refit_finding_L1": round(l1_refit, 4),
        "elapsed_s": round(time.time() - t0, 1),
    }
    outp = OUT / "tx6_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
