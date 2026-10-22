<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;

final class PlanGenerator
{
    private const SPLITS = [
        2 => [
            ['全身 A', ['Chest', 'Back', 'Legs', 'Core']],
            ['全身 B', ['Shoulders', 'Glutes', 'Biceps', 'Triceps']],
        ],
        3 => [
            ['Push Day', ['Chest', 'Shoulders', 'Triceps']],
            ['Pull Day', ['Back', 'Biceps', 'Core']],
            ['Leg Day', ['Legs', 'Glutes']],
        ],
        4 => [
            ['Push Day', ['Chest', 'Shoulders', 'Triceps']],
            ['Pull Day', ['Back', 'Biceps']],
            ['Legs + Core', ['Legs', 'Glutes', 'Core']],
            ['偏好部位補強', []],
        ],
        5 => [
            ['Push Day', ['Chest', 'Shoulders', 'Triceps']],
            ['Pull Day', ['Back', 'Biceps']],
            ['Legs + Core', ['Legs', 'Glutes', 'Core']],
            ['上肢補強', ['Chest', 'Back', 'Shoulders', 'Biceps', 'Triceps']],
            ['下肢 + 核心補強', ['Legs', 'Glutes', 'Core']],
        ],
        6 => [
            ['Push A', ['Chest', 'Shoulders', 'Triceps']],
            ['Pull A', ['Back', 'Biceps']],
            ['Legs A', ['Legs', 'Glutes', 'Core']],
            ['Push B', ['Chest', 'Shoulders', 'Triceps']],
            ['Pull B', ['Back', 'Biceps']],
            ['Legs B', ['Legs', 'Glutes', 'Core']],
        ],
    ];

    public static function generate(PDO $pdo, int $userId, ?string $requestedName = null): array
    {
        Database::beginTransaction($pdo);
        try {
            $userSql = 'SELECT u.*, tg.goal_name FROM users u '
                . 'LEFT JOIN training_goals tg ON tg.training_goal_id = u.training_goal_id '
                . 'WHERE u.user_id = ?';
            if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql') {
                $userSql .= ' FOR UPDATE OF u';
            }
            $userStatement = $pdo->prepare($userSql);
            $userStatement->execute([$userId]);
            $user = $userStatement->fetch();
            $required = [
                'age', 'height_cm', 'training_experience', 'training_goal_id',
                'training_days_per_week', 'training_duration_minutes', 'profile_completed_at',
            ];
            if (!$user || array_filter($required, static fn (string $key): bool => empty($user[$key]))) {
                throw new ApiException(422, 'PROFILE_INCOMPLETE', '請先完成個人資料、體重與訓練設定。');
            }

            $weightStatement = $pdo->prepare(
                'SELECT weight_kg, record_date FROM body_records WHERE user_id = ? '
                . 'ORDER BY record_date DESC, body_record_id DESC LIMIT 1'
            );
            $weightStatement->execute([$userId]);
            $weightSnapshot = $weightStatement->fetch();
            if (!$weightSnapshot) {
                throw new ApiException(422, 'WEIGHT_REQUIRED', '目前沒有有效體重，請先補填體重。');
            }

            $preferenceStatement = $pdo->prepare(
                'SELECT ubp.body_part_id, bp.body_part_name, ubp.priority FROM user_body_parts ubp '
                . 'JOIN body_parts bp ON bp.body_part_id = ubp.body_part_id '
                . 'WHERE ubp.user_id = ? ORDER BY ubp.priority'
            );
            $preferenceStatement->execute([$userId]);
            $preferenceRows = $preferenceStatement->fetchAll();
            if ($preferenceRows === []) {
                throw new ApiException(422, 'PROFILE_INCOMPLETE', '請至少選擇一個想加強的身體部位。');
            }
            $preferences = array_column($preferenceRows, 'body_part_name');

            $days = (int) $user['training_days_per_week'];
            $duration = (int) $user['training_duration_minutes'];
            $allBodyParts = $pdo->query('SELECT body_part_name FROM body_parts ORDER BY body_part_id')
                ->fetchAll(PDO::FETCH_COLUMN);
            $split = self::SPLITS[$days] ?? self::SPLITS[3];
            if ($days === 4) {
                $split[3][1] = array_values(array_unique(array_merge($preferences, $allBodyParts)));
            }
            [$sets, $reps, $rest] = self::prescription((string) $user['goal_name']);
            $exerciseLimit = self::exerciseLimit($duration, $sets, $reps, $rest);
            if ($exerciseLimit < 3) {
                throw new ApiException(409, 'PLAN_CONSTRAINT_UNSATISFIED', '每日時間不足以安排至少三個動作。');
            }
            $planName = trim((string) $requestedName);
            if ($planName === '') {
                $planName = $days . ' 天' . self::goalLabel((string) $user['goal_name']) . '訓練計畫';
            }
            if (mb_strlen($planName) > 120) {
                throw new ApiException(422, 'INVALID_PLAN_NAME', '課表名稱不可超過 120 個字。');
            }

            $planId = Database::insert(
                $pdo,
                'INSERT INTO workout_plans (user_id, plan_name) VALUES (?, ?)',
                [$userId, $planName],
                'workout_plan_id'
            );
            $pdo->prepare(
                'INSERT INTO planning_profiles '
                . '(workout_plan_id, training_goal_id, age_snapshot, height_cm_snapshot, weight_kg_snapshot, '
                . 'weight_record_date, experience_snapshot, training_days_per_week, duration_minutes, algorithm_version) '
                . "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'rules-v1')"
            )->execute([
                $planId,
                (int) $user['training_goal_id'],
                (int) $user['age'],
                (float) $user['height_cm'],
                (float) $weightSnapshot['weight_kg'],
                (string) $weightSnapshot['record_date'],
                (string) $user['training_experience'],
                $days,
                $duration,
            ]);
            $profilePart = $pdo->prepare(
                'INSERT INTO planning_profile_body_parts (workout_plan_id, body_part_id, priority) VALUES (?, ?, ?)'
            );
            foreach ($preferenceRows as $preference) {
                $profilePart->execute([$planId, (int) $preference['body_part_id'], (int) $preference['priority']]);
            }

            $coveredBodyParts = [];
            foreach ($split as $dayIndex => [$title, $parts]) {
                $orderedParts = array_values(array_unique(array_merge(
                    array_values(array_intersect($preferences, $parts)),
                    $parts
                )));
                $exercises = self::pickExercises(
                    $pdo,
                    $orderedParts,
                    (string) $user['training_experience'],
                    $exerciseLimit
                );
                if (count($exercises) < min(3, $exerciseLimit)) {
                    throw new ApiException(409, 'PLAN_CONSTRAINT_UNSATISFIED', '可用動作不足，請聯絡管理員新增或啟用動作。');
                }
                $planDayId = Database::insert(
                    $pdo,
                    'INSERT INTO plan_days (workout_plan_id, day_number, day_title) VALUES (?, ?, ?)',
                    [$planId, $dayIndex + 1, '第 ' . ($dayIndex + 1) . ' 天：' . $title],
                    'plan_day_id'
                );
                $insertExercise = $pdo->prepare(
                    'INSERT INTO plan_exercises '
                    . '(plan_day_id, exercise_version_id, exercise_order, target_sets, target_reps, rest_seconds) '
                    . 'VALUES (?, ?, ?, ?, ?, ?)'
                );
                foreach ($exercises as $exerciseIndex => $exercise) {
                    $coveredBodyParts[(string) $exercise['body_part_name']] = true;
                    $insertExercise->execute([
                        $planDayId,
                        (int) $exercise['exercise_version_id'],
                        $exerciseIndex + 1,
                        $sets,
                        $reps,
                        $rest,
                    ]);
                }
            }
            if (array_diff($allBodyParts, array_keys($coveredBodyParts)) !== []) {
                throw new ApiException(409, 'PLAN_CONSTRAINT_UNSATISFIED', '可用動作不足，無法完成八個部位的每週覆蓋。');
            }
            $pdo->commit();
            return self::findPlan($pdo, $userId, $planId);
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }
    }

    public static function createManual(
        PDO $pdo,
        int $userId,
        ?string $requestedName,
        array $requestedDays
    ): array {
        if (count($requestedDays) < 2 || count($requestedDays) > 6) {
            throw new ApiException(422, 'INVALID_PLAN_DAYS', '自訂課表需安排 2 至 6 個訓練日。');
        }

        Database::beginTransaction($pdo);
        try {
            $userSql = 'SELECT u.*, tg.goal_name FROM users u '
                . 'LEFT JOIN training_goals tg ON tg.training_goal_id = u.training_goal_id '
                . 'WHERE u.user_id = ?';
            if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql') {
                $userSql .= ' FOR UPDATE OF u';
            }
            $userStatement = $pdo->prepare($userSql);
            $userStatement->execute([$userId]);
            $user = $userStatement->fetch();
            $required = [
                'age', 'height_cm', 'training_experience', 'training_goal_id',
                'training_duration_minutes', 'profile_completed_at',
            ];
            if (!$user || array_filter($required, static fn (string $key): bool => empty($user[$key]))) {
                throw new ApiException(422, 'PROFILE_INCOMPLETE', '請先完成個人資料、體重與訓練設定。');
            }

            $weightStatement = $pdo->prepare(
                'SELECT weight_kg, record_date FROM body_records WHERE user_id = ? '
                . 'ORDER BY record_date DESC, body_record_id DESC LIMIT 1'
            );
            $weightStatement->execute([$userId]);
            $weightSnapshot = $weightStatement->fetch();
            if (!$weightSnapshot) {
                throw new ApiException(422, 'WEIGHT_REQUIRED', '目前沒有有效體重，請先補填體重。');
            }

            $preferenceStatement = $pdo->prepare(
                'SELECT ubp.body_part_id, bp.body_part_name, ubp.priority FROM user_body_parts ubp '
                . 'JOIN body_parts bp ON bp.body_part_id = ubp.body_part_id '
                . 'WHERE ubp.user_id = ? ORDER BY ubp.priority'
            );
            $preferenceStatement->execute([$userId]);
            $preferenceRows = $preferenceStatement->fetchAll();
            if ($preferenceRows === []) {
                throw new ApiException(422, 'PROFILE_INCOMPLETE', '請至少選擇一個想加強的身體部位。');
            }

            $planName = trim((string) $requestedName);
            if ($planName === '') {
                $planName = '我的自訂訓練課表';
            }
            if (mb_strlen($planName) > 120) {
                throw new ApiException(422, 'INVALID_PLAN_NAME', '課表名稱不可超過 120 個字。');
            }

            $planId = Database::insert(
                $pdo,
                'INSERT INTO workout_plans (user_id, plan_name) VALUES (?, ?)',
                [$userId, $planName],
                'workout_plan_id'
            );
            $pdo->prepare(
                'INSERT INTO planning_profiles '
                . '(workout_plan_id, training_goal_id, age_snapshot, height_cm_snapshot, weight_kg_snapshot, '
                . 'weight_record_date, experience_snapshot, training_days_per_week, duration_minutes, algorithm_version) '
                . "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual-v1')"
            )->execute([
                $planId,
                (int) $user['training_goal_id'],
                (int) $user['age'],
                (float) $user['height_cm'],
                (float) $weightSnapshot['weight_kg'],
                (string) $weightSnapshot['record_date'],
                (string) $user['training_experience'],
                count($requestedDays),
                (int) $user['training_duration_minutes'],
            ]);
            $profilePart = $pdo->prepare(
                'INSERT INTO planning_profile_body_parts (workout_plan_id, body_part_id, priority) VALUES (?, ?, ?)'
            );
            foreach ($preferenceRows as $preference) {
                $profilePart->execute([$planId, (int) $preference['body_part_id'], (int) $preference['priority']]);
            }

            $exerciseVersion = $pdo->prepare(
                'SELECT ev.exercise_version_id FROM exercises e '
                . 'JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
                . 'WHERE e.exercise_id = ? AND e.is_active = TRUE '
                . 'AND ev.version_no = (SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id = e.exercise_id)'
            );
            $insertExercise = $pdo->prepare(
                'INSERT INTO plan_exercises '
                . '(plan_day_id, exercise_version_id, exercise_order, target_sets, target_reps, rest_seconds) '
                . 'VALUES (?, ?, ?, ?, ?, ?)'
            );
            foreach ($requestedDays as $dayIndex => $requestedDay) {
                if (!is_array($requestedDay)
                    || array_diff(array_keys($requestedDay), ['day_title', 'exercises']) !== []) {
                    throw new ApiException(422, 'INVALID_PLAN_DAYS', '自訂訓練日格式不正確。');
                }
                if (!is_string($requestedDay['day_title'] ?? null)) {
                    throw new ApiException(422, 'INVALID_DAY_TITLE', '每個訓練日名稱必須是字串。');
                }
                $dayTitle = trim($requestedDay['day_title']);
                if ($dayTitle === '' || mb_strlen($dayTitle) > 100) {
                    throw new ApiException(422, 'INVALID_DAY_TITLE', '每個訓練日名稱需為 1 至 100 個字。');
                }
                $items = $requestedDay['exercises'] ?? null;
                if (!is_array($items) || count($items) < 1 || count($items) > 10) {
                    throw new ApiException(422, 'INVALID_PLAN_EXERCISES', '每個訓練日需安排 1 至 10 個動作。');
                }
                $planDayId = Database::insert(
                    $pdo,
                    'INSERT INTO plan_days (workout_plan_id, day_number, day_title) VALUES (?, ?, ?)',
                    [$planId, $dayIndex + 1, '第 ' . ($dayIndex + 1) . ' 天：' . $dayTitle],
                    'plan_day_id'
                );
                $seen = [];
                foreach ($items as $exerciseIndex => $item) {
                    if (!is_array($item)
                        || array_diff(array_keys($item), ['exercise_id', 'target_sets', 'target_reps', 'rest_seconds']) !== []) {
                        throw new ApiException(422, 'INVALID_PLAN_EXERCISE', '自訂動作格式不正確。');
                    }
                    $exerciseId = self::integerValue($item['exercise_id'] ?? null);
                    $sets = self::integerValue($item['target_sets'] ?? null);
                    $reps = self::integerValue($item['target_reps'] ?? null);
                    $rest = self::integerValue($item['rest_seconds'] ?? null);
                    if ($exerciseId === null || isset($seen[$exerciseId])
                        || $sets === null || $sets < 1 || $sets > 10
                        || $reps === null || $reps < 1 || $reps > 50
                        || $rest === null || $rest < 0 || $rest > 600) {
                        throw new ApiException(422, 'INVALID_PLAN_EXERCISE', '同一天不可重複動作，且組次或休息時間必須在合法範圍。');
                    }
                    $seen[$exerciseId] = true;
                    $exerciseVersion->execute([$exerciseId]);
                    $exerciseVersionId = $exerciseVersion->fetchColumn();
                    if (!$exerciseVersionId) {
                        throw new ApiException(422, 'INVALID_PLAN_EXERCISE', '自訂課表包含不存在或已停用的動作。');
                    }
                    $insertExercise->execute([
                        $planDayId,
                        (int) $exerciseVersionId,
                        $exerciseIndex + 1,
                        $sets,
                        $reps,
                        $rest,
                    ]);
                }
            }
            $pdo->commit();
            return self::findPlan($pdo, $userId, $planId);
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }
    }

    public static function listPlans(PDO $pdo, int $userId, int $limit = 20, int $offset = 0): array
    {
        $statement = $pdo->prepare(
            'SELECT workout_plan_id FROM workout_plans '
            . 'WHERE user_id = ? AND archived_at IS NULL '
            . 'ORDER BY created_at DESC, workout_plan_id DESC LIMIT ? OFFSET ?'
        );
        $statement->bindValue(1, $userId, PDO::PARAM_INT);
        $statement->bindValue(2, $limit, PDO::PARAM_INT);
        $statement->bindValue(3, $offset, PDO::PARAM_INT);
        $statement->execute();
        return array_map(
            static fn (int|string $id): array => self::findPlan($pdo, $userId, (int) $id),
            $statement->fetchAll(PDO::FETCH_COLUMN)
        );
    }

    public static function findPlan(PDO $pdo, int $userId, int $planId): array
    {
        $statement = $pdo->prepare(
            'SELECT wp.*, pp.training_goal_id, pp.age_snapshot, pp.height_cm_snapshot, '
            . 'pp.weight_kg_snapshot, pp.weight_record_date, pp.experience_snapshot, '
            . 'pp.training_days_per_week, pp.duration_minutes, pp.algorithm_version, pp.captured_at, '
            . 'tg.goal_name FROM workout_plans wp '
            . 'JOIN planning_profiles pp ON pp.workout_plan_id = wp.workout_plan_id '
            . 'JOIN training_goals tg ON tg.training_goal_id = pp.training_goal_id '
            . 'WHERE wp.workout_plan_id = ? AND wp.user_id = ?'
        );
        $statement->execute([$planId, $userId]);
        $plan = $statement->fetch();
        if (!$plan) {
            throw new ApiException(404, 'PLAN_NOT_FOUND', '找不到這份課表。');
        }
        $dayStatement = $pdo->prepare('SELECT * FROM plan_days WHERE workout_plan_id = ? ORDER BY day_number');
        $dayStatement->execute([$planId]);
        $days = $dayStatement->fetchAll();
        $exerciseStatement = $pdo->prepare(
            'SELECT pe.*, ev.exercise_id, ev.version_no, ev.exercise_name, ev.difficulty_level, '
            . 'ev.equipment, ev.description, ev.image_url, bp.body_part_name '
            . 'FROM plan_exercises pe '
            . 'JOIN exercise_versions ev ON ev.exercise_version_id = pe.exercise_version_id '
            . 'JOIN exercises e ON e.exercise_id = ev.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE pe.plan_day_id = ? ORDER BY pe.exercise_order'
        );
        foreach ($days as &$day) {
            $exerciseStatement->execute([(int) $day['plan_day_id']]);
            $day['exercises'] = $exerciseStatement->fetchAll();
            $day['estimated_seconds'] = self::estimatedSeconds($day['exercises']);
        }
        unset($day);
        $plan['days'] = $days;
        return $plan;
    }

    private static function pickExercises(
        PDO $pdo,
        array $parts,
        string $experience,
        int $limit
    ): array
    {
        $rank = ['Beginner' => 1, 'Intermediate' => 2, 'Advanced' => 3][$experience] ?? 1;
        $placeholders = implode(',', array_fill(0, count($parts), '?'));
        $query = 'SELECT e.exercise_id, ev.exercise_version_id, ev.exercise_name, ev.difficulty_level, '
            . 'ev.equipment, ev.description, ev.image_url, bp.body_part_name FROM exercises e '
            . 'JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . "WHERE e.is_active = TRUE AND bp.body_part_name IN ({$placeholders}) "
            . 'AND ev.version_no = (SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id = e.exercise_id) '
            . "AND CASE ev.difficulty_level WHEN 'Beginner' THEN 1 WHEN 'Intermediate' THEN 2 ELSE 3 END <= ? "
            . "ORDER BY CASE ev.difficulty_level WHEN 'Beginner' THEN 1 WHEN 'Intermediate' THEN 2 ELSE 3 END, e.exercise_id"
            . ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql' ? ' FOR SHARE OF e, ev' : '');
        $statement = $pdo->prepare($query);
        $statement->execute([...$parts, $rank]);
        $rows = $statement->fetchAll();
        if ($rows === []) {
            return [];
        }
        $grouped = [];
        foreach ($rows as $row) {
            $grouped[$row['body_part_name']][] = $row;
        }
        $picked = [];
        $seen = [];
        foreach ($parts as $part) {
            if (count($picked) >= $limit) {
                break;
            }
            $candidate = $grouped[$part][0] ?? null;
            if ($candidate !== null) {
                $picked[] = $candidate;
                $seen[(int) $candidate['exercise_id']] = true;
            }
        }
        $cursor = 1;
        while (count($picked) < $limit) {
            $added = false;
            foreach ($parts as $part) {
                $items = $grouped[$part] ?? [];
                if (!isset($items[$cursor])) {
                    continue;
                }
                $candidate = $items[$cursor];
                if (!isset($seen[(int) $candidate['exercise_id']])) {
                    $picked[] = $candidate;
                    $seen[(int) $candidate['exercise_id']] = true;
                    $added = true;
                    if (count($picked) >= $limit) {
                        break 2;
                    }
                }
            }
            $cursor++;
            if (!$added) {
                break;
            }
        }
        return $picked;
    }

    private static function integerValue(mixed $value): ?int
    {
        if (is_int($value)) {
            return $value;
        }
        if (!is_string($value) || !preg_match('/^\d+$/', $value)) {
            return null;
        }
        return (int) $value;
    }

    private static function prescription(string $goal): array
    {
        return match ($goal) {
            'Strength' => [4, 5, 120],
            'Fat Loss' => [3, 12, 45],
            'General Fitness' => [2, 12, 45],
            default => [3, 10, 60],
        };
    }

    private static function exerciseLimit(int $durationMinutes, int $sets, int $reps, int $rest): int
    {
        for ($count = 6; $count >= 3; $count--) {
            $seconds = 300
                + $count * ($sets * $reps * 3 + ($sets - 1) * $rest)
                + ($count - 1) * 60;
            if ($seconds <= $durationMinutes * 60) {
                return $count;
            }
        }
        return 0;
    }

    private static function estimatedSeconds(array $exercises): int
    {
        if ($exercises === []) {
            return 0;
        }
        $seconds = 300 + (count($exercises) - 1) * 60;
        foreach ($exercises as $exercise) {
            $sets = (int) $exercise['target_sets'];
            $seconds += $sets * (int) $exercise['target_reps'] * 3
                + ($sets - 1) * (int) $exercise['rest_seconds'];
        }
        return $seconds;
    }

    private static function goalLabel(string $goal): string
    {
        return match ($goal) {
            'Strength' => '力量',
            'Fat Loss' => '減脂',
            'General Fitness' => '一般健身',
            default => '增肌',
        };
    }
}
