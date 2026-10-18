<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Database;

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');

$driver = Database::driver();
$assetVersion = static function (string $file): string {
    $path = __DIR__ . '/assets/' . $file;
    $hash = @hash_file('sha256', $path);
    return $hash === false ? '1' : substr($hash, 0, 12);
};
$appCss = '/assets/app.css?v=' . rawurlencode($assetVersion('app.css'));
$appJs = '/assets/app.js?v=' . rawurlencode($assetVersion('app.js'));
?>
<!doctype html>
<html lang="zh-Hant">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="以 PostgreSQL 為核心的健身課表與訓練紀錄系統">
    <title>FitTrack Pro - 健身紀錄管理系統</title>
    <link rel="stylesheet" href="<?= htmlspecialchars($appCss, ENT_QUOTES, 'UTF-8') ?>">
</head>
<body data-db-driver="<?= htmlspecialchars($driver, ENT_QUOTES, 'UTF-8') ?>">
    <div id="app" aria-live="polite">
        <header class="site-header" id="site-header"></header>
        <main id="main-content" tabindex="-1">
            <div class="loading-screen">
                <span class="loading-mark" aria-hidden="true"></span>
                <p>正在連接訓練資料庫...</p>
            </div>
        </main>
        <footer class="site-footer">
            <span>FitTrack Pro</span>
            <span>Exercise media © Gym visual</span>
            <span id="database-status"><?= htmlspecialchars(strtoupper($driver), ENT_QUOTES, 'UTF-8') ?></span>
        </footer>
    </div>
    <div id="toast-region" class="toast-region" aria-live="assertive"></div>
    <script type="module" src="<?= htmlspecialchars($appJs, ENT_QUOTES, 'UTF-8') ?>"></script>
</body>
</html>
