"""Experiment 50 - refit PA/NY state offsets excluding the pandemic years.

Hypothesis: the partial-year FY2020 (27,112 rows nationally) and FY2021
(9,832 rows nationally; NY 221, PA 189 rows) files distort the cross-state
offsets baked into src/synth/pa_state.py and src/synth/ny_state.py, which
were fit on pooled FY2020-2024 microdata. NY6 already showed partial-year
files can move fitted quantities (FY2021's 221 NY rows moved the fitted
error rate 1.9pp).

Method: reuse the exact pa1/ny1 fitting recipes
(experiments/pa1_pa_generator.fit_pa_targets and
experiments/ny1_ny_generator.fit_ny_targets) with fys=[2022, 2023, 2024]
and compare every baked offset constant against the pooled FY2020-2024
refit (same recipe, so old-vs-new is apples-to-apples). A pooled refit is
also sanity-checked against the baked constants.

Usage:
    python3 experiments/exp50_offsets_ex_pandemic.py [--out results.json]

QC microdata is READ-ONLY; nothing is committed; outputs are printed and
optionally written to the given JSON path (default: /tmp/exp50_results.json).
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

QC_DEFAULT = str(Path.home() / "workspace" / "snap-qc-data" / "raw")
FYS_ALL = [2020, 2021, 2022, 2023, 2024]
FYS_EX = [2022, 2023, 2024]


def _load_mod(name, relpath):
    spec = importlib.util.spec_from_file_location(
        name, str(REPO / relpath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PA1 = _load_mod("pa1_pa_generator", "experiments/pa1_pa_generator.py")
NY1 = _load_mod("ny1_ny_generator", "experiments/ny1_ny_generator.py")
SUPPORTED = PA1.SUPPORTED


def extract_offsets(t, g, baked_label="old"):
    """Flatten every baked-style offset constant from a fit result dict."""
    d, nat, R = t[g], t["nat"], t["ratios"]
    o = {}
    # absolute empirical targets (used for validation; quoted in docstrings)
    o[f"{g}_case_err_rate"] = d["case_err_rate"]
    o[f"{g}_dollar_rate"] = d["dollar_rate"]
    for s in ("1", "2", "3"):
        o[f"{g}_finding_{s}"] = d["finding_mix"][s]
    o[f"{g}_p_over_given_err"] = d["p_over_given_err"]
    o[f"{g}_medO"] = d["medO"]
    o[f"{g}_medU"] = d["medU"]
    o[f"{g}_cause97_blank"] = d["cause97_blank"]
    o[f"{g}_near_full_given_over"] = d["near_full_given_over"]
    # applied ratios
    for k, v in R["coin"].items():
        o[f"{g}_coin_{k}"] = v
    for b in SUPPORTED:
        o[f"{g}_bucket_{b}"] = R["bucket"][b]
        o[f"{g}_97resolve_{b}"] = R["p97"][b]
        o[f"{g}_97share_{b}"] = R["nature97share"][b]
        o[f"{g}_dir_over_{b}"] = R["naturedir"][b]["over"]
        o[f"{g}_dir_under_{b}"] = R["naturedir"][b]["under"]
        for co in ("client", "agency", "no_fault", "other"):
            o[f"{g}_cause_{b}_{co}"] = R["cause_non97"][(b, co)]
        # 97-cause mix: summarize as max share (the dominant raw code)
        mix = R["cause97"][b]
        top = max(mix.values()) if mix else 0.0
        o[f"{g}_97cause_topshare_{b}"] = top
    o[f"{g}_s_over"] = R["s_over"]
    o[f"{g}_s_under"] = R["s_under"]
    o[f"{g}_n_rows"] = float(t.get("n_pa_rows", t.get("n_ny_rows", 0)))
    return o


def rel(old, new):
    if old == 0:
        return float("inf") if new != 0 else 0.0
    return (new - old) / abs(old)


def compare(old, new, g):
    rows = []
    for k in sorted(old):
        if k.endswith("_n_rows"):
            continue
        a, b = old[k], new[k]
        d = b - a
        rows.append((k, a, b, d, rel(a, b)))
    rows.sort(key=lambda r: -abs(r[3]) if r[0].find("_97cause") == -1 else 0)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc", default=QC_DEFAULT)
    ap.add_argument("--out", default="/tmp/exp50_results.json")
    args = ap.parse_args()

    fits = {}
    for label, fys in (("all", FYS_ALL), ("ex", FYS_EX)):
        print(f"fitting on FYs {fys} ...", flush=True)
        tpa = PA1.fit_pa_targets(args.qc, fys=fys)
        tny = NY1.fit_ny_targets(args.qc, fys=fys)
        fits[label] = (tpa, tny)

    res = {}
    for g, tkey in (("pa", 0), ("ny", 1)):
        old = extract_offsets(fits["all"][tkey], g)
        new = extract_offsets(fits["ex"][tkey], g)
        rows = compare(old, new, g)
        res[g] = {
            "old_n_rows": old[f"{g}_n_rows"],
            "new_n_rows": new[f"{g}_n_rows"],
            "rows": [{"name": r[0], "old": r[1], "new": r[2],
                      "delta": r[3], "reldelta": r[4]} for r in rows],
        }

    with open(args.out, "w") as f:
        json.dump(res, f, indent=1)
    print(f"\nwrote {args.out}")

    # compact report: largest absolute movers + headline quantities
    for g in ("pa", "ny"):
        R = res[g]
        print(f"\n===== {g.upper()} (pooled n={R['old_n_rows']:.0f} -> "
              f"FY22-24 n={R['new_n_rows']:.0f}) =====")
        print(f"{'offset':<34}{'old':>10}{'new':>10}{'delta':>10}{'rel%':>9}")
        head = ["case_err_rate", "dollar_rate", "p_over_given_err",
                "medO", "medU", "cause97_blank"]
        shown = set()
        for h in head:
            for r in R["rows"]:
                if r["name"] == f"{g}_{h}":
                    print(f"  {r['name']:<32}{r['old']:>10.4f}{r['new']:>10.4f}"
                          f"{r['delta']:>10.4f}{r['reldelta']*100:>8.1f}%")
                    shown.add(r["name"])
        print("  -- largest absolute movers --")
        n = 0
        for r in R["rows"]:
            if r["name"] in shown or "_97cause_topshare" in r["name"]:
                continue
            print(f"  {r['name']:<32}{r['old']:>10.4f}{r['new']:>10.4f}"
                  f"{r['delta']:>10.4f}{r['reldelta']*100:>8.1f}%")
            n += 1
            if n >= 12:
                break
        mx = max(abs(r["delta"]) for r in R["rows"]
                 if "_97cause_topshare" not in r["name"])
        mxrow = max((r for r in R["rows"]
                     if "_97cause_topshare" not in r["name"]),
                    key=lambda r: abs(r["delta"]))
        print(f"  max |delta| (excl 97-cause top-share): {mx:.4f} "
              f"({mxrow['name']})")

    # sanity check: pooled refit vs baked constants
    from src.synth import pa_state, ny_state
    checks = [
        ("pa", pa_state.PA_S_OVER, res["pa"], "pa_s_over"),
        ("pa", pa_state.PA_S_UNDER, res["pa"], "pa_s_under"),
        ("ny", ny_state.NY_S_OVER, res["ny"], "ny_s_over"),
        ("ny", ny_state.NY_S_UNDER, res["ny"], "ny_s_under"),
        ("pa", pa_state.PA_CAUSE97_BLANK, res["pa"], "pa_cause97_blank"),
        ("ny", ny_state.NY_CAUSE97_BLANK, res["ny"], "ny_cause97_blank"),
    ]
    print("\n===== sanity: pooled refit vs baked constants =====")
    for g, baked, R, name in checks:
        old = next(r for r in R["rows"] if r["name"] == name)["old"]
        print(f"  {name:<22} baked {baked:.4f}  refit {old:.4f}  "
              f"diff {old - baked:+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
