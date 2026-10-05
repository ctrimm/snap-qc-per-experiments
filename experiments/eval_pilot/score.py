"""Scorer for the QC-variance eval pilot (exp30).

Per-task metrics (primary metric first):
  T1 detection : macroF1 (secondary: accuracy)
  T2 finding   : macroF1 (secondary: accuracy)
  T3 element   : macroF1 (secondary: accuracy + per-bucket F1)
  T4 nature    : macroF1 (secondary: accuracy)
  T5 cause     : macroF1 (secondary: accuracy)
  T6 dollar    : direction accuracy (secondary: MAE, tolerance-band credits,
                 exact-match rate)

Composite = mean over T1-T5 of (model - dummy) / (ceiling - dummy),
clipped to [0, 1]. Ceilings: real->real macroF1 where published
(T2 0.832, T3 0.422); 1.0 elsewhere (placeholder, flagged in output).

Eval v1.1 (exp30 v1 run + cap test): T6 is scored and reported but left
out of the composite and the win count -- with RAWBEN withheld no model
tested beats the always-$0 dummy on it. Runs use max_tokens 1500.

Gate check (exp17 section 5), model vs its own base (--base-preds):
  1. composite strictly higher, 95% paired-bootstrap CI excludes zero
     (10k resamples over items);
  2. wins on >= 4 of the 5 composite tasks (per-task bootstrap CI
     excludes zero; was >= 4 of 6 in v1);
  3. T3 macroF1 >= 0.214 (GBM synth->real floor).
--ref-preds additionally reports composite vs a reference model (e.g. the
untuned 31B); informational only, not part of PASS.

Usage:
  python3 score.py --items items.json --preds preds.jsonl --out scores.json
  python3 score.py --items items.json --preds tuned.jsonl \\
      --base-preds base.jsonl --out gate.json
  python3 score.py --items items.json --preds tuned.jsonl \\
      --base-preds base.jsonl --ref-preds ref_31b.jsonl --out gate.json
  python3 score.py --items items.json --dummy --out baselines.json
  python3 score.py --items items.json --preds preds.jsonl --split test_2024

Prediction file format (JSONL): {"item_id": ..., "parsed": {"t1":..,"t2":..,
"t3":..,"t4":..,"t5":..,"t6":..}}. Unparseable/missing -> counted wrong
(parse failures are model failures, not abstentions).
"""

import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import labels as L  # noqa: E402

T2_REAL2REAL_MACROF1 = 0.832
T3_REAL2REAL_MACROF1 = 0.422
CEILINGS = {"t1": 1.0, "t2": T2_REAL2REAL_MACROF1, "t3": T3_REAL2REAL_MACROF1,
            "t4": 1.0, "t5": 1.0, "t6": 1.0}
T3_GBM_FLOOR = 0.214
BOOTSTRAP_B = 10000
EVAL_VERSION = "v1.1"
TASKS = ("t1", "t2", "t3", "t4", "t5", "t6")
COMPOSITE_TASKS = ("t1", "t2", "t3", "t4", "t5")  # v1.1: T6 reported only


# ---------------------------------------------------------------- metrics

def accuracy(pairs):
    if not pairs:
        return float("nan")
    return sum(1 for p, t in pairs if p == t) / len(pairs)


def macro_f1(pairs, classes):
    if not pairs:
        return float("nan")
    f1s = []
    for c in classes:
        tp = sum(1 for p, t in pairs if p == c and t == c)
        fp = sum(1 for p, t in pairs if p == c and t != c)
        fn = sum(1 for p, t in pairs if p != c and t == c)
        denom = 2 * tp + fp + fn
        f1s.append(0.0 if denom == 0 else 2 * tp / denom)
    return sum(f1s) / len(f1s)


def per_class_f1(pairs, classes):
    out = {}
    for c in classes:
        tp = sum(1 for p, t in pairs if p == c and t == c)
        fp = sum(1 for p, t in pairs if p == c and t != c)
        fn = sum(1 for p, t in pairs if p != c and t == c)
        denom = 2 * tp + fp + fn
        out[c] = 0.0 if denom == 0 else 2 * tp / denom
    return out


def sign3(v):
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def t6_band_credit(pred, true):
    """Tolerance-band partial credit: exact=1, +/-$10=0.5, +/-10%=0.25."""
    if pred is None or true is None:
        return 0.0
    try:
        p, t = float(pred), float(true)
    except (TypeError, ValueError):
        return 0.0
    d = abs(p - t)
    if d < 0.5:
        return 1.0
    if d <= 10:
        return 0.5
    if t != 0 and d <= 0.10 * abs(t):
        return 0.25
    return 0.0


# ---------------------------------------------------------------- loading

def load_items(path, splits):
    with open(path) as fh:
        items = json.load(fh)
    return [it for it in items if it["split"] in splits]


def load_preds(path):
    """Merge per-kind records ({item_id, kind, parsed}) into one parsed dict."""
    preds = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                d = preds.setdefault(r["item_id"], {})
                # run_lm.py writes "UNPARSEABLE"; normalize to None (= wrong)
                d.update({k: (None if v == "UNPARSEABLE" else v)
                          for k, v in r.get("parsed", {}).items()})
    return preds


def task_pairs(items, preds, task):
    """(pred, true) pairs; unparseable pred -> wrong (pred=None never equals)."""
    pairs = []
    for it in items:
        true = it["labels"][task]
        if true is None:
            continue
        pred = preds.get(it["item_id"], {}).get(task)
        if task == "t4" and pred is not None:
            pred = str(pred)
        pairs.append((pred, true))
    return pairs


# ---------------------------------------------------------------- scoring

def score_task(task, pairs):
    if task == "t6":
        dacc = sum(1 for p, t in pairs if sign3(p) == sign3(t)) / len(pairs)
        # unparseable prediction (p=None) penalized as |t|, i.e. as predicting 0
        mae = sum(abs((float(p) if p is not None else 0.0) - float(t))
                  for p, t in pairs) / len(pairs)
        bands = [t6_band_credit(p, t) for p, t in pairs]
        return {
            "n": len(pairs),
            "direction_accuracy": dacc,
            "mae": mae,
            "band_credit_mean": sum(bands) / len(bands),
            "exact_match_rate": sum(1 for b in bands if b == 1.0) / len(bands),
            "primary": dacc,
        }
    classes = L.TASKS[task]["values"]
    return {
        "n": len(pairs),
        "macro_f1": macro_f1(pairs, classes),
        "accuracy": accuracy(pairs),
        "per_class_f1": per_class_f1(pairs, classes),
        "primary": macro_f1(pairs, classes),
    }


def dummy_preds(items):
    """Most-frequent-class dummy (T6: constant median label)."""
    out = {}
    for task in ("t1", "t2", "t3", "t4", "t5"):
        vals = [it["labels"][task] for it in items if it["labels"][task] is not None]
        mf = Counter(vals).most_common(1)[0][0] if vals else None
        for it in items:
            out.setdefault(it["item_id"], {})[task] = mf
    t6vals = sorted(it["labels"]["t6"] for it in items)
    med = t6vals[len(t6vals) // 2] if t6vals else 0
    for it in items:
        out.setdefault(it["item_id"], {})["t6"] = med
    return out


def composite(task_scores, dummy_scores):
    parts = {}
    for t in COMPOSITE_TASKS:
        m, d, c = task_scores[t]["primary"], dummy_scores[t]["primary"], CEILINGS[t]
        parts[t] = min(1.0, max(0.0, (m - d) / (c - d))) if c > d else 0.0
    return sum(parts.values()) / len(parts), parts


# ---------------------------------------------------------------- fast bootstrap
# Integer-coded paired bootstrap (stdlib only). Replaces the naive version
# above for the 10k-resample gate: _bootstrap_gate_fast is what main() calls.


def _codes(items, preds, task):
    """Integer-coded (pred, true) arrays.

    pred codes: class index, or n_classes for missing/unparseable (never
    matches a true code). Returns (pred_codes, true_codes, n).
    """
    if task == "t6":
        pc, tc = [], []
        for it in items:
            t = it["labels"]["t6"]
            p = preds.get(it["item_id"], {}).get("t6")
            tc.append(sign3(t))
            pc.append(sign3(p) if p is not None and p != "UNPARSEABLE" else 9)
        return pc, tc, len(tc)
    classes = L.TASKS[task]["values"]
    cidx = {c: i for i, c in enumerate(classes)}
    pc, tc = [], []
    for it in items:
        t = it["labels"][task]
        if t is None:
            continue
        p = preds.get(it["item_id"], {}).get(task)
        if task == "t4" and p is not None:
            p = str(p)
        tc.append(cidx[t])
        pc.append(cidx.get(p, len(classes)))
    return pc, tc, len(tc)


def _macro_f1_codes(pc, tc, n_classes, idx):
    tp = [0] * n_classes
    fp = [0] * n_classes
    fn = [0] * n_classes
    for i in idx:
        p, t = pc[i], tc[i]
        if p == t:
            tp[t] += 1
        else:
            if p < n_classes:
                fp[p] += 1
            fn[t] += 1
    s = 0.0
    for c in range(n_classes):
        d = 2 * tp[c] + fp[c] + fn[c]
        if d:
            s += 2 * tp[c] / d
    return s / n_classes


def _dacc_codes(pc, tc, idx):
    return sum(1 for i in idx if pc[i] == tc[i]) / len(idx)


def bootstrap_gate(items, preds_model, preds_base, seed=12345, b=BOOTSTRAP_B):
    """Paired bootstrap: resample items, recompute composite diff + task diffs.

    Per-task resampling is over that task's applicable items (T3-T5 skip
    correct cases). 10k resamples, stdlib only.
    """
    rng = random.Random(seed)
    tasks = TASKS
    n_classes = {t: len(L.TASKS[t]["values"]) for t in tasks if t != "t6"}
    codes = {}
    for t in tasks:
        codes[t] = (_codes(items, preds_model, t), _codes(items, preds_base, t))
    dummy = dummy_preds(items)
    dummy_primary = {t: score_task(t, task_pairs(items, dummy, t))["primary"]
                     for t in tasks}

    def task_primary(t, pc, tc, n, idx):
        if t == "t6":
            return _dacc_codes(pc, tc, idx)
        return _macro_f1_codes(pc, tc, n_classes[t], idx)

    def composite_of(prim):
        parts = []
        for t in COMPOSITE_TASKS:
            m, d, c = prim[t], dummy_primary[t], CEILINGS[t]
            parts.append(min(1.0, max(0.0, (m - d) / (c - d))) if c > d else 0.0)
        return sum(parts) / len(parts)

    comp_diffs = []
    task_diffs = {t: [] for t in tasks}
    for _ in range(b):
        pm, pb = {}, {}
        for t in tasks:
            (mpc, mtc, n), (bpc, btc, _) = codes[t]
            idx = [rng.randrange(n) for _ in range(n)]
            pm[t] = task_primary(t, mpc, mtc, n, idx)
            pb[t] = task_primary(t, bpc, btc, n, idx)
            task_diffs[t].append(pm[t] - pb[t])
        comp_diffs.append(composite_of(pm) - composite_of(pb))

    def ci(xs):
        s = sorted(xs)
        return (s[int(0.025 * b)], s[int(0.975 * b)], sum(xs) / b)

    lo, hi, mean = ci(comp_diffs)
    wins = {}
    for t, xs in task_diffs.items():
        tlo, thi, tmean = ci(xs)
        wins[t] = {"mean_diff": tmean, "ci95": [tlo, thi], "win": tlo > 0}
    return {
        "composite_diff_mean": mean,
        "composite_diff_ci95": [lo, hi],
        "composite_win": lo > 0,
        "task_wins": wins,
        "n_wins": sum(1 for t in COMPOSITE_TASKS if wins[t]["win"]),
    }


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--preds", default=None)
    ap.add_argument("--base-preds", default=None,
                    help="base-model predictions for the gate comparison")
    ap.add_argument("--dummy", action="store_true",
                    help="score the most-frequent dummy instead of a preds file")
    ap.add_argument("--split", default="test",
                    choices=["test", "test_main", "test_2024", "dev", "all"],
                    help="test = test_main + test_2024")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ref-preds", default=None,
                    help="reference model preds (e.g. untuned 31B); reported only")
    ap.add_argument("--bootstrap-b", type=int, default=BOOTSTRAP_B)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--ids", default=None,
                    help="file of item_ids (one per line) to restrict scoring to")
    args = ap.parse_args()

    splits = {"test": ("test_main", "test_2024"), "all": ("test_main", "test_2024", "dev"),
              "test_main": ("test_main",), "test_2024": ("test_2024",),
              "dev": ("dev",)}[args.split]
    items = load_items(args.items, splits)
    if args.ids:
        keep = set(Path(args.ids).read_text().split())
        items = [it for it in items if it["item_id"] in keep]
    if args.dummy:
        preds = dummy_preds(items)
        model_name = "dummy (most-frequent)"
    else:
        if not args.preds:
            ap.error("--preds or --dummy required")
        preds = load_preds(args.preds)
        model_name = args.preds

    tasks = TASKS
    task_scores = {t: score_task(t, task_pairs(items, preds, t)) for t in tasks}
    dummy_scores = {t: score_task(t, task_pairs(items, dummy_preds(items), t))
                    for t in tasks}
    comp, parts = composite(task_scores, dummy_scores)

    out = {
        "eval_version": EVAL_VERSION,
        "composite_tasks": list(COMPOSITE_TASKS),
        "model": model_name,
        "split": args.split,
        "n_items": len(items),
        "tasks": task_scores,
        "dummy": {t: {"primary": dummy_scores[t]["primary"]} for t in tasks},
        "ceilings": CEILINGS,
        "composite": comp,
        "composite_parts": parts,
    }

    if args.base_preds and not args.dummy:
        base = load_preds(args.base_preds)
        gate = bootstrap_gate(items, preds, base, seed=args.seed, b=args.bootstrap_b)
        t3 = task_scores["t3"]["macro_f1"]
        gate["t3_clears_gbm_floor"] = t3 >= T3_GBM_FLOOR
        gate["t3_macro_f1"] = t3
        gate["pass"] = (gate["composite_win"] and gate["n_wins"] >= 4
                        and gate["t3_clears_gbm_floor"])
        out["gate_vs_base"] = gate
    if args.ref_preds and not args.dummy:
        ref = bootstrap_gate(items, preds, load_preds(args.ref_preds),
                             seed=args.seed, b=args.bootstrap_b)
        out["vs_reference"] = {"ref_preds": args.ref_preds,
                               "composite_diff_mean": ref["composite_diff_mean"],
                               "composite_diff_ci95": ref["composite_diff_ci95"],
                               "beats_reference": ref["composite_win"]}

    txt = []
    txt.append(f"eval {EVAL_VERSION}  model: {model_name}  split: {args.split}  "
               f"n={len(items)}")
    txt.append(f"{'task':<6}{'primary':>10}{'acc':>10}{'n':>7}")
    for t in tasks:
        s = task_scores[t]
        acc = s.get("accuracy", float("nan"))
        txt.append(f"{t:<6}{s['primary']:>10.3f}{acc:>10.3f}{s['n']:>7d}")
    txt.append(f"composite (T1-T5): {comp:.3f}")
    if "gate_vs_base" in out:
        g = out["gate_vs_base"]
        lo, hi = g["composite_diff_ci95"]
        txt.append(f"gate: composite diff {g['composite_diff_mean']:+.3f} "
                   f"[{lo:+.3f},{hi:+.3f}] wins={g['n_wins']}/{len(COMPOSITE_TASKS)} "
                   f"t3>={T3_GBM_FLOOR}: {g['t3_clears_gbm_floor']} "
                   f"PASS={g['pass']}")
    if "vs_reference" in out:
        r = out["vs_reference"]
        lo, hi = r["composite_diff_ci95"]
        txt.append(f"vs reference: composite diff {r['composite_diff_mean']:+.3f} "
                   f"[{lo:+.3f},{hi:+.3f}] beats={r['beats_reference']} "
                   f"(informational)")
    print("\n".join(txt))

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
