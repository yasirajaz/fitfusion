"""Data layer: every SQL statement the app needs lives here."""
import json
import os
from datetime import date, datetime

from calculations import calc_age
from db import IntegrityError, execute, query, transaction

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None


def today():
    """Today's date in the app's timezone (FITFUSION_TZ, default Asia/Kolkata),
    not whatever timezone the server happens to use."""
    name = os.environ.get("FITFUSION_TZ", "Asia/Kolkata")
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(name)).date()
        except ZoneInfoNotFoundError:
            pass
    return date.today()


# ---------- users ----------
def _with_age(u):
    u["age"] = calc_age(u["birth_date"], today())
    return u


def list_users():
    rows = query("SELECT * FROM users ORDER BY name")
    return [_with_age(r) for r in rows]


def create_user(name, birth_date, gender, height_cm, goal, activity, level, weight_kg, on_date):
    """Create the user and their first weight entry in ONE transaction."""
    try:
        with transaction() as cur:
            cur.execute(
                "INSERT INTO users (name, birth_date, gender, height_cm, goal, activity, level) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (name, birth_date, gender, height_cm, goal, activity, level),
            )
            uid = cur.lastrowid
            cur.execute(
                "INSERT INTO weight_log (user_id, log_date, weight_kg) VALUES (%s,%s,%s)",
                (uid, on_date, weight_kg),
            )
            return uid
    except IntegrityError:
        raise ValueError("That name already exists.")


def update_profile(uid, birth_date, gender, height_cm, goal, activity, level, reset_adjustment):
    execute(
        "UPDATE users SET birth_date=%s, gender=%s, height_cm=%s, goal=%s, "
        "activity=%s, level=%s WHERE id=%s",
        (birth_date, gender, height_cm, goal, activity, level, uid),
    )
    if reset_adjustment:  # a new goal makes the old adaptive tweak meaningless
        execute(
            "UPDATE users SET calorie_adjustment=0, last_adjust_date=NULL WHERE id=%s",
            (uid,),
        )


def set_adjustment(uid, adjustment, on_date):
    execute(
        "UPDATE users SET calorie_adjustment=%s, last_adjust_date=%s WHERE id=%s",
        (int(adjustment), on_date, uid),
    )


# ---------- weight ----------
def latest_weight(uid):
    rows = query(
        "SELECT weight_kg FROM weight_log WHERE user_id=%s ORDER BY log_date DESC LIMIT 1",
        (uid,),
    )
    return rows[0]["weight_kg"] if rows else None


def weight_history(uid):
    return query(
        "SELECT log_date, weight_kg FROM weight_log WHERE user_id=%s ORDER BY log_date",
        (uid,),
    )


def save_weight(uid, log_date, weight_kg):
    """One weight per day: saving again for the same day replaces it."""
    execute(
        "INSERT INTO weight_log (user_id, log_date, weight_kg) VALUES (%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE weight_kg=VALUES(weight_kg)",
        (uid, log_date, weight_kg),
    )


def delete_weight(uid, log_date):
    execute("DELETE FROM weight_log WHERE user_id=%s AND log_date=%s", (uid, log_date))


# ---------- food ----------
def list_foods():
    return query("SELECT * FROM food ORDER BY name")


def add_food(name, kcal, protein, carbs, fat):
    try:
        return execute(
            "INSERT INTO food (name, kcal, protein, carbs, fat) VALUES (%s,%s,%s,%s,%s)",
            (name, kcal, protein, carbs, fat),
        )
    except IntegrityError:
        raise ValueError("A food with that name already exists.")


def add_food_log(uid, log_date, food_id, grams):
    execute(
        "INSERT INTO food_log (user_id, log_date, food_id, grams) VALUES (%s,%s,%s,%s)",
        (uid, log_date, food_id, grams),
    )


def food_log_entries(uid, log_date):
    """Entries for one day with nutrients scaled by grams."""
    return query(
        "SELECT fl.id, f.name, fl.grams, "
        "f.kcal*fl.grams/100 AS kcal, f.protein*fl.grams/100 AS protein, "
        "f.carbs*fl.grams/100 AS carbs, f.fat*fl.grams/100 AS fat "
        "FROM food_log fl JOIN food f ON f.id = fl.food_id "
        "WHERE fl.user_id=%s AND fl.log_date=%s ORDER BY fl.id",
        (uid, log_date),
    )


def delete_food_entry(uid, entry_id):
    execute("DELETE FROM food_log WHERE id=%s AND user_id=%s", (entry_id, uid))


def clear_food_log(uid, log_date):
    execute("DELETE FROM food_log WHERE user_id=%s AND log_date=%s", (uid, log_date))


def daily_calories(uid):
    return query(
        "SELECT fl.log_date, SUM(f.kcal*fl.grams/100) AS kcal "
        "FROM food_log fl JOIN food f ON f.id = fl.food_id "
        "WHERE fl.user_id=%s GROUP BY fl.log_date ORDER BY fl.log_date",
        (uid,),
    )


# ---------- workout plan ----------
def get_plan(uid, level, goal):
    """The saved plan, or None if there isn't one for the user's current level and goal."""
    rows = query("SELECT level, goal, plan FROM workout_plan WHERE user_id=%s", (uid,))
    if not rows or rows[0]["level"] != level or rows[0]["goal"] != goal:
        return None
    data = rows[0]["plan"]
    try:
        if isinstance(data, (bytes, bytearray)):
            data = data.decode()
        return json.loads(data) if isinstance(data, str) else data
    except (ValueError, TypeError):
        return None


def save_plan(uid, level, goal, plan):
    execute(
        "INSERT INTO workout_plan (user_id, level, goal, plan) VALUES (%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE level=VALUES(level), goal=VALUES(goal), plan=VALUES(plan)",
        (uid, level, goal, json.dumps(plan)),
    )


# ---------- exercise library ----------
def list_exercises():
    return query(
        "SELECT id, name, muscle_group, level FROM exercise ORDER BY muscle_group, name"
    )


def add_exercise(name, muscle_group, level):
    try:
        return execute(
            "INSERT INTO exercise (name, muscle_group, level) VALUES (%s,%s,%s)",
            (name, muscle_group, level),
        )
    except IntegrityError:
        raise ValueError("An exercise with that name already exists.")


# ---------- water ----------
def water_for_day(uid, log_date):
    rows = query(
        "SELECT ml FROM water_log WHERE user_id=%s AND log_date=%s", (uid, log_date)
    )
    return int(rows[0]["ml"]) if rows else 0


def add_water(uid, log_date, ml):
    """Add (or, if negative, remove) water for a day. Never goes below 0."""
    execute(
        "INSERT INTO water_log (user_id, log_date, ml) VALUES (%s,%s,GREATEST(%s,0)) "
        "ON DUPLICATE KEY UPDATE ml=GREATEST(ml+%s,0)",
        (uid, log_date, ml, ml),
    )


def reset_water(uid, log_date):
    execute("DELETE FROM water_log WHERE user_id=%s AND log_date=%s", (uid, log_date))


def water_history(uid, days=14):
    rows = query(
        "SELECT log_date, ml FROM water_log WHERE user_id=%s "
        "ORDER BY log_date DESC LIMIT %s",
        (uid, int(days)),
    )
    return list(reversed(rows))


# ---------- exercise log ----------
def add_exercise_log(uid, log_date, exercise_id, sets, reps, weight_kg, duration_min):
    execute(
        "INSERT INTO exercise_log (user_id, log_date, exercise_id, sets, reps, weight_kg, duration_min) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (uid, log_date, exercise_id, sets, reps, weight_kg, duration_min),
    )


def exercise_log_entries(uid, log_date):
    return query(
        "SELECT el.id, e.name, e.muscle_group, el.sets, el.reps, el.weight_kg, el.duration_min "
        "FROM exercise_log el JOIN exercise e ON e.id = el.exercise_id "
        "WHERE el.user_id=%s AND el.log_date=%s ORDER BY el.id",
        (uid, log_date),
    )


def delete_exercise_log(uid, entry_id):
    execute("DELETE FROM exercise_log WHERE id=%s AND user_id=%s", (entry_id, uid))


def exercise_top_weights(uid, exercise_id):
    """Heaviest weight lifted per day for one exercise (for a progress chart)."""
    return query(
        "SELECT log_date, MAX(weight_kg) AS top_weight FROM exercise_log "
        "WHERE user_id=%s AND exercise_id=%s GROUP BY log_date ORDER BY log_date",
        (uid, exercise_id),
    )


def workout_dates(uid):
    rows = query(
        "SELECT DISTINCT log_date FROM exercise_log WHERE user_id=%s ORDER BY log_date",
        (uid,),
    )
    return [r["log_date"] for r in rows]
