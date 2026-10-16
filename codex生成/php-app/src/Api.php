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
        'login_failures',
        'training_goals',
        'body_parts',
        'user_body_parts',
        'body_records',
        'exercises',
        'exercise_versions',
        'workout_plans',
        'planning_profiles',
        'planning_profile_body_parts',
        'plan_days',
        'plan_exercises',
        'workout_sessions',
        'workout_session_plans',
        'workout_session_exercises',
        'workout_sets',
    ];

    private const DATABASE_RELATIONSHIPS = [
        ['user_auth', 'user_id', 'users', 'user_id', 'User 1:1 User_Auth', 'CASCADE'],
        ['user_sessions', 'auth_id', 'user_auth', 'auth_id', 'User_Auth 1:N User_Session', 'CASCADE'],
        ['admins', 'user_id', 'users', 'user_id', 'User 1:0..1 Admin', 'CASCADE'],
        ['users', 'training_goal_id', 'training_goals', 'training_goal_id', 'Training_Goal 1:N User', 'RESTRICT'],
        ['user_body_parts', 'user_id', 'users', 'user_id', 'User 1:N User_Body_Part', 'CASCADE'],
        ['user_body_parts', 'body_part_id', 'body_parts', 'body_part_id', 'User M:N Body_Part', 'RESTRICT'],
        ['body_records', 'user_id', 'users', 'user_id', 'User 1:N Body_Record', 'CASCADE'],
        ['exercises', 'body_part_id', 'body_parts', 'body_part_id', 'Body_Part 1:N Exercise', 'RESTRICT'],
        ['exercise_versions', 'exercise_id', 'exercises', 'exercise_id', 'Exercise 1:N Exercise_Version', 'RESTRICT'],
        ['workout_plans', 'user_id', 'users', 'user_id', 'User 1:N Workout_Plan', 'CASCADE'],
        ['workout_plans', 'copied_from_plan_id', 'workout_plans', 'workout_plan_id', 'Workout_Plan 0..1:N Revision', 'RESTRICT'],
        ['planning_profiles', 'workout_plan_id', 'workout_plans', 'workout_plan_id', 'Workout_Plan 1:1 Planning_Profile', 'RESTRICT'],
        ['planning_profiles', 'training_goal_id', 'training_goals', 'training_goal_id', 'Training_Goal 1:N Planning_Profile', 'RESTRICT'],
        ['planning_profile_body_parts', 'workout_plan_id', 'planning_profiles', 'workout_plan_id', 'Planning_Profile 1:N Preferred_Part', 'RESTRICT'],
        ['planning_profile_body_parts', 'body_part_id', 'body_parts', 'body_part_id', 'Body_Part 1:N Preferred_Part', 'RESTRICT'],
        ['plan_days', 'workout_plan_id', 'workout_plans', 'workout_plan_id', 'Workout_Plan 1:N Plan_Day', 'RESTRICT'],
        ['plan_exercises', 'plan_day_id', 'plan_days', 'plan_day_id', 'Plan_Day 1:N Plan_Exercise', 'RESTRICT'],
        ['plan_exercises', 'exercise_version_id', 'exercise_versions', 'exercise_version_id', 'Exercise_Version 1:N Plan_Exercise', 'RESTRICT'],
        ['workout_sessions', 'user_id', 'users', 'user_id', 'User 1:N Workout_Session', 'CASCADE'],
        ['workout_session_plans', 'workout_session_id', 'workout_sessions', 'workout_session_id', 'Workout_Session 1:1 Session_Plan', 'CASCADE'],
        ['workout_session_plans', 'plan_day_id', 'plan_days', 'plan_day_id', 'Plan_Day 1:N Session_Plan', 'RESTRICT'],
        ['workout_session_exercises', 'workout_session_id', 'workout_sessions', 'workout_session_id', 'Workout_Session 1:N Session_Exercise', 'CASCADE'],
        ['workout_session_exercises', 'plan_exercise_id', 'plan_exercises', 'plan_exercise_id', 'Plan_Exercise 1:N Session_Exercise', 'RESTRICT'],
        ['workout_session_exercises', 'exercise_version_id', 'exercise_versions', 'exercise_version_id', 'Exercise_Version 1:N Session_Exercise', 'RESTRICT'],
        ['workout_sets', 'workout_session_exercise_id', 'workout_session_exercises', 'workout_session_exercise_id', 'Session_Exercise 1:N Workout_Set', 'CASCADE'],
    ];

    public function __construct(private readonly PDO $pdo, private readonly string $clientIp = '127.0.0.1')
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
            $this->assertAllowedFields($input, ['name', 'email', 'password']);
            return [201, Auth::register($this->pdo, $input)];
        }
        if ($method === 'POST' && $path === '/auth/login') {
            $this->assertAllowedFields($input, ['email', 'password']);
            return [200, LoginRateLimiter::attempt(
                $this->pdo,
                $this->clientIp,
                fn (): array => Auth::login($this->pdo, $input)
            )];
        }

        $user = Auth::user($this->pdo, RequestSecurity::token());
        if ($method === 'GET' && $path === '/auth/session') {
            return [200, ['user_id' => $user['user_id'], 'name' => $user['name'], 'email' => $user['email'], 'role' => $user['role']]];
        }
        if ($method === 'POST' && $path === '/auth/logout') {
            $this->assertAllowedFields($input, []);
            Auth::logout($this->pdo, $user);
            return [204, null];
        }
        if ($method === 'PATCH' && $path === '/auth/password') {
            $this->assertAllowedFields($input, ['current_password', 'new_password']);
            Auth::changePassword($this->pdo, $user, $input);
            return [204, null];
        }
        if ($method === 'POST' && $path === '/auth/deactivate') {
            $this->assertAllowedFields($input, ['current_password']);
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
            $this->assertAllowedFields($input, ['name', 'gender', 'age', 'height_cm', 'training_experience', 'weight_kg']);
            return [200, $this->updateProfile((int) $user['user_id'], $input)];
        }
        if ($method === 'PUT' && $path === '/me/training-settings') {
            $this->assertAllowedFields($input, ['training_goal_id', 'training_days_per_week', 'training_duration_minutes']);
            return [200, $this->updateTrainingSettings((int) $user['user_id'], $input)];
        }
        if ($method === 'PUT' && $path === '/me/body-parts') {
            $this->assertAllowedFields($input, ['body_part_ids']);
            return [200, $this->updateBodyParts((int) $user['user_id'], $input)];
        }
        if ($method === 'GET' && $path === '/exercises') {
            return [200, $this->exercises()];
        }
        if ($method === 'GET' && $path === '/exercises/options') {
            return [200, $this->exerciseOptions()];
        }
        if (preg_match('#^/exercises/(\d+)$#', $path, $matches) && $method === 'GET') {
            $exercise = $this->findExercise((int) $matches[1]);
            if (!(bool) $exercise['is_active']) {
                throw new ApiException(404, 'EXERCISE_NOT_FOUND', '找不到這個動作。');
            }
            return [200, $exercise];
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
            $this->assertAllowedFields($input, ['plan_name']);
            return [201, PlanGenerator::generate(
                $this->pdo,
                (int) $user['user_id'],
                isset($input['plan_name']) ? (string) $input['plan_name'] : null
            )];
        }
        if ($method === 'POST' && $path === '/plans/manual') {
            $this->assertAllowedFields($input, ['plan_name', 'days']);
            return [201, PlanGenerator::createManual(
                $this->pdo,
                (int) $user['user_id'],
                isset($input['plan_name']) ? (string) $input['plan_name'] : null,
                is_array($input['days'] ?? null) ? $input['days'] : []
            )];
        }
        if ($method === 'POST' && $path === '/plans/ai-generate') {
            $this->assertAllowedFields($input, ['plan_name', 'focus']);
            return [201, AiPlanGenerator::generate(
                $this->pdo,
                (int) $user['user_id'],
                isset($input['plan_name']) ? (string) $input['plan_name'] : null,
                isset($input['focus']) ? (string) $input['focus'] : null
            )];
        }
        if (preg_match('#^/plans/(\d+)$#', $path, $matches) && $method === 'PATCH') {
            $this->assertAllowedFields($input, ['plan_name', 'exercises']);
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
            $this->assertAllowedFields($input, ['plan_day_id']);
            return $this->startSession((int) $user['user_id'], $input);
        }
        if ($method === 'GET' && $path === '/workout-sessions') {
            return [200, $this->history((int) $user['user_id'])];
        }
        if (preg_match('#^/workout-sessions/(\d+)$#', $path, $matches) && $method === 'GET') {
            return [200, $this->sessionDetail((int) $user['user_id'], (int) $matches[1])];
        }
        if (preg_match('#^/workout-sessions/(\d+)/sets$#', $path, $matches) && $method === 'POST') {
            $this->assertAllowedFields($input, ['workout_session_exercise_id', 'set_number', 'weight_kg', 'reps']);
            return $this->saveSet((int) $user['user_id'], (int) $matches[1], $input);
        }
        if (preg_match('#^/workout-sessions/(\d+)/exercises/(\d+)$#', $path, $matches) && $method === 'PATCH') {
            $this->assertAllowedFields($input, ['target_sets', 'target_reps', 'rest_seconds', 'target_weight_kg']);
            return [200, $this->updateSessionExercise(
                (int) $user['user_id'],
                (int) $matches[1],
                (int) $matches[2],
                $input
            )];
        }
        if (preg_match('#^/workout-sessions/(\d+)/(complete|cancel|cancelled)$#', $path, $matches) && $method === 'POST') {
            $this->assertAllowedFields($input, ['notes']);
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
            $this->assertAllowedFields($input, ['weight_kg', 'reps']);
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
            $this->assertAllowedFields($input, ['record_date', 'weight_kg', 'notes']);
            return [201, $this->createBodyRecord((int) $user['user_id'], $input)];
        }
        if (preg_match('#^/body-records/(\d+)$#', $path, $matches) && $method === 'DELETE') {
            $this->deleteBodyRecord((int) $user['user_id'], (int) $matches[1]);
            return [204, null];
        }
        if (preg_match('#^/body-records/(\d+)$#', $path, $matches) && $method === 'PATCH') {
            $this->assertAllowedFields($input, ['record_date', 'weight_kg', 'notes']);
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
                $this->assertAllowedFields($input, ['exercise_name', 'body_part_id', 'difficulty_level', 'equipment', 'description', 'image_url', 'is_active']);
                return [201, $this->createExercise($input)];
            }
            if (preg_match('#^/admin/exercises/(\d+)$#', $path, $matches) && $method === 'PATCH') {
                $this->assertAllowedFields($input, ['exercise_name', 'body_part_id', 'difficulty_level', 'equipment', 'description', 'image_url', 'is_active']);
                return [200, $this->updateExercise((int) $matches[1], $input)];
            }
            if (preg_match('#^/admin/exercises/(\d+)$#', $path, $matches) && $method === 'DELETE') {
                $this->deleteExercise((int) $matches[1]);
                return [204, null];
            }
            if (preg_match('#^/admin/(training-goals|body-parts)/(\d+)$#', $path, $matches) && $method === 'PATCH') {
                $this->assertAllowedFields($input, ['description']);
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
        $profile['profile_complete'] = $profile['profile_completed_at'] !== null
            && $profile['current_weight_kg'] !== null;
        return $profile;
    }

    private function updateProfile(int $userId, array $input): array
    {
        $name = trim((string) ($input['name'] ?? ''));
        $gender = $input['gender'] ?? null;
        $age = $this->strictInteger($input['age'] ?? null);
        $height = $this->decimal($input['height_cm'] ?? null, false);
        $experience = (string) ($input['training_experience'] ?? '');
        $weight = $this->decimal($input['weight_kg'] ?? null, false);

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

        Database::beginTransaction($this->pdo);
        try {
            $this->pdo->prepare(
                'UPDATE users SET name = ?, gender = ?, age = ?, height_cm = ?, training_experience = ? '
                . 'WHERE user_id = ?'
            )->execute([$name, $gender ?: null, $age, $height, $experience, $userId]);
            $this->upsertTodayWeight($userId, (float) $weight);
            $this->syncProfileCompletion($userId);
            $this->pdo->commit();
            return $this->profile($userId);
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function updateTrainingSettings(int $userId, array $input): array
    {
        $goalId = $this->strictInteger($input['training_goal_id'] ?? null);
        $days = $this->strictInteger($input['training_days_per_week'] ?? null);
        $duration = $this->strictInteger($input['training_duration_minutes'] ?? null);
        if ($goalId === false || $days === false || $duration === false
            || $days < 2 || $days > 6 || !in_array($duration, [30, 60, 90], true)) {
            throw new ApiException(422, 'INVALID_TRAINING_SETTINGS', '訓練目標、天數或時間不正確。');
        }
        Database::beginTransaction($this->pdo);
        try {
            $this->lockUser($userId);
            $goal = $this->pdo->prepare('SELECT 1 FROM training_goals WHERE training_goal_id = ?');
            $goal->execute([$goalId]);
            if (!$goal->fetchColumn()) {
                throw new ApiException(422, 'INVALID_TRAINING_GOAL', '訓練目標不存在。');
            }
            $this->pdo->prepare(
                'UPDATE users SET training_goal_id = ?, training_days_per_week = ?, '
                . 'training_duration_minutes = ? WHERE user_id = ?'
            )->execute([$goalId, $days, $duration, $userId]);
            $this->syncProfileCompletion($userId);
            $this->pdo->commit();
            return $this->profile($userId);
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function updateBodyParts(int $userId, array $input): array
    {
        $ids = $input['body_part_ids'] ?? null;
        if (!is_array($ids) || count($ids) < 1 || count($ids) > 8) {
            throw new ApiException(422, 'INVALID_BODY_PARTS', '請選擇 1 到 8 個部位。');
        }
        $validatedIds = [];
        foreach ($ids as $id) {
            $validated = $this->strictInteger($id);
            if ($validated === false || $validated < 1) {
                throw new ApiException(422, 'INVALID_BODY_PARTS', '身體部位 ID 必須是正整數。');
            }
            $validatedIds[] = $validated;
        }
        $ids = $validatedIds;
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

        Database::beginTransaction($this->pdo);
        try {
            $this->lockUser($userId);
            $this->pdo->prepare('DELETE FROM user_body_parts WHERE user_id = ?')->execute([$userId]);
            $insert = $this->pdo->prepare(
                'INSERT INTO user_body_parts (user_id, body_part_id, priority) VALUES (?, ?, ?)'
            );
            foreach ($ids as $index => $bodyPartId) {
                $insert->execute([$userId, $bodyPartId, $index + 1]);
            }
            $this->syncProfileCompletion($userId);
            $this->pdo->commit();
            return $this->profile($userId);
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function exercises(): array
    {
        $where = ['e.is_active = TRUE'];
        $params = [];
        if (isset($_GET['q'], $_GET['keyword']) && $_GET['q'] !== '' && $_GET['keyword'] !== '') {
            throw new ApiException(422, 'INVALID_KEYWORD', 'q 與 keyword 不可同時提供。');
        }
        $query = trim(isset($_GET['keyword']) ? $this->queryString('keyword') : $this->queryString('q'));
        if (mb_strlen($query) > 100) {
            throw new ApiException(422, 'INVALID_KEYWORD', '搜尋關鍵字不可超過 100 個字。');
        }
        $partId = $this->optionalQueryInteger('body_part_id');
        $difficulty = trim($this->queryString('difficulty_level'));
        if ($query !== '') {
            $where[] = '(LOWER(ev.exercise_name) LIKE LOWER(?) OR LOWER(bp.body_part_name) LIKE LOWER(?))';
            $params[] = '%' . $query . '%';
            $params[] = '%' . $query . '%';
        }
        if ($partId !== null) {
            $part = $this->pdo->prepare('SELECT 1 FROM body_parts WHERE body_part_id = ?');
            $part->execute([$partId]);
            if (!$part->fetchColumn()) {
                throw new ApiException(422, 'INVALID_BODY_PART', '身體部位篩選不存在。');
            }
            $where[] = 'e.body_part_id = ?';
            $params[] = $partId;
        }
        if ($difficulty !== '' && !in_array($difficulty, ['Beginner', 'Intermediate', 'Advanced'], true)) {
            throw new ApiException(422, 'INVALID_DIFFICULTY', '動作難度篩選不正確。');
        }
        if ($difficulty !== '') {
            $where[] = 'ev.difficulty_level = ?';
            $params[] = $difficulty;
        }
        [$page, $pageSize, $offset] = $this->pagination();
        $from = ' FROM exercises e '
            . 'JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE ev.version_no = (SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id = e.exercise_id) AND '
            . implode(' AND ', $where);
        $count = $this->pdo->prepare('SELECT COUNT(*)' . $from);
        $count->execute($params);
        $statement = $this->pdo->prepare(
            'SELECT e.exercise_id, e.body_part_id, e.is_active, ev.exercise_version_id, ev.version_no, '
            . 'ev.exercise_name, ev.difficulty_level, ev.equipment, ev.description, ev.image_url, bp.body_part_name'
            . $from
            . " ORDER BY ev.exercise_name, e.exercise_id LIMIT {$pageSize} OFFSET {$offset}"
        );
        $statement->execute($params);
        $items = $statement->fetchAll();
        return ['items' => $items, 'page' => $page, 'page_size' => $pageSize, 'total' => (int) $count->fetchColumn()];
    }

    private function exerciseOptions(): array
    {
        $statement = $this->pdo->query(
            'SELECT e.exercise_id, e.body_part_id, ev.exercise_name, ev.difficulty_level, '
            . 'ev.equipment, ev.image_url, bp.body_part_name '
            . 'FROM exercises e JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE e.is_active = TRUE '
            . 'AND ev.version_no = (SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id = e.exercise_id) '
            . 'ORDER BY bp.body_part_id, ev.exercise_name, e.exercise_id'
        );
        $items = $statement->fetchAll();
        return ['items' => $items, 'total' => count($items)];
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

        Database::beginTransaction($this->pdo);
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
                'SELECT ev.exercise_version_id FROM exercises e JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
                . 'WHERE e.exercise_id = ? AND e.is_active = TRUE '
                . 'AND ev.version_no = (SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id = e.exercise_id)'
            );
            $update = $this->pdo->prepare(
                'UPDATE plan_exercises SET exercise_version_id = ?, target_sets = ?, target_reps = ?, '
                . 'rest_seconds = ?, target_weight_kg = ? WHERE plan_exercise_id = ?'
            );
            $seen = [];
            foreach ($items as $item) {
                if (!is_array($item)) {
                    throw new ApiException(422, 'INVALID_EXERCISES', '課表動作格式不正確。');
                }
                $this->assertAllowedFields($item, [
                    'plan_exercise_id', 'exercise_id', 'target_sets', 'target_reps',
                    'rest_seconds', 'target_weight_kg',
                ]);
                $planExerciseId = $this->strictInteger($item['plan_exercise_id'] ?? null);
                if ($planExerciseId === false || $planExerciseId <= 0 || in_array($planExerciseId, $seen, true)) {
                    throw new ApiException(422, 'INVALID_EXERCISES', '課表動作不可缺漏或重複。');
                }
                $seen[] = $planExerciseId;
                $ownership->execute([$planExerciseId, $planId, $userId]);
                if (!$ownership->fetchColumn()) {
                    throw new ApiException(404, 'PLAN_EXERCISE_NOT_FOUND', '找不到課表中的動作。');
                }
                $exerciseId = $this->strictInteger($item['exercise_id'] ?? null);
                $sets = $this->strictInteger($item['target_sets'] ?? null);
                $reps = $this->strictInteger($item['target_reps'] ?? null);
                $rest = $this->strictInteger($item['rest_seconds'] ?? null);
                $targetWeight = array_key_exists('target_weight_kg', $item)
                    ? $this->decimal($item['target_weight_kg'], true)
                    : null;
                if ($exerciseId === false || $sets === false || $reps === false || $rest === false) {
                    throw new ApiException(422, 'INVALID_PLAN_EXERCISE', '課表動作、組次或休息時間必須是整數。');
                }
                $exerciseExists->execute([$exerciseId]);
                $exerciseVersionId = $exerciseExists->fetchColumn();
                if (!$exerciseVersionId || $sets < 1 || $sets > 10
                    || $reps < 1 || $reps > 50 || $rest < 0 || $rest > 600
                    || ($targetWeight === false)) {
                    throw new ApiException(422, 'INVALID_PLAN_EXERCISE', '課表動作、組次或休息時間不正確。');
                }
                $update->execute([(int) $exerciseVersionId, $sets, $reps, $rest, $targetWeight, $planExerciseId]);
            }
            $this->pdo->commit();
            return PlanGenerator::findPlan($this->pdo, $userId, $planId);
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            if ($error instanceof \PDOException && $this->isPlanLockViolation($error)) {
                throw new ApiException(409, 'PLAN_IN_USE', '這份課表已有進行中的訓練，不能修改來源課表。');
            }
            throw $error;
        }
    }

    private function exerciseHistory(int $userId, int $exerciseId): array
    {
        $exists = $this->pdo->prepare('SELECT 1 FROM exercises WHERE exercise_id = ?');
        $exists->execute([$exerciseId]);
        if (!$exists->fetchColumn()) {
            throw new ApiException(404, 'EXERCISE_NOT_FOUND', '找不到這個動作。');
        }
        [$startDate, $endDate] = $this->dateRange();
        [$page, $pageSize, $offset] = $this->pagination();
        $status = $this->historyStatus();
        $where = ['ws.user_id = ?', 'ev.exercise_id = ?', $this->taipeiDateExpression('ws.started_at') . ' BETWEEN ? AND ?'];
        $params = [$userId, $exerciseId, $startDate, $endDate];
        if ($status !== null) {
            $where[] = 'ws.status = ?';
            $params[] = $status;
        } else {
            $where[] = "ws.status IN ('completed', 'cancelled')";
        }
        $from = ' FROM workout_sets wset '
            . 'JOIN workout_session_exercises wse ON wse.workout_session_exercise_id = wset.workout_session_exercise_id '
            . 'JOIN workout_sessions ws ON ws.workout_session_id = wse.workout_session_id '
            . 'JOIN exercise_versions ev ON ev.exercise_version_id = wse.exercise_version_id '
            . 'WHERE ' . implode(' AND ', $where);
        $count = $this->pdo->prepare('SELECT COUNT(*)' . $from);
        $count->execute($params);
        $statement = $this->pdo->prepare(
            'SELECT wset.*, wse.workout_session_id, ws.started_at, ws.status, ev.exercise_name, ev.version_no '
            . $from
            . " ORDER BY ws.started_at DESC, ws.workout_session_id DESC, wset.set_number LIMIT {$pageSize} OFFSET {$offset}"
        );
        $statement->execute($params);
        $items = $statement->fetchAll();
        return [
            'items' => $items,
            'page' => $page,
            'page_size' => $pageSize,
            'total' => (int) $count->fetchColumn(),
            'start_date' => $startDate,
            'end_date' => $endDate,
        ];
    }

    private function deletePlan(int $userId, int $planId): void
    {
        PlanGenerator::findPlan($this->pdo, $userId, $planId);
        $this->assertPlanNotActive($userId, $planId);
        $statement = $this->pdo->prepare(
            'UPDATE workout_plans SET archived_at = COALESCE(archived_at, CURRENT_TIMESTAMP) '
            . 'WHERE workout_plan_id = ? AND user_id = ?'
        );
        try {
            $statement->execute([$planId, $userId]);
        } catch (\PDOException $error) {
            if ($this->isPlanLockViolation($error)) {
                throw new ApiException(409, 'PLAN_IN_USE', '這份課表已有進行中的訓練，不能封存來源課表。');
            }
            throw $error;
        }
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
            throw new ApiException(
                409,
                'PLAN_IN_USE',
                '這份課表有進行中的訓練，不能修改或封存來源課表。'
                . '請到訓練頁使用「調整本次目標」，或先完成／取消場次後再編輯課表。'
            );
        }
    }

    private function startSession(int $userId, array $input): array
    {
        $planDayId = $this->strictInteger($input['plan_day_id'] ?? null);
        if ($planDayId === false) {
            throw new ApiException(422, 'INVALID_PLAN_DAY', '請選擇有效的課表日。');
        }
        Database::beginTransaction($this->pdo);
        try {
            $lockSql = 'SELECT user_id FROM users WHERE user_id = ?';
            if ((string) $this->pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql') {
                $lockSql .= ' FOR UPDATE';
            }
            $lock = $this->pdo->prepare($lockSql);
            $lock->execute([$userId]);
            if (!$lock->fetchColumn()) {
                throw new ApiException(404, 'USER_NOT_FOUND', '找不到使用者。');
            }
            $activeStatement = $this->pdo->prepare(
                "SELECT ws.workout_session_id, wsp.plan_day_id FROM workout_sessions ws "
                . 'JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id '
                . "WHERE ws.user_id = ? AND ws.status = 'in_progress'"
            );
            $activeStatement->execute([$userId]);
            $active = $activeStatement->fetch();
            if ($active) {
                $this->pdo->commit();
                if ((int) $active['plan_day_id'] === (int) $planDayId) {
                    return [200, $this->sessionDetail($userId, (int) $active['workout_session_id'])];
                }
                throw new ApiException(409, 'WORKOUT_ALREADY_ACTIVE', '已有另一個進行中的訓練。');
            }
            $day = $this->pdo->prepare(
                'SELECT pd.plan_day_id, wp.published_at, wp.archived_at FROM plan_days pd '
                . 'JOIN workout_plans wp ON wp.workout_plan_id = pd.workout_plan_id '
                . 'WHERE pd.plan_day_id = ? AND wp.user_id = ?'
                . (Database::driver() === 'pgsql' ? ' FOR UPDATE OF wp, pd' : '')
            );
            $day->execute([$planDayId, $userId]);
            $source = $day->fetch();
            if (!$source) {
                throw new ApiException(404, 'PLAN_DAY_NOT_FOUND', '找不到可開始的課表日。');
            }
            $inactive = $this->pdo->prepare(
                'SELECT COUNT(*) FROM plan_exercises pe '
                . 'JOIN exercise_versions ev ON ev.exercise_version_id = pe.exercise_version_id '
                . 'JOIN exercises e ON e.exercise_id = ev.exercise_id '
                . 'WHERE pe.plan_day_id = ? AND e.is_active = FALSE'
            );
            $inactive->execute([$planDayId]);
            if ($source['published_at'] === null || $source['archived_at'] !== null
                || (int) $inactive->fetchColumn() > 0) {
                throw new ApiException(409, 'PLAN_REQUIRES_UPDATE', '來源課表已封存或包含停用動作，請重新產生或更新課表。');
            }
            $sessionId = Database::insert(
                $this->pdo,
                "INSERT INTO workout_sessions (user_id, status) VALUES (?, 'in_progress')",
                [$userId],
                'workout_session_id'
            );
            $this->pdo->prepare(
                'INSERT INTO workout_session_plans (workout_session_id, plan_day_id) VALUES (?, ?)'
            )->execute([$sessionId, $planDayId]);
            $this->pdo->prepare(
                'INSERT INTO workout_session_exercises '
                . '(workout_session_id, plan_exercise_id, exercise_version_id, exercise_order, target_sets, target_reps, rest_seconds, target_weight_kg) '
                . 'SELECT ?, pe.plan_exercise_id, pe.exercise_version_id, pe.exercise_order, pe.target_sets, pe.target_reps, pe.rest_seconds, pe.target_weight_kg '
                . 'FROM plan_exercises pe WHERE pe.plan_day_id = ? ORDER BY pe.exercise_order'
            )->execute([$sessionId, $planDayId]);
            $count = $this->pdo->prepare('SELECT COUNT(*) FROM workout_session_exercises WHERE workout_session_id = ?');
            $count->execute([$sessionId]);
            if ((int) $count->fetchColumn() === 0) {
                throw new ApiException(409, 'EMPTY_PLAN_DAY', '這個課表日沒有可執行的動作。');
            }
            $this->pdo->commit();
            return [201, $this->sessionDetail($userId, $sessionId)];
        } catch (\PDOException $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            if ($error->getCode() === '23505' || str_contains($error->getMessage(), 'uq_workout_sessions_user_active')) {
                $active = $this->currentSession($userId);
                if ($active !== null && (int) $active['plan_day_id'] === (int) $planDayId) {
                    return [200, $active];
                }
                throw new ApiException(409, 'WORKOUT_ALREADY_ACTIVE', '已有另一個進行中的訓練。');
            }
            throw $error;
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
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
            'SELECT wse.*, ev.exercise_id, ev.version_no, ev.exercise_name, ev.difficulty_level, '
            . 'ev.equipment, ev.description, ev.image_url, bp.body_part_name '
            . 'FROM workout_session_exercises wse '
            . 'JOIN exercise_versions ev ON ev.exercise_version_id = wse.exercise_version_id '
            . 'JOIN exercises e ON e.exercise_id = ev.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE wse.workout_session_id = ? ORDER BY wse.exercise_order'
        );
        $exerciseStatement->execute([$sessionId]);
        $session['exercises'] = $exerciseStatement->fetchAll();
        $setStatement = $this->pdo->prepare(
            'SELECT wset.*, wse.workout_session_id, ev.exercise_id, ev.exercise_name '
            . 'FROM workout_sets wset '
            . 'JOIN workout_session_exercises wse ON wse.workout_session_exercise_id = wset.workout_session_exercise_id '
            . 'JOIN exercise_versions ev ON ev.exercise_version_id = wse.exercise_version_id '
            . 'WHERE wse.workout_session_id = ? ORDER BY wse.exercise_order, wset.set_number'
        );
        $setStatement->execute([$sessionId]);
        $session['sets'] = $setStatement->fetchAll();
        return $session;
    }

    private function saveSet(int $userId, int $sessionId, array $input): array
    {
        $sessionExerciseId = $this->strictInteger($input['workout_session_exercise_id'] ?? null);
        $setNumber = $this->strictInteger($input['set_number'] ?? null);
        $weight = $this->decimal($input['weight_kg'] ?? null, true);
        $reps = $this->strictInteger($input['reps'] ?? null);
        if ($sessionExerciseId === false || $setNumber === false || $weight === false || $reps === false
            || $setNumber < 1 || $setNumber > 100 || $weight < 0 || $weight > 999.99
            || $reps < 1 || $reps > 999) {
            throw new ApiException(422, 'INVALID_SET', '組數、重量或次數不正確。');
        }
        $existing = $this->pdo->prepare(
            'SELECT * FROM workout_sets WHERE workout_session_exercise_id = ? AND set_number = ?'
        );
        Database::beginTransaction($this->pdo);
        try {
            $allowedSql = 'SELECT ws.status FROM workout_session_exercises wse '
                . 'JOIN workout_sessions ws ON ws.workout_session_id = wse.workout_session_id '
                . 'WHERE ws.workout_session_id = ? AND ws.user_id = ? AND wse.workout_session_exercise_id = ?';
            if (Database::driver() === 'pgsql') {
                $allowedSql .= ' FOR UPDATE OF ws';
            }
            $allowed = $this->pdo->prepare($allowedSql);
            $allowed->execute([$sessionId, $userId, $sessionExerciseId]);
            $status = $allowed->fetchColumn();
            if ($status === false) {
                throw new ApiException(404, 'WORKOUT_NOT_FOUND', '找不到訓練或動作不在課表中。');
            }
            if ($status !== 'in_progress') {
                throw new ApiException(409, 'WORKOUT_FINISHED', '這次訓練已結束，不能新增組數。');
            }
            $existing->execute([$sessionExerciseId, $setNumber]);
            $row = $existing->fetch();
            if ($row) {
                if ((float) $row['weight_kg'] === (float) $weight && (int) $row['reps'] === (int) $reps) {
                    $row['set_volume'] = (float) $row['weight_kg'] * (int) $row['reps'];
                    $this->pdo->commit();
                    return [200, $row];
                }
                throw new ApiException(409, 'SET_ALREADY_EXISTS', '這一組已有不同資料，請改用編輯功能。');
            }
            $workoutSetId = Database::insert(
                $this->pdo,
                'INSERT INTO workout_sets (workout_session_exercise_id, set_number, weight_kg, reps) VALUES (?, ?, ?, ?)',
                [$sessionExerciseId, $setNumber, $weight, $reps],
                'workout_set_id'
            );
            $this->pdo->commit();
        } catch (\PDOException $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            if ($error->getCode() !== '23505'
                && !str_contains(strtolower($error->getMessage()), 'unique constraint')) {
                throw $error;
            }
            $existing->execute([$sessionExerciseId, $setNumber]);
            $row = $existing->fetch();
            if ($row && (float) $row['weight_kg'] === (float) $weight && (int) $row['reps'] === (int) $reps) {
                $row['set_volume'] = (float) $row['weight_kg'] * (int) $row['reps'];
                return [200, $row];
            }
            throw new ApiException(409, 'SET_ALREADY_EXISTS', '這一組已有不同資料，請改用編輯功能。');
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
        return [201, [
            'workout_set_id' => $workoutSetId,
            'workout_session_id' => $sessionId,
            'workout_session_exercise_id' => $sessionExerciseId,
            'set_number' => $setNumber,
            'weight_kg' => number_format((float) $weight, 2, '.', ''),
            'reps' => $reps,
            'set_volume' => (float) $weight * (int) $reps,
        ]];
    }

    private function updateSessionExercise(int $userId, int $sessionId, int $sessionExerciseId, array $input): array
    {
        Database::beginTransaction($this->pdo);
        try {
            $sql = 'SELECT wse.*, ws.status FROM workout_session_exercises wse '
                . 'JOIN workout_sessions ws ON ws.workout_session_id = wse.workout_session_id '
                . 'WHERE wse.workout_session_exercise_id = ? AND ws.workout_session_id = ? AND ws.user_id = ?';
            if (Database::driver() === 'pgsql') {
                $sql .= ' FOR UPDATE OF ws, wse';
            }
            $statement = $this->pdo->prepare($sql);
            $statement->execute([$sessionExerciseId, $sessionId, $userId]);
            $item = $statement->fetch();
            if (!$item) {
                throw new ApiException(404, 'SESSION_EXERCISE_NOT_FOUND', '找不到本次運動的動作。');
            }
            if ($item['status'] !== 'in_progress') {
                throw new ApiException(409, 'WORKOUT_FINISHED', '只能調整進行中場次的目標。');
            }
            $sets = $this->strictInteger($input['target_sets'] ?? $item['target_sets']);
            $reps = $this->strictInteger($input['target_reps'] ?? $item['target_reps']);
            $rest = $this->strictInteger($input['rest_seconds'] ?? $item['rest_seconds']);
            $weight = array_key_exists('target_weight_kg', $input)
                ? $this->decimal($input['target_weight_kg'], true)
                : ($item['target_weight_kg'] === null ? null : (float) $item['target_weight_kg']);
            $completed = $this->pdo->prepare('SELECT COUNT(*) FROM workout_sets WHERE workout_session_exercise_id = ?');
            $completed->execute([$sessionExerciseId]);
            if ($sets === false || $sets < (int) $completed->fetchColumn() || $sets > 10
                || $reps === false || $reps < 1 || $reps > 50
                || $rest === false || $rest < 0 || $rest > 600 || $weight === false) {
                throw new ApiException(422, 'INVALID_SESSION_TARGET', '目標組數不得低於已完成組數，且重量、次數或休息秒數須在允許範圍。');
            }
            $this->pdo->prepare(
                'UPDATE workout_session_exercises SET target_sets = ?, target_reps = ?, rest_seconds = ?, target_weight_kg = ? '
                . 'WHERE workout_session_exercise_id = ?'
            )->execute([$sets, $reps, $rest, $weight, $sessionExerciseId]);
            $this->pdo->commit();
            $item['target_sets'] = $sets;
            $item['target_reps'] = $reps;
            $item['rest_seconds'] = $rest;
            $item['target_weight_kg'] = $weight;
            return $item;
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
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
        Database::beginTransaction($this->pdo);
        try {
            $sql = 'SELECT * FROM workout_sessions WHERE workout_session_id = ? AND user_id = ?';
            if (Database::driver() === 'pgsql') {
                $sql .= ' FOR UPDATE';
            }
            $statement = $this->pdo->prepare($sql);
            $statement->execute([$sessionId, $userId]);
            $session = $statement->fetch();
            if (!$session) {
                throw new ApiException(404, 'WORKOUT_NOT_FOUND', '找不到這次訓練。');
            }
            if ($session['status'] !== $targetStatus && $session['status'] !== 'in_progress') {
                throw new ApiException(409, 'INVALID_WORKOUT_STATE', '訓練狀態不能再次轉換。');
            }
            if ($session['status'] === 'in_progress') {
                if ($targetStatus === 'completed') {
                    $count = $this->pdo->prepare(
                        'SELECT COUNT(*) FROM workout_sets wset JOIN workout_session_exercises wse '
                        . 'ON wse.workout_session_exercise_id = wset.workout_session_exercise_id WHERE wse.workout_session_id = ?'
                    );
                    $count->execute([$sessionId]);
                    if ((int) $count->fetchColumn() === 0) {
                        throw new ApiException(409, 'EMPTY_WORKOUT', '至少儲存一組後才能完成訓練。');
                    }
                }
                $this->pdo->prepare(
                    "UPDATE workout_sessions SET status = ?, ended_at = CURRENT_TIMESTAMP, notes = ? "
                    . "WHERE workout_session_id = ? AND user_id = ? AND status = 'in_progress'"
                )->execute([$targetStatus, $notes === '' ? null : $notes, $sessionId, $userId]);
            }
            $this->pdo->commit();
            return $this->sessionDetail($userId, $sessionId);
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function updateSet(int $userId, int $setId, array $input): array
    {
        Database::beginTransaction($this->pdo);
        try {
            $sql = 'SELECT wset.*, wse.workout_session_id, ws.status FROM workout_sets wset '
                . 'JOIN workout_session_exercises wse ON wse.workout_session_exercise_id = wset.workout_session_exercise_id '
                . 'JOIN workout_sessions ws ON ws.workout_session_id = wse.workout_session_id '
                . 'WHERE wset.workout_set_id = ? AND ws.user_id = ?';
            if (Database::driver() === 'pgsql') {
                $sql .= ' FOR UPDATE OF ws, wset';
            }
            $statement = $this->pdo->prepare($sql);
            $statement->execute([$setId, $userId]);
            $set = $statement->fetch();
            if (!$set) {
                throw new ApiException(404, 'WORKOUT_SET_NOT_FOUND', '找不到這組訓練紀錄。');
            }
            if ($set['status'] === 'cancelled') {
                throw new ApiException(409, 'WORKOUT_CANCELLED', '取消的訓練不能修改組數。');
            }
            $weight = $this->decimal($input['weight_kg'] ?? $set['weight_kg'], true);
            $reps = $this->strictInteger($input['reps'] ?? $set['reps']);
            if ($weight === false || $weight < 0 || $weight > 999.99
                || $reps === false || $reps < 1 || $reps > 999) {
                throw new ApiException(422, 'INVALID_SET', '重量或次數不正確。');
            }
            $this->pdo->prepare(
                'UPDATE workout_sets SET weight_kg = ?, reps = ? WHERE workout_set_id = ?'
            )->execute([$weight, $reps, $setId]);
            $this->pdo->commit();
            $set['weight_kg'] = number_format((float) $weight, 2, '.', '');
            $set['reps'] = $reps;
            $set['set_volume'] = (float) $weight * (int) $reps;
            return $set;
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function deleteSet(int $userId, int $setId): void
    {
        Database::beginTransaction($this->pdo);
        try {
            $sql = 'SELECT wse.workout_session_id, ws.status FROM workout_sets wset '
                . 'JOIN workout_session_exercises wse ON wse.workout_session_exercise_id = wset.workout_session_exercise_id '
                . 'JOIN workout_sessions ws ON ws.workout_session_id = wse.workout_session_id '
                . 'WHERE wset.workout_set_id = ? AND ws.user_id = ?';
            if (Database::driver() === 'pgsql') {
                $sql .= ' FOR UPDATE OF ws, wset';
            }
            $statement = $this->pdo->prepare($sql);
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
                    'SELECT COUNT(*) FROM workout_sets wset JOIN workout_session_exercises wse '
                    . 'ON wse.workout_session_exercise_id = wset.workout_session_exercise_id WHERE wse.workout_session_id = ?'
                );
                $count->execute([(int) $set['workout_session_id']]);
                if ((int) $count->fetchColumn() <= 1) {
                    throw new ApiException(409, 'LAST_SET', '完成的訓練至少要保留一組。');
                }
            }
            $this->pdo->prepare('DELETE FROM workout_sets WHERE workout_set_id = ?')->execute([$setId]);
            $this->pdo->commit();
        } catch (\PDOException $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            if ($error->getCode() === '23514') {
                throw new ApiException(409, 'LAST_SET', '完成的訓練至少要保留一組。');
            }
            throw $error;
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function deleteSession(int $userId, int $sessionId): void
    {
        Database::beginTransaction($this->pdo);
        try {
            $sql = 'SELECT status FROM workout_sessions WHERE workout_session_id = ? AND user_id = ?';
            if (Database::driver() === 'pgsql') {
                $sql .= ' FOR UPDATE';
            }
            $statement = $this->pdo->prepare($sql);
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
            $this->pdo->commit();
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function history(int $userId, ?array $forcedRange = null, bool $completedOnly = false): array
    {
        [$startDate, $endDate] = $forcedRange ?? $this->dateRange();
        [$page, $pageSize, $offset] = $this->pagination();
        $where = ['ws.user_id = ?', $this->taipeiDateExpression('ws.started_at') . ' BETWEEN ? AND ?'];
        $params = [$userId, $startDate, $endDate];
        $status = $completedOnly ? 'completed' : $this->historyStatus();
        if ($status !== null) {
            $where[] = 'ws.status = ?';
            $params[] = $status;
        } else {
            $where[] = "ws.status IN ('completed', 'cancelled')";
        }
        if (!$completedOnly) {
            $exerciseId = $this->optionalQueryInteger('exercise_id');
            if ($exerciseId !== null) {
                $where[] = 'EXISTS (SELECT 1 FROM workout_session_exercises filtered_wse '
                    . 'JOIN exercise_versions filtered_ev ON filtered_ev.exercise_version_id = filtered_wse.exercise_version_id '
                    . 'WHERE filtered_wse.workout_session_id = ws.workout_session_id AND filtered_ev.exercise_id = ?)';
                $params[] = $exerciseId;
            }
        }
        $whereSql = implode(' AND ', $where);
        $count = $this->pdo->prepare('SELECT COUNT(*) FROM workout_sessions ws WHERE ' . $whereSql);
        $count->execute($params);
        $statement = $this->pdo->prepare(
            "SELECT ws.workout_session_id, ws.status, ws.started_at, ws.ended_at, ws.notes, "
            . 'pd.day_title, wp.plan_name, COUNT(wset.workout_set_id) AS set_count, '
            . 'COALESCE(SUM(wset.weight_kg * wset.reps), 0) AS total_volume '
            . 'FROM workout_sessions ws '
            . 'LEFT JOIN workout_session_plans wsp ON wsp.workout_session_id = ws.workout_session_id '
            . 'LEFT JOIN plan_days pd ON pd.plan_day_id = wsp.plan_day_id '
            . 'LEFT JOIN workout_plans wp ON wp.workout_plan_id = pd.workout_plan_id '
            . 'LEFT JOIN workout_session_exercises wse ON wse.workout_session_id = ws.workout_session_id '
            . 'LEFT JOIN workout_sets wset ON wset.workout_session_exercise_id = wse.workout_session_exercise_id '
            . 'WHERE ' . $whereSql . ' '
            . 'GROUP BY ws.workout_session_id, ws.status, ws.started_at, ws.ended_at, ws.notes, '
            . "pd.day_title, wp.plan_name ORDER BY ws.started_at DESC, ws.workout_session_id DESC LIMIT {$pageSize} OFFSET {$offset}"
        );
        $statement->execute($params);
        $items = $statement->fetchAll();
        return [
            'items' => $items,
            'page' => $page,
            'page_size' => $pageSize,
            'total' => (int) $count->fetchColumn(),
            'start_date' => $startDate,
            'end_date' => $endDate,
        ];
    }

    private function dashboard(int $userId): array
    {
        [$startDate, $endDate] = $this->dateRange();
        $statement = $this->pdo->prepare(
            "SELECT ws.workout_session_id, ws.started_at, wset.workout_set_id, ev.exercise_id, "
            . 'e.body_part_id, wset.weight_kg, wset.reps, ev.exercise_name, bp.body_part_name '
            . 'FROM workout_sessions ws '
            . 'JOIN workout_session_exercises wse ON wse.workout_session_id = ws.workout_session_id '
            . 'JOIN workout_sets wset ON wset.workout_session_exercise_id = wse.workout_session_exercise_id '
            . 'JOIN exercise_versions ev ON ev.exercise_version_id = wse.exercise_version_id '
            . 'JOIN exercises e ON e.exercise_id = ev.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . "WHERE ws.user_id = ? AND ws.status = 'completed' AND "
            . $this->taipeiDateExpression('ws.started_at') . ' BETWEEN ? AND ? '
            . 'ORDER BY ws.started_at, ws.workout_session_id, wset.workout_set_id'
        );
        $statement->execute([$userId, $startDate, $endDate]);
        $rows = $statement->fetchAll();
        $sessions = [];
        $weekly = [];
        $bodyParts = [];
        $exercises = [];
        $totalVolume = 0.0;
        $totalReps = 0;
        $bodyweightReps = 0;
        foreach ($rows as $row) {
            $volume = (float) $row['weight_kg'] * (int) $row['reps'];
            $totalVolume += $volume;
            $totalReps += (int) $row['reps'];
            if ((float) $row['weight_kg'] === 0.0) {
                $bodyweightReps += (int) $row['reps'];
            }
            $sessions[(int) $row['workout_session_id']] = true;
            $startedAt = $this->taipeiDateTime((string) $row['started_at']);
            $week = $startedAt->modify('monday this week')->format('Y-m-d');
            $weekly[$week] ??= ['week' => $week, 'volume' => 0.0, 'sessions' => []];
            $weekly[$week]['volume'] += $volume;
            $weekly[$week]['sessions'][(int) $row['workout_session_id']] = true;
            $bodyPartId = (int) $row['body_part_id'];
            $bodyParts[$bodyPartId] ??= [
                'body_part_id' => $bodyPartId,
                'body_part_name' => (string) $row['body_part_name'],
                'completed_sets' => 0,
            ];
            $bodyParts[$bodyPartId]['completed_sets']++;
            $exerciseId = (int) $row['exercise_id'];
            $exercises[$exerciseId] ??= [
                'exercise_id' => $exerciseId,
                'exercise_name' => (string) $row['exercise_name'],
                'name_label' => '最近訓練時名稱',
                'completed_sets' => 0,
            ];
            $exercises[$exerciseId]['exercise_name'] = (string) $row['exercise_name'];
            $exercises[$exerciseId]['completed_sets']++;
        }
        $bodyPartRanking = array_values($bodyParts);
        usort($bodyPartRanking, static fn (array $a, array $b): int =>
            $b['completed_sets'] <=> $a['completed_sets'] ?: $a['body_part_id'] <=> $b['body_part_id']);
        $exerciseRanking = array_values($exercises);
        usort($exerciseRanking, static fn (array $a, array $b): int =>
            $b['completed_sets'] <=> $a['completed_sets'] ?: $a['exercise_id'] <=> $b['exercise_id']);
        ksort($weekly);
        $volumeByWeek = array_map(static fn (array $item): array => [
            'week' => $item['week'],
            'volume' => round((float) $item['volume'], 2),
            'session_count' => count($item['sessions']),
        ], array_values($weekly));
        $weightStatement = $this->pdo->prepare(
            'SELECT * FROM body_records WHERE user_id = ? AND record_date BETWEEN ? AND ? '
            . 'ORDER BY record_date, body_record_id'
        );
        $weightStatement->execute([$userId, $startDate, $endDate]);
        $weights = $weightStatement->fetchAll();
        $latestWeight = $weights !== [] ? $weights[array_key_last($weights)]['weight_kg'] : null;
        $averageWeight = $weights === [] ? null : array_sum(array_map(
            static fn (array $row): float => (float) $row['weight_kg'],
            $weights
        )) / count($weights);
        return [
            'start_date' => $startDate,
            'end_date' => $endDate,
            'session_count' => count($sessions),
            'set_count' => count($rows),
            'completed_sets' => count($rows),
            'total_volume' => round($totalVolume, 2),
            'weighted_volume' => round($totalVolume, 2),
            'external_load_volume_kg_reps' => round($totalVolume, 2),
            'total_reps' => $totalReps,
            'bodyweight_reps' => $bodyweightReps,
            'latest_weight' => $latestWeight,
            'average_weight' => $averageWeight === null ? null : round($averageWeight, 2),
            'favorite_body_part' => $bodyPartRanking[0]['body_part_name'] ?? null,
            'favorite_exercise' => $exerciseRanking[0]['exercise_name'] ?? null,
            'body_part_ranking' => $bodyPartRanking,
            'exercise_ranking' => $exerciseRanking,
            'volume_by_week' => $volumeByWeek,
            'weight_history' => array_map(
                static fn (array $item): array => [
                    'date' => $item['record_date'],
                    'weight' => (float) $item['weight_kg'],
                ],
                $weights
            ),
            'recent_workouts' => array_slice($this->history($userId, [$startDate, $endDate], true)['items'], 0, 5),
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
        $weight = $this->decimal($input['weight_kg'] ?? null, false);
        $notes = trim((string) ($input['notes'] ?? ''));
        $parsedDate = \DateTimeImmutable::createFromFormat('!Y-m-d', $date);
        if (!$parsedDate || $parsedDate->format('Y-m-d') !== $date
            || $date < '1900-01-01' || $date > date('Y-m-d')) {
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
        try {
            $bodyRecordId = Database::insert(
                $this->pdo,
                'INSERT INTO body_records (user_id, record_date, weight_kg, notes) VALUES (?, ?, ?, ?)',
                [$userId, $date, $weight, $notes === '' ? null : $notes],
                'body_record_id'
            );
        } catch (\PDOException $error) {
            if ($this->isUniqueViolation($error)) {
                throw new ApiException(409, 'BODY_RECORD_EXISTS', '這一天已有體重紀錄。');
            }
            throw $error;
        }
        $this->syncProfileCompletion($userId);
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
        $weight = $this->decimal($input['weight_kg'] ?? $record['weight_kg'], false);
        $notes = (string) ($input['notes'] ?? $record['notes'] ?? '');
        $parsedDate = \DateTimeImmutable::createFromFormat('!Y-m-d', $date);
        if (!$parsedDate || $parsedDate->format('Y-m-d') !== $date
            || $date < '1900-01-01' || $date > date('Y-m-d')
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
        try {
            $this->pdo->prepare(
                'UPDATE body_records SET record_date = ?, weight_kg = ?, notes = ? '
                . 'WHERE body_record_id = ? AND user_id = ?'
            )->execute([$date, $weight, trim($notes) === '' ? null : trim($notes), $recordId, $userId]);
        } catch (\PDOException $error) {
            if ($this->isUniqueViolation($error)) {
                throw new ApiException(409, 'BODY_RECORD_EXISTS', '這一天已有其他體重紀錄。');
            }
            throw $error;
        }
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
        Database::beginTransaction($this->pdo);
        try {
            $lockSql = 'SELECT profile_completed_at FROM users WHERE user_id = ?';
            if (Database::driver() === 'pgsql') {
                $lockSql .= ' FOR UPDATE';
            }
            $lock = $this->pdo->prepare($lockSql);
            $lock->execute([$userId]);
            $completed = $lock->fetchColumn();
            $count = $this->pdo->prepare('SELECT COUNT(*) FROM body_records WHERE user_id = ?');
            $count->execute([$userId]);
            if ($completed !== false && $completed !== null && (int) $count->fetchColumn() <= 1) {
                throw new ApiException(409, 'LAST_BODY_RECORD_REQUIRED', '已完成基本資料後，至少要保留一筆體重紀錄；你可以修改這筆紀錄。');
            }
            $statement = $this->pdo->prepare(
                'DELETE FROM body_records WHERE body_record_id = ? AND user_id = ?'
            );
            $statement->execute([$recordId, $userId]);
            if ($statement->rowCount() === 0) {
                throw new ApiException(404, 'BODY_RECORD_NOT_FOUND', '找不到這筆體重紀錄。');
            }
            $this->pdo->commit();
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
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
            'SELECT e.exercise_id, e.body_part_id, e.is_active, ev.exercise_version_id, ev.version_no, '
            . 'ev.exercise_name, ev.difficulty_level, ev.equipment, ev.description, ev.image_url, bp.body_part_name '
            . 'FROM exercises e JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE ev.version_no = (SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id = e.exercise_id) '
            . 'ORDER BY e.exercise_id'
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
            if (array_key_exists('ip_hash', $row)) {
                $row['ip_hash'] = '[已隱藏]';
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
                'sql' => 'SELECT ev.exercise_name, bp.body_part_name, ev.difficulty_level, ev.equipment FROM exercises e JOIN exercise_versions ev ON ev.exercise_id=e.exercise_id JOIN body_parts bp ON bp.body_part_id=e.body_part_id WHERE e.is_active=TRUE AND ev.version_no=(SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id=e.exercise_id) ORDER BY bp.body_part_id, ev.exercise_name LIMIT 8;',
            ],
            [
                'title' => 'GROUP BY：各部位動作數量',
                'sql' => 'SELECT bp.body_part_name, COUNT(e.exercise_id) AS exercise_count, SUM(CASE WHEN e.is_active = TRUE THEN 1 ELSE 0 END) AS active_count FROM body_parts bp LEFT JOIN exercises e ON e.body_part_id = bp.body_part_id GROUP BY bp.body_part_id, bp.body_part_name ORDER BY bp.body_part_id;',
            ],
            [
                'title' => 'Aggregate：完成場次的外加重量訓練量',
                'sql' => "SELECT ev.exercise_name, COUNT(wset.workout_set_id) AS working_sets, COALESCE(SUM(wset.weight_kg * wset.reps),0) AS external_load_volume FROM workout_sets wset JOIN workout_session_exercises wse ON wse.workout_session_exercise_id=wset.workout_session_exercise_id JOIN workout_sessions ws ON ws.workout_session_id=wse.workout_session_id JOIN exercise_versions ev ON ev.exercise_version_id=wse.exercise_version_id WHERE ws.status='completed' GROUP BY ev.exercise_version_id, ev.exercise_name ORDER BY external_load_volume DESC LIMIT 8;",
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
        Database::beginTransaction($this->pdo);
        try {
            $exerciseId = Database::insert(
                $this->pdo,
                'INSERT INTO exercises (body_part_id, is_active) VALUES (?, ?)',
                [(int) $values[1], (bool) $values[6]],
                'exercise_id'
            );
            $this->pdo->prepare(
                'INSERT INTO exercise_versions '
                . '(exercise_id, version_no, exercise_name, difficulty_level, equipment, description, image_url) '
                . 'VALUES (?, 1, ?, ?, ?, ?, ?)'
            )->execute([$exerciseId, $values[0], $values[2], $values[3], $values[4], $values[5]]);
            $this->pdo->commit();
            return $this->findExercise($exerciseId);
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function updateExercise(int $exerciseId, array $input): array
    {
        if ($input === []) {
            throw new ApiException(422, 'NO_FIELDS', '沒有可更新的欄位。');
        }
        Database::beginTransaction($this->pdo);
        try {
            if (Database::driver() === 'pgsql') {
                $lock = $this->pdo->prepare('SELECT exercise_id FROM exercises WHERE exercise_id = ? FOR UPDATE');
                $lock->execute([$exerciseId]);
                if (!$lock->fetchColumn()) {
                    throw new ApiException(404, 'EXERCISE_NOT_FOUND', '找不到這個動作。');
                }
            }
            $current = $this->findExercise($exerciseId);
            if (array_key_exists('body_part_id', $input)
                && (int) $input['body_part_id'] !== (int) $current['body_part_id']) {
                throw new ApiException(409, 'EXERCISE_IDENTITY_IMMUTABLE', '主訓練部位屬於動作身份；請新增動作並停用舊動作。');
            }
            $merged = array_merge($current, $input, ['body_part_id' => (int) $current['body_part_id']]);
            $imageChanged = array_key_exists('image_url', $input)
                && (string) ($input['image_url'] ?? '') !== (string) ($current['image_url'] ?? '');
            $values = $this->validateExerciseInput($merged, $imageChanged);
            $descriptive = ['exercise_name', 'difficulty_level', 'equipment', 'description', 'image_url'];
            $needsVersion = false;
            foreach ($descriptive as $field) {
                if (array_key_exists($field, $input)
                    && (string) ($input[$field] ?? '') !== (string) ($current[$field] ?? '')) {
                    $needsVersion = true;
                }
            }
            if (array_key_exists('is_active', $input)) {
                $this->pdo->prepare('UPDATE exercises SET is_active = ? WHERE exercise_id = ?')
                    ->execute([(bool) $values[6], $exerciseId]);
            }
            if ($needsVersion) {
                $lockSql = 'SELECT COALESCE(MAX(version_no), 0) FROM exercise_versions WHERE exercise_id = ?';
                $version = $this->pdo->prepare($lockSql);
                $version->execute([$exerciseId]);
                $next = (int) $version->fetchColumn() + 1;
                $this->pdo->prepare(
                    'INSERT INTO exercise_versions '
                    . '(exercise_id, version_no, exercise_name, difficulty_level, equipment, description, image_url) '
                    . 'VALUES (?, ?, ?, ?, ?, ?, ?)'
                )->execute([$exerciseId, $next, $values[0], $values[2], $values[3], $values[4], $values[5]]);
            }
            $this->pdo->commit();
            return $this->findExercise($exerciseId);
        } catch (\Throwable $error) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $error;
        }
    }

    private function deleteExercise(int $exerciseId): void
    {
        $statement = $this->pdo->prepare('UPDATE exercises SET is_active = FALSE WHERE exercise_id = ?');
        $statement->execute([$exerciseId]);
        if ($statement->rowCount() === 0) {
            throw new ApiException(404, 'EXERCISE_NOT_FOUND', '找不到這個動作。');
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

    private function validateExerciseInput(array $input, bool $requireHttpsImage): array
    {
        $name = trim((string) ($input['exercise_name'] ?? ''));
        $bodyPartId = $this->strictInteger($input['body_part_id'] ?? null);
        $difficulty = (string) ($input['difficulty_level'] ?? '');
        $equipment = trim((string) ($input['equipment'] ?? ''));
        $description = trim((string) ($input['description'] ?? ''));
        $imageUrl = trim((string) ($input['image_url'] ?? ''));
        $activeValue = $input['is_active'] ?? true;
        $active = is_bool($activeValue)
            ? $activeValue
            : (is_int($activeValue) && in_array($activeValue, [0, 1], true) ? (bool) $activeValue : null);
        if ($name === '' || mb_strlen($name) > 120 || $bodyPartId === false
            || !in_array($difficulty, ['Beginner', 'Intermediate', 'Advanced'], true)
            || $description === '' || mb_strlen($description) > 4000 || mb_strlen($equipment) > 100
            || mb_strlen($imageUrl) > 2048 || $active === null
            || ($requireHttpsImage && $imageUrl !== ''
                && (!filter_var($imageUrl, FILTER_VALIDATE_URL)
                    || !str_starts_with(strtolower($imageUrl), 'https://')))) {
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
            'SELECT e.exercise_id, e.body_part_id, e.is_active, ev.exercise_version_id, ev.version_no, '
            . 'ev.exercise_name, ev.difficulty_level, ev.equipment, ev.description, ev.image_url, bp.body_part_name '
            . 'FROM exercises e JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
            . 'JOIN body_parts bp ON bp.body_part_id = e.body_part_id '
            . 'WHERE e.exercise_id = ? AND ev.version_no = '
            . '(SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id = e.exercise_id)'
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

    private function syncProfileCompletion(int $userId): void
    {
        $statement = $this->pdo->prepare(
            'SELECT age, height_cm, training_experience, training_goal_id, '
            . 'training_days_per_week, training_duration_minutes FROM users WHERE user_id = ?'
        );
        $statement->execute([$userId]);
        $user = $statement->fetch();
        if (!$user || in_array(null, $user, true)) {
            return;
        }
        $part = $this->pdo->prepare('SELECT 1 FROM user_body_parts WHERE user_id = ? LIMIT 1');
        $part->execute([$userId]);
        $weight = $this->pdo->prepare('SELECT 1 FROM body_records WHERE user_id = ? LIMIT 1');
        $weight->execute([$userId]);
        if ($part->fetchColumn() && $weight->fetchColumn()) {
            $this->pdo->prepare(
                'UPDATE users SET profile_completed_at = COALESCE(profile_completed_at, CURRENT_TIMESTAMP) '
                . 'WHERE user_id = ?'
            )->execute([$userId]);
        }
    }

    private function lockUser(int $userId): void
    {
        $sql = 'SELECT user_id FROM users WHERE user_id = ?';
        if (Database::driver() === 'pgsql') {
            $sql .= ' FOR UPDATE';
        }
        $statement = $this->pdo->prepare($sql);
        $statement->execute([$userId]);
        if (!$statement->fetchColumn()) {
            throw new ApiException(404, 'USER_NOT_FOUND', '找不到使用者。');
        }
    }

    private function assertAllowedFields(array $input, array $allowed): void
    {
        $unknown = array_values(array_diff(array_keys($input), $allowed));
        if ($unknown === []) {
            return;
        }
        $errors = [];
        foreach ($unknown as $field) {
            $errors[(string) $field] = '不支援這個欄位。';
        }
        throw new ApiException(422, 'UNKNOWN_FIELDS', '要求包含不支援的欄位。', [], $errors);
    }

    /** @return array{0:int,1:int,2:int} */
    private function pagination(): array
    {
        $page = $this->optionalQueryInteger('page') ?? 1;
        $pageSize = $this->optionalQueryInteger('page_size') ?? 20;
        if ($pageSize > 100) {
            throw new ApiException(422, 'INVALID_PAGINATION', 'page_size 需介於 1 到 100。');
        }
        return [$page, $pageSize, ($page - 1) * $pageSize];
    }

    private function optionalQueryInteger(string $name): ?int
    {
        if (!array_key_exists($name, $_GET) || $_GET[$name] === '') {
            return null;
        }
        $value = $_GET[$name];
        if (is_bool($value) || is_array($value) || !preg_match('/^[1-9]\d*$/', (string) $value)) {
            throw new ApiException(422, 'INVALID_QUERY_PARAMETER', "{$name} 必須是正整數。");
        }
        return (int) $value;
    }

    /** @return array{0:string,1:string} */
    private function dateRange(): array
    {
        $hasStart = isset($_GET['start_date']) && $_GET['start_date'] !== '';
        $hasEnd = isset($_GET['end_date']) && $_GET['end_date'] !== '';
        if ($hasStart !== $hasEnd) {
            throw new ApiException(422, 'INVALID_DATE_RANGE', '開始與結束日期必須同時提供。');
        }
        $today = new \DateTimeImmutable('today', new \DateTimeZone('Asia/Taipei'));
        if (!$hasStart) {
            return [$today->modify('-27 days')->format('Y-m-d'), $today->format('Y-m-d')];
        }
        $start = $this->queryString('start_date');
        $end = $this->queryString('end_date');
        $startDate = \DateTimeImmutable::createFromFormat('!Y-m-d', $start, new \DateTimeZone('Asia/Taipei'));
        $endDate = \DateTimeImmutable::createFromFormat('!Y-m-d', $end, new \DateTimeZone('Asia/Taipei'));
        if (!$startDate || !$endDate || $startDate->format('Y-m-d') !== $start
            || $endDate->format('Y-m-d') !== $end || $startDate > $endDate
            || $endDate > $today || (int) $startDate->diff($endDate)->format('%a') > 365) {
            throw new ApiException(422, 'INVALID_DATE_RANGE', '日期區間不合法、晚於今天或超過 366 天。');
        }
        return [$start, $end];
    }

    private function historyStatus(): ?string
    {
        $status = trim($this->queryString('status'));
        if ($status === '') {
            return null;
        }
        if (!in_array($status, ['completed', 'cancelled'], true)) {
            throw new ApiException(422, 'INVALID_STATUS', '歷史狀態篩選不正確。');
        }
        return $status;
    }

    private function taipeiDateExpression(string $column): string
    {
        return Database::driver() === 'pgsql'
            ? "DATE({$column} AT TIME ZONE 'Asia/Taipei')"
            : "DATE(DATETIME({$column}, '+8 hours'))";
    }

    private function queryString(string $name): string
    {
        if (!array_key_exists($name, $_GET)) {
            return '';
        }
        if (!is_string($_GET[$name])) {
            throw new ApiException(422, 'INVALID_QUERY_PARAMETER', "{$name} 格式不正確。");
        }
        return $_GET[$name];
    }

    private function taipeiDateTime(string $value): \DateTimeImmutable
    {
        return (new \DateTimeImmutable($value, new \DateTimeZone('UTC')))
            ->setTimezone(new \DateTimeZone('Asia/Taipei'));
    }

    private function strictInteger(mixed $value): int|false
    {
        if (is_int($value)) {
            return $value;
        }
        if (!is_string($value) || !preg_match('/^-?(?:0|[1-9]\d*)$/', $value)) {
            return false;
        }
        return (int) $value;
    }

    private function isUniqueViolation(\PDOException $error): bool
    {
        $message = strtolower($error->getMessage());
        return $error->getCode() === '23505'
            || str_contains($message, 'unique constraint')
            || str_contains($message, 'is not unique');
    }

    private function isPlanLockViolation(\PDOException $error): bool
    {
        return $error->getCode() === '55006'
            || str_contains(strtolower($error->getMessage()), 'source plan is locked');
    }

    private function decimal(mixed $value, bool $allowZero): float|false
    {
        if (is_float($value) || is_int($value)) {
            $value = rtrim(rtrim(number_format((float) $value, 10, '.', ''), '0'), '.');
        }
        $text = trim((string) $value);
        if (!preg_match('/^\d{1,3}(?:\.\d{1,2})?$/', $text)) {
            return false;
        }
        $number = (float) $text;
        return !$allowZero && $number <= 0 ? false : $number;
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
