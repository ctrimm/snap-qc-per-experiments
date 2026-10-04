"""UT fairness check — household-type review burden for the UT two-part winner.

Exp47 pattern applied to Utah: the UT5 winning ranker is the two-part
P(error) x E[dollars] (a dollar-maximizing ranker — the class the
risk-regressivity caveat is currently scoped to). Question: does the
two-part ranker over-review certain household types relative to their
actual error risk, or is the tilt proportional to where errors and dollars
are?

Method (exp47):
- Household taxonomy from the FY2024 tech-doc codebook (COMPOSITION,
  FSELDER, FSDIS), priority elderly > disabled > composition.
- Shared holdout: experiments/ut2_holdout_idx.json (1026).
- Ranker recipe reproduced exactly from ut5_dollar_ranking.py: (a)
  calibrated P(error) (GBM balanced, CLEAN8, isotonic/Platt by CV Brier on
  the real-UT train split) x (b) E[AMTERR|features] (GBM regressor on UT
  synth error cases, log1p target). Pooled seed-7 synthetic, same as the
  published run.
- Per type at top-10%/20%/30%: share of holdout, base error rate, review
  rate, precision within type, dollars recovered; vs random baseline.
- Decision metric: review_rate_t / base_error_rate_t per type — constant
  across types means proportional tilt; systematic deviation means
  over/under-review relative to risk.

Reproduction (from repo root):
  1) python3 -m src.synth.ut_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out /tmp/ut45out/ut_synth.jsonl
  2) python3 experiments/ut_fairness.py \\
        --ut-synth /tmp/ut45out/ut_synth.jsonl \\
        --qc-dir ~/workspace/snap-qc-data/raw

Requires: scikit-learn, numpy. CPU only. Microdata read-only.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # experiments/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import ut5_dollar_ranking as ut5  # noqa: E402

FY_FILES = (2020, 2021, 2022, 2023, 2024)
TOPK_FRACS = (0.10, 0.20, 0.30)
MIN_TYPE_N = 25  # types smaller than this merge into other_small

# Household taxonomy, documented from the FY2024 tech-doc codebook.
# COMPOSITION: 0=no children, 1=child(ren) only, 2=children+one male adult,
#   3=children+one female adult, 4=children+married head,
#   5=children+other multiple adults, 6=children+one adult (sex unspecified).
# FSELDER: elderly individual in unit. FSDIS: disabled individual (<=59) in unit.
# Priority: elderly > disabled > composition, so multigenerational units with
# an elder/disabled member count in the elder/disabled type.
TYPE_ORDER = ["elderly", "disabled_nonelderly", "single_parent",
              "married_with_kids", "multiadult_with_kids", "child_only",
              "childless_adult", "other_small"]


def household_type(row):
    if (row.get("FSELDER") or "").strip() == "1":
        return "elderly"
    if (row.get("FSDIS") or "").strip() == "1":
        return "disabled_nonelderly"
    comp = (row.get("COMPOSITION") or "").strip()
    if comp in ("2", "3", "6"):
        return "single_parent"
    if comp == "4":
        return "married_with_kids"
    if comp == "5":
        return "multiadult_with_kids"
    if comp == "1":
        return "child_only"
    if comp == "0":
        return "childless_adult"
    return "other"


def load_ut_real(qc_dir):
    """(fy, ut-relative idx) -> (features, status, amterr, raw row)."""
    rows = {}
    for fy in FY_FILES:
        path = Path(qc_dir) / f"qcfy{fy}_csv" / f"qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != "49":
                    continue
                rows[(fy, idx)] = (ut5.real_row_features(row),
                                   row["STATUS"].strip(),
                                   ut5.fnum(row["AMTERR"]), row)
                idx += 1
    return rows


def merge_small_types(types, counts):
    small = {t for t in types if counts[t] < MIN_TYPE_N}
    return ["other_small" if t in small else t for t in types]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ut-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    ap.add_argument("--holdout-json",
                    default="experiments/ut2_holdout_idx.json")
    args = ap.parse_args()

    import numpy as np
    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  HistGradientBoostingRegressor)
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    out = Path("/tmp/ut45out")
    out.mkdir(parents=True, exist_ok=True)
    results = {"household_taxonomy": {
        "source": "FY2024 tech-doc codebook (COMPOSITION/FSELDER/FSDIS)",
        "priority": "elderly > disabled_nonelderly > composition",
        "small_type_merge_threshold": MIN_TYPE_N}}

    print("loading real UT microdata + holdout...", flush=True)
    real = load_ut_real(args.qc_dir)
    hj = json.loads(Path(args.holdout_json).read_text())
    hold = {tuple(k) for k in hj["holdout_keys"]}
    keys = sorted(real.keys())
    train = [real[k] for k in keys if k not in hold]
    test = [real[k] for k in keys if k in hold]
    print(f"  UT train {len(train)} / test {len(test)}", flush=True)
    assert len(test) == 1026, "holdout size changed!"

    # ---- reproduce the UT5 two-part winner exactly ----
    print("training UT two-part winner (ut5 recipe, CLEAN8, balanced P(err))...",
          flush=True)
    synth = ut5.load_synth(args.ut_synth)
    synth_err = [r for r in synth if r[1]]
    sX = ut5.X(synth)
    sy = [1 if r[1] else 0 for r in synth]
    tX = ut5.X(train)
    ty = [1 if r[1] != "1" else 0 for r in train]
    hX = ut5.X(test)

    clf = HistGradientBoostingClassifier(random_state=0,
                                         class_weight="balanced")
    clf.fit(sX, sy)
    raw_train = clf.predict_proba(np.array(tX))[:, 1]
    raw_hold = clf.predict_proba(np.array(hX))[:, 1]
    # choose calibrator by the same CV-Brier protocol as ut5
    name, _, _ = ut5.choose_calibrator(raw_train, np.array(ty))
    if name == "isotonic":
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(raw_train, np.array(ty))
        p_err = np.clip(iso.predict(raw_hold), 1e-6, 1 - 1e-6)
    else:
        lr = LogisticRegression().fit(raw_train.reshape(-1, 1),
                                      np.array(ty))
        p_err = lr.predict_proba(raw_hold.reshape(-1, 1))[:, 1]
    print(f"  calibrator: {name}", flush=True)

    reg_err = HistGradientBoostingRegressor(random_state=0)
    reg_err.fit(ut5.X(synth_err),
                np.log1p(np.array([r[2] for r in synth_err])))
    score = p_err * np.clip(np.expm1(reg_err.predict(np.array(hX))), 0, None)

    # ---- per-type burden analysis ----
    n = len(test)
    y = np.array([1 if r[1] != "1" else 0 for r in test])
    amt = np.array([r[2] for r in test])
    raw_types = [household_type(r[3]) for r in test]
    counts = {t: raw_types.count(t) for t in set(raw_types)}
    print(f"\nUT holdout household-type counts (pre-merge): "
          f"{dict(sorted(counts.items()))}", flush=True)
    types = merge_small_types(raw_types, counts)
    merged_counts = {t: types.count(t) for t in set(types)}
    print(f"UT merged types: {dict(sorted(merged_counts.items()))}", flush=True)
    tlist = [t for t in TYPE_ORDER if t in merged_counts]
    total_amt = float(amt.sum())
    total_err = int(y.sum())

    blk = {"n_holdout": n, "ranker": "two-part P(err)xE[$] (UT5 winner)",
           "type_counts": merged_counts, "budgets": {}}
    for frac in TOPK_FRACS:
        k = int(round(n * frac))
        order = np.argsort(-score, kind="stable")[:k]
        sel = np.zeros(n, dtype=bool)
        sel[order] = True
        b = {"k": k, "types": {}, "overall": {}}
        b["overall"] = {
            "recovered_$": round(float(amt[order].sum()), 2),
            "share_of_total_$": round(float(amt[order].sum() / total_amt), 4),
            "precision": round(float(y[order].sum() / k), 4),
        }
        ratios = []
        for t in tlist:
            idx = np.array([i for i, tt in enumerate(types) if tt == t])
            nt = len(idx)
            err_t = int(y[idx].sum())
            amt_t = float(amt[idx].sum())
            sel_t = int(sel[idx].sum())
            rev_rate = sel_t / nt
            base_err = err_t / nt
            prec_t = float(y[idx][sel[idx]].sum() / sel_t) if sel_t else 0.0
            rec_t = float(amt[order][np.isin(order, idx)].sum())
            rand_rev_rate = k / n
            rand_rec_t = (k / n) * amt_t
            ratio = rev_rate / base_err if base_err else 0.0
            ratios.append(ratio)
            b["types"][t] = {
                "n": nt,
                "share_of_holdout": round(nt / n, 4),
                "share_of_holdout_errors": round(err_t / total_err, 4) if total_err else 0,
                "base_error_rate": round(base_err, 4),
                "review_rate": round(rev_rate, 4),
                "review_rate_random": round(rand_rev_rate, 4),
                "precision_in_type": round(prec_t, 4),
                "recovered_$_in_type": round(rec_t, 2),
                "random_expected_$_in_type": round(rand_rec_t, 2),
                "share_of_type_error_$_recovered": round(rec_t / amt_t, 4) if amt_t else 0,
                "review_rate_over_base_error_rate": round(ratio, 3),
            }
        ratios = np.array(ratios)
        b["proportionality"] = {
            "ratio_mean": round(float(ratios.mean()), 3),
            "ratio_cv": round(float(ratios.std() / ratios.mean()), 3)
            if ratios.mean() else 0,
            "ratio_min": round(float(ratios.min()), 3),
            "ratio_max": round(float(ratios.max()), 3),
            "note": "ratio = review_rate_t / base_error_rate_t; constant "
                    "across types => tilt proportional to risk; CV "
                    "summarizes spread",
        }
        blk["budgets"][f"{int(frac*100)}pct"] = b
        print(f"\n== UT top-{int(frac*100)}% (k={k}) ==", flush=True)
        print(f"  overall: ${b['overall']['recovered_$']:,.0f} recovered "
              f"({b['overall']['share_of_total_$']:.1%} of ${total_amt:,.0f}), "
              f"precision {b['overall']['precision']:.3f}", flush=True)
        print("  type | n | base_err | rev_rate | prec | ratio(rev/base)", flush=True)
        for t in tlist:
            d = b["types"][t]
            print(f"  {t:22s} | {d['n']:3d} | {d['base_error_rate']:.3f} | "
                  f"{d['review_rate']:.3f} | {d['precision_in_type']:.3f} | "
                  f"{d['review_rate_over_base_error_rate']:.3f}", flush=True)
        print(f"  proportionality: CV={b['proportionality']['ratio_cv']:.3f} "
              f"range [{b['proportionality']['ratio_min']:.3f}, "
              f"{b['proportionality']['ratio_max']:.3f}]", flush=True)
    results["UT"] = blk

    with open(out / "ut_fairness_results.json", "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nresults -> {out / 'ut_fairness_results.json'}", flush=True)


if __name__ == "__main__":
    main()
