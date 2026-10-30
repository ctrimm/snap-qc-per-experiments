"""Better Government Lab's snap_qc beside this repo: estimated dollars per state, and in total (exp106 follow-up).

    python3 whitepaper/better_government_lab_dollar_comparison.py      # prints the Markdown and writes the vault note

Both tools on one footing: mined/trained on FY2022-23, scored on each state's FY2024 QC cases, giannella's error
definition (|RAWBEN - FSBEN| above the $56 FY2024 tolerance) and their test frame (exp106 D1, 49 states).
  theirs   giannella v2.5.0 lists: methods/v250_benchmark_2024/v250_benchmark_2024.csv
  ours     our default model (leak-free inputs, official error label) on giannella's rebuilt pre-review inputs
           (exp109 arm B_over, like-for-like): experiments/exp109_leakfree_results.json
Estimated annual error dollars found = dollar recall at the budget x the state's annual over-threshold error dollars
(FY2024 QC cases weighted by FYWGT to monthly caseload, x 12).
Estimated FY2028 cost share avoided = exp69/exp93 central scenario (2% of cases reviewed a month, 80% of found errors
fixed, errors lasting 6 months) using each tool's 10%-budget dollar lift (dollar recall / 0.10); FY2025 error rates
and annual benefits as in exp93. Not a forecast: scenario arithmetic on one test year.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "experiments"))
from exp69_cost_share_scenarios import NAME_TO_USPS, share  # noqa: E402

NAMES = {v: " ".join(w.capitalize() if w != "OF" else "of" for w in k.split()) for k, v in NAME_TO_USPS.items()}
THEIRS = ROOT.parent / "giannella-snap_qc/methods/v250_benchmark_2024/v250_benchmark_2024.csv"
VAULT = Path.home() / "Documents/Nava Work Vault/Labs/2026-10-26 snap-qc Better Government Lab vs ours estimated dollars.md"


def num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def annual_error_dollars():
    out = {}
    for r in csv.DictReader(open(ROOT.parent / "snap-qc-data/raw/qcfy2024_csv/qc_pub_fy2024.csv", newline="", encoding="latin-1")):
        ab = NAME_TO_USPS.get((r.get("STATENAME") or "").strip().upper())
        d = abs(num(r["RAWBEN"]) - num(r["FSBEN"]))
        if ab and d > 56:
            out[ab] = out.get(ab, 0.0) + num(r["FYWGT"]) * d * 12
    return out


def avoided(per, benefits, lift):
    p1 = per / (1 + 0.02 * lift * 0.8 * 6)
    return (share(per) - share(p1)) * benefits


def main():
    ours = json.loads((ROOT / "experiments/exp109_leakfree_results.json").read_text())["states"]
    e93 = json.loads((ROOT / "experiments/exp93_official_results.json").read_text())["states"]
    theirs = {}
    for r in csv.DictReader(open(THEIRS)):
        theirs[(r["state"], round(float(r["budget"]), 2))] = r
    err = annual_error_dollars()
    rows = []
    for ab in sorted(ours, key=lambda s: NAMES[s]):
        n = NAMES[ab]
        if (n, 0.05) not in theirs:
            continue
        t5, t10 = float(theirs[(n, 0.05)]["dollar_recall"]), float(theirs[(n, 0.10)]["dollar_recall"])
        o5, o10 = ours[ab]["B_over"]["budget05"]["dollar_recall"], ours[ab]["B_over"]["budget10"]["dollar_recall"]
        E = err.get(ab, 0.0)
        per, ben = e93[ab]["per_fy2025"], e93[ab]["annual_benefits"]
        rows.append({"state": ab, "name": n, "err": E, "t5": t5 * E, "o5": o5 * E, "t10": t10 * E, "o10": o10 * E,
                     "t_cs": avoided(per, ben, t10 / 0.10), "o_cs": avoided(per, ben, o10 / 0.10),
                     "lift_t": t10 / 0.10, "lift_o": o10 / 0.10, "per": per})
    M = lambda x: f"${x / 1e6:,.1f}M"  # noqa: E731
    B = lambda x: f"${x / 1e9:,.2f}B"  # noqa: E731
    L = ["| State | Over-threshold error $ a year | Found at 5%: Better Government Lab | Found at 5%: ours | Found at 10%: Better Government Lab | Found at 10%: ours | 10% dollar lift: Better Government Lab / ours | FY2025 rate | FY2028 cost share avoided: Better Government Lab | ours |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    cum = {"err": 0, "t5": 0, "o5": 0, "t10": 0, "o10": 0, "t_cs": 0, "o_cs": 0}
    for r in rows:
        for k in cum:
            cum[k] += r[k]
        L.append(f"| {r['name']} ({r['state']}) | {M(r['err'])} | {M(r['t5'])} | {M(r['o5'])} | {M(r['t10'])} | {M(r['o10'])} | "
                 f"{r['lift_t']:.2f}× / {r['lift_o']:.2f}× | {r['per']:.2f}% | {M(r['t_cs'])} | {M(r['o_cs'])} |")
    L.append(f"| **Total, {len(rows)} states** | **{B(cum['err'])}** | **{B(cum['t5'])}** | **{B(cum['o5'])}** | **{B(cum['t10'])}** | "
             f"**{B(cum['o10'])}** | | | **{B(cum['t_cs'])}** | **{B(cum['o_cs'])}** |")
    table = "\n".join(L)
    better10 = sum(r["o10"] > r["t10"] for r in rows)
    cs_more = sum(r["o_cs"] > r["t_cs"] for r in rows); cs_less = sum(r["o_cs"] < r["t_cs"] for r in rows)
    summary = {k: round(v / 1e9, 3) for k, v in cum.items()}
    summary.update({"states": len(rows), "ours_more_dollars_10pct": better10, "cs_ours_more": cs_more, "cs_ours_less": cs_less})
    print(json.dumps(summary, indent=1))
    note = f"""---
date: 2026-10-26
tags: [snap-qc, labs, comparison, better-government-lab]
repo: snap-qc-per-experiments
---
# snap-qc: Better Government Lab vs ours, estimated dollars by state

## Conclusion

> **Note (Oct 30): building on Better Government Lab's work.** Much of what we changed after October 26 came from Better Government Lab's snap_qc: the leak (exp106), the rebuilt pre-review inputs (exp109, exp113, exp114), the official over-tolerance error definition (exp110–111), the reviewer's-finding label and yearly tolerances (exp112), and the test windows and price basis (exp113). Where this note sets our numbers beside theirs, it is our model's per-case predictions beside their published rule lists, not model against model. Their rule lists are built for agencies that can't run a model, so a model scoring higher is expected and isn't a judgment on that approach. Better Government Lab reports that its own boosted-tree models give numbers matching ours, and plans a release where one script outputs predictions. Repo: navapbc/snap-qc-per-experiments PR #4.

**On the same test and the same rebuilt inputs, our ranker's predictions find more error dollars than Better Government Lab's rule lists in {better10} of {len(rows)} states,** as expected of a model against rules built for agencies that can't run one. In total across {len(rows)} states, at a 10% review budget, it finds about **{B(cum['o10'])} a year**, against **{B(cum['t10'])}**, of {B(cum['err'])} in over-threshold error dollars.

**FY2028 cost share avoided:** the central scenario with each tool's own lift gives about **{B(cum['o_cs'])} a year** for ours and **{B(cum['t_cs'])}** for theirs. Cost share moves only when a state crosses a bracket line, so some states gain nothing under either tool. Ours avoids more in {cs_more} states, less in {cs_less}.

**Caveats:**
- **Scope:** these are scenario estimates on one test year (FY2024), not forecasts.
- **What their lists offer:** they are interpretable rules a state can read and edit; ours is a score.
- **Like-for-like:** both tools score the same FY2024 cases from the same rebuilt pre-review inputs (exp109). On the reviewer's corrected inputs our dollars would read about 17% higher; these figures don't use them.
- **Which of our versions:** ours is the default model (leak-free inputs, official error label) run on Better Government Lab's rebuilt pre-review inputs, so both tools see the same kind of inputs (exp109).

## How the numbers are built

| Step | What | Source |
|---|---|---|
| Test | Train or mine on FY2022–23, score each state's FY2024 QC cases, both on Better Government Lab's rebuilt pre-review inputs | exp109 B_over; Better Government Lab v2.5.0 benchmark |
| Error | \\|RAWBEN − FSBEN\\| above $56 (FY2024 tolerance), Better Government Lab's definition | `features.R` |
| Annual error dollars | Σ FYWGT × error dollars × 12, FY2024 | QC public-use file |
| Found a year | Dollar recall at the budget × annual error dollars | |
| Dollar lift | Dollar recall at the 10% budget ÷ 0.10 | |
| Cost share avoided | exp69 central scenario (2% reviewed a month, 80% fixed, 6 months) with that lift; FY2025 rates and benefits as exp93 | `exp69`, `exp93` |

Script: `whitepaper/better_government_lab_dollar_comparison.py`. Related: [[2026-10-26 snap-qc exp106 Better Government Lab comparison]], [[2026-10-26 snap-qc exp109 rebuilt inputs]].

## By state

{table}
"""
    VAULT.write_text(note)
    print("wrote", VAULT)
    wp = HERE / "better_government_lab_whitepaper.md"
    if wp.exists():
        import re
        t = wp.read_text()
        t = re.sub(r"<!-- DOLLAR-TABLE:START -->.*?<!-- DOLLAR-TABLE:END -->",
                   "<!-- DOLLAR-TABLE:START -->\n" + table + "\n<!-- DOLLAR-TABLE:END -->", t, flags=re.S)
        wp.write_text(t)
        print("updated", wp.name)


if __name__ == "__main__":
    main()
