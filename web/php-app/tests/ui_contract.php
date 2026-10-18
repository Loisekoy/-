<?php

declare(strict_types=1);

$root = dirname(__DIR__, 3);
$app = (string) file_get_contents(__DIR__ . '/../public/assets/app.js');
$index = (string) file_get_contents(__DIR__ . '/../public/index.php');
$render = (string) file_get_contents($root . '/render.yaml');
$maintenance = (string) file_get_contents($root . '/.github/workflows/fittrack-maintenance.yml');
$mediaManifest = (string) file_get_contents(__DIR__ . '/../docs/validation/media-sha256.txt');

function contractCheck(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
    echo "PASS: {$message}\n";
}

contractCheck(str_contains($app, 'class="workout-total-timer"'), '訓練頁提供總計時器區塊');
contractCheck(str_contains($app, "startWorkoutTimer(session.started_at)"), '只有載入進行中場次後才啟動總計時器');
contractCheck(str_contains($app, "return '儲存一組後開始'"), '尚未儲存組數時休息計時器保持等待狀態');
$saveSetPosition = strpos($app, "action === 'save-set'");
$restStartPosition = strpos($app, 'startRestTimer(Number(control.dataset.restSeconds))', $saveSetPosition === false ? 0 : $saveSetPosition);
contractCheck($saveSetPosition !== false && $restStartPosition !== false, '休息計時器只在儲存組數流程完成後啟動');
contractCheck(str_contains($app, 'data-status="cancel"') && str_contains($app, '取消本次訓練'), '訓練頁提供取消本次訓練操作');
contractCheck(str_contains($app, 'data-action="delete-plan"') && str_contains($app, '封存課表'), '課表操作使用封存而非永久刪除文字');
contractCheck(str_contains($app, 'aria-label="搜尋動作名稱或身體部位"')
    && str_contains($app, 'for="admin-exercise-name"')
    && str_contains($app, 'for="admin-exercise-description"'), '動作資料庫與管理表單具有可辨識欄位標籤');
contractCheck(str_contains($app, 'data-action="toggle-user"')
    && str_contains($app, '停用帳號')
    && str_contains($app, '恢復帳號')
    && str_contains($app, 'api(`/admin/users/${control.dataset.userId}`'), '管理員會員清單提供停用與恢復帳號操作');
contractCheck(str_contains($app, "path === '/admin/login'")
    && str_contains($app, "path === '/admin'")
    && str_contains($app, "path === '/database'"), '公開 Demo 的管理者與資料庫連結可直接進入登入流程');
contractCheck(str_contains($index, 'hash_file(\'sha256\', $path)')
    && str_contains($index, '/assets/app.js?v=')
    && str_contains($index, '/assets/app.css?v='), '前端資源使用內容版本號，避免部署後沿用舊快取');

contractCheck(str_contains($render, 'dockerfilePath: ./Dockerfile.render')
    && preg_match('/key: DATABASE_URL\s*\n\s*#.*\n\s*#.*\n\s*sync: false/s', $render) === 1,
    'Render 使用正式 Dockerfile 並保留 Neon DATABASE_URL 為外部 Secret');
contractCheck(str_contains($render, "key: AI_API_KEY\n        value: \"\""), 'Render 保留空白 AI_API_KEY 欄位');
contractCheck(preg_match('/key: DEMO_ADMIN_PASSWORD\s*\n\s*#.*\n\s*sync: false/s', $render) === 1
    && !preg_match('/key: DEMO_ADMIN_PASSWORD\s*\n\s*value:\s*\S+/s', $render), 'Render 不把管理員密碼寫入 Git，改由 Dashboard Secret 提供');
contractCheck(str_contains($maintenance, 'bin/cleanup-expired.php')
    && str_contains($maintenance, 'pg_dump')
    && str_contains($maintenance, 'pg_restore')
    && str_contains($maintenance, 'retention-days: 7'), '每日清理、備份與獨立還原工作流程已定義');
$mediaLines = preg_grep('/^[a-f0-9]{64}  /', preg_split('/\R/', $mediaManifest) ?: []);
contractCheck(count($mediaLines) >= 2600, '動作圖片 SHA-256 清單涵蓋完整資料集');
