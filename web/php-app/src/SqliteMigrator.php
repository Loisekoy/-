<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;
use RuntimeException;
use Throwable;

final class SqliteMigrator
{
    private const LEGACY_TABLES = [
        'training_goals',
        'body_parts',
        'users',
        'user_auth',
        'user_sessions',
        'admins',
        'user_body_parts',
        'body_records',
        'exercises',
        'workout_plans',
        'plan_days',
        'plan_exercises',
        'workout_sessions',
        'workout_session_plans',
        'workout_sets',
    ];

    private static ?string $lastBackupPath = null;

    public static function lastBackupPath(): ?string
    {
        return self::$lastBackupPath;
    }

    public static function migrateIfNeeded(PDO $pdo, string $databasePath): bool
    {
        if (self::hasTable($pdo, 'exercise_versions')) {
            return false;
        }

        self::assertLegacySchema($pdo);
        self::assertLegacyDataCanBeMapped($pdo);

        $pdo->exec('PRAGMA foreign_keys = OFF');
        try {
            $pdo->exec('BEGIN EXCLUSIVE');

            // Another local worker may have completed the migration while this
            // process was waiting for the exclusive lock.
            if (self::hasTable($pdo, 'exercise_versions')) {
                $pdo->exec('COMMIT');
                $pdo->exec('PRAGMA foreign_keys = ON');
                return false;
            }

            self::$lastBackupPath = self::backup($databasePath);
            self::renameLegacyTables($pdo);

            $schema = file_get_contents(Config::root() . '/database/sqlite.sql');
            if ($schema === false) {
                throw new RuntimeException('找不到目前版本的 SQLite schema。');
            }
            $pdo->exec($schema);
            self::copyLegacyData($pdo);
            self::dropLegacyTables($pdo);

            $violations = $pdo->query('PRAGMA foreign_key_check')->fetchAll();
            if ($violations !== []) {
                throw new RuntimeException('SQLite 升級後外鍵檢查失敗，已取消升級。');
            }

            $tableCount = (int) $pdo->query(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )->fetchColumn();
            if ($tableCount !== 20) {
                throw new RuntimeException("SQLite 升級後資料表數量錯誤：{$tableCount}，預期 20。 ");
            }

            $pdo->exec('COMMIT');
            $pdo->exec('PRAGMA foreign_keys = ON');
            return true;
        } catch (Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            $pdo->exec('PRAGMA foreign_keys = ON');
            throw $error;
        }
    }

    private static function assertLegacySchema(PDO $pdo): void
    {
        foreach (self::LEGACY_TABLES as $table) {
            if (!self::hasTable($pdo, $table)) {
                throw new RuntimeException("SQLite 結構不完整，缺少 {$table}；未自動修改原始資料庫。 ");
            }
        }

        $requiredColumns = [
            'exercises' => 'exercise_name',
            'plan_exercises' => 'exercise_id',
            'workout_sets' => 'workout_session_id',
        ];
        foreach ($requiredColumns as $table => $column) {
            if (!self::hasColumn($pdo, $table, $column)) {
                throw new RuntimeException("SQLite 不是可辨識的舊版結構：{$table}.{$column} 不存在。 ");
            }
        }
    }

    private static function assertLegacyDataCanBeMapped(PDO $pdo): void
    {
        $unmappedSessions = (int) $pdo->query(
            'SELECT COUNT(*) FROM workout_sessions ws '
            . 'LEFT JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id '
            . 'WHERE wsp.workout_session_id IS NULL'
        )->fetchColumn();
        if ($unmappedSessions > 0) {
            throw new RuntimeException('舊版 SQLite 有找不到來源課表日的訓練場次，無法安全升級。');
        }

        $unmappedSets = (int) $pdo->query(
            'SELECT COUNT(*) FROM workout_sets wset '
            . 'LEFT JOIN workout_session_plans wsp ON wsp.workout_session_id = wset.workout_session_id '
            . 'LEFT JOIN plan_exercises pe ON pe.plan_day_id = wsp.plan_day_id '
            . 'AND pe.exercise_id = wset.exercise_id '
            . 'WHERE pe.plan_exercise_id IS NULL'
        )->fetchColumn();
        if ($unmappedSets > 0) {
            throw new RuntimeException('舊版 SQLite 有無法對應課表動作的組數，無法安全升級。');
        }

        $incompletePlans = (int) $pdo->query(
            'SELECT COUNT(*) FROM workout_plans wp JOIN users u ON u.user_id = wp.user_id '
            . 'WHERE u.age IS NULL OR u.height_cm IS NULL OR u.training_days_per_week IS NULL '
            . 'OR NOT EXISTS (SELECT 1 FROM body_records br WHERE br.user_id = u.user_id) '
            . 'OR NOT EXISTS (SELECT 1 FROM user_body_parts ubp WHERE ubp.user_id = u.user_id)'
        )->fetchColumn();
        if ($incompletePlans > 0) {
            throw new RuntimeException('舊版 SQLite 的既有課表缺少可建立規劃快照的資料，無法安全升級。');
        }
    }

    private static function backup(string $databasePath): string
    {
        if ($databasePath === '' || !is_file($databasePath)) {
            throw new RuntimeException('找不到要備份的 SQLite 資料庫檔案。');
        }

        $backupPath = $databasePath . '.backup-v1.0-' . gmdate('Ymd-His');
        if (!copy($databasePath, $backupPath)) {
            throw new RuntimeException('無法建立 SQLite 升級前備份。');
        }
        return $backupPath;
    }

    private static function renameLegacyTables(PDO $pdo): void
    {
        foreach ([
            'uq_workout_sessions_user_active',
            'idx_exercises_recommendation',
            'idx_workout_plans_user',
            'idx_workout_sessions_user_started',
            'idx_workout_sets_exercise',
            'idx_body_records_user_date',
        ] as $index) {
            $pdo->exec("DROP INDEX IF EXISTS {$index}");
        }

        // Rename children first so SQLite does not leave the legacy graph
        // sharing any names with the new v1.1 tables.
        foreach (array_reverse(self::LEGACY_TABLES) as $table) {
            $pdo->exec("ALTER TABLE {$table} RENAME TO legacy_{$table}");
        }
    }

    private static function copyLegacyData(PDO $pdo): void
    {
        $statements = [
            'INSERT INTO training_goals SELECT * FROM legacy_training_goals',
            'INSERT INTO body_parts SELECT * FROM legacy_body_parts',
            'INSERT INTO users '
                . '(user_id, name, gender, age, height_cm, training_experience, training_goal_id, '
                . 'training_days_per_week, training_duration_minutes, profile_completed_at, created_at) '
                . 'SELECT u.user_id, u.name, u.gender, u.age, u.height_cm, u.training_experience, '
                . 'u.training_goal_id, u.training_days_per_week, u.training_duration_minutes, '
                . 'CASE WHEN u.age IS NOT NULL AND u.height_cm IS NOT NULL '
                . 'AND u.training_experience IS NOT NULL AND u.training_goal_id IS NOT NULL '
                . 'AND u.training_days_per_week IS NOT NULL AND u.training_duration_minutes IS NOT NULL '
                . 'AND EXISTS (SELECT 1 FROM legacy_body_records br WHERE br.user_id = u.user_id) '
                . 'AND EXISTS (SELECT 1 FROM legacy_user_body_parts ubp WHERE ubp.user_id = u.user_id) '
                . 'THEN u.created_at ELSE NULL END, u.created_at FROM legacy_users u',
            'INSERT INTO user_auth SELECT * FROM legacy_user_auth',
            'INSERT INTO user_sessions SELECT * FROM legacy_user_sessions',
            'INSERT INTO admins SELECT * FROM legacy_admins',
            'INSERT INTO user_body_parts SELECT * FROM legacy_user_body_parts',
            'INSERT INTO body_records SELECT * FROM legacy_body_records',
            'INSERT INTO exercises (exercise_id, body_part_id, is_active, created_at) '
                . 'SELECT exercise_id, body_part_id, is_active, CURRENT_TIMESTAMP FROM legacy_exercises',
            'INSERT INTO exercise_versions '
                . '(exercise_version_id, exercise_id, version_no, exercise_name, difficulty_level, '
                . 'equipment, description, image_url, created_at) '
                . 'SELECT exercise_id, exercise_id, 1, exercise_name, difficulty_level, equipment, '
                . 'description, image_url, CURRENT_TIMESTAMP FROM legacy_exercises',
            'INSERT INTO workout_plans '
                . '(workout_plan_id, user_id, copied_from_plan_id, plan_name, published_at, archived_at, created_at) '
                . 'SELECT workout_plan_id, user_id, NULL, plan_name, created_at, NULL, created_at '
                . 'FROM legacy_workout_plans',
            'INSERT INTO planning_profiles '
                . '(workout_plan_id, training_goal_id, age_snapshot, height_cm_snapshot, '
                . 'weight_kg_snapshot, weight_record_date, experience_snapshot, '
                . 'training_days_per_week, duration_minutes, algorithm_version, captured_at) '
                . 'SELECT wp.workout_plan_id, wp.training_goal_id, u.age, u.height_cm, '
                . '(SELECT br.weight_kg FROM legacy_body_records br WHERE br.user_id = wp.user_id '
                . 'ORDER BY br.record_date DESC, br.body_record_id DESC LIMIT 1), '
                . '(SELECT br.record_date FROM legacy_body_records br WHERE br.user_id = wp.user_id '
                . 'ORDER BY br.record_date DESC, br.body_record_id DESC LIMIT 1), '
                . 'wp.experience_snapshot, '
                . '(SELECT COUNT(*) FROM legacy_plan_days pd WHERE pd.workout_plan_id = wp.workout_plan_id), '
                . 'wp.duration_minutes, \'rules-v1-legacy-import\', wp.created_at '
                . 'FROM legacy_workout_plans wp JOIN legacy_users u ON u.user_id = wp.user_id',
            'INSERT INTO planning_profile_body_parts (workout_plan_id, body_part_id, priority) '
                . 'SELECT wp.workout_plan_id, ubp.body_part_id, ubp.priority '
                . 'FROM legacy_workout_plans wp '
                . 'JOIN legacy_user_body_parts ubp ON ubp.user_id = wp.user_id',
            'INSERT INTO plan_days SELECT * FROM legacy_plan_days',
            'INSERT INTO plan_exercises '
                . '(plan_exercise_id, plan_day_id, exercise_version_id, exercise_order, '
                . 'target_sets, target_reps, rest_seconds, target_weight_kg) '
                . 'SELECT plan_exercise_id, plan_day_id, exercise_id, exercise_order, '
                . 'target_sets, target_reps, rest_seconds, NULL FROM legacy_plan_exercises',
            'INSERT INTO workout_sessions '
                . '(workout_session_id, user_id, status, started_at, ended_at, notes) '
                . "SELECT workout_session_id, user_id, CASE WHEN status = 'completed' THEN 'in_progress' ELSE status END, "
                . "started_at, CASE WHEN status = 'completed' THEN NULL ELSE ended_at END, notes "
                . 'FROM legacy_workout_sessions',
            'INSERT INTO workout_session_plans SELECT * FROM legacy_workout_session_plans',
            'INSERT INTO workout_session_exercises '
                . '(workout_session_id, plan_exercise_id, exercise_version_id, exercise_order, '
                . 'target_sets, target_reps, rest_seconds, target_weight_kg, created_at) '
                . 'SELECT wsp.workout_session_id, pe.plan_exercise_id, pe.exercise_version_id, '
                . 'pe.exercise_order, pe.target_sets, pe.target_reps, pe.rest_seconds, '
                . 'pe.target_weight_kg, ws.started_at '
                . 'FROM workout_session_plans wsp '
                . 'JOIN workout_sessions ws ON ws.workout_session_id = wsp.workout_session_id '
                . 'JOIN plan_exercises pe ON pe.plan_day_id = wsp.plan_day_id',
            'INSERT INTO workout_sets '
                . '(workout_set_id, workout_session_exercise_id, set_number, weight_kg, reps, created_at) '
                . 'SELECT old.workout_set_id, wse.workout_session_exercise_id, old.set_number, '
                . 'old.weight_kg, old.reps, old.created_at '
                . 'FROM legacy_workout_sets old '
                . 'JOIN legacy_workout_session_plans wsp ON wsp.workout_session_id = old.workout_session_id '
                . 'JOIN legacy_plan_exercises pe ON pe.plan_day_id = wsp.plan_day_id '
                . 'AND pe.exercise_id = old.exercise_id '
                . 'JOIN workout_session_exercises wse ON wse.workout_session_id = old.workout_session_id '
                . 'AND wse.plan_exercise_id = pe.plan_exercise_id',
            "UPDATE workout_sessions SET status = 'completed', ended_at = ("
                . 'SELECT legacy.ended_at FROM legacy_workout_sessions legacy '
                . 'WHERE legacy.workout_session_id = workout_sessions.workout_session_id) '
                . 'WHERE workout_session_id IN (SELECT workout_session_id FROM legacy_workout_sessions '
                . "WHERE status = 'completed')",
        ];

        foreach ($statements as $statement) {
            $pdo->exec($statement);
        }
    }

    private static function dropLegacyTables(PDO $pdo): void
    {
        foreach (array_reverse(self::LEGACY_TABLES) as $table) {
            $pdo->exec("DROP TABLE legacy_{$table}");
        }
    }

    private static function hasTable(PDO $pdo, string $table): bool
    {
        $statement = $pdo->prepare(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name = ?"
        );
        $statement->execute([$table]);
        return (int) $statement->fetchColumn() > 0;
    }

    private static function hasColumn(PDO $pdo, string $table, string $column): bool
    {
        foreach ($pdo->query("PRAGMA table_info({$table})")->fetchAll() as $definition) {
            if (($definition['name'] ?? null) === $column) {
                return true;
            }
        }
        return false;
    }
}
