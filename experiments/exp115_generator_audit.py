"""Exp 115 — the synthetic generator against what exp106-exp113 established (descriptive audit, no model fitting).

Compares, for FY2024 errors over the federal tolerance ($56):
  public    the QC public-use file's "reported" (RAW*) fields vs the reviewer's verified (FS*) fields
  rebuilt   giannella/snap_qc's rebuilt pre-review values (exp109 nominal frame) vs FS*
  synthetic the generator's agency view (issued_facts) vs its truth (facts), default settings, dist.json
on: how often the agency-side value equals the verified one (gross, net, shelter deduction, and all three of gross,
net and household size together, exp52's view-identity measure); the official-error rate overall and by earner;
the error-dollar distribution; and the overpaid share.

Usage: python3 experiments/exp115_generator_audit.py --frame NOMINAL_FRAME.parquet --synth SYNTH.jsonl
       (synthetic: cd src && python3 -m synth.generate --n 20000 --seed 7 --dist ../experiments/dist.json --out SYNTH.jsonl)
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from synth import benefit as B  # noqa: E402

TOL = 56


def f(x):
    try:
        return float(x or 0)
    except ValueError:
        return 0.0


def q(xs):
    return {"median": float(np.median(xs)), "p75": float(np.percentile(xs, 75)), "p90": float(np.percentile(xs, 90))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--frame", required=True); ap.add_argument("--synth", required=True)
    args = ap.parse_args()
    out = {}
    # public file, FY2024
    pub = {"n": 0, "err": 0, "earner": [0, 0], "noearner": [0, 0], "amt": [], "over": 0, "eq": {"gross": 0, "net": 0, "shelter": 0, "all3": 0}}
    for r in csv.DictReader(open(ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv", encoding="latin-1")):
        st = r["STATUS"].strip(); a = abs(f(r["AMTERR"])); off = st in ("2", "3") and a > TOL; e = f(r["FSEARN"]) > 0
        pub["n"] += 1; k = "earner" if e else "noearner"; pub[k][0] += 1; pub[k][1] += off
        if off:
            pub["err"] += 1; pub["amt"].append(a); pub["over"] += st == "2"
            g = abs(f(r["RAWGROSS"]) - f(r["FSGRINC"])) < 1; n = abs(f(r["RAWNET"]) - f(r["FSNETINC"])) < 1
            h = abs(f(r["CERTHHSZ"]) - f(r["FSUSIZE"])) < 1; s = abs(f(r["SHELDED"]) - f(r["FSSLTDED"])) < 1
            pub["eq"]["gross"] += g; pub["eq"]["net"] += n; pub["eq"]["shelter"] += s; pub["eq"]["all3"] += g and n and h
    out["public"] = {"official_rate": pub["err"] / pub["n"], "rate_earner": pub["earner"][1] / pub["earner"][0],
                     "rate_noearner": pub["noearner"][1] / pub["noearner"][0], "dollars": q(pub["amt"]),
                     "overpaid_share": pub["over"] / pub["err"], "agency_equals_verified": {k: v / pub["err"] for k, v in pub["eq"].items()}}
    # rebuilt (giannella frame, nominal), FY2024 over-threshold
    import pandas as pd
    fr = pd.read_parquet(args.frame, columns=["fiscal_year", "over_threshold", "rawgross", "fsgrinc", "rawnet_capped", "fsnetinc",
                                              "rawsltded", "fssltded", "cert_HH_size_FS_n", "fsusize"])
    fr = fr[(fr.fiscal_year == 2024) & (fr.over_threshold.astype(str) == "1")]
    g = (fr.rawgross - fr.fsgrinc).abs() < 1; n = (fr.rawnet_capped - fr.fsnetinc).abs() < 1
    s = (fr.rawsltded - fr.fssltded).abs() < 1; h = (fr.cert_HH_size_FS_n - fr.fsusize).abs() < 1
    out["rebuilt"] = {"n": int(len(fr)), "agency_equals_verified": {"gross": float(g.mean()), "net": float(n.mean()),
                                                                     "shelter": float(s.mean()), "all3": float((g & n & h).mean())}}
    # synthetic
    rows = [json.loads(line) for line in open(args.synth)]
    ov = [r for r in rows if r["finding"] != 1 and abs(r["issued_benefit"] - r["correct_benefit"]) > TOL]
    eq = {"gross": [], "net": [], "shelter": [], "all3": []}
    for r in ov:
        a, v = B.compute(r["issued_facts"]), B.compute(r["facts"])
        gg = abs(a["gross"] - v["gross"]) < 1; nn = abs(a["net"] - v["net"]) < 1; ss = abs(a["excess_shelter"] - v["excess_shelter"]) < 1
        hh = r["issued_facts"]["hh_size"] == r["facts"]["hh_size"]
        eq["gross"].append(gg); eq["net"].append(nn); eq["shelter"].append(ss); eq["all3"].append(gg and nn and hh)
    earn = [r["facts"]["earned"] > 0 for r in rows]
    off = [r["finding"] != 1 and abs(r["issued_benefit"] - r["correct_benefit"]) > TOL for r in rows]
    out["synthetic"] = {"n": len(rows), "any_error_rate": float(np.mean([r["finding"] != 1 for r in rows])),
                        "official_rate": float(np.mean(off)),
                        "rate_earner": float(np.mean([o for e, o in zip(earn, off) if e])),
                        "rate_noearner": float(np.mean([o for e, o in zip(earn, off) if not e])),
                        "dollars": q([abs(r["issued_benefit"] - r["correct_benefit"]) for r in ov]),
                        "overpaid_share": float(np.mean([r["issued_benefit"] > r["correct_benefit"] for r in ov])),
                        "agency_equals_verified": {k: float(np.mean(v)) for k, v in eq.items()}}
    cal = json.loads((ROOT / "experiments/exp52_view_calibration.json").read_text()) if (ROOT / "experiments/exp52_view_calibration.json").exists() else {}
    out["exp52_view_calibration_targets"] = cal.get("p_identical")
    print(json.dumps(out, indent=1))
    (ROOT / "experiments/exp115_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
