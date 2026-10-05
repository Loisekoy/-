PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS training_goals (
    training_goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS body_parts (
    body_part_id INTEGER PRIMARY KEY AUTOINCREMENT,
    body_part_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    gender TEXT CHECK (gender IS NULL OR gender IN ('Female', 'Male', 'Other')),
    age INTEGER CHECK (age IS NULL OR age BETWEEN 13 AND 100),
    height_cm NUMERIC CHECK (height_cm IS NULL OR height_cm BETWEEN 100 AND 250),
    training_experience TEXT CHECK (
        training_experience IS NULL OR training_experience IN ('Beginner', 'Intermediate', 'Advanced')
    ),
    training_goal_id INTEGER REFERENCES training_goals(training_goal_id) ON DELETE RESTRICT,
    training_days_per_week INTEGER CHECK (
        training_days_per_week IS NULL OR training_days_per_week BETWEEN 2 AND 6
    ),
    training_duration_minutes INTEGER CHECK (
        training_duration_minutes IS NULL OR training_duration_minutes IN (30, 60, 90)
    ),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_auth (
    auth_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_email_verified INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    user_session_id TEXT PRIMARY KEY,
    auth_id INTEGER NOT NULL REFERENCES user_auth(auth_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_body_parts (
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    body_part_id INTEGER NOT NULL REFERENCES body_parts(body_part_id) ON DELETE RESTRICT,
    priority INTEGER NOT NULL DEFAULT 1 CHECK (priority BETWEEN 1 AND 8),
    PRIMARY KEY (user_id, body_part_id),
    UNIQUE (user_id, priority)
);

CREATE TABLE IF NOT EXISTS exercises (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_name TEXT NOT NULL UNIQUE,
    body_part_id INTEGER NOT NULL REFERENCES body_parts(body_part_id) ON DELETE RESTRICT,
    difficulty_level TEXT NOT NULL CHECK (
        difficulty_level IN ('Beginner', 'Intermediate', 'Advanced')
    ),
    equipment TEXT,
    description TEXT NOT NULL,
    image_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS workout_plans (
    workout_plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    training_goal_id INTEGER NOT NULL REFERENCES training_goals(training_goal_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    experience_snapshot TEXT NOT NULL CHECK (
        experience_snapshot IN ('Beginner', 'Intermediate', 'Advanced')
    ),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes IN (30, 60, 90))
);

CREATE TABLE IF NOT EXISTS plan_days (
    plan_day_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_plan_id INTEGER NOT NULL REFERENCES workout_plans(workout_plan_id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL CHECK (day_number BETWEEN 1 AND 6),
    day_title TEXT NOT NULL,
    UNIQUE (workout_plan_id, day_number)
);

CREATE TABLE IF NOT EXISTS plan_exercises (
    plan_exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id INTEGER NOT NULL REFERENCES plan_days(plan_day_id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(exercise_id) ON DELETE RESTRICT,
    exercise_order INTEGER NOT NULL CHECK (exercise_order BETWEEN 1 AND 6),
    target_sets INTEGER NOT NULL CHECK (target_sets BETWEEN 1 AND 10),
    target_reps INTEGER NOT NULL CHECK (target_reps BETWEEN 1 AND 50),
    rest_seconds INTEGER NOT NULL CHECK (rest_seconds BETWEEN 0 AND 300),
    UNIQUE (plan_day_id, exercise_order),
    UNIQUE (plan_day_id, exercise_id)
);

CREATE TABLE IF NOT EXISTS workout_sessions (
    workout_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (
        status IN ('in_progress', 'completed', 'cancelled')
    ),
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS workout_sets (
    workout_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_session_id INTEGER NOT NULL REFERENCES workout_sessions(workout_session_id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(exercise_id) ON DELETE RESTRICT,
    set_number INTEGER NOT NULL CHECK (set_number BETWEEN 1 AND 100),
    weight_kg NUMERIC NOT NULL CHECK (weight_kg BETWEEN 0 AND 999.99),
    reps INTEGER NOT NULL CHECK (reps BETWEEN 1 AND 999),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workout_session_id, exercise_id, set_number)
);

CREATE TABLE IF NOT EXISTS body_records (
    body_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    record_date TEXT NOT NULL,
    weight_kg NUMERIC NOT NULL CHECK (weight_kg BETWEEN 20 AND 500),
    notes TEXT,
    UNIQUE (user_id, record_date)
);

CREATE TABLE IF NOT EXISTS workout_session_plans (
    workout_session_id INTEGER PRIMARY KEY REFERENCES workout_sessions(workout_session_id) ON DELETE CASCADE,
    plan_day_id INTEGER NOT NULL REFERENCES plan_days(plan_day_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_workout_sessions_user_active
    ON workout_sessions(user_id) WHERE status = 'in_progress';
CREATE INDEX IF NOT EXISTS idx_exercises_recommendation
    ON exercises(body_part_id, difficulty_level, is_active);
CREATE INDEX IF NOT EXISTS idx_workout_plans_user
    ON workout_plans(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_started
    ON workout_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_workout_sets_exercise
    ON workout_sets(exercise_id, workout_session_id);
CREATE INDEX IF NOT EXISTS idx_body_records_user_date
    ON body_records(user_id, record_date DESC);
