"""Charts of the snap-qc experiments, read from the files the experiments left.

Three figures, each with a CSV table view, written to outputs/charts/ and copied
into the Obsidian vault's Labs folder:

- snap-qc-verdicts.png: every experiment exp1-exp83 by track, colored by verdict
  (parsed from the README index).
- snap-qc-tracks.png: one panel per track that has numbers.
  a. Generator calibration: synthetic/real element ratios before and after each
     fix (transcribed from the README verdicts; the early chronicles have no
     results JSON).
  b. Automatic generator calibration, exp81/exp81b (search logs).
  c. The exp52 training search on the dev set (sweep and SFT TSVs).
  d. The language-model gate on the fresh 1,200-case set (exp59/60/71 tables).
  e. Triage rankers, 53 jurisdictions per generation (results JSONs), including
     the October 26 leak correction.
  f. The FY2028 cost-share estimate as it was restated (chronicle tables).
- snap-qc-routing.png: exp104's routing signals (its AUTO-RESULTS block) and
  the exp105 confirmation.

    uv run --no-project --with matplotlib python experiments/lab_charts.py
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

EXP = Path(__file__).resolve().parent
REPO = EXP.parent
OUT = REPO / "outputs/charts"
VAULT = Path.home() / "Documents/Obsidian Vault/Labs"

SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#9a9893", "#e6e5e1"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
GOOD, WARNING, CRITICAL, NEUTRAL = "#0ca30c", "#fab219", "#d03b3b", "#b9b7b0"
LEAKY, LEAKFREE = SERIES[1], SERIES[0]


def _axes(ax, title, subtitle=None, grid="y"):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    if grid:
        ax.grid(axis=grid, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK_2, labelsize=8)
    ax.set_title(title, loc="left", fontsize=10.5, color=INK, fontweight="bold", pad=18 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=8, color=INK_2, va="bottom")


def _write_csv(path, header, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _save(fig, name):
    png = OUT / name
    fig.savefig(png, facecolor=SURFACE)
    plt.close(fig)
    if VAULT.is_dir():
        shutil.copy2(png, VAULT / name)
    print(f"wrote {png}")


# --- verdict ledger -----------------------------------------------------------

TRACKS = ["Generator calibration", "Synthetic-to-real transfer", "Language-model gate",
          "Triage rankers and cost share", "Fairness", "Flag cards (explaining a flag)", "Other"]
VERDICTS = [("Held", GOOD), ("Partly held / mixed", WARNING), ("Did not hold", CRITICAL),
            ("Informative / design, no gate", NEUTRAL), ("Staged or cancelled", SURFACE)]
FLAG_CARD_EXPS = {61, 62, 63, 65, 66, 74, 76, 77}


def _verdict(text):
    t = text.lower().replace("*", "")
    if re.match(r"(staged|cancelled)", t):
        return "Staged or cancelled"
    if re.search(r"did not hold|does not hold|clean negative|not hold as stated", t) and not t.startswith("partially"):
        return "Did not hold"
    if re.match(r"(partial|partly|held in part|mixed|held weakly|held with filters|held with a surprise|"
                r"largely|held for fidelity|persistent pool ports|mostly)", t):
        return "Partly held / mixed"
    if re.match(r"(informative|design delivered|measured|load-bearing|eval discriminates)", t):
        return "Informative / design, no gate"
    if re.match(r"(held|gate pass|pass|adopted)", t):
        return "Held"
    raise ValueError(f"unclassified verdict: {text[:80]}")


def _track(num, gate):
    g = gate.lower()
    if num in FLAG_CARD_EXPS:
        return "Flag cards (explaining a flag)"
    if g.startswith(("calibration", "rules recovery")):
        return "Generator calibration"
    if g.startswith("transfer /") or g.startswith("production"):
        return "Triage rankers and cost share"
    if g.startswith("transfer"):
        return "Synthetic-to-real transfer"
    if g.startswith("lm gate"):
        return "Language-model gate"
    if g.startswith("fairness"):
        return "Fairness"
    return "Other"


def _leaky(r):
    """Ranker results from exp56 on used the issued benefit with reviewer-recorded facts (exp106)."""
    return r["num"] >= 56 and r["track"] in ("Triage rankers and cost share", "Fairness")


def load_ledger(last=83):
    rows, lines = [], (REPO / "README.md").read_text().splitlines()
    start = lines.index("| # | Experiment | Gate | Verdict |")
    for line in lines[start:]:
        if not line.startswith("|"):
            break  # the index table ends; later tables reuse experiment numbers
        m = re.match(r"\| (\d+)([a-z]?)(?:–(\d+))? \| (.+?) \| (.+?) \| (.+) \|$", line)
        if not m:
            continue
        num = int(m.group(1))
        if num > last:
            continue
        title = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", m.group(4))
        verdict_text = m.group(6)
        exp_id = f"{num}{m.group(2)}" + (f"–{m.group(3)}" if m.group(3) else "")
        rows.append({"exp": exp_id, "num": num, "sub": m.group(2), "title": title, "gate": m.group(5),
                     "track": _track(num, m.group(5)), "verdict": _verdict(verdict_text),
                     "verdict_text": verdict_text.replace("**", "")})
    return rows


def plot_ledger(rows):
    fig, ax = plt.subplots(figsize=(15, 6.4), dpi=170, facecolor=SURFACE)
    fig.subplots_adjust(left=0.2, right=0.84, top=0.78, bottom=0.12)
    _axes(ax, "", grid=None)
    color = dict(VERDICTS)
    for r in rows:
        y = TRACKS.index(r["track"])
        x = r["num"] + (0.45 if r["sub"] else 0)
        fill = color[r["verdict"]]
        ax.add_patch(plt.Rectangle((x - 0.45, y - 0.36), 0.9 if not r["sub"] else 0.5, 0.72, facecolor=fill,
                                   edgecolor=MUTED if fill == SURFACE else SURFACE, linewidth=1.0,
                                   linestyle="--" if fill == SURFACE else "-",
                                   hatch="////" if _leaky(r) else None))
    for i, track in enumerate(TRACKS):
        mine = [r for r in rows if r["track"] == track]
        counts = [(v, sum(r["verdict"] == v for r in mine)) for v, _ in VERDICTS]
        held = counts[0][1]
        ax.text(86, i, f"{len(mine)}: {held} held · {counts[1][1]} partly · {counts[2][1]} not",
                va="center", fontsize=8, color=INK_2)
    ax.set_xlim(0, 85)
    ax.set_ylim(len(TRACKS) - 0.5, -0.6)
    ax.set_yticks(range(len(TRACKS)), TRACKS, fontsize=9, color=INK)
    ax.set_xticks([1, 10, 20, 30, 40, 50, 60, 70, 80, 83])
    ax.set_xlabel("Experiment number (Sep 28 → Oct 10, 2026). Lettered follow-ups (4b, 6b, 8a/b, 81b) sit in the "
                  "right half of their cell.", fontsize=8, color=MUTED)
    ax.tick_params(axis="y", length=0)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    n = len(rows)
    total = {v: sum(r["verdict"] == v for r in rows) for v, _ in VERDICTS}
    fig.text(0.2, 0.93, "snap-qc QC review: every experiment from exp1 to exp83, by track and verdict",
             fontsize=15, fontweight="bold", color=INK)
    fig.text(0.2, 0.885, f"{n} entries: {total['Held']} held, {total['Partly held / mixed']} partly held, "
             f"{total['Did not hold']} did not hold. The work moved from tuning the synthetic-case generator "
             f"(exp1–45) to rankers, the model gate and flag cards (exp52–83).", fontsize=9.5, color=INK_2)
    fig.legend(handles=[Patch(facecolor=c, edgecolor=MUTED if c == SURFACE else c,
                              linestyle="--" if c == SURFACE else "-", label=v) for v, c in VERDICTS]
               + [Patch(facecolor=SURFACE, edgecolor=INK_2, hatch="////",
                        label="numbers inflated by the leak found Oct 26 (exp106); restated in exp107–112")],
               loc="upper left", bbox_to_anchor=(0.2, 0.865), ncol=3, frameon=False, fontsize=8.5,
               labelcolor=INK_2)
    _save(fig, "snap-qc-verdicts.png")
    _write_csv(OUT / "snap-qc-verdicts.csv", ["exp", "track", "verdict", "gate", "title", "verdict_text", "leaky"],
               [[r["exp"], r["track"], r["verdict"], r["gate"], r["title"], r["verdict_text"], _leaky(r)] for r in rows])


# --- track panels -------------------------------------------------------------

# Synthetic/real ratio for one finding element, before -> after, as each
# experiment's README verdict states it. Only moves with both ends are kept.
CALIBRATION_MOVES = [
    (7, "household composition", 2.86, 1.27), (7, "arithmetic", 3.47, 1.42),
    (11, "medical", 0.11, 0.67), (11, "household composition", 1.16, 1.91),
    (12, "dependent care", 0.03, 0.56), (13, "nature 57", 0.50, 1.04),
    (21, "household composition", 1.59, 1.11), (21, "arithmetic", 1.51, 1.10),
    (28, "nature 57", 1.16, 1.03), (28, "dependent care", 0.44, 0.89), (32, "medical", 0.64, 0.71),
]
ELEMENTS = ["household composition", "arithmetic", "medical", "dependent care", "nature 57"]


def panel_calibration(ax):
    _axes(ax, "a. Generator calibration: element mix, synthetic ÷ real",
          "Arrow = one fix, before → after (1.0 = matches real QC). From README verdicts.")
    exps = sorted({m[0] for m in CALIBRATION_MOVES})
    ax.axhspan(0.8, 1.25, color=GRID, alpha=0.6, zorder=0)
    ax.axhline(1.0, color=MUTED, linewidth=1, zorder=1)
    for e, el, before, after in CALIBRATION_MOVES:
        k = ELEMENTS.index(el)
        same = [m for m in CALIBRATION_MOVES if m[0] == e]
        x = exps.index(e) + (same.index((e, el, before, after)) - (len(same) - 1) / 2) * 0.22
        ax.annotate("", xy=(x, after), xytext=(x, before),
                    arrowprops=dict(arrowstyle="-|>", color=SERIES[k], lw=2, mutation_scale=12))
        ax.plot(x, before, "o", color=SERIES[k], markersize=4, markeredgecolor=SURFACE, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(0.025, 4.5)
    ax.set_yticks([0.03, 0.1, 0.3, 1, 3], ["0.03×", "0.1×", "0.3×", "1×", "3×"])
    ax.set_xticks(range(len(exps)), [f"exp{e}" for e in exps], fontsize=8)
    ax.set_xlim(-0.6, len(exps) - 0.4)
    ax.text(len(exps) - 0.45, 1.27, "within 0.8–1.25×", fontsize=7, color=INK_2, ha="right", va="bottom")
    ax.legend(handles=[plt.Line2D([], [], color=SERIES[i], lw=2, label=el) for i, el in enumerate(ELEMENTS)],
              loc="lower right", fontsize=7, frameon=False, labelcolor=INK_2, ncol=2)


def panel_autocal(ax, rows):
    _axes(ax, "b. Automatic generator calibration (exp81, exp81b)",
          "Search climbed on its own seeds, then lost to the hand-tuned PA1 on the locked holdout")
    for k, (name, label) in enumerate([("exp81", "exp81, one seed"), ("exp81b", "exp81b, multi-seed")]):
        log = json.loads((EXP / f"{name}_log.json").read_text())["log"]
        res = json.loads((EXP / f"{name}_results.json").read_text())
        gens = [g["gen"] for g in log]
        ax.scatter(gens, [g["best_child"] for g in log], color=SERIES[k], alpha=0.25, s=12, linewidths=0)
        ax.step(gens, [g["parent_score"] for g in log], where="post", color=SERIES[k], lw=2, label=label)
        hold = res["holdout"]["best"]["element_macroF1"]
        ax.plot(64 + k * 2, hold, marker="D", color=SERIES[k], markersize=7, markeredgecolor=SURFACE)
        ax.text(64 + k * 2 + 0.8, hold, f"{hold:.3f}", fontsize=7.5, color=INK_2, va="center")
        for g in log:
            rows.append(["b", name, f"gen {g['gen']}", "parent_score", round(g["parent_score"], 4)])
        rows.append(["b", name, "locked holdout", "element_macroF1", round(hold, 4)])
        pa1 = res["holdout"]["PA1"]["element_macroF1"]
    ax.axhline(pa1, color=INK_2, lw=1, ls="--")
    ax.text(0, pa1 + 0.0015, f"hand-tuned PA1 on the locked holdout ({pa1:.3f})", fontsize=7.5, color=INK_2)
    ax.axvline(61.5, color=GRID, lw=1)
    ax.set_xticks([0, 20, 40, 59, 65], ["0", "20", "40", "59", "holdout"], fontsize=8)
    ax.set_xlabel("Search generation (step line = accepted parent; dots = best child)", fontsize=7.5, color=MUTED)
    ax.set_ylabel("Element macro-F1 (higher is better)", fontsize=8, color=INK_2)
    ax.legend(loc="lower center", fontsize=7.5, frameon=False, labelcolor=INK_2, ncol=2)


def panel_exp52(ax, rows):
    _axes(ax, "c. Training the QC model: exp52's search on the dev set (197 cases)",
          "Every trial in run order. Step = best so far; GRPO alone never cleared 0.1, SFT did")
    trials = []
    for name, kind in (("exp52_sweep_results.tsv", "GRPO"), ("exp52_sft_results.tsv", "SFT")):
        with (EXP / name).open() as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r["trial"] == "base" and trials:
                    continue
                try:
                    score = float(r["dev_composite"])
                except ValueError:
                    score = None  # diverged (nan)
                method = "base" if r["trial"] == "base" else ("SFT + GRPO" if r["trial"].startswith("grpo")
                                                              else kind)
                trials.append((r["trial"], method, score))
    shapes = {"base": "s", "GRPO": "^", "SFT": "o", "SFT + GRPO": "D"}
    best, xs, ys = -1, [], []
    for i, (name, method, score) in enumerate(trials):
        rows.append(["c", "exp52", name, method, score])
        if score is None:
            ax.plot(i, 0, marker="x", color=CRITICAL, markersize=6)
            continue
        gain = score - best
        new = score > best
        ax.scatter(i, score, marker=shapes[method], color=SERIES[0], s=34, alpha=1 if new else 0.3,
                   edgecolors=SURFACE, linewidths=0.8, zorder=3)
        if new:
            best = score
            if score > 0.05 and gain >= 0.03:
                label = name.replace("_lr1e-5", "").replace("sft_", "SFT ").replace("_ckpt", " step ")
                label = label.replace("_", " ").replace("SFT 600 step 400", "SFT, step 400 (chosen)")
                ax.annotate(label, (i, score), xytext=(-6, 6), ha="right",
                            textcoords="offset points", fontsize=6.8, color=INK_2)
        xs.append(i)
        ys.append(best)
    ax.step(xs, ys, where="post", color=SERIES[0], lw=1.6, zorder=2)
    seed = next((i, s) for i, (n, _, s) in enumerate(trials) if n == "sft_lr1e-5_600_seed53_ckpt400")
    ax.annotate(f"same recipe, other seed: {seed[1]:.3f}", seed, xytext=(-10, -26), textcoords="offset points",
                fontsize=7, color=INK_2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xlabel(f"{len(trials)} trials in the order they were run (✕ = diverged)", fontsize=7.5, color=MUTED)
    ax.set_ylabel("Dev composite (0 = most-frequent dummy)", fontsize=8, color=INK_2)
    ax.set_xticks([])
    ax.legend(handles=[plt.Line2D([], [], marker=m, color=INK_2, linestyle="", markersize=5, label=k)
                       for k, m in shapes.items()], loc="upper left", fontsize=7, frameon=False,
              labelcolor=INK_2, ncol=4, bbox_to_anchor=(0, 0.94))


# Fresh 1,200-case set, eval v1.2 (exp59, exp60, exp71 result tables).
GATE = [
    ("E2B untrained", 0.000, "exp60", None),
    ("E4B untrained", 0.005, "exp59", None),
    ("E4B trained to list differences first", 0.072, "exp71", "−0.260 [−0.279, −0.241] vs answer-only"),
    ("Gradient-boosted classifier, same data", 0.240, "exp59", None),
    ("E2B, answer-only SFT", 0.249, "exp60", "missed the T3 leg (0.190 < 0.210)"),
    ("E4B, answer-only SFT, step 400", 0.334, "exp59", "PASS: +0.328 [+0.309, +0.347], 5/5 wins"),
]


def panel_gate(ax, rows):
    _axes(ax, "d. The language-model gate, confirmed on 1,200 fresh real QC cases",
          "Composite skill above a dummy (pre-registered). Only answer-only SFT on E4B passed", grid="x")
    for i, (name, score, src, note) in enumerate(GATE):
        trained = "SFT" in name or "trained" in name and "untrained" not in name
        c = SERIES[0] if trained else (SERIES[1] if "classifier" in name else MUTED)
        ax.plot([0, score], [i, i], color=GRID, lw=2, zorder=1)
        ax.plot(score, i, "o", color=c, markersize=8, markeredgecolor=SURFACE, zorder=3)
        ax.text(score + 0.008, i, f"{score:.3f}" + (f"   {note}" if note else ""), va="center", fontsize=7.5,
                color=INK_2)
        ax.text(0.003, i - 0.32, f"{name} ({src})", fontsize=8, color=INK, va="center")
        rows.append(["d", src, name, "fresh composite", score])
    ax.set_yticks([])
    ax.set_ylim(len(GATE) - 0.5, -0.8)
    ax.set_xlim(0, 0.62)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Composite (0 = dummy, 1 = ceiling)", fontsize=7.5, color=MUTED)


GENERATIONS = [
    ("Per-state\n(exp68)", True),
    ("+ small states\npooled (exp75)", True),
    ("Context-aware\npooled (exp82/83)", True),
    ("Leak-free\n(exp107)", False),
    ("Official error\nlabel (exp112)", False),
]


def _ranker_generations():
    e68 = {r["state"]: r["holdout"]["top20"]["lift"] for r in json.loads((EXP / "exp68_results.json").read_text())}
    pooled = dict(e68)
    for st, r in json.loads((EXP / "exp75_results.json").read_text()).items():
        pooled[st] = r[r["adopted"]]["holdout"]
    lifts = [e68, pooled]
    for name in ("exp83_results.json", "exp83_leakfree_results.json", "exp83_official_results.json"):
        lifts.append({st: r["top20"]["lift"] for st, r in json.loads((EXP / name).read_text()).items()})
    return lifts


def panel_rankers(ax, rows):
    _axes(ax, "e. Triage rankers: top-20% lift for all 53 jurisdictions, each generation",
          "Dollars found by reviewing the ranker's top 20% ÷ a random 20% (holdout). Bar = median")
    for g, ((label, leaky), lifts) in enumerate(zip(GENERATIONS, _ranker_generations())):
        vals = sorted(lifts.values())
        c = LEAKY if leaky else LEAKFREE
        n = len(vals)
        for j, v in enumerate(vals):
            ax.scatter(g + ((j * 0.618) % 1 - 0.5) * 0.5, v, color=c, s=14, alpha=0.55, linewidths=0)
        med = statistics.median(vals)
        ax.plot([g - 0.32, g + 0.32], [med, med], color=INK, lw=2)
        ax.text(g + 0.36, med, f"{med:.2f}×", fontsize=8, color=INK, va="center", fontweight="bold")
        for st, v in sorted(lifts.items()):
            rows.append(["e", label.replace("\n", " "), st, "top20_lift", v])
        assert n == 53, (label, n)
    ax.axhline(1, color=MUTED, lw=1)
    ax.text(4.75, 1.05, "random", fontsize=7, color=INK_2, ha="right")
    ax.axvspan(2.5, 4.6, color=GRID, alpha=0.35, zorder=0)
    ax.text(2.55, 6.0, "Oct 26: issued benefit found leaking the\nreviewer's corrected facts (exp106)",
            fontsize=7.2, color=INK_2, va="top")
    ax.set_xticks(range(len(GENERATIONS)), [g for g, _ in GENERATIONS], fontsize=7.5)
    ax.set_xlim(-0.6, 4.75)
    ax.set_ylim(0, 6.3)
    ax.set_ylabel("Top-20% lift (×)", fontsize=8, color=INK_2)
    ax.legend(handles=[Patch(color=LEAKY, label="saw the leaked field"), Patch(color=LEAKFREE, label="leak-free")],
              loc="upper left", fontsize=7.5, frameon=False, labelcolor=INK_2)


# FY2028 state cost share avoided by ranker-guided reviews, $B/yr: central (low, high).
COST = [
    ("exp69\nOct 10", 5.28, 0.32, 9.41, True, "first estimate"),
    ("exp78\nOct 10", 3.49, 0.30, 7.33, True, "fairness floor,\ntop-20% basis"),
    ("exp93\nOct 15", 6.05, 0.39, 10.06, True, "context models,\nfloor on"),
    ("exp107\nOct 26", 3.42, 0.21, 6.63, False, "leak-free"),
    ("exp111\nOct 26", 3.15, 0.21, 7.05, False, "benefit-gap\nlabel"),
    ("exp112\nOct 27", 4.47, 0.21, 8.24, False, "official label\n(current)"),
]


def panel_cost(ax, rows):
    _axes(ax, "f. The FY2028 cost-share headline, as it was restated",
          r"Avoided per year, central with low–high range. Random reviews avoid \$1.03B (\$0.16–2.39B)")
    ax.axhspan(0.16, 2.39, color=GRID, alpha=0.6, zorder=0)
    ax.axhline(1.03, color=MUTED, lw=1, ls="--")
    ax.text(5.45, 1.1, "random reviews", fontsize=7, color=INK_2, ha="right")
    for i, (label, mid, lo, hi, leaky, note) in enumerate(COST):
        c = LEAKY if leaky else LEAKFREE
        ax.plot([i, i], [lo, hi], color=c, lw=2, alpha=0.45, solid_capstyle="round")
        ax.plot(i, mid, "o", color=c, markersize=9, markeredgecolor=SURFACE, zorder=3)
        ax.text(i + 0.12, mid, f"\\${mid:.2f}B", fontsize=8, color=INK, va="center", fontweight="bold")
        ax.text(i, 10.9, note, fontsize=6.8, color=INK_2, ha="center", va="top")
        rows.append(["f", label.split()[0], "central/low/high $B", note.replace("\n", " "), f"{mid}/{lo}/{hi}"])
    ax.set_xticks(range(len(COST)), [c[0] for c in COST], fontsize=7.5)
    ax.set_ylim(0, 11)
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylabel(r"\$ billions per year", fontsize=8, color=INK_2)


def plot_tracks():
    fig, axes = plt.subplots(3, 2, figsize=(15, 17), dpi=170, facecolor=SURFACE)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.885, bottom=0.04, hspace=0.42, wspace=0.28)
    rows = []
    panel_calibration(axes[0, 0])
    for e, el, b, a in CALIBRATION_MOVES:
        rows.append(["a", f"exp{e}", el, "synthetic/real before→after", f"{b}→{a}"])
    panel_autocal(axes[0, 1], rows)
    panel_exp52(axes[1, 0], rows)
    panel_gate(axes[1, 1], rows)
    panel_rankers(axes[2, 0], rows)
    panel_cost(axes[2, 1], rows)
    fig.text(0.07, 0.962, "snap-qc QC review: the numbers behind each track", fontsize=16, fontweight="bold",
             color=INK)
    fig.text(0.07, 0.948, "Hand fixes moved the generator toward real QC; automatic search overfit. Answer-only SFT "
             "passed the model gate. The rankers' early lifts were inflated by a leak found on Oct 26;\n"
             "leak-free, they still find 2.7–3.0× the error dollars of random review. Orange marks results that "
             "saw the leaked field.", fontsize=9.5, color=INK_2, va="top")
    _save(fig, "snap-qc-tracks.png")
    _write_csv(OUT / "snap-qc-tracks.csv", ["panel", "source", "item", "measure", "value"], rows)


# --- routing signals (exp104) ---------------------------------------------------


def _md_tables(path, start="<!-- AUTO-RESULTS:START -->", end="<!-- AUTO-RESULTS:END -->"):
    text = path.read_text()
    block = text[text.index(start):text.index(end)]
    tables, heading = {}, None
    for line in block.splitlines():
        if line.startswith("### "):
            heading = line[4:].strip()
        elif line.startswith("|") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            tables.setdefault(heading, []).append(cells)
    return {h: [dict(zip(t[0], r)) for r in t[1:]] for h, t in tables.items()}


def _pct(s):
    return float(re.match(r"-?[\d.]+", s.strip()).group())


def plot_routing():
    tables = _md_tables(EXP / "exp104_routing_signals.md")
    retrieval = next(v for k, v in tables.items() if k.startswith("Retrieval"))
    signals = next(v for k, v in tables.items() if k.startswith("How well"))
    singles = next(v for k, v in tables.items() if k.startswith("Single setups"))
    routers = next(v for k, v in tables.items() if k.startswith("Routers"))
    thresholds = next(v for k, v in tables.items() if k.startswith("Threshold"))
    ceilings = next(v for k, v in tables.items() if k.startswith("Ceilings"))
    rows = []

    fig = plt.figure(figsize=(15, 15), dpi=170, facecolor=SURFACE)
    gs = fig.add_gridspec(2, 2, left=0.13, right=0.97, top=0.88, bottom=0.05, hspace=0.32, wspace=0.62,
                          height_ratios=[1, 1.05])

    # a. retrieval
    ax = fig.add_subplot(gs[0, 0])
    _axes(ax, "a. Retrieval: is the gold document in the top results?",
          "224-question hard set, BM25 unless noted. Hollow = top 1, filled = top 5", grid="x")
    key = next(k for k in retrieval[0] if k.startswith("Our hard set"))
    data = []
    for r in retrieval:
        h1, h5 = (_pct(x) for x in r[key].split("/"))
        ca = _pct(r[next(k for k in r if "California" in k)])
        data.append((r["Config"], h1, h5, ca))
    data.sort(key=lambda d: d[2])
    for i, (cfg, h1, h5, ca) in enumerate(data):
        hi = cfg in ("pre_letters", "current", "cited_letters_cite_only")
        c = SERIES[0] if hi else MUTED
        ax.plot([h1, h5], [i, i], color=c, lw=2, alpha=0.5)
        ax.plot(h1, i, "o", markerfacecolor=SURFACE, markeredgecolor=c, markersize=6)
        ax.plot(h5, i, "o", color=c, markersize=7, markeredgecolor=SURFACE)
        ax.text(h5 + 1, i, f"{h5:.1f}%", va="center", fontsize=7.5, color=INK if hi else INK_2,
                fontweight="bold" if hi else None)
        rows.append(["a", cfg, "hard set hit@1 / hit@5 / California QA hit@5", "", f"{h1}/{h5}/{ca}"])
    names = {"pre_letters": "before the CDSS letters", "current": "letters in search (current)",
             "cited_letters_cite_only": "letters cite-only (the fix)"}
    ax.set_yticks(range(len(data)), [names.get(d[0], d[0].replace("_", " ")) for d in data], fontsize=8)
    ax.set_xlim(20, 95)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("% of questions", fontsize=7.5, color=MUTED)

    # b. signals
    ax = fig.add_subplot(gs[0, 1])
    _axes(ax, "b. Which signals flag the plain agent's mistakes?",
          "AUROC on Cornell (52 wrong of 500); 0.5 = chance", grid="x")
    sig = sorted(signals, key=lambda r: float(r["AUROC"]))

    def family(name):
        n = name.lower()
        if "differ" in n or "disagrees" in n:
            return "disagreement between setups", SERIES[0]
        if "confidence" in n or "agreement" in n:
            return "model's own confidence", SERIES[1]
        return "other", MUTED

    for i, r in enumerate(sig):
        au = float(r["AUROC"])
        fam, c = family(r["Signal (higher = riskier)"])
        ax.plot([0.5, au], [i, i], color=GRID, lw=2)
        ax.plot(au, i, "o", color=c, markersize=8, markeredgecolor=SURFACE)
        ax.text(au + 0.004, i, f"{au:.2f}", va="center", fontsize=7.5, color=INK_2)
        rows.append(["b", r["Signal (higher = riskier)"], "AUROC", fam, au])
    ax.axvline(0.5, color=MUTED, lw=1)
    ax.set_yticks(range(len(sig)), [r["Signal (higher = riskier)"].replace(" (higher = riskier)", "")
                                    for r in sig], fontsize=7.5)
    ax.set_xlim(0.48, 0.76)
    ax.tick_params(axis="y", length=0)
    ax.legend(handles=[plt.Line2D([], [], marker="o", color=c, linestyle="", label=l) for l, c in
                       [("disagreement between setups", SERIES[0]), ("model's own confidence", SERIES[1]),
                        ("other", MUTED)]], loc="lower right", fontsize=7.5, frameon=False, labelcolor=INK_2)

    # c. router ladder
    ax = fig.add_axes([0.36, 0.05, 0.6, 0.39])
    _axes(ax, "c. Routing each question to a setup: what it bought, what a perfect router could, and the confirmation",
          "Cornell accuracy (500). Routers re-use answers from existing runs (exploratory); exp105 re-ran the "
          "topic router fresh, pre-registered", grid="x")
    plain = _pct(next(r for r in singles if r["Setup"] == "plain")["Accuracy"])
    ladder = [("Single setups", r["Setup"].replace("datenotes", "date + notes").replace("notes_check",
                                                                                      "notes + check"),
               _pct(r["Accuracy"]), None, MUTED) for r in singles]
    for r in routers:
        ci = re.findall(r"-?[+\d.]+", r["vs plain (95% CI)"])
        lo, hi = plain + float(ci[1]), plain + float(ci[2])
        ladder.append(("Routers (exploratory)", r["Router"], _pct(r["Accuracy"]), (lo, hi), SERIES[0]))
    best_t = max(thresholds, key=lambda r: _pct(r["Cross-validated accuracy"]))
    ladder.append(("Best threshold router\n(split-half CV)", best_t["Signal → escalate to"],
                   _pct(best_t["Cross-validated accuracy"]), None, SERIES[0]))
    for r in ceilings:
        ladder.append(("Perfect router (ceiling)", r["Setups available"], _pct(r["Oracle accuracy"]), None, MUTED))
    ladder.append(("exp105, fresh run", "plain agent (same run)", 88.2, None, SERIES[1]))
    ladder.append(("exp105, fresh run", "topic router: noncitizens → date + notes", 89.8, (88.8, 91.0), SERIES[1]))
    y, ticks, groups, prev = 0, [], [], None
    for grp, name, acc, ci, c in ladder:
        if grp != prev:
            if prev is not None:
                y += 0.4
            groups.append((grp.replace("\n", " "), y))
            y += 1
            prev = grp
        if ci:
            ax.plot(ci, [y, y], color=c, lw=2, alpha=0.4)
        hollow = grp.startswith("Perfect")
        ax.plot(acc, y, "o", markersize=7, color=c, markerfacecolor=SURFACE if hollow else c,
                markeredgecolor=c if hollow else SURFACE)
        ax.text(max(acc, ci[1] if ci else acc) + 0.12, y, f"{acc:.1f}%", va="center", fontsize=7.5, color=INK_2)
        ticks.append((y, name))
        rows.append(["c", grp.replace("\n", " "), name, "accuracy", acc])
        y += 1
    ax.axvline(plain, color=MUTED, lw=1, ls="--")
    ax.text(plain + 0.08, -0.9, f"plain agent {plain:.1f}%", fontsize=7.5, color=INK_2, ha="center")
    ax.set_yticks([t for t, _ in ticks], [n for _, n in ticks], fontsize=7.5)
    ax.set_ylim(y - 0.4, -1.4)
    ax.set_xlim(85.5, 96.5)
    ax.tick_params(axis="y", length=0)
    for grp, gy in groups:
        ax.text(-0.005, gy, grp, transform=ax.get_yaxis_transform(), fontsize=8.5, color=INK, fontweight="bold",
                va="center", ha="right")
    ax.text(92.0, ticks[-1][0], "exp105 interval: router − plain, +1.6 [+0.6, +2.8]", fontsize=7, color=INK_2,
            va="center")
    ax.set_xlabel("% correct", fontsize=7.5, color=MUTED)

    fig.text(0.05, 0.957, "snap-qc exp104: what a per-question routing layer could use", fontsize=16,
             fontweight="bold", color=INK)
    fig.text(0.05, 0.937, "Keeping the CDSS letters out of search fixed retrieval. Models' own confidence can't "
             "tell right from wrong (AUROC ≈ 0.5);\ndisagreement between setups can. A topic router was the "
             "first routing gain to hold up in a fresh, pre-registered run (exp105).", fontsize=9.5,
             color=INK_2, va="top")
    _save(fig, "snap-qc-routing.png")
    _write_csv(OUT / "snap-qc-routing.csv", ["panel", "item", "measure", "group", "value"], rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plot_ledger(load_ledger())
    plot_tracks()
    plot_routing()


if __name__ == "__main__":
    main()
