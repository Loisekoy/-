# FitTrack Pro 驗收修正報告

日期：2026-10-18（總檢查更新）
範圍：本機 `web/php-app`、根目錄 Render 設定與 GitHub 維運流程。
原則：未在隔離 PostgreSQL 或正式雲端實測的項目，不標示為通過。

## 本次修正

- 管理員後台動作與參考資料欄位補上 `label for`／`id` 關聯，符合鍵盤與讀屏辨識要求。
- 課表操作顯示「封存課表」，保留後端 soft archive 語意。
- 訓練頁保留總訓練計時器；休息計時器初始顯示「儲存一組後開始」，只有組數 API 成功後才啟動；取消本次訓練會清理計時器並寫入 cancelled 狀態。
- `bin/setup.php` 每次容器啟動會依 `DEMO_ADMIN_PASSWORD` 同步展示管理員密碼，修正既有 Neon 資料庫沿用舊雜湊造成的登入失敗。
- 新增 `tests/admin_bootstrap.php` 與 `tests/ui_contract.php`，把上述行為與 Render／備份契約納入可重跑檢查。

## 本機驗證結果

以下命令已在 2026-10-18 重新執行並通過：

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

結果包括：20 張應用表、25 條 FK、完整 SQLite 功能流程、舊版資料升級、501 筆分批清理、管理員密碼輪替、圖片 SHA-256 清單、總／休息計時器與取消／封存 UI 契約均 PASS；全 PHP 語法與 JavaScript 語法也通過。

## 已完成的公開站抽查

公開站 `https://fittrack-pro-php.onrender.com/admin/login` 已在 2026-10-18 以課堂展示管理員帳號登入成功，管理後台顯示 `ADMIN`、1,324 筆動作、20 張資料表與 25 條外鍵；瀏覽器 Console 沒有 error 或 warning。

## 仍需正式環境執行的完整驗收

這些不是本機程式碼缺口，而是需要部署後的外部證據：

1. 在隔離 PostgreSQL 執行 `FITTRACK_TEST_DATABASE=1 php tests/postgres_integrity.php`，取得 Trigger、Constraint 與併發證據；本機目前沒有可安全使用的隔離 PostgreSQL，因此本項未宣稱通過。
2. 執行 GitHub Actions `fittrack-load-acceptance.yml`，取得 200 虛擬使用者、5 分鐘、P95 與錯誤率結果；目前 GitHub Actions 尚無此分支的執行紀錄。
3. 以 Chrome、Safari、Edge 各最新兩個主要版本完成註冊、產課與逐組儲存；目前已完成公開站登入／管理／資料庫頁抽查，尚不是完整瀏覽器矩陣。
4. 在 GitHub Actions 設定 `FITTRACK_DATABASE_URL` 與 `FITTRACK_BACKUP_KEY` 後手動執行一次每日維運流程，確認 PostgreSQL 還原、20／25 結構、筆數與媒體雜湊驗證通過。

## 規格書差異註記

規格書 FR-04 的功能敘述曾寫身高 `90–250 cm`，但同一份規格書的資料表欄位、TC-07 與 PDF 表格寫的是 `100–250 cm`。目前實作採用資料表與驗收案例的 `100–250 cm`，這是規格書本身的文字矛盾，不是程式與驗收案例的差異；正式交件前應請老師確認要以哪一個範圍為準。

因此本報告仍把「本機驗證」、「公開站抽查」與「正式 PostgreSQL／負載驗收」分開，不把未取得外部證據的項目標示為通過。
