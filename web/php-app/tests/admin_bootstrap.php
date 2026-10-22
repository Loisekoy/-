<?php

declare(strict_types=1);

$databasePath = sys_get_temp_dir() . '/fittrack-admin-bootstrap-' . bin2hex(random_bytes(6)) . '.sqlite';
putenv('APP_ENV=test');
putenv('SQLITE_PATH=' . $databasePath);
putenv('SECRET_KEY=admin-bootstrap-test-secret');
putenv('RATE_LIMIT_SECRET=admin-bootstrap-test-rate-secret');
putenv('DEMO_BOOTSTRAP_PASSWORD=Demo123456');
putenv('DEMO_ADMIN_PASSWORD=InitialAdmin123');

require dirname(__DIR__) . '/src/bootstrap.php';

function bootstrapCheck(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
    echo "PASS: {$message}\n";
}

try {
    $pdo = \FitTrack\Database::connection();
    $adminHash = (string) $pdo->query(
        "SELECT ua.password_hash FROM user_auth ua WHERE ua.email='admin@fittrack.local'"
    )->fetchColumn();
    bootstrapCheck(password_verify('InitialAdmin123', $adminHash), '首次建置會建立展示管理員密碼');

    // setup.php is also run on every container start.  A changed Render
    // environment value must therefore repair the existing demo account.
    putenv('DEMO_ADMIN_PASSWORD=RotatedAdmin123');
    require dirname(__DIR__) . '/bin/setup.php';

    $rotatedHash = (string) $pdo->query(
        "SELECT ua.password_hash FROM user_auth ua WHERE ua.email='admin@fittrack.local'"
    )->fetchColumn();
    bootstrapCheck(password_verify('RotatedAdmin123', $rotatedHash), '重啟時會同步 Render 的管理員初始密碼');
    bootstrapCheck(!password_verify('InitialAdmin123', $rotatedHash), '舊管理員密碼不會在同步後繼續有效');
} finally {
    foreach ([$databasePath, $databasePath . '-wal', $databasePath . '-shm'] as $path) {
        if (is_file($path)) {
            unlink($path);
        }
    }
}
