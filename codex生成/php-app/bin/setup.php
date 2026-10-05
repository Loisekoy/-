<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Database;
use FitTrack\PlanGenerator;
use FitTrack\Seeder;

$pdo = Database::connection();
if (Database::driver() === 'pgsql') {
    $schema = file_get_contents(dirname(__DIR__) . '/database/postgres.sql');
    if ($schema === false) {
        throw new RuntimeException('找不到 PostgreSQL schema。');
    }
    $pdo->exec($schema);
}
$goalCount = (int) $pdo->query('SELECT COUNT(*) FROM training_goals')->fetchColumn();
if ($goalCount === 0) {
    Seeder::seed($pdo);
}
$demoUserId = (int) $pdo->query(
    "SELECT u.user_id FROM users u JOIN user_auth ua ON ua.user_id = u.user_id WHERE ua.email='demo@fittrack.local'"
)->fetchColumn();
$planCount = (int) $pdo->query(
    'SELECT COUNT(*) FROM workout_plans WHERE user_id = ' . $demoUserId
)->fetchColumn();
if ($demoUserId > 0 && $planCount === 0) {
    PlanGenerator::generate($pdo, $demoUserId, '4 天增肌示範課表');
}

$completedCountStatement = $pdo->prepare(
    "SELECT COUNT(*) FROM workout_sessions WHERE user_id = ? AND status = 'completed'"
);
$completedCountStatement->execute([$demoUserId]);
if ($demoUserId > 0 && (int) $completedCountStatement->fetchColumn() === 0) {
    $dayStatement = $pdo->prepare(
        'SELECT pd.plan_day_id FROM plan_days pd '
        . 'JOIN workout_plans wp ON wp.workout_plan_id = pd.workout_plan_id '
        . 'WHERE wp.user_id = ? ORDER BY wp.created_at DESC, pd.day_number LIMIT 1'
    );
    $dayStatement->execute([$demoUserId]);
    $planDayId = (int) $dayStatement->fetchColumn();
    if ($planDayId > 0) {
        $endedAt = new DateTimeImmutable('now', new DateTimeZone('UTC'));
        $startedAt = $endedAt->modify('-45 minutes');
        $sessionId = Database::insert(
            $pdo,
            'INSERT INTO workout_sessions (user_id, status, started_at, ended_at, notes) '
            . "VALUES (?, 'completed', ?, ?, ?)",
            [
                $demoUserId,
                $startedAt->format('Y-m-d\TH:i:s\Z'),
                $endedAt->format('Y-m-d\TH:i:s\Z'),
                '示範訓練紀錄',
            ],
            'workout_session_id'
        );
        $pdo->prepare(
            'INSERT INTO workout_session_plans (workout_session_id, plan_day_id) VALUES (?, ?)'
        )->execute([$sessionId, $planDayId]);
        $exerciseStatement = $pdo->prepare(
            'SELECT exercise_id FROM plan_exercises WHERE plan_day_id = ? ORDER BY exercise_order LIMIT 3'
        );
        $exerciseStatement->execute([$planDayId]);
        $insertSet = $pdo->prepare(
            'INSERT INTO workout_sets '
            . '(workout_session_id, exercise_id, set_number, weight_kg, reps) VALUES (?, ?, 1, ?, ?)'
        );
        foreach ($exerciseStatement->fetchAll(PDO::FETCH_COLUMN) as $index => $exerciseId) {
            $insertSet->execute([$sessionId, (int) $exerciseId, 40 + $index * 10, 10 + $index]);
        }
    }
}

$bodyRecordCount = $pdo->prepare('SELECT COUNT(*) FROM body_records WHERE user_id = ?');
$bodyRecordCount->execute([$demoUserId]);
if ($demoUserId > 0 && (int) $bodyRecordCount->fetchColumn() < 4) {
    $insertWeight = $pdo->prepare(
        'INSERT INTO body_records (user_id, record_date, weight_kg, notes) VALUES (?, ?, ?, ?)'
    );
    foreach ([28 => 70.1, 21 => 69.6, 14 => 69.0] as $daysAgo => $weight) {
        $date = (new DateTimeImmutable('today'))->modify("-{$daysAgo} days")->format('Y-m-d');
        try {
            $insertWeight->execute([$demoUserId, $date, $weight, '示範體重趨勢']);
        } catch (PDOException) {
            // Re-running setup keeps existing records.
        }
    }
}

echo "Database ready (" . Database::driver() . ").\n";
echo "Demo member: demo@fittrack.local / Demo12345\n";
echo "Demo admin: admin@fittrack.local / Admin12345\n";
