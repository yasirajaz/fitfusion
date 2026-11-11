import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from calculations import (  # noqa: E402
    adapt_calories, calc_age, calc_targets, weekly_rate,
)


def test_age():
    assert calc_age(date(2000, 6, 15), date(2026, 6, 14)) == 25
    assert calc_age(date(2000, 6, 15), date(2026, 6, 15)) == 26


def test_basic_targets():
    r = calc_targets(70, 170, 20, "male", "moderate", "lose")
    assert r["bmr"] == 1668 and r["tdee"] == 2585   # 1667.5 and 2584.6 before rounding
    assert r["calories"] == 2085


def test_carbs_never_negative_for_heavy_user():
    r = calc_targets(200, 160, 30, "female", "sedentary", "lose")
    assert r["carbs_g"] > 0 and r["protein_g"] > 0


def test_calorie_floor():
    r = calc_targets(45, 150, 60, "female", "sedentary", "lose")
    assert r["calories"] >= 1200


def test_adjustment_applied():
    base = calc_targets(70, 170, 20, "male", "moderate", "lose")
    adj = calc_targets(70, 170, 20, "male", "moderate", "lose", adjustment=-150)
    assert adj["calories"] == base["calories"] - 150


def test_validation():
    with pytest.raises(ValueError):
        calc_targets(-5, 170, 20, "male", "moderate", "lose")
    with pytest.raises(ValueError):
        calc_targets(70, 170, 20, "male", "couch", "lose")


def _pts(start_kg, per_week, days, step=2):
    d0 = date(2026, 1, 1)
    return [(d0 + timedelta(days=i), start_kg + per_week * i / 7) for i in range(0, days + 1, step)]


def test_weekly_rate():
    assert weekly_rate(_pts(80, -0.5, 14)) == pytest.approx(-0.5)
    assert weekly_rate(_pts(80, -0.5, 7)) is None          # spans too few days
    assert weekly_rate([(date(2026, 1, 1), 80)]) is None   # too few entries


def test_adapt_lose_not_losing_cuts_calories():
    assert adapt_calories(2000, "lose", 0.0, floor=1500) == 1850


def test_adapt_respects_floor():
    assert adapt_calories(1550, "lose", 0.0, floor=1500) == 1500


def test_adapt_on_track_unchanged():
    assert adapt_calories(2000, "lose", -0.5, floor=1500) == 2000
    assert adapt_calories(2500, "gain", 0.3, floor=1500) == 2500


def test_adapt_too_fast_loss_adds_calories():
    assert adapt_calories(2000, "lose", -1.5, floor=1500) == 2150


def test_adapt_capped_from_base():
    # 2150 + 150 = 2300, but the cap is formula target (1700) + 500 = 2200
    assert adapt_calories(2150, "gain", 0.0, floor=1500, base_calories=1700) == 2200


def test_water_goal():
    from calculations import calc_water_ml
    assert calc_water_ml(70) == 2450
    assert calc_water_ml(30) == 1500     # lower bound
    assert calc_water_ml(200) == 4500    # upper bound
