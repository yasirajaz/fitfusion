from datetime import date

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}

GOAL_ADJUSTMENT = {"lose": -500, "maintain": 0, "gain": 300}

# Never recommend less than this (kcal/day) regardless of goal or adaptive steps.
CALORIE_FLOOR = {"male": 1500, "female": 1200}

PROTEIN_G_PER_KG = 2.0     # applied to a healthy reference weight, see calc_targets
MAX_PROTEIN_SHARE = 0.30   # protein never exceeds 30% of calories
FAT_SHARE = 0.25           # fat is 25% of calories -> carbs are always >= 45%

# Adaptive calories
ADJUST_STEP = 150               # kcal per adjustment
MAX_ADJUSTMENT_FROM_BASE = 500  # total adaptive change is limited to +/- this
MIN_TREND_DAYS = 14             # need weigh-ins spanning at least this many days
MIN_TREND_ENTRIES = 3           # ...and at least this many weigh-ins
# (too_slow_below, too_fast_above) in kg per week
TARGET_RATE = {
    "lose": (-0.20, -1.00),     # losing less than 0.2 kg/wk is too slow, > 1 kg/wk too fast
    "gain": (0.10, 0.75),
}
MAINTAIN_TOLERANCE = 0.25       # kg per week


def calc_age(birth_date, on=None):
    on = on or date.today()
    return on.year - birth_date.year - ((on.month, on.day) < (birth_date.month, birth_date.day))


def _validate(weight_kg, height_cm, age, gender, activity, goal):
    if not 20 <= weight_kg <= 400:
        raise ValueError("weight_kg must be between 20 and 400")
    if not 100 <= height_cm <= 250:
        raise ValueError("height_cm must be between 100 and 250")
    if not 10 <= age <= 100:
        raise ValueError("age must be between 10 and 100")
    if gender not in CALORIE_FLOOR:
        raise ValueError(f"unknown gender: {gender}")
    if activity not in ACTIVITY_FACTORS:
        raise ValueError(f"unknown activity level: {activity}")
    if goal not in GOAL_ADJUSTMENT:
        raise ValueError(f"unknown goal: {goal}")


def calc_bmi(weight_kg, height_cm):
    return weight_kg / (height_cm / 100) ** 2


def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def calc_bmr(weight_kg, height_cm, age, gender):
    """Mifflin-St Jeor equation."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "male" else base - 161


def calc_tdee(bmr, activity):
    return bmr * ACTIVITY_FACTORS[activity]


def calc_targets(weight_kg, height_cm, age, gender, activity, goal, adjustment=0):
    """Returns all metrics and daily calorie/macro targets.

    adjustment: persisted adaptive calorie change (kcal) added to the formula target.
    """
    _validate(weight_kg, height_cm, age, gender, activity, goal)

    bmi = calc_bmi(weight_kg, height_cm)
    bmr = calc_bmr(weight_kg, height_cm, age, gender)
    tdee = calc_tdee(bmr, activity)
    base_calories = tdee + GOAL_ADJUSTMENT[goal]
    floor = CALORIE_FLOOR[gender]
    calories = max(base_calories + adjustment, floor)

    # Protein: 2 g/kg of a healthy reference weight (capped at BMI 25) so heavier users
    # don't get inflated targets, and never more than 30% of calories.
    healthy_weight = 25 * (height_cm / 100) ** 2
    reference = min(weight_kg, healthy_weight)
    protein_g = min(PROTEIN_G_PER_KG * reference, MAX_PROTEIN_SHARE * calories / 4)
    fat_g = FAT_SHARE * calories / 9
    # With the caps above carbs are always >= 45% of calories, so never negative.
    carbs_g = (calories - protein_g * 4 - fat_g * 9) / 4

    return {
        "bmi": round(bmi, 1),
        "bmi_category": bmi_category(bmi),
        "bmr": round(bmr),
        "tdee": round(tdee),
        "base_calories": round(base_calories),
        "adjustment": adjustment,
        "calorie_floor": floor,
        "calories": round(calories),
        "protein_g": round(protein_g),
        "fat_g": round(fat_g),
        "carbs_g": round(carbs_g),
    }


def weekly_rate(points):
    """Weight trend in kg/week from [(date, kg), ...] using a least-squares line.

    Returns None when there isn't enough data (fewer than MIN_TREND_ENTRIES weigh-ins,
    or they span less than MIN_TREND_DAYS days). A fitted line is much less noisy than
    comparing two single-day weights.
    """
    pts = sorted(points)
    if len(pts) < MIN_TREND_ENTRIES:
        return None
    first = pts[0][0]
    xs = [(d - first).days for d, _ in pts]
    ys = [float(w) for _, w in pts]
    if xs[-1] < MIN_TREND_DAYS:
        return None
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return slope * 7


def adapt_calories(current_calories, goal, rate_kg_per_week, floor=0, base_calories=None):
    """Adaptive step: nudge the calorie target if the weight trend is off-goal.

    Never goes below `floor`, and (if base_calories is given) never drifts more than
    MAX_ADJUSTMENT_FROM_BASE away from the formula target.
    """
    if rate_kg_per_week is None:
        return round(current_calories)

    step = 0
    if goal == "maintain":
        if rate_kg_per_week > MAINTAIN_TOLERANCE:
            step = -ADJUST_STEP
        elif rate_kg_per_week < -MAINTAIN_TOLERANCE:
            step = ADJUST_STEP
    else:
        too_slow, too_fast = TARGET_RATE[goal]
        if goal == "lose":
            if rate_kg_per_week > too_slow:       # not losing fast enough
                step = -ADJUST_STEP
            elif rate_kg_per_week < too_fast:     # losing too fast
                step = ADJUST_STEP
        else:  # gain
            if rate_kg_per_week < too_slow:       # not gaining
                step = ADJUST_STEP
            elif rate_kg_per_week > too_fast:     # gaining too fast
                step = -ADJUST_STEP

    new = current_calories + step
    low, high = floor, None
    if base_calories is not None:
        low = max(low, base_calories - MAX_ADJUSTMENT_FROM_BASE)
        high = base_calories + MAX_ADJUSTMENT_FROM_BASE
    new = max(new, low)
    if high is not None:
        new = min(new, high)
    return round(new)


def calc_water_ml(weight_kg):
    """Daily water goal: about 35 ml per kg, rounded to 50 ml, kept within 1.5-4.5 L."""
    ml = round(weight_kg * 35 / 50) * 50
    return int(min(max(ml, 1500), 4500))


if __name__ == "__main__":
    # Quick test
    print(calc_targets(70, 170, 20, "male", "moderate", "lose"))
