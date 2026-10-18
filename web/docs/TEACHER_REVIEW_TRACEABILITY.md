# 老師 12 項意見修訂與驗收對照表

專案：Fitness Tracking Management System（健身紀錄管理系統）  
正式修訂版：v1.1（2026-10-06）  
主要實作：`web/php-app`（PHP 8.4 + PostgreSQL 16）

狀態只使用「已修正且已驗證」、「已修正但尚未驗證」、「受阻」或「不適用，附具體理由」。本表的「驗證結果」均為本次隔離測試環境的實際結果；不等同正式雲端環境或 200 人效能測試已通過。

| 編號 | 老師指出的原始問題 | 正式修正 | 主要落點 | 文件狀態 | 實作狀態 | 驗證方法與實際結果 |
|---|---|---|---|---|---|---|
| A1 | `workout_sets` 缺少場次來源防護，動作主檔變更會破壞歷史 | 新增不可變 `exercise_versions`、開始運動時建立 `workout_session_exercises` 快照；`workout_sets` 只參照場次動作，不重存 `exercise_id`。本版不允許課表外臨時動作。 | SRS 3.5、3.7、4.2、4.5、4.6；R08–R09、R22–R25；DDL、Migration、`Api.php` | 已修正且已驗證 | 已修正且已驗證 | SQLite 回歸與 PostgreSQL 反向測試皆 PASS；跨場次快照被 Trigger 拒絕；歷史仍讀到 V1 名稱與處方。 |
| A2 | 登出／停用立即失效與過期 Session 清理混淆，沒有可部署排程 | 每次認證依 `jti` 查 `user_sessions`，登出、改密碼與停用立即撤銷；另以 `cleanup-expired.php` 每日分批清除到期 Session 與舊限流事件。 | SRS 2.1、2.2、3.2、4.9、TC-05／06／31；`Auth.php`、`bin/cleanup-expired.php`、`render.yaml` | 已修正且已驗證 | 已修正且已驗證 | 清理測試實際刪除 1 筆過期 Session 與 1 筆舊事件，仍保留 1 筆有效 Session；Smoke 驗證登出與停用後舊 Token 失效。 |
| A3 | 體重與訓練重量精度不一致，邊界及小數政策不完整 | 公斤欄位統一 `NUMERIC(6,2)`；體重 20.00–500.00 kg，外加重量 0.00–999.99 kg；最多兩位小數，超限由 API 與 CHECK 雙層拒絕。 | SRS FR-04／13／18、4.2；PostgreSQL／SQLite Schema、Migration | 已修正且已驗證 | 已修正且已驗證 | Smoke 邊界與非法值測試 PASS；PostgreSQL Fresh Schema 及舊版資料 Migration 均成功。 |
| A4 | ERD 的 R 編號、外鍵對照與 DDL 數量不一致 | 以最終 PostgreSQL DDL 為唯一來源，重繪 4 張分區 ERD；R01–R25 與 4.3 節及 Schema Manifest 一一對應。 | SRS 圖 2–5、4.2、4.3；`docs/diagrams`、`docs/schema_manifest.json` | 已修正且已驗證 | 已修正且已驗證 | `schema_consistency.py` PASS：20 張應用表、25 條 FK；Fresh PostgreSQL 同樣回報 20／25。 |
| B1 | Profile 完成後能刪光體重；並行刪除可能留下零筆 | `profile_completed_at` 表示已完成 Profile；最後一筆體重不可刪但可修改。API 鎖定 `users`，DB deferred constraint trigger 在 COMMIT 再驗證。 | SRS FR-04／18、4.5.3、TC-07／21；`Api.php`、DDL、Migration | 已修正且已驗證 | 已修正且已驗證 | Smoke 驗證新增、修改、回退及最後一筆 409；PostgreSQL Trigger 反向測試 PASS。 |
| B2 | 課表鎖定與進行中場次調整互相矛盾 | 課表模板、場次快照、場次目標與實際組數分離。進行中禁止改來源模板，但可修改當場目標；取消或完成後來源模板再解鎖，歷史快照不回寫。 | SRS FR-11、3.10、4.5.2、TC-11；`workout_session_exercises`、`Api.php`、前端 | 已修正且已驗證 | 已修正且已驗證 | Smoke 驗證來源模板 409、本場目標 200、完成後舊歷史不變。 |
| B3 | 徒手運動量為 0 容易被解讀為沒有運動 | 原「總訓練量」改為「外加重量訓練量（kg·次）」；另列完成組數、總次數、徒手次數，避免把不同單位相加。未來如引入徒手等效負荷，需以具版本的動作係數乘上場次開始時體重快照與次數，並與實際外加重量分開呈現。 | SRS FR-17、TC-20；Dashboard 查詢與介面 | 已修正且已驗證 | 已修正且已驗證 | 測試資料 60×12、65×10、65×8、徒手 0×15：外加重量量 1890、總次數 45、徒手次數 15；取消場次排除。 |
| C1 | Token 只放前端記憶體，重新整理即登出；Cookie／CSRF 未定義 | Access JWT 效期 7,200 秒，存於 `Secure`、`HttpOnly`、`SameSite=Strict` Cookie；JWT 僅含 `sub/jti/iat/exp`。同源 Origin／Referer 與 double-submit CSRF 保護寫入；`GET /auth/session` 在 F5 後恢復狀態。 | SRS FR-01／02、4.7、NFR-05、TC-01／05；`Auth.php`、`RequestSecurity.php`、`api.php`、`app.js` | 已修正且已驗證 | 已修正且已驗證 | Smoke 驗證 Cookie 屬性、JWT 無 role、CSRF、登出撤銷及重新載入流程；PHP 語法檢查 PASS。 |
| C2 | PHP Worker 間沒有共用且原子的登入限流 | 以 PostgreSQL `login_failures` 實作 15 分鐘滑動視窗；對 `ip_hash` 取 transaction advisory lock。前 20 次失敗回 401，第 21 次回 429；成功登入清除；來源 IP 只信任精確白名單代理。 | SRS 4.9、NFR-08、TC-27；`LoginRateLimiter.php`、`RequestSecurity.php`、DDL、清理腳本 | 已修正且已驗證 | 已修正且已驗證 | Smoke 驗證第 20／21 次邊界、不同 IP 與成功後清除；Schema 有索引與清理流程。多容器正式負載仍須部署後量測。 |
| D1 | 目錄、頁碼與交叉引用可能沿用舊版 | 以 Word Styles 與自動目錄重建，使用 Microsoft Word 更新欄位並原生輸出 PDF；目錄指向第 4、6、8、23、50、54、55 頁。 | 正式 DOCX／PDF 的目錄、頁尾與交叉引用 | 已修正且已驗證 | 不適用，附具體理由：文件排版不屬於系統執行功能 | DOCX 結構掃描與 Word 顯示皆為 55 頁；PDF `pdfinfo` 為 55 頁，逐項核對目錄頁碼一致。 |
| D2 | 資料字典表格、ERD 可能截斷、跨頁不可讀 | 統一欄寬、內距、灰藍表頭、重複表頭與識別字；ERD 以高解析分區圖呈現；PDF 全頁渲染檢查。 | SRS 4.1–4.3、圖 1–5、表 4.2.1–4.2.20、TC 表 | 已修正且已驗證 | 不適用，附具體理由：文件排版不屬於系統執行功能 | 55／55 頁均渲染檢查；無裁切、亂碼或超出頁面，ERD、SQL 與表格可讀。 |
| D3 | JSON／JWT／PostgreSQL 等大小寫、核心名詞及表／FK 數量不一致 | 統一 JSON、JWT、PostgreSQL、Schema、Migration、Session 等名詞；統一 20 表／25 FK；移除舊 19 表／23 FK、Phinx 等殘留文字。 | SRS 全文、README、Schema、變更紀錄 | 已修正且已驗證 | 已修正且已驗證 | DOCX XML 與 PDF 文字掃描無舊數量及已淘汰名詞；`schema_consistency.py` 與實際 PostgreSQL 結果一致。 |

## 可重跑驗證命令

```bash
cd web/php-app

find . -name '*.php' -print0 | xargs -0 -n1 php -l
php tests/smoke.php
python3 tests/schema_consistency.py
node --check public/assets/app.js
```

PostgreSQL 專屬完整性測試必須使用隔離測試資料庫，並將連線字串透過環境變數傳入：

```bash
TEST_DATABASE_URL='postgresql://<test-user>:<password>@<host>:<port>/<test-db>' \
php tests/postgres_integrity.php
```

Migration 驗證以舊版代表資料庫執行 `bin/migrate.php`，完成後再執行 `tests/schema_consistency.py` 與歷史查詢。敏感連線資訊不得寫入 Git。

## 驗證邊界

1. 本次已在隔離 PostgreSQL 16 執行 Fresh Schema、Migration、Trigger、歷史快照、兩個平行開始請求與排程清理測試。
2. 第 5 章 NFR-01／NFR-02 的 P95 與 200 人、5 分鐘壓力測試尚未在正式雲端環境執行，因此文件將其標示為驗收門檻，不宣稱已通過。
3. 本次未部署正式雲端資料庫、未修改正式環境、未推送 GitHub；只產生可部署設定與隔離測試證據。
