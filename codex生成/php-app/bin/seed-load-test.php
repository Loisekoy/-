<?php

declare(strict_types=1);

if (getenv('FITTRACK_TEST_DATABASE') !== '1') {
    fwrite(STDERR, "REFUSED: set FITTRACK_TEST_DATABASE=1 for an isolated load-test database.\n");
    exit(2);
}
$databaseUrl = (string) getenv('DATABASE_URL');
if (!str_contains($databaseUrl, 'fittrack_load')) {
    fwrite(STDERR, "REFUSED: DATABASE_URL must name an isolated fittrack_load database.\n");
    exit(2);
}

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Database;

$outputPath = $argv[1] ?? (sys_get_temp_dir() . '/fittrack-load-users.json');
$pdo = Database::connection();
if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) !== 'pgsql') {
    throw new RuntimeException('Load-test data generation requires PostgreSQL.');
}

$existing = (int) $pdo->query("SELECT COUNT(*) FROM user_auth WHERE email LIKE 'load-%@fittrack.test'")->fetchColumn();
if ($existing > 0) {
    throw new RuntimeException('Load-test users already exist; use a fresh isolated database.');
}

$totalUsers = 1000;
$loadUsers = 200;
$sessionsPerUser = 10;
$setsPerSession = 10;
$password = 'LoadTest12345';
$passwordHash = password_hash($password, PASSWORD_BCRYPT, ['cost' => 10]);
$goalId = (int) $pdo->query('SELECT training_goal_id FROM training_goals ORDER BY training_goal_id LIMIT 1')->fetchColumn();
$bodyPartIds = array_map('intval', $pdo->query('SELECT body_part_id FROM body_parts ORDER BY body_part_id')->fetchAll(PDO::FETCH_COLUMN));
$versionIds = array_map('intval', $pdo->query(
    'SELECT MIN(exercise_version_id) FROM exercise_versions GROUP BY exercise_id ORDER BY exercise_id LIMIT 3'
)->fetchAll(PDO::FETCH_COLUMN));
if ($goalId <= 0 || count($bodyPartIds) !== 8 || count($versionIds) !== 3) {
    throw new RuntimeException('Reference data is incomplete for the load test.');
}

$insertUser = $pdo->prepare(
    "INSERT INTO users (name, age, height_cm, training_experience, training_goal_id, "
    . "training_days_per_week, training_duration_minutes, profile_completed_at) "
    . "VALUES (?, 25, 170.00, 'Beginner', ?, 2, 60, CURRENT_TIMESTAMP) RETURNING user_id"
);
$insertAuth = $pdo->prepare(
    'INSERT INTO user_auth (user_id, email, password_hash, is_email_verified, is_active) VALUES (?, ?, ?, TRUE, TRUE)'
);
$insertPreference = $pdo->prepare(
    'INSERT INTO user_body_parts (user_id, body_part_id, priority) VALUES (?, ?, ?)'
);
$insertWeight = $pdo->prepare(
    'INSERT INTO body_records (user_id, record_date, weight_kg) VALUES (?, CURRENT_DATE, 70.00)'
);
$insertPlan = $pdo->prepare(
    "INSERT INTO workout_plans (user_id, plan_name) VALUES (?, 'Load Test Baseline') RETURNING workout_plan_id"
);
$insertProfile = $pdo->prepare(
    "INSERT INTO planning_profiles (workout_plan_id, training_goal_id, age_snapshot, height_cm_snapshot, "
    . "weight_kg_snapshot, weight_record_date, experience_snapshot, training_days_per_week, duration_minutes, algorithm_version) "
    . "VALUES (?, ?, 25, 170.00, 70.00, CURRENT_DATE, 'Beginner', 2, 60, 'load-test-fixture')"
);
$insertProfilePart = $pdo->prepare(
    'INSERT INTO planning_profile_body_parts (workout_plan_id, body_part_id, priority) VALUES (?, ?, ?)'
);
$insertDay = $pdo->prepare(
    'INSERT INTO plan_days (workout_plan_id, day_number, day_title) VALUES (?, ?, ?) RETURNING plan_day_id'
);
$insertPlanExercise = $pdo->prepare(
    'INSERT INTO plan_exercises (plan_day_id, exercise_version_id, exercise_order, target_sets, target_reps, rest_seconds) '
    . 'VALUES (?, ?, ?, 3, 10, 60) RETURNING plan_exercise_id'
);
$insertSession = $pdo->prepare(
    "INSERT INTO workout_sessions (user_id, status, started_at, ended_at) "
    . "VALUES (?, 'completed', CURRENT_TIMESTAMP - INTERVAL '1 hour', CURRENT_TIMESTAMP) RETURNING workout_session_id"
);
$insertActiveSession = $pdo->prepare(
    "INSERT INTO workout_sessions (user_id, status) VALUES (?, 'in_progress') RETURNING workout_session_id"
);
$insertSessionPlan = $pdo->prepare(
    'INSERT INTO workout_session_plans (workout_session_id, plan_day_id) VALUES (?, ?)'
);
$insertSnapshot = $pdo->prepare(
    'INSERT INTO workout_session_exercises '
    . '(workout_session_id, plan_exercise_id, exercise_version_id, exercise_order, target_sets, target_reps, rest_seconds) '
    . 'VALUES (?, ?, ?, ?, 10, 10, 60) RETURNING workout_session_exercise_id'
);
$insertSet = $pdo->prepare(
    'INSERT INTO workout_sets (workout_session_exercise_id, set_number, weight_kg, reps) VALUES (?, ?, 40.00, 10)'
);

$loadIdentities = [];
$pdo->beginTransaction();
try {
    for ($userIndex = 1; $userIndex <= $totalUsers; $userIndex++) {
        $email = sprintf('load-%04d@fittrack.test', $userIndex);
        $insertUser->execute([sprintf('Load User %04d', $userIndex), $goalId]);
        $userId = (int) $insertUser->fetchColumn();
        $insertAuth->execute([$userId, $email, $passwordHash]);
        $insertWeight->execute([$userId]);
        foreach ($bodyPartIds as $priority => $bodyPartId) {
            $insertPreference->execute([$userId, $bodyPartId, $priority + 1]);
        }

        $insertPlan->execute([$userId]);
        $planId = (int) $insertPlan->fetchColumn();
        $insertProfile->execute([$planId, $goalId]);
        foreach ($bodyPartIds as $priority => $bodyPartId) {
            $insertProfilePart->execute([$planId, $bodyPartId, $priority + 1]);
        }

        $days = [];
        foreach ([1, 2] as $dayNumber) {
            $insertDay->execute([$planId, $dayNumber, 'Load Day ' . $dayNumber]);
            $dayId = (int) $insertDay->fetchColumn();
            $planExercises = [];
            foreach ($versionIds as $order => $versionId) {
                $insertPlanExercise->execute([$dayId, $versionId, $order + 1]);
                $planExercises[] = [
                    'plan_exercise_id' => (int) $insertPlanExercise->fetchColumn(),
                    'exercise_version_id' => $versionId,
                ];
            }
            $days[] = ['plan_day_id' => $dayId, 'exercises' => $planExercises];
        }

        for ($sessionIndex = 0; $sessionIndex < $sessionsPerUser; $sessionIndex++) {
            $insertSession->execute([$userId]);
            $sessionId = (int) $insertSession->fetchColumn();
            $insertSessionPlan->execute([$sessionId, $days[0]['plan_day_id']]);
            $snapshotIds = [];
            foreach ($days[0]['exercises'] as $order => $exercise) {
                $insertSnapshot->execute([
                    $sessionId,
                    $exercise['plan_exercise_id'],
                    $exercise['exercise_version_id'],
                    $order + 1,
                ]);
                $snapshotIds[] = (int) $insertSnapshot->fetchColumn();
            }
            for ($setIndex = 1; $setIndex <= $setsPerSession; $setIndex++) {
                $insertSet->execute([$snapshotIds[($setIndex - 1) % count($snapshotIds)], $setIndex]);
            }
        }

        if ($userIndex <= $loadUsers) {
            $insertActiveSession->execute([$userId]);
            $activeSessionId = (int) $insertActiveSession->fetchColumn();
            $insertSessionPlan->execute([$activeSessionId, $days[0]['plan_day_id']]);
            $activeExerciseId = 0;
            foreach ($days[0]['exercises'] as $order => $exercise) {
                $insertSnapshot->execute([
                    $activeSessionId,
                    $exercise['plan_exercise_id'],
                    $exercise['exercise_version_id'],
                    $order + 1,
                ]);
                $snapshotId = (int) $insertSnapshot->fetchColumn();
                if ($activeExerciseId === 0) {
                    $activeExerciseId = $snapshotId;
                }
            }
            $loadIdentities[] = [
                'email' => $email,
                'password' => $password,
                'workout_session_id' => $activeSessionId,
                'workout_session_exercise_id' => $activeExerciseId,
            ];
        }
    }
    $pdo->commit();
} catch (Throwable $error) {
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }
    throw $error;
}

$manifest = [
    'generated_at_utc' => gmdate('c'),
    'members' => (int) $pdo->query('SELECT COUNT(*) FROM users')->fetchColumn(),
    'workout_sessions' => (int) $pdo->query('SELECT COUNT(*) FROM workout_sessions')->fetchColumn(),
    'workout_sets' => (int) $pdo->query('SELECT COUNT(*) FROM workout_sets')->fetchColumn(),
    'load_users' => $loadIdentities,
];
if (file_put_contents($outputPath, json_encode($manifest, JSON_PRETTY_PRINT) . PHP_EOL, LOCK_EX) === false) {
    throw new RuntimeException("Unable to write {$outputPath}");
}

echo sprintf(
    "Load fixture ready: %d members, %d sessions, %d sets, %d active users.\n",
    $manifest['members'],
    $manifest['workout_sessions'],
    $manifest['workout_sets'],
    count($loadIdentities)
);
