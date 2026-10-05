"""IDF — household-type review-burden analysis for the ID P(error)-only winner.

Exp47 pattern applied to Idaho. The risk-regressivity caveat from exp47 is
currently scoped to dollar-maximizing rankers (PA two-part, NY direct):
they deprioritize elderly/disabled households because those errors are
frequent but small-dollar. Idaho's ID5 winner is (a) P(error)-only — which
does NOT chase dollars. Question: does the regressivity replicate for a
P(error)-only ranker, or is the caveat correctly scoped?

Method:
- Household taxonomy from the FY2024 tech-doc codebook (COMPOSITION,
  FSELDER, FSDIS), priority elderly > disabled > composition.
- Shared holdout: experiments/id2_holdout_idx.json (960).
- Ranker reproduced exactly from id5_dollar_ranking.py arm (a): ID synth
  (pooled seed-7, 20k) + HistGradientBoostingClassifier(class_weight=
  "balanced"), isotonic calibration on the real-ID train split, clean-8.
- Per type at top-10%/20%/30%: share of holdout, base error rate, review
  rate, precision within type, dollars recovered; vs random baseline.
- Decision metric: review_rate_t / base_error_rate_t per type — constant
  across types means proportional tilt.

Reproduction (from repo root):
  1) python3 -m src.synth.id_state --n 20000 --seed 7 \\
        --dist experiments/dist.json --out /tmp/idfout/id_synth.jsonl
  2) python3 experiments/idf_id_household_burden.py \\
        --id-synth /tmp/idfout/id_synth.jsonl \\
        --qc-dir ../snap-qc-data/raw

Requires: scikit-learn, numpy. CPU only. Microdata read-only.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # experiments/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import id5_id_dollar_ranking as id5  # noqa: E402

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


def load_state_real(qc_dir, state_code, feat_fn):
    """(fy, state-relative idx) -> (features, status, amterr, raw row)."""
    rows = {}
    for fy in FY_FILES:
        path = Path(qc_dir) / f"qcfy{fy}_csv" / f"qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            idx = 0
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != state_code:
                    continue
                rows[(fy, idx)] = (feat_fn(row), row["STATUS"].strip(),
                                   id5.fnum(row["AMTERR"]), row)
                idx += 1
    return rows


def merge_small_types(types, counts):
    small = {t for t in types if counts[t] < MIN_TYPE_N}
    return ["other_small" if t in small else t for t in types]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    args = ap.parse_args()

    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.isotonic import IsotonicRegression

    out = Path("/tmp/idfout")
    out.mkdir(parents=True, exist_ok=True)
    results = {"household_taxonomy": {
        "source": "FY2024 tech-doc codebook (COMPOSITION/FSELDER/FSDIS)",
        "priority": "elderly > disabled_nonelderly > composition",
        "small_type_merge_threshold": MIN_TYPE_N}}

    # ---------------- load real data + holdout ----------------
    print("loading real microdata...", flush=True)
    id_real = load_state_real(args.qc_dir, "16", id5.real_row_features)
    id_hj = json.loads(Path("experiments/id2_holdout_idx.json").read_text())
    id_hold = {tuple(k) for k in id_hj["holdout_keys"]}

    keys = sorted(id_real.keys())
    tr = [id_real[k] for k in keys if k not in id_hold]
    te = [id_real[k] for k in keys if k in id_hold]
    print(f"  ID train {len(tr)} / test {len(te)}", flush=True)
    assert len(te) == 960, "holdout size changed!"

    # ---------------- train the published winning ranker ----------------
    # ID5 winner (a): P(error)-only — ID synth + balanced GBM (3-class),
    # isotonic calibration on the real-ID train split, clean-8 features.
    print("training ID P(error)-only ranker (id5 arm (a) recipe, CLEAN8)...",
          flush=True)
    id_synth = id5.load_synth(args.id_synth)
    sX = id5.X(id_synth)
    sy = [1 if r[1] else 0 for r in id_synth]
    tX = id5.X(tr)
    ty = [1 if r[1] != "1" else 0 for r in tr]
    hX = id5.X(te)
    clf = HistGradientBoostingClassifier(random_state=0,
                                         class_weight="balanced")
    clf.fit(sX, sy)
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(clf.predict_proba(tX)[:, 1], ty)
    score = np.clip(iso.predict(clf.predict_proba(hX)[:, 1]), 1e-6, 1 - 1e-6)

    # reproduction check vs ID5's published (a) numbers at top-20%
    n = len(te)
    y = np.array([1 if r[1] != "1" else 0 for r in te])
    amt = np.array([r[2] for r in te])
    k20 = int(round(n * 0.20))
    order20 = np.argsort(-score, kind="stable")[:k20]
    rec20 = float(amt[order20].sum())
    print(f"  reproduction check top-20%: ${rec20:,.0f} recovered "
          f"(ID5 published $3,000)", flush=True)

    # ---------------- per-type burden analysis ----------------
    test = te
    raw_types = [household_type(r[3]) for r in test]
    counts = {t: raw_types.count(t) for t in set(raw_types)}
    print(f"\nID holdout household-type counts (pre-merge): "
          f"{dict(sorted(counts.items()))}", flush=True)
    types = merge_small_types(raw_types, counts)
    merged_counts = {t: types.count(t) for t in set(types)}
    print(f"ID merged types: {dict(sorted(merged_counts.items()))}", flush=True)
    tlist = [t for t in TYPE_ORDER if t in merged_counts]
    total_amt = float(amt.sum())
    total_err = int(y.sum())

    blk = {"n_holdout": n, "ranker": "P(error)-only (id5 winner (a))",
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
        print(f"\n== ID top-{int(frac*100)}% (k={k}) ==", flush=True)
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
    results["ID"] = blk

    with open(out / "idf_results.json", "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nresults -> {out / 'idf_results.json'}", flush=True)


if __name__ == "__main__":
    main()
