<?php

declare(strict_types=1);

$databasePath = sys_get_temp_dir() . '/fittrack-smoke-' . bin2hex(random_bytes(6)) . '.sqlite';
putenv('SQLITE_PATH=' . $databasePath);
putenv('APP_KEY=smoke-test-key');

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Auth;
use FitTrack\Api;
use FitTrack\ApiException;
use FitTrack\Database;
use FitTrack\PlanGenerator;

function check(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
    echo "PASS: {$message}\n";
}

try {
    $pdo = Database::connection();
    $tableCount = (int) $pdo->query(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )->fetchColumn();
    check($tableCount === 15, '15 張核心資料表已建立');

    $exerciseCount = (int) $pdo->query('SELECT COUNT(*) FROM exercises')->fetchColumn();
    check($exerciseCount >= 24, '動作資料已匯入');

    $login = Auth::login($pdo, [
        'email' => 'demo@fittrack.local',
        'password' => 'Demo12345',
    ]);
    $user = Auth::user($pdo, $login['access_token']);
    check($user['role'] === 'USER', '會員 JWT 可驗證');

    $_SERVER['HTTP_AUTHORIZATION'] = 'Bearer ' . $login['access_token'];
    [$aiStatusCode, $aiStatus] = (new Api($pdo))->dispatch('GET', '/ai/status');
    check(
        $aiStatusCode === 200 && $aiStatus['enabled'] === false && $aiStatus['secret_configured'] === false,
        '未設定模型金鑰時安全停用 AI，且不影響規則式功能'
    );

    $plan = PlanGenerator::generate($pdo, (int) $user['user_id'], 'Smoke Test Plan');
    check(count($plan['days']) === 4, '依每週天數產生完整課表');
    check(count($plan['days'][0]['exercises']) >= 3, '課表日包含至少三個動作');

    $sessionId = Database::insert(
        $pdo,
        "INSERT INTO workout_sessions (user_id, status) VALUES (?, 'in_progress')",
        [(int) $user['user_id']],
        'workout_session_id'
    );
    $planDayId = (int) $plan['days'][0]['plan_day_id'];
    $pdo->prepare(
        'INSERT INTO workout_session_plans (workout_session_id, plan_day_id) VALUES (?, ?)'
    )->execute([$sessionId, $planDayId]);
    $exerciseId = (int) $plan['days'][0]['exercises'][0]['exercise_id'];
    $pdo->prepare(
        'INSERT INTO workout_sets '
        . '(workout_session_id, exercise_id, set_number, weight_kg, reps) VALUES (?, ?, 1, 50, 10)'
    )->execute([$sessionId, $exerciseId]);
    $pdo->prepare(
        "UPDATE workout_sessions SET status='completed', ended_at=CURRENT_TIMESTAMP WHERE workout_session_id=?"
    )->execute([$sessionId]);
    $volume = (float) $pdo->query(
        'SELECT SUM(weight_kg * reps) FROM workout_sets WHERE workout_session_id = ' . $sessionId
    )->fetchColumn();
    check($volume === 500.0, '逐組紀錄可彙總訓練量');

    $pdo->prepare('DELETE FROM workout_plans WHERE workout_plan_id = ?')->execute([
        (int) $plan['workout_plan_id'],
    ]);
    $historyPreserved = (int) $pdo->query(
        'SELECT COUNT(*) FROM workout_sessions WHERE workout_session_id = ' . $sessionId
    )->fetchColumn();
    check($historyPreserved === 1, '刪除課表後仍保留實際訓練歷史');

    $adminLogin = Auth::login($pdo, [
        'email' => 'admin@fittrack.local',
        'password' => 'Admin12345',
    ]);
    $admin = Auth::user($pdo, $adminLogin['access_token']);
    check($admin['role'] === 'ADMIN', '管理員資格由 admins 資料表決定');

    $_SERVER['HTTP_AUTHORIZATION'] = 'Bearer ' . $adminLogin['access_token'];
    [$databaseStatus, $databaseOverview] = (new Api($pdo))->dispatch(
        'GET',
        '/admin/database/overview'
    );
    check($databaseStatus === 200 && count($databaseOverview['tables']) === 15, '管理員可檢視 15 張資料表架構');
    [$tableStatus, $authTable] = (new Api($pdo))->dispatch(
        'GET',
        '/admin/database/tables/user_auth'
    );
    check(
        $tableStatus === 200 && $authTable['rows'][0]['password_hash'] === '[已隱藏]',
        '資料表預覽會隱藏密碼雜湊'
    );

    $registered = Auth::register($pdo, [
        'name' => '測試會員',
        'email' => 'member@example.com',
        'password' => 'Member12345',
    ]);
    $registeredUser = Auth::user($pdo, $registered['access_token']);
    check($registeredUser['email'] === 'member@example.com', '註冊交易同時建立會員與登入工作階段');

    Auth::changePassword($pdo, $registeredUser, [
        'current_password' => 'Member12345',
        'new_password' => 'Member67890',
    ]);
    try {
        Auth::user($pdo, $registered['access_token']);
        check(false, '變更密碼後舊 Token 應失效');
    } catch (ApiException $error) {
        check($error->status === 401, '變更密碼會撤銷所有舊 Token');
    }
    $newLogin = Auth::login($pdo, [
        'email' => 'member@example.com',
        'password' => 'Member67890',
    ]);
    check($newLogin['access_token'] !== '', '新密碼可重新登入');

    try {
        Auth::register($pdo, [
            'name' => '重複會員',
            'email' => 'member@example.com',
            'password' => 'Another12345',
        ]);
        check(false, '重複 Email 應被拒絕');
    } catch (ApiException $error) {
        check($error->errorCode === 'EMAIL_EXISTS', '重複 Email 回傳 EMAIL_EXISTS');
    }
} finally {
    if (is_file($databasePath)) {
        unlink($databasePath);
    }
}
