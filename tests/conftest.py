"""Shared helpers for the synthetic QC-case generator tests.

Run from the repo root:  uv run --no-project --with pytest pytest tests
(the generator is standard-library only; no install needed).
"""
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from synth import dollar_mech, errors, household  # noqa: E402
from synth.distutil import load_dist  # noqa: E402

DIST = ROOT / "experiments/dist.json"


def generate(n, seed, *, dollar_mechanisms=True, persistent_buckets=True,
             legacy_materialization=False, max_attempts=12):
    """In-process copy of synth.generate.main's loop.

    enable_adopted() patches module state, so the mechanisms are always
    disabled again afterwards; otherwise one test's setting leaks into the next.
    """
    dist = load_dist(str(DIST))
    if dollar_mechanisms:
        dist = dollar_mech.enable_adopted(dist)
        injector = dollar_mech.inject_case
    else:
        injector = errors.inject
    try:
        rng = random.Random(seed)
        return [injector(household.sample_household(rng), rng, dist, max_attempts=max_attempts,
                         persistent_buckets=persistent_buckets,
                         legacy_materialization=legacy_materialization)
                for _ in range(n)]
    finally:
        if dollar_mechanisms:
            dollar_mech.disable()


@pytest.fixture(autouse=True)
def _stock_injector():
    """Every test starts and ends with the mechanism patches off."""
    dollar_mech.disable()
    yield
    dollar_mech.disable()
