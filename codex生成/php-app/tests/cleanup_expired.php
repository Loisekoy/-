<?php

declare(strict_types=1);

$databasePath = sys_get_temp_dir() . '/fittrack-cleanup-' . bin2hex(random_bytes(6)) . '.sqlite';
putenv('APP_ENV=test');
putenv('SQLITE_PATH=' . $databasePath);
putenv('SECRET_KEY=cleanup-test-secret');
putenv('RATE_LIMIT_SECRET=cleanup-test-rate-secret');

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Database;
use FitTrack\ExpiredDataCleaner;

function cleanupCheck(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
    echo "PASS: {$message}\n";
}

try {
    $pdo = Database::connection();
    $authId = (int) $pdo->query('SELECT auth_id FROM user_auth ORDER BY auth_id LIMIT 1')->fetchColumn();
    $insertSession = $pdo->prepare(
        'INSERT INTO user_sessions (user_session_id, auth_id, created_at, expires_at) VALUES (?, ?, ?, ?)'
    );
    $pdo->beginTransaction();
    for ($index = 0; $index < 501; $index++) {
        $insertSession->execute([
            sprintf('expired-%04d-%s', $index, bin2hex(random_bytes(4))),
            $authId,
            '2026-10-14 00:00:00',
            '2026-10-15 00:00:00',
        ]);
    }
    $validSessionId = 'valid-' . bin2hex(random_bytes(8));
    $insertSession->execute([
        $validSessionId,
        $authId,
        gmdate('Y-m-d H:i:s'),
        gmdate('Y-m-d H:i:s', time() + 7200),
    ]);
    $insertFailure = $pdo->prepare('INSERT INTO login_failures (ip_hash, failed_at) VALUES (?, ?)');
    $insertFailure->execute([str_repeat('a', 64), '2026-10-15 00:00:00']);
    $insertFailure->execute([str_repeat('b', 64), gmdate('Y-m-d H:i:s')]);
    $pdo->commit();

    $result = ExpiredDataCleaner::run($pdo);
    $output = json_encode($result, JSON_THROW_ON_ERROR);

    cleanupCheck($result['status'] === 'ok', '清理排程輸出可機器解析的成功 JSON');
    cleanupCheck((int) $result['expired_sessions_deleted'] === 501, '超過 500 筆時會分批清理所有過期 Session');
    cleanupCheck((int) $result['expired_login_failures_deleted'] === 1, '只清理超過 15 分鐘的失敗登入事件');
    $remaining = $pdo->query('SELECT user_session_id FROM user_sessions')->fetchAll(PDO::FETCH_COLUMN);
    cleanupCheck(in_array($validSessionId, $remaining, true), '有效 Session 保留');
    cleanupCheck(count($remaining) === 1, '過期 Session 無漏刪');
    cleanupCheck((int) $pdo->query('SELECT COUNT(*) FROM login_failures')->fetchColumn() === 1, '視窗內的限流事件保留');
    cleanupCheck(
        !preg_match('/token|password|[a-f0-9]{64}/i', $output),
        '清理日誌不包含 Token、密碼、雜湊或原始 IP'
    );
} finally {
    if (is_file($databasePath)) {
        unlink($databasePath);
    }
}
