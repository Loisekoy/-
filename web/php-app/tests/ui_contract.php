<?php

declare(strict_types=1);

$root = dirname(__DIR__, 3);
$app = (string) file_get_contents(__DIR__ . '/../public/assets/app.js');
$index = (string) file_get_contents(__DIR__ . '/../public/index.php');
$render = (string) file_get_contents($root . '/render.yaml');
$maintenance = (string) file_get_contents($root . '/.github/workflows/fittrack-maintenance.yml');
$loadWorkflow = (string) file_get_contents($root . '/.github/workflows/fittrack-load-acceptance.yml');
$loadScript = (string) file_get_contents(__DIR__ . '/load/fittrack.js');
$migrate = (string) file_get_contents(__DIR__ . '/../bin/migrate.php');
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
contractCheck(str_contains($app, 'api(`/plans?page=${state.planPage}&page_size=20`)')
    && str_contains($app, "paginationMarkup(result, 'plan-page', '課表分頁')"), '課表清單提供共通分頁控制');
contractCheck(str_contains($app, 'class="plan-weight"')
    && str_contains($app, 'target_weight_kg: row.querySelector(\'.plan-weight\')'), '課表編輯可顯示、修改與清除目標重量');
contractCheck(str_contains($app, "timeZone: 'Asia/Taipei'")
    && str_contains($app, 'max="${taipeiToday()}"'), '體重日期上限依台北日期計算');
contractCheck(str_contains($app, 'api(`/body-records?page=${state.bodyRecordPage}&page_size=20`)')
    && str_contains($app, 'data-action="edit-body-record"'), '體重紀錄支援分頁與日期編輯');
contractCheck(str_contains($app, "data-action=\"history-page\"")
    && str_contains($app, "session.status === 'cancelled' ? ''"), '訓練歷史支援分頁且取消場次不顯示編修控制');
contractCheck(str_contains($app, 'body-part-priority')
    && str_contains($app, 'state.bodyPartPriority.push(id)'), '偏好部位保留使用者點選順位');
contractCheck(str_contains($app, 'aria-label="搜尋動作名稱或身體部位"')
    && str_contains($app, 'for="admin-exercise-name"')
    && str_contains($app, 'for="admin-exercise-description"'), '動作資料庫與管理表單具有可辨識欄位標籤');
contractCheck(!str_contains($app, 'data-action="toggle-user"')
    && str_contains($app, '管理員清單為唯讀'), '管理員會員清單不提供停用或恢復他人帳號');
contractCheck(str_contains($app, 'tableData.rows_hidden_for_privacy')
    && str_contains($app, '不顯示其他會員的資料列'), '資料庫管理畫面不預覽其他會員私密資料列');
contractCheck(str_contains($app, "path === '/admin/login'")
    && str_contains($app, "path === '/admin'")
    && str_contains($app, "path === '/database'"), '公開 Demo 的管理者與資料庫連結可直接進入登入流程');
contractCheck(str_contains($index, 'hash_file(\'sha256\', $path)')
    && str_contains($index, '/assets/app.js?v=')
    && str_contains($index, '/assets/app.css?v=')
    && str_contains($index, "header('Cache-Control: no-store"), '前端資源使用內容版本號，避免部署後沿用舊快取');

contractCheck(str_contains($render, 'dockerfilePath: ./Dockerfile.render')
    && preg_match('/key: DATABASE_URL\s*\n\s*#.*\n\s*#.*\n\s*sync: false/s', $render) === 1,
    'Render 使用正式 Dockerfile 並保留 Neon DATABASE_URL 為外部 Secret');
contractCheck(str_contains($render, "key: AI_API_KEY\n        value: \"\""), 'Render 保留空白 AI_API_KEY 欄位');
contractCheck(str_contains($render, "key: AI_FEATURE_ENABLED\n        value: \"false\""), '非規格核心的 AI 規劃預設停用');
contractCheck(str_contains($migrate, '20261022_archive_neon_sample'), '部署會將 Neon 範例表移出正式 public schema 並保留內容');
contractCheck(preg_match('/key: DEMO_ADMIN_PASSWORD\s*\n\s*#.*\n\s*sync: false/s', $render) === 1
    && !preg_match('/key: DEMO_ADMIN_PASSWORD\s*\n\s*value:\s*\S+/s', $render), 'Render 不把管理員密碼寫入 Git，改由 Dashboard Secret 提供');
contractCheck(str_contains($maintenance, 'bin/cleanup-expired.php')
    && str_contains($maintenance, 'pg_dump')
    && str_contains($maintenance, 'pg_restore')
    && str_contains($maintenance, 'cron: "0 19 * * *"')
    && str_contains($maintenance, 'retention-days: 7'), '每日清理、備份與獨立還原工作流程已定義');
contractCheck(str_contains($loadScript, 'noCookiesReset: true')
    && str_contains($loadScript, "'X-Forwarded-For': benchmarkIp()")
    && str_contains($loadWorkflow, '--env TRUSTED_PROXY_IPS=127.0.0.1')
    && str_contains($loadWorkflow, '--user "$(id -u):$(id -g)"'),
    '200 人驗收保留每位使用者 Cookie、分離登入 IP 並可寫出摘要');
$mediaLines = preg_grep('/^[a-f0-9]{64}  /', preg_split('/\R/', $mediaManifest) ?: []);
contractCheck(count($mediaLines) >= 2600, '動作圖片 SHA-256 清單涵蓋完整資料集');
