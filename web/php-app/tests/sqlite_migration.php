<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\SqliteMigrator;

function checkMigration(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException('FAIL: ' . $message);
    }
    echo "PASS: {$message}\n";
}

$path = sys_get_temp_dir() . '/fittrack-sqlite-migration-' . bin2hex(random_bytes(6)) . '.sqlite';
$pdo = new PDO('sqlite:' . $path, null, null, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);
$pdo->exec('PRAGMA foreign_keys = ON');

$legacySchema = <<<'SQL'
CREATE TABLE training_goals (
    training_goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_name TEXT NOT NULL UNIQUE,
    description TEXT
);
CREATE TABLE body_parts (
    body_part_id INTEGER PRIMARY KEY AUTOINCREMENT,
    body_part_name TEXT NOT NULL UNIQUE,
    description TEXT
);
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    gender TEXT,
    age INTEGER,
    height_cm NUMERIC,
    training_experience TEXT,
    training_goal_id INTEGER,
    training_days_per_week INTEGER,
    training_duration_minutes INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_auth (
    auth_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_email_verified INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_sessions (
    user_session_id TEXT PRIMARY KEY,
    auth_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE TABLE admins (
    user_id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_body_parts (
    user_id INTEGER NOT NULL,
    body_part_id INTEGER NOT NULL,
    priority INTEGER NOT NULL,
    PRIMARY KEY (user_id, body_part_id)
);
CREATE TABLE body_records (
    body_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    record_date TEXT NOT NULL,
    weight_kg NUMERIC NOT NULL,
    notes TEXT,
    UNIQUE (user_id, record_date)
);
CREATE TABLE exercises (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_name TEXT NOT NULL UNIQUE,
    body_part_id INTEGER NOT NULL,
    difficulty_level TEXT NOT NULL,
    equipment TEXT,
    description TEXT NOT NULL,
    image_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE workout_plans (
    workout_plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan_name TEXT NOT NULL,
    training_goal_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    experience_snapshot TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL
);
CREATE TABLE plan_days (
    plan_day_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_plan_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    day_title TEXT NOT NULL,
    UNIQUE (workout_plan_id, day_number)
);
CREATE TABLE plan_exercises (
    plan_exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    exercise_order INTEGER NOT NULL,
    target_sets INTEGER NOT NULL,
    target_reps INTEGER NOT NULL,
    rest_seconds INTEGER NOT NULL,
    UNIQUE (plan_day_id, exercise_order),
    UNIQUE (plan_day_id, exercise_id)
);
CREATE TABLE workout_sessions (
    workout_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    notes TEXT
);
CREATE TABLE workout_session_plans (
    workout_session_id INTEGER PRIMARY KEY,
    plan_day_id INTEGER NOT NULL
);
CREATE TABLE workout_sets (
    workout_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_session_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    weight_kg NUMERIC NOT NULL,
    reps INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (workout_session_id, exercise_id, set_number)
);
SQL;

try {
    $pdo->exec($legacySchema);
    $pdo->exec("INSERT INTO training_goals VALUES (1, 'Strength', '力量')");
    $pdo->exec("INSERT INTO body_parts VALUES (1, 'Chest', '胸部')");
    $pdo->exec(
        "INSERT INTO users VALUES (1, 'Legacy User', 'Other', 25, 170, 'Beginner', 1, 2, 60, "
        . "'2026-10-01 08:00:00')"
    );
    $pdo->exec(
        "INSERT INTO user_auth VALUES (1, 1, 'legacy@example.test', 'hash', 0, 1, "
        . "'2026-10-01 08:00:00')"
    );
    $pdo->exec(
        "INSERT INTO user_sessions VALUES ('session-1', 1, '2026-10-01 08:00:00', "
        . "'2027-10-01 08:00:00', NULL)"
    );
    $pdo->exec("INSERT INTO user_body_parts VALUES (1, 1, 1)");
    $pdo->exec("INSERT INTO body_records VALUES (1, 1, '2026-10-01', 70, 'legacy')");
    $pdo->exec(
        "INSERT INTO exercises VALUES (1, 'Legacy Press', 1, 'Beginner', 'Barbell', "
        . "'Legacy instructions', '/legacy.gif', 1)"
    );
    $pdo->exec(
        "INSERT INTO workout_plans VALUES (1, 1, 'Legacy Plan', 1, "
        . "'2026-10-01 08:00:00', 'Beginner', 60)"
    );
    $pdo->exec("INSERT INTO plan_days VALUES (1, 1, 1, 'Day 1')");
    $pdo->exec("INSERT INTO plan_days VALUES (2, 1, 2, 'Day 2')");
    $pdo->exec("INSERT INTO plan_exercises VALUES (1, 1, 1, 1, 3, 10, 60)");
    $pdo->exec(
        "INSERT INTO workout_sessions VALUES (1, 1, 'completed', '2026-10-02 08:00:00', "
        . "'2026-10-02 09:00:00', 'legacy workout')"
    );
    $pdo->exec("INSERT INTO workout_session_plans VALUES (1, 1)");
    $pdo->exec(
        "INSERT INTO workout_sets VALUES (1, 1, 1, 1, 50, 10, '2026-10-02 08:10:00')"
    );

    checkMigration(SqliteMigrator::migrateIfNeeded($pdo, $path), '舊版 SQLite 會執行一次升級');
    $backup = SqliteMigrator::lastBackupPath();
    checkMigration($backup !== null && is_file($backup), '升級前備份已建立');
    checkMigration(
        (int) $pdo->query(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )->fetchColumn() === 20,
        '升級後共有 20 張應用資料表'
    );
    checkMigration(
        (string) $pdo->query('SELECT exercise_name FROM exercise_versions')->fetchColumn() === 'Legacy Press',
        '舊動作已轉為不可變版本'
    );
    checkMigration(
        (string) $pdo->query('SELECT algorithm_version FROM planning_profiles')->fetchColumn()
            === 'rules-v1-legacy-import',
        '舊課表已建立可識別的規劃快照'
    );
    checkMigration(
        (int) $pdo->query('SELECT COUNT(*) FROM workout_session_exercises')->fetchColumn() === 1,
        '舊訓練已建立場次動作快照'
    );
    $set = $pdo->query(
        'SELECT wset.weight_kg, wset.reps, ev.exercise_name FROM workout_sets wset '
        . 'JOIN workout_session_exercises wse '
        . 'ON wse.workout_session_exercise_id = wset.workout_session_exercise_id '
        . 'JOIN exercise_versions ev ON ev.exercise_version_id = wse.exercise_version_id'
    )->fetch();
    checkMigration(
        (float) $set['weight_kg'] === 50.0
            && (int) $set['reps'] === 10
            && $set['exercise_name'] === 'Legacy Press',
        '舊組數、重量、次數與動作關係均保留'
    );
    checkMigration($pdo->query('PRAGMA foreign_key_check')->fetchAll() === [], '升級後外鍵檢查通過');
    checkMigration(!SqliteMigrator::migrateIfNeeded($pdo, $path), '目前版本重跑不會重複升級');
} finally {
    $pdo = null;
    foreach (glob($path . '*') ?: [] as $temporaryFile) {
        unlink($temporaryFile);
    }
}
