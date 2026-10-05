"""Exp48 — over/under-issuance split of recovered and MISSED dollars by household type.

Motivation: exp47 showed the PA/NY dollar rankers systematically under-review
elderly and disabled households relative to their error risk (review-rate/base-
error-rate ratios 0.22-0.35) while over-reviewing childless adults (1.41-1.45).
The pilot-relevant follow-up question: are the errors the ranker SKIPS in those
vulnerable types disproportionately UNDERPAYMENTS (money owed to the
household), i.e. does the dollar objective hide under-issuance as well as
small-dollar over-issuance?

Method:
- Same taxonomy, same holdouts, same rankers as exp47 (reproduced exactly;
  pooled seed-7 synthetic; PA: pa5 two-part P(err)xE[$] V1; NY: ny5 direct
  expected-$ CLEAN8). STATUS codes the direction: "2" = over-issuance,
  "3" = under-issuance, "1" = correct; AMTERR carries the dollars
  (pa5/ny5 field logic, reused).
- Top-20% review budget only. Per household type: dollars recovered split
  over/under, dollars MISSED (unselected error dollars) split over/under,
  and the under-share of missed dollars = missed_under / missed_total.
  Random-allocation baseline: under-share of missed would equal the
  under-share of total error dollars (~30% aggregate per pa5/ny5).

Reproduction (from repo root):
  python3 experiments/exp48_overunder_by_household.py \\
      --pa-synth /tmp/exp47out/pa_synth.jsonl \\
      --ny-synth /tmp/exp47out/ny_synth.jsonl \\
      --qc-dir ../snap-qc-data/raw

Requires: scikit-learn, numpy. CPU only. Microdata read-only.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # experiments/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import exp47_household_type_burden as e47  # noqa: E402
import pa5_dollar_ranking as pa5  # noqa: E402
import ny5_dollar_ranking as ny5  # noqa: E402

BUDGET_FRAC = 0.20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pa-synth", required=True)
    ap.add_argument("--ny-synth", required=True)
    ap.add_argument("--qc-dir", required=True)
    args = ap.parse_args()

    import numpy as np
    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  HistGradientBoostingRegressor)
    from sklearn.isotonic import IsotonicRegression

    out = Path("/tmp/exp48out")
    out.mkdir(parents=True, exist_ok=True)
    results = {"method_note": (
        "taxonomy, holdouts, and ranker recipes reproduced exactly from "
        "exp47_household_type_burden.py; STATUS '2'=over / '3'=under / "
        "'1'=correct (pa5/ny5 field logic); top-20% review budget")}

    # ---------------- load real data + holdouts (exp47 loader) ----------------
    print("loading real microdata...", flush=True)
    pa_real = e47.load_state_real(args.qc_dir, "42", pa5.real_row_features)
    ny_real = e47.load_state_real(args.qc_dir, "36", ny5.real_row_features)
    pa_hj = json.loads(Path("experiments/pa2_holdout_idx.json").read_text())
    ny_hj = json.loads(Path("experiments/ny2_holdout_idx.json").read_text())
    pa_hold = {tuple(k) for k in pa_hj["holdout_keys"]}
    ny_hold = {tuple(k) for k in ny_hj["holdout_keys"]}

    def split(real, hold):
        keys = sorted(real.keys())
        return ([real[k] for k in keys if k not in hold],
                [real[k] for k in keys if k in hold])

    pa_train, pa_test = split(pa_real, pa_hold)
    ny_train, ny_test = split(ny_real, ny_hold)
    assert len(pa_test) == 817 and len(ny_test) == 815, "holdout sizes changed!"
    print(f"  PA train {len(pa_train)} / test {len(pa_test)}; "
          f"NY train {len(ny_train)} / test {len(ny_test)}", flush=True)

    # ---------------- train the published winning rankers (exp47 recipe) ------
    print("training PA two-part ranker (pa5 recipe, V1 features)...", flush=True)
    pa_synth = pa5.load_synth(args.pa_synth)
    pa_synth_err = [r for r in pa_synth if r[1]]
    sX = pa5.X(pa_synth)
    sy = [1 if r[1] else 0 for r in pa_synth]
    tX = pa5.X(pa_train)
    ty = [1 if r[1] != "1" else 0 for r in pa_train]
    hX_pa = pa5.X(pa_test)
    clf = HistGradientBoostingClassifier(random_state=0)
    clf.fit(sX, sy)
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(clf.predict_proba(tX)[:, 1], ty)
    p_err_pa = np.clip(iso.predict(clf.predict_proba(hX_pa)[:, 1]),
                       1e-6, 1 - 1e-6)
    reg_err = HistGradientBoostingRegressor(random_state=0)
    reg_err.fit(pa5.X(pa_synth_err),
                np.log1p(np.array([r[2] for r in pa_synth_err])))
    score_pa = p_err_pa * np.clip(np.expm1(reg_err.predict(hX_pa)), 0, None)

    print("training NY direct expected-dollar ranker (ny5 recipe, CLEAN8)...",
          flush=True)
    ny_synth = ny5.load_synth(args.ny_synth)
    sXn = ny5.X(ny_synth)
    reg_all = HistGradientBoostingRegressor(random_state=0)
    reg_all.fit(sXn, np.log1p(np.array([r[2] for r in ny_synth])))
    hX_ny = ny5.X(ny_test)
    score_ny = np.clip(np.expm1(reg_all.predict(hX_ny)), 0, None)

    states = {"PA": {"test": pa_test, "score": score_pa},
              "NY": {"test": ny_test, "score": score_ny}}

    # ---------------- over/under split of recovered and missed dollars -------
    for st, S in states.items():
        test, score = S["test"], S["score"]
        n = len(test)
        k = int(round(n * BUDGET_FRAC))
        order = np.argsort(-score, kind="stable")[:k]
        sel = np.zeros(n, dtype=bool)
        sel[order] = True

        y = np.array([1 if r[1] != "1" else 0 for r in test])
        amt = np.array([r[2] for r in test])
        is_over = np.array([r[1] == "2" for r in test])
        is_under = np.array([r[1] == "3" for r in test])

        raw_types = [e47.household_type(r[3]) for r in test]
        counts = {t: raw_types.count(t) for t in set(raw_types)}
        types = e47.merge_small_types(raw_types, counts)
        tlist = [t for t in e47.TYPE_ORDER if t in set(types)]

        # aggregate under-share baseline: under $ / total error $
        tot_err_amt = float(amt[y == 1].sum())
        tot_under_amt = float(amt[(y == 1) & is_under].sum())
        base_under_share = tot_under_amt / tot_err_amt if tot_err_amt else 0.0

        blk = {"k": k, "n_holdout": n,
               "aggregate_under_share_of_error_$": round(base_under_share, 4),
               "types": {}}
        print(f"\n== {st} top-20% (k={k}) — over/under split by household type ==",
              flush=True)
        print("  type                 | rec_over | rec_under | miss_over | "
              "miss_under | under_share_of_missed", flush=True)
        for t in tlist:
            idx = np.array([i for i, tt in enumerate(types) if tt == t])
            in_t = np.zeros(n, dtype=bool)
            in_t[idx] = True
            rev = sel & in_t           # reviewed cases of this type
            miss = (~sel) & in_t       # unreviewed cases of this type
            rec_over = float(amt[rev & is_over].sum())
            rec_under = float(amt[rev & is_under].sum())
            miss_over = float(amt[miss & is_over].sum())
            miss_under = float(amt[miss & is_under].sum())
            miss_tot = miss_over + miss_under
            us_missed = miss_under / miss_tot if miss_tot else 0.0
            rec_tot = rec_over + rec_under
            us_rec = rec_under / rec_tot if rec_tot else 0.0
            type_tot = float(amt[in_t & (y == 1)].sum())
            us_type = (float(amt[in_t & is_under].sum()) / type_tot
                       if type_tot else 0.0)
            blk["types"][t] = {
                "n": int(in_t.sum()),
                "recovered_over_$": round(rec_over, 2),
                "recovered_under_$": round(rec_under, 2),
                "recovered_under_share": round(us_rec, 4),
                "missed_over_$": round(miss_over, 2),
                "missed_under_$": round(miss_under, 2),
                "under_share_of_missed_$": round(us_missed, 4),
                "under_share_of_type_error_$": round(us_type, 4),
                "missed_under_$_cases": int((miss & is_under).sum()),
                "missed_over_$_cases": int((miss & is_over).sum()),
            }
            print(f"  {t:22s} | {rec_over:8.0f} | {rec_under:9.0f} | "
                  f"{miss_over:9.0f} | {miss_under:10.0f} | {us_missed:.3f}",
                  flush=True)
        # overall line for reference
        o_rec = float(amt[sel & is_over].sum())
        u_rec = float(amt[sel & is_under].sum())
        o_miss = float(amt[(~sel) & is_over].sum())
        u_miss = float(amt[(~sel) & is_under].sum())
        blk["overall"] = {
            "recovered_over_$": round(o_rec, 2),
            "recovered_under_$": round(u_rec, 2),
            "missed_over_$": round(o_miss, 2),
            "missed_under_$": round(u_miss, 2),
            "under_share_of_missed_$":
                round(u_miss / (o_miss + u_miss), 4)
                if (o_miss + u_miss) else 0,
        }
        print(f"  {'OVERALL':22s} | {o_rec:8.0f} | {u_rec:9.0f} | "
              f"{o_miss:9.0f} | {u_miss:10.0f} | "
              f"{blk['overall']['under_share_of_missed_$']:.3f}", flush=True)
        print(f"  aggregate under-share of error $ (random-review baseline "
              f"for missed mix): {base_under_share:.3f}", flush=True)
        results[st] = blk

    with open(out / "exp48_results.json", "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nresults -> {out / 'exp48_results.json'}", flush=True)


if __name__ == "__main__":
    main()
