# Experiment 107 — leak-free rebuild of the deployed rankers

**Date:** 2026-10-26 (pre-registered before running) · **Code:** `SNAPQC_FEATURES=leakfree` switch in `exp58_agency_rankers.py` / `exp80_state_context.py`; runs of `exp83`, `exp93`, `exp79` and the exp80 packager under it · **Results:** `exp83_leakfree_results.json`, `exp93_leakfree_results.json`, `exp79_leakfree_results.json`, `deliverables/state_rankers/` (refit)

### Why

exp106 found that our ranker inputs paired the issued benefit (`RAWBEN`) with QC reviewers' corrected facts. Two inputs carry the issued benefit: `issued_benefit` and `benefit_share_of_max`. Dropping them (feature set L1) cut the median top-20% lift from 3.97× to 2.70×. This experiment rebuilds everything downstream on L1, so the papers, the dashboard and the packaged models can be corrected:
- the full held-out evaluation (exp83: lift, dollars per review hour, forecast check, fairness);
- the cost-share scenarios (exp93);
- the underpayment ranker (exp79);
- the packaged per-state models.

### Design

- **The switch:** with `SNAPQC_FEATURES=leakfree`, `agency_features()` omits `issued_benefit` and `context_features()` omits `benefit_share_of_max`. Unset, both are unchanged, so the published results still reproduce.
- **Results files:** the exp83, exp93 and exp79 scripts write `*_leakfree_results.json` under the switch, and leave the published files alone.
- **Unchanged:** splits, seeds, engine settings and each jurisdiction's adopted variant (from exp80/exp82, chosen on the leaky features; a stated bias). exp79 keeps its own-state models and exp68 configurations, as published.
- **Gate:** exp83 under the switch must reproduce exp106's L1 top-20% lifts (`exp106_leakfree_results.json`) in all 53 jurisdictions. exp93's built-in gate checks against `exp83_leakfree_results.json`.
- **Packaging:** each state's model is refit on all its rows plus all other jurisdictions' rows, as exp80's packager does, without the two inputs. `score_cases.py` builds features by name from the model's feature list, so old and new models both score.

### What it feeds

- **Papers and dashboard:** the state briefs (all generated from results), the replication guide appendix, the dashboard datasets, `cost_share_replicate.py`, and the older-adults numbers.
- **Hand-written figures** in the triage whitepaper, the project summary and the PA–NY brief are updated by hand and re-checked with `whitepaper/state_numbers.py`.

### Amendment 1 (2026-10-26, before it ran): the later-years test

The briefs also quote each state's later-years result (train FY2020–22, test the state's FY2023–24), taken from exp80/exp82, which used the leaky features. `exp107_timesplit.py` recomputes it under the switch: the adopted variant, other jurisdictions' FY2020–22 rows pooled in, and exp82's procedure. Results go to `exp107_timesplit_results.json`. The state-only comparisons in the briefs (exp68, also leaky) are dropped rather than recomputed.

### Results

<!-- AUTO-RESULTS:START -->
(pending)
<!-- AUTO-RESULTS:END -->
