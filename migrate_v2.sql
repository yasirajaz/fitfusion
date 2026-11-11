-- Upgrade from the previous FitFusion version WITHOUT losing users, weights or food logs.
-- Run order:   mysql -u root -p < migrate_v2.sql
--              mysql -u root -p < schema.sql
-- Only the exercise library and saved workout plans are rebuilt (new muscle groups,
-- 85+ exercises); schema.sql recreates them plus the new water and exercise-log tables.
USE fitfusion;
DROP TABLE IF EXISTS workout_plan;
DROP TABLE IF EXISTS exercise_log;
DROP TABLE IF EXISTS exercise;
