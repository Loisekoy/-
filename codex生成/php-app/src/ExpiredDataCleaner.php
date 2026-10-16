<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;
use Throwable;

final class ExpiredDataCleaner
{
    /** @return array{status:string,expired_sessions_deleted?:int,expired_login_failures_deleted?:int,elapsed_ms?:int,time_zone:string,reason?:string} */
    public static function run(PDO $pdo): array
    {
        $driver = (string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME);
        $startedAt = microtime(true);
        $deletedSessions = 0;
        $locked = false;

        try {
            if ($driver === 'pgsql') {
                $locked = (bool) $pdo->query('SELECT pg_try_advisory_lock(671902106)')->fetchColumn();
                if (!$locked) {
                    return [
                        'status' => 'skipped',
                        'reason' => 'another cleanup job is running',
                        'time_zone' => 'Asia/Taipei',
                    ];
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

            return [
                'status' => 'ok',
                'expired_sessions_deleted' => $deletedSessions,
                'expired_login_failures_deleted' => $statement->rowCount(),
                'elapsed_ms' => (int) round((microtime(true) - $startedAt) * 1000),
                'time_zone' => 'Asia/Taipei',
            ];
        } catch (Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        } finally {
            if ($driver === 'pgsql' && $locked) {
                $pdo->query('SELECT pg_advisory_unlock(671902106)');
            }
        }
    }
}
