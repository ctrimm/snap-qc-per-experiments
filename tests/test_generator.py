"""The synthetic QC-case generator: sampler, case schema, invariants, determinism,
a loose calibration guard, the CLI and the PA variant."""
import json
import random
import subprocess
import sys
from collections import Counter

import pytest

from conftest import DIST, ROOT, generate
from synth import benefit, household, params

FACT_KEYS = {"hh_size", "n_kids", "earned", "unearned", "shelter", "sua", "medical_exp", "depcare",
             "senior_disabled", "review_month", "n_elderly", "n_disabled"}
CASE_KEYS = {"facts", "issued_facts", "correct_benefit", "issued_benefit", "finding", "dollar_error",
             "reportable", "variances"}
OPTIONAL_CASE_KEYS = {"unit_ineligible"}  # dollar_mech whole-unit cases only
VARIANCE_KEYS = {"element", "element_bucket", "nature", "cause", "timing"}

CONFIGS = {
    "default": {},
    "no-dollar-mechanisms": {"dollar_mechanisms": False},
    "retry-loop": {"persistent_buckets": False},
    "legacy-materialization": {"legacy_materialization": True},
}


# --- household sampler ---------------------------------------------------------

def test_sampler_is_deterministic_per_seed():
    a, b = random.Random(11), random.Random(11)
    assert [household.sample_household(a) for _ in range(50)] == \
           [household.sample_household(b) for _ in range(50)]


def test_sampler_households_have_the_schema_and_mostly_pass_the_screen():
    rng = random.Random(5)
    hh = [household.sample_household(rng) for _ in range(2000)]
    assert all(set(h) == FACT_KEYS for h in hh)
    assert all(1 <= h["hh_size"] <= 6 and 1 <= h["review_month"] <= 12 for h in hh)
    assert all(h["earned"] >= 0 and h["unearned"] >= 0 for h in hh)
    # The screen gives up after 25 draws (documented), so a few slip through.
    eligible = sum(household._income_eligible(h) for h in hh) / len(hh)
    assert eligible >= 0.99


# --- case invariants, for every generator mode -----------------------------------

@pytest.fixture(scope="module", params=list(CONFIGS), ids=list(CONFIGS))
def cases(request):
    from synth import dollar_mech
    try:
        return generate(1500, 7, **CONFIGS[request.param])
    finally:
        dollar_mech.disable()


def test_case_and_variance_schema(cases):
    for c in cases:
        assert CASE_KEYS <= set(c) <= CASE_KEYS | OPTIONAL_CASE_KEYS
        assert set(c["facts"]) == FACT_KEYS and set(c["issued_facts"]) == FACT_KEYS
        assert c["finding"] in (1, 2, 3)
        for v in c["variances"]:
            assert set(v) == VARIANCE_KEYS


def test_dollar_error_reportable_and_direction_agree(cases):
    for c in cases:
        diff = c["issued_benefit"] - c["correct_benefit"]
        assert c["dollar_error"] == abs(diff)
        assert c["reportable"] == (c["dollar_error"] > params.QC_ERROR_THRESHOLD)
        assert c["issued_benefit"] >= 0 and c["correct_benefit"] >= 0
        if c["finding"] == 2:
            assert diff > 0
        elif c["finding"] == 3:
            assert diff < 0


def test_correct_cases_are_clean_and_error_cases_record_variances(cases):
    for c in cases:
        if c["finding"] == 1:
            assert c["variances"] == [] and c["dollar_error"] == 0
            assert c["issued_facts"] == c["facts"]
        else:
            assert c["variances"] and c["dollar_error"] > 0


def test_correct_benefit_is_recomputable_except_whole_unit_ineligibility(cases):
    for c in cases:
        if c.get("unit_ineligible"):
            # The whole unit was ineligible: correct is $0, the issued benefit is all error,
            # recorded as one earned-income variance of nature 35.
            assert c["correct_benefit"] == 0 and c["finding"] == 2
            assert c["dollar_error"] == c["issued_benefit"]
            assert [(v["element_bucket"], v["nature"]) for v in c["variances"]] == [("earned", 35)]
            continue
        assert c["correct_benefit"] == benefit.compute(c["facts"])["benefit"]


# --- determinism and state hygiene ---------------------------------------------

def test_same_seed_same_cases_different_seed_different_cases():
    assert generate(200, 3) == generate(200, 3)
    assert generate(200, 3) != generate(200, 4)


def test_whole_unit_ineligibility_only_with_dollar_mechanisms():
    assert any(c.get("unit_ineligible") for c in generate(3000, 7))
    assert not any(c.get("unit_ineligible") for c in generate(3000, 7, dollar_mechanisms=False))


def test_dollar_mechanisms_do_not_leak_into_later_stock_runs():
    before = generate(300, 9, dollar_mechanisms=False)
    generate(300, 9)  # installs and removes the patches
    assert generate(300, 9, dollar_mechanisms=False) == before


# --- calibration guard (loose: catches breakage, not drift) --------------------

def test_default_mix_stays_near_the_calibrated_shape():
    cs = generate(5000, 7)
    n = len(cs)
    finding = Counter(c["finding"] for c in cs)
    assert 0.53 <= finding[1] / n <= 0.67          # seed 7: 0.60
    assert finding[2] > finding[3]                  # overissuances outnumber under
    assert 0.08 <= sum(c["reportable"] for c in cs) / n <= 0.17   # seed 7: 0.12
    small = [c["dollar_error"] <= params.QC_ERROR_THRESHOLD for c in cs if c["finding"] != 1]
    assert 0.55 <= sum(small) / len(small) <= 0.85  # real QC ~0.70 (exp26/31)


# --- CLI and the PA variant ------------------------------------------------------

def _run(args, tmp_path):
    out = tmp_path / "cases.jsonl"
    res = subprocess.run([sys.executable, *args, "--out", str(out)], cwd=ROOT, capture_output=True,
                         text=True, env={"PYTHONPATH": str(ROOT / "src")}, check=True)
    return [json.loads(line) for line in out.read_text().splitlines()], res.stderr


def test_cli_writes_n_cases_matching_the_in_process_loop(tmp_path):
    rows, err = _run(["-m", "synth.generate", "--n", "40", "--seed", "7", "--dist", str(DIST)], tmp_path)
    assert len(rows) == 40 and "wrote 40 cases" in err
    assert rows == json.loads(json.dumps(generate(40, 7)))


def test_cli_no_dollar_mechanisms_matches_the_stock_injector(tmp_path):
    rows, _ = _run(["-m", "synth.generate", "--n", "40", "--seed", "7", "--dist", str(DIST),
                    "--no-dollar-mechanisms"], tmp_path)
    assert rows == json.loads(json.dumps(generate(40, 7, dollar_mechanisms=False)))


def test_pa_variant_tags_cases_and_leaves_national_generation_untouched():
    from synth.pa_state import generate_pa  # shares module state with the national generator
    national = generate(200, 7)
    pa = [json.loads(line) for line in generate_pa(n=200, seed=7, dist=str(DIST))]
    assert all(c["state"] == "PA" and CASE_KEYS | {"state"} <= set(c) <= CASE_KEYS | OPTIONAL_CASE_KEYS | {"state"}
               for c in pa)
    assert all(c["finding"] in (1, 2, 3) for c in pa)
    assert generate(200, 7) == national
