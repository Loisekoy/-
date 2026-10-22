<?php

declare(strict_types=1);

if (getenv('FITTRACK_TEST_DATABASE') !== '1') {
    fwrite(STDERR, "REFUSED: set FITTRACK_TEST_DATABASE=1 for the isolated test database.\n");
    exit(2);
}

$databaseUrl = (string) getenv('DATABASE_URL');
if (!str_contains($databaseUrl, 'fittrack_')) {
    fwrite(STDERR, "REFUSED: DATABASE_URL must name an isolated fittrack_* database.\n");
    exit(2);
}

putenv('APP_ENV=test');
putenv('SECRET_KEY=postgres-integrity-test-key');
putenv('RATE_LIMIT_SECRET=postgres-integrity-rate-limit-key');

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Api;
use FitTrack\ApiException;
use FitTrack\Auth;
use FitTrack\Database;
use FitTrack\PlanGenerator;

function checkPg(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
    echo "PASS: {$message}\n";
}

/** @return array{dsn:string,user:string,password:string} */
function pgConnectionParts(string $url): array
{
    $parts = parse_url($url);
    if (!$parts || !isset($parts['host'], $parts['path'])) {
        throw new RuntimeException('Invalid PostgreSQL test URL.');
    }
    return [
        'dsn' => sprintf(
            'pgsql:host=%s;port=%d;dbname=%s',
            $parts['host'],
            $parts['port'] ?? 5432,
            ltrim($parts['path'], '/')
        ),
        'user' => urldecode($parts['user'] ?? ''),
        'password' => urldecode($parts['pass'] ?? ''),
    ];
}

function independentPdo(string $url): PDO
{
    $parts = pgConnectionParts($url);
    return new PDO($parts['dsn'], $parts['user'], $parts['password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
}

/** @return array{user_id:int,plan_day_id:int} */
function createPreparedUser(PDO $pdo, string $suffix): array
{
    $registered = Auth::register($pdo, [
        'name' => 'PostgreSQL Test ' . $suffix,
        'email' => 'pg-' . $suffix . '@fittrack.test',
        'password' => 'TestPass12345',
    ]);
    $userId = (int) Auth::user($pdo, (string) $registered['access_token'])['user_id'];
    $goalId = (int) $pdo->query('SELECT training_goal_id FROM training_goals ORDER BY training_goal_id LIMIT 1')->fetchColumn();
    $partId = (int) $pdo->query('SELECT body_part_id FROM body_parts ORDER BY body_part_id LIMIT 1')->fetchColumn();
    Database::beginTransaction($pdo);
    try {
        $pdo->prepare(
            "UPDATE users SET age=22, height_cm=168.00, training_experience='Beginner', "
            . 'training_goal_id=?, training_days_per_week=2, training_duration_minutes=60 '
            . 'WHERE user_id=?'
        )->execute([$goalId, $userId]);
        $pdo->prepare('INSERT INTO user_body_parts (user_id, body_part_id) VALUES (?, ?)')->execute([$userId, $partId]);
        $pdo->prepare('INSERT INTO body_records (user_id, record_date, weight_kg) VALUES (?, CURRENT_DATE, 65.25)')
            ->execute([$userId]);
        $pdo->prepare('UPDATE users SET profile_completed_at=CURRENT_TIMESTAMP WHERE user_id=?')
            ->execute([$userId]);
        $pdo->commit();
    } catch (Throwable $error) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        throw $error;
    }
    $plan = PlanGenerator::generate($pdo, $userId, 'PostgreSQL Integrity Plan');
    return ['user_id' => $userId, 'plan_day_id' => (int) $plan['days'][0]['plan_day_id']];
}

function invokeStart(PDO $pdo, int $userId, int $planDayId): array
{
    $method = new ReflectionMethod(Api::class, 'startSession');
    return $method->invoke(new Api($pdo, '198.51.100.30'), $userId, ['plan_day_id' => $planDayId]);
}

function cleanupPreparedUser(PDO $pdo, int $userId): void
{
    $pdo->prepare("UPDATE workout_sessions SET status='cancelled', ended_at=COALESCE(ended_at, CURRENT_TIMESTAMP) WHERE user_id=?")
        ->execute([$userId]);
    $pdo->prepare(
        'DELETE FROM workout_sets USING workout_session_exercises wse, workout_sessions ws '
        . 'WHERE workout_sets.workout_session_exercise_id=wse.workout_session_exercise_id '
        . 'AND wse.workout_session_id=ws.workout_session_id AND ws.user_id=?'
    )->execute([$userId]);
    $pdo->prepare(
        'DELETE FROM workout_session_exercises USING workout_sessions ws '
        . 'WHERE workout_session_exercises.workout_session_id=ws.workout_session_id AND ws.user_id=?'
    )->execute([$userId]);
    $pdo->prepare(
        'DELETE FROM workout_session_plans USING workout_sessions ws '
        . 'WHERE workout_session_plans.workout_session_id=ws.workout_session_id AND ws.user_id=?'
    )->execute([$userId]);
    $pdo->prepare('DELETE FROM workout_sessions WHERE user_id=?')->execute([$userId]);
    $pdo->prepare(
        'DELETE FROM plan_exercises USING plan_days pd, workout_plans wp '
        . 'WHERE plan_exercises.plan_day_id=pd.plan_day_id AND pd.workout_plan_id=wp.workout_plan_id AND wp.user_id=?'
    )->execute([$userId]);
    $pdo->prepare(
        'DELETE FROM plan_days USING workout_plans wp '
        . 'WHERE plan_days.workout_plan_id=wp.workout_plan_id AND wp.user_id=?'
    )->execute([$userId]);
    $pdo->prepare(
        'DELETE FROM planning_profile_body_parts USING workout_plans wp '
        . 'WHERE planning_profile_body_parts.workout_plan_id=wp.workout_plan_id AND wp.user_id=?'
    )->execute([$userId]);
    $pdo->prepare(
        'DELETE FROM planning_profiles USING workout_plans wp '
        . 'WHERE planning_profiles.workout_plan_id=wp.workout_plan_id AND wp.user_id=?'
    )->execute([$userId]);
    $pdo->prepare('DELETE FROM workout_plans WHERE user_id=?')->execute([$userId]);
    $pdo->prepare('UPDATE users SET profile_completed_at=NULL WHERE user_id=?')->execute([$userId]);
    $pdo->prepare('DELETE FROM users WHERE user_id=?')->execute([$userId]);
}

$pdo = Database::connection();
$suffix = bin2hex(random_bytes(5));
$createdUserIds = [];

try {
    checkPg($pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql', '測試確實使用 PostgreSQL');
    checkPg((string) $pdo->query('SHOW transaction_isolation')->fetchColumn() === 'read committed', '交易隔離層級明確為 READ COMMITTED');
    checkPg((int) $pdo->query("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' AND tablename <> 'schema_migrations'")->fetchColumn() === 20, 'PostgreSQL 建立 20 張應用資料表');
    checkPg((int) $pdo->query("SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY'")->fetchColumn() === 25, 'PostgreSQL 建立 25 條外鍵');

    $prepared = createPreparedUser($pdo, $suffix);
    $createdUserIds[] = $prepared['user_id'];
    $algorithm = $pdo->prepare(
        'SELECT pp.algorithm_version FROM planning_profiles pp '
        . 'JOIN workout_plans wp ON wp.workout_plan_id = pp.workout_plan_id '
        . 'WHERE wp.user_id = ? ORDER BY wp.workout_plan_id DESC LIMIT 1'
    );
    $algorithm->execute([$prepared['user_id']]);
    checkPg($algorithm->fetchColumn() === 'rules-v1', 'PostgreSQL 規則式課表使用可重現的 rules-v1');
    [$status, $session] = invokeStart($pdo, $prepared['user_id'], $prepared['plan_day_id']);
    checkPg($status === 201 && count($session['exercises']) > 0, '開始訓練時建立場次動作快照');
    $sessionId = (int) $session['workout_session_id'];
    $sessionExerciseId = (int) $session['exercises'][0]['workout_session_exercise_id'];

    try {
        $pdo->prepare("UPDATE workout_sessions SET status='completed', ended_at=CURRENT_TIMESTAMP WHERE workout_session_id=?")
            ->execute([$sessionId]);
        checkPg(false, '空場次不應完成');
    } catch (PDOException $error) {
        checkPg($error->getCode() === '23514', '延遲 Constraint Trigger 阻止 completed 空場次');
    }

    $pdo->prepare('INSERT INTO workout_sets (workout_session_exercise_id, set_number, weight_kg, reps) VALUES (?, 1, 40.50, 10)')
        ->execute([$sessionExerciseId]);
    $pdo->prepare("UPDATE workout_sessions SET status='completed', ended_at=CURRENT_TIMESTAMP WHERE workout_session_id=?")
        ->execute([$sessionId]);
    checkPg((string) $pdo->query('SELECT status FROM workout_sessions WHERE workout_session_id=' . $sessionId)->fetchColumn() === 'completed', '至少一組後可完成場次');

    try {
        $pdo->prepare('DELETE FROM workout_sets WHERE workout_session_exercise_id=? AND set_number=1')->execute([$sessionExerciseId]);
        checkPg(false, '完成場次最後一組不應被刪除');
    } catch (PDOException $error) {
        checkPg($error->getCode() === '23514', '資料庫阻止刪除 completed 場次最後一組');
    }

    try {
        $pdo->prepare('DELETE FROM workout_session_exercises WHERE workout_session_exercise_id=?')->execute([$sessionExerciseId]);
        checkPg(false, '完成場次的最後一個動作快照不應被刪除');
    } catch (PDOException $error) {
        checkPg($error->getCode() === '23514', '資料庫阻止藉由刪除場次動作繞過 completed 至少一組約束');
    }

    $versionId = (int) $session['exercises'][0]['exercise_version_id'];
    try {
        $pdo->prepare('UPDATE exercise_versions SET exercise_name=? WHERE exercise_version_id=?')->execute(['非法覆寫', $versionId]);
        checkPg(false, '動作版本不應被覆寫');
    } catch (PDOException $error) {
        checkPg($error->getCode() === '23514', '不可變 Trigger 阻止覆寫 exercise_versions');
    }

    $bodyRecordId = (int) $pdo->query('SELECT body_record_id FROM body_records WHERE user_id=' . $prepared['user_id'])->fetchColumn();
    try {
        $pdo->prepare('DELETE FROM body_records WHERE body_record_id=?')->execute([$bodyRecordId]);
        checkPg(false, '完整 Profile 的最後一筆體重不應被刪除');
    } catch (PDOException $error) {
        checkPg($error->getCode() === '23514', '資料庫阻止刪除完整 Profile 的最後一筆體重');
    }

    $invariantRegistration = Auth::register($pdo, [
        'name' => 'PostgreSQL Invariant ' . $suffix,
        'email' => 'pg-invariant-' . $suffix . '@fittrack.test',
        'password' => 'InvariantPass123',
    ]);
    $invariantUserId = (int) Auth::user($pdo, (string) $invariantRegistration['access_token'])['user_id'];
    $createdUserIds[] = $invariantUserId;
    try {
        $pdo->prepare('UPDATE users SET profile_completed_at=CURRENT_TIMESTAMP WHERE user_id=?')
            ->execute([$invariantUserId]);
        checkPg(false, '無體重的 Profile 不得設為完成');
    } catch (PDOException $error) {
        checkPg($error->getCode() === '23514', '延遲 Constraint Trigger 拒絕無體重的完成 Profile');
    }
    try {
        $pdo->prepare('UPDATE body_records SET user_id=? WHERE body_record_id=?')
            ->execute([$invariantUserId, $bodyRecordId]);
        checkPg(false, '不得移走已完成 Profile 的最後體重');
    } catch (PDOException $error) {
        checkPg($error->getCode() === '23514', '延遲 Constraint Trigger 拒絕移走最後體重');
    }

    try {
        $pdo->prepare(
            "INSERT INTO workout_sessions (user_id, status, started_at, ended_at) "
            . "VALUES (?, 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        )->execute([$prepared['user_id']]);
        checkPg(false, '不得直接建立空的 completed 場次');
    } catch (PDOException $error) {
        checkPg($error->getCode() === '23514', '延遲 Constraint Trigger 拒絕直接建立空的 completed 場次');
    }

    $concurrent = createPreparedUser($pdo, $suffix . '-concurrent');
    $createdUserIds[] = $concurrent['user_id'];
    if (!function_exists('pcntl_fork')) {
        throw new RuntimeException('pcntl extension is required for the PostgreSQL concurrency test.');
    }
    $resultFiles = [];
    for ($worker = 1; $worker <= 2; $worker++) {
        $resultFile = sys_get_temp_dir() . '/fittrack-pg-concurrency-' . getmypid() . '-' . $worker . '.json';
        $resultFiles[] = $resultFile;
        $pid = pcntl_fork();
        if ($pid === -1) {
            throw new RuntimeException('Unable to fork concurrency worker.');
        }
        if ($pid === 0) {
            try {
                $childPdo = independentPdo($databaseUrl);
                usleep(100000);
                [$childStatus, $childSession] = invokeStart(
                    $childPdo,
                    $concurrent['user_id'],
                    $concurrent['plan_day_id']
                );
                file_put_contents($resultFile, json_encode([
                    'status' => $childStatus,
                    'session_id' => $childSession['workout_session_id'] ?? null,
                ], JSON_THROW_ON_ERROR));
                exit(0);
            } catch (Throwable $error) {
                file_put_contents($resultFile, json_encode([
                    'error' => get_class($error),
                    'message' => $error->getMessage(),
                ], JSON_THROW_ON_ERROR));
                exit(1);
            }
        }
    }
    while (pcntl_wait($workerStatus) > 0) {
        // Wait for both independently connected requests.
    }
    $results = [];
    foreach ($resultFiles as $resultFile) {
        $results[] = json_decode((string) file_get_contents($resultFile), true, 512, JSON_THROW_ON_ERROR);
        unlink($resultFile);
    }
    // libpq connections opened before fork must not be reused by the parent.
    $pdo = independentPdo($databaseUrl);
    checkPg(!isset($results[0]['error'], $results[1]['error']), '兩個平行 Request 均取得可解釋回應');
    checkPg(
        in_array((int) $results[0]['status'], [200, 201], true)
        && in_array((int) $results[1]['status'], [200, 201], true)
        && (int) $results[0]['session_id'] === (int) $results[1]['session_id'],
        '同日雙擊「開始運動」回傳同一場次（201 + 200）'
    );
    $activeCount = $pdo->prepare("SELECT COUNT(*) FROM workout_sessions WHERE user_id=? AND status='in_progress'");
    $activeCount->execute([$concurrent['user_id']]);
    checkPg((int) $activeCount->fetchColumn() === 1, '使用者列鎖與部分唯一索引保證僅一個進行中場次');

    $differentDay = createPreparedUser($pdo, $suffix . '-different-day');
    $createdUserIds[] = $differentDay['user_id'];
    $dayStatement = $pdo->prepare(
        'SELECT pd.plan_day_id FROM plan_days pd JOIN workout_plans wp ON wp.workout_plan_id=pd.workout_plan_id '
        . 'WHERE wp.user_id=? ORDER BY pd.day_number LIMIT 2'
    );
    $dayStatement->execute([$differentDay['user_id']]);
    $differentDayIds = array_map('intval', $dayStatement->fetchAll(PDO::FETCH_COLUMN));
    checkPg(count($differentDayIds) === 2, '異日併發測試具有兩個不同課表日');
    $differentDayFiles = [];
    foreach ($differentDayIds as $worker => $differentPlanDayId) {
        $resultFile = sys_get_temp_dir() . '/fittrack-pg-different-day-' . getmypid() . '-' . $worker . '.json';
        $differentDayFiles[] = $resultFile;
        $pid = pcntl_fork();
        if ($pid === -1) {
            throw new RuntimeException('Unable to fork different-day concurrency worker.');
        }
        if ($pid === 0) {
            try {
                $childPdo = independentPdo($databaseUrl);
                usleep(100000);
                [$childStatus, $childSession] = invokeStart(
                    $childPdo,
                    $differentDay['user_id'],
                    $differentPlanDayId
                );
                $payload = ['status' => $childStatus, 'session_id' => $childSession['workout_session_id'] ?? null];
            } catch (ApiException $error) {
                $payload = ['status' => $error->status, 'code' => $error->errorCode];
            } catch (Throwable $error) {
                $payload = ['error' => get_class($error), 'message' => $error->getMessage()];
            }
            file_put_contents($resultFile, json_encode($payload, JSON_THROW_ON_ERROR));
            exit(isset($payload['error']) ? 1 : 0);
        }
    }
    while (pcntl_wait($workerStatus) > 0) {
        // Wait for both different-day requests.
    }
    $differentResults = [];
    foreach ($differentDayFiles as $resultFile) {
        $differentResults[] = json_decode((string) file_get_contents($resultFile), true, 512, JSON_THROW_ON_ERROR);
        unlink($resultFile);
    }
    $pdo = independentPdo($databaseUrl);
    checkPg(!isset($differentResults[0]['error'], $differentResults[1]['error']), '異日平行 Request 均回傳明確 API 狀態');
    $differentStatuses = array_map(static fn (array $item): int => (int) $item['status'], $differentResults);
    sort($differentStatuses);
    checkPg($differentStatuses === [201, 409], '異日同時開始僅一個 201，另一個 409');
    $activeCount = $pdo->prepare("SELECT COUNT(*) FROM workout_sessions WHERE user_id=? AND status='in_progress'");
    $activeCount->execute([$differentDay['user_id']]);
    checkPg((int) $activeCount->fetchColumn() === 1, '異日併發不會產生兩個進行中場次');

    $deleteRace = createPreparedUser($pdo, $suffix . '-delete-race');
    $createdUserIds[] = $deleteRace['user_id'];
    [$deleteStatus, $deleteSession] = invokeStart($pdo, $deleteRace['user_id'], $deleteRace['plan_day_id']);
    checkPg($deleteStatus === 201, '最後組併發刪除測試場次已建立');
    $deleteSessionId = (int) $deleteSession['workout_session_id'];
    $deleteExerciseId = (int) $deleteSession['exercises'][0]['workout_session_exercise_id'];
    $deleteSetStatement = $pdo->prepare(
        'INSERT INTO workout_sets (workout_session_exercise_id, set_number, weight_kg, reps) '
        . 'VALUES (?, ?, 30.00, 10) RETURNING workout_set_id'
    );
    $deleteSetIds = [];
    foreach ([1, 2] as $setNumber) {
        $deleteSetStatement->execute([$deleteExerciseId, $setNumber]);
        $deleteSetIds[] = (int) $deleteSetStatement->fetchColumn();
    }
    $pdo->prepare("UPDATE workout_sessions SET status='completed', ended_at=CURRENT_TIMESTAMP WHERE workout_session_id=?")
        ->execute([$deleteSessionId]);

    $readyFiles = [
        sys_get_temp_dir() . '/fittrack-pg-delete-ready-' . getmypid() . '-0',
        sys_get_temp_dir() . '/fittrack-pg-delete-ready-' . getmypid() . '-1',
    ];
    $deleteResultFiles = [
        sys_get_temp_dir() . '/fittrack-pg-delete-result-' . getmypid() . '-0.json',
        sys_get_temp_dir() . '/fittrack-pg-delete-result-' . getmypid() . '-1.json',
    ];
    foreach ($deleteSetIds as $worker => $deleteSetId) {
        $pid = pcntl_fork();
        if ($pid === -1) {
            throw new RuntimeException('Unable to fork last-set delete worker.');
        }
        if ($pid === 0) {
            $payload = [];
            try {
                $childPdo = independentPdo($databaseUrl);
                $childPdo->beginTransaction();
                $childPdo->prepare('DELETE FROM workout_sets WHERE workout_set_id=?')->execute([$deleteSetId]);
                file_put_contents($readyFiles[$worker], 'ready');
                $other = $readyFiles[1 - $worker];
                $deadline = microtime(true) + 5;
                while (!is_file($other) && microtime(true) < $deadline) {
                    usleep(10000);
                }
                if (!is_file($other)) {
                    throw new RuntimeException('Delete concurrency barrier timed out.');
                }
                $childPdo->commit();
                $payload = ['status' => 'committed'];
            } catch (PDOException $error) {
                if (isset($childPdo) && $childPdo->inTransaction()) {
                    $childPdo->rollBack();
                }
                $payload = ['status' => 'rejected', 'code' => $error->getCode()];
            } catch (Throwable $error) {
                if (isset($childPdo) && $childPdo->inTransaction()) {
                    $childPdo->rollBack();
                }
                $payload = ['error' => get_class($error), 'message' => $error->getMessage()];
            }
            file_put_contents($deleteResultFiles[$worker], json_encode($payload, JSON_THROW_ON_ERROR));
            exit(isset($payload['error']) ? 1 : 0);
        }
    }
    while (pcntl_wait($workerStatus) > 0) {
        // Wait for both delete transactions to commit or roll back.
    }
    $deleteResults = [];
    foreach ($deleteResultFiles as $resultFile) {
        $deleteResults[] = json_decode((string) file_get_contents($resultFile), true, 512, JSON_THROW_ON_ERROR);
        unlink($resultFile);
    }
    foreach ($readyFiles as $readyFile) {
        if (is_file($readyFile)) {
            unlink($readyFile);
        }
    }
    $pdo = independentPdo($databaseUrl);
    checkPg(!isset($deleteResults[0]['error'], $deleteResults[1]['error']), '兩個刪組交易均取得明確結果');
    $committedDeletes = count(array_filter(
        $deleteResults,
        static fn (array $item): bool => ($item['status'] ?? '') === 'committed'
    ));
    $constraintRejects = count(array_filter(
        $deleteResults,
        static fn (array $item): bool => ($item['code'] ?? '') === '23514'
    ));
    checkPg($committedDeletes === 1 && $constraintRejects === 1, '兩筆最後組併發刪除僅一筆提交，另一筆以 23514 回滾');
    $remainingSets = $pdo->prepare(
        'SELECT COUNT(*) FROM workout_sets ws JOIN workout_session_exercises wse '
        . 'ON wse.workout_session_exercise_id=ws.workout_session_exercise_id WHERE wse.workout_session_id=?'
    );
    $remainingSets->execute([$deleteSessionId]);
    checkPg((int) $remainingSets->fetchColumn() === 1, '併發刪除後 completed 場次仍保留一組');

    echo "PostgreSQL integrity and concurrency checks completed.\n";
} finally {
    foreach ($createdUserIds as $userId) {
        cleanupPreparedUser($pdo, $userId);
    }
}
