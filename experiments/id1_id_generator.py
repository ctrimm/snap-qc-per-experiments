"""ID1: ID-conditioned SNAP QC synthetic generator.

Fits Idaho empirical targets from QC public-use microdata (READ-ONLY,
never committed), bakes them as ID/national offset ratios, and validates the
ID-conditioned generator (src/synth/id_state.py) against real ID marginals.

Usage:
    python3 experiments/id1_id_generator.py fit
        # recompute ID targets from microdata; prints the ID_* constants
        # baked into src/synth/id_state.py (documents their provenance)
    python3 experiments/id1_id_generator.py validate --qc ~/workspace/snap-qc-data/raw
        # generate national + ID-conditioned cases, report validation metrics

North-star gates: calibration (synthetic ID marginals match real ID QC) and
transfer (ID-conditioned training data for the ID chain; ID2 trains on it).
"""
import argparse
import csv
import json
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.synth.codebook import element_bucket, cause_bucket  # noqa: E402

QC_DEFAULT = str(Path.home() / "workspace" / "snap-qc-data" / "raw")
# Fitting window: FY2022-2024 only. FY2020 (n=515) and FY2021 (n=213) are
# partial-year/thin QC files for Idaho; the NY6 lesson (partial-year files
# move the fitted error rate ~1.9pp and distort bucket ratios) is adopted
# as a standing rule — exclude them from generator fitting. The ID2
# holdout is still built on all pooled FY2020-2024 rows (the national arm
# is unaffected; the state-synth arm is simply calibrated to the FY22-24
# process regime).
FYS = [2022, 2023, 2024]
ID_STATE = "16"
SUPPORTED = ("earned", "unearned", "shelter", "sua", "medical",
             "depcare", "hhcomp", "arithmetic")


def senior_disabled(row):
    if row.get("FSELDER") == "1":
        return True
    for i in range(1, 13):
        if row.get(f"DIS{i}") == "1":
            return True
    return False


def fnum(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def fit_id_targets(qc_dir=QC_DEFAULT, fys=FYS):
    """Compute ID and national empirical targets from microdata.

    Returns dict with 'id'/'nat' marginals plus ID/nat ratios. All aggregates
    FYWGT-weighted; rates are microdata-implied (NOT FNS-published).
    Mirrors ny1_ny_generator.fit_id_targets with STATE='16'.
    """
    finding = {"id": Counter(), "nat": Counter()}
    err_cond = {"id": defaultdict(float), "nat": defaultdict(float)}
    amterr = {"id": [], "nat": []}          # (weight, |amterr|, status)
    w_amterr = {"id": 0.0, "nat": 0.0}
    w_fsben = {"id": 0.0, "nat": 0.0}
    near_full = {"id": [0.0, 0.0], "nat": [0.0, 0.0]}  # [w, over w]
    bucket = {"id": Counter(), "nat": Counter()}       # variance-level, supported only
    bucket_n = {"id": Counter(), "nat": Counter()}     # unweighted case counts per bucket
    nature = {"id": Counter(), "nat": Counter()}       # (bucket, nature) -> w
    nature_n = {"id": Counter(), "nat": Counter()}     # unweighted
    p97 = {"id": defaultdict(lambda: [0.0, 0.0]),
           "nat": defaultdict(lambda: [0.0, 0.0])}     # bucket -> [over w, tot w]
    p97_n = {"id": Counter(), "nat": Counter()}        # unweighted 97 counts per bucket
    cause = {"id": Counter(), "nat": Counter()}        # (bucket, coarse) -> w, non-blank
    cause97 = {"id": Counter(), "nat": Counter()}      # (bucket, rawcode) -> w, 97 only
    cause97_n = {"id": Counter(), "nat": Counter()}    # unweighted 97-cause counts
    causenon97 = {"id": Counter(), "nat": Counter()}   # (bucket, coarse) -> w, non-97 only
    cause97blank = {"id": [0.0, 0.0], "nat": [0.0, 0.0]}
    n_id = 0

    for fy in fys:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                is_id = row["STATE"] == ID_STATE
                g = "id" if is_id else "nat"
                w = fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                n_id += is_id
                status = row["STATUS"].strip()
                finding[g][status] += w
                ek = "earner" if fnum(row.get("FSEARN")) > 0 else "no_earner"
                if status in ("2", "3"):
                    err_cond[g][(ek, "err")] += w
                err_cond[g][(ek, "tot")] += w
                am = fnum(row.get("AMTERR"))
                w_amterr[g] += w * am
                w_fsben[g] += w * fnum(row.get("FSBEN"))
                if status in ("2", "3"):
                    amterr[g].append((w, abs(am), status))
                    if status == "2":
                        raw = fnum(row.get("RAWBEN"))
                        near_full[g][1] += w
                        if raw > 0 and abs(am) / raw >= 0.9:
                            near_full[g][0] += w
                    for i in range(1, 10):
                        e = (row.get(f"ELEMENT{i}") or "").strip()
                        if not e or e == "0":
                            continue
                        try:
                            ei = int(float(e))
                        except ValueError:
                            continue
                        b = element_bucket(ei)
                        if b not in SUPPORTED:
                            continue
                        n = (row.get(f"NATURE{i}") or "").strip()
                        c = (row.get(f"AGENCY{i}") or "").strip()
                        ni = int(float(n)) if n and n != "0" else None
                        ci = int(float(c)) if c and c != "0" else None
                        bucket[g][b] += w
                        bucket_n[g][b] += 1
                        if ni is not None:
                            nature[g][(b, ni)] += w
                            nature_n[g][(b, ni)] += 1
                            if ni == 97:
                                p97[g][b][1] += w
                                p97_n[g][b] += 1
                                if status == "2":
                                    p97[g][b][0] += w
                                cause97blank[g][1] += w
                                if ci is None:
                                    cause97blank[g][0] += w
                                else:
                                    cause97[g][(b, ci)] += w
                                    cause97_n[g][(b, ci)] += 1
                            elif ci is not None:
                                causenon97[g][(b, cause_bucket(ci))] += w
                        if ci is not None:
                            cause[g][(b, cause_bucket(ci))] += w

    def wq(pairs, q):
        tot = sum(w for w, _ in pairs)
        tgt, acc = tot * q, 0.0
        for w, v in sorted(pairs, key=lambda t: t[1]):
            acc += w
            if acc >= tgt:
                return v
        return pairs[-1][1]

    t = {"n_id_rows": n_id, "id": {}, "nat": {}}
    for g in ("id", "nat"):
        tot = sum(finding[g].values())
        fm = {s: finding[g][s] / tot for s in ("1", "2", "3")}
        P = amterr[g]
        tw = sum(w for w, _, _ in P)
        qs = {q: wq([(w, v) for w, v, _ in P], q)
              for q in (0.10, 0.25, 0.50, 0.90)}
        over = [(w, v) for w, v, s in P if s == "2"]
        under = [(w, v) for w, v, s in P if s == "3"]
        t[g] = {
            "finding_mix": fm,
            "case_err_rate": (finding[g]["2"] + finding[g]["3"]) / tot,
            "dollar_rate": w_amterr[g] / w_fsben[g],
            "p_err_earner": err_cond[g][("earner", "err")] / err_cond[g][("earner", "tot")],
            "p_err_no_earner": err_cond[g][("no_earner", "err")] / err_cond[g][("no_earner", "tot")],
            "p_over_given_err": finding[g]["2"] / (finding[g]["2"] + finding[g]["3"]),
            "near_full_given_over": near_full[g][0] / near_full[g][1],
            "dollar_q": qs,
            "dollar_mean": sum(w * v for w, v, _ in P) / tw,
            "share_le56": sum(w for w, v, _ in P if v <= 56) / tw,
            "medO": wq(over, 0.50),
            "medU": wq(under, 0.50),
            "cause97_blank": cause97blank[g][0] / cause97blank[g][1],
        }
    # ratios
    id, nat = t["id"], t["nat"]
    # behavioral direction classes (match id_state.ID_OVER/UNDER_NATURES)
    OVER = {35, 37, 38, 39, 53, 56, 7}
    UNDER = {44, 52, 57, 6, 13}
    t["ratios"] = {
        "coin": {s: id[f"p_err_{s}"] / nat[f"p_err_{s}"]
                for s in ("earner", "no_earner")},
        "bucket": {},
        "nature97share": {},
        "naturedir": {},
        "cause_non97": {},
        "cause97": {},
        "p97": {},
        "s_over": id["medO"] / nat["medO"],
        "s_under": id["medU"] / nat["medU"],
    }
    tb_id = sum(bucket["id"].values())
    tb_nat = sum(bucket["nat"].values())
    for b in SUPPORTED:
        r = (bucket["id"][b] / tb_id) / (bucket["nat"][b] / tb_nat)
        # sparsity guard: ID unweighted bucket n < 25 -> no adjustment
        t["ratios"]["bucket"][b] = r if bucket_n["id"][b] >= 25 else 1.0
    for b in SUPPORTED:
        # 97-share margin: P(97|b); guard ID unweighted 97-n < 5
        tot_id = sum(v for (bb, _), v in nature["id"].items() if bb == b)
        tot_nat = sum(v for (bb, _), v in nature["nat"].items() if bb == b)
        if p97_n["id"][b] >= 5 and tot_id > 0 and tot_nat > 0:
            r = (nature["id"][(b, 97)] / tot_id) / (nature["nat"][(b, 97)] / tot_nat)
            t["ratios"]["nature97share"][b] = r
        else:
            t["ratios"]["nature97share"][b] = 1.0
        # direction margins among non-97; guard ID unweighted non-97 n < 25
        nn97_id = sum(v for (bb, n_), v in nature["id"].items()
                      if bb == b and n_ != 97)
        nn97_nat = sum(v for (bb, n_), v in nature["nat"].items()
                       if bb == b and n_ != 97)
        dr = {}
        for k, nset in (("over", OVER), ("under", UNDER)):
            pk = sum(v for (bb, n_), v in nature["id"].items()
                     if bb == b and n_ in nset) / nn97_id if nn97_id else 0
            qk = sum(v for (bb, n_), v in nature["nat"].items()
                     if bb == b and n_ in nset) / nn97_nat if nn97_nat else 0
            dr[k] = pk / qk if qk > 0 else 1.0
        nn97_n_id = bucket_n["id"][b] - p97_n["id"][b]
        t["ratios"]["naturedir"][b] = dr if nn97_n_id >= 25 else \
            {"over": 1.0, "under": 1.0}
    for b in SUPPORTED:
        tc_id = sum(v for (bb, _), v in causenon97["id"].items() if bb == b)
        tc_nat = sum(v for (bb, _), v in causenon97["nat"].items() if bb == b)
        for co in ("client", "agency", "no_fault", "other"):
            # guard: ID unweighted bucket n < 25 -> no adjustment
            if bucket_n["id"][b] < 25 or tc_id == 0 or tc_nat == 0:
                r = 1.0
            else:
                p = causenon97["id"][(b, co)] / tc_id
                q = causenon97["nat"][(b, co)] / tc_nat
                r = p / q if q > 0 else 1.0
            t["ratios"]["cause_non97"][(b, co)] = r
    # ID empirical 97-cause mix per bucket (raw codes); fallback pooled
    pool = Counter()
    for (b, c), w in cause97["id"].items():
        pool[c] += w
    ptot = sum(pool.values())
    for b in SUPPORTED:
        nu = sum(v for (bb, _), v in cause97_n["id"].items() if bb == b)
        tot = sum(v for (bb, _), v in cause97["id"].items() if bb == b)
        if nu >= 5 and tot > 0:
            t["ratios"]["cause97"][b] = {
                c: v / tot for (bb, c), v in cause97["id"].items() if bb == b}
        else:
            t["ratios"]["cause97"][b] = {c: v / ptot for c, v in pool.items()}
    for b in SUPPORTED:
        o_id, tot_id = p97["id"][b]
        o_nat, tot_nat = p97["nat"][b]
        if p97_n["id"][b] >= 5 and tot_nat > 0 and o_nat > 0:
            t["ratios"]["p97"][b] = (o_id / tot_id) / (o_nat / tot_nat)
        else:
            t["ratios"]["p97"][b] = 1.0
    t["id_cause97_blank"] = id["cause97_blank"]
    return t


def cmd_fit(args):
    t = fit_id_targets()
    id, nat, R = t["id"], t["nat"], t["ratios"]
    print(f"# ID rows pooled FY2020-2024: {t['n_id_rows']}")
    print("# ID vs national empirical targets (FYWGT-weighted, microdata-implied)")
    for g, d in (("id", id), ("nat", nat)):
        m = d["finding_mix"]
        print(f"# {g}: finding c/o/u {m['1']:.4f}/{m['2']:.4f}/{m['3']:.4f} "
              f"case_err {d['case_err_rate']:.4f} dollar_rate {d['dollar_rate']:.4f} "
              f"p(err|earn) {d['p_err_earner']:.4f} p(err|noearn) {d['p_err_no_earner']:.4f} "
              f"p(over|err) {d['p_over_given_err']:.4f}")
        q = d["dollar_q"]
        print(f"#   dollar: p10 {q[0.10]:.0f} p25 {q[0.25]:.0f} p50 {q[0.50]:.0f} "
              f"p90 {q[0.90]:.0f} mean {d['dollar_mean']:.0f} le56 {d['share_le56']:.3f} "
              f"medO {d['medO']:.0f} medU {d['medU']:.0f}")
    print(f"# cause97 blank: id {t['id_cause97_blank']:.3f} nat {nat['cause97_blank']:.3f}")
    print(f"# near-full|over: id {id['near_full_given_over']:.4f} nat {nat['near_full_given_over']:.4f}")
    print()
    print("ID_COIN_RATIO = " + repr({k: round(v, 4) for k, v in R["coin"].items()}))
    print("ID_BUCKET_RATIO = " + repr({k: round(v, 4) for k, v in R["bucket"].items()}))
    print("ID_97_RATIO = " + repr({k: round(v, 4) for k, v in R["p97"].items()}))
    print(f"ID_S_OVER = {R['s_over']:.4f}")
    print(f"ID_S_UNDER = {R['s_under']:.4f}")
    print(f"ID_CAUSE97_BLANK = {t['id_cause97_blank']:.4f}")
    print("ID_97_SHARE_RATIO = " + repr({k: round(v, 4) for k, v in R["nature97share"].items()}))
    print("ID_DIR_RATIO = {")
    for b, dr in R["naturedir"].items():
        print(f"    {b!r}: {{'over': {dr['over']:.4f}, 'under': {dr['under']:.4f}}},")
    print("}")
    print("ID_CAUSE_RATIO = {")
    for b in SUPPORTED:
        cells = {c: R["cause_non97"][(b, c)] for c in ("client", "agency", "no_fault", "other")}
        print(f"    {b!r}: " + repr({k: round(v, 4) for k, v in cells.items()}) + ",")
    print("}")
    print("ID_97_CAUSE = {")
    for b, mix in R["cause97"].items():
        print(f"    {b!r}: " + repr({str(c): round(v, 4) for c, v in sorted(mix.items())}) + ",")
    print("}")


def _run_gen_id(n, seed, out):
    from src.synth import id_state
    id_state.generate_id(n=n, seed=seed, dist="experiments/dist.json", out=out)


def _run_gen_nat(n, seed, out):
    subprocess.run(
        [sys.executable, "-m", "src.synth.generate", "--n", str(n),
         "--seed", str(seed), "--dist", "experiments/dist.json", "--out", out],
        check=True, cwd=str(Path(__file__).resolve().parent.parent))


def _l1(a, b):
    keys = set(a) | set(b)
    return sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)


def _synth_marginals(path):
    find = Counter()
    bucket = Counter()
    cause = Counter()
    dollars = []
    over_u = []
    w_amterr = 0.0
    w_fsben = 0.0
    n = 0
    with open(path) as fh:
        for line in fh:
            c = json.loads(line)
            n += 1
            f = c["finding"]
            find[f] += 1
            w_amterr += c["dollar_error"]
            w_fsben += c["correct_benefit"]
            if f in (2, 3):
                dollars.append(c["dollar_error"])
                over_u.append(1 if f == 2 else 0)
                for v in c["variances"]:
                    bucket[v["element_bucket"]] += 1
                    if v["cause"] is not None:
                        cause[cause_bucket(v["cause"])] += 1
    dollars.sort()
    def q(p):
        return dollars[min(int(p * len(dollars)), len(dollars) - 1)]
    return {
        "n": n,
        "finding_mix": {1: find[1] / n, 2: find[2] / n, 3: find[3] / n},
        "case_err_rate": (find[2] + find[3]) / n,
        "dollar_rate": w_amterr / w_fsben if w_fsben else 0,
        "p_over_given_err": sum(over_u) / len(over_u) if over_u else 0,
        "bucket": {b: bucket[b] / sum(bucket.values()) for b in bucket},
        "cause": {c_: cause[c_] / sum(cause.values()) for c_ in cause},
        "dollar_q": {p_: q(p_) for p_ in (0.10, 0.25, 0.50, 0.90)},
        "dollar_mean": statistics.mean(dollars) if dollars else 0,
        "share_le56": sum(1 for d in dollars if d <= 56) / len(dollars) if dollars else 0,
    }


def cmd_validate(args):
    from src.synth import id_state  # noqa: F401  (import must be side-effect-free)
    t = fit_id_targets(args.qc)
    id = t["id"]
    tmp = Path("/tmp/id1_validate")
    tmp.mkdir(exist_ok=True)
    nat_out, id_out = str(tmp / "nat.jsonl"), str(tmp / "id.jsonl")
    print("generating national...", file=sys.stderr)
    _run_gen_nat(args.n, args.seed, nat_out)
    print("generating ID-conditioned...", file=sys.stderr)
    _run_gen_id(args.n, args.seed, id_out)
    nat = _synth_marginals(nat_out)
    ns = _synth_marginals(id_out)

    print(f"\n== validation: ID-conditioned synth (n={args.n}, seed={args.seed}) vs real ID ==")
    fm_id = {1: id["finding_mix"]["1"], 2: id["finding_mix"]["2"], 3: id["finding_mix"]["3"]}
    print(f"finding L1 (ID synth vs ID real): {_l1(ns['finding_mix'], fm_id):.4f}")
    print(f"  synth {ns['finding_mix'][1]:.4f}/{ns['finding_mix'][2]:.4f}/{ns['finding_mix'][3]:.4f} "
          f"real {fm_id[1]:.4f}/{fm_id[2]:.4f}/{fm_id[3]:.4f}")
    # real ID bucket / cause mixes recomputed on the recorded basis for comparison
    real_bucket, real_cause = _real_id_var_mixes(args.qc)
    print(f"element L1 (ID synth vs ID real): {_l1(ns['bucket'], real_bucket):.4f}")
    print(f"cause L1 (ID synth vs ID real): {_l1(ns['cause'], real_cause):.4f}")
    print("dollar quantiles (ID synth vs ID real):")
    for p_ in (0.10, 0.25, 0.50, 0.90):
        print(f"  p{int(p_*100)}: synth {ns['dollar_q'][p_]:.0f}  real {id['dollar_q'][p_]:.0f}")
    print(f"  mean: synth {ns['dollar_mean']:.0f}  real {id['dollar_mean']:.0f} | "
          f"share<=$56: synth {ns['share_le56']:.3f}  real {id['share_le56']:.3f}")
    print("offset recovery (ID minus national):")
    print(f"  case_err_rate: real {id['case_err_rate']-t['nat']['case_err_rate']:+.4f} | "
          f"synth {ns['case_err_rate']-nat['case_err_rate']:+.4f}")
    print(f"  dollar_rate:   real {id['dollar_rate']-t['nat']['dollar_rate']:+.4f} | "
          f"synth {ns['dollar_rate']-nat['dollar_rate']:+.4f}")
    print(f"  p(over|err):   real {id['p_over_given_err']-t['nat']['p_over_given_err']:+.4f} | "
          f"synth {ns['p_over_given_err']-nat['p_over_given_err']:+.4f}")
    print("\nnational-mode sanity (should match the generator's published calibration):")
    print(f"  nat synth finding c/o/u "
          f"{nat['finding_mix'][1]:.3f}/{nat['finding_mix'][2]:.3f}/{nat['finding_mix'][3]:.3f} "
          f"(exp31 adopted: 0.610/0.241/0.149)")


def _real_id_var_mixes(qc_dir):
    """Real ID recorded variance mixes on the generator's recorded basis."""
    bucket = Counter()
    cause = Counter()
    for fy in FYS:
        path = f"{qc_dir}/qcfy{fy}_csv/qc_pub_fy{fy}.csv"
        with open(path, newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                if row["STATE"] != ID_STATE or row["STATUS"].strip() not in ("2", "3"):
                    continue
                w = fnum(row.get("FYWGT"), 1.0)
                if w <= 0:
                    continue
                for i in range(1, 10):
                    e = (row.get(f"ELEMENT{i}") or "").strip()
                    if not e or e == "0":
                        continue
                    try:
                        ei = int(float(e))
                    except ValueError:
                        continue
                    b = element_bucket(ei)
                    if b not in SUPPORTED:
                        continue
                    bucket[b] += w
                    c = (row.get(f"AGENCY{i}") or "").strip()
                    # recorded basis: skip blank causes (97 blanking in the
                    # microdata mirrors what the generator's _recorded_cause
                    # wrapper produces for ID)
                    if c and c != "0":
                        cause[cause_bucket(int(float(c)))] += w
    tb, tc = sum(bucket.values()), sum(cause.values())
    return ({b: bucket[b] / tb for b in bucket},
            {c_: cause[c_] / tc for c_ in cause})


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fit", help="recompute ID targets; print baked constants")
    v = sub.add_parser("validate", help="generate + compare vs real ID marginals")
    v.add_argument("--qc", default=QC_DEFAULT)
    v.add_argument("--n", type=int, default=20000)
    v.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    if args.cmd == "fit":
        cmd_fit(args)
    else:
        cmd_validate(args)


if __name__ == "__main__":
    main()
