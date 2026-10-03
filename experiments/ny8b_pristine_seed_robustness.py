"""NY8b — pristine seed-robustness: does the +0.016 pristine finding-AUC edge
hold at seeds 8 and 9?

NY8 ran the pristine refit (NY offsets fit on NY microdata EXCLUDING the
815 holdout rows in experiments/ny2_holdout_idx.json) at seed 7 only:
finding binary AUC 0.6262 (NY no-classweight) vs 0.6107 (national
no-classweight), edge +0.016. NY2's contaminated edge held at all 3 seeds;
this checks the pristine gap isn't seed luck. NY8's own next-steps flagged
this as the open check.

Method: replicate NY8's recipe exactly at seeds 8 and 9. The pristine fit
(fit_ny_targets_excl) is deterministic and seed-independent, so it runs
once; per seed: NY1 it2 recipe (20k pilot at coin cal 1.0 -> one-step
realized-output bucket/97-resolution/direction calibrations -> NY_COIN_CAL
grid over {0.90, 0.93, 0.96, 1.0} on 8k pilots -> final 20k) and the
national arm regenerated per NY2's exact recipe at the same seed. Transfer
battery: NY2's recipe on the shared ny2_holdout_idx.json holdout — GBM
without class_weight (NY2's winning setting), finding task only, binary AUC
from P(error) = proba(2)+proba(3).

Usage (from repo root):
    python3 experiments/ny8b_pristine_seed_robustness.py
Results -> /tmp/ny8bout/ny8b_results.json (workspace scratch, not the repo).

Requires: scikit-learn. Microdata read-only at ~/workspace/snap-qc-data.
CPU only.
"""
import copy
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import ny8_ny_pristine_rerun as ny8  # noqa: E402
import ny2_ny_transfer as ny2  # noqa: E402
from src.synth import ny_state  # noqa: E402

QC_DIR = ny8.QC_DIR
HOLDOUT_JSON = ny8.HOLDOUT_JSON
DIST = ny8.DIST
OUT = Path("/tmp/ny8bout")
OUT.mkdir(exist_ok=True)
N_SYNTH = ny8.N_SYNTH
SEEDS = (8, 9)
FYS = ny8.FYS
SUPPORTED = ny8.SUPPORTED
GUARD_BUCKETS = ny8.GUARD_BUCKETS

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402


def pristine_fit_once(exclude):
    """Seed-independent pristine refit (NY8 stage 1). Returns (const, real_t, target_mix)."""
    t = ny8.fit_ny_targets_excl(QC_DIR, fys=FYS, exclude=exclude)
    const = ny8.fit_to_constants(t)
    real_t = ny8.real_ny_var_targets_excl(QC_DIR, FYS, exclude)
    return const, real_t, t["ny"]["finding_mix"]


def it2_recipe(const, real_t, target_mix, seed, tag, log):
    """NY8 stage 2 verbatim, parameterized by seed. Returns (ny_path, finding_l1, coin_cal)."""
    # 2a. pilot with pure refit ratios (coin cal 1.0) -> bucket calibration
    ny8.install_constants(const, coin_cal=1.0)
    pilot_path = ny8.gen_ny(OUT / f"{tag}_pilot.jsonl", seed=seed)
    synth_sh = ny8.synth_var_targets(pilot_path)
    real_sh = real_t["bucket"]
    cal = {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS:
            cal[b] = 1.0
        else:
            cal[b] = real_sh[b] / synth_sh["bucket"][b] if synth_sh["bucket"][b] > 0 else 1.0
    final_bucket = {b: const["NY_BUCKET_RATIO"][b] * cal[b] for b in SUPPORTED}

    # 2b. 97-resolution coins + non-97 direction margins (real/synth on pilot)
    res97, dir97 = {}, {}
    for b in SUPPORTED:
        if b in GUARD_BUCKETS:
            res97[b] = 1.0
            dir97[b] = {"over": 1.0, "under": 1.0}
            continue
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
    final_97 = {b: const["NY_97_RATIO"][b] * res97[b] for b in SUPPORTED}
    final_dir = {b: {"over": const["NY_DIR_RATIO"][b]["over"] * dir97[b]["over"],
                     "under": const["NY_DIR_RATIO"][b]["under"] * dir97[b]["under"]}
                 for b in SUPPORTED}
    ny_state.NY_BUCKET_RATIO = copy.deepcopy(final_bucket)
    ny_state.NY_97_RATIO = copy.deepcopy(final_97)
    ny_state.NY_DIR_RATIO = copy.deepcopy(final_dir)

    # 2c. coin-cal grid search (8k pilots) against pristine marginal rate
    best = None
    for scal in (0.90, 0.93, 0.96, 1.0):
        ny_state.NY_COIN_CAL = scal
        pp = ny8.gen_ny(OUT / f"{tag}_coin_{scal:.2f}.jsonl", n=8000, seed=seed)
        l1, _ = ny8.finding_l1(pp, target_mix)
        log(f"    cal={scal:.2f}: finding L1={l1:.4f}")
        if best is None or l1 < best[1]:
            best = (scal, l1)
    coin_cal = best[0]
    log(f"    chosen NY_COIN_CAL={coin_cal:.2f} (L1={best[1]:.4f})")

    # 2d. final pristine-NY generation
    ny8.install_constants(const, coin_cal=coin_cal)
    ny_state.NY_BUCKET_RATIO = copy.deepcopy(final_bucket)
    ny_state.NY_97_RATIO = copy.deepcopy(final_97)
    ny_state.NY_DIR_RATIO = copy.deepcopy(final_dir)
    ny_path = ny8.gen_ny(OUT / f"{tag}_ny_pristine.jsonl", seed=seed)
    l1, sm = ny8.finding_l1(ny_path, target_mix)
    log(f"    final: finding L1={l1:.4f} "
        f"(synth c/o/u {sm[1]:.4f}/{sm[2]:.4f}/{sm[3]:.4f})")
    return ny_path, l1, coin_cal


def gen_national_seed(out, seed):
    """NY2's exact national recipe at the given seed."""
    subprocess.run(
        [sys.executable, "-m", "synth.generate", "--n", str(N_SYNTH),
         "--seed", str(seed), "--dist", "../experiments/dist.json",
         "--max-attempts", "12", "--out", str(out)],
        check=True, cwd=str(ROOT / "src"))


def finding_auc(synth_rows, test_rows):
    sX, sy = ny2.as_Xy(synth_rows, 1)
    rX, ry = ny2.as_Xy(test_rows, 1)
    clf = HistGradientBoostingClassifier(random_state=0)  # no class_weight: NY2's winner
    clf.fit(sX, sy)
    proba = clf.predict_proba(rX)
    cls = list(clf.classes_)
    p_err = sum(proba[:, cls.index(c)] for c in (2, 3))
    y_bin = [0 if y == 1 else 1 for y in ry]
    return round(float(roc_auc_score(y_bin, p_err)), 4)


def main():
    t0 = time.time()
    log = lambda *a: print(*a, flush=True)

    saved = json.loads(Path(HOLDOUT_JSON).read_text())
    exclude = {(k[0], k[1]) for k in saved["holdout_keys"]}
    log(f"holdout keys: {len(exclude)}")

    log("pristine refit (seed-independent, run once)...")
    const, real_t, target_mix = pristine_fit_once(exclude)

    real = ny2.load_ny_real(QC_DIR)
    holdout_keys = [tuple(k) for k in saved["holdout_keys"]]
    test_finding = [real[k] for k in holdout_keys]
    log(f"test rows: {len(test_finding)}")

    results = {"seeds": {}, "setting": "no-classweight",
               "holdout": HOLDOUT_JSON, "n": N_SYNTH}
    for seed in SEEDS:
        log(f"\n=== seed {seed} ===")
        tag = f"ny8b_s{seed}"
        log("  it2 recipe on pristine fit...")
        ny_path, l1, coin_cal = it2_recipe(const, real_t, target_mix, seed, tag, log)
        log("  national arm (NY2 recipe)...")
        nat_path = OUT / f"{tag}_nat_synth.jsonl"
        gen_national_seed(nat_path, seed)
        log("  battery (finding, GBM no-cw)...")
        ny_synth = ny2.load_synth(str(ny_path))
        nat_synth = ny2.load_synth(str(nat_path))
        auc_ny = finding_auc(ny_synth, test_finding)
        auc_nat = finding_auc(nat_synth, test_finding)
        edge = round(auc_ny - auc_nat, 4)
        log(f"  seed {seed}: NY no-cw AUC={auc_ny:.4f} vs national no-cw AUC={auc_nat:.4f} "
            f"-> edge {edge:+.4f} ({'HOLDS' if edge > 0 else 'DOES NOT HOLD'})")
        results["seeds"][seed] = {
            "ny_auc": auc_ny, "nat_auc": auc_nat, "edge": edge,
            "pristine_finding_L1": round(l1, 4), "NY_COIN_CAL": coin_cal,
            "ny_synth": str(ny_path), "nat_synth": str(nat_path),
        }

    outp = OUT / "ny8b_results.json"
    outp.write_text(json.dumps(results, indent=2))
    log(f"\nresults -> {outp} ({time.time()-t0:.0f}s)")
    for seed in SEEDS:
        r = results["seeds"][seed]
        log(f"seed {seed}: edge {r['edge']:+.4f}")


if __name__ == "__main__":
    main()
