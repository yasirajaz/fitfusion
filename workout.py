import random
from db import query

LEVEL_ORDER = ["Beginner", "Intermediate", "Advanced"]
MUSCLE_GROUPS = ["back", "biceps", "chest", "triceps", "legs", "shoulders", "abs", "cardio"]
WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Which weekdays (0 = Monday) each level trains on; all other days are rest days.
TRAINING_DAYS = {
    "Beginner": [0, 1, 2, 3, 4, 5],       # 6 days, Sunday off
    "Intermediate": [0, 1, 2, 3, 4, 5],   # 6 days, Sunday off
    "Advanced": [0, 1, 2, 3, 4, 5],       # 6 days, Sunday off
}

# Each session is (label, [muscle groups]); a group listed twice = two exercises for it.
# All levels: Back+Biceps / Chest+Triceps / Legs+Shoulders+Abs, done twice a week.
SPLITS = {
    "Beginner": [
        ("Back + Biceps", ["back"] * 3 + ["biceps"] * 2),
        ("Chest + Triceps", ["chest"] * 3 + ["triceps"] * 2),
        ("Legs + Shoulders + Abs", ["legs"] * 3 + ["shoulders"] * 2 + ["abs"] * 2),
    ] * 2,
    "Intermediate": [
        ("Back + Biceps", ["back"] * 4 + ["biceps"] * 2),
        ("Chest + Triceps", ["chest"] * 4 + ["triceps"] * 2),
        ("Legs + Shoulders + Abs", ["legs"] * 3 + ["shoulders"] * 3 + ["abs"] * 2),
    ] * 2,
    "Advanced": [
        ("Back + Biceps", ["back"] * 4 + ["biceps"] * 3),
        ("Chest + Triceps", ["chest"] * 4 + ["triceps"] * 3),
        ("Legs + Shoulders + Abs", ["legs"] * 4 + ["shoulders"] * 3 + ["abs"] * 3),
    ] * 2,
}

# Sets x reps depend on level AND goal.
SETS_REPS = {
    "Beginner":     {"lose": "3 x 12-15", "maintain": "3 x 10-12", "gain": "3 x 8-12"},
    "Intermediate": {"lose": "4 x 10-12", "maintain": "4 x 8-10",  "gain": "4 x 6-10"},
    "Advanced":     {"lose": "4 x 8-10",  "maintain": "4 x 6-8",   "gain": "5 x 5-8"},
}

TRAINING_NOTE = {
    "lose": "Finish with 15-20 min of cardio.",
    "maintain": "Optional: 10 min of light cardio.",
    "gain": "Keep cardio light and eat enough to recover.",
}
REST_NOTE = {
    "lose": "Rest day: a 30-45 min walk is ideal.",
    "maintain": "Rest day: stretch or take a short walk.",
    "gain": "Rest day: sleep well and eat your target calories.",
}

# Exercises at the user's own level are most likely, one level easier is next, rest least.
_LEVEL_WEIGHT = {0: 4, 1: 3}


def _pick(options, level, used_week):
    """Prefer exercises not yet used this week, weighted toward the user's own level."""
    fresh = [e for e in options if e["name"] not in used_week]
    pool = fresh or options
    me = LEVEL_ORDER.index(level)
    weights = [_LEVEL_WEIGHT.get(me - LEVEL_ORDER.index(e["level"]), 1) for e in pool]
    return random.choices(pool, weights=weights, k=1)[0]


def generate_plan(level, goal="maintain"):
    """Return an ordered {weekday: {"focus": str, "note": str, "items": [rows]}}.

    Uses exercises at or below the user's level, favours the user's own level, and
    avoids repeating exercises across the week when there are enough to choose from.
    """
    allowed = tuple(LEVEL_ORDER[: LEVEL_ORDER.index(level) + 1])
    marks = ",".join(["%s"] * len(allowed))
    rows = query(
        f"SELECT name, muscle_group, level FROM exercise "
        f"WHERE level IN ({marks}) AND muscle_group <> 'cardio'",
        allowed,
    )
    by_group = {}
    for r in rows:
        by_group.setdefault(r["muscle_group"], []).append(r)

    sessions = dict(zip(TRAINING_DAYS[level], SPLITS[level]))
    sets_reps = SETS_REPS[level][goal]
    used_week = set()
    plan = {}

    for i, weekday in enumerate(WEEK):
        if i not in sessions:
            plan[weekday] = {"focus": "Rest", "note": REST_NOTE[goal], "items": []}
            continue
        focus, groups = sessions[i]
        used_today = set()
        items = []
        for g in groups:
            options = [e for e in by_group.get(g, []) if e["name"] not in used_today]
            if not options:
                continue
            ex = _pick(options, level, used_week)
            used_today.add(ex["name"])
            used_week.add(ex["name"])
            items.append(
                {"Muscle": g.title(), "Exercise": ex["name"], "Sets x Reps": sets_reps}
            )
        plan[weekday] = {"focus": focus, "note": TRAINING_NOTE[goal], "items": items}
    return plan
