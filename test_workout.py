"""Workout generator tests. Uses a fake `db` module and reads the exercise seed straight
from schema.sql, so no MySQL server is needed (and the SQL list itself gets checked)."""
import os
import re
import sys
import types

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

_fake_db = types.ModuleType("db")
_fake_db.query = lambda sql, params=None: []
sys.modules["db"] = _fake_db
import workout  # noqa: E402


def _seed_exercises():
    sql = open(os.path.join(ROOT, "schema.sql"), encoding="utf-8").read()
    block = sql[sql.index("INSERT IGNORE INTO exercise"):]
    rows = re.findall(r"\('((?:[^']|'')+)', '(\w+)', '(\w+)'\)", block)
    return [{"name": n.replace("''", "'"), "muscle_group": g, "level": l} for n, g, l in rows]


EXERCISES = _seed_exercises()


def _fake_query(sql, params=None):
    allowed = set(params)
    return [e for e in EXERCISES if e["level"] in allowed and e["muscle_group"] != "cardio"]


def _plan(level, goal="maintain"):
    workout.query = _fake_query
    return workout.generate_plan(level, goal)


def test_seed_has_all_requested_exercises():
    strength = [e for e in EXERCISES if e["muscle_group"] != "cardio"]
    assert len(strength) == 79
    assert len({e["name"] for e in EXERCISES}) == len(EXERCISES)   # unique names
    assert "Captain's Chair Leg Raises" in {e["name"] for e in EXERCISES}


def test_all_levels_train_six_days():
    for level in ("Beginner", "Intermediate", "Advanced"):
        plan = _plan(level)
        assert [d for d, v in plan.items() if v["items"]] == list(workout.WEEK[:6])
        assert plan["Sunday"]["items"] == []
        focuses = [plan[d]["focus"] for d in workout.WEEK[:6]]
        assert focuses == ["Back + Biceps", "Chest + Triceps", "Legs + Shoulders + Abs"] * 2


def test_day_muscles_match_split():
    plan = _plan("Beginner")
    assert {i["Muscle"] for i in plan["Monday"]["items"]} == {"Back", "Biceps"}
    assert {i["Muscle"] for i in plan["Tuesday"]["items"]} == {"Chest", "Triceps"}
    assert {i["Muscle"] for i in plan["Wednesday"]["items"]} == {"Legs", "Shoulders", "Abs"}


def test_no_duplicate_exercise_in_a_day_and_level_respected():
    levels = {e["name"]: e["level"] for e in EXERCISES}
    for _ in range(30):
        plan = _plan("Beginner")
        for v in plan.values():
            names = [i["Exercise"] for i in v["items"]]
            assert len(names) == len(set(names))
            assert all(levels[n] == "Beginner" for n in names)


def test_intermediate_between_beginner_and_advanced_volume():
    counts = {lvl: len(_plan(lvl)["Monday"]["items"]) for lvl in ("Beginner", "Intermediate", "Advanced")}
    assert counts["Beginner"] <= counts["Intermediate"] <= counts["Advanced"]
