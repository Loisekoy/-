# FitTrack Pro PHP

依據 `Fitness_Tracking_Management_System_SRS.pdf` 製作的資料庫系統網站。正式資料庫使用 PostgreSQL；本機預覽若未設定 `DATABASE_URL`，會自動使用 SQLite 建立相同的 15 張核心資料表。

## 已完成的主要流程

- 會員註冊、登入、JWT 工作階段與登出撤銷
- 基本資料、訓練目標、每週天數、時間與偏好部位
- 動作搜尋、中文步驟與本機 GIF 示範
- 規則式課表產生，保留目標、程度與時間快照
- 可選的 OpenAI 相容模型課表規劃，後端驗證模型回傳的動作、天數與組次
- 課表 GIF 示意、名稱／動作／組次／休息時間編輯
- 開始／繼續訓練、逐組新增／修改／刪除、休息計時、備註、完成與取消
- 訓練歷史、體重紀錄、總訓練量與 Dashboard
- 管理員統計、會員清單、動作啟用／停用與 15 張資料表唯讀管理系統

## 本機啟動

需求：PHP 8.4 以上，並啟用 PDO、pdo_sqlite。若要連 PostgreSQL，另需 pdo_pgsql。

```bash
cp .env.example .env
php bin/setup.php
php -S 127.0.0.1:8080 -t public public/router.php
```

開啟 `http://127.0.0.1:8080`。

示範帳號：

- 會員：`demo@fittrack.local` / `Demo12345`
- 管理員：`admin@fittrack.local` / `Admin12345`

示範密碼只供本機驗收，部署前必須刪除或更換。

## PostgreSQL

1. 建立空白資料庫。
2. 執行 `database/postgres.sql`。
3. 在 `.env` 設定 `DATABASE_URL` 與新的 `APP_KEY`。
4. 執行 `php bin/setup.php` 匯入目標、部位、示範帳號與動作資料。

```bash
psql "$DATABASE_URL" -f database/postgres.sql
php bin/setup.php
```

## Docker

專案附有 PHP 8.4 + Apache 映像設定。部署時先建立 PostgreSQL schema 與 seed，再啟動網站容器：

```bash
docker build -t fittrack-php .
docker run --rm -p 8080:80 --env-file .env fittrack-php
```

容器啟動時會以可重複執行的方式建立 PostgreSQL schema、匯入 48 個動作與 GIF 對應資料，再啟動 Apache。

## Render

儲存庫根目錄的 `render.yaml` 會建立一個 Docker Web Service 與一個 PostgreSQL 資料庫。Render 建立 Blueprint 時，請填入以下祕密值：

- `DEMO_BOOTSTRAP_PASSWORD`
- `ADMIN_BOOTSTRAP_PASSWORD`
- `AI_API_KEY`（可稍後填入；不填時仍可使用規則式課表）
- `AI_MODEL`（模型供應商提供的模型名稱）

`AI_API_URL` 預設為 OpenAI Chat Completions 網址，也可在 Render Environment 改成其他 OpenAI 相容服務的完整網址。API Key 只存在 Render 的環境變數，不會寫入資料庫或回傳前端。管理員可在「模型接口」頁確認是否啟用，但看不到金鑰內容。

部署完成後使用 `demo@fittrack.local` 或 `admin@fittrack.local`，搭配你在 Render 填入的密碼登入。健康檢查路徑為 `/api/health`。

## 測試

```bash
php tests/smoke.php
```

測試會使用獨立的暫存 SQLite，驗證 15 張表、JWT、課表產生、訓練量彙總、歷史保留、管理員資格與資料庫管理 API，不會修改正式資料庫。

## 資料來源

動作文字與 GIF 取自工作區中的 `參考資料/exercises-dataset-main`。媒體依原資料集 `NOTICE.md` 標示為 Gym visual。
