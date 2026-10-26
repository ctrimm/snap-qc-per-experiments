"""Older adults in the SNAP QC data: every figure for whitepaper/older_adults_whitepaper.md, computed from source.

    python3 whitepaper/older_adults_numbers.py        # prints the figures, writes older_adults_numbers.json and the appendix table

Data: SNAP QC public-use files FY2020-2024 (snap-qc-data/raw), unweighted, five years pooled unless noted.
An elderly household is one with FSELDER = 1 (a member aged 60+), as in exp47/exp72 (elderly is checked first).
Error case: STATUS 2 (overissuance) or 3 (underissuance); error dollars: AMTERR.
A medical-deduction error is a case with any variance element 365 (ELEMENT1..ELEMENTn); exp42's
elderly-or-disabled, medical-expense-on-file rate (24.2%) is reproduced first as a check of the method.
Income sources use the verified income fields (FSSOCSEC, FSSSI, FSPENSION, FSWAGES > 0); the ranker never uses them.
Per-jurisdiction fairness ratios come from experiments/exp83_leakfree_results.json (leak-free models, exp107); the random-review
ratio is computed on the same held-out cases (experiments/exp68_holdouts.json) as overall error rate / elderly error rate.
"""
import csv
import glob
import json
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT.parent / "snap-qc-data/raw"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
from synth.codebook import ELEMENT_LABELS  # noqa: E402
from exp69_cost_share_scenarios import NAME_TO_USPS  # noqa: E402

NAMES = {v: " ".join(w.capitalize() if w != "OF" else "of" for w in k.split()) for k, v in NAME_TO_USPS.items()}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def load():
    """Rows per state, keyed (fy, idx) in the same order as exp58.load_state, so exp68 holdout keys line up."""
    rows = defaultdict(dict)
    abbr = {}
    for fy in range(2020, 2025):
        idx = Counter()
        for r in csv.DictReader(open(glob.glob(str(RAW / f"qcfy{fy}_csv/*.csv"))[0], newline="", encoding="latin-1")):
            c = r["STATE"].strip()
            abbr.setdefault(c, NAME_TO_USPS.get((r.get("STATENAME") or "").strip().upper()))
            els = [int(num(r.get(f"ELEMENT{i}"))) for i in range(1, 10) if r.get(f"ELEMENT{i}") not in (None, "")]
            rows[c][(fy, idx[c])] = {
                "elderly": (r.get("FSELDER") or "").strip() == "1",
                "disabled": (r.get("FSDIS") or "").strip() == "1",
                "status": r["STATUS"].strip(), "amt": num(r["AMTERR"]), "medexp": num(r.get("FSMEDEXP")),
                "el1": int(num(r.get("ELEMENT1"))), "nat1": int(num(r.get("NATURE1"))), "med_var": 365 in els,
                "socsec": num(r.get("FSSOCSEC")) > 0, "ssi": num(r.get("FSSSI")) > 0, "pension": num(r.get("FSPENSION")) > 0,
                "wages": num(r.get("FSWAGES")) > 0, "w": num(r.get("FYWGT")), "fy": fy}
            idx[c] += 1
    return rows, abbr


def profile(R):
    n = len(R)
    err = [x for x in R if x["status"] in ("2", "3")]
    od = sum(x["amt"] for x in err if x["status"] == "2")
    ud = sum(x["amt"] for x in err if x["status"] == "3")
    eld_d, eld_n = Counter(), Counter()
    for x in err:
        eld_d[x["el1"]] += x["amt"]
        eld_n[x["el1"]] += 1
    tot = sum(eld_d.values()) or 1
    amts = sorted(x["amt"] for x in err)
    return {"n": n, "err_rate": 100 * len(err) / n, "errors": len(err),
            "over": sum(x["status"] == "2" for x in err), "under": sum(x["status"] == "3" for x in err),
            "under_dollar_share": 100 * ud / (od + ud) if od + ud else None,
            "median_err": amts[len(amts) // 2] if amts else None, "p90_err": amts[int(0.9 * len(amts))] if amts else None,
            "timing_share": 100 * sum(x["nat1"] == 97 for x in err) / len(err),
            "el_dollars": [(ELEMENT_LABELS.get(e, f"code {e}"), round(100 * v / tot, 1)) for e, v in eld_d.most_common(6)],
            "el_count": [(ELEMENT_LABELS.get(e, f"code {e}"), round(100 * v / len(err), 1)) for e, v in eld_n.most_common(6)],
            "income": {k: 100 * sum(x[k] for x in R) / n for k in ("socsec", "ssi", "pension", "wages")}}


def main():
    rows, abbr = load()
    allR = [x for R in rows.values() for x in R.values()]
    out = {}
    # method check: exp42's elderly-or-disabled with medical expenses on file
    sd_med = [x for x in allR if (x["elderly"] or x["disabled"]) and x["medexp"] > 0]
    out["check_exp42_senior_dis_medexp"] = {"n": len(sd_med), "med_error_pct": 100 * sum(x["med_var"] for x in sd_med) / len(sd_med)}
    eld = [x for x in allR if x["elderly"]]
    non = [x for x in allR if not x["elderly"]]
    out["national"] = {"elderly": profile(eld), "non_elderly": profile(non), "all": profile(allR)}
    em = [x for x in eld if x["medexp"] > 0]
    en = [x for x in eld if x["medexp"] <= 0]
    out["medical"] = {"elderly_medexp_n": len(em), "elderly_medexp_pct_of_elderly": 100 * len(em) / len(eld),
                      "med_error_pct_with_medexp": 100 * sum(x["med_var"] for x in em) / len(em),
                      "med_error_pct_without_medexp": 100 * sum(x["med_var"] for x in en) / len(en),
                      "med_error_pct_nonelderly_nondisabled": 100 * sum(x["med_var"] for x in allR if not x["elderly"] and not x["disabled"]) / sum(1 for x in allR if not x["elderly"] and not x["disabled"])}
    f24 = [x for x in allR if x["fy"] == 2024]
    out["fy2024_share"] = {"unweighted": 100 * sum(x["elderly"] for x in f24) / len(f24),
                           "weighted": 100 * sum(x["w"] * x["elderly"] for x in f24) / sum(x["w"] for x in f24)}
    # per jurisdiction: profile + today's fairness ratios + random-review ratio on the exp68 holdout
    e83 = json.loads((ROOT / "experiments/exp83_leakfree_results.json").read_text())  # leak-free (exp107)
    hold = json.loads((ROOT / "experiments/exp68_holdouts.json").read_text())
    table = []
    for c, R in rows.items():
        s = abbr[c]
        h = hold[s]
        keys = [tuple(k) for k in h["keys"]]
        H = [R[k] for k in keys]
        he = [x for x in H if x["elderly"]]
        overall = sum(x["status"] in ("2", "3") for x in H) / len(H)
        eld_rate = sum(x["status"] in ("2", "3") for x in he) / len(he)
        p = profile([x for x in R.values() if x["elderly"]])
        fr = e83[s]["fairness"]
        table.append({"state": s, "elderly_share": 100 * sum(x["elderly"] for x in R.values()) / len(R), "elderly_err": p["err_rate"],
                      "all_err": profile(list(R.values()))["err_rate"], "under_share": p["under_dollar_share"],
                      "ratio": fr["baseline_ratio"]["elderly"], "floor": fr["floor_ratio"]["elderly"], "random": overall / eld_rate,
                      "holdout_elderly_n": len(he)})
    table.sort(key=lambda r: NAMES.get(r["state"], r["state"]))
    out["states"] = table
    out["state_summary"] = {"ratio_below_random": sum(r["ratio"] < r["random"] for r in table),
                            "elderly_err_above_all": sum(r["elderly_err"] > r["all_err"] for r in table),
                            "median_ratio": st.median(r["ratio"] for r in table), "median_floor": st.median(r["floor"] for r in table),
                            "median_random": st.median(r["random"] for r in table), "below_08": sum(r["ratio"] < 0.8 for r in table)}
    (HERE / "older_adults_numbers.json").write_text(json.dumps(out, indent=1))
    L = ["| Jurisdiction | Elderly share of reviewed cases | Elderly error rate | All households' error rate | Underpayment share of elderly error dollars | Review ratio, dollars only | With the floor | Random review would give |",
         "|---|---|---|---|---|---|---|---|"]
    for r in table:
        L.append(f"| {NAMES.get(r['state'], r['state'])} ({r['state']}) | {r['elderly_share']:.0f}% | {r['elderly_err']:.0f}% | {r['all_err']:.0f}% | "
                 f"{r['under_share']:.0f}% | {r['ratio']:.2f} | {r['floor']:.2f} | {r['random']:.2f} |")
    p = HERE / "older_adults_whitepaper.md"
    if p.exists():
        s = p.read_text()
        s = re.sub(r"<!-- OLDER-TABLE:START -->.*?<!-- OLDER-TABLE:END -->",
                   "<!-- OLDER-TABLE:START -->\n" + "\n".join(L) + "\n<!-- OLDER-TABLE:END -->", s, flags=re.S)
        p.write_text(s)
    print(json.dumps({k: v for k, v in out.items() if k != "states"}, indent=1))


if __name__ == "__main__":
    main()
