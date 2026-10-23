"""State figures for the briefs and the replication guide, computed from the committed results.

    python3 whitepaper/state_numbers.py table   # write the 53-jurisdiction appendix into state_replication_guide.md
    python3 whitepaper/state_numbers.py check   # every state figure quoted in the briefs must match its source

Sources: experiments/exp83_results.json (deployed models, held-out), exp80/exp82_results.json (adoption, later-years
test), exp68_results.json (state-only baseline, sample sizes), exp79_results.json (underpayment ranker),
exp93_results.json (FY2025 rates, cost-share scenarios). Ranks: 1 = best of 53.
"""
import json
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent / "experiments"
load = lambda f: json.loads((EXP / f).read_text())  # noqa: E731
E83, E93 = load("exp83_results.json"), load("exp93_results.json")["states"]
E68 = {r["state"]: r for r in load("exp68_results.json")}
E79 = {r["state"]: r for r in load("exp79_results.json")}
ADOPT = {**load("exp80_results.json"), **load("exp82_results.json")}
TS = {s: r[r["adopted"]]["time_split"] for s, r in ADOPT.items()}
STATES = sorted(E83)


def rank(val):
    order = sorted(STATES, key=lambda s: -val(s))
    return {s: i + 1 for i, s in enumerate(order)}


T20 = {s: E83[s]["top20"]["lift"] for s in STATES}
T10 = {s: E83[s]["top10"]["lift"] for s in STATES}
FL = {s: E83[s]["fairness"]["floor_lift"] for s in STATES}
R20, R10, RTS = rank(T20.get), rank(T10.get), rank(TS.get)
RPER = {s: i + 1 for i, s in enumerate(sorted(STATES, key=lambda s: E93[s]["per_fy2025"]))}  # 1 = lowest rate


def table():
    rows = ["| Jurisdiction | Top 20% lift (rank) | Top 10% lift (rank) | Later years (rank) | With floor (cost) | Forecast ÷ actual | QC cases | FY2025 rate | Central: avoided a year |",
            "|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(STATES, key=R20.get):
        v, c = E83[s], E93[s]["scenarios"]["central"]["ranker"]["saving_vs_now"]
        cost = 100 * (1 - FL[s] / T20[s])
        rows.append(f"| {s} | {T20[s]:.2f}× ({R20[s]}) | {T10[s]:.2f}× ({R10[s]}) | {TS[s]:.2f}× ({RTS[s]}) | "
                    f"{FL[s]:.2f}× ({cost:+.1f}%) | {v['top20']['expected_over_actual']:.2f} | {E68[s]['n_rows']:,} | "
                    f"{E93[s]['per_fy2025']:.2f}% | {'$%dM' % round(c / 1e6) if c else '—'} |")
    med = lambda d: st.median(d.values())  # noqa: E731
    rows.append(f"| **Median** | {med(T20):.2f}× | {med(T10):.2f}× | {med(TS):.2f}× | {st.median(FL.values()):.2f}× "
                f"({st.median(100 * (1 - FL[s] / T20[s]) for s in STATES):+.1f}%) | "
                f"{st.median(E83[s]['top20']['expected_over_actual'] for s in STATES):.2f} | | | |")
    return "\n".join(rows)


def expected():
    """(file, text that must appear) for every state figure quoted in the briefs."""
    out = []
    for s, f in (("PA", "state_brief_pa.md"), ("NY", "state_brief_ny.md"), ("WY", "state_brief_wy.md")):
        v, sc, a = E83[s], E93[s]["scenarios"], ADOPT[s]
        base = "deployed"
        out += [(f, f"{T20[s]:.1f}×"), (f, f"{T10[s]:.1f}×"), (f, f"{TS[s]:.1f}×"), (f, f"{FL[s]:.1f}×"),
                (f, f"${v['top20']['per_hour_$']:.0f}"), (f, f"${v['top10']['per_hour_$']:.0f}"),
                (f, f"{E93[s]['per_fy2025']:.2f}%"), (f, f"{E68[s]['n_rows']:,}"), (f, f"{E68[s]['n_holdout']}"),
                (f, f"{E79[s]['under']['under_lift']:.1f} times"), (f, f"{E79[s]['total']['under_lift']:.1f} times"),
                (f, f"{round(100 * (1 - FL[s] / T20[s]))}%")]
        for k in ("elderly", "disabled", "single_parent", "childless_adult"):
            out += [(f, f"{v['fairness']['baseline_ratio'][k]:.2f}"), (f, f"{v['fairness']['floor_ratio'][k]:.2f}")]
        for name in (("central",) if s == "WY" else ("low", "central", "high")):  # WY's brief tabulates hypothetical rates instead
            out.append((f, f"{sc[name]['ranker']['per']:.2f}%"))
            if s != "WY":
                out.append((f, f"{sc[name]['random']['per']:.2f}%"))
        if s == "WY":
            out += [(f, f"{E68[s]['holdout']['top20']['lift']:.1f}×"), (f, f"{E68[s]['time_split_top20_lift']['untuned']:.1f}×"),
                    (f, "the lowest of the 53") if RTS[s] == 53 else (f, "__WY time split is not lowest__"),
                    (f, "third lowest of 53") if RPER[s] == 3 else (f, "__WY rate rank changed__")]
        else:
            out += [(f, f"{a[base]['holdout']:.1f}× → {T20[s]:.1f}×"), (f, f"{a[base]['time_split']:.1f}× → {TS[s]:.1f}×")]
    pilots = ["PA", "NY", "TX", "SD", "UT", "ID"]
    if max(pilots, key=T10.get) == "NY":
        out.append(("state_brief_ny.md", "highest top-10% result of our six pilot states"))
    if R20["WY"] > 26:
        out.append(("state_brief_wy.md", "a little below the 53-jurisdiction median"))
    return out


def check():
    bad = 0
    for f, text in expected():
        if text not in (HERE / f).read_text():
            print(f"MISSING in {f}: {text!r}")
            bad += 1
    print(f"{len(expected()) - bad} of {len(expected())} quoted state figures match their source")
    return 1 if bad else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["table"]:
        p = HERE / "state_replication_guide.md"
        s = p.read_text()
        s = re.sub(r"<!-- STATE-TABLE:START -->.*?<!-- STATE-TABLE:END -->",
                   "<!-- STATE-TABLE:START -->\n" + table() + "\n<!-- STATE-TABLE:END -->", s, flags=re.S)
        p.write_text(s)
        print(table())
    else:
        sys.exit(check())
