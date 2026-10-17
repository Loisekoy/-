# FitTrack Pro 驗收修正報告

日期：2026-10-17（依 2026-10-16 驗收結果更新部署狀態）
範圍：本機 `codex生成/php-app`、根目錄 Render 設定與 GitHub 維運流程。
原則：未在隔離 PostgreSQL 或正式雲端實測的項目，不標示為通過。

## 本次修正

- 管理員後台動作與參考資料欄位補上 `label for`／`id` 關聯，符合鍵盤與讀屏辨識要求。
- 課表操作顯示「封存課表」，保留後端 soft archive 語意。
- 訓練頁保留總訓練計時器；休息計時器初始顯示「儲存一組後開始」，只有組數 API 成功後才啟動；取消本次訓練會清理計時器並寫入 cancelled 狀態。
- `bin/setup.php` 每次容器啟動會依 `ADMIN_BOOTSTRAP_PASSWORD` 同步展示管理員密碼，修正既有 Neon 資料庫沿用舊雜湊造成的登入失敗。
- 新增 `tests/admin_bootstrap.php` 與 `tests/ui_contract.php`，把上述行為與 Render／備份契約納入可重跑檢查。

## 本機驗證結果

以下命令均在 2026-10-16 執行並通過：

```text
node --check public/assets/app.js
php tests/admin_bootstrap.php
php tests/ui_contract.php
php tests/smoke.php
php tests/sqlite_migration.php
php tests/cleanup_expired.php
python3 tests/schema_consistency.py
php -l（全部 PHP 檔案）
```

結果包括：20 張應用表、25 條 FK、完整 SQLite 功能流程、舊版資料升級、501 筆分批清理、管理員密碼輪替、圖片 SHA-256 清單、總／休息計時器與取消／封存 UI 契約均 PASS。

## 仍需正式環境執行的驗收

這些不是本機程式碼缺口，而是需要部署後的外部證據：

1. 本次修正會隨本次提交推送到 GitHub；Render 仍需完成自動部署（或在 Dashboard 手動觸發）後，公開站的管理員登入才會反映密碼同步修正。
2. 在隔離 PostgreSQL 執行 `FITTRACK_TEST_DATABASE=1 php tests/postgres_integrity.php`，取得 Trigger、Constraint 與併發證據。
3. 執行 GitHub Actions `fittrack-load-acceptance.yml`，取得 200 虛擬使用者、5 分鐘、P95 與錯誤率結果。
4. 以 Chrome、Safari、Edge 各最新兩個主要版本完成註冊、產課與逐組儲存；目前已完成本機／公開站的功能抽查與 375×812、768×1024、1440×900 響應式檢查，但尚不是完整矩陣。
5. 在 GitHub Actions 設定 `FITTRACK_DATABASE_URL` 與 `FITTRACK_BACKUP_KEY` 後手動執行一次每日維運流程，確認 PostgreSQL 還原、20／25 結構、筆數與媒體雜湊驗證通過。

因此本報告仍把「本機驗證」與「公開站驗收」刻意分開：GitHub push 不等於 Render 已部署，必須等 Render 部署完成後再重新驗證公開站。
