<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;

final class Api
{
    private const DATABASE_TABLES = [
        'users',
        'user_auth',
        'user_sessions',
        'admins',
        'training_goals',
        'body_parts',
        'user_body_parts',
        'exercises',
        'workout_plans',
        'plan_days',
        'plan_exercises',
        'workout_sessions',
        'workout_sets',
        'body_records',
        'workout_session_plans',
    ];

    private const DATABASE_RELATIONSHIPS = [
        ['user_auth', 'user_id', 'users', 'user_id', 'User 1:1 User_Auth', 'CASCADE'],
        ['user_sessions', 'auth_id', 'user_auth', 'auth_id', 'User_Auth 1:N User_Session', 'CASCADE'],
        ['admins', 'user_id', 'users', 'user_id', 'User 1:0..1 Admin', 'CASCADE'],
        ['users', 'training_goal_id', 'training_goals', 'training_goal_id', 'Training_Goal 1:N User', 'RESTRICT'],
        ['user_body_parts', 'user_id', 'users', 'user_id', 'User 1:N User_Body_Part', 'CASCADE'],
        ['user_body_parts', 'body_part_id', 'body_parts', 'body_part_id', 'User M:N Body_Part', 'RESTRICT'],
        ['exercises', 'body_part_id', 'body_parts', 'body_part_id', 'Body_Part 1:N Exercise', 'RESTRICT'],
        ['workout_plans', 'user_id', 'users', 'user_id', 'User 1:N Workout_Plan', 'CASCADE'],
        ['workout_plans', 'training_goal_id', 'training_goals', 'training_goal_id', 'Training_Goal 1:N Workout_Plan', 'RESTRICT'],
        ['plan_days', 'workout_plan_id', 'workout_plans', 'workout_plan_id', 'Workout_Plan 1:N Plan_Day', 'CASCADE'],
        ['plan_exercises', 'plan_day_id', 'plan_days', 'plan_day_id', 'Plan_Day 1:N Plan_Exercise', 'CASCADE'],
        ['plan_exercises', 'exercise_id', 'exercises', 'exercise_id', 'Exercise 1:N Plan_Exercise', 'RESTRICT'],
        ['workout_sessions', 'user_id', 'users', 'user_id', 'User 1:N Workout_Session', 'CASCADE'],
        ['workout_sets', 'workout_session_id', 'workout_sessions', 'workout_session_id', 'Workout_Session 1:N Workout_Set', 'CASCADE'],
        ['workout_sets', 'exercise_id', 'exercises', 'exercise_id', 'Exercise 1:N Workout_Set', 'RESTRICT'],
        ['body_records', 'user_id', 'users', 'user_id', 'User 1:N Body_Record', 'CASCADE'],
        ['workout_session_plans', 'workout_session_id', 'workout_sessions', 'workout_session_id', 'Workout_Session 1:1 Session_Plan', 'CASCADE'],
        ['workout_session_plans', 'plan_day_id', 'plan_days', 'plan_day_id', 'Plan_Day 1:N Session_Plan', 'CASCADE'],
    ];

    public function __construct(private readonly PDO $pdo)
    {
    }

    public function dispatch(string $method, string $path): array
    {
        $path = '/' . trim($path, '/');
        $input = $this->input();

        if ($method === 'GET' && $path === '/health') {
            return [200, [
                'status' => 'ok',
                'database' => Database::driver(),
                'tables' => $this->tableCount(),
            ]];
        }
        if ($method === 'POST' && $path === '/auth/register') {
            return [201, Auth::register($this->pdo, $input)];
        }
        if ($method === 'POST' && $path === '/auth/login') {
            return [200, Auth::login($this->pdo, $input)];
        }

        $user = Auth::user($this->pdo, $this->bearerToken());
        if ($method === 'POST' && $path === '/auth/logout') {
            Auth::logout($this->pdo, $user);
            return [204, null];
        }
        if ($method === 'PATCH' && $path === '/auth/password') {
            Auth::changePassword($this->pdo, $user, $input);
            return [204, null];
        }
        if ($method === 'POST' && $path === '/auth/deactivate') {
            Auth::deactivate($this->pdo, $user, $input);
            return [204, null];
        }
        if ($method === 'GET' && $path === '/reference') {
            return [200, $this->reference()];
        }
        if ($method === 'GET' && $path === '/me') {
            return [200, $this->profile((int) $user['user_id'])];
        }
        if ($method === 'PUT' && $path === '/me/profile') {
            return [200, $this->updateProfile((int) $user['user_id'], $input)];
        }
        if ($method === 'PUT' && $path === '/me/training-settings') {
            return [200, $this->updateTrainingSettings((int) $user['user_id'], $input)];
        }
        if ($method === 'PUT' && $path === '/me/body-parts') {
            return [200, $this->updateBodyParts((int) $user['user_id'], $input)];
        }
        if ($method === 'GET' && $path === '/exercises') {
            return [200, $this->exercises()];
        }
        if (preg_match('#^/exercises/(\d+)/history$#', $path, $matches) && $method === 'GET') {
            return [200, $this->exerciseHistory((int) $user['user_id'], (int) $matches[1])];
        }
        if ($method === 'GET' && $path === '/plans') {
            return [200, ['items' => PlanGenerator::listPlans($this->pdo, (int) $user['user_id'])]];
        }
        if ($method === 'GET' && $path === '/ai/status') {
            return [200, AiPlanGenerator::status()];
        }
        if (preg_match('#^/plans/(\d+)$#', $path, $matches) && $method === 'GET') {
            return [200, PlanGenerator::findPlan(
                $this->pdo,
                (int) $user['user_id'],
                (int) $matches[1]
            )];
        }
        if ($method === 'POST' && $path === '/plans/generate') {
            return [201, PlanGenerator::generate(
                $this->pdo,
                (int) $user['user_id'],
                isset($input['plan_name']) ? (string) $input['plan_name'] : null
            )];
        }
        if ($method === 'POST' && $path === '/plans/ai-generate') {
            return [201, AiPlanGenerator::generate(
                $this->pdo,
                (int) $user['user_id'],
                isset($input['plan_name']) ? (string) $input['plan_name'] : null,
                isset($input['focus']) ? (string) $input['focus'] : null
            )];
        }
        if (preg_match('#^/plans/(\d+)$#', $path, $matches) && $method === 'PATCH') {
            return [200, $this->updatePlan((int) $user['user_id'], (int) $matches[1], $input)];
        }
        if (preg_match('#^/plans/(\d+)$#', $path, $matches) && $method === 'DELETE') {
            $this->deletePlan((int) $user['user_id'], (int) $matches[1]);
            return [204, null];
        }
        if ($method === 'GET' && $path === '/workout-sessions/current') {
            return [200, $this->currentSession((int) $user['user_id'])];
        }
        if ($method === 'POST' && $path === '/workout-sessions') {
            return $this->startSession((int) $user['user_id'], $input);
        }
        if ($method === 'GET' && $path === '/workout-sessions') {
            return [200, $this->history((int) $user['user_id'])];
        }
        if (preg_match('#^/workout-sessions/(\d+)$#', $path, $matches) && $method === 'GET') {
            return [200, $this->sessionDetail((int) $user['user_id'], (int) $matches[1])];
        }
        if (preg_match('#^/workout-sessions/(\d+)/sets$#', $path, $matches) && $method === 'POST') {
            return $this->saveSet((int) $user['user_id'], (int) $matches[1], $input);
        }
        if (preg_match('#^/workout-sessions/(\d+)/(complete|cancel)$#', $path, $matches) && $method === 'POST') {
            return [200, $this->finishSession(
                (int) $user['user_id'],
                (int) $matches[1],
                $matches[2] === 'complete' ? 'completed' : 'cancelled',
                (string) ($input['notes'] ?? '')
            )];
        }
        if (preg_match('#^/workout-sessions/(\d+)$#', $path, $matches) && $method === 'DELETE') {
            $this->deleteSession((int) $user['user_id'], (int) $matches[1]);
            return [204, null];
        }
        if (preg_match('#^/workout-sets/(\d+)$#', $path, $matches) && $method === 'PATCH') {
            return [200, $this->updateSet((int) $user['user_id'], (int) $matches[1], $input)];
        }
        if (preg_match('#^/workout-sets/(\d+)$#', $path, $matches) && $method === 'DELETE') {
            $this->deleteSet((int) $user['user_id'], (int) $matches[1]);
            return [204, null];
        }
        if ($method === 'GET' && $path === '/dashboard') {
            return [200, $this->dashboard((int) $user['user_id'])];
        }
        if ($method === 'GET' && $path === '/body-records') {
            return [200, $this->bodyRecords((int) $user['user_id'])];
        }
        if ($method === 'POST' && $path === '/body-records') {
            return [201, $this->createBodyRecord((int) $user['user_id'], $input)];
        }
        if (preg_match('#^/body-records/(\d+)$#', $path, $matches) && $method === 'DELETE') {
            $this->deleteBodyRecord((int) $user['user_id'], (int) $matches[1]);
            return [204, null];
        }
        if (preg_match('#^/body-records/(\d+)$#', $path, $matches) && $method === 'PATCH') {
            return [200, $this->updateBodyRecord((int) $user['user_id'], (int) $matches[1], $input)];
        }

        if (str_starts_with($path, '/admin/')) {
            $this->requireAdmin($user);
            if ($method === 'GET' && $path === '/admin/statistics') {
                return [200, $this->adminStatistics()];
            }
            if ($method === 'GET' && $path === '/admin/users') {
                return [200, $this->adminUsers()];
            }
            if ($method === 'GET' && $path === '/admin/exercises') {
                return [200, $this->adminExercises()];
            }
            if ($method === 'GET' && $path === '/admin/database/overview') {
                return [200, $this->databaseOverview()];
            }
            if (preg_match('#^/admin/database/tables/([a-z_]+)$#', $path, $matches)
                && $method === 'GET') {
                return [200, $this->databaseTable($matches[1])];
            }
            if ($method === 'POST' && $path === '/admin/exercises') {
                return [201, $this->createExercise($input)];
            }
            if (preg_match('#^/admin/exercises/(\d+)$#', $path, $matches) && $method === 'PATCH') {
                return [200, $this->updateExercise((int) $matches[1], $input)];
            }
            if (preg_match('#^/admin/exercises/(\d+)$#', $path, $matches) && $method === 'DELETE') {
                $this->deleteExercise((int) $matches[1]);
                return [204, null];
            }
            if (preg_match('#^/admin/(training-goals|body-parts)/(\d+)$#', $path, $matches) && $method === 'PATCH') {
                return [200, $this->updateReference($matches[1], (int) $matches[2], $input)];
            }
        }

        throw new ApiException(404, 'NOT_FOUND', '找不到這個 API。');
    }

    private function reference(): array
    {
        return [
            'training_goals' => $this->pdo->query(
                'SELECT * FROM training_goals ORDER BY training_goal_id'
            )->fetchAll(),
            'body_parts' => $this->pdo->query(
                'SELECT * FROM body_parts ORDER BY body_part_id'
            )->fetchAll(),
        ];
    }

    private function profile(int $userId): array
    {
        $statement = $this->pdo->prepare(
            'SELECT u.*, ua.email, tg.goal_name, '
            . 'CASE WHEN a.user_id IS NULL THEN 0 ELSE 1 END AS is_admin '
            . 'FROM users u JOIN user_auth ua ON ua.user_id = u.user_id '
            . 'LEFT JOIN training_goals tg ON tg.training_goal_id = u.training_goal_id '
            . 'LEFT JOIN admins a ON a.user_id = u.user_id WHERE u.user_id = ?'
        );
        $statement->execute([$userId]);
        $profile = $statement->fetch();
        if (!$profile) {
            throw new ApiException(404, 'USER_NOT_FOUND', '找不到使用者。');
        }
        $parts = $this->pdo->prepare(
            'SELECT bp.body_part_id, bp.body_part_name, ubp.priority '
            . 'FROM user_body_parts ubp JOIN body_parts bp ON bp.body_part_id = ubp.body_part_id '
            . 'WHERE ubp.user_id = ? ORDER BY ubp.priority'
        );
        $parts->execute([$userId]);
        $weight = $this->pdo->prepare(
            'SELECT weight_kg FROM body_records WHERE user_id = ? '
            . 'ORDER BY record_date DESC, body_record_id DESC LIMIT 1'
        );
        $weight->execute([$userId]);
        $profile['preferred_body_parts'] = $parts->fetchAll();
        $profile['current_weight_kg'] = $weight->fetchColumn() ?: null;
        $profile['profile_complete'] = $profile['age'] !== null
            && $profile['height_cm'] !== null
            && $profile['training_experience'] !== null
            && $profile['training_goal_id'] !== null
            && $profile['training_days_per_week'] !== null
            && $profile['training_duration_minutes'] !== null
            && $profile['preferred_body_parts'] !== [];
        return $profile;
    }

    private function updateProfile(int $userId, array $input): array
    {
        $name = trim((string) ($input['name'] ?? ''));
        $gender = $input['gender'] ?? null;
        $age = filter_var($input['age'] ?? null, FILTER_VALIDATE_INT);
        $height = filter_var($input['height_cm'] ?? null, FILTER_VALIDATE_FLOAT);
        $experience = (string) ($input['training_experience'] ?? '');
        $weight = filter_var($input['weight_kg'] ?? null, FILTER_VALIDATE_FLOAT);

        if ($name === '' || mb_strlen($name) > 100) {
            throw new ApiException(422, 'INVALID_NAME', '姓名需為 1 至 100 個字。');
        }
        if (!in_array($gender, ['Female', 'Male', 'Other', null, ''], true)) {
            throw new ApiException(422, 'INVALID_GENDER', '性別選項不正確。');
        }
        if ($age === false || $age < 13 || $age > 100) {
            throw new ApiException(422, 'INVALID_AGE', '年齡需介於 13 到 100 歲。');
        }
        if ($height === false || $height < 100 || $height > 250) {
            throw new ApiException(422, 'INVALID_HEIGHT', '身高需介於 100 到 250 公分。');
        }
        if (!in_array($experience, ['Beginner', 'Intermediate', 'Advanced'], true)) {
            throw new ApiException(422, 'INVALID_EXPERIENCE', '訓練程度不正確。');
        }
        if ($weight === false || $weight < 20 || $weight > 500) {
            throw new ApiException(422, 'INVALID_WEIGHT', '體重需介於 20 到 500 公斤。');
        }

        $this->pdo->beginTransaction();
        try {
            $this->pdo->prepare(
                'UPDATE users SET name = ?, gender = ?, age = ?, height_cm = ?, training_experience = ? '
                . 'WHERE user_id = ?'
            )->execute([$name, $gender ?: null, $age, $height, $experience, $userId]);
            $this->upsertTodayWeight($userId, (float) $weight);
            $this->pdo->commit();
            return $this->profile($userId);
        } catch (\Throwable $error) {
            $this->pdo->rollBack();
            throw $error;
        }
    }

    private function updateTrainingSettings(int $userId, array $input): array
    {
        $goalId = filter_var($input['training_goal_id'] ?? null, FILTER_VALIDATE_INT);
        $days = filter_var($input['training_days_per_week'] ?? null, FILTER_VALIDATE_INT);
        $duration = filter_var($input['training_duration_minutes'] ?? null, FILTER_VALIDATE_INT);
        if ($goalId === false || $days === false || $duration === false
            || $days < 2 || $days > 6 || !in_array($duration, [30, 60, 90], true)) {
            throw new ApiException(422, 'INVALID_TRAINING_SETTINGS', '訓練目標、天數或時間不正確。');
        }
        $goal = $this->pdo->prepare('SELECT 1 FROM training_goals WHERE training_goal_id = ?');
        $goal->execute([$goalId]);
        if (!$goal->fetchColumn()) {
            throw new ApiException(422, 'INVALID_TRAINING_GOAL', '訓練目標不存在。');
        }
        $this->pdo->prepare(
            'UPDATE users SET training_goal_id = ?, training_days_per_week = ?, '
            . 'training_duration_minutes = ? WHERE user_id = ?'
        )->execute([$goalId, $days, $duration, $userId]);
        return $this->profile($userId);
    }

    private function updateBodyParts(int $userId, array $input): array
    {
        $ids = $input['body_part_ids'] ?? null;
        if (!is_array($ids) || count($ids) < 1 || count($ids) > 8) {
            throw new ApiException(422, 'INVALID_BODY_PARTS', '請選擇 1 到 8 個部位。');
        }
        $ids = array_map('intval', $ids);
        if (count(array_unique($ids)) !== count($ids)) {
            throw new ApiException(422, 'DUPLICATE_BODY_PARTS', '身體部位不可重複。');
        }
        $placeholders = implode(',', array_fill(0, count($ids), '?'));
        $statement = $this->pdo->prepare(
            "SELECT COUNT(*) FROM body_parts WHERE body_part_id IN ({$placeholders})"
        );
        $statement->execute($ids);
        if ((int) $statement->fetchColumn() !== count($ids)) {
            throw new ApiException(422, 'INVALID_BODY_PARTS', '包含不存在的身體部位。');
        }

        $this->pdo->beginTransaction();
        try {
            $this->pdo->prepare('DELETE FROM user_body_parts WHERE user_id = ?')->execute([$userId]);
            $insert = $this->pdo->prepare(
                'INSERT INTO user_body_parts (user_id, body_part_id, priority) VALUES (?, ?, ?)'
            );
            foreach ($ids as $index => $bodyPartId) {
                $insert->execute([$userId, $bodyPartId, $index + 1]);
            }
            $this->pdo->commit();
            return $this->profile($userId);
        } catch (\Throwable $error) {
            $this->pdo->rollBack();
            throw $error;
        }
    }

    private function exercises(): array
    {
        $where = ['e.is_active = TRUE'];
        $params = [];
        $query = trim((string) ($_GET['q'] ?? ''));
        $partId = filter_var($_GET['body_part_id'] ?? null, FILTER_VALIDATE_INT);
        $difficulty = trim((string) ($_GET['difficulty_level'] ?? ''));
        if ($query !== '') {
            $where[] = '(LOWER(e.exercise_name) LIKE LOWER(?) OR LOWER(e.equipment) LIKE LOWER(?))';
            $params[] = '%' . $query . '%';
            $params[] = '%' . $query . '%';
        }
        if ($partId !== false && $partId !== null) {
            $where[] = 'e.body_part_id = ?';
            $params[] = $partId;
        }
        if (in_array($difficulty, ['Beginner', 'Intermediate', 'Advanced'], true)) {
            $where[] = 'e.difficulty_level = ?';
            $params[] = $difficulty;
        }
        $statement = $this->pdo->prepare(
            'SELECT e.*, bp.body_part_name FROM exercises e '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE ' . implode(' AND ', $where)
            . ' ORDER BY bp.body_part_id, e.exercise_id LIMIT 100'
        );
        $statement->execute($params);
        $items = $statement->fetchAll();
        return ['items' => $items, 'page' => 1, 'page_size' => count($items), 'total' => count($items)];
    }

    private function updatePlan(int $userId, int $planId, array $input): array
    {
        $plan = PlanGenerator::findPlan($this->pdo, $userId, $planId);
        $this->assertPlanNotActive($userId, $planId);
        $planName = array_key_exists('plan_name', $input)
            ? trim((string) $input['plan_name'])
            : (string) $plan['plan_name'];
        if ($planName === '' || mb_strlen($planName) > 120) {
            throw new ApiException(422, 'INVALID_PLAN_NAME', '課表名稱需為 1 至 120 個字。');
        }
        $items = $input['exercises'] ?? [];
        if (!is_array($items)) {
            throw new ApiException(422, 'INVALID_EXERCISES', '課表動作格式不正確。');
        }

        $this->pdo->beginTransaction();
        try {
            $this->pdo->prepare(
                'UPDATE workout_plans SET plan_name = ? WHERE workout_plan_id = ? AND user_id = ?'
            )->execute([$planName, $planId, $userId]);
            $ownership = $this->pdo->prepare(
                'SELECT pe.plan_exercise_id FROM plan_exercises pe '
                . 'JOIN plan_days pd ON pd.plan_day_id = pe.plan_day_id '
                . 'JOIN workout_plans wp ON wp.workout_plan_id = pd.workout_plan_id '
                . 'WHERE pe.plan_exercise_id = ? AND wp.workout_plan_id = ? AND wp.user_id = ?'
            );
            $exerciseExists = $this->pdo->prepare(
                'SELECT 1 FROM exercises WHERE exercise_id = ? AND is_active = TRUE'
            );
            $update = $this->pdo->prepare(
                'UPDATE plan_exercises SET exercise_id = ?, target_sets = ?, target_reps = ?, '
                . 'rest_seconds = ? WHERE plan_exercise_id = ?'
            );
            $seen = [];
            foreach ($items as $item) {
                if (!is_array($item)) {
                    throw new ApiException(422, 'INVALID_EXERCISES', '課表動作格式不正確。');
                }
                $planExerciseId = (int) ($item['plan_exercise_id'] ?? 0);
                if ($planExerciseId <= 0 || in_array($planExerciseId, $seen, true)) {
                    throw new ApiException(422, 'INVALID_EXERCISES', '課表動作不可缺漏或重複。');
                }
                $seen[] = $planExerciseId;
                $ownership->execute([$planExerciseId, $planId, $userId]);
                if (!$ownership->fetchColumn()) {
                    throw new ApiException(404, 'PLAN_EXERCISE_NOT_FOUND', '找不到課表中的動作。');
                }
                $exerciseId = (int) ($item['exercise_id'] ?? 0);
                $sets = (int) ($item['target_sets'] ?? 0);
                $reps = (int) ($item['target_reps'] ?? 0);
                $rest = (int) ($item['rest_seconds'] ?? -1);
                $exerciseExists->execute([$exerciseId]);
                if (!$exerciseExists->fetchColumn() || $sets < 1 || $sets > 10
                    || $reps < 1 || $reps > 50 || $rest < 0 || $rest > 300) {
                    throw new ApiException(422, 'INVALID_PLAN_EXERCISE', '課表動作、組次或休息時間不正確。');
                }
                $update->execute([$exerciseId, $sets, $reps, $rest, $planExerciseId]);
            }
            $this->pdo->commit();
            return PlanGenerator::findPlan($this->pdo, $userId, $planId);
        } catch (\Throwable $error) {
            $this->pdo->rollBack();
            throw $error;
        }
    }

    private function exerciseHistory(int $userId, int $exerciseId): array
    {
        $statement = $this->pdo->prepare(
            'SELECT wset.*, ws.started_at, ws.status, e.exercise_name '
            . 'FROM workout_sets wset '
            . 'JOIN workout_sessions ws ON ws.workout_session_id = wset.workout_session_id '
            . 'JOIN exercises e ON e.exercise_id = wset.exercise_id '
            . 'WHERE ws.user_id = ? AND wset.exercise_id = ? '
            . 'ORDER BY ws.started_at DESC, wset.set_number'
        );
        $statement->execute([$userId, $exerciseId]);
        $items = $statement->fetchAll();
        return ['items' => $items, 'page' => 1, 'page_size' => count($items), 'total' => count($items)];
    }

    private function deletePlan(int $userId, int $planId): void
    {
        PlanGenerator::findPlan($this->pdo, $userId, $planId);
        $this->assertPlanNotActive($userId, $planId);
        $statement = $this->pdo->prepare(
            'DELETE FROM workout_plans WHERE workout_plan_id = ? AND user_id = ?'
        );
        $statement->execute([$planId, $userId]);
    }

    private function assertPlanNotActive(int $userId, int $planId): void
    {
        $statement = $this->pdo->prepare(
            'SELECT 1 FROM workout_sessions ws '
            . 'JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id '
            . 'JOIN plan_days pd ON pd.plan_day_id = wsp.plan_day_id '
            . "WHERE ws.user_id = ? AND pd.workout_plan_id = ? AND ws.status = 'in_progress'"
        );
        $statement->execute([$userId, $planId]);
        if ($statement->fetchColumn()) {
            throw new ApiException(409, 'PLAN_IN_USE', '這份課表有進行中的訓練，不能修改或刪除。');
        }
    }

    private function startSession(int $userId, array $input): array
    {
        $planDayId = filter_var($input['plan_day_id'] ?? null, FILTER_VALIDATE_INT);
        if ($planDayId === false) {
            throw new ApiException(422, 'INVALID_PLAN_DAY', '請選擇有效的課表日。');
        }
        $day = $this->pdo->prepare(
            'SELECT pd.plan_day_id FROM plan_days pd '
            . 'JOIN workout_plans wp ON wp.workout_plan_id = pd.workout_plan_id '
            . 'WHERE pd.plan_day_id = ? AND wp.user_id = ?'
        );
        $day->execute([$planDayId, $userId]);
        if (!$day->fetchColumn()) {
            throw new ApiException(404, 'PLAN_DAY_NOT_FOUND', '找不到這個課表日。');
        }
        $active = $this->currentSession($userId);
        if ($active !== null) {
            if ((int) $active['plan_day_id'] === (int) $planDayId) {
                return [200, $active];
            }
            throw new ApiException(409, 'WORKOUT_ALREADY_ACTIVE', '已有另一個進行中的訓練。');
        }

        $this->pdo->beginTransaction();
        try {
            $sessionId = Database::insert(
                $this->pdo,
                "INSERT INTO workout_sessions (user_id, status) VALUES (?, 'in_progress')",
                [$userId],
                'workout_session_id'
            );
            $this->pdo->prepare(
                'INSERT INTO workout_session_plans (workout_session_id, plan_day_id) VALUES (?, ?)'
            )->execute([$sessionId, $planDayId]);
            $this->pdo->commit();
            return [201, $this->sessionDetail($userId, $sessionId)];
        } catch (\Throwable $error) {
            $this->pdo->rollBack();
            throw $error;
        }
    }

    private function currentSession(int $userId): ?array
    {
        $statement = $this->pdo->prepare(
            "SELECT workout_session_id FROM workout_sessions WHERE user_id = ? AND status = 'in_progress' LIMIT 1"
        );
        $statement->execute([$userId]);
        $sessionId = $statement->fetchColumn();
        return $sessionId ? $this->sessionDetail($userId, (int) $sessionId) : null;
    }

    private function sessionDetail(int $userId, int $sessionId): array
    {
        $statement = $this->pdo->prepare(
            'SELECT ws.*, wsp.plan_day_id, pd.day_title, pd.day_number, wp.plan_name '
            . 'FROM workout_sessions ws '
            . 'LEFT JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id '
            . 'LEFT JOIN plan_days pd ON pd.plan_day_id = wsp.plan_day_id '
            . 'LEFT JOIN workout_plans wp ON wp.workout_plan_id = pd.workout_plan_id '
            . 'WHERE ws.workout_session_id = ? AND ws.user_id = ?'
        );
        $statement->execute([$sessionId, $userId]);
        $session = $statement->fetch();
        if (!$session) {
            throw new ApiException(404, 'WORKOUT_NOT_FOUND', '找不到這次訓練。');
        }
        $exerciseStatement = $this->pdo->prepare(
            'SELECT pe.*, e.exercise_name, e.equipment, e.description, e.image_url, bp.body_part_name '
            . 'FROM workout_session_plans wsp '
            . 'JOIN plan_exercises pe ON pe.plan_day_id = wsp.plan_day_id '
            . 'JOIN exercises e ON e.exercise_id = pe.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE wsp.workout_session_id = ? ORDER BY pe.exercise_order'
        );
        $exerciseStatement->execute([$sessionId]);
        $session['exercises'] = $exerciseStatement->fetchAll();
        $setStatement = $this->pdo->prepare(
            'SELECT ws.*, e.exercise_name FROM workout_sets ws '
            . 'JOIN exercises e ON e.exercise_id = ws.exercise_id '
            . 'WHERE ws.workout_session_id = ? ORDER BY ws.exercise_id, ws.set_number'
        );
        $setStatement->execute([$sessionId]);
        $session['sets'] = $setStatement->fetchAll();
        return $session;
    }

    private function saveSet(int $userId, int $sessionId, array $input): array
    {
        $exerciseId = filter_var($input['exercise_id'] ?? null, FILTER_VALIDATE_INT);
        $setNumber = filter_var($input['set_number'] ?? null, FILTER_VALIDATE_INT);
        $weight = filter_var($input['weight_kg'] ?? null, FILTER_VALIDATE_FLOAT);
        $reps = filter_var($input['reps'] ?? null, FILTER_VALIDATE_INT);
        if ($exerciseId === false || $setNumber === false || $weight === false || $reps === false
            || $setNumber < 1 || $setNumber > 100 || $weight < 0 || $weight > 999.99
            || $reps < 1 || $reps > 999) {
            throw new ApiException(422, 'INVALID_SET', '組數、重量或次數不正確。');
        }
        $allowed = $this->pdo->prepare(
            'SELECT ws.status FROM workout_sessions ws '
            . 'JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id '
            . 'JOIN plan_exercises pe ON pe.plan_day_id = wsp.plan_day_id '
            . 'WHERE ws.workout_session_id = ? AND ws.user_id = ? AND pe.exercise_id = ?'
        );
        $allowed->execute([$sessionId, $userId, $exerciseId]);
        $status = $allowed->fetchColumn();
        if ($status === false) {
            throw new ApiException(404, 'WORKOUT_NOT_FOUND', '找不到訓練或動作不在課表中。');
        }
        if ($status !== 'in_progress') {
            throw new ApiException(409, 'WORKOUT_FINISHED', '這次訓練已結束，不能新增組數。');
        }
        $existing = $this->pdo->prepare(
            'SELECT * FROM workout_sets WHERE workout_session_id = ? AND exercise_id = ? AND set_number = ?'
        );
        $existing->execute([$sessionId, $exerciseId, $setNumber]);
        $row = $existing->fetch();
        if ($row) {
            if ((float) $row['weight_kg'] === (float) $weight && (int) $row['reps'] === (int) $reps) {
                $row['set_volume'] = (float) $row['weight_kg'] * (int) $row['reps'];
                return [200, $row];
            }
            throw new ApiException(409, 'SET_ALREADY_EXISTS', '這一組已有不同資料，請改用編輯功能。');
        }
        $workoutSetId = Database::insert(
            $this->pdo,
            'INSERT INTO workout_sets '
            . '(workout_session_id, exercise_id, set_number, weight_kg, reps) VALUES (?, ?, ?, ?, ?)',
            [$sessionId, $exerciseId, $setNumber, $weight, $reps],
            'workout_set_id'
        );
        return [201, [
            'workout_set_id' => $workoutSetId,
            'workout_session_id' => $sessionId,
            'exercise_id' => $exerciseId,
            'set_number' => $setNumber,
            'weight_kg' => number_format((float) $weight, 2, '.', ''),
            'reps' => $reps,
            'set_volume' => (float) $weight * (int) $reps,
        ]];
    }

    private function finishSession(
        int $userId,
        int $sessionId,
        string $targetStatus,
        string $notes
    ): array {
        if (mb_strlen($notes) > 1000) {
            throw new ApiException(422, 'NOTES_TOO_LONG', '訓練備註不可超過 1,000 個字。');
        }
        $statement = $this->pdo->prepare(
            'SELECT * FROM workout_sessions WHERE workout_session_id = ? AND user_id = ?'
        );
        $statement->execute([$sessionId, $userId]);
        $session = $statement->fetch();
        if (!$session) {
            throw new ApiException(404, 'WORKOUT_NOT_FOUND', '找不到這次訓練。');
        }
        if ($session['status'] === $targetStatus) {
            return $this->sessionDetail($userId, $sessionId);
        }
        if ($session['status'] !== 'in_progress') {
            throw new ApiException(409, 'INVALID_WORKOUT_STATE', '訓練狀態不能再次轉換。');
        }
        if ($targetStatus === 'completed') {
            $count = $this->pdo->prepare(
                'SELECT COUNT(*) FROM workout_sets WHERE workout_session_id = ?'
            );
            $count->execute([$sessionId]);
            if ((int) $count->fetchColumn() === 0) {
                throw new ApiException(409, 'EMPTY_WORKOUT', '至少儲存一組後才能完成訓練。');
            }
        }
        $this->pdo->prepare(
            'UPDATE workout_sessions SET status = ?, ended_at = CURRENT_TIMESTAMP, notes = ? '
            . 'WHERE workout_session_id = ? AND user_id = ?'
        )->execute([$targetStatus, $notes === '' ? null : $notes, $sessionId, $userId]);
        return $this->sessionDetail($userId, $sessionId);
    }

    private function updateSet(int $userId, int $setId, array $input): array
    {
        $statement = $this->pdo->prepare(
            'SELECT wset.*, ws.status FROM workout_sets wset '
            . 'JOIN workout_sessions ws ON ws.workout_session_id = wset.workout_session_id '
            . 'WHERE wset.workout_set_id = ? AND ws.user_id = ?'
        );
        $statement->execute([$setId, $userId]);
        $set = $statement->fetch();
        if (!$set) {
            throw new ApiException(404, 'WORKOUT_SET_NOT_FOUND', '找不到這組訓練紀錄。');
        }
        if ($set['status'] === 'cancelled') {
            throw new ApiException(409, 'WORKOUT_CANCELLED', '取消的訓練不能修改組數。');
        }
        $weight = filter_var($input['weight_kg'] ?? $set['weight_kg'], FILTER_VALIDATE_FLOAT);
        $reps = filter_var($input['reps'] ?? $set['reps'], FILTER_VALIDATE_INT);
        if ($weight === false || $weight < 0 || $weight > 999.99
            || $reps === false || $reps < 1 || $reps > 999) {
            throw new ApiException(422, 'INVALID_SET', '重量或次數不正確。');
        }
        $this->pdo->prepare(
            'UPDATE workout_sets SET weight_kg = ?, reps = ? WHERE workout_set_id = ?'
        )->execute([$weight, $reps, $setId]);
        $set['weight_kg'] = number_format((float) $weight, 2, '.', '');
        $set['reps'] = $reps;
        $set['set_volume'] = (float) $weight * (int) $reps;
        return $set;
    }

    private function deleteSet(int $userId, int $setId): void
    {
        $statement = $this->pdo->prepare(
            'SELECT wset.workout_session_id, ws.status FROM workout_sets wset '
            . 'JOIN workout_sessions ws ON ws.workout_session_id = wset.workout_session_id '
            . 'WHERE wset.workout_set_id = ? AND ws.user_id = ?'
        );
        $statement->execute([$setId, $userId]);
        $set = $statement->fetch();
        if (!$set) {
            throw new ApiException(404, 'WORKOUT_SET_NOT_FOUND', '找不到這組訓練紀錄。');
        }
        if ($set['status'] === 'cancelled') {
            throw new ApiException(409, 'WORKOUT_CANCELLED', '取消的訓練不能刪除組數。');
        }
        if ($set['status'] === 'completed') {
            $count = $this->pdo->prepare(
                'SELECT COUNT(*) FROM workout_sets WHERE workout_session_id = ?'
            );
            $count->execute([(int) $set['workout_session_id']]);
            if ((int) $count->fetchColumn() <= 1) {
                throw new ApiException(409, 'LAST_SET', '完成的訓練至少要保留一組。');
            }
        }
        $this->pdo->prepare(
            'DELETE FROM workout_sets WHERE workout_set_id = ?'
        )->execute([$setId]);
    }

    private function deleteSession(int $userId, int $sessionId): void
    {
        $statement = $this->pdo->prepare(
            'SELECT status FROM workout_sessions WHERE workout_session_id = ? AND user_id = ?'
        );
        $statement->execute([$sessionId, $userId]);
        $status = $statement->fetchColumn();
        if ($status === false) {
            throw new ApiException(404, 'WORKOUT_NOT_FOUND', '找不到這次訓練。');
        }
        if ($status === 'in_progress') {
            throw new ApiException(409, 'WORKOUT_ACTIVE', '請先取消進行中的訓練。');
        }
        $this->pdo->prepare(
            'DELETE FROM workout_sessions WHERE workout_session_id = ? AND user_id = ?'
        )->execute([$sessionId, $userId]);
    }

    private function history(int $userId): array
    {
        $statement = $this->pdo->prepare(
            "SELECT ws.workout_session_id, ws.status, ws.started_at, ws.ended_at, ws.notes, "
            . 'pd.day_title, wp.plan_name, COUNT(wset.workout_set_id) AS set_count, '
            . 'COALESCE(SUM(wset.weight_kg * wset.reps), 0) AS total_volume '
            . 'FROM workout_sessions ws '
            . 'LEFT JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id '
            . 'LEFT JOIN plan_days pd ON pd.plan_day_id = wsp.plan_day_id '
            . 'LEFT JOIN workout_plans wp ON wp.workout_plan_id = pd.workout_plan_id '
            . 'LEFT JOIN workout_sets wset ON wset.workout_session_id = ws.workout_session_id '
            . "WHERE ws.user_id = ? AND ws.status IN ('completed', 'cancelled') "
            . 'GROUP BY ws.workout_session_id, ws.status, ws.started_at, ws.ended_at, ws.notes, '
            . 'pd.day_title, wp.plan_name ORDER BY ws.started_at DESC LIMIT 100'
        );
        $statement->execute([$userId]);
        $items = $statement->fetchAll();
        return ['items' => $items, 'page' => 1, 'page_size' => count($items), 'total' => count($items)];
    }

    private function dashboard(int $userId): array
    {
        $statement = $this->pdo->prepare(
            "SELECT ws.workout_session_id, ws.started_at, wset.exercise_id, wset.weight_kg, wset.reps, "
            . 'e.exercise_name, bp.body_part_name '
            . 'FROM workout_sessions ws '
            . 'JOIN workout_sets wset ON wset.workout_session_id = ws.workout_session_id '
            . 'JOIN exercises e ON e.exercise_id = wset.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . "WHERE ws.user_id = ? AND ws.status = 'completed' ORDER BY ws.started_at"
        );
        $statement->execute([$userId]);
        $rows = $statement->fetchAll();
        $sessions = [];
        $volumeByWeek = [];
        $bodyParts = [];
        $exercises = [];
        $totalVolume = 0.0;
        foreach ($rows as $row) {
            $volume = (float) $row['weight_kg'] * (int) $row['reps'];
            $totalVolume += $volume;
            $sessions[(int) $row['workout_session_id']] = true;
            $week = date('o-\WW', strtotime((string) $row['started_at']));
            $volumeByWeek[$week] = ($volumeByWeek[$week] ?? 0) + $volume;
            $bodyParts[$row['body_part_name']] = ($bodyParts[$row['body_part_name']] ?? 0) + 1;
            $exercises[$row['exercise_name']] = ($exercises[$row['exercise_name']] ?? 0) + 1;
        }
        arsort($bodyParts);
        arsort($exercises);
        $weights = $this->bodyRecords($userId)['items'];
        $latestWeight = $weights !== [] ? $weights[0]['weight_kg'] : null;
        return [
            'session_count' => count($sessions),
            'set_count' => count($rows),
            'total_volume' => round($totalVolume, 2),
            'latest_weight' => $latestWeight,
            'favorite_body_part' => array_key_first($bodyParts),
            'favorite_exercise' => array_key_first($exercises),
            'volume_by_week' => array_map(
                static fn (string $week, float|int $volume): array => [
                    'week' => $week,
                    'volume' => round((float) $volume, 2),
                ],
                array_keys($volumeByWeek),
                array_values($volumeByWeek)
            ),
            'weight_history' => array_reverse(array_map(
                static fn (array $item): array => [
                    'date' => $item['record_date'],
                    'weight' => (float) $item['weight_kg'],
                ],
                $weights
            )),
            'recent_workouts' => array_slice($this->history($userId)['items'], 0, 5),
        ];
    }

    private function bodyRecords(int $userId): array
    {
        $statement = $this->pdo->prepare(
            'SELECT * FROM body_records WHERE user_id = ? ORDER BY record_date DESC, body_record_id DESC'
        );
        $statement->execute([$userId]);
        $items = $statement->fetchAll();
        return ['items' => $items, 'page' => 1, 'page_size' => count($items), 'total' => count($items)];
    }

    private function createBodyRecord(int $userId, array $input): array
    {
        $date = (string) ($input['record_date'] ?? '');
        $weight = filter_var($input['weight_kg'] ?? null, FILTER_VALIDATE_FLOAT);
        $notes = trim((string) ($input['notes'] ?? ''));
        $parsedDate = \DateTimeImmutable::createFromFormat('!Y-m-d', $date);
        if (!$parsedDate || $parsedDate->format('Y-m-d') !== $date || $date > date('Y-m-d')) {
            throw new ApiException(422, 'INVALID_DATE', '日期格式不正確或不可晚於今天。');
        }
        if ($weight === false || $weight < 20 || $weight > 500 || mb_strlen($notes) > 1000) {
            throw new ApiException(422, 'INVALID_BODY_RECORD', '體重或備註不正確。');
        }
        $exists = $this->pdo->prepare(
            'SELECT 1 FROM body_records WHERE user_id = ? AND record_date = ?'
        );
        $exists->execute([$userId, $date]);
        if ($exists->fetchColumn()) {
            throw new ApiException(409, 'BODY_RECORD_EXISTS', '這一天已有體重紀錄。');
        }
        $bodyRecordId = Database::insert(
            $this->pdo,
            'INSERT INTO body_records (user_id, record_date, weight_kg, notes) VALUES (?, ?, ?, ?)',
            [$userId, $date, $weight, $notes === '' ? null : $notes],
            'body_record_id'
        );
        return [
            'body_record_id' => $bodyRecordId,
            'user_id' => $userId,
            'record_date' => $date,
            'weight_kg' => number_format((float) $weight, 2, '.', ''),
            'notes' => $notes === '' ? null : $notes,
        ];
    }

    private function updateBodyRecord(int $userId, int $recordId, array $input): array
    {
        $statement = $this->pdo->prepare(
            'SELECT * FROM body_records WHERE body_record_id = ? AND user_id = ?'
        );
        $statement->execute([$recordId, $userId]);
        $record = $statement->fetch();
        if (!$record) {
            throw new ApiException(404, 'BODY_RECORD_NOT_FOUND', '找不到這筆體重紀錄。');
        }
        $date = (string) ($input['record_date'] ?? $record['record_date']);
        $weight = filter_var($input['weight_kg'] ?? $record['weight_kg'], FILTER_VALIDATE_FLOAT);
        $notes = (string) ($input['notes'] ?? $record['notes'] ?? '');
        $parsedDate = \DateTimeImmutable::createFromFormat('!Y-m-d', $date);
        if (!$parsedDate || $parsedDate->format('Y-m-d') !== $date || $date > date('Y-m-d')
            || $weight === false || $weight < 20 || $weight > 500 || mb_strlen($notes) > 1000) {
            throw new ApiException(422, 'INVALID_BODY_RECORD', '日期、體重或備註不正確。');
        }
        $duplicate = $this->pdo->prepare(
            'SELECT 1 FROM body_records WHERE user_id = ? AND record_date = ? AND body_record_id <> ?'
        );
        $duplicate->execute([$userId, $date, $recordId]);
        if ($duplicate->fetchColumn()) {
            throw new ApiException(409, 'BODY_RECORD_EXISTS', '這一天已有其他體重紀錄。');
        }
        $this->pdo->prepare(
            'UPDATE body_records SET record_date = ?, weight_kg = ?, notes = ? '
            . 'WHERE body_record_id = ? AND user_id = ?'
        )->execute([$date, $weight, trim($notes) === '' ? null : trim($notes), $recordId, $userId]);
        return [
            'body_record_id' => $recordId,
            'user_id' => $userId,
            'record_date' => $date,
            'weight_kg' => number_format((float) $weight, 2, '.', ''),
            'notes' => trim($notes) === '' ? null : trim($notes),
        ];
    }

    private function deleteBodyRecord(int $userId, int $recordId): void
    {
        $statement = $this->pdo->prepare(
            'DELETE FROM body_records WHERE body_record_id = ? AND user_id = ?'
        );
        $statement->execute([$recordId, $userId]);
        if ($statement->rowCount() === 0) {
            throw new ApiException(404, 'BODY_RECORD_NOT_FOUND', '找不到這筆體重紀錄。');
        }
    }

    private function adminStatistics(): array
    {
        return [
            'users' => (int) $this->pdo->query('SELECT COUNT(*) FROM users')->fetchColumn(),
            'exercises' => (int) $this->pdo->query('SELECT COUNT(*) FROM exercises')->fetchColumn(),
            'plans' => (int) $this->pdo->query('SELECT COUNT(*) FROM workout_plans')->fetchColumn(),
            'completed_workouts' => (int) $this->pdo->query(
                "SELECT COUNT(*) FROM workout_sessions WHERE status='completed'"
            )->fetchColumn(),
            'sets' => (int) $this->pdo->query('SELECT COUNT(*) FROM workout_sets')->fetchColumn(),
        ];
    }

    private function adminUsers(): array
    {
        return ['items' => $this->pdo->query(
            'SELECT u.user_id, u.name, ua.email, ua.is_active, u.created_at, '
            . 'CASE WHEN a.user_id IS NULL THEN 0 ELSE 1 END AS is_admin '
            . 'FROM users u JOIN user_auth ua ON ua.user_id = u.user_id '
            . 'LEFT JOIN admins a ON a.user_id = u.user_id ORDER BY u.created_at DESC'
        )->fetchAll()];
    }

    private function adminExercises(): array
    {
        return ['items' => $this->pdo->query(
            'SELECT e.*, bp.body_part_name FROM exercises e '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id ORDER BY e.exercise_id'
        )->fetchAll()];
    }

    private function databaseOverview(): array
    {
        $tables = array_map(function (string $table): array {
            return [
                'table_name' => $table,
                'row_count' => (int) $this->pdo->query("SELECT COUNT(*) FROM {$table}")->fetchColumn(),
                'columns' => $this->databaseColumns($table),
            ];
        }, self::DATABASE_TABLES);

        $relationships = array_map(static fn (array $item): array => [
            'from_table' => $item[0],
            'from_column' => $item[1],
            'to_table' => $item[2],
            'to_column' => $item[3],
            'relationship_type' => $item[4],
            'on_delete' => $item[5],
        ], self::DATABASE_RELATIONSHIPS);

        return [
            'driver' => Database::driver(),
            'tables' => $tables,
            'relationships' => $relationships,
            'query_examples' => $this->databaseQueryExamples(),
            'normalization_notes' => [
                '1NF：每個欄位只保存單一值，偏好部位透過 user_body_parts 關聯表保存。',
                '2NF：關聯表的非鍵資料依賴完整複合主鍵，不只依賴其中一部分。',
                '3NF：訓練目標、身體部位與動作獨立成表，名稱不重複寫入交易資料。',
                'Referential Integrity：Foreign Key 搭配 CASCADE 或 RESTRICT 維持資料一致性。',
            ],
        ];
    }

    private function databaseTable(string $table): array
    {
        if (!in_array($table, self::DATABASE_TABLES, true)) {
            throw new ApiException(404, 'TABLE_NOT_FOUND', '找不到這張資料表。');
        }
        $limit = filter_var($_GET['limit'] ?? 25, FILTER_VALIDATE_INT);
        $limit = $limit === false ? 25 : max(1, min(100, $limit));
        $columns = $this->databaseColumns($table);
        $primaryKey = null;
        foreach ($columns as $column) {
            if ($column['is_primary_key']) {
                $primaryKey = $column['column_name'];
                break;
            }
        }
        $orderBy = $primaryKey ? " ORDER BY {$primaryKey} DESC" : '';
        $rows = $this->pdo->query("SELECT * FROM {$table}{$orderBy} LIMIT {$limit}")->fetchAll();
        foreach ($rows as &$row) {
            if (array_key_exists('password_hash', $row)) {
                $row['password_hash'] = '[已隱藏]';
            }
            if (array_key_exists('user_session_id', $row)) {
                $row['user_session_id'] = '[已隱藏]';
            }
        }
        unset($row);
        return [
            'table_name' => $table,
            'row_count' => (int) $this->pdo->query("SELECT COUNT(*) FROM {$table}")->fetchColumn(),
            'columns' => $columns,
            'rows' => $rows,
            'limit' => $limit,
            'read_only' => true,
        ];
    }

    private function databaseColumns(string $table): array
    {
        if (!in_array($table, self::DATABASE_TABLES, true)) {
            throw new ApiException(404, 'TABLE_NOT_FOUND', '找不到這張資料表。');
        }
        if (Database::driver() === 'sqlite') {
            $foreignKeys = [];
            foreach ($this->pdo->query("PRAGMA foreign_key_list({$table})")->fetchAll() as $key) {
                $foreignKeys[$key['from']] = $key['table'] . '.' . $key['to'];
            }
            return array_map(static fn (array $column): array => [
                'column_name' => $column['name'],
                'data_type' => strtoupper((string) $column['type']),
                'is_primary_key' => (int) $column['pk'] > 0,
                'is_nullable' => (int) $column['pk'] === 0 && (int) $column['notnull'] === 0,
                'foreign_key' => $foreignKeys[$column['name']] ?? null,
            ], $this->pdo->query("PRAGMA table_info({$table})")->fetchAll());
        }

        $statement = $this->pdo->prepare(
            "SELECT c.column_name, c.data_type, (c.is_nullable = 'YES') AS is_nullable, "
            . "EXISTS (SELECT 1 FROM information_schema.table_constraints tc "
            . "JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name "
            . "AND tc.table_schema = kcu.table_schema WHERE tc.table_schema = 'public' "
            . "AND tc.table_name = c.table_name AND tc.constraint_type = 'PRIMARY KEY' "
            . "AND kcu.column_name = c.column_name) AS is_primary_key, "
            . "(SELECT ccu.table_name || '.' || ccu.column_name FROM information_schema.table_constraints tc "
            . "JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name "
            . "AND tc.table_schema = kcu.table_schema JOIN information_schema.constraint_column_usage ccu "
            . "ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema "
            . "WHERE tc.table_schema = 'public' AND tc.table_name = c.table_name "
            . "AND tc.constraint_type = 'FOREIGN KEY' AND kcu.column_name = c.column_name LIMIT 1) AS foreign_key "
            . "FROM information_schema.columns c WHERE c.table_schema = 'public' AND c.table_name = ? "
            . 'ORDER BY c.ordinal_position'
        );
        $statement->execute([$table]);
        return array_map(static fn (array $column): array => [
            'column_name' => $column['column_name'],
            'data_type' => strtoupper((string) $column['data_type']),
            'is_primary_key' => filter_var($column['is_primary_key'], FILTER_VALIDATE_BOOL),
            'is_nullable' => filter_var($column['is_nullable'], FILTER_VALIDATE_BOOL),
            'foreign_key' => $column['foreign_key'],
        ], $statement->fetchAll());
    }

    private function databaseQueryExamples(): array
    {
        $definitions = [
            [
                'title' => 'JOIN：動作與主要部位',
                'sql' => 'SELECT e.exercise_name, bp.body_part_name, e.difficulty_level, e.equipment FROM exercises e JOIN body_parts bp ON bp.body_part_id = e.body_part_id WHERE e.is_active = TRUE ORDER BY bp.body_part_id, e.exercise_name LIMIT 8;',
            ],
            [
                'title' => 'GROUP BY：各部位動作數量',
                'sql' => 'SELECT bp.body_part_name, COUNT(e.exercise_id) AS exercise_count, SUM(CASE WHEN e.is_active = TRUE THEN 1 ELSE 0 END) AS active_count FROM body_parts bp LEFT JOIN exercises e ON e.body_part_id = bp.body_part_id GROUP BY bp.body_part_id, bp.body_part_name ORDER BY bp.body_part_id;',
            ],
            [
                'title' => 'Aggregate：完成訓練總量',
                'sql' => "SELECT e.exercise_name, COUNT(wset.workout_set_id) AS working_sets, COALESCE(SUM(wset.weight_kg * wset.reps), 0) AS volume_kg FROM exercises e JOIN workout_sets wset ON wset.exercise_id = e.exercise_id JOIN workout_sessions ws ON ws.workout_session_id = wset.workout_session_id WHERE ws.status = 'completed' GROUP BY e.exercise_id, e.exercise_name ORDER BY volume_kg DESC LIMIT 8;",
            ],
        ];
        return array_map(function (array $definition): array {
            return [
                'title' => $definition['title'],
                'sql' => $definition['sql'],
                'rows' => $this->pdo->query($definition['sql'])->fetchAll(),
            ];
        }, $definitions);
    }

    private function createExercise(array $input): array
    {
        $values = $this->validateExerciseInput($input, true);
        $exerciseId = Database::insert(
            $this->pdo,
            'INSERT INTO exercises '
            . '(exercise_name, body_part_id, difficulty_level, equipment, description, image_url, is_active) '
            . 'VALUES (?, ?, ?, ?, ?, ?, ?)',
            $values,
            'exercise_id'
        );
        return $this->findExercise($exerciseId);
    }

    private function updateExercise(int $exerciseId, array $input): array
    {
        $allowed = ['exercise_name', 'body_part_id', 'difficulty_level', 'equipment', 'description', 'image_url', 'is_active'];
        $sets = [];
        $values = [];
        foreach ($allowed as $field) {
            if (array_key_exists($field, $input)) {
                $sets[] = $field . ' = ?';
                $values[] = $input[$field];
            }
        }
        if ($sets === []) {
            throw new ApiException(422, 'NO_FIELDS', '沒有可更新的欄位。');
        }
        if (array_key_exists('exercise_name', $input) && trim((string) $input['exercise_name']) === '') {
            throw new ApiException(422, 'INVALID_EXERCISE', '動作名稱不可為空。');
        }
        if (array_key_exists('difficulty_level', $input)
            && !in_array($input['difficulty_level'], ['Beginner', 'Intermediate', 'Advanced'], true)) {
            throw new ApiException(422, 'INVALID_EXERCISE', '動作難度不正確。');
        }
        $values[] = $exerciseId;
        $statement = $this->pdo->prepare(
            'UPDATE exercises SET ' . implode(', ', $sets) . ' WHERE exercise_id = ?'
        );
        $statement->execute($values);
        if ($statement->rowCount() === 0) {
            throw new ApiException(404, 'EXERCISE_NOT_FOUND', '找不到這個動作。');
        }
        return $this->findExercise($exerciseId);
    }

    private function deleteExercise(int $exerciseId): void
    {
        try {
            $statement = $this->pdo->prepare('DELETE FROM exercises WHERE exercise_id = ?');
            $statement->execute([$exerciseId]);
            if ($statement->rowCount() === 0) {
                throw new ApiException(404, 'EXERCISE_NOT_FOUND', '找不到這個動作。');
            }
        } catch (\PDOException $error) {
            throw new ApiException(409, 'EXERCISE_IN_USE', '動作已有課表或歷史紀錄，請改用停用。');
        }
    }

    private function updateReference(string $type, int $id, array $input): array
    {
        $description = array_key_exists('description', $input)
            ? trim((string) $input['description'])
            : null;
        if ($description === null || mb_strlen($description) > 1000) {
            throw new ApiException(422, 'INVALID_DESCRIPTION', '說明不可超過 1,000 個字。');
        }
        $table = $type === 'training-goals' ? 'training_goals' : 'body_parts';
        $idColumn = $type === 'training-goals' ? 'training_goal_id' : 'body_part_id';
        $statement = $this->pdo->prepare(
            "UPDATE {$table} SET description = ? WHERE {$idColumn} = ?"
        );
        $statement->execute([$description === '' ? null : $description, $id]);
        if ($statement->rowCount() === 0) {
            throw new ApiException(404, 'REFERENCE_NOT_FOUND', '找不到這筆參考資料。');
        }
        $fetch = $this->pdo->prepare("SELECT * FROM {$table} WHERE {$idColumn} = ?");
        $fetch->execute([$id]);
        return $fetch->fetch();
    }

    private function validateExerciseInput(array $input, bool $requireAll): array
    {
        $name = trim((string) ($input['exercise_name'] ?? ''));
        $bodyPartId = filter_var($input['body_part_id'] ?? null, FILTER_VALIDATE_INT);
        $difficulty = (string) ($input['difficulty_level'] ?? '');
        $equipment = trim((string) ($input['equipment'] ?? ''));
        $description = trim((string) ($input['description'] ?? ''));
        $imageUrl = trim((string) ($input['image_url'] ?? ''));
        $active = filter_var($input['is_active'] ?? true, FILTER_VALIDATE_BOOL, FILTER_NULL_ON_FAILURE);
        if ($name === '' || mb_strlen($name) > 120 || $bodyPartId === false
            || !in_array($difficulty, ['Beginner', 'Intermediate', 'Advanced'], true)
            || $description === '' || mb_strlen($description) > 4000 || mb_strlen($equipment) > 100
            || mb_strlen($imageUrl) > 2048 || $active === null) {
            throw new ApiException(422, 'INVALID_EXERCISE', '動作欄位不完整或格式不正確。');
        }
        $part = $this->pdo->prepare('SELECT 1 FROM body_parts WHERE body_part_id = ?');
        $part->execute([$bodyPartId]);
        if (!$part->fetchColumn()) {
            throw new ApiException(422, 'INVALID_BODY_PART', '身體部位不存在。');
        }
        return [
            $name,
            $bodyPartId,
            $difficulty,
            $equipment === '' ? null : $equipment,
            $description,
            $imageUrl === '' ? null : $imageUrl,
            $active,
        ];
    }

    private function findExercise(int $exerciseId): array
    {
        $fetch = $this->pdo->prepare(
            'SELECT e.*, bp.body_part_name FROM exercises e '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id WHERE e.exercise_id = ?'
        );
        $fetch->execute([$exerciseId]);
        $exercise = $fetch->fetch();
        if (!$exercise) {
            throw new ApiException(404, 'EXERCISE_NOT_FOUND', '找不到這個動作。');
        }
        return $exercise;
    }

    private function upsertTodayWeight(int $userId, float $weight): void
    {
        $today = date('Y-m-d');
        $statement = $this->pdo->prepare(
            'SELECT body_record_id FROM body_records WHERE user_id = ? AND record_date = ?'
        );
        $statement->execute([$userId, $today]);
        $recordId = $statement->fetchColumn();
        if ($recordId) {
            $this->pdo->prepare(
                'UPDATE body_records SET weight_kg = ? WHERE body_record_id = ? AND user_id = ?'
            )->execute([$weight, $recordId, $userId]);
            return;
        }
        $this->pdo->prepare(
            'INSERT INTO body_records (user_id, record_date, weight_kg) VALUES (?, ?, ?)'
        )->execute([$userId, $today, $weight]);
    }

    private function requireAdmin(array $user): void
    {
        if (($user['role'] ?? 'USER') !== 'ADMIN') {
            throw new ApiException(403, 'ADMIN_REQUIRED', '需要管理員權限。');
        }
    }

    private function bearerToken(): ?string
    {
        $header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
        if (preg_match('/^Bearer\s+(.+)$/i', $header, $matches)) {
            return trim($matches[1]);
        }
        return null;
    }

    private function input(): array
    {
        $raw = file_get_contents('php://input');
        if ($raw === false || trim($raw) === '') {
            return $_POST;
        }
        $decoded = json_decode($raw, true);
        if (!is_array($decoded)) {
            throw new ApiException(422, 'INVALID_JSON', 'JSON 格式不正確。');
        }
        return $decoded;
    }

    private function tableCount(): int
    {
        if (Database::driver() === 'sqlite') {
            return (int) $this->pdo->query(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )->fetchColumn();
        }
        return (int) $this->pdo->query(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'"
        )->fetchColumn();
    }
}
