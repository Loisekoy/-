# Fitness Tracking Management System — PHP Application

本專案是以資料庫設計為核心的健身紀錄管理系統。正式環境使用 PostgreSQL 16，後端使用 PHP 8.4 + PDO，前端為同源 HTML/CSS/JavaScript。SQLite 僅用於本機快速預覽與煙霧測試。

## 已完成功能

- 註冊、登入、登出、修改密碼與停用帳號
- 使用者基本資料、體重歷史、訓練目標與偏好部位
- 動作資料庫、不可變動作版本、管理員新增／修改／停用
- 本機資料集 1,324 筆動作、JPG 與 GIF 可重跑匯入，動作庫提供搜尋、篩選與分頁
- 使用者可自行安排 2 至 6 個訓練日，從完整動作庫挑選動作並設定順序、組數、次數與休息時間
- 電腦規劃保留目標、程度、偏好部位、時間與八部位覆蓋規則，並優先避開最近三份課表及同一份課表的重複動作
- OpenAI 相容模型接口保留於後端，模型不可用時不影響自己規劃與電腦規劃
- 課表模板、規劃輸入快照、開始／繼續／完成／取消訓練
- 總訓練時間由場次開始時間持續計算；休息倒數只在成功儲存一組後啟動
- 開始訓練時建立 `workout_session_exercises` 場次動作快照
- 每組 Weight / Reps 立即寫入、冪等重送、本場目標調整
- Workout History、Exercise History、體重歷史、Dashboard
- History／Dashboard 採台北日期篩選，預設最近 28 天、最長 366 天
- 外加重量訓練量 `weight_kg × reps`、完成次數與徒手次數分開統計
- 資料庫管理頁：20 張應用資料表、25 條外鍵關係與查詢範例

## 安全與交易邊界

- JWT 僅放 `sub` / `jti` / `iat` / `exp`，不把 `role` 當成即時授權來源。
- 管理員權限每次從 `admins` 查詢，所以撤權可立即生效。
- 瀏覽器以 `HttpOnly` + `SameSite=Strict` Cookie 儲存 Access Token；CSRF Token 以 HMAC 綁定目前 Access Token，寫入要求同時驗證同源、Cookie、Header 與簽章。
- JWT Header 固定只接受 `HS256`，Payload 必須包含型別正確的 `sub`、`jti`、`iat`、`exp`。
- PostgreSQL 明確採用 `READ COMMITTED`。開始運動時鎖定使用者資料列，並以部分唯一索引作為最後防線。
- 完成場次至少一組、完整 Profile 至少一筆體重、動作版本不可覆寫，均有資料庫 Trigger 保護。
- 登入限流以 PostgreSQL `login_failures` 實作 15 分鐘滑動視窗；第 21 次失敗要求回應 429。

## 本機啟動

需求：PHP 8.4+，並啟用 PDO、`pdo_sqlite`；連線 PostgreSQL 時另需 `pdo_pgsql`。

```bash
cp .env.example .env
php bin/setup.php
php -S 127.0.0.1:8080 -t public public/router.php
```

開啟 `http://127.0.0.1:8080`。本機示範帳號：

- 會員：`demo@fittrack.local` / `Demo12345`
- 管理員：`admin@fittrack.local` / `Admin12345`

## 動作資料匯入

資料集預設位於 `../../參考資料/exercises-dataset-main`。下列指令會驗證 1,324 筆資料與兩種媒體、補入目前資料庫、複製 JPG/GIF 到 `public/media/exercises/`，並更新可供全新資料庫使用的 `database/exercises-seed.json`：

```bash
php bin/import-exercises.php
```

也可將資料集絕對路徑當作第一個參數。此流程以資料集 ID 識別既有動作；內容變更時會新增不可變版本，不會刪除課表或歷史紀錄。

## 資料庫位置

- 本機目前使用 SQLite：`storage/app.sqlite`。
- SQLite 建表定義：`database/sqlite.sql`。
- 正式 PostgreSQL 建表定義：`database/postgres.sql`；部署時由 `DATABASE_URL` 指向雲端資料庫，不會使用本機 SQLite 檔案。
- 管理員登入後可從「管理 → 資料庫系統」查看 20 張應用資料表、25 條外鍵與查詢範例。

上述管理員是刻意公開的課堂展示帳號，不可存放真實個資或正式環境資料；正式上線前必須改用未公開的密碼。

若本機已有舊版 15 表的 `storage/app.sqlite`，首次執行會先在同目錄建立
`app.sqlite.backup-v1.0-<UTC時間>` 備份，再原地升級為 20 表的 v1.1 結構；
會員、課表、歷史組數與體重資料都會保留。

## PostgreSQL 與 Migration

全新空資料庫：

```bash
psql "$DATABASE_URL" -f database/postgres.sql
php bin/setup.php
```

舊版 Schema 升級至 v1.1：

```bash
php bin/migrate.php
```

Migration 檔案為 `database/migrations/20261006_teacher_review_v1_1.sql`。正式執行前必須先備份；Migration 會在交易內進行先備條件檢查與資料回填，失敗即回滾。

## 過期資料清理

`bin/cleanup-expired.php` 每批最多刪除 500 筆過期 `user_sessions`，並清理超過 15 分鐘的 `login_failures`。正式環境由 GitHub Actions 的 `.github/workflows/fittrack-maintenance.yml` 每日台北時間 03:17 執行，不需另外購買 Render Cron Service。排程日誌只記錄刪除筆數、執行時間與時區，不輸出 Token、雜湊或連線字串。

## 每日備份與還原驗證

同一個 GitHub Actions 排程會完成下列步驟：

1. 使用 `pg_dump` 產生 PostgreSQL custom-format 備份。
2. 還原到獨立 PostgreSQL 16 測試庫，核對 20 張表、25 條外鍵、Schema 版本與每表筆數。
3. 使用 `docs/validation/media-sha256.txt` 核對 2,648 個 JPG/GIF 檔案。圖片本體由 Git 的不可覆寫 commit 保留，每份資料庫備份同時收入對應 SHA-256 清單。
4. 將資料庫、筆數 Manifest 與媒體雜湊清單以 AES-256-CBC + PBKDF2 加密，再上傳為保留 7 天的 Workflow Artifact。公開儲存庫不會上傳明文資料庫。

排程需在 GitHub 設定兩個 Repository Secrets：`FITTRACK_DATABASE_URL`與至少 32 字元的 `FITTRACK_BACKUP_KEY`。排程檔必須存在預設分支；公開儲存庫 60 天沒有任何活動時，GitHub 可能自動停用排程，驗收前應於 Actions 頁面確認最近一次執行成功。

## 測試

```bash
php tests/smoke.php
php tests/sqlite_migration.php
php tests/cleanup_expired.php
php tests/admin_bootstrap.php
php tests/ui_contract.php
php bin/verify-media-manifest.php
python3 tests/schema_consistency.py
DATABASE_URL='postgresql://.../fittrack_test' FITTRACK_TEST_DATABASE=1 php tests/postgres_integrity.php
```

- `smoke.php`：在暫存 SQLite 驗證完整功能流程。
- `cleanup_expired.php`：建立 501 筆過期 Session 驗證分批清理、有效資料保留與無機密日誌。
- `admin_bootstrap.php`：驗證容器重啟時會同步 `ADMIN_BOOTSTRAP_PASSWORD`，且舊密碼失效。
- `ui_contract.php`：驗證總計時器、儲存後休息計時器、取消／封存操作、表單標籤、Render Secret 與每日備份還原契約。
- `verify-media-manifest.php`：比對 2,648 個動作媒體的 SHA-256。
- `schema_consistency.py`：比對 `postgres.sql` 與 `docs/schema_manifest.json`。
- `postgres_integrity.php`：只允許在名稱含 `fittrack_` 的隔離測試庫執行，驗證 PostgreSQL Trigger、Constraint 與兩個平行開始請求。

## 部署環境變數

必要值：`DATABASE_URL`、`SECRET_KEY`、`RATE_LIMIT_SECRET`、`DEMO_BOOTSTRAP_PASSWORD`、`ADMIN_BOOTSTRAP_PASSWORD`。正式環境的 `DATABASE_URL` 必須使用 `sslmode=require`、`verify-ca` 或 `verify-full`；不加密的 PostgreSQL 連線會直接拒絕啟動。`TRUSTED_PROXY_IPS` 僅能列出自己控制的 Reverse Proxy；未設定時不信任 `X-Forwarded-For`。AI 相關變數為選填。

根目錄的 `render.yaml` 建立 Render Docker Web Service，並由 Render 產生 `SECRET_KEY`、`RATE_LIMIT_SECRET`。`DATABASE_URL` 使用 `sync: false`，由 Render Dashboard 安全指向 Neon PostgreSQL，不會被 Blueprint 覆寫或寫入 Git。課堂展示管理員固定使用公開密碼 `Admin12345`，每次啟動會同步該展示帳號的密碼。`AI_API_KEY`、`AI_MODEL` 預設保持空白，因此不會阻擋核心功能部署；要啟用 AI 規劃時，請在 Render 的 Environment 頁面同時填入這兩個值，金鑰不可寫進 Git。

本次 72 頁規格書的本機實作狀態請見 `../docs/validation/IMPLEMENTATION_STATUS_2026-10-14.md`；完整架構、ERD 與資料字典位於 `../output/specification/`。
