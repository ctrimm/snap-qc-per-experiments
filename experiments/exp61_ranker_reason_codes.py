"""Exp 61 — do the ranker's own reasons point at the real error?

Groundwork for ranker-grounded explanations ("why was this case flagged?").
For each exp58 agency-side ranker, refit on the non-holdout rows (exp58's
chosen config), then on holdout error cases compute reason codes: ablate one
feature group at a time (set every feature in the group to its training
median) and record how much the expected-dollar score drops. The groups with
the biggest drops are the case's top reasons. Each group maps to eval T3
element buckets; a reason "hits" when its bucket is the case's real T3 label
(largest reportable variance, eval_pilot/labels.py).

Only states that record per-variance amounts carry T3 labels (exp55
correction): PA, NY, ID (UT/SD partially). Baseline: always name the state's
most common T3 bucket among training error cases (and its top two).

Usage: OMP_NUM_THREADS=4 python3 experiments/exp61_ranker_reason_codes.py [--states PA,NY,ID,UT,SD]
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "experiments"), str(ROOT / "experiments" / "eval_pilot"), str(ROOT / "src")]
import exp56_pa_tuned_classifier as E56  # noqa: E402
import exp58_agency_rankers as E58  # noqa: E402
import labels as L  # noqa: E402

# feature groups (indices into E58.FEATURES) -> T3 buckets a reason in that group points at
GROUPS = {
    "earned income": (["earned_deduction", "earned_est", "earned_share"], {"earned"}),
    "unearned income": (["unearned_est"], {"unearned"}),
    "total income": (["gross_income", "net_income", "net_to_gross", "income_per_person"], {"earned", "unearned"}),
    "shelter costs": (["shelter_deduction", "rent", "utilities", "shelter_to_income", "homeless"], {"shelter"}),
    "utility allowance": (["sua_used"], {"sua"}),
    "medical deduction": (["medical_claimed"], {"medical"}),
    "dependent care": (["depcare_claimed"], {"depcare"}),
    "child support": (["child_support_claimed"], {"childsupport"}),
    "household size": (["hh_size_cert", "hh_size_reported"], {"hhcomp"}),
}
FIDX = {f: i for i, f in enumerate(E58.FEATURES)}


def t3_labels(qc_dir, code):
    """(fy, idx) -> T3 bucket or None, indexed exactly like E58.load_state."""
    out = {}
    for fy in E58.FY_FILES:
        path = next(iter((Path(qc_dir) / f"qcfy{fy}_csv").glob("*.csv")))
        idx = 0
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                if row["STATE"].strip() != code:
                    continue
                out[(fy, idx)] = L.label_case(row)["t3"]
                idx += 1
    return out


def reasons(f, X, med):
    base = f(X)
    drops = {}
    for g, (feats, _) in GROUPS.items():
        Xa = X.copy()
        for name in feats:
            Xa[:, FIDX[name]] = med[FIDX[name]]
        drops[g] = base - f(Xa)
    D = np.column_stack([drops[g] for g in GROUPS])
    return D  # rows: cases, cols: groups (positive = this group pushed the score up)


def run_state(st, qc_dir, cfg):
    code, hfile, _, _ = E56.STATES[st]
    real = E58.load_state(qc_dir, code)
    t3 = t3_labels(qc_dir, code)
    hold = {tuple(k) for k in json.loads((ROOT / "experiments" / hfile).read_text())["holdout_keys"]}
    tr = [k for k in sorted(real) if k not in hold]
    te = [k for k in sorted(real) if k in hold]
    X, y, a = E58.arrays(real, tr)
    Xh, yh, ah = E58.arrays(real, te)
    f, _ = E56.fit_two_part(X, y, a, cfg["clf"], cfg["reg"])
    med = np.median(X, axis=0)
    prior = Counter(t3[k] for k in tr if real[k][1] != "1" and t3[k])
    if sum(prior.values()) < 50:
        return None
    top_prior = [b for b, _ in prior.most_common(2)]
    # flagged = top 20% of holdout by score; evaluate error cases with a T3 label among them
    score = f(Xh)
    flag = score >= np.quantile(score, 0.80)
    D = reasons(f, Xh, med)
    names = list(GROUPS)
    hit1 = hit2 = base1 = base2 = n = 0
    first_reason = Counter()
    for i, k in enumerate(te):
        if not flag[i] or yh[i] == 0 or not t3[k]:
            continue
        n += 1
        order = np.argsort(-D[i])
        r1, r2 = names[order[0]], names[order[1]]
        first_reason[r1] += 1
        hit1 += t3[k] in GROUPS[r1][1]
        hit2 += t3[k] in GROUPS[r1][1] | GROUPS[r2][1]
        base1 += t3[k] == top_prior[0]
        base2 += t3[k] in top_prior
    # "where to look" model: per-state multiclass classifier P(T3 | agency features),
    # trained on non-holdout error cases with a T3 label; ranked checklist = top-2 buckets
    from sklearn.ensemble import HistGradientBoostingClassifier
    tr_e = [i for i, k in enumerate(tr) if y[i] and t3[k]]
    wl = HistGradientBoostingClassifier(random_state=61, max_iter=200, learning_rate=0.05,
                                        class_weight=None).fit(X[tr_e], [t3[tr[i]] for i in tr_e])
    proba = wl.predict_proba(Xh)
    wl1 = wl2 = 0
    for i, k in enumerate(te):
        if not flag[i] or yh[i] == 0 or not t3[k]:
            continue
        top = wl.classes_[np.argsort(-proba[i])[:2]]
        wl1 += t3[k] == top[0]
        wl2 += t3[k] in top
    # how much of the flag is explained by the issued benefit (dollar size), not a case part
    Xb = Xh.copy(); Xb[:, FIDX["issued_benefit"]] = med[FIDX["issued_benefit"]]
    ben_share = float(np.mean(np.clip(score - f(Xb), 0, None)[flag] / np.maximum(score[flag], 1e-9)))
    return {"state": st, "flagged_error_cases_with_t3": n,
            "reason_top1_hit": round(hit1 / n, 3), "reason_top2_hit": round(hit2 / n, 3),
            "where_to_look_top1_hit": round(wl1 / n, 3), "where_to_look_top2_hit": round(wl2 / n, 3),
            "prior_top1_hit": round(base1 / n, 3), "prior_top2_hit": round(base2 / n, 3),
            "prior_buckets": top_prior, "most_common_first_reason": first_reason.most_common(4),
            "issued_benefit_share_of_flag_score": round(ben_share, 3),
            "t3_mix_flagged": Counter(t3[k] for i, k in enumerate(te)
                                      if flag[i] and yh[i] and t3[k]).most_common(6)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-dir", default=str(ROOT.parent / "snap-qc-data/raw"))
    ap.add_argument("--states", default="PA,NY,ID,UT,SD")
    args = ap.parse_args()
    cfgs = {r["state"]: r["cfg"] for r in json.loads((ROOT / "experiments" / "exp58_results.json").read_text())}
    out = []
    for st in args.states.split(","):
        r = run_state(st, args.qc_dir, cfgs[st])
        if r is None:
            print(f"{st}: too few T3-labelled error cases, skipped"); continue
        out.append(r)
        print(f"{st}: n={r['flagged_error_cases_with_t3']:3d} | reason top-1 {r['reason_top1_hit']:.0%} top-2 {r['reason_top2_hit']:.0%} "
              f"| where-to-look top-1 {r['where_to_look_top1_hit']:.0%} top-2 {r['where_to_look_top2_hit']:.0%} "
              f"| prior top-1 {r['prior_top1_hit']:.0%} top-2 {r['prior_top2_hit']:.0%} ({'/'.join(r['prior_buckets'])}) "
              f"| benefit share of score {r['issued_benefit_share_of_flag_score']:.0%} | first reasons {r['most_common_first_reason']}", flush=True)
    (ROOT / "experiments" / "exp61_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
