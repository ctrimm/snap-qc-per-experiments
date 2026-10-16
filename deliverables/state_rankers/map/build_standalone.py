"""Build the standalone product in outputs/: the report and a self-contained state map.

outputs/
  README.md
  report/                     the executive whitepaper (PDF, Markdown, HTML)
  state_map/index.html        the map dashboard as one file: open it in any browser, offline;
                              same page code as the hosted dashboard (map/index.html), with a small
                              stand-in for the dashboard runtime, the data embedded, and d3 inlined
  state_map/data/             the data it shows (JSON and CSV)

Run after build_datasets.py:  python3 deliverables/state_rankers/map/build_standalone.py
"""
import csv
import datetime
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "outputs"
DATASETS = ["state_results", "state_shapes", "scenario_assumptions"]

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>SNAP Triage Rankers by State</title>
<style>
  :root {
    --color-fg: #1c2530; --color-fg-muted: #5a6573; --color-bg: #f6f7f5; --color-panel: #ffffff;
    --color-border-line: #dce1df; --color-ok: #1f7a4d; --color-warn: #8a5a00; --color-bad: #b42318;
    --cds-chart-grid: #e3e8ea; --cds-chart-muted: #c3cbcf; --cds-chart-axis: #9aa4aa; --cds-chart-reference: #7d878d;
    --cds-chart-status-critical: #c2410c; --cds-surface-popover: #ffffff; --cds-border: #d0d6d9;
    --cds-shadow-popover: 0 6px 18px rgba(20, 30, 40, .14); --cds-text-secondary: #5a6573;
    --series-1: #1d6f8a; --series-2: #d9772b; --series-3: #e3b341;
    --font-anthropic-sans: "Public Sans", "Segoe UI", system-ui, -apple-system, Helvetica, Arial, sans-serif;
    --font-anthropic-serif: Charter, "Iowan Old Style", Georgia, "Times New Roman", serif;
    --cds-font-size-caption: .8rem; --cds-font-size-body: .95rem; --cds-font-size-heading: 1.1rem; --cds-font-size-title: 1.9rem;
    --cds-font-weight-medium: 600;
    --cds-gap-xs: .25rem; --cds-gap-sm: .5rem; --cds-gap-md: .9rem; --cds-gap-lg: 1.4rem; --cds-gap-xl: 2rem;
    --cds-pad-xs: .3rem; --cds-pad-sm: .55rem; --cds-pad-md: .9rem; --cds-pad-lg: 1.2rem; --cds-pad-xl: 1.8rem;
    --cds-radius: 10px; --cds-dur-slow: .4s; --cds-ease-out: cubic-bezier(.2, .8, .2, 1);
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --color-fg: #e6ebee; --color-fg-muted: #a3adb4; --color-bg: #111619; --color-panel: #182025;
      --color-border-line: #2a343a; --color-warn: #e0b45c; --color-bad: #f2876f;
      --cds-chart-grid: #2a343a; --cds-chart-muted: #3d4950; --cds-chart-status-critical: #f08a4b;
      --cds-surface-popover: #1d262c; --cds-border: #33404a; --cds-text-secondary: #a3adb4;
      --series-1: #5fb3cf; --series-2: #f0a05a; --series-3: #f1cf6b; color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --color-fg: #e6ebee; --color-fg-muted: #a3adb4; --color-bg: #111619; --color-panel: #182025;
    --color-border-line: #2a343a; --color-warn: #e0b45c; --color-bad: #f2876f;
    --cds-chart-grid: #2a343a; --cds-chart-muted: #3d4950; --cds-chart-status-critical: #f08a4b;
    --cds-surface-popover: #1d262c; --cds-border: #33404a; --cds-text-secondary: #a3adb4;
    --series-1: #5fb3cf; --series-2: #f0a05a; --series-3: #f1cf6b; color-scheme: dark;
  }
  html, body { margin: 0; }
  body { background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); }
  #dash-root { padding-inline: clamp(16px, 4vw, 40px); padding-block: 28px 48px; }
  .dash-skeleton { color: transparent !important; background: var(--cds-chart-grid); border-radius: 6px; min-height: 1em; }
  .sa-foot { max-width: 78rem; margin: 24px auto 0; font-size: .8rem; color: var(--color-fg-muted); }
</style>
</head>
<body>
<div id="dash-root">
"""

SHIM = """<script>
/* Stand-in for the hosted dashboard runtime: the same page code runs on embedded data. */
(function () {
  const raw = {};
  document.querySelectorAll('script[type="application/json"][data-dataset]').forEach((el) => { raw[el.dataset.dataset] = JSON.parse(el.textContent); });
  const calcs = {}, subs = [];
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  window.dash = {
    data(id) {
      if (id in raw) return { status: 'ok', data: raw[id], columns: raw[id].length ? Object.keys(raw[id][0]) : [], meta: [] };
      if (id in calcs) { const c = calcs[id]; return { status: 'ok', data: c.fn(...c.inputs.map((i) => dash.data(i).data)), meta: [] }; }
      return { status: 'missing', data: [] };
    },
    calc(id, spec) { calcs[id] = spec; },
    onData(fn) { subs.push(fn); fn(); },
    params() { return {}; }, setParams() {}, resetParams() {}, setLink() {}, refresh() {},
    get colors() { return [css('--series-1'), css('--series-2'), css('--series-3')]; },
  };
  let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => subs.forEach((f) => f()), 150); });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => subs.forEach((f) => f()));
})();
</script>
"""


def main():
    page = (HERE / "index.html").read_text()
    data_tags = "".join(
        f'<script type="application/json" data-dataset="{d}">{(HERE / f"{d}.json").read_text().replace("</", "<\\\\/")}</script>\n'
        for d in DATASETS)
    d3 = (HERE / "vendor/d3.v7.9.0.min.js").read_text()
    built = datetime.date.today().isoformat()
    foot = (f'<div class="sa-foot">Standalone copy built {built} from snap-qc-per-experiments '
            '(experiments exp68, exp69, exp72, exp75, exp83, exp93; USDA FY2025 payment error rates). '
            'Data files are in the data/ folder next to this page. d3 v7.9.0 © Mike Bostock (ISC license).</div>\n')
    html = HEAD + data_tags + f"<script>{d3}</script>\n" + SHIM + page + foot + "</div>\n</body>\n</html>\n"
    sm = OUT / "state_map"; (sm / "data").mkdir(parents=True, exist_ok=True)
    (sm / "index.html").write_text(html)
    for d in DATASETS:
        shutil.copy(HERE / f"{d}.json", sm / "data" / f"{d}.json")
    rows = json.loads((HERE / "state_results.json").read_text())
    with open(sm / "data/state_results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    shutil.copy(HERE / "vendor/d3-LICENSE.txt", sm / "data/d3-LICENSE.txt")
    rep = OUT / "report"; rep.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "md", "html"):
        shutil.copy(ROOT / f"whitepaper/whitepaper_snap_qc_triage.{ext}", rep / f"snap_qc_triage_report.{ext}")
    print(f"wrote {sm / 'index.html'} ({len(html) // 1024} KB) and {rep}")


if __name__ == "__main__":
    main()
