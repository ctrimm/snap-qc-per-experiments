"""Exp51 — under-issuance-keyed review floors.

Motivation: exp47 showed the dollar rankers under-review elderly/disabled
households relative to error risk (ratios 0.22-0.35). Exp48 refuted the
compositional story (missed mix tracks each type's own over/under mix) but
confirmed the volumetric one: $2.1k (PA) / $2.6k (NY) of owed benefits
(under-issuances) go unreviewed in elderly+disabled types. Exp49 went GO on
error-share floors (Variant A, f=1.0) at no measurable $/hr cost.

Question: does keying the floors specifically to UNDER-ISSUANCE dollars
(owed benefits) — rather than base error rate, total error dollars, or error
shares — move owed-benefit recovery? I.e., is there a targeted underpayment
gain beyond what generic equity floors already buy?

Method:
- Same taxonomy, holdouts, ranker recipes as exp47/exp48 (pooled seed-7
  synthetic; PA pa5 two-part P(err)xE[$] V1; NY ny5 direct expected-$ CLEAN8).
  Top-20% review budget (k=163), f=1.0 (exp49's GO value; f<1 is a dead
  parameter).
- Floor weights from the TRAIN split (exp49's honesty fix — never holdout
  labels). Within-type selection is top-by-dollar-score; remainder filled by
  global dollar rank (exp49's largest-remainder + fill procedure, reused).
- Variants:
    V0 dollar            pure dollar rank (baseline)
    V1 floor_baseerr     floors proportional to train BASE ERROR RATE
                         (exp47's suggestion: reserve per type ∝ risk rate)
    V2 floor_errdollar   floors proportional to train TOTAL ERROR dollars
    V3 floor_underdollar  floors proportional to train UNDER-ISSUANCE dollars
                         <-- the hypothesis under test
    V4 floor_errshare    floors proportional to train ERROR SHARES
                         (exp49 Variant A reference, the GO'd approach)
- Sensitivity (labeled oracle, NOT decision-relevant):
    V3o floor_underdollar_holdout  floors ∝ HOLDOUT under-issuance dollars.
    Uses holdout labels to size the allocation (the leakage exp49 caught);
    reported only to bound how much of any V3 gain is real vs leakage.
- Metrics per variant x state: total $ recovered, $/hr (30-min reviews),
  precision, per-type review_rate/base_error_rate ratios + CV, under-issuance
  $ recovered (overall and elderly+disabled), and Δ$/hr vs the pure ranker.

Reproduction (from repo root):
  python3 experiments/exp51_underissuance_floors.py \\
      --pa-synth /tmp/exp47out/pa_synth.jsonl \\
      --ny-synth /tmp/exp47out/ny_synth.jsonl \\
      --qc-dir ~/workspace/snap-qc-data/raw

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
HOURS_PER_REVIEW = 0.5  # exp49 convention

# Published baselines this experiment must reproduce (else stop, do not build on it)
EXPECT_PA_REC = 5483
EXPECT_NY_REC = 6958


def largest_remainder(quotas, total):
    """Integer allocation of `total` to keys by largest remainder (exp49)."""
    base = {t: int(q) for t, q in quotas.items()}
    rem = total - sum(base.values())
    fracs = sorted(((quotas[t] - base[t], t) for t in quotas), reverse=True)
    i = 0
    while rem > 0 and fracs:
        base[fracs[i % len(fracs)][1]] += 1
        rem -= 1
        i += 1
    return base


def floor_selection(score, types, tlist, k, weights, counts):
    """Floors proportional to `weights` (train-derived); within-type top by
    dollar score; remainder of budget filled by global dollar rank."""
    import numpy as np
    quotas = {t: k * weights[t] for t in tlist}
    floors = largest_remainder(quotas, k)
    floors = {t: min(floors[t], counts[t]) for t in tlist}
    sel = set()
    for t in tlist:
        idx = np.array([i for i, tt in enumerate(types) if tt == t])
        if floors[t] > 0 and len(idx):
            top = idx[np.argsort(-score[idx], kind="stable")[:floors[t]]]
            sel.update(int(i) for i in top)
    rest = k - len(sel)
    glob = np.argsort(-score, kind="stable")
    for i in glob:
        if rest <= 0:
            break
        i = int(i)
        if i not in sel:
            sel.add(i)
            rest -= 1
    return np.array(sorted(sel)), floors


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

    out = Path("/tmp/exp51out")
    out.mkdir(parents=True, exist_ok=True)
    results = {"method_note": (
        "taxonomy/holdouts/rankers reproduced exactly from exp47/exp48 "
        "(pooled seed-7; PA pa5 two-part V1; NY ny5 direct CLEAN8); top-20% "
        "budget k=163; floors f=1.0; floor weights from TRAIN split "
        "(exp49 honesty fix) except the labeled V3o oracle; within-type "
        "selection top-by-dollar-score; remainder filled by global rank")}

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

    states = {"PA": {"train": pa_train, "test": pa_test, "score": score_pa},
              "NY": {"train": ny_train, "test": ny_test, "score": score_ny}}

    # ---------------- reproduction check (stop on mismatch) ------------------
    print("\n-- reproduction check --", flush=True)
    for st, S in states.items():
        test, score = S["test"], S["score"]
        n = len(test)
        k = int(round(n * BUDGET_FRAC))
        order = np.argsort(-score, kind="stable")[:k]
        rec = float(np.array([r[2] for r in test])[order].sum())
        expect = EXPECT_PA_REC if st == "PA" else EXPECT_NY_REC
        print(f"  {st}: recovered ${rec:,.0f} (expect ${expect:,})", flush=True)
        assert abs(rec - expect) < 1.0, (
            f"REPRODUCTION MISMATCH: {st} recovered ${rec:,.0f}, "
            f"expected ${expect:,}. Stopping; not building on a moved baseline.")
    print("  reproduction OK", flush=True)

    # ---------------- per-state variant comparison ---------------------------
    for st, S in states.items():
        train, test, score = S["train"], S["test"], S["score"]
        n = len(test)
        k = int(round(n * BUDGET_FRAC))

        y = np.array([1 if r[1] != "1" else 0 for r in test])
        amt = np.array([r[2] for r in test])
        is_under = np.array([r[1] == "3" for r in test])

        # holdout types (merged, exp48 convention)
        raw_types = [e47.household_type(r[3]) for r in test]
        counts = {t: raw_types.count(t) for t in set(raw_types)}
        types = e47.merge_small_types(raw_types, counts)
        tlist = [t for t in e47.TYPE_ORDER if t in set(types)]
        type_counts = {t: types.count(t) for t in tlist}
        # holdout base error rates (for parity ratios)
        base_err = {}
        for t in tlist:
            idx = [i for i, tt in enumerate(types) if tt == t]
            base_err[t] = float(y[idx].sum() / len(idx)) if idx else 0.0

        # ---- train-side per-type aggregates (honesty: weights from TRAIN) ---
        # map train rows through the same taxonomy, then to merged types
        tr_raw = [e47.household_type(r[3]) for r in train]
        # merged-type mapping derived from holdout merge (same type system)
        holdout_small = {t for t in set(raw_types) if counts[t] < e47.MIN_TYPE_N}
        tr_types = ["other_small" if t in holdout_small else t for t in tr_raw]
        tr_y = np.array([1 if r[1] != "1" else 0 for r in train])
        tr_amt = np.array([r[2] for r in train])
        tr_under = np.array([r[1] == "3" for r in train])

        w_baseerr, w_errdollar, w_underdollar, w_errshare = {}, {}, {}, {}
        for t in tlist:
            m = np.array([tt == t for tt in tr_types])
            nt = int(m.sum())
            ne = int(tr_y[m].sum())
            ed = float(tr_amt[m & (tr_y == 1)].sum())
            ud = float(tr_amt[m & tr_under].sum())
            w_baseerr[t] = (ne / nt) if nt else 0.0
            w_errdollar[t] = ed
            w_underdollar[t] = ud
            w_errshare[t] = ne
        # normalize to shares
        def norm(d):
            s = sum(d.values())
            return {t: (d[t] / s if s else 1.0 / len(d)) for t in d}
        W = {
            "floor_baseerr": norm(w_baseerr),
            "floor_errdollar": norm(w_errdollar),
            "floor_underdollar": norm(w_underdollar),
            "floor_errshare": norm(w_errshare),
        }
        # oracle: weights from HOLDOUT under-issuance $ (labeled, not decision-relevant)
        ho_under = {}
        for t in tlist:
            m = np.array([tt == t for tt in types])
            ho_under[t] = float(amt[m & is_under].sum())
        W["floor_underdollar_holdout"] = norm(ho_under)

        total_err_amt = float(amt[y == 1].sum())
        vuln = {"elderly", "disabled_nonelderly"}

        def evaluate(sel):
            sel = np.asarray(sel, dtype=int)
            mask = np.zeros(n, dtype=bool)
            mask[sel] = True
            rec = float(amt[mask].sum())
            under_rec = float(amt[mask & is_under].sum())
            vuln_idx = np.array([tt in vuln for tt in types])
            under_rec_vuln = float(amt[mask & is_under & vuln_idx].sum())
            ratios = []
            per_type = {}
            for t in tlist:
                idx = np.array([i for i, tt in enumerate(types) if tt == t])
                rev_rate = float(mask[idx].sum() / len(idx)) if len(idx) else 0.0
                r = rev_rate / base_err[t] if base_err[t] else 0.0
                ratios.append(r)
                per_type[t] = {"review_rate": round(rev_rate, 4),
                               "ratio_rev_over_base": round(r, 3)}
            ratios = np.array(ratios)
            return {
                "recovered_$": round(rec, 2),
                "share_of_error_$": round(rec / total_err_amt, 4) if total_err_amt else 0,
                "$_per_hr": round(rec / (k * HOURS_PER_REVIEW), 2),
                "precision": round(float(y[mask].sum() / len(sel)), 4) if len(sel) else 0,
                "under_recovered_$": round(under_rec, 2),
                "under_recovered_elderly_disabled_$": round(under_rec_vuln, 2),
                "ratio_cv": round(float(ratios.std() / ratios.mean()), 3) if ratios.mean() else 0,
                "ratio_min": round(float(ratios.min()), 3),
                "per_type": per_type,
            }

        # V0 baseline: pure dollar rank
        order = np.argsort(-score, kind="stable")[:k]
        variants = {"dollar": {"sel": order, "floors": None,
                               "note": "pure dollar rank (baseline)"}}
        for vname in ["floor_baseerr", "floor_errdollar", "floor_underdollar",
                      "floor_errshare", "floor_underdollar_holdout"]:
            sel, floors = floor_selection(score, types, tlist, k, W[vname],
                                          type_counts)
            variants[vname] = {"sel": sel, "floors": floors,
                               "note": ("train-keyed" if "holdout" not in vname
                                        else "ORACLE: holdout-keyed, not decision-relevant")}

        blk = {"k": k, "n_holdout": n, "variants": {}}
        base_hr = None
        print(f"\n== {st} top-20% (k={k}) — floor-variant comparison ==",
              flush=True)
        print("  variant              | rec $ | $/hr  | prec  | under $ | "
              "under eld/dis $ | CV   | minR", flush=True)
        for vname, V in variants.items():
            ev = evaluate(V["sel"])
            if vname == "dollar":
                base_hr = ev["$_per_hr"]
            ev["delta_$_per_hr_vs_baseline"] = round(ev["$_per_hr"] - base_hr, 2)
            ev["floors"] = V["floors"]
            ev["note"] = V["note"]
            blk["variants"][vname] = ev
            print(f"  {vname:22s} | {ev['recovered_$']:5.0f} | "
                  f"{ev['$_per_hr']:5.1f} | {ev['precision']:.3f} | "
                  f"{ev['under_recovered_$']:7.0f} | "
                  f"{ev['under_recovered_elderly_disabled_$']:13.0f} | "
                  f"{ev['ratio_cv']:.3f} | {ev['ratio_min']:.3f}",
                  flush=True)
        # floor weight tables for the chronicle
        blk["train_weights"] = {vn: {t: round(W[vn][t], 4) for t in tlist}
                                for vn in W}
        blk["holdout_base_err"] = {t: round(base_err[t], 4) for t in tlist}
        results[st] = blk

    with open(out / "exp51_results.json", "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nresults -> {out / 'exp51_results.json'}", flush=True)


if __name__ == "__main__":
    main()
