"""Exp 15 — cause-mix calibration audit.

Does the synthetic generator's recorded cause mix (who is responsible for a
variance: the agency, the client, or neither) track the empirical mix from the
real FY2024 QC file — overall and within each element bucket?

The generator draws cause codes from the empirical per-bucket conditional
distribution (dist.json cause_given_bucket) with no importance weighting, then
drops non-materializing variances (persistent single-draw-and-drop, exp 7).
The audit checks whether the materialization filter distorts the recorded
cause shares.

Usage: python experiments/exp15_cause_audit.py [--n 20000] [--seed 7]
         [--synth /tmp/exp15_synth.jsonl] [--no-regen]

Held-out rule: reads the real QC public-use file from snap-qc-data/ beside the
repo checkout (the microdata is never committed or written into the repo).
"""
import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from synth.codebook import element_bucket  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QC = ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv"

# Coarse cause buckets. Labels below are the FY2024 Tech Doc codebook text
# (Chapter V). Note: src/synth/codebook.py's CAUSE_BUCKETS groups only
# 1,2,4 -> client and a subset of agency codes; here the full agency series
# 10-25 is agency, code 3 (client IPV) is client, and 26/99/7/8 are other.
# The three-way split is what the task asks for; the fine-grained table
# below lets a reader regroup as they like.
AGENCY_CAUSE = {10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25}
CLIENT_CAUSE = {1, 2, 3, 4}
# 7 = collateral contact; 8 = federal computer match (excluded from error
# determination); 26 = change not required to be reported/acted upon
# (no-fault); 99 = other; blank = not recorded.
OTHER_CAUSE = {7, 8, 26, 99}

CAUSE_LABELS_SHORT = {
    1: "info not reported", 2: "incomplete info (agency not req. verify)",
    3: "info withheld by client (IPV)", 4: "incorrect info by client (IPV)",
    7: "collateral contact", 8: "federal computer match",
    10: "policy incorrectly applied", 12: "reported info disregarded",
    14: "agency no follow-up on inconsistent info",
    15: "agency no follow-up on impending changes",
    16: "agency failed to verify", 17: "computer programming error",
    18: "data entry/coding error", 19: "mass change",
    20: "arithmetic computation error", 21: "computer user error",
    22: "agency budgeted wrong amount",
    23: "recert procedure: notices/forms", 24: "recert procedure: interviews",
    25: "recert procedure: time frames",
    26: "not required to be reported (no-fault)", 99: "other",
}


def coarse_cause(code):
    if code is None:
        return "unknown"
    if code in AGENCY_CAUSE:
        return "agency"
    if code in CLIENT_CAUSE:
        return "client"
    return "other"


def real_variances():
    """Yield (element_bucket, nature_code_or_None, cause_code_or_None) per variance."""
    out = []
    with open(QC, newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            for i in range(1, 10):
                e = row.get(f"ELEMENT{i}", "").strip()
                if not e:
                    continue
                b = element_bucket(int(e))
                ntr = row.get(f"NATURE{i}", "").strip()
                cau = row.get(f"AGENCY{i}", "").strip()
                out.append((b, int(ntr) if ntr else None,
                            int(cau) if cau else None))
    return out


def synth_variances(path):
    out = []
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            for v in c["variances"]:
                b = v["element_bucket"]
                code = v.get("cause")
                out.append((b, int(code) if code is not None else None))
    return out


def shares(counter):
    n = sum(counter.values())
    return {k: v / n for k, v in counter.items()}, n


def l1(p, q, keys):
    return sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def ratio_table(real_s, synth_s, keys):
    rows = []
    for k in keys:
        r, s = real_s.get(k, 0.0), synth_s.get(k, 0.0)
        rows.append((k, r, s, (s / r) if r > 0 else float("nan")))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--synth", type=str, default="/tmp/exp15_synth.jsonl")
    ap.add_argument("--no-regen", action="store_true")
    args = ap.parse_args()

    synth_path = Path(args.synth)
    if not args.no_regen or not synth_path.exists():
        subprocess.run(
            [sys.executable, "-m", "synth.generate", "--n", str(args.n),
             "--seed", str(args.seed), "--dist", str(ROOT / "experiments/dist.json"),
             "--out", str(synth_path)],
            cwd=ROOT / "src", check=True, capture_output=True,
        )

    real = real_variances()
    synth = synth_variances(synth_path)

    real_c = Counter(coarse_cause(c) for _, _, c in real)
    synth_c = Counter(coarse_cause(c) for _, c in synth)
    real_s, r_n = shares(real_c)
    synth_s, s_n = shares(synth_c)
    keys = ["agency", "client", "other", "unknown"]

    print(f"real variances: {r_n}; synth variances: {s_n}")
    print(f"\n== overall cause mix (share of variances) == L1 = "
          f"{l1(real_s, synth_s, keys):.3f}")
    print(f"  {'cause':<10}{'real':>9}{'synth':>9}{'ratio':>8}")
    for k, r, s, rt in ratio_table(real_s, synth_s, keys):
        print(f"  {k:<10}{r:>9.3f}{s:>9.3f}{rt:>8.2f}")

    # known-conditional: the generator always records a cause, so compare the
    # three coarse categories among variances that have a recorded cause.
    keys3 = ["agency", "client", "other"]
    real_k = {k: real_s[k] / (1 - real_s["unknown"]) for k in keys3}
    synth_k = {k: synth_s[k] for k in keys3}  # synth unknown = 0
    print(f"\n== overall cause mix, conditional on recorded cause =="
          f" L1 = {l1(real_k, synth_k, keys3):.3f}")
    print(f"  {'cause':<10}{'real':>9}{'synth':>9}{'ratio':>8}")
    for k, r, s, rt in ratio_table(real_k, synth_k, keys3):
        print(f"  {k:<10}{r:>9.3f}{s:>9.3f}{rt:>8.2f}")

    # per element bucket, conditional on known cause (fair comparison: the
    # generator always records a cause; the real file leaves 12.5% blank)
    rb = defaultdict(Counter)
    sb = defaultdict(Counter)
    for b, _, c in real:
        rb[b][coarse_cause(c)] += 1
    for b, c in synth:
        sb[b][coarse_cause(c)] += 1
    print("\n== cause mix by element bucket, conditional on known cause ==")
    print("   (shares of variances with a recorded cause; u = share blank)")
    for b in sorted(set(rb) | set(sb)):
        rs, rn = shares(rb[b])
        ss, sn = shares(sb[b])
        rk = 1.0 - rs.get("unknown", 0.0)
        cells = []
        for k in ["agency", "client", "other"]:
            rr = rs.get(k, 0) / rk if rk > 0 else 0
            sr = ss.get(k, 0.0)
            cells.append(f"{k} {rr:.3f}/{sr:.3f}({sr / rr if rr else 0:.2f})")
        print(f"  {b:<12} n_real={rn:<6} n_synth={sn:<6} u={rs.get('unknown',0):.3f}  "
              + " ".join(cells))

    # where does the blank cause live? P(blank | bucket) and P(blank | nature)
    rnb = defaultdict(Counter)
    rnn = defaultdict(Counter)
    for b, ntr, c in real:
        rnb[b]["blank" if c is None else "known"] += 1
        if ntr is not None:
            rnn[ntr]["blank" if c is None else "known"] += 1
    print("\n== real P(blank cause | element bucket) ==")
    for b in sorted(rnb):
        c = rnb[b]
        tot = sum(c.values())
        print(f"  {b:<12} {c['blank'] / tot:.3f}  (n={tot})")
    print("\n== real P(blank cause | nature code) ==")
    for ntr in sorted(rnn):
        c = rnn[ntr]
        tot = sum(c.values())
        print(f"  {ntr:>3} {c['blank'] / tot:.3f}  (n={tot})")

    # fine-grained cause codes overall: locate the drivers of any gap
    rfc = Counter(c for _, _, c in real if c is not None)
    sfc = Counter(c for _, c in synth if c is not None)
    rfs, _ = shares(rfc)
    sfs, _ = shares(sfc)
    print("\n== cause codes overall (top by real share) ==")
    print(f"  {'code':>4}  {'label':<44}{'real':>8}{'synth':>8}{'ratio':>8}")
    for code, _ in rfc.most_common(15):
        r, s = rfs[code], sfs.get(code, 0.0)
        lab = CAUSE_LABELS_SHORT.get(code, str(code))
        print(f"  {code:>4}  {lab:<44}{r:>8.3f}{s:>8.3f}"
              f"{(s / r if r else 0):>8.2f}")

    # write machine-readable summary next to the script's chronicle
    out_path = ROOT / "experiments" / "exp15_cause_audit_results.json"
    json.dump(
        {"real_overall": {k: round(real_s.get(k, 0), 4) for k in keys},
         "synth_overall": {k: round(synth_s.get(k, 0), 4) for k in keys},
         "real_n": r_n, "synth_n": s_n,
         "real_by_bucket": {b: {k: round(v / sum(rb[b].values()), 4)
                                for k, v in rb[b].items()}
                            for b in rb},
         "synth_by_bucket": {b: {k: round(v / sum(sb[b].values()), 4)
                                 for k, v in sb[b].items()}
                             for b in sb},
         "real_by_code": {str(k): round(v, 4) for k, v in rfs.items()},
         "synth_by_code": {str(k): round(v, 4) for k, v in sfs.items()}},
        open(out_path, "w"), indent=2, sort_keys=True,
    )
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
