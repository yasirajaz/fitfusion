from datetime import timedelta

import pandas as pd
import streamlit as st

import repository as repo
import style
from calculations import adapt_calories, calc_age, calc_targets, calc_water_ml, weekly_rate
from workout import MUSCLE_GROUPS, SETS_REPS, WEEK, generate_plan

st.set_page_config(page_title="FitFusion", page_icon="💪", layout="wide")
if not hasattr(style, "grid"):
    st.error("style.py is outdated. Replace it with the new style.py that came with this app.py.")
    st.stop()
style.inject()
style.sidebar_brand()

NEW = "-- New user --"
GENDERS = ["male", "female"]
GOALS = ["lose", "maintain", "gain"]
ACTIVITIES = ["sedentary", "light", "moderate", "active"]
LEVELS = ["Beginner", "Intermediate", "Advanced"]
PAGES = ["Profile", "Workout", "Food Log", "Water", "Exercise Log", "Progress"]

today = repo.today()


def idx(options, value):
    return options.index(value) if value in options else 0


def clean_name(name):
    """Trim and collapse repeated spaces."""
    return " ".join(name.split())


def years_ago(n):
    try:
        return today.replace(year=today.year - n)
    except ValueError:  # 29 Feb
        return today.replace(year=today.year - n, day=28)


def pretty_sr(text):
    return text.replace(" x ", " × ")


def need_user():
    st.info("Create or select a user first.")


def page_header(title, date_key=None):
    """Page title. With date_key, a date picker sits on the right and its value is returned."""
    if date_key is None:
        st.title(title)
        return None
    left, right = st.columns([3, 1], vertical_alignment="center")
    left.title(title)
    return right.date_input(
        "Date", today, max_value=today, key=date_key, label_visibility="collapsed"
    )


@st.cache_data(ttl=300)
def load_foods():
    return repo.list_foods()


@st.cache_data(ttl=300)
def load_exercises():
    return repo.list_exercises()


# ---------- Sidebar: choose user, then page ----------
# After creating a profile we select it on the next run (a widget's value can't be
# changed after it has been drawn, so we stash the name and apply it before drawing).
if "_select_after" in st.session_state:
    st.session_state["user_choice"] = st.session_state.pop("_select_after")

try:
    users = repo.list_users()
except Exception as e:  # bad credentials, DB down, schema not loaded...
    st.error(f"Could not connect to the database: {e}")
    st.stop()

by_name = {u_["name"]: u_ for u_ in users}
choice = st.sidebar.selectbox("Select user", [NEW] + list(by_name), key="user_choice")
u = by_name.get(choice)  # None when creating a new user
page = st.sidebar.radio("Navigation", PAGES, key="page", label_visibility="collapsed")


def get_targets(user):
    """Daily targets for a user based on their latest logged weight."""
    weight = repo.latest_weight(user["id"])
    if weight is None:
        return None
    return calc_targets(
        weight, user["height_cm"], user["age"], user["gender"],
        user["activity"], user["goal"], user["calorie_adjustment"],
    )


# ============================ Profile ============================
def page_profile():
    if u is None:
        st.title("Create your profile")
        with st.form("new_user"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Name")
            dob = c2.date_input(
                "Date of birth", value=years_ago(20),
                min_value=years_ago(100), max_value=today,
            )
            gender = c1.selectbox("Gender", GENDERS)
            height = c2.number_input("Height (cm)", 100.0, 250.0, 170.0, step=1.0, format="%g")
            weight = c1.number_input("Weight (kg)", 30.0, 250.0, 70.0, step=0.5, format="%g")
            goal = c2.selectbox("Goal", GOALS)
            activity = c1.selectbox("Activity level", ACTIVITIES)
            level = c2.selectbox("Fitness level", LEVELS)
            submitted = st.form_submit_button("Save profile")

        if submitted:
            name = clean_name(name)
            if not name:
                st.error("Please enter a name.")
            elif name.lower() in {n.lower() for n in by_name}:
                st.error("That name already exists.")
            elif not 10 <= calc_age(dob, today) <= 100:
                st.error("Age must be between 10 and 100.")
            else:
                try:
                    repo.create_user(
                        name, dob, gender, height, goal, activity, level, weight, today
                    )
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.session_state["_select_after"] = name
                    st.rerun()
        return

    todays_plan = repo.get_plan(u["id"], u["level"], u["goal"])
    if not todays_plan:
        pill = "Open the Workout page to get your plan"
    else:
        focus = todays_plan.get(WEEK[today.weekday()], {}).get("focus", "")
        pill = "Today: Rest day" if focus in ("", "Rest") else f"Today: {focus}"
    style.hero(u["name"], f"Age {u['age']} · {u['level']} · goal: {u['goal']}", pill)

    r = get_targets(u)
    if r is None:
        st.warning("No weight logged yet. Add one on the Progress page.")
    else:
        style.grid(
            style.metric_html("BMI", r["bmi"], r["bmi_category"]),
            style.metric_html("BMR", r["bmr"], "kcal"),
            style.metric_html("TDEE", r["tdee"], "kcal"),
            cols=3,
        )
        total = max(r["calories"], 1)
        style.macro_card(
            "Daily calories", r["calories"], "kcal",
            [
                ("Protein", r["protein_g"] * 4 / total, f"{r['protein_g']} g"),
                ("Carbs", r["carbs_g"] * 4 / total, f"{r['carbs_g']} g"),
                ("Fat", r["fat_g"] * 9 / total, f"{r['fat_g']} g"),
            ],
        )
        if r["adjustment"]:
            st.caption(
                f"Includes an adaptive adjustment of {r['adjustment']:+d} kcal "
                f"(formula target: {r['base_calories']} kcal)."
            )
        if r["calories"] == r["calorie_floor"] and r["base_calories"] + r["adjustment"] < r["calorie_floor"]:
            st.caption(f"Raised to the minimum safe level of {r['calorie_floor']} kcal.")

    with st.expander("Edit profile"):
        with st.form("edit_user"):
            c1, c2 = st.columns(2)
            e_dob = c1.date_input(
                "Date of birth", value=u["birth_date"],
                min_value=years_ago(100), max_value=today,
            )
            e_gender = c2.selectbox("Gender", GENDERS, index=idx(GENDERS, u["gender"]))
            e_height = c1.number_input(
                "Height (cm)", 100.0, 250.0,
                float(min(max(u["height_cm"], 100.0), 250.0)), step=1.0, format="%g",
            )
            e_goal = c2.selectbox("Goal", GOALS, index=idx(GOALS, u["goal"]))
            e_activity = c1.selectbox(
                "Activity level", ACTIVITIES, index=idx(ACTIVITIES, u["activity"])
            )
            e_level = c2.selectbox("Fitness level", LEVELS, index=idx(LEVELS, u["level"]))
            saved = st.form_submit_button("Update profile")
        if saved:
            if not 10 <= calc_age(e_dob, today) <= 100:
                st.error("Age must be between 10 and 100.")
            else:
                repo.update_profile(
                    u["id"], e_dob, e_gender, e_height, e_goal, e_activity, e_level,
                    reset_adjustment=(e_goal != u["goal"]),
                )
                st.rerun()


# ============================ Workout ============================
def page_workout():
    if u is None:
        st.title("Workout")
        need_user()
        return

    exercises = load_exercises()
    ex_by_group = {}
    for e in exercises:
        ex_by_group.setdefault(e["muscle_group"], []).append(e["name"])
    group_options = [g for g in MUSCLE_GROUPS if g in ex_by_group]
    default_sr = SETS_REPS[u["level"]][u["goal"]]

    plan = repo.get_plan(u["id"], u["level"], u["goal"])
    head, action = st.columns([3, 1], vertical_alignment="center")
    head.title(f"{u['level']} weekly plan")
    regenerate = action.button(
        "Generate new plan", key="gen_plan",
        help="Builds a fresh plan and replaces any changes you made",
    )
    if plan is None or regenerate:
        plan = generate_plan(u["level"], u["goal"])
        repo.save_plan(u["id"], u["level"], u["goal"], plan)

    tips = [i["note"] for i in plan.values() if i["items"]]
    if tips:
        st.caption(tips[0])

    cards = []
    for day, info in plan.items():
        if not info["items"]:
            cards.append(style.rows_html(day, chip="Rest", note=info["note"]))
        else:
            rows = [(it["Exercise"], pretty_sr(it["Sets x Reps"])) for it in info["items"]]
            cards.append(style.rows_html(day, rows, chip=info["focus"]))

    # every day in the grid except the last, which sits next to the "+ Add exercise" tile
    if len(cards) > 1:
        style.grid(*cards[:-1])
    last, tile = st.columns(2)
    with last:
        st.markdown(cards[-1], unsafe_allow_html=True)
    with tile:
        with st.container(key="tile_add"):
            if st.button("+ Add exercise", key="soft_add_exercise"):
                st.session_state["add_open"] = not st.session_state.get("add_open", False)

    if st.session_state.get("add_open"):
        with st.container(key="card_add_exercise"):
            st.subheader("Add an exercise")
            a1, a2, a3 = st.columns(3)
            day_pick = a1.selectbox("Day", WEEK, key="ap_day")
            grp = a2.selectbox("Muscle group", group_options, key="ap_grp")
            ex_name = a3.selectbox("Exercise", ex_by_group.get(grp, []), key="ap_ex")
            sr_text = st.text_input(
                "Sets x Reps (optional)", key="ap_sr",
                placeholder="20-30 min" if grp == "cardio" else default_sr,
            )
            b1, b2, _ = st.columns([1, 1, 4])
            if b1.button("Add to day", key="ap_add") and ex_name:
                info = plan[day_pick]
                if any(it["Exercise"] == ex_name for it in info["items"]):
                    st.error("That exercise is already on this day.")
                else:
                    info["items"].append({
                        "Muscle": grp.title(),
                        "Exercise": ex_name,
                        "Sets x Reps": sr_text.strip() or ("20-30 min" if grp == "cardio" else default_sr),
                    })
                    if info["focus"] == "Rest":
                        info["focus"] = "Custom"
                    repo.save_plan(u["id"], u["level"], u["goal"], plan)
                    st.rerun()
            if b2.button("Close", key="soft_ap_close"):
                st.session_state["add_open"] = False
                st.rerun()

    with st.expander("Remove an exercise from a day"):
        days_with_items = [d for d, i in plan.items() if i["items"]]
        if not days_with_items:
            st.write("No exercises to remove.")
        else:
            r1, r2, r3 = st.columns([2, 3, 1], vertical_alignment="bottom")
            rm_day = r1.selectbox("Day", days_with_items, key="rm_day")
            rm_ex = r2.selectbox(
                "Exercise", [it["Exercise"] for it in plan[rm_day]["items"]], key="rm_ex"
            )
            if r3.button("Remove", key="soft_rm_exercise"):
                plan[rm_day]["items"] = [
                    it for it in plan[rm_day]["items"] if it["Exercise"] != rm_ex
                ]
                repo.save_plan(u["id"], u["level"], u["goal"], plan)
                st.rerun()

    with st.expander("Create a new exercise"):
        with st.form("new_exercise", clear_on_submit=True):
            n_name = st.text_input("Exercise name")
            n1, n2 = st.columns(2)
            n_group = n1.selectbox("Muscle group", MUSCLE_GROUPS)
            n_level = n2.selectbox("Level", LEVELS)
            n_save = st.form_submit_button("Save exercise")
        if n_save:
            n_name = clean_name(n_name)
            if not n_name:
                st.error("Please enter an exercise name.")
            elif n_name.lower() in {e["name"].lower() for e in exercises}:
                st.error("An exercise with that name already exists.")
            else:
                try:
                    repo.add_exercise(n_name, n_group, n_level)
                except ValueError as err:
                    st.error(str(err))
                else:
                    load_exercises.clear()
                    st.rerun()


# ============================ Food Log ============================
def page_food():
    if u is None:
        st.title("Food Log")
        need_user()
        return

    foods = load_foods()
    food_by_name = {f["name"]: f for f in foods}
    log_day = page_header("Food Log", "food_date")

    if not food_by_name:
        st.info("No foods in the database yet. Add a custom food below.")
    else:
        with st.container(key="card_add_food"):
            c1, c2, c3 = st.columns([2, 2, 1.4], vertical_alignment="bottom")
            pick = c1.selectbox("Food", list(food_by_name))
            grams = c2.number_input("Grams", 1.0, 2000.0, 100.0, step=5.0, format="%g")
            if c3.button("Add to log", key="add_food_log"):
                repo.add_food_log(u["id"], log_day, food_by_name[pick]["id"], grams)
                st.rerun()

    with st.expander("Add a custom food (values per 100 g)"):
        with st.form("new_food", clear_on_submit=True):
            f_name = st.text_input("Food name")
            k1, k2, k3, k4 = st.columns(4)
            f_kcal = k1.number_input("kcal", 0.0, 900.0, 0.0)
            f_prot = k2.number_input("Protein (g)", 0.0, 100.0, 0.0)
            f_carb = k3.number_input("Carbs (g)", 0.0, 100.0, 0.0)
            f_fat = k4.number_input("Fat (g)", 0.0, 100.0, 0.0)
            add_food = st.form_submit_button("Save food")
        if add_food:
            f_name = clean_name(f_name)
            if not f_name:
                st.error("Please enter a food name.")
            elif f_prot + f_carb + f_fat > 100:
                st.error("Protein + carbs + fat can't exceed 100 g per 100 g.")
            elif f_name.lower() in {n.lower() for n in food_by_name}:
                st.error("A food with that name already exists.")
            else:
                try:
                    repo.add_food(f_name, f_kcal, f_prot, f_carb, f_fat)
                except ValueError as e:
                    st.error(str(e))
                else:
                    load_foods.clear()
                    st.rerun()

    rows = repo.food_log_entries(u["id"], log_day)
    heading = "Today" if log_day == today else f"Log for {log_day:%d %b %Y}"
    if not rows:
        style.rows_card(heading, note="Nothing logged yet.")
        return

    style.rows_card(
        heading, [(f"{r['name']} · {r['grams']:g} g", f"{r['kcal']:.0f} kcal") for r in rows]
    )

    p = sum(r["protein"] for r in rows)
    c = sum(r["carbs"] for r in rows)
    f = sum(r["fat"] for r in rows)
    eaten = sum(r["kcal"] for r in rows)
    t = get_targets(u)

    if t:
        style.stat_card(
            "Calories", f"{eaten:.0f}", f"/ {t['calories']} kcal",
            progress=eaten / t["calories"] if t["calories"] > 0 else 0,
        )
        targets = [("Protein", p, t["protein_g"]), ("Carbs", c, t["carbs_g"]), ("Fat", f, t["fat_g"])]
        macro_bars = style.macro_html(
            "Progress vs target", None, "",
            [(n, got / tgt if tgt > 0 else 0, f"{got:.0f} / {tgt} g") for n, got, tgt in targets],
        )
    else:
        style.stat_card("Calories", f"{eaten:.0f}", "kcal")
        macro_bars = None

    split = style.split_html(
        "Macro split (by calories)",
        [("Protein", f"{p:.0f} g", p * 4), ("Carbs", f"{c:.0f} g", c * 4), ("Fat", f"{f:.0f} g", f * 9)],
    )
    style.grid(*(x for x in (macro_bars, split) if x))

    with st.expander("Edit this day's log"):
        for r in rows:
            ec = st.columns([6, 1], vertical_alignment="center")
            ec[0].write(f"{r['name']} · {r['grams']:g} g · {r['kcal']:.0f} kcal")
            if ec[1].button("🗑", key=f"soft_del_food_{r['id']}", help="Delete this entry"):
                repo.delete_food_entry(u["id"], r["id"])
                st.rerun()
        if st.button("Clear this day's log", key="soft_clear_food"):
            repo.clear_food_log(u["id"], log_day)
            st.rerun()


# ============================ Water ============================
def page_water():
    if u is None:
        st.title("Water")
        need_user()
        return

    cur_weight = repo.latest_weight(u["id"])
    water_goal = calc_water_ml(cur_weight) if cur_weight else 2500
    water_day = page_header("Water", "water_date")
    drunk = repo.water_for_day(u["id"], water_day)

    style.stat_card(
        "Water intake", drunk, f"/ {water_goal} ml",
        progress=drunk / water_goal,
        chip="Goal reached" if drunk >= water_goal else None,
        note=None if drunk >= water_goal else f"Goal: about 35 ml per kg ({water_goal} ml).",
    )

    with st.container(key="card_water_add"):
        st.markdown('<div class="ff-label">Add water</div>', unsafe_allow_html=True)
        b = st.columns(5)
        for col, amount in zip(b[:3], (250, 500, 1000)):
            if col.button(f"+{amount} ml", key=f"water_add_{amount}"):
                repo.add_water(u["id"], water_day, amount)
                st.rerun()
        if b[3].button("-250 ml", key="soft_water_sub"):
            repo.add_water(u["id"], water_day, -250)
            st.rerun()
        if b[4].button("Reset day", key="soft_water_reset"):
            repo.reset_water(u["id"], water_day)
            st.rerun()

        cw1, cw2 = st.columns([3, 1], vertical_alignment="bottom")
        custom_ml = cw1.number_input("Custom amount (ml)", 50, 3000, 300, step=50)
        if cw2.button("Add", key="water_custom"):
            repo.add_water(u["id"], water_day, int(custom_ml))
            st.rerun()

    wh = repo.water_history(u["id"])
    if wh:
        style.bar_card(
            "Last 14 logged days (dashed = goal)",
            [w["ml"] for w in wh],
            target=water_goal,
            labels=[f"{w['log_date']:%d %b} · {int(w['ml'])} ml" for w in wh],
        )


# ============================ Exercise Log ============================
def page_exercise_log():
    if u is None:
        st.title("Exercise Log")
        need_user()
        return

    lib = load_exercises()
    lib_by_group = {}
    for e in lib:
        lib_by_group.setdefault(e["muscle_group"], []).append(e)
    log_groups = [g for g in MUSCLE_GROUPS if g in lib_by_group]

    ex_day = page_header("Exercise Log", "ex_date")

    with st.container(key="card_log_exercise"):
        st.subheader("Log an exercise")
        x1, x2 = st.columns(2)
        sel_group = x1.selectbox("Muscle group", log_groups, key="exlog_group")
        sel_ex = x2.selectbox(
            "Exercise", [e["name"] for e in lib_by_group.get(sel_group, [])], key="exlog_ex"
        )
        sel_row = next((e for e in lib_by_group.get(sel_group, []) if e["name"] == sel_ex), None)

        if sel_group == "cardio":
            mins = st.number_input("Duration (minutes)", 1, 600, 30)
            sets_in, reps_in, kg_in = 0, 0, 0.0
        else:
            y1, y2, y3 = st.columns(3)
            sets_in = y1.number_input("Sets", 1, 20, 3)
            reps_in = y2.number_input("Reps per set", 1, 100, 10)
            kg_in = y3.number_input(
                "Weight (kg, 0 = bodyweight)", 0.0, 500.0, 0.0, step=2.5, format="%g"
            )
            mins = 0
        log_clicked = st.button("Log exercise", key="log_exercise")

    if log_clicked and sel_row:
        repo.add_exercise_log(
            u["id"], ex_day, sel_row["id"], int(sets_in), int(reps_in), float(kg_in), int(mins)
        )
        st.rerun()

    entries = repo.exercise_log_entries(u["id"], ex_day)
    heading = "Today" if ex_day == today else f"Log for {ex_day:%d %b %Y}"
    if not entries:
        style.rows_card(heading, note="Nothing logged yet.")
    else:
        rows = []
        for en in entries:
            if en["muscle_group"] == "cardio":
                detail = f"{en['duration_min']} min"
            else:
                load = f" @ {en['weight_kg']:g} kg" if en["weight_kg"] else " (bodyweight)"
                detail = f"{en['sets']} × {en['reps']}{load}"
            rows.append((f"{en['name']} ({en['muscle_group']})", detail))
        style.rows_card(heading, rows)

        with st.expander("Edit this day's log"):
            for en in entries:
                ec = st.columns([6, 1], vertical_alignment="center")
                ec[0].write(f"{en['name']} ({en['muscle_group']})")
                if ec[1].button("🗑", key=f"soft_del_ex_{en['id']}", help="Delete this entry"):
                    repo.delete_exercise_log(u["id"], en["id"])
                    st.rerun()

    cards = []
    if sel_row and sel_group != "cardio":
        tops = repo.exercise_top_weights(u["id"], sel_row["id"])
        if tops and any(t_["top_weight"] > 0 for t_ in tops):
            cards.append(style.line_html(
                f"{sel_ex}: heaviest weight per day (kg)", [t_["top_weight"] for t_ in tops]
            ))

    dates = repo.workout_dates(u["id"])
    if dates:
        per_week = pd.Series(1, index=pd.to_datetime(dates)).resample("W").sum().tail(12)
        cards.append(style.bar_html(
            "Workout days per week",
            list(per_week.values),
            labels=[f"Week ending {d:%d %b}: {n} day(s)" for d, n in per_week.items()],
        ))
    if cards:
        style.grid(*cards, cols=len(cards))


# ============================ Progress ============================
def page_progress():
    if u is None:
        st.title("Progress")
        need_user()
        return

    wl = repo.weight_history(u["id"])
    latest_w = wl[-1]["weight_kg"] if wl else 70.0
    t = get_targets(u)
    st.title("Progress")

    # ----- Adaptive calorie check (computed first, drawn next to the weight chart) -----
    since = u["last_adjust_date"]
    rate, suggest = None, False
    if not t or not wl:
        adaptive = style.stat_html(
            "Adaptive calorie check", "—", "kg/week",
            note="Log your weight to get an adaptive suggestion.",
        )
    else:
        latest_date = wl[-1]["log_date"]
        cutoff = latest_date - timedelta(days=28)
        if since and since > cutoff:
            cutoff = since  # only judge weigh-ins after the last change
        points = [(r["log_date"], r["weight_kg"]) for r in wl if r["log_date"] >= cutoff]
        rate = weekly_rate(points)

        if rate is None:
            msg = "Log at least 3 weigh-ins spanning 14+ days to get a suggestion"
            if since:
                msg += f" (counting from your last calorie change on {since:%d %b %Y})"
            adaptive = style.stat_html("Adaptive calorie check", "—", "kg/week", note=msg + ".")
        else:
            new_cal = adapt_calories(
                t["calories"], u["goal"], rate, t["calorie_floor"], t["base_calories"]
            )
            if new_cal != t["calories"]:
                suggest = True
                chip = "Off track"
                note = (f"Not on track for your goal ({u['goal']}). "
                        f"Suggested new target: {new_cal} kcal (now {t['calories']}).")
            elif u["goal"] == "lose" and rate > -0.2 and t["calories"] <= t["calorie_floor"]:
                chip = "At minimum intake"
                note = (f"You're already at the minimum safe intake ({t['calorie_floor']} kcal). "
                        "Consider more activity or talk to a doctor or dietitian rather than eating less.")
            else:
                chip = "On track"
                note = f"Keep your current target of {t['calories']} kcal."
            adaptive = style.stat_html(
                "Adaptive calorie check", f"{rate:+.2f}", "kg/week", chip=chip, note=note
            )

    style.grid(style.line_html("Body weight (kg)", [w["weight_kg"] for w in wl]), adaptive)
    if suggest and st.button("Apply suggested target", key="apply_target"):
        repo.set_adjustment(u["id"], new_cal - t["base_calories"], today)
        st.rerun()

    # ----- Calorie chart (with target line) -----
    cal = repo.daily_calories(u["id"])
    if cal:
        style.bar_card(
            "Daily calorie intake" + (" (dashed = target)" if t else ""),
            [float(c["kcal"]) for c in cal],
            target=t["calories"] if t else None,
            labels=[f"{c['log_date']:%d %b} · {float(c['kcal']):.0f} kcal" for c in cal],
        )

    # ----- Log weight -----
    with st.container(key="card_log_weight"):
        st.subheader("Log weight")
        c1, c2, c3 = st.columns([2, 2, 1.4], vertical_alignment="bottom")
        log_date = c1.date_input("Date", today, max_value=today, key="weight_date")
        new_w = c2.number_input(
            "Weight (kg)", 30.0, 250.0, float(min(max(latest_w, 30.0), 250.0)),
            step=0.1, format="%g",
        )
        if c3.button("Save weight", key="save_weight"):
            repo.save_weight(u["id"], log_date, new_w)
            st.rerun()

    if wl:
        with st.expander("Recent weight entries"):
            for r in reversed(wl[-10:]):
                cols = st.columns([2, 2, 1], vertical_alignment="center")
                cols[0].write(f"{r['log_date']:%d %b %Y}")
                cols[1].write(f"{r['weight_kg']:g} kg")
                if cols[2].button("🗑", key=f"soft_del_w_{r['log_date']}", help="Delete this entry"):
                    if len(wl) == 1:
                        st.error("You can't delete your only weight entry.")
                    else:
                        repo.delete_weight(u["id"], r["log_date"])
                        st.rerun()


# ---------- Route to the chosen page ----------
{
    "Profile": page_profile,
    "Workout": page_workout,
    "Food Log": page_food,
    "Water": page_water,
    "Exercise Log": page_exercise_log,
    "Progress": page_progress,
}[page]()
