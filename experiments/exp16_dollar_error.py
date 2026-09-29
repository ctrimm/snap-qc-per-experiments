"""Experiment 16 - dollar-error distribution re-check.

North-star gate: calibration. exp1 (early generator) had dollar-error p90 of
77 synth vs 78 real; since then the generator changed substantially (exps 3/5/6/7:
direction fixes, omission coherence, eligibility-screen injection, per-bucket
persistence). This script recomputes the dollar-error marginal on both sides.

Real side: FY2024 QC microdata (held-out; NEVER committed). Signed dollar error
= AMTERR (non-negative per tech doc) with sign from STATUS (2=over => positive,
3=under => negative). AMTERR is used rather than RAWBEN-FSBEN because the two
disagree on ~22% of error cases (median discrepancy $1, p90 $145, max $6368);
the tech doc defines AMTERR as the authoritative "amount of benefit in error"
and uses it directly in consistency checks, e.g. "STATUS = 2 and RAWBEN <= AMTERR".

Synth side: cases from src/synth/generate.py (persistent buckets on by default,
exp7). Signed dollar error = issued_benefit - correct_benefit (== +/- dollar_error
keyed by finding: 2=over, 3=under).

Usage:
    python3 experiments/exp16_dollar_error.py \
        --real ~/workspace/snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv \
        --synth /tmp/exp16_synth.jsonl
"""
import argparse
import csv
import json
import statistics
import sys

QUANTS = (0.10, 0.25, 0.50, 0.75, 0.90, 0.99)


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarize(signed, label):
    ab = [abs(x) for x in signed]
    overs = [x for x in signed if x > 0]
    unders = [-x for x in signed if x < 0]
    s = {
        "label": label,
        "n_error": len(signed),
        "n_over": len(overs),
        "n_under": len(unders),
    }
    for q in QUANTS:
        s[f"p{int(q*100)}"] = pct(ab, q)
    s["mean"] = statistics.fmean(ab) if ab else float("nan")
    s["median_over"] = pct(overs, 0.5)
    s["median_under"] = pct(unders, 0.5)
    s["mean_over"] = statistics.fmean(overs) if overs else float("nan")
    s["mean_under"] = statistics.fmean(unders) if unders else float("nan")
    # breakdown by finding (only for error cases; zeros excluded from both)
    s["p50_over"] = pct(overs, 0.5)
    s["p90_over"] = pct(overs, 0.9)
    s["p50_under"] = pct(unders, 0.5)
    s["p90_under"] = pct(unders, 0.9)
    return s


def load_real(path):
    signed = []
    n = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            n += 1
            st = row["STATUS"].strip()
            if st not in ("2", "3"):
                continue
            amterr = float(row["AMTERR"] or 0)
            signed.append(amterr if st == "2" else -amterr)
    return signed, n


def load_synth(path):
    signed = []
    n = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n += 1
            case = json.loads(line)
            finding = case["finding"]
            if finding not in (2, 3):
                continue
            s = case["issued_benefit"] - case["correct_benefit"]
            # consistency: sign must match finding
            assert (s > 0) == (finding == 2), (case["finding"], s)
            assert abs(s) == case["dollar_error"], (s, case["dollar_error"])
            signed.append(s)
    return signed, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--synth", required=True)
    args = ap.parse_args()

    real_signed, real_n = load_real(args.real)
    synth_signed, synth_n = load_synth(args.synth)
    r = summarize(real_signed, "real")
    s = summarize(synth_signed, "synth")

    print(f"real: {real_n} rows, {r['n_error']} error cases "
          f"(over {r['n_over']}, under {r['n_under']})")
    print(f"synth: {synth_n} rows, {s['n_error']} error cases "
          f"(over {s['n_over']}, under {s['n_under']})")

    rows = ["p10", "p25", "p50", "p75", "p90", "p99", "mean"]
    print("\n== absolute dollar error (error cases only) ==")
    print(f"{'stat':>6} {'real':>9} {'synth':>9} {'ratio s/r':>10}")
    for k in rows:
        rv, sv = r[k], s[k]
        print(f"{k:>6} {rv:9.1f} {sv:9.1f} {sv/rv:10.2f}")

    print("\n== over vs under dollar asymmetry (absolute $ within each finding) ==")
    print(f"{'stat':>12} {'real':>9} {'synth':>9}")
    for k, lab in [("median_over", "median over"), ("median_under", "median under"),
                   ("mean_over", "mean over"), ("mean_under", "mean under"),
                   ("p50_over", "p50 over"), ("p90_over", "p90 over"),
                   ("p50_under", "p50 under"), ("p90_under", "p90 under")]:
        print(f"{lab:>12} {r[k]:9.1f} {s[k]:9.1f}")

    out = {"real": r, "synth": s}
    with open("/tmp/exp16_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nresults -> /tmp/exp16_results.json")


if __name__ == "__main__":
    sys.exit(main())
