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


FILES = {"PA": "pa_pilot_whitepaper.md", "NY": "ny_pilot_whitepaper.md", "TX": "tx_pilot_whitepaper.md",
         "SD": "sd_pilot_whitepaper.md", "UT": "ut_pilot_whitepaper.md", "ID": "id_pilot_whitepaper.md", "WY": "wy_state_brief.md"}


def expected():
    """(file, text that must appear) for every state figure quoted in the briefs and the PA-NY brief."""
    out = []
    for s, f in FILES.items():
        v, sc, owes = E83[s], E93[s]["scenarios"], E93[s]["cost_share_now"] > 0
        cost = 100 * (1 - FL[s] / T20[s])
        out += [(f, f"{T20[s]:.1f}×"), (f, f"{T10[s]:.1f}×"), (f, f"{TS[s]:.1f}×"), (f, f"{FL[s]:.1f}×"),
                (f, f"${v['top20']['per_hour_$']:.0f}"), (f, f"${v['top10']['per_hour_$']:.0f}"),
                (f, f"{E93[s]['per_fy2025']:.2f}%"), (f, f"{E68[s]['n_rows']:,}"), (f, f"{E68[s]['n_holdout']:,}"),
                (f, f"{E79[s]['under']['under_lift']:.1f} times"), (f, f"{E79[s]['total']['under_lift']:.1f} times"),
                (f, f"{E68[s]['holdout']['top20']['lift']:.1f}×"), (f, f"{sc['central']['ranker']['per']:.2f}%")]
        if cost >= 0.5:
            out.append((f, f"{round(cost)}%"))
        for k in ("elderly", "disabled", "single_parent", "childless_adult"):
            if k in v["fairness"]["baseline_ratio"]:
                out += [(f, f"{v['fairness']['baseline_ratio'][k]:.2f}"), (f, f"{v['fairness']['floor_ratio'][k]:.2f}")]
        if owes:
            for name in ("low", "central", "high"):
                out += [(f, f"{sc[name]['ranker']['per']:.2f}%"), (f, f"{sc[name]['random']['per']:.2f}%")]
        elif s != "WY":
            out.append((f, f"{sc['central']['random']['per']:.2f}%"))
    out += [("pa_pilot_whitepaper.md", "3.1× → 3.8×"), ("ny_pilot_whitepaper.md", "3.3× → 4.1×"),
            ("wy_state_brief.md", "the lowest of the 53") if RTS["WY"] == 53 else ("wy_state_brief.md", "__WY time split not lowest__"),
            ("wy_state_brief.md", "third lowest of 53") if RPER["WY"] == 3 else ("wy_state_brief.md", "__WY rate rank__"),
            ("sd_pilot_whitepaper.md", "the lowest of 53") if RPER["SD"] == 1 else ("sd_pilot_whitepaper.md", "__SD rate rank__"),
            ("id_pilot_whitepaper.md", "second lowest of 53") if RPER["ID"] == 2 else ("id_pilot_whitepaper.md", "__ID rate rank__"),
            ("ut_pilot_whitepaper.md", "eighth lowest of 53") if RPER["UT"] == 8 else ("ut_pilot_whitepaper.md", "__UT rate rank__")]
    for s, rk in (("TX", R20), ("SD", R20), ("UT", R20), ("ID", R20)):
        out.append((FILES[s], f"| {rk[s]} |"))
    if max(["PA", "NY", "TX", "SD", "UT", "ID"], key=T10.get) == "NY":
        out.append(("ny_pilot_whitepaper.md", "highest top-10% result of our six pilot states"))
    if R20["WY"] > 26:
        out.append(("wy_state_brief.md", "a little below the 53-jurisdiction median"))
    c = "pa_ny_combined_brief.md"
    for s in ("PA", "NY"):
        v, sc = E83[s], E93[s]["scenarios"]["central"]
        out += [(c, f"{T20[s]:.1f}×"), (c, f"{T10[s]:.1f}×"), (c, f"{TS[s]:.1f}×"), (c, f"{FL[s]:.1f}×"),
                (c, f"${v['top20']['per_hour_$']:.0f}"), (c, f"{E93[s]['per_fy2025']:.2f}%"), (c, f"{sc['ranker']['per']:.2f}%"),
                (c, f"{sc['reviews_per_month']:,}"), (c, f"{E68[s]['n_rows']:,} ({E68[s]['n_holdout']})")]
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
