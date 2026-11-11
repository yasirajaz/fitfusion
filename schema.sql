-- FitFusion schema. Safe to re-run: tables use IF NOT EXISTS and seed data uses INSERT IGNORE
-- (food.name and exercise.name are UNIQUE, so existing rows are skipped).
--
-- UPGRADING from the previous FitFusion version? Run migrate_v2.sql FIRST, then this file.
-- (It keeps your users, weights and food logs; only exercises/plans are rebuilt.)
--
-- NOTE: this version changes the `users` and `weight_log` tables (birth_date instead of age,
-- adaptive-calorie columns, one weight per day). If you have an OLD database you want to
-- discard, run:  DROP DATABASE fitfusion;  and then run this file.

CREATE DATABASE IF NOT EXISTS fitfusion CHARACTER SET utf8mb4;
USE fitfusion;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    gender ENUM('male','female') NOT NULL,
    height_cm DECIMAL(5,1) NOT NULL,
    goal ENUM('lose','maintain','gain') NOT NULL,
    activity ENUM('sedentary','light','moderate','active') NOT NULL,
    level ENUM('Beginner','Intermediate','Advanced') NOT NULL,
    -- adaptive calorie change (kcal) applied on top of the formula target
    calorie_adjustment INT NOT NULL DEFAULT 0,
    last_adjust_date DATE NULL,
    UNIQUE KEY uq_users_name (name)   -- case-insensitive with the default collation
);

-- One weight per user per day (saving again on the same day updates it).
CREATE TABLE IF NOT EXISTS weight_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    log_date DATE NOT NULL,
    weight_kg DECIMAL(5,2) NOT NULL,
    UNIQUE KEY uq_weight_user_date (user_id, log_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Nutrients are per 100 g and can never be NULL.
CREATE TABLE IF NOT EXISTS food (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(60) NOT NULL,
    kcal DECIMAL(6,1) NOT NULL DEFAULT 0,
    protein DECIMAL(5,1) NOT NULL DEFAULT 0,
    carbs DECIMAL(5,1) NOT NULL DEFAULT 0,
    fat DECIMAL(5,1) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_food_name (name)
);

CREATE TABLE IF NOT EXISTS food_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    log_date DATE NOT NULL,
    food_id INT NOT NULL,
    grams DECIMAL(7,1) NOT NULL,
    INDEX idx_food_log_user_date (user_id, log_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (food_id) REFERENCES food(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS exercise (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(60) NOT NULL,
    muscle_group ENUM('back','biceps','chest','triceps','legs','shoulders','abs','cardio') NOT NULL,
    level ENUM('Beginner','Intermediate','Advanced') NOT NULL,
    UNIQUE KEY uq_exercise_name (name)
);

-- The user's current weekly plan, so it survives page reloads.
CREATE TABLE IF NOT EXISTS workout_plan (
    user_id INT PRIMARY KEY,
    level ENUM('Beginner','Intermediate','Advanced') NOT NULL,
    goal ENUM('lose','maintain','gain') NOT NULL,
    plan JSON NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Water drunk per user per day (ml).
CREATE TABLE IF NOT EXISTS water_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    log_date DATE NOT NULL,
    ml INT NOT NULL DEFAULT 0,
    UNIQUE KEY uq_water_user_date (user_id, log_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Workouts actually performed. Strength: sets/reps/weight. Cardio: duration_min.
CREATE TABLE IF NOT EXISTS exercise_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    log_date DATE NOT NULL,
    exercise_id INT NOT NULL,
    sets INT NOT NULL DEFAULT 0,
    reps INT NOT NULL DEFAULT 0,
    weight_kg DECIMAL(6,2) NOT NULL DEFAULT 0,
    duration_min INT NOT NULL DEFAULT 0,
    INDEX idx_exercise_log_user_date (user_id, log_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercise(id) ON DELETE RESTRICT
);

INSERT IGNORE INTO food (name, kcal, protein, carbs, fat) VALUES
('Cooked white rice', 130, 2.7, 28, 0.3),
('Brown rice (cooked)', 112, 2.3, 23.5, 0.8),
('Chapati', 297, 9, 46, 7),
('Whole wheat bread', 247, 13, 41, 3.4),
('Boiled egg', 155, 13, 1.1, 11),
('Chicken breast (cooked)', 165, 31, 0, 3.6),
('Salmon (cooked)', 206, 22, 0, 12),
('Paneer', 265, 18, 1.2, 20),
('Tofu', 76, 8, 1.9, 4.8),
('Soya chunks (dry)', 345, 52, 33, 0.5),
('Dal (cooked)', 116, 9, 20, 0.4),
('Rajma (cooked)', 127, 8.7, 23, 0.5),
('Chickpeas (boiled)', 164, 8.9, 27, 2.6),
('Banana', 89, 1.1, 23, 0.3),
('Apple', 52, 0.3, 14, 0.2),
('Orange', 47, 0.9, 12, 0.1),
('Broccoli', 34, 2.8, 6.6, 0.4),
('Milk (whole)', 61, 3.2, 4.8, 3.3),
('Curd (whole milk)', 61, 3.5, 4.7, 3.3),
('Greek yogurt', 59, 10, 3.6, 0.4),
('Oats', 389, 17, 66, 7),
('Peanuts', 567, 26, 16, 49),
('Almonds', 579, 21, 22, 50),
('Potato (boiled)', 87, 1.9, 20, 0.1),
('Sweet potato (boiled)', 76, 1.4, 18, 0.1),
('Olive oil', 884, 0, 0, 100),
('Whey protein powder', 400, 80, 8, 6);

INSERT IGNORE INTO exercise (name, muscle_group, level) VALUES
-- back
('Lat Pulldown', 'back', 'Beginner'),
('Pull-ups', 'back', 'Intermediate'),
('Chin-ups', 'back', 'Intermediate'),
('Barbell Bent-over Row', 'back', 'Intermediate'),
('Seated Cable Row', 'back', 'Beginner'),
('One-arm Dumbbell Row', 'back', 'Beginner'),
('T-Bar Row', 'back', 'Advanced'),
('Chest-supported Row', 'back', 'Beginner'),
('Straight-arm Pulldown', 'back', 'Intermediate'),
('Reverse Grip Lat Pulldown', 'back', 'Intermediate'),
('Machine Row', 'back', 'Beginner'),
-- biceps
('Barbell Curl', 'biceps', 'Intermediate'),
('EZ Bar Curl', 'biceps', 'Beginner'),
('Dumbbell Curl', 'biceps', 'Beginner'),
('Hammer Curl', 'biceps', 'Beginner'),
('Incline Dumbbell Curl', 'biceps', 'Intermediate'),
('Preacher Curl', 'biceps', 'Intermediate'),
('Concentration Curl', 'biceps', 'Beginner'),
('Cable Curl', 'biceps', 'Beginner'),
('Spider Curl', 'biceps', 'Advanced'),
('Reverse Curl', 'biceps', 'Advanced'),
-- chest
('Barbell Bench Press', 'chest', 'Intermediate'),
('Incline Bench Press', 'chest', 'Intermediate'),
('Decline Bench Press', 'chest', 'Advanced'),
('Dumbbell Bench Press', 'chest', 'Beginner'),
('Incline Dumbbell Press', 'chest', 'Intermediate'),
('Dumbbell Fly', 'chest', 'Intermediate'),
('Cable Crossover', 'chest', 'Intermediate'),
('Pec Deck Fly', 'chest', 'Beginner'),
('Chest Press Machine', 'chest', 'Beginner'),
('Push-ups', 'chest', 'Beginner'),
('Chest Dips', 'chest', 'Advanced'),
-- triceps
('Rope Pushdown', 'triceps', 'Beginner'),
('Straight Bar Pushdown', 'triceps', 'Beginner'),
('Overhead Cable Extension', 'triceps', 'Intermediate'),
('Overhead Dumbbell Extension', 'triceps', 'Beginner'),
('Skull Crushers', 'triceps', 'Intermediate'),
('Close-grip Bench Press', 'triceps', 'Advanced'),
('Bench Dips', 'triceps', 'Beginner'),
('Dumbbell Kickbacks', 'triceps', 'Beginner'),
('Single-arm Cable Extension', 'triceps', 'Intermediate'),
('Assisted Dips', 'triceps', 'Beginner'),
-- legs
('Barbell Squats', 'legs', 'Intermediate'),
('Front Squats', 'legs', 'Advanced'),
('Leg Press', 'legs', 'Beginner'),
('Leg Extensions', 'legs', 'Beginner'),
('Hack Squats', 'legs', 'Intermediate'),
('Bulgarian Split Squats', 'legs', 'Intermediate'),
('Walking Lunges', 'legs', 'Beginner'),
('Goblet Squats', 'legs', 'Beginner'),
('Lying Leg Curl', 'legs', 'Beginner'),
('Seated Leg Curl', 'legs', 'Beginner'),
('Romanian Deadlift', 'legs', 'Intermediate'),
('Stiff-leg Deadlift', 'legs', 'Advanced'),
('Barbell Hip Thrust', 'legs', 'Intermediate'),
('Glute Bridges', 'legs', 'Beginner'),
('Standing Calf Raises', 'legs', 'Beginner'),
('Seated Calf Raises', 'legs', 'Beginner'),
-- shoulders
('Shoulder Press', 'shoulders', 'Intermediate'),
('Dumbbell Shoulder Press', 'shoulders', 'Beginner'),
('Arnold Press', 'shoulders', 'Intermediate'),
('Dumbbell Lateral Raise', 'shoulders', 'Beginner'),
('Cable Lateral Raise', 'shoulders', 'Intermediate'),
('Front Raise', 'shoulders', 'Beginner'),
('Reverse Pec Deck', 'shoulders', 'Beginner'),
('Bent-over Rear Delt Fly', 'shoulders', 'Intermediate'),
('Face Pull', 'shoulders', 'Beginner'),
('Upright Row', 'shoulders', 'Advanced'),
-- abs
('Crunches', 'abs', 'Beginner'),
('Reverse Crunches', 'abs', 'Beginner'),
('Hanging Leg Raises', 'abs', 'Intermediate'),
('Captain''s Chair Leg Raises', 'abs', 'Intermediate'),
('Cable Crunches', 'abs', 'Intermediate'),
('Ab Wheel Rollouts', 'abs', 'Advanced'),
('Plank', 'abs', 'Beginner'),
('Side Plank', 'abs', 'Beginner'),
('Russian Twists', 'abs', 'Intermediate'),
('Bicycle Crunches', 'abs', 'Beginner'),
('Mountain Climbers', 'abs', 'Beginner'),
-- cardio
('Running', 'cardio', 'Beginner'),
('Cycling', 'cardio', 'Beginner'),
('Brisk Walking', 'cardio', 'Beginner'),
('Jump Rope', 'cardio', 'Beginner'),
('Elliptical', 'cardio', 'Beginner'),
('Swimming', 'cardio', 'Intermediate'),
('Rowing Machine', 'cardio', 'Intermediate'),
('Stair Climber', 'cardio', 'Intermediate'),
('HIIT Circuit', 'cardio', 'Advanced');
