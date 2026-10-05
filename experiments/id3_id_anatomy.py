"""ID3 - Idaho SNAP QC error anatomy (microdata-only).

Compares ID (STATE=36) against national across FY2020-2024 QC public-use
files: finding mix, direction mix, dollar-error quantiles, element/nature/
cause mixes with ID-vs-national outlier ratios, top ID error patterns in
plain language, and FY trends within ID.

All rates use FYWGT sample weights. Read-only on the microdata.

Usage:
    python3 ny3_ny_anatomy.py --qc ../snap-qc-data/raw --out results.json
"""
import argparse
import csv
import json
import os
import sys

FYS = (2020, 2021, 2022, 2023, 2024)
NSLOTS = 9

ELEMENT_BUCKETS = {
    311: "earned", 312: "earned", 314: "earned", 321: "earned",
    331: "unearned", 332: "unearned", 333: "unearned", 334: "unearned",
    335: "unearned", 336: "unearned", 342: "unearned", 343: "unearned",
    344: "unearned", 345: "unearned", 346: "unearned", 350: "unearned",
    323: "depcare", 363: "shelter", 364: "sua", 365: "medical",
    366: "childsupport", 150: "hhcomp",
    211: "assets", 212: "assets", 213: "assets", 214: "assets",
    221: "assets", 222: "assets", 224: "assets", 225: "assets",
    520: "arithmetic", 540: "reporting", 542: "reporting", 560: "reporting",
    361: "standard", 371: "income_total", 372: "income_total",
}
ELEMENT_LABELS = {
    311: "Wages and salaries", 312: "Self-employment",
    314: "Other earned income", 321: "Earned income deductions",
    323: "Dependent care deduction", 331: "RSDI benefits",
    332: "Veterans' benefits", 333: "SSI",
    334: "Unemployment compensation", 335: "Workers' compensation",
    336: "Other government benefits", 342: "TANF",
    343: "General assistance", 344: "Foster care payments",
    345: "Other cash assistance", 346: "Other unearned income",
    350: "Child support received", 361: "Standard deduction",
    363: "Shelter deduction", 364: "Standard utility allowance",
    365: "Medical expense deductions", 366: "Child support deduction",
    150: "Unit composition", 520: "Arithmetic computation",
    540: "Reporting systems", 542: "Reporting systems", 560: "Reporting systems",
    371: "Total countable income", 372: "Total countable income",
    211: "Liquid assets", 212: "Vehicle assets", 213: "Other countable assets",
}
NATURE_LABELS = {
    35: "Unreported source of income",
    37: "All income from source known but not included",
    38: "More income received from this source than budgeted",
    39: "Employment status changed from unemployed to employed",
    40: "Employment status changed from employed to unemployed",
    41: "Change only in amount of earnings",
    44: "Less income received from this source than budgeted",
    45: "Cost of doing business not used or incorrectly applied",
    52: "Deduction that should have been included was not",
    53: "Deduction included that should not have been",
    54: "Incorrect standard used",
    56: "Incorrect deduction amount included - budgeted too much",
    57: "Incorrect deduction amount included - budgeted too little",
    64: "Incorrect amount used resulting from change in residence",
    75: "Benefit/allotment/eligibility incorrectly computed",
    80: "Improper prorating of initial month's benefits",
    97: "Not required to be reported or acted upon (time frames/reporting)",
    98: "Transcription or computation errors",
    99: "Other",
}
CAUSE_LABELS = {
    1: "Information not reported",
    2: "Incomplete/incorrect info provided; agency not required to verify",
    3: "Information withheld by client (IPV)",
    4: "Incorrect information provided by client (IPV)",
    7: "Inaccurate info reported by collateral contact",
    10: "Policy incorrectly applied",
    12: "Reported information disregarded or not applied",
    14: "Agency failed to follow up on inconsistent/incomplete information",
    15: "Agency failed to follow up on impending changes",
    16: "Agency failed to verify required information",
    17: "Computer programming error",
    18: "Data entry and/or coding error",
    19: "Mass change (computer-generated)",
    20: "Arithmetic computation error",
    21: "Computer user error",
    22: "Agency budgeted an incorrect amount",
    23: "Failed recertification procedure: notices/forms",
    25: "Failed recertification procedure: time frames",
    26: "Change not required to be reported/acted upon",
    99: "Other",
}
CAUSE_BUCKETS = {
    1: "client", 2: "client", 4: "client",
    10: "agency", 12: "agency", 14: "agency", 16: "agency",
    18: "agency", 19: "agency", 20: "agency", 21: "agency", 22: "agency",
    26: "no_fault",
}


def wquant(vals, wts, qs):
    pairs = sorted((v, w) for v, w in zip(vals, wts) if w > 0)
    tot = sum(w for _, w in pairs)
    out = []
    for q in qs:
        target = q * tot
        cum = 0.0
        val = pairs[-1][0]
        for v, w in pairs:
            cum += w
            if cum >= target:
                val = v
                break
        out.append(val)
    return out


def load(qc_dir):
    cols = ["STATE", "STATUS", "FSBEN", "RAWBEN", "AMTERR", "FYWGT"]
    cols += [f"ELEMENT{i}" for i in range(1, NSLOTS + 1)]
    cols += [f"NATURE{i}" for i in range(1, NSLOTS + 1)]
    cols += [f"AGENCY{i}" for i in range(1, NSLOTS + 1)]
    rows = []
    for fy in FYS:
        path = os.path.join(qc_dir, f"qcfy{fy}_csv", f"qc_pub_fy{fy}.csv")
        with open(path, newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    w = float(row["FYWGT"] or 0)
                except ValueError:
                    w = 0.0
                if w <= 0:
                    continue
                try:
                    amterr = float(row["AMTERR"] or 0)
                except ValueError:
                    amterr = 0.0
                slots = []
                for i in range(1, NSLOTS + 1):
                    e = row[f"ELEMENT{i}"]
                    n = row[f"NATURE{i}"]
                    c = row[f"AGENCY{i}"]
                    if e and e.strip():
                        slots.append((int(float(e)), int(float(n)) if n and n.strip() else None,
                                      int(float(c)) if c and c.strip() else None))
                rows.append({
                    "fy": fy,
                    "state": row["STATE"],
                    "id": row["STATE"] == "16",
                    "status": row["STATUS"],
                    "w": w,
                    "amterr": amterr,
                    "slots": slots,
                })
    return rows


def share_of(d, total):
    return {k: (v / total if total else 0.0) for k, v in d.items()}


def mix(rows, key):
    d = {}
    tot = 0.0
    for r in rows:
        d[key(r)] = d.get(key(r), 0.0) + r["w"]
        tot += r["w"]
    return share_of(d, tot), d, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = load(a.qc)
    id = [r for r in rows if r["id"]]
    us = rows
    errors_id = [r for r in id if r["status"] in ("2", "3")]
    errors_us = [r for r in us if r["status"] in ("2", "3")]

    out = {"n_rows": len(rows), "n_id": len(id),
           "n_errors_id": len(errors_id), "n_errors_us": len(errors_us)}

    # 1a. Finding mix, weighted, ID vs national, overall
    fmix_id, fraw_id, ftot_id = mix(id, lambda r: r["status"])
    fmix_us, fraw_us, ftot_us = mix(us, lambda r: r["status"])
    out["finding_mix"] = {"id": fmix_id, "us": fmix_us,
                          "wtot_id": ftot_id, "wtot_us": ftot_us}

    # 1b. Direction mix among errors
    dmix_id, _, _ = mix(errors_id, lambda r: r["status"])
    dmix_us, _, _ = mix(errors_us, lambda r: r["status"])
    out["direction_mix_errors"] = {"id": dmix_id, "us": dmix_us}

    # 1c. Dollar-error quantiles
    for name, err in (("id", errors_id), ("us", errors_us)):
        vals = [r["amterr"] for r in err]
        wts = [r["w"] for r in err]
        q = wquant(vals, wts, [0.10, 0.25, 0.50, 0.75, 0.90])
        over = [r for r in err if r["status"] == "2"]
        under = [r for r in err if r["status"] == "3"]
        out.setdefault("amterr_quantiles", {})[name] = {
            "all": dict(zip(["p10", "p25", "p50", "p75", "p90"], q)),
            "over": dict(zip(["p10", "p25", "p50", "p75", "p90"],
                             wquant([r["amterr"] for r in over], [r["w"] for r in over],
                                    [0.10, 0.25, 0.50, 0.75, 0.90]))),
            "under": dict(zip(["p10", "p25", "p50", "p75", "p90"],
                              wquant([r["amterr"] for r in under], [r["w"] for r in under],
                                     [0.10, 0.25, 0.50, 0.75, 0.90]))),
        }

    # 2. Element / nature / cause mixes on primary variance (slot 1), errors only
    def primary(r):
        return r["slots"][0] if r["slots"] else (None, None, None)

    def mix2(err, idx, buck=None):
        d = {}
        tot = 0.0
        for r in err:
            v = primary(r)[idx]
            if v is None:
                continue
            k = buck(v) if buck else v
            d[k] = d.get(k, 0.0) + r["w"]
            tot += r["w"]
        return share_of(d, tot), d, tot

    def eratio(ny_s, us_s):
        r = {}
        for k in set(ny_s) | set(us_s):
            ns, uss = ny_s.get(k, 0.0), us_s.get(k, 0.0)
            r[k] = (ns / uss) if uss > 0 else (float("inf") if ns > 0 else 0.0)
        return r

    eb_id, eb_raw_id, _ = mix2(errors_id, 0, lambda v: ELEMENT_BUCKETS.get(v, "other"))
    eb_us, eb_raw_us, _ = mix2(errors_us, 0, lambda v: ELEMENT_BUCKETS.get(v, "other"))
    nat_id, nat_raw_id, _ = mix2(errors_id, 1)
    nat_us, nat_raw_us, _ = mix2(errors_us, 1)
    cau_id, cau_raw_id, _ = mix2(errors_id, 2)
    cau_us, cau_raw_us, _ = mix2(errors_us, 2)
    cbuck_id, _, _ = mix2(errors_id, 2, lambda v: CAUSE_BUCKETS.get(v, "other"))
    cbuck_us, _, _ = mix2(errors_us, 2, lambda v: CAUSE_BUCKETS.get(v, "other"))

    out["element_bucket_mix"] = {"id": eb_id, "us": eb_us,
                                 "ratio_ny_over_us": eratio(eb_id, eb_us)}
    out["nature_mix"] = {"id": nat_id, "us": nat_us,
                         "ratio_ny_over_us": eratio(nat_id, nat_us),
                         "labels": {str(k): NATURE_LABELS.get(k, "?") for k in set(nat_id) | set(nat_us)}}
    out["cause_mix"] = {"id": cau_id, "us": cau_us,
                        "ratio_ny_over_us": eratio(cau_id, cau_us),
                        "labels": {str(k): CAUSE_LABELS.get(k, "?") for k in set(cau_id) | set(cau_us)}}
    out["cause_bucket_mix"] = {"id": cbuck_id, "us": cbuck_us,
                               "ratio_ny_over_us": eratio(cbuck_id, cbuck_us)}
    # raw element code mix (for label checks)
    ec_id, ec_raw_id, ec_tot_id = mix2(errors_id, 0)
    ec_us, ec_raw_us, _ = mix2(errors_us, 0)
    out["element_code_mix"] = {"id": ec_id, "us": ec_us,
                               "ratio_ny_over_us": eratio(ec_id, ec_us)}
    out["w_primary_variances_id"] = ec_tot_id

    # all-slots sensitivity: each variance slot weighted by case weight
    def mix_all(err, idx, buck=None):
        d = {}
        tot = 0.0
        for r in err:
            for s in r["slots"]:
                v = s[idx]
                if v is None:
                    continue
                k = buck(v) if buck else v
                d[k] = d.get(k, 0.0) + r["w"]
                tot += r["w"]
        return share_of(d, tot)
    out["element_bucket_mix_allslots"] = {
        "id": mix_all(errors_id, 0, lambda v: ELEMENT_BUCKETS.get(v, "other")),
        "us": mix_all(errors_us, 0, lambda v: ELEMENT_BUCKETS.get(v, "other"))}

    # 3. Top ID patterns: (element bucket, nature), weighted counts
    pat = {}
    for r in errors_id:
        e, n, c = primary(r)
        if e is None:
            continue
        k = (ELEMENT_BUCKETS.get(e, "other"), n)
        if k not in pat:
            pat[k] = {"w": 0.0, "n": 0, "dir": {"2": 0.0, "3": 0.0},
                      "amterr": [], "amw": [], "el_codes": {}}
        p = pat[k]
        p["w"] += r["w"]
        p["n"] += 1
        p["dir"][r["status"]] = p["dir"].get(r["status"], 0.0) + r["w"]
        p["amterr"].append(r["amterr"])
        p["amw"].append(r["w"])
        p["el_codes"][e] = p["el_codes"].get(e, 0.0) + r["w"]
    tot_pw = sum(p["w"] for p in pat.values())
    pats = []
    for (eb, n), p in pat.items():
        q = wquant(p["amterr"], p["amw"], [0.50])[0]
        us_share = 0.0
        # national share of same pattern
        usw = sum(r["w"] for r in errors_us
                  if r["slots"] and ELEMENT_BUCKETS.get(r["slots"][0][0], "other") == eb
                  and r["slots"][0][1] == n)
        us_tot = sum(r["w"] for r in errors_us if r["slots"])
        us_share = usw / us_tot if us_tot else 0.0
        top_el = max(p["el_codes"].items(), key=lambda kv: kv[1])[0]
        pats.append({"element_bucket": eb, "nature": n,
                     "nature_label": NATURE_LABELS.get(n, "?"),
                     "top_element_code": top_el,
                     "top_element_label": ELEMENT_LABELS.get(top_el, "?"),
                     "w": p["w"], "share_id": p["w"] / tot_pw if tot_pw else 0,
                     "n_rows": p["n"], "w_over": p["dir"].get("2", 0.0),
                     "w_under": p["dir"].get("3", 0.0), "median_amterr": q,
                     "share_us": us_share,
                     "ratio": (p["w"] / tot_pw) / us_share if us_share else None})
    pats.sort(key=lambda x: -x["w"])
    out["patterns"] = pats

    # 4. FY trend within ID
    fy = {}
    for y in FYS:
        pr = [r for r in id if r["fy"] == y]
        er = [r for r in pr if r["status"] in ("2", "3")]
        fm, _, _ = mix(pr, lambda r: r["status"])
        dm, _, _ = mix(er, lambda r: r["status"])
        eb, _, _ = mix2(er, 0, lambda v: ELEMENT_BUCKETS.get(v, "other"))
        cb, _, _ = mix2(er, 2, lambda v: CAUSE_BUCKETS.get(v, "other"))
        fy[y] = {"n": len(pr), "n_err": len(er), "finding": fm,
                 "direction": dm, "element_bucket": eb, "cause_bucket": cb}
    out["fy_trend_id"] = fy

    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
