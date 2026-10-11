"""Exp 81 — loop 3, tier A: automatic calibration of the PA generator's knobs.

Can an automatic search over the PA generator's numeric settings match or beat
the hand-built PA1 generator on the transfer test it was built for (PA2)?

Pre-registered (this docstring, committed before running):
  Knobs (13, all in src/synth/pa_state.py, patched in memory only; the module
  file is never edited): PA_COIN_CAL; PA_COIN_RATIO earner / no_earner;
  PA_BUCKET_RATIO for the 8 buckets; PA_S_OVER; PA_S_UNDER. Each searched as
  a multiplier on its PA1 value, bounded to [1/3, 3].
  Candidate evaluation: generate 8,000 PA synthetic cases (seed 7, the same
  for every candidate), train PA2's arm (b) classifier (HistGradientBoosting,
  no class weights, PA2 V1 features) and score on REAL PA dev rows = PA2's
  training split (the PA2 holdout stays locked):
    objective   element macro-F1 (error rows with an element label)
    constraints finding-mix L1 and element-mix L1 (synthetic vs real dev) no
                worse than PA1's by more than 0.01 and 0.02
  Search: (1+6) evolution strategy, log-normal steps (sigma 0.12, 1/5th-rule
  adaptation), a child replaces the parent only if it satisfies the
  constraints and improves the objective by more than 0.002. Stops at 60
  generations (360 candidates) or 06:30, whichever comes first.
  Final check (once): PA1 vs the best knobs on (1) dev, 3 fresh seeds
  (11-13); (2) the locked PA2 holdout, 20,000 cases, seed 7, as PA2 ran it:
  element macro-F1 and finding accuracy.
  Verdict: "matches or beats PA1" if the best knobs' holdout element macro-F1
  >= PA1's and finding accuracy is no more than 0.01 lower, and the dev gain
  holds on the fresh seeds (mean > PA1). The loop never changes generator
  defaults: winning knobs are written to exp81_best_knobs.json for review.

exp81b (--seeds 3, pre-registered 2026-10-10 after exp81 chased single-seed
noise): each candidate scored as the mean over seeds 7, 8, 9; a child must
improve the parent by more than 0.005; the final check uses 5 fresh seeds
(21-25) plus the locked holdout as before; results to exp81b_*.json.

Usage: python3 experiments/exp81_generator_autocal_pa.py [--workers 6] [--seeds 3]
"""
import argparse
import copy
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "experiments")]
DEADLINE = datetime.datetime.now().replace(hour=6, minute=30, second=0, microsecond=0) + datetime.timedelta(days=1)

_G = {}


def knob_base():
    import src.synth.pa_state as P
    v = {"COIN_CAL": P.PA_COIN_CAL, "COIN_earner": P.PA_COIN_RATIO["earner"], "COIN_no_earner": P.PA_COIN_RATIO["no_earner"],
         "S_OVER": P.PA_S_OVER, "S_UNDER": P.PA_S_UNDER}
    for b, x in P.PA_BUCKET_RATIO.items():
        v[f"BUCKET_{b}"] = x
    return v


def apply_knobs(mult):
    import src.synth.pa_state as P
    if "orig" not in _G:
        _G["orig"] = (P.PA_COIN_CAL, copy.deepcopy(P.PA_COIN_RATIO), P.PA_S_OVER, P.PA_S_UNDER, copy.deepcopy(P.PA_BUCKET_RATIO))
    cal, coin, so, su, br = _G["orig"]
    P.PA_COIN_CAL = cal * mult["COIN_CAL"]
    P.PA_COIN_RATIO = {"earner": coin["earner"] * mult["COIN_earner"], "no_earner": coin["no_earner"] * mult["COIN_no_earner"]}
    P.PA_S_OVER = so * mult["S_OVER"]; P.PA_S_UNDER = su * mult["S_UNDER"]
    P.PA_BUCKET_RATIO = {b: x * mult[f"BUCKET_{b}"] for b, x in br.items()}


def init_worker():
    import pa2_pa_transfer as T
    real = T.load_pa_real(str(ROOT.parent / "snap-qc-data/raw"))
    hold = {tuple(k) for k in json.loads((ROOT / "experiments/pa2_holdout_idx.json").read_text())["holdout_keys"]}
    _G["dev"] = [real[k] for k in sorted(real) if k not in hold]
    _G["test"] = [real[k] for k in sorted(real) if k in hold]


def mixes(rows):
    fin = np.array([sum(r[1] == s for r in rows) for s in (1, 2, 3)], float); fin /= fin.sum()
    err = [r[2] for r in rows if r[2] is not None]
    keys = ["earned", "unearned", "shelter", "sua", "medical", "depcare", "hhcomp", "arithmetic"]
    el = np.array([sum(b == k for b in err) for k in keys] + [sum(b not in keys for b in err)], float); el /= max(el.sum(), 1)
    return fin, el


def evaluate(args):
    mult, seed, n, split = args
    if "dev" not in _G:
        init_worker()
    import pa2_pa_transfer as T
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score
    from src.synth.pa_state import generate_pa
    apply_knobs(mult)
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        path = tf.name
    try:
        generate_pa(n=n, seed=seed, dist=str(ROOT / "experiments/dist.json"), out=path)
        syn = T.load_synth(path)
    finally:
        os.unlink(path)
    real = _G[split]
    se = [r for r in syn if r[2] is not None]; re_ = [r for r in real if r[2] is not None]
    X, y = T.as_Xy(se, 2); Xr, yr = T.as_Xy(re_, 2)
    pe = HistGradientBoostingClassifier(random_state=0).fit(X, y).predict(Xr)
    Xf, yf = T.as_Xy(syn, 1); Xrf, yrf = T.as_Xy(real, 1)
    pf = HistGradientBoostingClassifier(random_state=0).fit(Xf, yf).predict(Xrf)
    fs, es = mixes(syn); fr, er = mixes(real)
    return {"element_macroF1": float(f1_score(yr, pe, average="macro", zero_division=0)),
            "finding_acc": float(accuracy_score(yrf, pf)),
            "finding_L1": float(np.abs(fs - fr).sum()), "element_L1": float(np.abs(es - er).sum())}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seeds", type=int, default=1); args = ap.parse_args()
    seeds = [7, 8, 9][: args.seeds]; thr = 0.002 if args.seeds == 1 else 0.005
    fresh = (11, 12, 13) if args.seeds == 1 else (21, 22, 23, 24, 25)
    tag = "exp81" if args.seeds == 1 else "exp81b"

    def score_many(pool, kids):
        flat = pool.map(evaluate, [(k, s, 8000, "dev") for k in kids for s in seeds])
        out = []
        for i in range(len(kids)):
            rs = flat[i * len(seeds):(i + 1) * len(seeds)]
            out.append({m: float(np.mean([r[m] for r in rs])) for m in rs[0]})
        return out
    os.environ["OMP_NUM_THREADS"] = "2"
    from multiprocessing import get_context
    base_vals = knob_base(); names = list(base_vals)
    ones = {k: 1.0 for k in names}
    log = []
    with get_context("spawn").Pool(args.workers) as pool:
        base = score_many(pool, [ones])[0]
        print(f"PA1 baseline (dev, seeds {seeds}): {base}", flush=True)
        lim_f, lim_e = base["finding_L1"] + 0.01, base["element_L1"] + 0.02
        parent, pscore, sigma = dict(ones), base["element_macroF1"], 0.12
        rng = np.random.RandomState(81)
        for gen in range(60):
            if datetime.datetime.now() > DEADLINE:
                print("deadline reached", flush=True); break
            kids = []
            for _ in range(args.workers):
                kid = {k: float(np.clip(parent[k] * np.exp(sigma * rng.randn()), 1 / 3, 3)) for k in names}
                kids.append(kid)
            res = score_many(pool, kids)
            ok = [(r["element_macroF1"], k, r) for k, r in zip(kids, res)
                  if r["finding_L1"] <= lim_f and r["element_L1"] <= lim_e]
            best = max(ok, key=lambda t: t[0]) if ok else None
            improved = best is not None and best[0] > pscore + thr
            if improved:
                parent, pscore = best[1], best[0]
            sigma *= 1.22 if improved else 0.96
            sigma = float(np.clip(sigma, 0.02, 0.5))
            log.append({"gen": gen, "best_child": max(r["element_macroF1"] for r in res), "feasible": len(ok),
                        "parent_score": pscore, "sigma": sigma, "improved": improved})
            print(f"gen {gen:2d}: best child {log[-1]['best_child']:.4f} | feasible {len(ok)}/{len(kids)} | "
                  f"parent {pscore:.4f} | sigma {sigma:.3f}{' *' if improved else ''}", flush=True)
            (ROOT / f"experiments/{tag}_log.json").write_text(json.dumps({"baseline": base, "log": log, "parent": parent}, indent=1))
        print("final check", flush=True)
        dev_b = pool.map(evaluate, [(ones, s, 8000, "dev") for s in fresh])
        dev_p = pool.map(evaluate, [(parent, s, 8000, "dev") for s in fresh])
        hb, hp = pool.map(evaluate, [(ones, 7, 20000, "test"), (parent, 7, 20000, "test")])
    mean = lambda rs, k: float(np.mean([r[k] for r in rs]))
    verdict = (hp["element_macroF1"] >= hb["element_macroF1"] and hp["finding_acc"] >= hb["finding_acc"] - 0.01
               and mean(dev_p, "element_macroF1") > mean(dev_b, "element_macroF1"))
    out = {"baseline_dev_seed7": base, "best_multipliers": parent,
           "best_knob_values": {k: base_vals[k] * parent[k] for k in names},
           "dev_fresh_seeds": {"PA1": dev_b, "best": dev_p}, "holdout": {"PA1": hb, "best": hp},
           "matches_or_beats_PA1": verdict, "generations": len(log)}
    (ROOT / f"experiments/{tag}_results.json").write_text(json.dumps(out, indent=1))
    if verdict:
        (ROOT / f"experiments/{tag}_best_knobs.json").write_text(json.dumps(out["best_knob_values"], indent=1))
    print(f"dev fresh seeds element macro-F1: PA1 {mean(dev_b, 'element_macroF1'):.4f} vs best {mean(dev_p, 'element_macroF1'):.4f}")
    print(f"HOLDOUT element macro-F1: PA1 {hb['element_macroF1']:.4f} vs best {hp['element_macroF1']:.4f} | "
          f"finding acc PA1 {hb['finding_acc']:.4f} vs best {hp['finding_acc']:.4f} | verdict {verdict}")


if __name__ == "__main__":
    main()
