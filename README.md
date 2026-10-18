# FitTrack Pro｜健身紀錄管理系統

這是依據 `參考資料/Fitness_Tracking_Management_System_SRS_.md` 實作的資料庫課程專案。Render 目前部署的是 `web/php-app` 這個正式 PHP 版本。

## 公開網站

- 公開網站：[https://fittrack-pro-php.onrender.com](https://fittrack-pro-php.onrender.com)
- 管理者登入：[https://fittrack-pro-php.onrender.com/admin/login](https://fittrack-pro-php.onrender.com/admin/login)
- 資料庫系統頁：登入管理者後選擇「管理 → 資料庫系統」
- GitHub 部署分支：`codex/fitness-tracking-system`

課堂展示管理者帳號只供 Render 公開展示流程使用；為避免憑證進入公開 GitHub，帳密不寫入本 README，也不會顯示在公開登入頁。管理者登入資訊請由專案維護者私下提供，不可用於真實個資或正式營運。

## 目前使用的架構

```text
瀏覽器 HTML/CSS/JavaScript
        ↓ Fetch API（同源 /api）
PHP 8.4 + Apache + PDO_PGSQL
        ↓ DATABASE_URL（Render Secret）
Neon PostgreSQL
```

- 前端：原生 HTML、CSS、JavaScript，檔案位於 `web/php-app/public/`
- 後端：PHP API 與資料驗證，檔案位於 `web/php-app/src/`
- 資料庫：正式環境 PostgreSQL 16；本機快速測試使用 SQLite
- 部署：`Dockerfile.render` + `render.yaml` + Render Web Service
- AI：保留 `AI_API_KEY`、`AI_MODEL` 與 `AI_API_URL` 欄位；目前 `AI_API_KEY` 空白時仍使用規則式排課

## 已實作功能

- 註冊、登入、登出、修改密碼、停用帳號與 Cookie Session
- 個人資料、訓練目標、訓練天數／時間與偏好部位
- 1,324 筆動作、2,648 個 JPG/GIF 動作媒體與動作搜尋／分頁
- 電腦規劃與使用者自訂課表；電腦規劃會避開最近課表並隨機選擇動作
- 課表編輯、封存、訓練場次快照與歷史紀錄
- 每組重量／次數立即儲存、冪等重送、修改與刪除
- 總訓練計時器；休息計時器只在成功儲存一組後開始
- 完成、取消與刪除訓練場次
- Dashboard、訓練量、徒手次數、體重歷史與日期篩選
- 管理員動作版本、固定參考資料與唯讀資料庫系統頁
- 20 張應用資料表、25 條外鍵、PostgreSQL Trigger 與 Migration

## 本機啟動

需求：PHP 8.4+，並啟用 PDO、`pdo_sqlite`；連接 PostgreSQL 時另需 `pdo_pgsql`。

```bash
cd web/php-app
cp .env.example .env
php bin/setup.php
php -S 127.0.0.1:8080 -t public public/router.php
```

開啟 <http://127.0.0.1:8080>。本機資料庫是 `web/php-app/storage/app.sqlite`；正式 PostgreSQL Schema 是 `web/php-app/database/postgres.sql`。

## 驗收測試

```bash
cd web/php-app
php tests/admin_bootstrap.php
php tests/ui_contract.php
php tests/smoke.php
php tests/sqlite_migration.php
php tests/cleanup_expired.php
python3 tests/schema_consistency.py
php bin/verify-media-manifest.php
node --check public/assets/app.js
```

PostgreSQL 專屬 Trigger／Constraint／併發測試必須使用名稱含 `fittrack_` 的隔離測試資料庫：

```bash
FITTRACK_TEST_DATABASE=1 DATABASE_URL='postgresql://.../fittrack_test' php tests/postgres_integrity.php
```

200 位使用者、P95、瀏覽器相容性矩陣與備份還原，仍須在正式測試環境另外執行，不能用 SQLite 結果代替。

## 主要文件

- `web/php-app/README.md`：目前 PHP 應用的完整啟動、資料庫與部署說明
- `web/php-app/database/postgres.sql`：正式 PostgreSQL Schema、Trigger 與外鍵
- `web/docs/SQL_QUERIES.md`：常用資料庫查詢範例
- `web/docs/schema_manifest.json`：資料表與外鍵結構清單
- `web/docs/diagrams/architecture_v1_1.mmd`：系統架構圖原始檔
- `參考資料/Fitness_Tracking_Management_System_SRS_.md`：軟體需求規格書
