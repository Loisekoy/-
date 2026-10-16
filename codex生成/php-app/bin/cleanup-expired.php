<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Database;

$pdo = Database::connection();
$driver = (string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME);
$startedAt = microtime(true);
$deletedSessions = 0;
$deletedFailures = 0;
$locked = false;

try {
    if ($driver === 'pgsql') {
        $locked = (bool) $pdo->query('SELECT pg_try_advisory_lock(671902106)')->fetchColumn();
        if (!$locked) {
            fwrite(STDOUT, json_encode([
                'status' => 'skipped',
                'reason' => 'another cleanup job is running',
                'time_zone' => 'Asia/Taipei',
            ], JSON_UNESCAPED_UNICODE) . PHP_EOL);
            exit(0);
        }
    }

    do {
        $pdo->beginTransaction();
        if ($driver === 'pgsql') {
            $statement = $pdo->prepare(
                'DELETE FROM user_sessions WHERE user_session_id IN ('
                . 'SELECT user_session_id FROM user_sessions WHERE expires_at <= CURRENT_TIMESTAMP '
                . 'ORDER BY expires_at LIMIT 500 FOR UPDATE SKIP LOCKED)'
            );
        } else {
            $statement = $pdo->prepare(
                'DELETE FROM user_sessions WHERE user_session_id IN ('
                . 'SELECT user_session_id FROM user_sessions WHERE expires_at <= CURRENT_TIMESTAMP '
                . 'ORDER BY expires_at LIMIT 500)'
            );
        }
        $statement->execute();
        $batch = $statement->rowCount();
        $deletedSessions += $batch;
        $pdo->commit();
    } while ($batch === 500);

    if ($driver === 'pgsql') {
        $statement = $pdo->prepare(
            "DELETE FROM login_failures WHERE failed_at <= CURRENT_TIMESTAMP - INTERVAL '15 minutes'"
        );
    } else {
        $statement = $pdo->prepare(
            "DELETE FROM login_failures WHERE failed_at <= datetime('now', '-15 minutes')"
        );
    }
    $statement->execute();
    $deletedFailures = $statement->rowCount();

    fwrite(STDOUT, json_encode([
        'status' => 'ok',
        'expired_sessions_deleted' => $deletedSessions,
        'expired_login_failures_deleted' => $deletedFailures,
        'elapsed_ms' => (int) round((microtime(true) - $startedAt) * 1000),
        'time_zone' => 'Asia/Taipei',
    ], JSON_UNESCAPED_UNICODE) . PHP_EOL);
} catch (Throwable $error) {
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }
    error_log('Session cleanup failed [' . get_class($error) . '] code=' . $error->getCode());
    fwrite(STDERR, json_encode([
        'status' => 'error',
        'error_type' => get_class($error),
        'error_code' => (string) $error->getCode(),
    ], JSON_UNESCAPED_UNICODE) . PHP_EOL);
    exit(1);
} finally {
    if ($driver === 'pgsql' && $locked) {
        $pdo->query('SELECT pg_advisory_unlock(671902106)');
    }
}
