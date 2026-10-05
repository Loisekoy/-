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
            ['Pull Day', ['Back', 'Biceps']],
            ['Legs + Core', ['Legs', 'Glutes', 'Core']],
        ],
        4 => [
            ['胸 + 三頭', ['Chest', 'Triceps']],
            ['背 + 二頭', ['Back', 'Biceps']],
            ['腿 + 臀', ['Legs', 'Glutes']],
            ['肩 + 核心', ['Shoulders', 'Core']],
        ],
        5 => [
            ['胸部', ['Chest', 'Triceps']],
            ['背部', ['Back', 'Biceps']],
            ['腿部', ['Legs', 'Glutes']],
            ['肩部', ['Shoulders', 'Core']],
            ['偏好加強', ['Chest', 'Back', 'Legs', 'Core']],
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
        $userStatement = $pdo->prepare(
            'SELECT u.*, tg.goal_name FROM users u '
            . 'LEFT JOIN training_goals tg ON tg.training_goal_id = u.training_goal_id '
            . 'WHERE u.user_id = ?'
        );
        $userStatement->execute([$userId]);
        $user = $userStatement->fetch();
        $required = [
            'age', 'height_cm', 'training_experience', 'training_goal_id',
            'training_days_per_week', 'training_duration_minutes',
        ];
        if (!$user || array_filter($required, static fn (string $key): bool => empty($user[$key]))) {
            throw new ApiException(422, 'PROFILE_INCOMPLETE', '請先完成個人資料與訓練設定。');
        }

        $preferenceStatement = $pdo->prepare(
            'SELECT bp.body_part_name FROM user_body_parts ubp '
            . 'JOIN body_parts bp ON bp.body_part_id = ubp.body_part_id '
            . 'WHERE ubp.user_id = ? ORDER BY ubp.priority'
        );
        $preferenceStatement->execute([$userId]);
        $preferences = $preferenceStatement->fetchAll(PDO::FETCH_COLUMN);
        if ($preferences === []) {
            throw new ApiException(422, 'PROFILE_INCOMPLETE', '請至少選擇一個想加強的身體部位。');
        }

        $days = (int) $user['training_days_per_week'];
        $duration = (int) $user['training_duration_minutes'];
        $split = self::SPLITS[$days] ?? self::SPLITS[3];
        if ($days === 5) {
            $split[4][1] = array_values(array_unique(array_merge($preferences, $split[4][1])));
        }
        $exerciseLimit = $duration === 30 ? 3 : ($duration === 60 ? 5 : 6);
        [$sets, $reps, $rest] = self::prescription((string) $user['goal_name']);
        $planName = trim((string) $requestedName);
        if ($planName === '') {
            $planName = $days . ' 天' . self::goalLabel((string) $user['goal_name']) . '訓練計畫';
        }
        if (mb_strlen($planName) > 120) {
            throw new ApiException(422, 'INVALID_PLAN_NAME', '課表名稱不可超過 120 個字。');
        }

        $pdo->beginTransaction();
        try {
            $planId = Database::insert(
                $pdo,
                'INSERT INTO workout_plans '
                . '(user_id, plan_name, training_goal_id, experience_snapshot, duration_minutes) '
                . 'VALUES (?, ?, ?, ?, ?)',
                [$userId, $planName, (int) $user['training_goal_id'], $user['training_experience'], $duration],
                'workout_plan_id'
            );

            foreach ($split as $dayIndex => [$title, $parts]) {
                $orderedParts = array_values(array_unique(array_merge(
                    array_values(array_intersect($preferences, $parts)),
                    $parts
                )));
                $exercises = self::pickExercises(
                    $pdo,
                    $orderedParts,
                    (string) $user['training_experience'],
                    $exerciseLimit,
                    $dayIndex
                );
                if (count($exercises) < min(3, $exerciseLimit)) {
                    throw new ApiException(
                        409,
                        'PLAN_CONSTRAINT_UNSATISFIED',
                        '可用動作不足，請聯絡管理員新增或啟用動作。'
                    );
                }

                $planDayId = Database::insert(
                    $pdo,
                    'INSERT INTO plan_days (workout_plan_id, day_number, day_title) VALUES (?, ?, ?)',
                    [$planId, $dayIndex + 1, '第 ' . ($dayIndex + 1) . ' 天：' . $title],
                    'plan_day_id'
                );
                $insertExercise = $pdo->prepare(
                    'INSERT INTO plan_exercises '
                    . '(plan_day_id, exercise_id, exercise_order, target_sets, target_reps, rest_seconds) '
                    . 'VALUES (?, ?, ?, ?, ?, ?)'
                );
                foreach ($exercises as $exerciseIndex => $exercise) {
                    $insertExercise->execute([
                        $planDayId,
                        (int) $exercise['exercise_id'],
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

    public static function listPlans(PDO $pdo, int $userId): array
    {
        $statement = $pdo->prepare(
            'SELECT workout_plan_id FROM workout_plans WHERE user_id = ? ORDER BY created_at DESC, workout_plan_id DESC'
        );
        $statement->execute([$userId]);
        return array_map(
            static fn (int|string $id): array => self::findPlan($pdo, $userId, (int) $id),
            $statement->fetchAll(PDO::FETCH_COLUMN)
        );
    }

    public static function findPlan(PDO $pdo, int $userId, int $planId): array
    {
        $statement = $pdo->prepare(
            'SELECT wp.*, tg.goal_name FROM workout_plans wp '
            . 'JOIN training_goals tg ON tg.training_goal_id = wp.training_goal_id '
            . 'WHERE wp.workout_plan_id = ? AND wp.user_id = ?'
        );
        $statement->execute([$planId, $userId]);
        $plan = $statement->fetch();
        if (!$plan) {
            throw new ApiException(404, 'PLAN_NOT_FOUND', '找不到這份課表。');
        }
        $dayStatement = $pdo->prepare(
            'SELECT * FROM plan_days WHERE workout_plan_id = ? ORDER BY day_number'
        );
        $dayStatement->execute([$planId]);
        $days = $dayStatement->fetchAll();
        $exerciseStatement = $pdo->prepare(
            'SELECT pe.*, e.exercise_name, e.equipment, e.description, e.image_url, '
            . 'bp.body_part_name FROM plan_exercises pe '
            . 'JOIN exercises e ON e.exercise_id = pe.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE pe.plan_day_id = ? ORDER BY pe.exercise_order'
        );
        foreach ($days as &$day) {
            $exerciseStatement->execute([(int) $day['plan_day_id']]);
            $day['exercises'] = $exerciseStatement->fetchAll();
        }
        unset($day);
        $plan['days'] = $days;
        return $plan;
    }

    private static function pickExercises(
        PDO $pdo,
        array $parts,
        string $experience,
        int $limit,
        int $rotation
    ): array {
        $rank = ['Beginner' => 1, 'Intermediate' => 2, 'Advanced' => 3][$experience] ?? 1;
        $placeholders = implode(',', array_fill(0, count($parts), '?'));
        $query = 'SELECT e.*, bp.body_part_name FROM exercises e '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . "WHERE e.is_active = TRUE AND bp.body_part_name IN ({$placeholders}) "
            . "AND CASE e.difficulty_level WHEN 'Beginner' THEN 1 WHEN 'Intermediate' THEN 2 ELSE 3 END <= ? "
            . 'ORDER BY bp.body_part_id, e.exercise_id';
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
        $cursor = $rotation;
        while (count($picked) < $limit) {
            $added = false;
            foreach ($parts as $part) {
                $items = $grouped[$part] ?? [];
                if ($items === []) {
                    continue;
                }
                $candidate = $items[$cursor % count($items)];
                $ids = array_column($picked, 'exercise_id');
                if (!in_array($candidate['exercise_id'], $ids, true)) {
                    $picked[] = $candidate;
                    $added = true;
                    if (count($picked) >= $limit) {
                        break 2;
                    }
                }
            }
            $cursor++;
            if (!$added || $cursor > $rotation + 10) {
                break;
            }
        }
        return $picked;
    }

    private static function prescription(string $goal): array
    {
        return match ($goal) {
            'Strength' => [5, 5, 120],
            'Fat Loss' => [3, 15, 45],
            'General Fitness' => [3, 12, 60],
            default => [3, 10, 60],
        };
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
