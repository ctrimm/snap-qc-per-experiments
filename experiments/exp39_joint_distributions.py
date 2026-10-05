"""Experiment 39 - household joint-distribution realism.

North-star gate: calibration. Earlier calibration rounds matched *marginals*
(exp6 income screen, exp29 base-positivity strata) but the sampler draws each
household attribute independently (or only via the income screen), so *joint*
distributions can still diverge from real QC in ways marginal checks miss -
particularly joints that feed the benefit computation (income x shelter x
earner status).

Method:
  Real: FY2024 QC public-use microdata (held-out; NEVER committed), weighted
  by HWGT. Comparable bins are built on both sides:
    hhsize        : 1..5, 6+  (synth draws 1..6; real CERTHHSZ grouped at 6+)
    earner        : FSEARN>0 (real) / earned>0 (synth)
    income band   : gross=earned+unearned -> [0,1000), [1000,2000),
                    [2000,3000), [3000,inf)
    shelter band  : real RENT+UTIL vs synth shelter
                    -> 0, (0,700], (700,1200], >1200
    senior_dis    : real FSNELDER>0 or FSNDIS>0 / synth senior_disabled
    med flag      : real FSMEDEXP>0 / synth medical_exp>0
  Synth: cases from `cd src && python -m synth.generate --n 20000 --seed 7
    --dist ../experiments/dist.json --out ...` (the task's literal
    `python3 src/synth/generate.py` fails: generate.py uses relative imports,
    so it must run as a module from src/). Uses case["facts"] (true facts,
    before error injection) and case["correct_benefit"].

  Joints compared (L1 distance on joint cell probabilities; chi-square as
  secondary; cells ranked by |p_real - p_synth| contribution):
    A: hhsize x earner                     (12 cells)
    B: income band x shelter band          (16 cells)
    C: hhsize x income band x earner       (48 cells)
    D: senior_dis x medical flag x earner  (8 cells)

  Benefit tracing: for each joint, importance-reweight the synthetic cases
  with w = p_real(cell) / p_synth(cell) and compare the mean correct benefit
  before/after reweighting. If the joint divergence is cosmetic, the mean
  barely moves; if it is material, it does. Also reports mean benefit per
  cell (synth) vs mean FSBEN per cell (real, the QC-corrected benefit) for
  the top divergent cells, to check whether the benefit model itself is the
  problem in that cell.

Usage:
    python3 experiments/exp39_joint_distributions.py \
        --real ../snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv \
        --synth /tmp/exp39_synth.jsonl
"""
import argparse
import csv
import json
import math

INC_EDGES = [1000.0, 2000.0, 3000.0]          # gross income bands
SHEL_EDGES = [700.0, 1200.0]                 # shelter-cost bands (plus 0)


def band(x, edges):
    for i, e in enumerate(edges):
        if x < e:
            return i
    return len(edges)


def hhsize_bin(s):
    return min(int(s), 6)


def load_real(path):
    """Weighted feature list from FY2024 QC microdata."""
    rows = []
    with open(path, newline="") as f:
        rdr = csv.DictReader(f)
        need = ["CERTHHSZ", "FSEARN", "FSUNEARN", "RENT", "UTIL", "FSNELDER",
                "FSNDIS", "FSMEDEXP", "FSBEN", "HWGT"]
        for row in rdr:
            def f_(k):
                v = (row.get(k) or "0").strip()
                try:
                    return float(v)
                except ValueError:
                    return 0.0
            vals = {k: f_(k) for k in need}
            earned = vals["FSEARN"]
            unearned = vals["FSUNEARN"]
            shelter = vals["RENT"] + vals["UTIL"]
            feats = {
                "hh": hhsize_bin(vals["CERTHHSZ"]),
                "earner": 1 if earned > 0 else 0,
                "inc": band(earned + unearned, INC_EDGES),
                "shel": 0 if shelter <= 0 else band(shelter, SHEL_EDGES) + 1,
                "sen": 1 if (vals["FSNELDER"] > 0 or vals["FSNDIS"] > 0) else 0,
                "med": 1 if vals["FSMEDEXP"] > 0 else 0,
                "benefit": vals["FSBEN"],
                "w": vals["HWGT"] if vals["HWGT"] > 0 else 1.0,
            }
            rows.append(feats)
    return rows


def load_synth(path):
    rows = []
    with open(path) as f:
        for line in f:
            case = json.loads(line)
            fr = case["facts"]
            shelter = fr["shelter"]
            rows.append({
                "hh": hhsize_bin(fr["hh_size"]),
                "earner": 1 if fr["earned"] > 0 else 0,
                "inc": band(fr["earned"] + fr["unearned"], INC_EDGES),
                "shel": 0 if shelter <= 0 else band(shelter, SHEL_EDGES) + 1,
                "sen": int(fr["senior_disabled"]),
                "med": 1 if fr["medical_exp"] > 0 else 0,
                "benefit": float(case["correct_benefit"]),
                "w": 1.0,
            })
    return rows


JOINTS = {
    "A hhsize x earner": ("hh", "earner"),
    "B income x shelter": ("inc", "shel"),
    "C hhsize x income x earner": ("hh", "inc", "earner"),
    "D senior/dis x medical x earner": ("sen", "med", "earner"),
}

LBL = {
    "hh": {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6+"},
    "earner": {0: "noEarn", 1: "earn"},
    "inc": {0: "<1k", 1: "1-2k", 2: "2-3k", 3: "3k+"},
    "shel": {0: "0", 1: "1-700", 2: "701-1200", 3: ">1200"},
    "sen": {0: "nonSen", 1: "senDis"},
    "med": {0: "noMed", 1: "med"},
}


def joint_probs(rows, keys):
    """Joint cell probabilities (weight-normalized)."""
    from collections import defaultdict
    acc = defaultdict(float)
    tot = 0.0
    for r in rows:
        acc[tuple(r[k] for k in keys)] += r["w"]
        tot += r["w"]
    return {c: v / tot for c, v in acc.items()}, tot


def compare(real, synth, keys):
    pr, _ = joint_probs(real, keys)
    ps, _ = joint_probs(synth, keys)
    cells = sorted(set(pr) | set(ps))
    diffs = []
    l1 = 0.0
    chi2 = 0.0
    n_synth = len(synth)
    for c in cells:
        a, b = pr.get(c, 0.0), ps.get(c, 0.0)
        d = a - b
        l1 += abs(d)
        diffs.append((c, a, b, d))
        # chi-square (expected = real share, observed = synth count share)
        exp = a * n_synth
        if exp > 0:
            chi2 += (b * n_synth - exp) ** 2 / exp
    diffs.sort(key=lambda t: -abs(t[3]))
    dof = len(cells) - 1
    return {"l1": l1, "chi2": chi2, "dof": dof, "cells": diffs,
            "pr": pr, "ps": ps}


def reweight_mean(synth, keys, pr, ps):
    """Mean benefit after importance-reweighting synth by real/synth odds."""
    num = den = 0.0
    ess_num = ess_den = 0.0
    for r in synth:
        c = tuple(r[k] for k in keys)
        b = ps.get(c, 0.0)
        w = (pr.get(c, 0.0) / b) if b > 0 else 0.0
        if w == 0:
            continue
        num += w * r["benefit"]
        den += w
        ess_num += w
        ess_den += w * w
    ess = ess_num ** 2 / ess_den if ess_den else 0.0
    return (num / den if den else float("nan"), ess)


def cell_mean_benefit(rows, keys, cells, benefit_key="benefit"):
    from collections import defaultdict
    acc = defaultdict(lambda: [0.0, 0.0])  # sum, wsum
    for r in rows:
        c = tuple(r[k] for k in keys)
        if c in cells:
            acc[c][0] += r[benefit_key] * r["w"]
            acc[c][1] += r["w"]
    return {c: (v[0] / v[1] if v[1] else float("nan")) for c, v in acc.items()}


def fmt_cell(keys, cell):
    return "x".join(f"{LBL[k][v]}" for k, v in zip(keys, cell))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--synth", required=True)
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args()

    real = load_real(args.real)
    synth = load_synth(args.synth)
    rw = sum(r["w"] for r in real)
    base_mean = sum(r["benefit"] * r["w"] for r in synth) / sum(r["w"] for r in synth)
    real_mean = sum(r["benefit"] * r["w"] for r in real) / rw
    print(f"real n={len(real)} (wsum={rw:,.0f})  synth n={len(synth)}")
    print(f"mean benefit: real FSBEN={real_mean:.1f}  synth correct={base_mean:.1f}\n")

    results = {}
    for name, keys in JOINTS.items():
        cmp_ = compare(real, synth, keys)
        cells = cmp_["cells"]
        rw_mean, ess = reweight_mean(synth, keys, cmp_["pr"], cmp_["ps"])
        results[name] = cmp_
        print(f"=== {name} ===")
        print(f"L1={cmp_['l1']:.4f}  chi2={cmp_['chi2']:.1f} (dof={cmp_['dof']}, "
              f"n_synth={len(synth)})  mean benefit: unweighted={base_mean:.1f} "
              f"reweighted={rw_mean:.1f} (delta={rw_mean - base_mean:+.2f}, ESS={ess:,.0f})")
        top = [c for c, *_ in cells[:args.top]]
        rb = cell_mean_benefit(real, keys, set(top))
        sb = cell_mean_benefit(synth, keys, set(top))
        print(f"{'cell':22s} {'p_real':>8s} {'p_synth':>8s} {'delta':>8s} "
              f"{'ben_real':>8s} {'ben_synth':>9s}")
        for c, a, b, d in cells[:args.top]:
            lab = fmt_cell(keys, c)
            print(f"{lab:22s} {a:8.4f} {b:8.4f} {d:+8.4f} "
                  f"{rb.get(c, float('nan')):8.1f} {sb.get(c, float('nan')):9.1f}")
        print()
    json.dump({n: {"l1": v["l1"], "chi2": v["chi2"]}
               for n, v in results.items()},
              open("/tmp/exp39_summary.json", "w"))


if __name__ == "__main__":
    main()
