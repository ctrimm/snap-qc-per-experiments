"""Shared loader for the empirical bundle: dist.json + eff.json + inject.json.

dist.json carries the empirical FY2024 QC distributions (built by
experiments/build_dist.py). eff.json carries per-bucket materialization
rates (experiments/measure_effectiveness.py). inject.json carries the
attrition-corrected injection coin per earner status and the attrition-
corrected 97-resolution coin per bucket (experiments/calibrate_injection.py).
JSON object keys that are really ints (nature/cause codes) are normalized
back on load.
"""
import json
from pathlib import Path


def load_dist(dist_path):
    dist_path = Path(dist_path)
    root = dist_path.parent
    with open(dist_path) as fh:
        dist = json.load(fh)
    eff_path = root / "eff.json"
    if eff_path.exists():
        with open(eff_path) as fh:
            dist["effectiveness"] = json.load(fh)
    inj_path = root / "inject.json"
    if inj_path.exists():
        with open(inj_path) as fh:
            dist["injection_rate"] = json.load(fh)
    dist["nature_given_bucket"] = {
        b: {int(k): v for k, v in d.items()}
        for b, d in dist["nature_given_bucket"].items()
    }
    for nkey in ("nature_given_bucket_earner", "nature_given_bucket_no_earner"):
        if nkey in dist:
            dist[nkey] = {
                b: {int(k): v for k, v in d.items()}
                for b, d in dist[nkey].items()
            }
    dist["cause_given_bucket"] = {
        b: {int(k): v for k, v in d.items()}
        for b, d in dist["cause_given_bucket"].items()
    }
    dist["bucket_probs"] = {b: float(v) for b, v in dist["bucket_probs"].items()}
    return dist
