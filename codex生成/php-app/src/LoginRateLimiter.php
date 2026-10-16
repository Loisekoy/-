<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;
use PDOException;

final class LoginRateLimiter
{
    private const WINDOW_SECONDS = 900;
    private const MAX_FAILURES = 20;

    /** @return array<string,mixed> */
    public static function attempt(PDO $pdo, string $clientIp, callable $authenticate): array
    {
        $ipHash = hash_hmac('sha256', $clientIp, Config::rateLimitSecret());
        try {
            Database::beginTransaction($pdo);
            if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql') {
                $lock = $pdo->prepare('SELECT pg_advisory_xact_lock(hashtextextended(?, 0))');
                $lock->execute([$ipHash]);
            }
            self::deleteExpired($pdo, $ipHash);
            $oldest = $pdo->prepare(
                'SELECT COUNT(*) AS failure_count, MIN(failed_at) AS oldest_failure '
                . 'FROM login_failures WHERE ip_hash = ?'
            );
            $oldest->execute([$ipHash]);
            $state = $oldest->fetch() ?: ['failure_count' => 0, 'oldest_failure' => null];
            if ((int) $state['failure_count'] >= self::MAX_FAILURES) {
                $retryAfter = self::retryAfter((string) $state['oldest_failure']);
                $pdo->commit();
                throw new ApiException(
                    429,
                    'LOGIN_RATE_LIMITED',
                    '登入失敗次數過多，請稍後再試。',
                    ['Retry-After' => (string) $retryAfter]
                );
            }

            try {
                $result = $authenticate();
            } catch (ApiException $error) {
                if ($error->status === 401 && $error->errorCode === 'INVALID_CREDENTIALS') {
                    $pdo->prepare(
                        'INSERT INTO login_failures (ip_hash, failed_at) VALUES (?, CURRENT_TIMESTAMP)'
                    )->execute([$ipHash]);
                    $pdo->commit();
                    throw $error;
                }
                throw $error;
            }

            $pdo->prepare('DELETE FROM login_failures WHERE ip_hash = ?')->execute([$ipHash]);
            $pdo->commit();
            return $result;
        } catch (ApiException $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        } catch (PDOException $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            error_log('Login rate limiter database error: ' . $error->getCode());
            throw new ApiException(503, 'LOGIN_PROTECTION_UNAVAILABLE', '登入保護暫時無法使用，請稍後再試。');
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }
    }

    private static function deleteExpired(PDO $pdo, string $ipHash): void
    {
        if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql') {
            $pdo->prepare(
                "DELETE FROM login_failures WHERE ip_hash = ? AND failed_at <= CURRENT_TIMESTAMP - INTERVAL '15 minutes'"
            )->execute([$ipHash]);
            return;
        }
        $pdo->prepare(
            "DELETE FROM login_failures WHERE ip_hash = ? AND failed_at <= datetime('now', '-15 minutes')"
        )->execute([$ipHash]);
    }

    private static function retryAfter(string $oldestFailure): int
    {
        $oldest = strtotime($oldestFailure);
        if ($oldest === false) {
            return self::WINDOW_SECONDS;
        }
        return max(1, ($oldest + self::WINDOW_SECONDS) - time());
    }
}
