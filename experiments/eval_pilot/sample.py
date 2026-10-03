"""Frozen sampler for the QC-variance eval pilot (exp30).

Builds the 1,400-item frozen sample from the real QC public-use files:
  - test_main : 1,000 items, FY2021-2023 (locked test set)
  - test_2024:   200 items, FY2024 (year-robustness cut, reported separately)
  - dev       :   200 items, FY2021-2023, disjoint from test_main

Stratification (per exp17 section 4, deliberately not the natural prior):
  - finding mix: test_main 333 correct / 375 over / 292 under;
    test_2024 and dev 67 / 75 / 58.
  - element buckets: up to 50 per bucket in test_main (take-all for buckets
    with < 50 available), up to 8 per bucket in test_2024/dev.
  - nature-97 dedicated cut: tracked via flags; topped up to >= 40 in test_main.
  - state cap 10% (verified; non-binding in practice).

Eligibility: error cases used for taxonomy stratification must have a
reportable primary variance (AMOUNT > 0) whose nature code is one of the 12
standard codes (T4's option list). Error cases without a reportable primary
still enter the finding mix (they score on T1/T2/T6).

Writes (into this directory):
  - items.json: [{item_id, fiscal_year, case_id_hash, split, finding,
      labels{t1..t6}, flags{...}, fields{...}}] - ids + labels + de-identified
      input fields only; never raw microdata rows, never PII.
  - denylist.txt: "fiscal_year case_id_hash" per line (training exclusion list).
  - sampling_report.json: actual-vs-plan tables, rule-agreement stats,
      dollar-error distribution (open questions 2 and 4).

Usage: python3 sample.py [--seed 30] [--smoke]
  --smoke: 20-item dry run to /tmp (for pipeline verification only).

Deterministic: fixed seed; all draws via random.Random(seed).
"""

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import labels as L  # noqa: E402

RAW = ROOT.parent / "snap-qc-data/raw"
YEAR_FILES = {
    2021: RAW / "qcfy2021_csv/qc_pub_fy2021.csv",
    2022: RAW / "qcfy2022_csv/qc_pub_fy2022.csv",
    2023: RAW / "qcfy2023_csv/qc_pub_fy2023.csv",
    2024: RAW / "qcfy2024_csv/qc_pub_fy2024.csv",
}

# columns needed for labels + input fields
USECOLS = list({
    "STATE", "STATENAME", "YRMONTH", "HHLDNO", "STATUS", "AMTERR",
    "RAWGROSS", "RAWNET", "RAWHSIZE", "CERTHHSZ", "RAWERND",
    "FSCSEXP", "FSDEPDED", "FSMEDEXP", "SHELDED", "RENT", "UTIL",
    "SUA1", "SUA2", "HOMEDED", "FSUSIZE", "CTPRHH",
    "FSGRINC", "FSNETINC", "FSEARN", "FSUNEARN", "FSBEN",
    "FSSTDDED", "FSERNDED", "FSMEDDED", "FSSLTDED", "FSTOTDED",
    "FSCSDED", "FSSLTEXP", "HOMELESS_DED",
    "COMPOSITION", "CAT_ELIG", "FSKID", "FSELDER", "FSNELDER", "FSNDIS",
} | {code for code, _ in L.INCOME_SOURCES}
  | {f"{p}{i}" for p in ("ELEMENT", "NATURE", "AGENCY", "AMOUNT", "E_FINDG")
     for i in range(1, 10)})

PLAN = {
    "test_main": {"years": (2021, 2022, 2023), "n": 1000,
                  "finding": {"correct": 333, "overissuance": 375, "underissuance": 292},
                  "bucket_quota": 50, "nature97_min": 40},
    "test_2024": {"years": (2024,), "n": 200,
                  "finding": {"correct": 67, "overissuance": 75, "underissuance": 58},
                  "bucket_quota": 8, "nature97_min": 8},
    "dev": {"years": (2021, 2022, 2023), "n": 200,
            "finding": {"correct": 67, "overissuance": 75, "underissuance": 58},
            "bucket_quota": 8, "nature97_min": 8},
}


def case_id_hash(fiscal_year, state, yrmnth, hhldno):
    preimage = f"{fiscal_year}|{state}|{yrmnth}|{hhldno}"
    return hashlib.sha256(preimage.encode()).hexdigest()[:32]


def load_year(fy):
    cols = pd.read_csv(YEAR_FILES[fy], nrows=1).columns
    use = [c for c in USECOLS if c in cols]
    df = pd.read_csv(YEAR_FILES[fy], usecols=use, low_memory=False)
    df["fy"] = fy
    return df


def row_dict(row):
    d = row.to_dict()
    # normalize NaN -> None for labels.py helpers
    return {k: (None if (isinstance(v, float) and pd.isna(v)) else v)
            for k, v in d.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=30)
    ap.add_argument("--smoke", action="store_true",
                    help="20-item dry run to /tmp (pipeline verification)")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    outdir = Path("/tmp/eval_pilot_smoke") if args.smoke else HERE
    outdir.mkdir(parents=True, exist_ok=True)

    # ---- load + label -----------------------------------------------------
    frames = [load_year(fy) for fy in (2021, 2022, 2023, 2024)]
    df = pd.concat(frames, ignore_index=True)
    print(f"loaded {len(df)} rows", flush=True)

    recs = []
    for idx, row in df.iterrows():
        r = row_dict(row)
        status = L._int_or_none(L._num(r, "STATUS"))
        if status not in (1, 2, 3):
            continue
        labels = L.label_case(r)
        prim = labels.pop("_primary", None)
        n_rec, n_rep = L.variance_stats(r)
        first = L.first_recorded_variance(r)
        rec = {
            "_row": r,
            "fiscal_year": int(r["fy"]),
            "case_id_hash": case_id_hash(
                int(r["fy"]), r.get("STATE"), r.get("YRMONTH"), r.get("HHLDNO")),
            "finding": labels["t2"],
            "labels": labels,
            "bucket": labels["t3"],  # None unless reportable primary
            "nature": labels["t4"],
            "nature97": labels["t4"] == "97",
            "has_primary": prim is not None,
            "n_variances": n_rec,
            "n_reportable": n_rep,
            # open question 2: largest-dollar vs first-recorded agreement
            "rule_agree": (None if (prim is None or first is None or n_rep < 2)
                           else prim["index"] == first["index"]),
            "amterr": abs(labels["t6"]) if labels["t6"] else 0,
            "state": str(r.get("STATENAME") or r.get("STATE")),
        }
        recs.append(rec)
    print(f"eligible rows: {len(recs)}", flush=True)

    by_id = {rc["case_id_hash"]: rc for rc in recs}
    assert len(by_id) == len(recs), "case_id_hash collision!"

    used = set()
    items = []

    def draw(pool, k, split):
        pool = [rc for rc in pool if rc["case_id_hash"] not in used]
        rng.shuffle(pool)
        chosen = pool[:k]
        for rc in chosen:
            used.add(rc["case_id_hash"])
        return chosen

    def finalize(chosen, split, start_idx):
        out = []
        for j, rc in enumerate(chosen):
            fields = L.extract_fields(rc["_row"])
            lab = dict(rc["labels"])
            item = {
                "item_id": f"{split}-{start_idx + j:04d}",
                "fiscal_year": rc["fiscal_year"],
                "case_id_hash": rc["case_id_hash"],
                "split": split,
                "finding": rc["finding"],
                "labels": {t: lab[t] for t in ("t1", "t2", "t3", "t4", "t5", "t6")},
                "flags": {
                    "has_primary": rc["has_primary"],
                    "nature97": rc["nature97"],
                    "n_variances": rc["n_variances"],
                    "n_reportable": rc["n_reportable"],
                    "element_bucket": rc["bucket"],
                    "state": rc["state"],
                },
                "fields": fields,
            }
            out.append(item)
        return out

    # ---- draw each split --------------------------------------------------
    for split, plan in PLAN.items():
        pool = [rc for rc in recs if rc["fiscal_year"] in plan["years"]]
        if args.smoke:
            pool = pool[:500]
        chosen = []
        chosen_tax = []  # bucket-quota + nature97 items (protected on trim)
        # 1) taxonomy draw: per-bucket quotas from reportable-primary errors
        #    with standard nature codes
        tax_pool = [rc for rc in pool
                    if rc["finding"] != "correct" and rc["bucket"] is not None
                    and rc["nature"] is not None]
        by_bucket = defaultdict(list)
        for rc in tax_pool:
            by_bucket[rc["bucket"]].append(rc)
        for bucket in L.ELEMENT_BUCKETS:
            got = draw(by_bucket.get(bucket, []), plan["bucket_quota"], split)
            chosen += got
            chosen_tax += got
        # 2) nature-97 top-up
        n97 = sum(1 for rc in chosen if rc["nature97"])
        if n97 < plan["nature97_min"]:
            extra = draw([rc for rc in tax_pool if rc["nature97"]],
                         plan["nature97_min"] - n97, split)
            chosen += extra
            chosen_tax += extra
        # 3) fill the finding mix from all remaining error/correct cases
        have = Counter(rc["finding"] for rc in chosen)
        for finding, want in plan["finding"].items():
            if finding == "correct":
                cpool = [rc for rc in pool if rc["finding"] == "correct"]
            else:
                cpool = [rc for rc in pool if rc["finding"] == finding]
            need = want - have.get(finding, 0)
            if need > 0:
                chosen += draw(cpool, need, split)
            elif need < 0:
                # taxonomy overshot this finding: drop fill items first,
                # then taxonomy items, all of this finding
                drop = -need
                fill_ids = {id(rc) for rc in chosen} - {id(rc) for rc in chosen_tax}
                victims = [rc for rc in chosen
                           if rc["finding"] == finding and id(rc) in fill_ids]
                if len(victims) < drop:
                    victims += [rc for rc in chosen
                                if rc["finding"] == finding and id(rc) not in fill_ids]
                for rc in victims[:drop]:
                    chosen.remove(rc)
                    used.discard(rc["case_id_hash"])
        # 4) exact fit: trim or pad to n
        # 4) exact fit: trim or pad to n
        if len(chosen) > plan["n"]:
            rng.shuffle(chosen)
            for rc in chosen[plan["n"]:]:
                used.discard(rc["case_id_hash"])
            chosen = chosen[:plan["n"]]
        elif len(chosen) < plan["n"]:
            rest = [rc for rc in pool if rc["case_id_hash"] not in used]
            chosen += draw(rest, plan["n"] - len(chosen), split)
        items += finalize(chosen, split, {"test_main": 1, "test_2024": 1, "dev": 1}[split])

    # ---- write -------------------------------------------------------------
    with open(outdir / "items.json", "w") as fh:
        json.dump(items, fh)
    with open(outdir / "denylist.txt", "w") as fh:
        for it in items:
            fh.write(f"{it['fiscal_year']} {it['case_id_hash']}\n")

    # ---- sampling report ----------------------------------------------------
    def tab(key, splits=("test_main", "test_2024", "dev")):
        c = Counter()
        for it in items:
            if it["split"] in splits:
                c[it["flags"].get(key) if key != "finding" else it["finding"]] += 1
        return dict(c)

    test_items = [it for it in items if it["split"] in ("test_main", "test_2024")]
    agree_vals = [rc["rule_agree"] for rc in recs
                  if rc["rule_agree"] is not None
                  and rc["case_id_hash"] in {it["case_id_hash"] for it in test_items}]
    amterrs = sorted(it["labels"]["t6"] and abs(it["labels"]["t6"]) or 0
                     for it in test_items if it["finding"] != "correct")
    import statistics
    report = {
        "seed": args.seed,
        "n_items": len(items),
        "plan": {s: {"n": p["n"], "finding": p["finding"],
                     "bucket_quota": p["bucket_quota"]}
                 for s, p in PLAN.items()},
        "actual_finding": {s: tab("finding", (s,)) for s in PLAN},
        "actual_bucket_test": tab("element_bucket", ("test_main", "test_2024")),
        "actual_bucket_test_main": tab("element_bucket", ("test_main",)),
        "actual_bucket_test_2024": tab("element_bucket", ("test_2024",)),
        "actual_bucket_dev": tab("element_bucket", ("dev",)),
        "nature97_test": sum(1 for it in test_items if it["flags"]["nature97"]),
        "state_share_test_max": max(
            Counter(it["flags"]["state"] for it in test_items).values()) / len(test_items),
        # open question 2: primary-variance rule agreement on test items
        "rule_agreement": {
            "n_multi_reportable_test": len(agree_vals),
            "largest_dollar_vs_first_recorded": (
                sum(agree_vals) / len(agree_vals) if agree_vals else None),
        },
        # open question 4: dollar-error distribution (test error cases)
        "dollar_error_test": {
            "n": len(amterrs),
            "p10": amterrs[int(0.10 * len(amterrs))],
            "p25": amterrs[int(0.25 * len(amterrs))],
            "p50": amterrs[int(0.50 * len(amterrs))],
            "p75": amterrs[int(0.75 * len(amterrs))],
            "p90": amterrs[int(0.90 * len(amterrs))],
            "p99": amterrs[int(0.99 * len(amterrs))],
            "max": amterrs[-1],
            "mean": statistics.mean(amterrs),
        },
    }
    with open(outdir / "sampling_report.json", "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("plan",)}, indent=2)[:3000])


if __name__ == "__main__":
    main()
