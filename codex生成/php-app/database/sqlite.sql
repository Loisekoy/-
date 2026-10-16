PRAGMA foreign_keys = ON;

CREATE TABLE training_goals (
    training_goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_name TEXT NOT NULL UNIQUE,
    description TEXT CHECK (description IS NULL OR length(description) <= 1000)
);
CREATE TABLE body_parts (
    body_part_id INTEGER PRIMARY KEY AUTOINCREMENT,
    body_part_name TEXT NOT NULL UNIQUE,
    description TEXT CHECK (description IS NULL OR length(description) <= 1000)
);
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 100),
    gender TEXT CHECK (gender IS NULL OR gender IN ('Female', 'Male', 'Other')),
    age INTEGER CHECK (age IS NULL OR age BETWEEN 13 AND 100),
    height_cm NUMERIC CHECK (height_cm IS NULL OR height_cm BETWEEN 100.00 AND 250.00),
    training_experience TEXT CHECK (training_experience IS NULL OR training_experience IN ('Beginner', 'Intermediate', 'Advanced')),
    training_goal_id INTEGER REFERENCES training_goals(training_goal_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    training_days_per_week INTEGER CHECK (training_days_per_week IS NULL OR training_days_per_week BETWEEN 2 AND 6),
    training_duration_minutes INTEGER CHECK (training_duration_minutes IS NULL OR training_duration_minutes IN (30, 60, 90)),
    profile_completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_auth (
    auth_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_email_verified INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_sessions (
    user_session_id TEXT PRIMARY KEY,
    auth_id INTEGER NOT NULL REFERENCES user_auth(auth_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    CHECK (expires_at > created_at)
);
CREATE TABLE admins (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE login_failures (
    login_failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_hash TEXT NOT NULL CHECK (length(ip_hash) = 64),
    failed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_body_parts (
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    body_part_id INTEGER NOT NULL REFERENCES body_parts(body_part_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    priority INTEGER NOT NULL DEFAULT 1 CHECK (priority BETWEEN 1 AND 8),
    PRIMARY KEY (user_id, body_part_id),
    UNIQUE (user_id, priority)
);
CREATE TABLE body_records (
    body_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    record_date TEXT NOT NULL,
    weight_kg NUMERIC NOT NULL CHECK (weight_kg BETWEEN 20.00 AND 500.00),
    notes TEXT CHECK (notes IS NULL OR length(notes) <= 1000),
    UNIQUE (user_id, record_date)
);
CREATE TABLE exercises (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    body_part_id INTEGER NOT NULL REFERENCES body_parts(body_part_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE exercise_versions (
    exercise_version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER NOT NULL REFERENCES exercises(exercise_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    exercise_name TEXT NOT NULL CHECK (length(trim(exercise_name)) BETWEEN 1 AND 120),
    difficulty_level TEXT NOT NULL CHECK (difficulty_level IN ('Beginner', 'Intermediate', 'Advanced')),
    equipment TEXT,
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 4000),
    image_url TEXT CHECK (image_url IS NULL OR length(image_url) <= 2048),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (exercise_id, version_no)
);
CREATE TABLE workout_plans (
    workout_plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    copied_from_plan_id INTEGER REFERENCES workout_plans(workout_plan_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    plan_name TEXT NOT NULL CHECK (length(trim(plan_name)) BETWEEN 1 AND 120),
    published_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (copied_from_plan_id IS NULL OR copied_from_plan_id <> workout_plan_id)
);
CREATE TABLE planning_profiles (
    workout_plan_id INTEGER PRIMARY KEY REFERENCES workout_plans(workout_plan_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    training_goal_id INTEGER NOT NULL REFERENCES training_goals(training_goal_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    age_snapshot INTEGER NOT NULL CHECK (age_snapshot BETWEEN 13 AND 100),
    height_cm_snapshot NUMERIC NOT NULL CHECK (height_cm_snapshot BETWEEN 100.00 AND 250.00),
    weight_kg_snapshot NUMERIC NOT NULL CHECK (weight_kg_snapshot BETWEEN 20.00 AND 500.00),
    weight_record_date TEXT NOT NULL,
    experience_snapshot TEXT NOT NULL CHECK (experience_snapshot IN ('Beginner', 'Intermediate', 'Advanced')),
    training_days_per_week INTEGER NOT NULL CHECK (training_days_per_week BETWEEN 2 AND 6),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes IN (30, 60, 90)),
    algorithm_version TEXT NOT NULL DEFAULT 'rules-v1',
    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE planning_profile_body_parts (
    workout_plan_id INTEGER NOT NULL REFERENCES planning_profiles(workout_plan_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    body_part_id INTEGER NOT NULL REFERENCES body_parts(body_part_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 8),
    PRIMARY KEY (workout_plan_id, body_part_id),
    UNIQUE (workout_plan_id, priority)
);
CREATE TABLE plan_days (
    plan_day_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_plan_id INTEGER NOT NULL REFERENCES workout_plans(workout_plan_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    day_number INTEGER NOT NULL CHECK (day_number BETWEEN 1 AND 6),
    day_title TEXT NOT NULL CHECK (length(trim(day_title)) BETWEEN 1 AND 120),
    UNIQUE (workout_plan_id, day_number)
);
CREATE TABLE plan_exercises (
    plan_exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id INTEGER NOT NULL REFERENCES plan_days(plan_day_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    exercise_version_id INTEGER NOT NULL REFERENCES exercise_versions(exercise_version_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    exercise_order INTEGER NOT NULL CHECK (exercise_order BETWEEN 1 AND 10),
    target_sets INTEGER NOT NULL CHECK (target_sets BETWEEN 1 AND 10),
    target_reps INTEGER NOT NULL CHECK (target_reps BETWEEN 1 AND 50),
    rest_seconds INTEGER NOT NULL CHECK (rest_seconds BETWEEN 0 AND 600),
    target_weight_kg NUMERIC CHECK (target_weight_kg IS NULL OR target_weight_kg BETWEEN 0.00 AND 999.99),
    UNIQUE (plan_day_id, exercise_order)
);
CREATE TABLE workout_sessions (
    workout_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'cancelled')),
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT,
    notes TEXT CHECK (notes IS NULL OR length(notes) <= 1000),
    CHECK ((status = 'in_progress' AND ended_at IS NULL) OR (status IN ('completed', 'cancelled') AND ended_at IS NOT NULL))
);
CREATE TABLE workout_session_plans (
    workout_session_id INTEGER PRIMARY KEY REFERENCES workout_sessions(workout_session_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    plan_day_id INTEGER NOT NULL REFERENCES plan_days(plan_day_id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE workout_session_exercises (
    workout_session_exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_session_id INTEGER NOT NULL REFERENCES workout_sessions(workout_session_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    plan_exercise_id INTEGER NOT NULL REFERENCES plan_exercises(plan_exercise_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    exercise_version_id INTEGER NOT NULL REFERENCES exercise_versions(exercise_version_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    exercise_order INTEGER NOT NULL CHECK (exercise_order BETWEEN 1 AND 10),
    target_sets INTEGER NOT NULL CHECK (target_sets BETWEEN 1 AND 10),
    target_reps INTEGER NOT NULL CHECK (target_reps BETWEEN 1 AND 50),
    rest_seconds INTEGER NOT NULL CHECK (rest_seconds BETWEEN 0 AND 600),
    target_weight_kg NUMERIC CHECK (target_weight_kg IS NULL OR target_weight_kg BETWEEN 0.00 AND 999.99),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workout_session_id, plan_exercise_id),
    UNIQUE (workout_session_id, exercise_order)
);
CREATE TABLE workout_sets (
    workout_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_session_exercise_id INTEGER NOT NULL REFERENCES workout_session_exercises(workout_session_exercise_id) ON DELETE CASCADE ON UPDATE RESTRICT,
    set_number INTEGER NOT NULL CHECK (set_number BETWEEN 1 AND 100),
    weight_kg NUMERIC NOT NULL CHECK (weight_kg BETWEEN 0.00 AND 999.99),
    reps INTEGER NOT NULL CHECK (reps BETWEEN 1 AND 999),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workout_session_exercise_id, set_number)
);

CREATE UNIQUE INDEX uq_workout_sessions_user_active ON workout_sessions(user_id) WHERE status = 'in_progress';
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_login_failures_ip_time ON login_failures(ip_hash, failed_at DESC);
CREATE INDEX idx_body_records_user_date ON body_records(user_id, record_date DESC, body_record_id DESC);
CREATE INDEX idx_exercises_body_active ON exercises(body_part_id, is_active);
CREATE INDEX idx_exercise_versions_latest ON exercise_versions(exercise_id, version_no DESC);
CREATE INDEX idx_workout_plans_user_created ON workout_plans(user_id, created_at DESC);
CREATE INDEX idx_plan_days_plan ON plan_days(workout_plan_id, day_number);
CREATE INDEX idx_plan_exercises_day ON plan_exercises(plan_day_id, exercise_order);
CREATE INDEX idx_workout_sessions_user_started ON workout_sessions(user_id, started_at DESC);
CREATE INDEX idx_session_exercises_session ON workout_session_exercises(workout_session_id, exercise_order);
CREATE INDEX idx_workout_sets_session_exercise ON workout_sets(workout_session_exercise_id, set_number);

CREATE TRIGGER trg_exercise_versions_immutable_update BEFORE UPDATE ON exercise_versions
BEGIN SELECT RAISE(ABORT, 'exercise_versions are immutable; create a new version instead'); END;
CREATE TRIGGER trg_exercise_versions_immutable_delete BEFORE DELETE ON exercise_versions
BEGIN SELECT RAISE(ABORT, 'exercise_versions are immutable; create a new version instead'); END;

CREATE TRIGGER trg_plan_exercise_identity_insert BEFORE INSERT ON plan_exercises
WHEN EXISTS (
    SELECT 1 FROM plan_exercises other
    JOIN exercise_versions ov ON ov.exercise_version_id = other.exercise_version_id
    JOIN exercise_versions nv ON nv.exercise_version_id = NEW.exercise_version_id
    WHERE other.plan_day_id = NEW.plan_day_id AND ov.exercise_id = nv.exercise_id
)
BEGIN SELECT RAISE(ABORT, 'the same exercise identity cannot appear twice on one plan day'); END;

CREATE TRIGGER trg_session_exercise_snapshot_insert BEFORE INSERT ON workout_session_exercises
WHEN NOT EXISTS (
    SELECT 1 FROM workout_session_plans wsp
    JOIN plan_exercises pe ON pe.plan_day_id = wsp.plan_day_id
    WHERE wsp.workout_session_id = NEW.workout_session_id
      AND pe.plan_exercise_id = NEW.plan_exercise_id
      AND pe.exercise_version_id = NEW.exercise_version_id
)
BEGIN SELECT RAISE(ABORT, 'session exercise must match the session source plan day'); END;

CREATE TRIGGER trg_session_exercise_membership_immutable BEFORE UPDATE OF workout_session_id, plan_exercise_id, exercise_version_id ON workout_session_exercises
BEGIN SELECT RAISE(ABORT, 'session exercise membership is immutable'); END;

CREATE TRIGGER trg_body_records_keep_last BEFORE DELETE ON body_records
WHEN EXISTS (SELECT 1 FROM users WHERE user_id = OLD.user_id AND profile_completed_at IS NOT NULL)
 AND (SELECT COUNT(*) FROM body_records WHERE user_id = OLD.user_id) <= 1
BEGIN SELECT RAISE(ABORT, 'a completed profile must retain at least one body record'); END;

CREATE TRIGGER trg_completed_session_has_set BEFORE UPDATE OF status ON workout_sessions
WHEN NEW.status = 'completed' AND NOT EXISTS (
    SELECT 1 FROM workout_sets ws
    JOIN workout_session_exercises wse ON wse.workout_session_exercise_id = ws.workout_session_exercise_id
    WHERE wse.workout_session_id = NEW.workout_session_id
)
BEGIN SELECT RAISE(ABORT, 'a completed workout session must contain at least one set'); END;

CREATE TRIGGER trg_completed_session_keep_set BEFORE DELETE ON workout_sets
WHEN EXISTS (
    SELECT 1 FROM workout_session_exercises wse
    JOIN workout_sessions s ON s.workout_session_id = wse.workout_session_id
    WHERE wse.workout_session_exercise_id = OLD.workout_session_exercise_id AND s.status = 'completed'
) AND (
    SELECT COUNT(*) FROM workout_sets ws
    JOIN workout_session_exercises wse ON wse.workout_session_exercise_id = ws.workout_session_exercise_id
    WHERE wse.workout_session_id = (
        SELECT workout_session_id FROM workout_session_exercises WHERE workout_session_exercise_id = OLD.workout_session_exercise_id
    )
) <= 1
BEGIN SELECT RAISE(ABORT, 'a completed workout session must retain at least one set'); END;

CREATE TRIGGER trg_completed_session_keep_exercise BEFORE DELETE ON workout_session_exercises
WHEN EXISTS (
    SELECT 1 FROM workout_sessions s
    WHERE s.workout_session_id = OLD.workout_session_id AND s.status = 'completed'
)
BEGIN SELECT RAISE(ABORT, 'a completed workout session must retain its exercise snapshots'); END;

CREATE TRIGGER trg_completed_session_keep_exercise_parent BEFORE UPDATE OF workout_session_id ON workout_session_exercises
WHEN EXISTS (
    SELECT 1 FROM workout_sessions s
    WHERE s.workout_session_id = OLD.workout_session_id AND s.status = 'completed'
)
BEGIN SELECT RAISE(ABORT, 'a completed workout session must retain its exercise snapshots'); END;

CREATE TRIGGER trg_lock_active_workout_plan BEFORE UPDATE ON workout_plans
WHEN EXISTS (
    SELECT 1 FROM workout_sessions ws JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id
    JOIN plan_days pd ON pd.plan_day_id = wsp.plan_day_id
    WHERE pd.workout_plan_id = OLD.workout_plan_id AND ws.status = 'in_progress'
)
BEGIN SELECT RAISE(ABORT, 'source plan is locked while a workout is in progress'); END;
CREATE TRIGGER trg_lock_active_plan_day BEFORE UPDATE ON plan_days
WHEN EXISTS (
    SELECT 1 FROM workout_sessions ws JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id
    WHERE wsp.plan_day_id = OLD.plan_day_id AND ws.status = 'in_progress'
)
BEGIN SELECT RAISE(ABORT, 'source plan is locked while a workout is in progress'); END;
CREATE TRIGGER trg_lock_active_plan_exercise BEFORE UPDATE ON plan_exercises
WHEN EXISTS (
    SELECT 1 FROM workout_sessions ws JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id
    WHERE wsp.plan_day_id = OLD.plan_day_id AND ws.status = 'in_progress'
)
BEGIN SELECT RAISE(ABORT, 'source plan is locked while a workout is in progress'); END;
