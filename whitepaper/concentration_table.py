"""How concentrated are SNAP error dollars? One row per jurisdiction, from the FY2020-24 QC public-use files.

    python3 whitepaper/concentration_table.py     # writes the appendix table into whitepaper/project_summary.md

Per jurisdiction (unweighted, all five years pooled):
  reviewed   QC cases reviewed (all STATUS values)
  errors     error cases (STATUS 2 overissuance or 3 underissuance)
  A          share of error dollars (AMTERR) held by the 10% of error cases with the largest AMTERR
  B          share of error dollars held by the 10% of all reviewed cases with the largest AMTERR
             (correct cases count as $0); the October 4 pilot papers quoted this figure as the share held
             by "the top tenth of errors"
  median, p90  AMTERR of error cases, dollars
Top 10% = the round(n x 0.10) largest values. National = all 53 jurisdictions pooled.
"""
import csv
import glob
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent.parent / "snap-qc-data/raw"
sys.path.insert(0, str(HERE.parent / "experiments"))
from exp69_cost_share_scenarios import NAME_TO_USPS  # noqa: E402

NAMES = {v: " ".join(w.capitalize() if w != "OF" else "of" for w in k.split()) for k, v in NAME_TO_USPS.items()}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def top_share(vals, q=0.10):
    v = sorted(vals, reverse=True)
    t = sum(v)
    return 100 * sum(v[:max(1, round(len(v) * q))]) / t if t else float("nan")


def quantile(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))]


def compute():
    data = defaultdict(list)  # state code -> [(is_error, amterr)]
    abbr = {}
    for fy in range(2020, 2025):
        for r in csv.DictReader(open(glob.glob(str(RAW / f"qcfy{fy}_csv/*.csv"))[0], newline="", encoding="latin-1")):
            c = r["STATE"].strip()
            data[c].append((r["STATUS"].strip() in ("2", "3"), num(r["AMTERR"])))
            if c not in abbr and r.get("STATENAME"):
                abbr[c] = NAME_TO_USPS.get(r["STATENAME"].strip().upper())
    rows = []
    for c, R in data.items():
        err = [a for e, a in R if e]
        rows.append({"state": abbr.get(c) or c, "reviewed": len(R), "errors": len(err), "A": top_share(err),
                     "B": top_share([a if e else 0.0 for e, a in R]), "median": quantile(err, 0.5), "p90": quantile(err, 0.9)})
    allR = [x for R in data.values() for x in R]
    err = [a for e, a in allR if e]
    nat = {"state": "National", "reviewed": len(allR), "errors": len(err), "A": top_share(err),
           "B": top_share([a if e else 0.0 for e, a in allR]), "median": quantile(err, 0.5), "p90": quantile(err, 0.9)}
    return sorted(rows, key=lambda r: NAMES.get(r["state"], r["state"])), nat


def table(rows, nat):
    L = ["| Jurisdiction | Reviewed cases | Error cases | A: top 10% of error cases | B: top 10% of all cases | Median error | 90th pct. |",
         "|---|---|---|---|---|---|---|"]
    for r in [*rows, nat]:
        name = f"**{r['state']}**" if r["state"] == "National" else f"{NAMES.get(r['state'], r['state'])} ({r['state']})"
        L.append(f"| {name} | {r['reviewed']:,} | {r['errors']:,} | {r['A']:.1f}% | {r['B']:.1f}% | ${r['median']:.0f} | ${r['p90']:.0f} |")
    return "\n".join(L)


if __name__ == "__main__":
    rows, nat = compute()
    t = table(rows, nat)
    p = HERE / "project_summary.md"
    s = p.read_text()
    s = re.sub(r"<!-- CONCENTRATION:START -->.*?<!-- CONCENTRATION:END -->",
               "<!-- CONCENTRATION:START -->\n" + t + "\n<!-- CONCENTRATION:END -->", s, flags=re.S)
    p.write_text(s)
    a = sorted(r["A"] for r in rows)
    b = sorted(r["B"] for r in rows)
    print(f"{len(rows)} jurisdictions; A median {a[len(a) // 2]:.1f}% (range {a[0]:.1f}–{a[-1]:.1f}); "
          f"B median {b[len(b) // 2]:.1f}% (range {b[0]:.1f}–{b[-1]:.1f}); national A {nat['A']:.1f}% B {nat['B']:.1f}%")
