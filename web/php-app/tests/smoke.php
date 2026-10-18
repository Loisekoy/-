<?php

declare(strict_types=1);

$databasePath = sys_get_temp_dir() . '/fittrack-smoke-' . bin2hex(random_bytes(6)) . '.sqlite';
putenv('SQLITE_PATH=' . $databasePath);
putenv('SECRET_KEY=smoke-test-key');
putenv('RATE_LIMIT_SECRET=smoke-rate-limit-key');
putenv('DEMO_ADMIN_PASSWORD=SmokeAdmin123');
putenv('APP_ENV=development');

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Api;
use FitTrack\ApiException;
use FitTrack\ApiResponse;
use FitTrack\Auth;
use FitTrack\Database;
use FitTrack\LoginRateLimiter;
use FitTrack\PlanGenerator;
use FitTrack\RequestSecurity;

function check(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
    echo "PASS: {$message}\n";
}

/** @return array{0:int,1:mixed} */
function callApi(PDO $pdo, string $token, string $method, string $path): array
{
    $_SERVER['HTTP_AUTHORIZATION'] = 'Bearer ' . $token;
    return (new Api($pdo, '198.51.100.10'))->dispatch($method, $path);
}

try {
    $pdo = Database::connection();
    $tableCount = (int) $pdo->query(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )->fetchColumn();
    check($tableCount === 20, '20 張應用資料表已建立');
    $normalizedTime = ApiResponse::normalize([
        'started_at' => '2026-10-14 03:20:00',
        'record_date' => '2026-10-14',
    ]);
    check(
        $normalizedTime['started_at'] === '2026-10-14T03:20:00Z'
        && $normalizedTime['record_date'] === '2026-10-14',
        'API 將無時區的 SQLite 時間轉為 UTC ISO 8601，且不改動日期欄位'
    );

    $exerciseCount = (int) $pdo->query('SELECT COUNT(*) FROM exercises')->fetchColumn();
    $versionCount = (int) $pdo->query('SELECT COUNT(*) FROM exercise_versions')->fetchColumn();
    check($exerciseCount >= 24 && $exerciseCount === $versionCount, '動作身份與版本資料已建立');

    $login = LoginRateLimiter::attempt($pdo, '198.51.100.10', fn (): array => Auth::login($pdo, [
        'email' => 'demo@fittrack.local',
        'password' => 'Demo12345',
    ]));
    $token = (string) $login['access_token'];
    check(
        $login['name'] === '示範會員' && $login['email'] === 'demo@fittrack.local',
        '登入回應包含規格要求的姓名與 Email'
    );
    $user = Auth::user($pdo, $token);
    check($user['role'] === 'USER', 'JWT 以 Session 白名單驗證，角色由資料庫推導');
    $segments = explode('.', $token);
    $segments[0] = rtrim(strtr(base64_encode('{"alg":"none","typ":"JWT"}'), '+/', '-_'), '=');
    try {
        Auth::user($pdo, implode('.', $segments));
        check(false, 'JWT Header 不得改用其他演算法');
    } catch (ApiException $error) {
        check($error->errorCode === 'TOKEN_INVALID', 'JWT 僅接受固定 HS256 Header');
    }

    $_COOKIE[RequestSecurity::accessCookieName()] = $token;
    check(RequestSecurity::token() === $token, 'HttpOnly Cookie 的伺服器端取值路徑可恢復登入');
    unset($_COOKIE[RequestSecurity::accessCookieName()]);

    $plan = PlanGenerator::generate($pdo, (int) $user['user_id'], 'Smoke Test Plan');
    check(count($plan['days']) === 4, '依每週天數產生完整課表與規劃輸入快照');
    check(
        (int) $plan['age_snapshot'] > 0
        && (float) $plan['height_cm_snapshot'] > 0
        && (float) $plan['weight_kg_snapshot'] > 0
        && (string) $plan['weight_record_date'] !== '',
        '規劃快照保留當時年齡、身高、體重與體重日期'
    );
    check(count($plan['days'][0]['exercises']) >= 3, '課表日包含至少三個固定動作版本');
    $coveredParts = [];
    foreach ($plan['days'] as $day) {
        check(
            count($day['exercises']) >= 3 && count($day['exercises']) <= 6
            && (int) $day['estimated_seconds'] <= (int) $plan['duration_minutes'] * 60,
            '每個課表日有 3 至 6 動作且不超過可用時間'
        );
        foreach ($day['exercises'] as $exercise) {
            $coveredParts[$exercise['body_part_name']] = true;
            check(
                (int) $exercise['target_sets'] === 3
                && (int) $exercise['target_reps'] === 10
                && (int) $exercise['rest_seconds'] === 60,
                '增肌處方固定為 3×10、休息 60 秒'
            );
        }
    }
    check(count($coveredParts) === 8, '規則式課表先完成八個身體部位的每週覆蓋');

    $secondComputerPlan = PlanGenerator::generate($pdo, (int) $user['user_id'], 'Randomized Plan');
    $firstPlanExerciseIds = [];
    foreach ($plan['days'] as $planDay) {
        foreach ($planDay['exercises'] as $exercise) {
            $firstPlanExerciseIds[] = (int) $exercise['exercise_id'];
        }
    }
    $secondPlanExerciseIds = [];
    foreach ($secondComputerPlan['days'] as $planDay) {
        foreach ($planDay['exercises'] as $exercise) {
            $secondPlanExerciseIds[] = (int) $exercise['exercise_id'];
        }
    }
    $overlap = array_intersect($firstPlanExerciseIds, $secondPlanExerciseIds);
    check(
        count($overlap) <= (int) floor(count($firstPlanExerciseIds) * 0.25),
        '連續兩份電腦課表優先避開最近使用動作，重複率不超過 25%'
    );
    check(
        count($secondPlanExerciseIds) === count(array_unique($secondPlanExerciseIds)),
        '同一份電腦課表不重複安排相同動作'
    );

    $manualPlan = PlanGenerator::createManual($pdo, (int) $user['user_id'], 'Manual Test Plan', [
        [
            'day_title' => '自主上肢',
            'exercises' => [[
                'exercise_id' => (int) $plan['days'][0]['exercises'][0]['exercise_id'],
                'target_sets' => 4,
                'target_reps' => 8,
                'rest_seconds' => 90,
            ]],
        ],
        [
            'day_title' => '自主下肢',
            'exercises' => [[
                'exercise_id' => (int) $plan['days'][2]['exercises'][0]['exercise_id'],
                'target_sets' => 3,
                'target_reps' => 12,
                'rest_seconds' => 60,
            ]],
        ],
    ]);
    check(
        $manualPlan['algorithm_version'] === 'manual-v1'
        && count($manualPlan['days']) === 2
        && (int) $manualPlan['days'][0]['exercises'][0]['target_sets'] === 4,
        '使用者可自行選擇動作、訓練日與組次建立課表'
    );

    try {
        callApi($pdo, $token, 'POST', '/workout-sessions');
        check(false, '缺少 plan_day_id 的開始要求應被拒絕');
    } catch (ApiException $error) {
        check($error->status === 422, '缺少 plan_day_id 的開始要求會被拒絕');
    }

    $api = new Api($pdo, '198.51.100.10');
    $method = new ReflectionMethod(Api::class, 'startSession');
    [$startStatus, $session] = $method->invoke($api, (int) $user['user_id'], [
        'plan_day_id' => (int) $plan['days'][0]['plan_day_id'],
    ]);
    check($startStatus === 201, '開始運動會建立進行中場次');
    check(count($session['exercises']) === count($plan['days'][0]['exercises']), '開始場次會建立完整動作快照');

    $sessionId = (int) $session['workout_session_id'];
    $sessionExercise = $session['exercises'][0];
    $sessionExerciseId = (int) $sessionExercise['workout_session_exercise_id'];

    try {
        $otherPlanDayId = (int) $plan['days'][1]['plan_day_id'];
        $otherVersion = (int) $plan['days'][1]['exercises'][0]['exercise_version_id'];
        $otherPlanExercise = (int) $pdo->query(
            'SELECT plan_exercise_id FROM plan_exercises WHERE plan_day_id = ' . $otherPlanDayId . ' LIMIT 1'
        )->fetchColumn();
        $pdo->prepare(
            'INSERT INTO workout_session_exercises '
            . '(workout_session_id, plan_exercise_id, exercise_version_id, exercise_order, target_sets, target_reps, rest_seconds) '
            . 'VALUES (?, ?, ?, 10, 3, 10, 60)'
        )->execute([$sessionId, $otherPlanExercise, $otherVersion]);
        check(false, '跨課表日的場次動作應被資料庫拒絕');
    } catch (PDOException) {
        check(true, '直接 SQL 插入跨課表日動作會被 Trigger 拒絕');
    }

    try {
        $pdo->prepare(
            'INSERT INTO workout_sets (workout_session_exercise_id, set_number, weight_kg, reps) VALUES (?, 1, 50, 10)'
        )->execute([$sessionExerciseId + 999999]);
        check(false, '不存在的場次動作應被拒絕');
    } catch (PDOException) {
        check(true, 'workout_sets 外鍵阻止不存在的場次動作');
    }

    $saveSet = new ReflectionMethod(Api::class, 'saveSet');
    [$setStatus, $set] = $saveSet->invoke($api, (int) $user['user_id'], $sessionId, [
        'workout_session_exercise_id' => $sessionExerciseId,
        'set_number' => 1,
        'weight_kg' => '60.00',
        'reps' => 12,
    ]);
    check($setStatus === 201 && (float) $set['set_volume'] === 720.0, '合法組數可立即寫入並計算外加重量訓練量');
    [$retryStatus] = $saveSet->invoke($api, (int) $user['user_id'], $sessionId, [
        'workout_session_exercise_id' => $sessionExerciseId,
        'set_number' => 1,
        'weight_kg' => '60.00',
        'reps' => 12,
    ]);
    check($retryStatus === 200, '完全相同的組數重送具有冪等性');
    try {
        $saveSet->invoke($api, (int) $user['user_id'], $sessionId, [
            'workout_session_exercise_id' => $sessionExerciseId,
            'set_number' => 1,
            'weight_kg' => '55.00',
            'reps' => 10,
        ]);
        check(false, '相同組號不同內容應衝突');
    } catch (ReflectionException|ApiException $error) {
        check($error instanceof ApiException && $error->errorCode === 'SET_ALREADY_EXISTS', '重複組號不同內容回 409');
    }

    $adjust = new ReflectionMethod(Api::class, 'updateSessionExercise');
    $updatedTarget = $adjust->invoke($api, (int) $user['user_id'], $sessionId, $sessionExerciseId, [
        'target_sets' => 4,
        'target_reps' => 8,
        'rest_seconds' => 90,
        'target_weight_kg' => '52.50',
    ]);
    check((int) $updatedTarget['target_sets'] === 4, '進行中只調整本場目標，不回寫來源課表');
    $sourceSets = (int) $pdo->query(
        'SELECT target_sets FROM plan_exercises WHERE plan_exercise_id = ' . (int) $sessionExercise['plan_exercise_id']
    )->fetchColumn();
    check($sourceSets !== 4 || (int) $sessionExercise['target_sets'] === 4, '來源課表與場次目標為不同資料列');

    foreach ([
        ['set_number' => 2, 'weight_kg' => '65.00', 'reps' => 10],
        ['set_number' => 3, 'weight_kg' => '65.00', 'reps' => 8],
        ['set_number' => 4, 'weight_kg' => '0.00', 'reps' => 15],
    ] as $additionalSet) {
        [$additionalStatus] = $saveSet->invoke($api, (int) $user['user_id'], $sessionId, [
            'workout_session_exercise_id' => $sessionExerciseId,
            ...$additionalSet,
        ]);
        check($additionalStatus === 201, '加權與徒手測試組數可立即寫入');
    }

    try {
        $updatePlan = new ReflectionMethod(Api::class, 'updatePlan');
        $updatePlan->invoke($api, (int) $user['user_id'], (int) $plan['workout_plan_id'], ['plan_name' => '不應成功']);
        check(false, '進行中場次的來源課表應被鎖定');
    } catch (ApiException $error) {
        check(
            $error->errorCode === 'PLAN_IN_USE' && str_contains($error->getMessage(), '調整本次目標'),
            '進行中來源課表修改回 409，並提示可調整本次目標'
        );
    }

    $finish = new ReflectionMethod(Api::class, 'finishSession');
    $completed = $finish->invoke($api, (int) $user['user_id'], $sessionId, 'completed', 'smoke');
    check($completed['status'] === 'completed', '至少一組時可完成場次');

    try {
        $pdo->prepare('DELETE FROM workout_session_exercises WHERE workout_session_exercise_id = ?')
            ->execute([$sessionExerciseId]);
        check(false, '完成場次的動作快照不應被刪除');
    } catch (PDOException) {
        check(true, 'SQLite Trigger 阻止藉由刪除場次動作繞過 completed 至少一組約束');
    }

    [, $cancelSession] = $method->invoke($api, (int) $user['user_id'], [
        'plan_day_id' => (int) $plan['days'][1]['plan_day_id'],
    ]);
    [$cancelStatus, $cancelled] = callApi(
        $pdo,
        $token,
        'POST',
        '/workout-sessions/' . (int) $cancelSession['workout_session_id'] . '/cancel'
    );
    check(
        $cancelStatus === 200 && $cancelled['status'] === 'cancelled' && $cancelled['ended_at'] !== null,
        '未儲存組數也能取消本次訓練，並記錄結束時間'
    );

    [, $legacyCancelSession] = $method->invoke($api, (int) $user['user_id'], [
        'plan_day_id' => (int) $plan['days'][2]['plan_day_id'],
    ]);
    [$legacyCancelStatus, $legacyCancelled] = callApi(
        $pdo,
        $token,
        'POST',
        '/workout-sessions/' . (int) $legacyCancelSession['workout_session_id'] . '/cancelled'
    );
    check(
        $legacyCancelStatus === 200 && $legacyCancelled['status'] === 'cancelled',
        '舊版 cancelled 路徑仍可相容取消訓練'
    );

    $deletePlan = new ReflectionMethod(Api::class, 'deletePlan');
    $deletePlan->invoke($api, (int) $user['user_id'], (int) $manualPlan['workout_plan_id']);
    $visiblePlanIds = array_map(
        static fn (array $visiblePlan): int => (int) $visiblePlan['workout_plan_id'],
        PlanGenerator::listPlans($pdo, (int) $user['user_id'])
    );
    check(
        !in_array((int) $manualPlan['workout_plan_id'], $visiblePlanIds, true),
        '封存課表保留歷史資料，但不再出現在可選課表清單'
    );

    $oldName = (string) $sessionExercise['exercise_name'];
    $adminLogin = Auth::login($pdo, ['email' => 'admin@fittrack.local', 'password' => (string) getenv('DEMO_ADMIN_PASSWORD')]);
    $adminToken = (string) $adminLogin['access_token'];
    $admin = Auth::user($pdo, $adminToken);
    check($admin['role'] === 'ADMIN', '管理員資格由 admins 資料表決定');
    $_SERVER['HTTP_AUTHORIZATION'] = 'Bearer ' . $adminToken;
    $adminApi = new Api($pdo, '203.0.113.8');
    $updateAdminUser = new ReflectionMethod(Api::class, 'updateAdminUser');
    $deactivatedUser = $updateAdminUser->invoke($adminApi, (int) $user['user_id'], ['is_active' => 0], $admin);
    check((int) $deactivatedUser['is_active'] === 0, '管理員可以停用其他會員帳號');
    try {
        Auth::user($pdo, $token);
        check(false, '被管理員停用的會員舊 Token 應立即失效');
    } catch (ApiException $error) {
        check($error->status === 401 && $error->errorCode === 'TOKEN_INVALID', '被管理員停用的會員舊 Token 立即失效');
    }
    $reactivatedUser = $updateAdminUser->invoke($adminApi, (int) $user['user_id'], ['is_active' => 1], $admin);
    check((int) $reactivatedUser['is_active'] === 1, '管理員可以恢復其他會員帳號');
    try {
        $updateAdminUser->invoke($adminApi, (int) $admin['user_id'], ['is_active' => 0], $admin);
        check(false, '管理員不應透過會員管理停用自己的帳號');
    } catch (ApiException $error) {
        check($error->status === 409 && $error->errorCode === 'CANNOT_CHANGE_SELF', '管理員不能透過會員管理停用自己的帳號');
    }
    $updateExercise = new ReflectionMethod(Api::class, 'updateExercise');
    $newName = $oldName . '（新版）';
    $updatedExercise = $updateExercise->invoke($adminApi, (int) $sessionExercise['exercise_id'], [
        'exercise_name' => $newName,
    ]);
    check((int) $updatedExercise['version_no'] === (int) $sessionExercise['version_no'] + 1, '修改動作會新增不可變版本');
    $detail = new ReflectionMethod(Api::class, 'sessionDetail');
    $historyDetail = $detail->invoke($api, (int) $user['user_id'], $sessionId);
    check($historyDetail['exercises'][0]['exercise_name'] === $oldName, '歷史場次仍顯示當時動作名稱');

    $dashboard = new ReflectionMethod(Api::class, 'dashboard');
    $stats = $dashboard->invoke($api, (int) $user['user_id']);
    check((float) $stats['external_load_volume_kg_reps'] === 1890.0, 'Dashboard 明確回傳外加重量訓練量');
    check((int) $stats['total_reps'] === 45, 'Dashboard 另列實際完成次數');
    check((int) $stats['bodyweight_reps'] === 15, 'Dashboard 另列徒手完成次數，不會被 0 kg 訓練量隱藏');
    check(
        (int) $stats['completed_sets'] === 4
        && (float) $stats['weighted_volume'] === 1890.0
        && ($stats['volume_by_week'][0]['session_count'] ?? 0) >= 1,
        'Dashboard 回傳完成組數、規格命名的 weighted_volume 與每週場次'
    );
    $_GET = ['start_date' => date('Y-m-d')];
    try {
        $dashboard->invoke($api, (int) $user['user_id']);
        check(false, '日期篩選只提供一端應被拒絕');
    } catch (ApiException $error) {
        check($error->errorCode === 'INVALID_DATE_RANGE', '日期篩選必須同時提供起訖');
    }
    $_GET = [];

    $bodyRecordId = (int) $pdo->query(
        'SELECT body_record_id FROM body_records WHERE user_id = ' . (int) $user['user_id'] . ' LIMIT 1'
    )->fetchColumn();
    $deleteBody = new ReflectionMethod(Api::class, 'deleteBodyRecord');
    try {
        $deleteBody->invoke($api, (int) $user['user_id'], $bodyRecordId);
        check(false, '完成 Profile 後最後一筆體重不可刪除');
    } catch (ApiException $error) {
        check($error->errorCode === 'LAST_BODY_RECORD_REQUIRED', 'API 拒絕刪除最後一筆體重');
    }
    try {
        $pdo->prepare('DELETE FROM body_records WHERE body_record_id = ?')->execute([$bodyRecordId]);
        check(false, '繞過 API 仍不可刪除最後一筆體重');
    } catch (PDOException) {
        check(true, '資料庫 Trigger 拒絕刪除最後一筆體重');
    }

    for ($attempt = 1; $attempt <= 20; $attempt++) {
        try {
            LoginRateLimiter::attempt($pdo, '203.0.113.99', fn (): array => Auth::login($pdo, [
                'email' => 'demo@fittrack.local', 'password' => 'wrong-password',
            ]));
        } catch (ApiException $error) {
            check($error->status === 401, "第 {$attempt} 次失敗登入仍回 401 並計入窗口");
        }
    }
    try {
        LoginRateLimiter::attempt($pdo, '203.0.113.99', fn (): array => Auth::login($pdo, [
            'email' => 'demo@fittrack.local', 'password' => 'wrong-password',
        ]));
        check(false, '第 21 次登入應被限流');
    } catch (ApiException $error) {
        check($error->status === 429 && isset($error->headers['Retry-After']), '第 21 次回 429 與 Retry-After');
    }
    try {
        LoginRateLimiter::attempt($pdo, '203.0.113.100', fn (): array => Auth::login($pdo, [
            'email' => 'demo@fittrack.local', 'password' => 'wrong-password',
        ]));
    } catch (ApiException $error) {
        check($error->status === 401, '不同 IP 不共用失敗登入計數');
    }

    $overview = new ReflectionMethod(Api::class, 'databaseOverview');
    $databaseOverview = $overview->invoke($adminApi);
    check(count($databaseOverview['tables']) === 20, '管理介面顯示 20 張應用資料表');
    check(count($databaseOverview['relationships']) === 25, '管理介面顯示與 DDL 一致的 25 條外鍵關係');
} finally {
    if (is_file($databasePath)) {
        unlink($databasePath);
    }
}
