# SNAP QC triage: report and state map

The finished product of this project, kept apart from the experiments, data and working files. Everything here can be opened and shared as is.

| | What it is |
|---|---|
| `report/snap_qc_triage_report.pdf` | The executive whitepaper: what was built, how well it works, what it could mean for FY2028 cost sharing, limitations and recommendations. Also as `.md` and `.html`. |
| `state_map/index.html` | An interactive map of all 53 SNAP jurisdictions (50 states, DC, Guam, Virgin Islands). Open it in any web browser; it works offline, with all data built in. Click a state for its numbers; sort and search the table below the map. |
| `state_map/data/` | The numbers the map shows: `state_results.csv` / `.json` (one row per jurisdiction), the cost-share scenario inputs, and the map outlines. |
| `charts/` | Research charts of the experiments themselves: `snap-qc-verdicts.png` (every experiment exp1–83 by track and verdict), `snap-qc-tracks.png` (the numbers behind each track, including the leak restatement), `snap-qc-routing.png` (exp104 routing signals and the exp105 confirmation). Each has a `.csv` table. Rebuilt by `uv run --no-project --with matplotlib python experiments/lab_charts.py`. |

## What the map shows

- **Top-20% lift:** how many times more error dollars a reviewer finds by working the top fifth of the ranker's queue instead of random cases, on held-out QC cases.
- **Dollars per review hour,** ranked vs random (30 minutes a review).
- **Elderly review vs risk:** whether elderly households get reviews in proportion to their error risk (1.0 = proportional), and what the fairness floor does.
- **FY2025 error rate** (USDA's official figures) and the **FY2028 cost share** a state would pay under H.R. 1, now and in a central scenario with ranker-guided reviews.

## Where the numbers come from

Federal SNAP Quality Control public-use files, FY2020–2024; USDA's FY2025 payment error rates (June 24, 2026). Methods, assumptions and every experiment behind these figures are in the repository's `experiments/` folder (deployed rankers: exp80/82, evaluated in exp83; cost scenarios: exp69 design, run on the deployed models with the fairness floor on in exp93; fairness: exp72/exp83; the earlier state-only rankers of exp68 are kept for reference) and summarized in the report. Cost-share figures are scenarios that show the size of the opportunity, not forecasts.

## Rebuilding

From the repository root, after any update to the experiments:

```bash
python3 deliverables/state_rankers/map/build_datasets.py
python3 deliverables/state_rankers/map/build_standalone.py
```

The same page code also runs as a hosted dashboard; this folder is its standalone copy. The map's charting library (d3 v7.9.0, ISC license) is included in the page; its license is in `state_map/data/d3-LICENSE.txt`.
