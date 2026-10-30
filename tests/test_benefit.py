"""synth.benefit / synth.params: the FY2024 benefit approximation, by hand-worked cases."""
import pytest

from synth import benefit, params


def facts(**kw):
    base = {"hh_size": 1, "n_kids": 0, "earned": 0.0, "unearned": 0.0, "shelter": 0.0, "sua": 0,
            "medical_exp": 0.0, "depcare": 0.0, "senior_disabled": 0, "review_month": 1,
            "n_elderly": 0, "n_disabled": 0}
    base.update(kw)
    return base


def test_no_income_gets_the_maximum_allotment():
    assert benefit.compute(facts(hh_size=1))["benefit"] == 291


def test_earned_standard_and_excess_shelter_deductions():
    # 1000 earned: -200 (20%), -198 standard = 602; excess shelter 900 - 301 = 599; net 3
    r = benefit.compute(facts(hh_size=3, earned=1000.0, shelter=900.0))
    assert (r["earn_ded"], r["std_ded"], r["excess_shelter"], r["net"]) == (200, 198, 599.0, 3.0)
    assert r["benefit"] == 765  # floor(766 - 0.9)


def test_shelter_deduction_is_capped_for_non_elderly_households():
    r = benefit.compute(facts(hh_size=3, earned=1000.0, shelter=2000.0))
    assert r["excess_shelter"] == params.SHELTER_DEDUCTION_CAP
    assert r["net"] == 0.0 and r["benefit"] == 766


def test_elderly_disabled_get_medical_deduction_and_uncapped_shelter():
    # 1200 unearned - 198 standard - (135 - 35) medical = 902; shelter 1000 - 451 = 549; net 353
    r = benefit.compute(facts(unearned=1200.0, medical_exp=135.0, shelter=1000.0, senior_disabled=1))
    assert (r["med_ded"], r["excess_shelter"], r["net"]) == (100.0, 549.0, 353.0)
    assert r["benefit"] == 185  # floor(291 - 105.9)


def test_medical_deduction_needs_an_elderly_or_disabled_member():
    assert benefit.compute(facts(unearned=1200.0, medical_exp=500.0))["med_ded"] == 0.0


def test_small_households_get_the_minimum_benefit():
    assert benefit.compute(facts(hh_size=2, unearned=2000.0))["benefit"] == params.MINIMUM_BENEFIT


def test_larger_households_can_compute_to_zero():
    assert benefit.compute(facts(hh_size=3, unearned=4000.0))["benefit"] == 0


@pytest.mark.parametrize("fn, size8, step", [
    (params.max_allotment, 1751, 219),
    (params.gross_income_limit, 5478, 557),
    (params.net_income_limit, 4214, 429),
])
def test_tables_extend_past_eight_people(fn, size8, step):
    assert fn(8) == size8
    assert fn(10) == size8 + 2 * step


def test_standard_deduction_tops_out_at_six():
    assert params.standard_deduction(9) == params.standard_deduction(6) == 279
