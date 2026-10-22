<?php

declare(strict_types=1);

$databasePath = sys_get_temp_dir() . '/fittrack-srs-' . bin2hex(random_bytes(6)) . '.sqlite';
$partialPath = sys_get_temp_dir() . '/fittrack-srs-partial-' . bin2hex(random_bytes(6)) . '.sqlite';
putenv('APP_ENV=test');
putenv('SQLITE_PATH=' . $databasePath);
putenv('SECRET_KEY=srs-conformance-secret');
putenv('RATE_LIMIT_SECRET=srs-conformance-rate-secret');
putenv('DEMO_BOOTSTRAP_PASSWORD=ConformanceDemo123');
putenv('DEMO_ADMIN_PASSWORD=ConformanceAdmin123');

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Api;
use FitTrack\ApiException;
use FitTrack\ApiResponse;
use FitTrack\Auth;
use FitTrack\Database;
use FitTrack\PlanGenerator;
use FitTrack\RequestSecurity;
use FitTrack\Seeder;

function srsCheck(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
    echo "PASS: {$message}\n";
}

try {
    $pdo = Database::connection();

    try {
        Auth::register($pdo, [
            'name' => [],
            'email' => 'bad-type@example.test',
            'password' => 'ValidPass123',
        ]);
        srsCheck(false, '陣列型別姓名應被拒絕');
    } catch (ApiException $error) {
        srsCheck($error->status === 422 && $error->errorCode === 'INVALID_FIELD_TYPE', 'JSON 字串欄位拒絕陣列型別');
    }

    try {
        Auth::register($pdo, [
            'name' => 'NUL Test',
            'email' => 'nul@example.test',
            'password' => "ValidPass123\0",
        ]);
        srsCheck(false, '含 NUL 密碼應被拒絕');
    } catch (ApiException $error) {
        srsCheck($error->status === 422 && $error->errorCode === 'INVALID_PASSWORD', '密碼含 NUL 回 422 而非 500');
    }

    $normalized = ApiResponse::normalize([
        'height_cm' => 168,
        'weight_kg' => 68.4,
        'target_weight_kg' => null,
        'reps' => 10,
    ]);
    srsCheck($normalized['height_cm'] === '168.00' && $normalized['weight_kg'] === '68.40'
        && $normalized['target_weight_kg'] === null && $normalized['reps'] === 10,
        'NUMERIC 回應固定為兩位小數字串且不改變整數欄位');

    $demoUserId = (int) $pdo->query(
        "SELECT user_id FROM user_auth WHERE email='demo@fittrack.local'"
    )->fetchColumn();
    $plan = PlanGenerator::generate($pdo, $demoUserId, 'SRS Conformance Plan');
    $first = $plan['days'][0]['exercises'][0];
    $pdo->prepare('UPDATE plan_exercises SET target_weight_kg = 42 WHERE plan_exercise_id = ?')
        ->execute([(int) $first['plan_exercise_id']]);
    $updatePlan = new ReflectionMethod(Api::class, 'updatePlan');
    $updatePlan->invoke(new Api($pdo), $demoUserId, (int) $plan['workout_plan_id'], [
        'exercises' => [[
            'plan_exercise_id' => (int) $first['plan_exercise_id'],
            'exercise_id' => (int) $first['exercise_id'],
            'target_sets' => (int) $first['target_sets'],
            'target_reps' => (int) $first['target_reps'],
            'rest_seconds' => (int) $first['rest_seconds'],
        ]],
    ]);
    $preservedWeight = $pdo->query(
        'SELECT target_weight_kg FROM plan_exercises WHERE plan_exercise_id = ' . (int) $first['plan_exercise_id']
    )->fetchColumn();
    srsCheck((float) $preservedWeight === 42.0, 'PATCH 未提供目標重量時保留原值');

    $registered = Auth::register($pdo, [
        'name' => 'Invariant User',
        'email' => 'invariant@example.test',
        'password' => 'Invariant123',
    ]);
    $invariantUserId = (int) Auth::user($pdo, (string) $registered['access_token'])['user_id'];
    try {
        $pdo->prepare('UPDATE users SET profile_completed_at = CURRENT_TIMESTAMP WHERE user_id = ?')
            ->execute([$invariantUserId]);
        srsCheck(false, '無體重不得完成 Profile');
    } catch (PDOException) {
        srsCheck(true, 'SQLite Trigger 拒絕無體重的已完成 Profile');
    }
    $pdo->prepare('INSERT INTO body_records (user_id, record_date, weight_kg) VALUES (?, ?, 65)')
        ->execute([$invariantUserId, date('Y-m-d')]);
    $pdo->prepare('UPDATE users SET profile_completed_at = CURRENT_TIMESTAMP WHERE user_id = ?')
        ->execute([$invariantUserId]);
    $other = Auth::register($pdo, [
        'name' => 'Other User',
        'email' => 'other@example.test',
        'password' => 'OtherValid123',
    ]);
    $otherUserId = (int) Auth::user($pdo, (string) $other['access_token'])['user_id'];
    try {
        $pdo->prepare('UPDATE body_records SET user_id = ? WHERE user_id = ?')
            ->execute([$otherUserId, $invariantUserId]);
        srsCheck(false, '不得移走已完成 Profile 的最後體重');
    } catch (PDOException) {
        srsCheck(true, 'SQLite Trigger 拒絕移走已完成 Profile 的最後體重');
    }

    try {
        $pdo->prepare(
            "INSERT INTO workout_sessions (user_id, status, started_at, ended_at) "
            . "VALUES (?, 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        )->execute([$demoUserId]);
        srsCheck(false, '不得直接建立空的 completed 場次');
    } catch (PDOException) {
        srsCheck(true, 'SQLite Trigger 拒絕直接建立空的 completed 場次');
    }

    $dayExercises = $plan['days'][0]['exercises'];
    $sourceVersion = $pdo->prepare('SELECT * FROM exercise_versions WHERE exercise_version_id = ?');
    $sourceVersion->execute([(int) $dayExercises[0]['exercise_version_id']]);
    $version = $sourceVersion->fetch();
    $nextVersion = (int) $version['version_no'] + 1;
    $pdo->prepare(
        'INSERT INTO exercise_versions '
        . '(exercise_id, version_no, exercise_name, difficulty_level, equipment, description, image_url) '
        . 'VALUES (?, ?, ?, ?, ?, ?, ?)'
    )->execute([
        (int) $version['exercise_id'],
        $nextVersion,
        (string) $version['exercise_name'],
        (string) $version['difficulty_level'],
        $version['equipment'],
        (string) $version['description'],
        $version['image_url'],
    ]);
    $newVersionId = (int) $pdo->lastInsertId();
    try {
        $pdo->prepare('UPDATE plan_exercises SET exercise_version_id = ? WHERE plan_exercise_id = ?')
            ->execute([$newVersionId, (int) $dayExercises[1]['plan_exercise_id']]);
        srsCheck(false, '更新課表不得產生同日重複動作身份');
    } catch (PDOException) {
        srsCheck(true, 'SQLite UPDATE Trigger 防止同日重複動作身份');
    }

    for ($daysAgo = 1; $daysAgo <= 20; $daysAgo++) {
        $date = (new DateTimeImmutable('today'))->modify("-{$daysAgo} days")->format('Y-m-d');
        $pdo->prepare('INSERT INTO body_records (user_id, record_date, weight_kg) VALUES (?, ?, 68)')
            ->execute([$demoUserId, $date]);
    }
    $_GET = ['page' => '2', 'page_size' => '20'];
    $bodyRecords = new ReflectionMethod(Api::class, 'bodyRecords');
    $bodyPage = $bodyRecords->invoke(new Api($pdo), $demoUserId);
    srsCheck($bodyPage['page'] === 2 && $bodyPage['page_size'] === 20
        && $bodyPage['total'] === 21 && count($bodyPage['items']) === 1, '體重清單遵守共通分頁契約');
    $_GET = ['page' => '2', 'page_size' => '20'];
    $plans = new ReflectionMethod(Api::class, 'plans');
    $planPage = $plans->invoke(new Api($pdo), $demoUserId);
    srsCheck($planPage['page'] === 2 && $planPage['page_size'] === 20
        && $planPage['total'] === 1 && $planPage['items'] === [], '課表清單遵守共通分頁契約');
    $_GET = [];

    $databaseTable = new ReflectionMethod(Api::class, 'databaseTable');
    $privatePreview = $databaseTable->invoke(new Api($pdo), 'body_records');
    $sharedPreview = $databaseTable->invoke(new Api($pdo), 'training_goals');
    srsCheck($privatePreview['rows_hidden_for_privacy'] === true && $privatePreview['rows'] === []
        && $sharedPreview['rows_hidden_for_privacy'] === false && $sharedPreview['rows'] !== [],
        '管理員只可預覽共用主資料，不可瀏覽會員私密資料列');

    $_SERVER['HTTP_HOST'] = 'example.test:8080';
    $_SERVER['HTTP_ORIGIN'] = 'http://example.test:9090';
    $_SERVER['HTTPS'] = 'off';
    try {
        RequestSecurity::enforceBrowserWriteProtection('POST', '/auth/login');
        srsCheck(false, '同 hostname 不同 port 應被拒絕');
    } catch (ApiException $error) {
        srsCheck($error->errorCode === 'ORIGIN_REJECTED', 'Same-origin 驗證會比對 port');
    }
    $_SERVER['HTTP_ORIGIN'] = 'http://example.test:8080';
    RequestSecurity::enforceBrowserWriteProtection('POST', '/auth/login');
    srsCheck(true, '完全相同的 origin 可通過驗證');
    unset($_SERVER['HTTP_HOST'], $_SERVER['HTTP_ORIGIN'], $_SERVER['HTTPS']);

    $pdo->prepare('UPDATE users SET training_days_per_week = 6, training_duration_minutes = 90 WHERE user_id = ?')
        ->execute([$demoUserId]);
    $pdo->exec(
        "UPDATE exercises SET is_active = FALSE WHERE body_part_id = "
        . "(SELECT body_part_id FROM body_parts WHERE body_part_name = 'Core')"
    );
    $plansBefore = (int) $pdo->query('SELECT COUNT(*) FROM workout_plans')->fetchColumn();
    try {
        PlanGenerator::generate($pdo, $demoUserId, 'Missing Required Part Plan');
        srsCheck(false, '缺少必要部位候選時不得保存不完整課表');
    } catch (ApiException $error) {
        $plansAfter = (int) $pdo->query('SELECT COUNT(*) FROM workout_plans')->fetchColumn();
        srsCheck($error->status === 409 && $error->errorCode === 'PLAN_CONSTRAINT_UNSATISFIED'
            && $plansBefore === $plansAfter, '候選不足回 409 並回滾整份課表');
    }

    $partial = new PDO('sqlite:' . $partialPath, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $partial->exec('PRAGMA foreign_keys = ON');
    $partial->exec((string) file_get_contents(dirname(__DIR__) . '/database/sqlite.sql'));
    putenv('DEMO_ADMIN_PASSWORD=');
    try {
        Seeder::seed($partial);
        srsCheck(false, '缺少管理員密碼的初始化應失敗');
    } catch (RuntimeException) {
        $goals = (int) $partial->query('SELECT COUNT(*) FROM training_goals')->fetchColumn();
        $exercises = (int) $partial->query('SELECT COUNT(*) FROM exercises')->fetchColumn();
        $users = (int) $partial->query('SELECT COUNT(*) FROM users')->fetchColumn();
        srsCheck($goals === 0 && $exercises === 0 && $users === 0, '初始化失敗不留下半套資料');
    }
    putenv('DEMO_ADMIN_PASSWORD=RecoveredAdmin123');
    Seeder::seed($partial);
    srsCheck((int) $partial->query('SELECT COUNT(*) FROM users')->fetchColumn() === 2, '補上密碼後可完整初始化');
} finally {
    $_GET = [];
    foreach ([$databasePath, $databasePath . '-wal', $databasePath . '-shm', $partialPath] as $path) {
        if (is_file($path)) unlink($path);
    }
}
